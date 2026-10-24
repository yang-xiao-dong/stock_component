"""在线→持久化→重启→离线逐字段一致，含真实计算层与模式隔离。"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.history.store import HistoryStore
from core.history.service import HistoryService
from core import data_source, group_calc, pe_calc
from components.group.component import GroupApi
from components.stock.component import StockApi
from components.analysis.component import AnalysisApi
from components.pe_compare.component import PeCompareApi
from history_fixtures import Provider, settings


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = HistoryStore(Path(self.tmp.name) / "market.sqlite3")
        self.provider = Provider()
        self.config = settings()
        self.service = HistoryService(self.store, self.provider, lambda: deepcopy(self.config))

    def test_latest_and_offline_identical_after_restart_including_group_and_pe(self):
        result = self.service.collect(force=True)
        self.assertTrue(result["complete"], result)
        codes = [s["code"] for s in self.config["STOCKS"]]
        quotes = self.service.quotes(codes)
        bars = {c: self.service.series("kline", c, 3) for c in codes}
        minute = {c: self.service.series("minute", c) for c in codes}
        close = self.service.series("close", "usTEST", 7)
        group = group_calc.build_group_kline(bars, self.config["PRINCIPAL"])
        pe = pe_calc.pe_history(close, 20, 12)
        self.provider.forbidden = True
        reopened = HistoryService(HistoryStore(self.store.path), self.provider, lambda: self.config)
        self.assertTrue(reopened.set_mode("offline", result["date"]))
        self.assertEqual(reopened.quotes(codes), quotes)
        self.assertEqual({c: reopened.series("minute", c) for c in codes}, minute)
        offline_bars = {c: reopened.series("kline", c, 3) for c in codes}
        self.assertEqual(offline_bars, bars)
        self.assertEqual(group_calc.build_group_kline(offline_bars, self.config["PRINCIPAL"]), group)
        self.assertEqual(pe_calc.pe_history(reopened.series("close", "usTEST", 7), 20, 12), pe)
        self.assertFalse(reopened.collect(force=True)["ok"])

    def test_old_day_stays_fixed_after_new_prices_adjustment_and_config(self):
        self.service.collect(force=True)
        original = self.service.series("kline", "sh600001", 3)
        self.provider.day, self.provider.price, self.provider.adjustment = "2026-09-23", 20, "none"
        self.config["PRINCIPAL"] = 200000
        self.service.collect(force=True)
        self.service.set_mode("offline", "2026-09-22")
        self.assertEqual(self.service.series("kline", "sh600001", 3), original)
        self.assertEqual(self.service.quotes(["sh600001"])["sh600001"]["price"], 12)
        self.assertEqual(self.service.config("PRINCIPAL", 1), 100000)

    def test_automatically_persisted_getter_data_can_be_replayed_without_manual_save(self):
        quote = self.service.quotes(["sh600001"])
        self.service.series("kline", "sh600001", 3)
        self.provider.forbidden = True
        self.assertTrue(self.service.set_mode("offline", "2026-09-22"))
        self.assertEqual(self.service.quotes(["sh600001"]), quote)
        self.assertEqual(self.service.series("minute", "sh600001"), [])
        self.assertTrue(self.service.status()["missing"])
        self.assertTrue(self.service.set_mode("offline", "2026-09-19"))
        self.assertEqual(self.service.quotes(["sh600001"]), {})
        self.assertTrue(all(b["date"] <= "2026-09-19" for b in self.service.series("kline", "sh600001", 5)))

    def test_partial_capture_does_not_replace_complete_replay(self):
        self.service.collect(force=True)
        first = self.store.replay("2026-09-22")
        self.provider.fail.add("minute:sh600001")
        result = self.service.collect(force=True)
        self.assertTrue(result["ok"])
        self.assertFalse(result["complete"])
        self.assertIn("minute:sh600001", result["missing"])
        self.assertEqual(first, self.store.replay("2026-09-22"))

    def test_shared_requests_fetch_largest_window_and_slice_consistently(self):
        short = self.service.series("kline", "sh600001", 3)
        long = self.service.series("kline", "sh600001", 5)
        self.assertEqual(short, long[-3:])
        self.assertEqual(self.provider.calls.count(("kline", "sh600001")), 1)
        self.service.quotes(["sh600001"])
        self.service.quotes(["sz000002"])
        self.assertEqual(self.provider.calls.count(("quote", "sz000002")), 1)

    def test_completed_live_request_is_discarded_after_switch(self):
        self.service.collect(force=True)
        self.service.set_mode("live")
        started, release = threading.Event(), threading.Event()
        original = self.provider.get_quote_batches
        def blocked(codes):
            started.set()
            self.assertTrue(release.wait(5))
            return original(codes)
        with patch.object(self.provider, "get_quote_batches", side_effect=blocked), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.service.quotes, ["sh600001"])
            self.assertTrue(started.wait(5))
            self.service.set_mode("offline", "2026-09-22")
            release.set()
            self.assertEqual(future.result(timeout=5), {})

    def test_components_discard_previous_day_and_use_saved_configuration(self):
        self.service.collect(force=True)
        self.provider.day, self.provider.price = "2026-09-23", 20
        self.config["PRINCIPAL"] = 200000
        self.service.collect(force=True)
        self.provider.forbidden = True
        with patch.object(data_source, "_service", self.service):
            self.service.set_mode("offline", "2026-09-23")
            group, stock, analysis, pe = GroupApi(), StockApi(), AnalysisApi(), PeCompareApi()
            group.get_group_kline()
            value = group.get_group_realtime()["total_value"]
            self.service.set_mode("offline", "2026-09-22")
            self.assertEqual(group.get_group()["principal"], 100000)
            group.get_group_kline()
            self.assertNotEqual(group.get_group_realtime()["total_value"], value)
            self.assertEqual(stock.get_realtime("sh600001")["price"], 12)
            analysis._refresh()
            pe._refresh()
            self.assertEqual(analysis.get_analysis()["date"], "2026-09-22")
            self.assertEqual(pe.get_pe_compare()["window_days"], 7)
            self.assertEqual(len(pe.get_pe_compare()["reference"]["points"]), 7)


if __name__ == "__main__":
    unittest.main()
