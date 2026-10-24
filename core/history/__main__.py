"""不启动窗口、不联网的历史库维护命令：python -m core.history --help。"""
import argparse
import json
from pathlib import Path

from core.runtime_paths import user_data_path
from .legacy import import_directories
from .store import HistoryStore, TABLES


def main():
    parser = argparse.ArgumentParser(description="股票历史数据库备份、迁移与旧快照导入（不联网）")
    parser.add_argument("--db", type=Path, default=user_data_path("data", "market.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info")
    for name in ("backup", "export", "restore", "import-snapshots"):
        child = sub.add_parser(name)
        child.add_argument("path", type=Path)
    args = parser.parse_args()
    store = HistoryStore(args.db)
    if args.command == "info":
        with store.connection() as conn:
            counts = {table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES}
        print(json.dumps({"database": str(store.path.resolve()), "tables": counts,
                          "dates": store.dates()}, ensure_ascii=False, indent=2))
    elif args.command == "backup":
        store.backup(args.path)
    elif args.command == "export":
        store.export_jsonl(args.path)
    elif args.command == "restore":
        store.import_jsonl(args.path)
    elif args.command == "import-snapshots":
        import_directories(store, [args.path])


if __name__ == "__main__":
    main()
