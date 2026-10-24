# -*- coding: utf-8 -*-
"""行情历史回补：用项目自带腾讯适配器向前翻页拉长窗口日K/收盘序列写入历史库。

不新增网络端点；入库走 store.save_batch（内容哈希去重，重复执行幂等，中断后
重跑自动从库内最早日期续补，已完成轮次永不丢失）。历史分时/逐笔报价上游不
提供，无法回补（见 docs/数据库设计.md §5）。

用法（项目根目录）：
  python scripts/backfill_market.py                       # 从库内最早日期续补到 2015-01-01
  python scripts/backfill_market.py --until 2018-01-01    # 指定回补目标日
  python scripts/backfill_market.py --codes sh603893,sz300458
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import PE_COMPARE, STOCKS          # noqa: E402
from core import stock_api                     # noqa: E402
from core.history.settings import current_config  # noqa: E402
from core.history.store import HistoryStore    # noqa: E402
from core.runtime_paths import user_data_path  # noqa: E402

MAX_ROUNDS = 40  # 单标的单域安全上限（800根/轮 × 40 ≈ 32年）


def earliest_in_store(store, code, kind):
    with store.connection() as conn:
        row = conn.execute("SELECT MIN(trade_date) FROM market_point WHERE code=? AND kind=?",
                           (code, kind)).fetchone()
    return row[0] if row else None


def main():
    parser = argparse.ArgumentParser(description="回补日K(qfq)与收盘价历史到历史库（不启动窗口、不耗MCP配额）")
    parser.add_argument("--days", type=int, default=800, help="单轮窗口（腾讯单次上限约800根）")
    parser.add_argument("--until", default="2015-01-01", help="回补目标日 YYYY-MM-DD（更早上市的补到上市日自然停止）")
    parser.add_argument("--codes", help="逗号分隔；默认 config.STOCKS + PE 参照股")
    parser.add_argument("--db", type=Path, default=user_data_path("data", "market.sqlite3"))
    args = parser.parse_args()

    codes = args.codes.split(",") if args.codes else \
        [s["code"] for s in STOCKS] + [PE_COMPARE["reference"]["code"]]
    store = HistoryStore(args.db)
    config = current_config()
    before = len(store.dates())
    for code in codes:
        for kind, fetch in (("kline", stock_api.get_kline_batch),
                            ("close", stock_api.get_close_batch)):
            if kind == "kline" and code.startswith("us"):
                # 美股日K端点只回 2 根首尾标记（stock_api 已注明不可用）；参照股只需 close
                continue
            end = earliest_in_store(store, code, kind)  # None=从最新开始（首轮冷启动）
            if end is not None and end <= args.until:
                print(f"{code} {kind}: 已覆盖至 {end}，无需回补")
                continue
            rounds = 0
            while rounds < MAX_ROUNDS:
                try:
                    batch = fetch(code, args.days, end=end)
                except Exception as exc:  # noqa: BLE001 单轮失败不阻断其他轮次
                    print(f"{code} {kind}: 第{rounds + 1}轮请求失败 {exc}")
                    break
                if not batch or not batch.rows:
                    break
                rows = batch.rows
                earliest = rows[0]["date"]
                store.save_batch(batch, config)
                rounds += 1
                print(f"{code} {kind}: 第{rounds}轮 {len(rows)} 根 止于 {earliest} 复权={batch.adjustment}")
                if earliest <= args.until:
                    break
                if end is not None and earliest >= end:
                    break  # 已到上市初，无法再向前
                end = earliest
            print(f"{code} {kind}: 完成，库内覆盖 {earliest_in_store(store, code, kind)} 起")
    print(f"库内可回放交易日数: {before} -> {len(store.dates())}")


if __name__ == "__main__":
    main()
