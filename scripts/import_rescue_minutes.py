# -*- coding: utf-8 -*-
"""把手工救援落盘的历史分时 JSON 导入历史库（幂等，可重复执行）。

数据来源是 Wind 分钟级行情经人工转写的 docs/mcp/minute_*.json
（以及更早的 docs/minute_rescue_*.json），rows = [HH:MM, 成交价, 该分钟成交量(股)]。
库内 minute.vol 统一为「手」（累计），本脚本负责 股→手 折算与累计；
以新数据集版本表达，不改动旧版本。用法：

    python scripts/import_rescue_minutes.py [--db 路径] [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.data_define.history import MarketBatch          # noqa: E402
from core.history.settings import current_config           # noqa: E402
from core.history.store import HistoryStore                # noqa: E402
from core.runtime_paths import user_data_path              # noqa: E402

DEFAULT_TARGETS = [
    Path("docs/mcp"),
    Path("docs"),
]
DEFAULT_DB = user_data_path("data", "market.sqlite3")


def build_batch(doc):
    rows, cumulative = [], 0.0
    for hhmm, price, vol in doc["rows"]:
        cumulative += float(vol)
        rows.append({"date": doc["date"], "time": hhmm, "price": float(price),
                     "vol": round(cumulative / 100, 2)})
    return MarketBatch(code=doc["code"], kind="minute", source="rescue_wind",
                       adjustment="none", rows=rows, raw=doc, requested_count=None)


def main():
    parser = argparse.ArgumentParser(description="导入救援分时 JSON 到历史库（vol 折算为手）")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true", help="只校验不入库")
    args = parser.parse_args()

    documents = []
    for directory in DEFAULT_TARGETS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("minute_*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if {"code", "date", "rows"} <= set(doc):
                documents.append((path, doc))
    if not documents:
        print("未发现救援分时 JSON")
        return

    config = current_config()
    store = None if args.dry_run else HistoryStore(args.db)
    for path, doc in documents:
        batch = build_batch(doc)
        total = sum(r[2] for r in doc["rows"])
        note = f"{doc['code']} {doc['date']}: {len(batch.rows)}分钟 " \
               f"总量{total:,.0f}股(={total/100:,.0f}手) 末价{doc['rows'][-1][1]}"
        if args.dry_run:
            print("[dry-run]", note)
            continue
        store.save_batch(batch, config)
        print("已入库", note, f"← {path.name}")
    if store:
        print(f"目标库: {store.path}")


if __name__ == "__main__":
    main()
