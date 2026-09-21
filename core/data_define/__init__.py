# -*- coding: utf-8 -*-
"""数据契约包（唯一维护处）：所有跨层数据结构的字段定义。

- quote.py    实时行情 RealtimeQuote
- kline.py    日K KlineBar
- minute.py   分时点 MinutePoint
- stock.py    股票条目 StockInfo
- group.py    组合聚合 GroupMinute / GroupKline / ContributionRow / ContributionTotal
- snapshot.py 收盘快照 MarketSnapshot（离线加载基础）+ save/load

约定：字段增改先改这里，再改生产端（stock_api/group_calc）与前端；
from_dict 容错以兼容旧快照。详见 AGENTS.md「数据契约」。
"""
from .common import Contract
from .group import ContributionRow, ContributionTotal, GroupKline, GroupMinute, StockSeries
from .kline import KlineBar
from .minute import MinutePoint
from .quote import RealtimeQuote
from .snapshot import (
    SNAPSHOT_VERSION,
    MarketSnapshot,
    load_snapshot,
    save_snapshot,
    snapshot_path,
)
from .stock import StockInfo

__all__ = [
    "Contract",
    "RealtimeQuote", "KlineBar", "MinutePoint", "StockInfo",
    "GroupMinute", "GroupKline", "StockSeries",
    "ContributionRow", "ContributionTotal",
    "MarketSnapshot", "SNAPSHOT_VERSION",
    "save_snapshot", "load_snapshot", "snapshot_path",
]
