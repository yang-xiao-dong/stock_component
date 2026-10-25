"""数据入口与收盘调度回归；数据库及旧快照均隔离在临时目录。"""
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data_source
from core.history.store import HistoryStore
from core.history.service import HistoryService
from history_fixtures import Provider, settings


class DataSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.provider = Provider()
        self.service = HistoryService(HistoryStore(Path(self.tmp.name)/"market.sqlite3"), self.provider, settings)
        patcher = patch.object(data_source, "_service", self.service)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_mode_switch_and_all_getters(self):
        self.assertFalse(data_source.set_mode("nonsense"))
        self.assertFalse(data_source.set_mode("offline", "2000-01-01"))
        result = data_source.capture_today()
        self.assertTrue(result["ok"], result)
        live = data_source.get_realtime("sh600001")
        self.provider.forbidden = True
        self.assertTrue(data_source.set_mode("offline", result["date"]))
        self.assertTrue(data_source.is_offline())
        self.assertEqual(data_source.get_realtime("sh600001"), live)
        self.assertIsNone(data_source.get_realtime("missing"))
        self.assertEqual(len(data_source.get_minute_data("sh600001")), 2)
        self.assertEqual(len(data_source.get_kline("sh600001")), 3)
        self.assertEqual(len(data_source.get_close_series("usTEST", 7)), 7)
        self.assertIn(result["date"], data_source.list_snapshots())
        self.assertFalse(data_source.capture_today()["ok"])
        self.assertTrue(data_source.set_mode("live"))
        self.assertFalse(data_source.is_offline())

    def test_prev_close_falls_back_to_close_series_in_offline(self):
        result = data_source.capture_today()
        self.assertEqual(data_source.get_prev_close("sh600001"), 10)  # 在线：行情昨收
        self.provider.forbidden = True
        # 回放采集日（有行情快照）：仍用快照昨收
        self.assertTrue(data_source.set_mode("offline", result["date"]))
        self.assertEqual(data_source.get_prev_close("sh600001"), 10)
        # 回放仅有收盘序列的更早日期（无快照，如历史救援日）：取前一交易日收盘
        self.assertTrue(data_source.set_mode("offline", "2026-09-21"))
        self.assertEqual(data_source.get_prev_close("sh600001"), 12)
        self.assertIsNone(data_source.get_prev_close("missing"))

    def test_should_auto_save_and_next_day_rearm(self):
        self.assertFalse(data_source.should_auto_save(datetime(2026,9,21,15,4)))
        self.assertTrue(data_source.should_auto_save(datetime(2026,9,21,15,5)))
        self.assertFalse(data_source.should_auto_save(datetime(2026,9,19,16)))
        now = datetime(2026,9,18,16)
        self.assertEqual(data_source._fire_time(now), now)
        self.assertEqual(data_source._fire_time(now, initial=False), datetime(2026,9,21,15,5))
        self.assertEqual(data_source._fire_time(datetime(2026,9,21,10)), datetime(2026,9,21,15,5))

    def test_auto_save_rearms_without_immediate_loop_even_on_failure(self):
        class Scheduler:
            def add_once(self, name, when, callback):
                self.when = when
        scheduler = Scheduler()
        with patch.object(data_source, "capture_today", side_effect=ValueError("failure")):
            with self.assertRaises(ValueError):
                data_source._auto_save_fired(scheduler)
        now = datetime.now(scheduler.when.tzinfo)
        self.assertGreater(scheduler.when, now)

    def test_offline_auto_save_never_calls_provider(self):
        self.service.collect(force=True)
        self.service.set_mode("offline", "2026-09-22")
        self.provider.forbidden = True
        class Scheduler:
            def add_once(self, *args):
                pass
        data_source._auto_save_fired(Scheduler())

    def test_restart_restores_offline_preference_before_any_request(self):
        self.service.collect(force=True)
        self.assertTrue(data_source.set_mode("offline", "2026-09-22"))
        with patch.object(data_source, "_service", None), \
                patch.object(data_source, "user_data_path", return_value=self.service.store.path), \
                patch.object(data_source, "import_directories"), \
                patch.object(data_source.stock_api, "get_quote_batches", side_effect=AssertionError("联网")):
            data_source.initialize()
            self.assertEqual(data_source.get_mode(), {"mode": "offline", "date": "2026-09-22"})
            self.assertEqual(data_source.get_realtime("sh600001")["price"], 12)

    def test_offline_missing_quote_restores_from_kline(self):
        from core.data_define.history import MarketBatch
        result = data_source.capture_today()
        self.assertTrue(result["ok"], result)
        rows = [
            {"date": "2026-09-23", "open": 10, "close": 11, "high": 11.5, "low": 9.8},
            {"date": "2026-09-24", "open": 11, "close": 12, "high": 12.5, "low": 10.8},
        ]
        self.service.store.save_batch(MarketBatch(
            code="sh600001", kind="kline", rows=rows, raw=rows,
            requested_count=2, adjustment="qfq"), settings())
        minute = [{"date": "2026-09-24", "time": "09:30", "price": 11, "vol": 5},
                  {"date": "2026-09-24", "time": "15:00", "price": 12, "vol": 25}]
        self.service.store.save_batch(MarketBatch(
            code="sh600001", kind="minute", rows=minute, raw=minute), settings())

        self.assertTrue(data_source.set_mode("offline", "2026-09-24"))
        quote = data_source.get_realtime("sh600001")
        self.assertIsNotNone(quote)
        self.assertEqual(quote["name"], "测试甲")
        self.assertEqual(quote["open"], 11)
        self.assertEqual(quote["price"], 12)
        self.assertEqual(quote["prev_close"], 11)
        self.assertEqual(quote["change_pct"], 9.09)
        self.assertEqual(quote["volume"], 25)   # 分时末点累计，库内口径为手
        self.assertEqual(quote["time"], "20260924150000")
        self.assertIsNone(quote["pe_ttm"])      # 估值与成交额无处还原，保持缺失
        self.assertIsNone(quote["amount"])
        # 批量接口不注入还原行情：组合/PE/分析组件的回放口径不变
        self.assertEqual(data_source.get_realtime_batch(["sh600001"]), {})
        # 当日无日K行的日期（仅有收盘价）不还原
        close = [{"date": "2026-09-25", "close": 13}]
        self.service.store.save_batch(MarketBatch(
            code="sh600001", kind="close", rows=close, raw=close), settings())
        self.assertTrue(data_source.set_mode("offline", "2026-09-25"))
        self.assertIsNone(data_source.get_realtime("sh600001"))


if __name__ == "__main__":
    unittest.main()
