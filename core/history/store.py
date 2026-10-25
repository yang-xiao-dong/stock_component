"""SQLite 仓储：内容去重、不可变数据版本、事务与可迁移导出。无网络/组件依赖。"""
import hashlib
import json
import math
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from core.data_define.history import MarketBatch, ReplayContext
from core.data_define import KlineBar, MinutePoint, RealtimeQuote
from core.data_define.history import ClosePoint
from .schema import migrate, MIGRATIONS

CONTRACTS = {"quote": RealtimeQuote, "minute": MinutePoint,
             "kline": KlineBar, "close": ClosePoint}
TABLES = ("instrument", "profile", "dataset", "market_point", "dataset_point",
          "ingestion", "replay", "replay_dataset", "imported_file")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def valid_date(value):
    return datetime.strptime(str(value), "%Y-%m-%d").date().isoformat()


def quote_date(quote):
    value = str(quote.get("time"))
    if len(value) != 14 or not value.isdigit():
        raise ValueError("行情时间必须为市场本地 yyyyMMddHHmmss")
    return datetime.strptime(value, "%Y%m%d%H%M%S").date().isoformat()


def normalized_rows(batch):
    """只接受可定位到交易日的有限数值；失败整批拒绝，不发布半个序列。"""
    if batch.kind not in CONTRACTS or not batch.code or not batch.rows:
        raise ValueError("空行情或未知数据类型")
    if batch.adjustment not in ("none", "qfq", "unknown"):
        raise ValueError("未知复权口径")
    rows = []
    seen = set()
    for value in batch.rows:
        if not isinstance(value, dict) or not value:
            raise ValueError("无效行情数据点")
        row = CONTRACTS[batch.kind].from_dict(value).to_dict()
        if batch.kind == "quote":
            row["code"] = batch.code
            day, moment = quote_date(row), str(row["time"])
            required = ("price", "prev_close")
        else:
            day = row["date"] = valid_date(row.get("date"))
            moment = ""
            required = ("open", "close", "high", "low") if batch.kind == "kline" else ("close",)
            if batch.kind == "minute":
                raw_time = str(row["time"]).replace(":", "")
                moment = datetime.strptime(raw_time, "%H%M").strftime("%H:%M")
                row["time"] = moment
                required = ("price",)
        for key, val in row.items():
            if isinstance(val, (int, float)) and not math.isfinite(val):
                raise ValueError(f"非法数值 {key}")
        if any(not isinstance(row.get(key), (int, float)) or row[key] <= 0 for key in required):
            raise ValueError("价格字段不完整或无效")
        if batch.kind == "kline" and not (row["low"] <= min(row["open"], row["close"])
                                          <= max(row["open"], row["close"]) <= row["high"]):
            raise ValueError("日K高低价不一致")
        if (day, moment) in seen:
            raise ValueError("序列包含重复时点")
        seen.add((day, moment))
        rows.append((day, moment, row))
    return sorted(rows, key=lambda item: item[:2])


class HistoryStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            migrate(conn)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _profile(conn, config):
        identity = digest(config)
        conn.execute("INSERT OR IGNORE INTO profile VALUES (?,?)", (identity, encode(config)))
        return identity

    def save_batch(self, batch: MarketBatch, config, received_at=None):
        rows = normalized_rows(batch)
        identity = digest([batch.code, batch.kind, batch.source, batch.adjustment,
                           [row for _, _, row in rows], batch.raw, batch.requested_count])
        market = "US" if batch.code.startswith("us") else "HK" if batch.code.startswith("hk") else "CN"
        currency, zone = {"CN": ("CNY", "Asia/Shanghai"), "HK": ("HKD", "Asia/Hong_Kong"),
                          "US": ("USD", "America/New_York")}[market]
        with self._write_lock, self.connection() as conn:
            conn.execute("INSERT OR IGNORE INTO instrument VALUES (?,?,?,?)",
                         (batch.code, market, currency, zone))
            profile_id = self._profile(conn, config)
            exists = conn.execute("SELECT 1 FROM dataset WHERE id=?", (identity,)).fetchone()
            if not exists:
                conn.execute("INSERT INTO dataset VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                             (identity, batch.code, batch.kind, batch.source, batch.adjustment,
                              rows[0][0], rows[-1][0], len(rows), batch.requested_count, encode(batch.raw), 1))
                for ordinal, (day, moment, row) in enumerate(rows):
                    point_id = digest([batch.code, batch.kind, row])
                    conn.execute("INSERT OR IGNORE INTO market_point VALUES (?,?,?,?,?,?)",
                                 (point_id, batch.code, batch.kind, day, moment, encode(row)))
                    conn.execute("INSERT INTO dataset_point VALUES (?,?,?)", (identity, ordinal, point_id))
            conn.execute("INSERT INTO ingestion(code,kind,received_at,dataset_id,profile_id) VALUES (?,?,?,?,?)",
                         (batch.code, batch.kind, received_at or utc_now(), identity, profile_id))
        return identity

    def record_failure(self, code, kind, config, error):
        with self._write_lock, self.connection() as conn:
            profile_id = self._profile(conn, config)
            conn.execute("INSERT INTO ingestion(code,kind,received_at,profile_id,error) VALUES (?,?,?,?,?)",
                         (code, kind, utc_now(), profile_id, str(error)))

    def read(self, identity, count=None, end_date=None):
        if not identity:
            return []
        with self.connection() as conn:
            rows = conn.execute("""SELECT p.payload FROM dataset_point dp
                JOIN market_point p ON p.id=dp.point_id WHERE dp.dataset_id=?
                AND (? IS NULL OR p.trade_date<=?) ORDER BY dp.ordinal""",
                                (identity, end_date, end_date)).fetchall()
        result = [json.loads(row[0]) for row in rows]
        return result[-count:] if count is not None and count > 0 else result if count is None else []

    def info(self, identity):
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM dataset WHERE id=?", (identity,)).fetchone()
            return dict(row) if row else None

    def latest(self, code, kind, date=None):
        with self.connection() as conn:
            # quote/minute 必须属于选定交易日；历史日K/收盘优先取“窗口跨越该日”的
            # 版本中起点最早者（该日之前深度最大，读取时按该日裁剪、绝不读未来行），
            # 否则取 end 离该日最近的版本。不按入库时间挑：深度回补会让最小/最旧的
            # 窗口成为“最新入库”；也不按 end 挑：浅起点的长窗口会挤掉深起点版本。
            if date:
                if kind in ("quote", "minute"):
                    row = conn.execute("""SELECT d.id FROM ingestion i JOIN dataset d ON d.id=i.dataset_id
                        WHERE i.code=? AND i.kind=? AND d.end_date=?
                        ORDER BY i.received_at DESC,i.id DESC LIMIT 1""", (code, kind, date)).fetchone()
                else:
                    row = conn.execute("""SELECT d.id FROM ingestion i JOIN dataset d ON d.id=i.dataset_id
                        WHERE i.code=? AND i.kind=? AND d.start_date<=? AND d.end_date>=?
                        ORDER BY d.start_date ASC, d.row_count DESC, i.received_at DESC, d.id DESC
                        LIMIT 1""", (code, kind, date, date)).fetchone()
                    if not row:
                        row = conn.execute("""SELECT d.id FROM ingestion i JOIN dataset d ON d.id=i.dataset_id
                            WHERE i.code=? AND i.kind=? AND d.end_date<=?
                            ORDER BY d.end_date DESC, d.row_count DESC, i.received_at DESC, i.id DESC
                            LIMIT 1""", (code, kind, date)).fetchone()
            else:
                row = conn.execute("""SELECT d.id FROM ingestion i JOIN dataset d ON d.id=i.dataset_id
                    WHERE i.code=? AND i.kind=?
                    ORDER BY i.received_at DESC,i.id DESC LIMIT 1""", (code, kind)).fetchone()
            return row[0] if row else None

    def dates(self):
        # 离线可选日期只列 A 股有数据的交易日；美股参照数据不单独构成可回放日
        # （A 股休市、仅美股开市的日子选了必然全缺失）。
        with self.connection() as conn:
            return [row[0] for row in conn.execute("""SELECT trade_date FROM replay UNION
                SELECT DISTINCT trade_date FROM market_point
                WHERE code LIKE 'sh%' OR code LIKE 'sz%'
                ORDER BY trade_date""")]

    def save_replay(self, context: ReplayContext):
        valid_date(context.date)
        identity = digest([context.date, context.datasets, context.config, context.missing, context.origin])
        with self._write_lock, self.connection() as conn:
            profile_id = self._profile(conn, context.config)
            conn.execute("INSERT OR IGNORE INTO replay VALUES (?,?,?,?,?,?)",
                         (identity, context.date, context.saved_at or utc_now(), profile_id,
                          encode(context.missing), context.origin))
            for stream, dataset_id in context.datasets.items():
                conn.execute("INSERT OR IGNORE INTO replay_dataset VALUES (?,?,?)", (identity, stream, dataset_id))
        return identity

    def replay(self, date):
        with self.connection() as conn:
            row = conn.execute("""SELECT r.*,p.payload FROM replay r JOIN profile p ON p.id=r.profile_id
                WHERE trade_date=? ORDER BY CASE WHEN missing='[]' THEN 0 ELSE 1 END,
                saved_at DESC,id DESC LIMIT 1""", (date,)).fetchone()
            if not row:
                return None
            refs = {r[0]: r[1] for r in conn.execute(
                "SELECT stream,dataset_id FROM replay_dataset WHERE replay_id=?", (row["id"],))}
            return ReplayContext(date=date, saved_at=row["saved_at"], datasets=refs,
                                 config=json.loads(row["payload"]), missing=json.loads(row["missing"]),
                                 origin=row["origin"])

    def profile_at(self, date):
        with self.connection() as conn:
            row = conn.execute("""SELECT p.payload FROM ingestion i JOIN profile p ON p.id=i.profile_id
                JOIN dataset d ON d.id=i.dataset_id WHERE d.end_date<=?
                ORDER BY i.received_at DESC,i.id DESC LIMIT 1""", (date,)).fetchone()
            return json.loads(row[0]) if row else {}

    def has_import(self, file_digest):
        with self.connection() as conn:
            return conn.execute("SELECT 1 FROM imported_file WHERE digest=?", (file_digest,)).fetchone() is not None

    def mark_import(self, file_digest, path, replay_id):
        with self.connection() as conn:
            conn.execute("INSERT OR IGNORE INTO imported_file VALUES (?,?,?,?)",
                         (file_digest, str(path), utc_now(), replay_id))

    def backup(self, target):
        target = Path(target)
        with target.open("xb"):
            pass
        with self.connection() as source:
            destination = sqlite3.connect(str(target))
            try:
                source.backup(destination)
            finally:
                destination.close()

    def export_jsonl(self, target):
        """事务快照导出，使用普通 JSON 值与显式表名，便于迁移其他数据库。"""
        with Path(target).open("x", encoding="utf-8") as output, self.connection() as conn:
            conn.execute("BEGIN")
            output.write(encode({"format": "stock-widget-history", "version": 1,
                                 "schema_version": MIGRATIONS[-1][0]}) + "\n")
            for table in TABLES:
                for row in conn.execute(f"SELECT * FROM {table}"):
                    output.write(encode({"table": table, "row": dict(row)}) + "\n")

    def import_jsonl(self, source):
        """只恢复到空库；失败整笔回滚，版本/表名/外键均校验。"""
        with Path(source).open(encoding="utf-8") as stream, self._write_lock, self.connection() as conn:
            header = json.loads(next(stream))
            if header != {"format": "stock-widget-history", "version": 1, "schema_version": MIGRATIONS[-1][0]}:
                raise ValueError("不支持的历史库导出版本")
            if any(conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in TABLES):
                raise ValueError("仅允许恢复到空数据库")
            conn.execute("BEGIN IMMEDIATE")
            for line in stream:
                item = json.loads(line)
                table, row = item["table"], item["row"]
                if table not in TABLES:
                    raise ValueError("未知表")
                columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
                if set(row) != set(columns):
                    raise ValueError(f"字段不匹配: {table}")
                conn.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                             [row[c] for c in columns])
            if conn.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("外键校验失败")
