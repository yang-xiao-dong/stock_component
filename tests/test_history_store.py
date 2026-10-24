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
