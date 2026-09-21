# -*- coding: utf-8 -*-
"""日K线契约（前复权）。组合市值蜡烛复用同一结构（单位为¥）。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class KlineBar(Contract):
    date: str = None    # 交易日 yyyy-mm-dd
    open: float = None
    close: float = None
    high: float = None
    low: float = None
