# -*- coding: utf-8 -*-
"""外壳布局偏好契约。"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class ComponentLayout(Contract):
    order: list = None  # 按显示顺序排列的组件 id
