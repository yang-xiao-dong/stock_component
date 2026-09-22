# -*- coding: utf-8 -*-
"""价格形态预警契约；原始行情百分比与形态幅度均不依赖组合本金。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class ShortTermAssessment(Contract):
    code: str = None
    name: str = None
    status: str = None             # signal / clear / insufficient
    reason: str = None
    change_pct: float = None       # 行情原始涨跌幅
    observed_at: str = None        # 行情时间 YYYYMMDDHHMMSS
    peak_time: str = None          # HH:MM
    trough_time: str = None        # HH:MM
    drawdown_pct: float = None     # 高点到低点的回撤百分比
    rebound_pct: float = None      # 当前价相对低点的反弹百分比
    recovery_pct: float = None     # (当前价 - 低点) / (高点 - 低点) × 100


@dataclass
class LongTermAssessment(Contract):
    code: str = None
    name: str = None
    status: str = None             # uptrend / downtrend / range / insufficient
    reason: str = None
    change_pct: float = None       # 行情原始涨跌幅
    price: float = None
    as_of: str = None              # 趋势使用的最后一根日K日期
    ma_medium: float = None        # 默认 20 日均价
    ma_long: float = None          # 默认 60 日均价
    support: float = None          # 最近区间最低价（参考）
    resistance: float = None       # 最近区间最高价（参考）


@dataclass
class AnalysisBoard(Contract):
    mode: str = None               # live / offline
    date: str = None               # 当前分析交易日 YYYY-MM-DD
    status: str = None             # loading / ready / error
    updated_at: str = None
    message: str = None
    long_term: list = None         # [LongTermAssessment]
    short_term: list = None        # [ShortTermAssessment]
