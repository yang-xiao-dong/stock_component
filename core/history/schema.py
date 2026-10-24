"""仅存储层使用的版本化 SQL；发布后不得修改已发布迁移，追加新版本。"""

MIGRATIONS = [(1, (
    """CREATE TABLE instrument (
        code TEXT PRIMARY KEY, market TEXT NOT NULL, currency TEXT NOT NULL,
        timezone TEXT NOT NULL)""",
    """CREATE TABLE profile (
        id TEXT PRIMARY KEY, payload TEXT NOT NULL)""",
    """CREATE TABLE dataset (
        id TEXT PRIMARY KEY, code TEXT NOT NULL REFERENCES instrument(code),
        kind TEXT NOT NULL CHECK(kind IN ('quote','minute','kline','close')),
        source TEXT NOT NULL, adjustment TEXT NOT NULL,
        start_date TEXT NOT NULL, end_date TEXT NOT NULL,
        row_count INTEGER NOT NULL, requested_count INTEGER, raw TEXT,
        contract_version INTEGER NOT NULL)""",
    """CREATE TABLE market_point (
        id TEXT PRIMARY KEY, code TEXT NOT NULL REFERENCES instrument(code),
        kind TEXT NOT NULL, trade_date TEXT NOT NULL, event_time TEXT NOT NULL,
        payload TEXT NOT NULL)""",
    """CREATE TABLE dataset_point (
        dataset_id TEXT NOT NULL REFERENCES dataset(id),
        ordinal INTEGER NOT NULL, point_id TEXT NOT NULL REFERENCES market_point(id),
        PRIMARY KEY(dataset_id, ordinal))""",
    """CREATE TABLE ingestion (
        id INTEGER PRIMARY KEY, code TEXT NOT NULL, kind TEXT NOT NULL,
        received_at TEXT NOT NULL, dataset_id TEXT REFERENCES dataset(id),
        profile_id TEXT NOT NULL REFERENCES profile(id), error TEXT)""",
    """CREATE TABLE replay (
        id TEXT PRIMARY KEY, trade_date TEXT NOT NULL, saved_at TEXT NOT NULL,
        profile_id TEXT NOT NULL REFERENCES profile(id), missing TEXT NOT NULL,
        origin TEXT NOT NULL)""",
    """CREATE TABLE replay_dataset (
        replay_id TEXT NOT NULL REFERENCES replay(id), stream TEXT NOT NULL,
        dataset_id TEXT NOT NULL REFERENCES dataset(id), PRIMARY KEY(replay_id, stream))""",
    """CREATE TABLE imported_file (
        digest TEXT PRIMARY KEY, path TEXT NOT NULL, imported_at TEXT NOT NULL,
        replay_id TEXT NOT NULL REFERENCES replay(id))""",
    "CREATE INDEX dataset_stream_date ON dataset(code, kind, end_date)",
    "CREATE INDEX point_history ON market_point(code, kind, trade_date, event_time)",
    "CREATE INDEX ingestion_stream ON ingestion(code, kind, id)",
    "CREATE INDEX replay_date ON replay(trade_date, saved_at)",
)), (2, (
    # 外部核验的基本面参考数据（慢变、按截面日修订留痕），不参与行情采集与回放；
    # 由维护脚本直插（见 docs/数据库设计.md），store.py 暂不感知本表
    """CREATE TABLE fundamental (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL REFERENCES instrument(code),
        as_of TEXT NOT NULL, report_period TEXT,
        payload TEXT NOT NULL)""",
    "CREATE INDEX fundamental_stream ON fundamental(code, as_of)",
))]


def migrate(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migration (version INTEGER PRIMARY KEY)")
    versions = {row[0] for row in connection.execute("SELECT version FROM schema_migration")}
    if versions - {v for v, _ in MIGRATIONS}:
        raise RuntimeError("数据库版本高于当前程序，请升级程序；禁止降级写入")
    for version, statements in MIGRATIONS:
        if version in versions:
            continue
        connection.execute("BEGIN IMMEDIATE")
        try:
            for statement in statements:
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migration VALUES (?)", (version,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
