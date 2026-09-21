# -*- coding: utf-8 -*-
"""股票列表条目契约（config.STOCKS / 前端股票列表共用）。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class StockInfo(Contract):
    code: str = None    # 腾讯格式代码
    name: str = None
    weight: float = None  # 可选自定义权重（缺省等权）
