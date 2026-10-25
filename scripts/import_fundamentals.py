# -*- coding: utf-8 -*-
"""基本面种子导入 fundamental 表（幂等，内容哈希主键，重复执行零新增）。

种子文件为 docs/fundamentals_2026-10-23.json（三源核验快照）与
docs/fundamentals_report_periods_2026-10-24.json（报告期历史）；
写法与 docs/数据库设计.md fundamental 小节、tests/test_fundamentals.py 的
insert() 一致：先 INSERT OR IGNORE instrument，再按内容哈希主键写入。

用法（项目根目录）：
  python scripts/import_fundamentals.py            # 源码运行库 data/market.sqlite3
  python scripts/import_fundamentals.py --db "%LOCALAPPDATA%/StockWidget/data/market.sqlite3"
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.data_define.fundamental import FundamentalRecord  # noqa: E402
from core.history.store import HistoryStore, encode         # noqa: E402
from core.runtime_paths import user_data_path               # noqa: E402

SNAPSHOT_SEED = Path("docs/fundamentals_2026-10-23.json")
PERIODS_SEED = Path("docs/fundamentals_report_periods_2026-10-24.json")


def build_records():
    records = [FundamentalRecord.from_dict(r).to_dict()
               for r in json.loads(SNAPSHOT_SEED.read_text(encoding="utf-8"))]
    seed = json.loads(PERIODS_SEED.read_text(encoding="utf-8"))
    for code, rows in seed["data"].items():
        for period, net_profit, roe, margin, debt, eps, yoy in rows:
            rec = {"code": code, "name": seed["names"][code], "currency": "CNY", "as_of": period,
                   "report_period": period, "report_net_profit": net_profit,
                   "report_net_profit_yoy_pct": yoy, "roe_pct": roe, "gross_margin_pct": margin,
                   "debt_ratio_pct": debt, "eps_ttm": eps,
                   "source": "同花顺iFinD报告期序列(MCP 2026-10-24导入；隐含重构+快照硬校验通过)"}
            if period.endswith("-12-31"):
                rec["annual_period"], rec["annual_net_profit"] = period, net_profit
            records.append(FundamentalRecord.from_dict(rec).to_dict())
    return records


def main():
    parser = argparse.ArgumentParser(description="导入基本面种子到 fundamental 表（不联网、幂等）")
    parser.add_argument("--db", type=Path, default=user_data_path("data", "market.sqlite3"))
    args = parser.parse_args()

    digest = lambda v: hashlib.sha256(encode(v).encode("utf-8")).hexdigest()  # noqa: E731
    store = HistoryStore(args.db)
    before = None
    with store.connection() as conn:
        before = conn.execute("SELECT count(*) FROM fundamental").fetchone()[0]
    for row in build_records():
        with store.connection() as conn:
            conn.execute("INSERT OR IGNORE INTO instrument VALUES (?,?,?,?)",
                         (row["code"], "CN", "CNY", "Asia/Shanghai"))
            conn.execute("INSERT OR IGNORE INTO fundamental VALUES (?,?,?,?,?)",
                         (digest(["fundamental", row]), row["code"], row["as_of"],
                          row.get("report_period"), encode(row)))
    with store.connection() as conn:
        after = conn.execute("SELECT count(*) FROM fundamental").fetchone()[0]
    print(f"{args.db}: fundamental {before} -> {after} 行（新增 {after - before}）")


if __name__ == "__main__":
    main()
