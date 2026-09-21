# -*- coding: utf-8 -*-
"""组合聚合结构契约（计算逻辑见 core/group_calc.py，本文件只管字段）。

口径：¥ 为绝对度量；% 相对建仓本金。
"""
from dataclasses import dataclass
from typing import Optional

from .common import Contract
from .kline import KlineBar


@dataclass
class StockSeries(Contract):
    """个股序列线（与图中色点对应）"""
    code: str = None
    data: list = None   # [float|None, ...]


@dataclass
class GroupMinute(Contract):
    """组合分时：各股当日盈亏(¥) + 组合合计(¥)"""
    times: list = None          # ["09:30", ...]
    total: list = None          # 组合当日盈亏合计 [¥|None]
    stocks: list = None         # [StockSeries]


@dataclass
class GroupKline(Contract):
    """组合日K：市值(¥)蜡烛 + 个股持市值(¥)线 + 建仓份额"""
    principal: float = None     # 建仓本金(¥)
    dates: list = None          # ["2026-06-30", ...]
    candles: list = None        # [KlineBar] 市值¥蜡烛
    stocks: list = None         # [StockSeries] 个股持市值¥
    shares: dict = None         # {code: 建仓份额}


@dataclass
class ContributionRow(Contract):
    """个股盈亏分解行（按 day_pnl 降序）"""
    code: str = None
    name: str = None
    change_pct: Optional[float] = None   # 当日涨跌幅(%)
    day_pnl: Optional[float] = None      # 当日盈亏(¥)
    value: float = None                  # 持仓市值(¥)
    total_pnl: Optional[float] = None    # 累计盈亏(¥)，建仓数据未就绪时为 None


@dataclass
class ContributionTotal(Contract):
    """组合合计（% 一律相对本金）"""
    principal: float = None        # 本金(¥)
    day_pnl: float = None          # 当日盈亏(¥)
    total_value: float = None      # 总市值(¥)
    total_pnl: Optional[float] = None  # 累计盈亏(¥)
    total_pct: Optional[float] = None  # 累计收益率(%) = total_pnl/principal
    up: int = None                 # 上涨家数
    down: int = None               # 下跌家数
