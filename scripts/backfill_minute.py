# -*- coding: utf-8 -*-
"""分时救援回补：用腾讯 day/query 端点补最近5个交易日内缺失的当日分时。

应用某天没运行时，该日分时在腾讯免费通道只保留最近5个交易日——本脚本就是
这个救援窗口的执行器（更早的日期只能用 Wind 经 MCP 零星救援，见
docs/MCP数据目录.md §9.5）。幂等：库内已有该日分时则跳过。

用法（项目根目录）：
  python scripts/backfill_minute.py
  python scripts/backfill_minute.py --db "%LOCALAPPDATA%/StockWidget/data/market.sqlite3"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import STOCKS                                # noqa: E402
from core import stock_api                              # noqa: E402
from core.history.settings import current_config        # noqa: E402
from core.history.store import HistoryStore             # noqa: E402
from core.runtime_paths import user_data_path           # noqa: E402


def has_minute(store, code, day):
    with store.connection() as conn:
        return conn.execute("SELECT 1 FROM market_point WHERE code=? AND kind='minute'"
                            " AND trade_date=? LIMIT 1", (code, day)).fetchone() is not None


def main():
    parser = argparse.ArgumentParser(description="补最近5个交易日内缺失的分时（腾讯直连、幂等）")
    parser.add_argument("--db", type=Path, default=user_data_path("data", "market.sqlite3"))
    args = parser.parse_args()

    store = HistoryStore(args.db)
    config = current_config()
    saved = skipped = 0
    for stock in STOCKS:
        code = stock["code"]
        for batch in stock_api.get_minute_history_batches(code):
            day = batch.rows[0]["date"]
            if has_minute(store, code, day):
                skipped += 1
                continue
            identity = store.save_batch(batch, config)
            saved += 1
            print(f"{code} {day}: 补 {len(batch.rows)} 点（版本 {identity[:8]}）")
    print(f"完成：补 {saved} 日，已有跳过 {skipped} 日（救援窗口=最近5个交易日）")


if __name__ == "__main__":
    main()
