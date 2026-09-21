# -*- coding: utf-8 -*-
"""实时行情契约。字段名与腾讯接口解析一一对应（解析逻辑见 core/stock_api.py）。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class RealtimeQuote(Contract):
    name: str = None        # 名称
    code: str = None        # 代码（腾讯格式，如 sh603893）
    price: float = None     # 最新价
    prev_close: float = None  # 昨收
    open: float = None      # 今开
    time: str = None        # 行情时间 yyyymmddHHMMSS
    change: float = None    # 涨跌（元）
    change_pct: float = None  # 涨跌幅（%）
    high: float = None      # 最高
    low: float = None       # 最低
    volume: float = None    # 成交量（手）
    amount: float = None    # 成交额（亿元）

    def is_complete(self) -> bool:
        """关键字段齐全（停牌/异常行情时可用于降级判断）"""
        return all(v is not None for v in
                   (self.price, self.prev_close, self.change_pct))
