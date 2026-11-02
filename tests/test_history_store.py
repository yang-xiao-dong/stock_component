"""持久化、去重、数据修订、迁移与事务测试。仅临时目录，不联网。"""
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.history.store import HistoryStore, TABLES
from core.history.legacy import import_snapshot
from core.data_define.history import ReplayContext
from history_fixtures import Provider, settings


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = HistoryStore(self.root / "market.sqlite3")
        self.provider = Provider()
        self.config = settings()

    def counts(self, store=None):
        with (store or self.store).connection() as conn:
            return {table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES}

    def test_duplicate_fetches_reuse_content_and_survive_restart(self):
        batch = self.provider.get_kline_batch("sh600001", 5)
        first = self.store.save_batch(batch, self.config)
        second = self.store.save_batch(batch, self.config)
        self.assertEqual(first, second)
        self.assertEqual(self.counts()["dataset"], 1)
        self.assertEqual(self.counts()["market_point"], 5)
        self.assertEqual(self.counts()["ingestion"], 2)
        reopened = HistoryStore(self.store.path)
        self.assertEqual(reopened.read(first), batch.rows)

    def test_correction_preserves_original_and_deduplicates_unchanged_points(self):
        batch = self.provider.get_minute_batch("sh600001")
        original = self.store.save_batch(batch, self.config)
        batch.rows[-1]["price"] = 13
        corrected = self.store.save_batch(batch, self.config)
        self.assertNotEqual(original, corrected)
        self.assertEqual(self.store.read(original)[-1]["price"], 12)
        self.assertEqual(self.store.read(corrected)[-1]["price"], 13)
        self.assertEqual(self.counts()["market_point"], 3)

    def test_adjustment_versions_are_distinct_and_never_spliced(self):
        batch = self.provider.get_kline_batch("sh600001", 5)
        first = self.store.save_batch(batch, self.config)
        batch.adjustment = "none"
        second = self.store.save_batch(batch, self.config)
        self.assertNotEqual(first, second)
        self.assertEqual(self.store.info(first)["adjustment"], "qfq")
        self.assertEqual(len(self.store.read(first, 3)), 3)
        self.assertEqual(len(self.store.read(second, end_date="2026-09-20")), 3)

    def test_invalid_batch_is_not_partially_committed(self):
        batch = self.provider.get_kline_batch("sh600001", 5)
        batch.rows[-1]["close"] = float("nan")
        with self.assertRaises(ValueError):
            self.store.save_batch(batch, self.config)
        self.assertTrue(all(value == 0 for value in self.counts().values()))

    def test_concurrent_writes_and_reads(self):
        def save(number):
            batch = self.provider.get_kline_batch(f"sh{number:06d}", 5)
            identity = self.store.save_batch(batch, self.config)
            return self.store.read(identity)
        with ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(save, range(12)))
        self.assertTrue(all(len(value) == 5 for value in values))
        self.assertEqual(self.counts()["dataset"], 12)

    def test_reconstruction_prefers_spanning_widest_window_over_latest_ingested(self):
        # 深度回补会让“最小/最旧”的窗口成为最新入库；带日期的历史版本选择必须
        # 优先取窗口跨越该日且行数最多的版本，读取时按该日裁剪出满窗。
        code = "sh600001"
        wide = self.store.save_batch(self.provider.get_kline_batch(code, 60), self.config)
        deep = self.store.save_batch(Provider(day="2020-01-10").get_kline_batch(code, 3),
                                     self.config)  # 更晚入库，但窗口古老且只有3根
        picked = self.store.latest(code, "kline", date="2026-08-15")
        self.assertEqual(picked, wide)
        rows = self.store.read(picked, count=60, end_date="2026-08-15")
        self.assertEqual(rows[-1]["date"], "2026-08-15")  # 恰好裁到所选日，不读未来行
        self.assertEqual(len(rows), 22)  # 夹具按日历日生成：窗口 07-25~09-22 截到 08-15 共 22 根
        # 无窗口跨越该日时回退到 end 离该日最近的版本
        self.assertEqual(self.store.latest(code, "kline", date="2021-06-01"), deep)

    def test_spanning_tie_prefers_more_rows(self):
        code = "sh600001"
        wide = self.store.save_batch(self.provider.get_kline_batch(code, 60), self.config)
        narrow = self.store.save_batch(self.provider.get_kline_batch(code, 10), self.config)  # 同终点更晚入库
        self.assertEqual(self.store.latest(code, "kline", date="2026-09-10"), wide)

    def test_spanning_prefers_earliest_start_over_latest_end(self):
        # 跨越该日的版本中，起点最早（该日前深度最大）者优先——
        # 浅起点的窗口虽然 end 更新，也不能挤掉深起点版本
        code = "sh600001"
        deep = self.store.save_batch(Provider(day="2026-09-20").get_kline_batch(code, 40), self.config)
        shallow = self.store.save_batch(Provider(day="2026-09-22").get_kline_batch(code, 15), self.config)
        picked = self.store.latest(code, "kline", date="2026-09-15")
        self.assertEqual(picked, deep)
        self.assertGreater(self.store.info(shallow)["end_date"], self.store.info(deep)["end_date"])

    def test_dates_exclude_foreign_only_days(self):
        # 离线可选日期只列 A 股有数据的交易日；仅港美股有数据的日子不出现在清单
        self.store.save_batch(self.provider.get_kline_batch("sh600001", 3), self.config)
        self.store.save_batch(Provider(day="2026-09-25").get_kline_batch("hk000001", 2), self.config)
        dates = self.store.dates()
        self.assertEqual(dates, ["2026-09-20", "2026-09-21", "2026-09-22"])

    def test_minute_day_totals_recent_days_only(self):
        # 量比兜底查询：严格早于给定日的近 N 个交易日全天累计量，倒序；
        # 同日多版本（当日采集与历史批次）取最大累计值，给定日自身不计入
        code = "sh600001"
        self.store.save_batch(self.provider.get_minute_batch(code), self.config)  # 09-22，不应计入
        self.store.save_batch(Provider(day="2026-09-21").get_minute_batch(code), self.config)
        bigger = Provider(day="2026-09-21").get_minute_batch(code)
        bigger.rows[-1]["vol"] = 12
        self.store.save_batch(bigger, self.config)
        self.store.save_batch(Provider(day="2026-09-18").get_minute_batch(code), self.config)
        self.assertEqual(self.store.minute_day_totals(code, "2026-09-22", days=2), [12.0, 10.0])
        self.assertEqual(self.store.minute_day_totals(code, "2026-09-23", days=5), [10.0, 12.0, 10.0])
        self.assertEqual(self.store.minute_day_totals("sh600002", "2026-09-22"), [])

    def test_backup_export_restore_preserve_replay_and_refuse_overwrite(self):
        identity = self.store.save_batch(self.provider.get_kline_batch("sh600001", 5), self.config)
        replay = ReplayContext(date="2026-09-22", config=self.config, datasets={"kline:sh600001": identity})
        self.store.save_replay(replay)
        exported = self.root / "history.jsonl"
        self.store.export_jsonl(exported)
        restored = HistoryStore(self.root / "restored.sqlite3")
        restored.import_jsonl(exported)
        self.assertEqual(self.counts(), self.counts(restored))
        self.assertEqual(self.store.replay(replay.date), restored.replay(replay.date))
        self.assertEqual(self.store.read(identity), restored.read(identity))
        with self.assertRaises(ValueError):
            restored.import_jsonl(exported)
        target = self.root / "backup.sqlite3"
        self.store.backup(target)
        self.assertEqual(self.counts(), self.counts(HistoryStore(target)))
        with self.assertRaises(FileExistsError):
            self.store.backup(target)

    def test_restore_rolls_back_on_unknown_table(self):
        self.store.save_batch(self.provider.get_kline_batch("sh600001", 5), self.config)
        exported = self.root / "invalid.jsonl"
        self.store.export_jsonl(exported)
        with exported.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"table": "not_allowed", "row": {}})+"\n")
        target = HistoryStore(self.root / "empty.sqlite3")
        with self.assertRaises(ValueError):
            target.import_jsonl(exported)
        self.assertTrue(all(value == 0 for value in self.counts(target).values()))

    def test_newer_schema_refuses_downgrade(self):
        with self.store.connection() as conn:
            conn.execute("INSERT INTO schema_migration VALUES (999)")
        with self.assertRaises(RuntimeError):
            HistoryStore(self.store.path)

    def test_legacy_import_keeps_file_and_marks_unknown_adjustment(self):
        quote = self.provider.get_quote_batches(["sh600001"])["sh600001"].rows[0]
        quote["code"] = "600001"
        minute = self.provider.get_minute_batch("sh600001").rows
        for point in minute:
            point.pop("date")
        snapshot = {"date": "2026-09-22", "saved_at": "2026-09-22 15:05:00",
                    "realtime": {"sh600001": quote}, "minute": {"sh600001": minute},
                    "kline": {"sh600001": self.provider.get_kline_batch("sh600001", 5).rows}}
        path = self.root / "old.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        before = path.read_bytes()
        import_snapshot(self.store, path)
        counts = self.counts()
        import_snapshot(self.store, path)
        self.assertEqual(self.counts(), counts)
        self.assertEqual(before, path.read_bytes())
        replay = self.store.replay(snapshot["date"])
        self.assertNotIn("close:sh600001", replay.datasets)
        self.assertEqual(self.store.info(replay.datasets["kline:sh600001"])["adjustment"], "unknown")
        self.assertEqual(self.store.read(replay.datasets["minute:sh600001"])[0]["date"], snapshot["date"])
        self.assertEqual(self.store.read(replay.datasets["quote:sh600001"])[0]["code"], "sh600001")


if __name__ == "__main__":
    unittest.main()
