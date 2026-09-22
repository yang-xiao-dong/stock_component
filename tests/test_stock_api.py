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
        self.assertEqual(get.call_count, 2)
        self.assertNotEqual(get.call_args_list[0].args[0], get.call_args_list[1].args[0])

    def test_kline_preserves_ohlc_and_request(self):
        payload = {"code": 0, "data": {"sh603893": {"qfqday": [
            ["2026-09-22", "203.90", "217.80", "217.80", "203.90", "254013"],
        ]}}}
        with patch.object(stock_api.session, "get", return_value=response(payload)) as get:
            bars = stock_api.get_kline("sh603893", 60)
        self.assertEqual(bars, [{"date": "2026-09-22", "open": 203.9,
                                 "close": 217.8, "high": 217.8, "low": 203.9}])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"]["param"], "sh603893,day,,,60,qfq")

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
                self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
