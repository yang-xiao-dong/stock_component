# -*- coding: utf-8 -*-
"""图表取数回归测试：接口被拦截或返回无效响应时的回退（离线）。"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import stock_api


def response(payload, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = (payload if isinstance(payload, str) else json.dumps(payload)).encode()
    return result


class ChartApiTests(unittest.TestCase):
    def test_minute_recovers_from_block_page(self):
        payload = {"code": 0, "data": {"sh603893": {"data": {"date": "20260922", "data": [
            "0930 203.90 1383 28199370.00", "0931 205.17 8642 176949561.29",
        ]}}}}
        with patch.object(stock_api.session, "get", side_effect=[
            response("<html>blocked</html>", 501), response(payload),
        ]) as get:
            points = stock_api.get_minute_data("sh603893")
        self.assertEqual([p["price"] for p in points], [203.90, 205.17])
        self.assertEqual([p["date"] for p in points], ["2026-09-22", "2026-09-22"])
        self.assertEqual([p["time"] for p in points], ["09:30", "09:31"])
        self.assertEqual([p["vol"] for p in points], [1383, 8642])
        self.assertEqual(get.call_count, 2)
        self.assertNotEqual(get.call_args_list[0].args[0], get.call_args_list[1].args[0])

    def test_kline_preserves_ohlc_and_request(self):
        payload = {"code": 0, "data": {"sh603893": {"qfqday": [
            ["2026-09-22", "203.90", "217.80", "217.80", "203.90", "254013"],
        ]}}}
        with patch.object(stock_api.session, "get", return_value=response(payload)) as get:
            bars = stock_api.get_kline("sh603893", 60)
        self.assertEqual(bars, [{"date": "2026-09-22", "open": 203.9,
                                 "close": 217.8, "high": 217.8, "low": 203.9,
                                 "vol": 254013.0}])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"]["param"], "sh603893,day,,,60,qfq")

    def test_kline_and_close_end_date_fill_fourth_param_slot(self):
        kline_payload = {"data": {"sh603893": {"qfqday": [["2023-07-05", "10", "11", "12", "9"]]}}}
        close_payload = {"data": {"sh603893": {"day": [["2023-07-05", "10", "11", "12", "9"]]}}}
        with patch.object(stock_api.session, "get", return_value=response(kline_payload)) as get:
            stock_api.get_kline("sh603893", 5, end="2023-07-05")
            self.assertEqual(get.call_args.kwargs["params"]["param"], "sh603893,day,,2023-07-05,5,qfq")
        with patch.object(stock_api.session, "get", return_value=response(close_payload)) as get:
            stock_api.get_close_series("sh603893", 5, end="2023-07-05")
            self.assertEqual(get.call_args.kwargs["params"]["param"], "sh603893,day,,2023-07-05,5,")

    def test_invalid_payload_uses_backup(self):
        valid = {"data": {"sh603893": {"day": [
            ["2026-09-22", "10", "11", "12", "9"],
        ]}}}
        for invalid in ("<html>not JSON</html>", {"code": -1, "data": {}}, {"data": {}}):
            with self.subTest(invalid=invalid), patch.object(stock_api.session, "get", side_effect=[
                response(invalid), response(valid),
            ]):
                self.assertEqual(stock_api.get_kline()[0]["close"], 11)

    def test_all_endpoints_unavailable_returns_none(self):
        for fetch in (stock_api.get_minute_data, stock_api.get_kline):
            with self.subTest(fetch=fetch.__name__), patch.object(
                stock_api.session, "get", side_effect=requests.Timeout("timeout"),
            ) as get:
                self.assertIsNone(fetch())
                self.assertEqual(get.call_count, 4 if fetch is stock_api.get_kline else 2)

    def test_adjustment_metadata_follows_actual_response(self):
        for field, expected in (("qfqday", "qfq"), ("day", "none")):
            payload = {"data": {"sh603893": {field: [["2026-09-22", "10", "11", "12", "9"]]}}}
            with self.subTest(field=field), patch.object(stock_api.session, "get", return_value=response(payload)):
                batch = stock_api.get_kline_batch("sh603893", 60)
                self.assertEqual(batch.adjustment, expected)
                self.assertEqual(batch.raw, payload["data"]["sh603893"][field])

    def test_minute_history_days_are_split_per_day(self):
        payload = {"code": 0, "data": {"sh603893": {"data": [
            {"date": "20261023", "data": ["0930 10.0 1 100.0", "0931 11.0 2 220.0"]},
            {"date": "20261022", "data": ["0930 9.0 1 90.0"]},
        ]}}}
        with patch.object(stock_api.session, "get", return_value=response(payload)) as get:
            batches = stock_api.get_minute_history_batches("sh603893")
        self.assertEqual(get.call_args.kwargs["params"], {"code": "sh603893"})
        self.assertEqual([b.rows[0]["date"] for b in batches], ["2026-10-23", "2026-10-22"])
        self.assertEqual(batches[0].rows[0], {"date": "2026-10-23", "time": "09:30", "price": 10.0, "vol": 1.0})
        self.assertEqual(batches[1].kind, "minute")

    def test_quote_response_uses_symbols_instead_of_response_position(self):
        fields = ["0"] * 54
        fields[1], fields[2], fields[3], fields[4], fields[30] = "测试", "000002", "12", "10", "20260922150000"
        payload = 'v_sh600001="";v_sz000002="' + "~".join(fields) + '";'
        with patch.object(stock_api.session, "get", return_value=response(payload)):
            quotes = stock_api.get_realtime_batch(["sh600001", "sz000002"])
        self.assertEqual(set(quotes), {"sz000002"})
        self.assertEqual(quotes["sz000002"]["code"], "sz000002")

    def test_us_quote_time_is_normalized_and_raw_value_is_preserved(self):
        fields = ["0"] * 54
        fields[1], fields[2], fields[3], fields[4], fields[30] = "Test", "TEST.OQ", "12", "10", "2026-09-22 16:00:00"
        raw = "~".join(fields)
        with patch.object(stock_api.session, "get", return_value=response('v_usTEST="'+raw+'";')):
            batch = stock_api.get_quote_batches(["usTEST"])["usTEST"]
        self.assertEqual(batch.rows[0]["time"], "20260922160000")
        self.assertEqual(batch.raw, raw)

    def test_quote_numeric_fields_are_floats(self):
        # 腾讯响应全是字符串；契约数值字段必须转 float，否则前端 .toFixed 抛
        # TypeError（v1.2.8/1.2.9 的「连接失败」即 high/low 漏转导致）
        fields = ["0"] * 54
        fields[1], fields[2] = "测试", "sh600001"
        fields[3], fields[4], fields[5] = "12.5", "10", "10.2"      # 价/昨收/开
        fields[30] = "20260922150000"
        fields[31], fields[32] = "2.5", "25"                        # 涨跌/涨跌%
        fields[33], fields[34] = "13", "9.8"                        # 最高/最低
        fields[36], fields[37] = "12345", "678900"                  # 量(手)/额(万)
        fields[39], fields[45], fields[46], fields[49] = "20", "100", "2", "1.2"
        with patch.object(stock_api.session, "get",
                          return_value=response('v_sh600001="' + "~".join(fields) + '";')):
            quote = stock_api.get_realtime("sh600001")
        for key in ("price", "prev_close", "open", "change", "change_pct",
                    "high", "low", "volume", "amount", "pe_ttm",
                    "market_cap", "pb", "liang_ratio"):
            self.assertIsInstance(quote[key], float, f"{key} 应为 float，实为 {type(quote[key])}")
        self.assertAlmostEqual(quote["amount"], 67.89)


if __name__ == "__main__":
    unittest.main()
