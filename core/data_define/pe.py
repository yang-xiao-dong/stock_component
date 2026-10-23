# -*- coding: utf-8 -*-
"""PE 对比契约：参照公司 + 对比组的历史PE序列与统计（计算见 core/pe_calc.py）。

口径约定：
- PE 一律用 TTM；历史值按「当前 EPS 折算」：pe(t) = close(t) × pe_now / close_now，
  财报发布日之间准确，跨财报季会出现台阶（界面需注明）
- 分位数 = 窗口内 pe ≤ 当前值 的交易日占比（0-100），回答「当前PE在历史上高还是低」
- 亏损/无PE（pe_ttm 为空或 ≤0）时序列为空，界面显示「亏损」而非折线
"""
from dataclasses import dataclass, field
from typing import List

from .common import Contract


@dataclass
class PePoint(Contract):
    date: str = None   # 交易日 yyyy-mm-dd
    pe: float = None   # 折算PE-TTM


@dataclass
class PeSeries(Contract):
    code: str = None       # 腾讯代码（如 sh603893 / usQCOM）
    name: str = None       # 显示名
    pe_now: float = None   # 当前PE-TTM（None=亏损或无数据）
    points: List[PePoint] = field(default_factory=list)  # 历史折算PE
    percentile: float = None  # 当前PE在窗口内的历史分位（%，None=无法计算）
    median: float = None      # 窗口PE中位数
    note: str = None          # 数据备注（亏损/快照缺失/接口受限等）
    is_reference: bool = False  # True=参照公司（高通），画虚线不计排名


@dataclass
class PeCompareBoard(Contract):
    mode: str = None        # live | offline
    date: str = None        # 数据基准日
    status: str = None      # loading | ready | error
    message: str = None
    updated_at: str = None
    window_days: int = None # 历史窗口交易日数
    reference: PeSeries = None   # 参照（高通），可为 None（快照模式无美股）
    peers: List[PeSeries] = field(default_factory=list)
