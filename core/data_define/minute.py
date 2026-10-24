# -*- coding: utf-8 -*-
"""当日分时点契约。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class MinutePoint(Contract):
    time: str = None    # HH:MM
    price: float = None
    vol: float = None   # 腾讯该时点累计成交量（手）；旧快照可能误存成交额，见数据库说明
    date: str = None    # 交易日 YYYY-MM-DD；旧快照缺省，由数据源补齐快照日期
