# -*- coding: utf-8 -*-
"""当日分时点契约。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class MinutePoint(Contract):
    time: str = None    # HH:MM
    price: float = None
    vol: float = None   # 该分钟成交量（手）
