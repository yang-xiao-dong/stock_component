"""旧 JSON 快照一次性、可重复导入；不改动或删除原文件。"""
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core.data_define.history import MarketBatch, ReplayContext
from .store import utc_now, valid_date

logger = logging.getLogger(__name__)


def import_snapshot(store, path):
    path = Path(path)
    raw_bytes = path.read_bytes()
    file_digest = hashlib.sha256(raw_bytes).hexdigest()
    data = json.loads(raw_bytes.decode("utf-8-sig"))
    day = valid_date(data["date"])
    if store.has_import(file_digest):
        return day
    saved = data.get("saved_at")
    timestamp = (datetime.fromisoformat(saved).replace(tzinfo=timezone(timedelta(hours=8)))
                 .astimezone(timezone.utc).isoformat(timespec="microseconds")) if saved else utc_now()
    refs, missing = {}, ["旧快照没有历史配置，计算采用当前配置；复权口径未知", "旧快照未保存独立PE收盘序列"]
    for kind, field in (("quote", "realtime"), ("minute", "minute"), ("kline", "kline")):
        for code, value in (data.get(field) or {}).items():
            if not value:
                missing.append(f"{kind}:{code}")
                continue
            rows = [dict(value)] if kind == "quote" else [dict(row) for row in value]
            if kind == "minute":
                for row in rows:
                    row["date"] = row.get("date") or day
            try:
                batch = MarketBatch(code=code, kind=kind, source="legacy_snapshot",
                                    adjustment="unknown" if kind == "kline" else "none", rows=rows, raw=value)
                refs[f"{kind}:{code}"] = store.save_batch(batch, {}, timestamp)
            except (ValueError, TypeError, KeyError):
                missing.append(f"无效旧数据 {kind}:{code}")
    if not refs:
        raise ValueError("快照无有效数据")
    context = ReplayContext(date=day, saved_at=timestamp, datasets=refs, missing=missing, origin="legacy")
    replay_id = store.save_replay(context)
    store.mark_import(file_digest, path.resolve(), replay_id)
    return day


def import_directories(store, directories):
    for directory in dict.fromkeys(Path(p) for p in directories):
        for path in sorted(directory.glob("*.json")):
            try:
                import_snapshot(store, path)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                logger.warning("旧快照导入失败 %s: %s", path, exc)
