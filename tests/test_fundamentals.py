"""fundamental 表（schema v2 追加）与基本面契约测试。仅临时目录，不联网。

该表由维护脚本直插，store.py 不感知；测试直接走 SQL 验证迁移、幂等与读取约定。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.history.store import HistoryStore, encode
from core.data_define.fundamental import FundamentalRecord


def digest(value):
    import hashlib
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def insert(store, record):
    """与 docs/数据库设计.md 记录的维护脚本同一写法：内容哈希主键 + OR IGNORE。"""
    row = FundamentalRecord.from_dict(record).to_dict()
    identity = digest(["fundamental", row])
    with store.connection() as conn:
        market = "US" if row["code"].startswith("us") else "CN"
        conn.execute("INSERT OR IGNORE INTO instrument VALUES (?,?,?,?)",
                     (row["code"], market, "USD" if market == "US" else "CNY",
                      "America/New_York" if market == "US" else "Asia/Shanghai"))
        conn.execute("INSERT OR IGNORE INTO fundamental VALUES (?,?,?,?,?)",
                     (identity, row["code"], row["as_of"], row.get("report_period"), encode(row)))
    return identity


def sample(code="sh600001", as_of="2026-10-23", profit=1.0):
    return {"code": code, "name": "测试甲", "as_of": as_of, "report_period": "2026-06-30",
            "annual_net_profit": profit * 1e8, "net_profit_ttm": profit * 1.2e8,
            "total_shares": 1e8, "source": "test"}


class FundamentalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = HistoryStore(Path(self.tmp.name) / "market.sqlite3")

    def test_table_created_on_fresh_and_upgraded_databases(self):
        with self.store.connection() as conn:
            self.assertEqual(conn.execute(
                "SELECT version FROM schema_migration WHERE version=2").fetchone()[0], 2)
        # 模拟旧库：删掉 v2 痕迹后重开，迁移应补建 fundamental 且不影响既有行情表
        with self.store.connection() as conn:
            conn.execute("DROP TABLE fundamental")
            conn.execute("DELETE FROM schema_migration WHERE version=2")
        reopened = HistoryStore(self.store.path)
        with reopened.connection() as conn:
            self.assertIsNotNone(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name='fundamental'").fetchone())

    def test_insert_is_idempotent_and_revision_keeps_history(self):
        first = insert(self.store, sample())
        again = insert(self.store, sample())
        self.assertEqual(first, again)
        with self.store.connection() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM fundamental").fetchone()[0], 1)
        newer = insert(self.store, sample(as_of="2026-11-20", profit=2.0))
        self.assertNotEqual(first, newer)
        with self.store.connection() as conn:
            rows = conn.execute("SELECT as_of, payload FROM fundamental WHERE code=?"
                                " ORDER BY as_of DESC, id DESC", ("sh600001",)).fetchall()
        self.assertEqual([r[0] for r in rows], ["2026-11-20", "2026-10-23"])  # 最新在前，旧行保留
        import json
        self.assertEqual(json.loads(rows[0][1])["annual_net_profit"], 2.0e8)

    def test_foreign_key_rejects_unknown_instrument(self):
        row = {"code": "sh999999", "as_of": "2026-10-23"}
        identity = digest(["fundamental", FundamentalRecord.from_dict(row).to_dict()])
        with self.store.connection() as conn:
            with self.assertRaises(Exception):
                conn.execute("INSERT INTO fundamental VALUES (?,?,?,?,?)",
                             (identity, "sh999999", "2026-10-23", None, encode(row)))

    def test_contract_roundtrip_and_tolerance(self):
        record = FundamentalRecord.from_dict(sample())
        self.assertEqual(record.to_dict()["code"], "sh600001")
        partial = FundamentalRecord.from_dict({"code": "sh600001"})
        self.assertIsNone(partial.net_profit_ttm)
        self.assertIsNone(getattr(partial, "unknown_field", None) if hasattr(partial, "unknown_field") else None)
        dropped = FundamentalRecord.from_dict({**sample(), "future_field": 1})
        self.assertNotIn("future_field", dropped.to_dict())


if __name__ == "__main__":
    unittest.main()
