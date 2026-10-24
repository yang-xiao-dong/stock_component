"""历史库跨层契约。SQL 结构见 core/history/schema.py；维护说明见 docs/数据库设计.md。"""
from dataclasses import dataclass, field
from typing import List, Dict

from .common import Contract


@dataclass
class ClosePoint(Contract):
    date: str = None
    close: float = None


@dataclass
class MarketBatch(Contract):
    code: str = None
    kind: str = None             # quote / minute / kline / close
    source: str = "tencent"
    adjustment: str = "none"    # none / qfq / unknown
    rows: List[dict] = field(default_factory=list)
    raw: object = None           # 供应商返回的本股票数据，旧快照为原始快照片段
    requested_count: int = None


@dataclass
class ReplayContext(Contract):
    date: str = None
    saved_at: str = None
    datasets: Dict[str, str] = field(default_factory=dict)  # kind:code -> 内容版本 ID
    config: dict = field(default_factory=dict)
    missing: List[str] = field(default_factory=list)
    origin: str = "collected"    # collected / legacy / reconstructed


@dataclass
class HistoryStatus(Contract):
    mode: str = "live"
    date: str = None
    saved_at: str = None
    missing: List[str] = field(default_factory=list)
    message: str = None


@dataclass
class DataModePreference(Contract):
    mode: str = "live"
    date: str = None

