# -*- coding: utf-8 -*-
"""core/vol_calc 成交量派生计算测试：全部合成数据，无网络无数据库
运行（项目根目录下）：python tests/test_vol_calc.py
"""
import os
import sys
from itertools import accumulate

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vol_calc import MINUTES_PER_DAY, minute_deltas, volume_ratio


def pts(*vols):
    """按累计量序列构造分时点（价格字段与差分无关）"""
    return [{"time": "09:30", "price": 10.0, "vol": v} for v in vols]


def cum_pts(per_minute):
    """按每分钟量构造累计分时点"""
    return pts(*accumulate(per_minute))


def test_minute_deltas_normal():
    # 单分钟量 = 相邻累计值相减；首点差分即开盘集合竞价量
    assert minute_deltas(pts(100, 150, 220)) == [100.0, 50.0, 70.0]


def test_minute_deltas_clamp_small_jitter():
    # 小幅回退（0.5 < 末端累计 1%）钳为 0，不判损坏
    assert minute_deltas(pts(100, 150, 149.5, 220)) == [100.0, 50.0, 0.0, 70.5]


def test_minute_deltas_reject_broken_series():
    # 大幅回退（负差分总量超过末端累计 1%）视为数据损坏，整段不画
    assert minute_deltas(pts(1000, 1500, 800)) is None


def test_minute_deltas_missing_or_short():
    assert minute_deltas([]) is None
    assert minute_deltas(pts(100)) is None
    assert minute_deltas([{"time": "09:30", "price": 10}, {"time": "09:31", "vol": 5}]) is None
    assert minute_deltas(pts(None, 100)) is None


def test_volume_ratio_full_day():
    # 全天分时（240 分钟、每分钟 5 → 累计 1200）对比近几日全天量均值 1200 → 量比 1.0
    today = cum_pts([5] * MINUTES_PER_DAY)
    assert abs(volume_ratio(today, [960, 1200, 1440]) - 1.0) < 1e-9


def test_volume_ratio_partial_day():
    # 盘中 60 分钟累计 300 → 每分钟 5；历史日均 960 → 每分钟 4 → 量比 1.25
    today = cum_pts([5] * 60)
    assert abs(volume_ratio(today, [960]) - 1.25) < 1e-9


def test_volume_ratio_insufficient():
    assert volume_ratio([], [1000]) is None
    assert volume_ratio(pts(100), []) is None
    assert volume_ratio(pts(100), [0, None]) is None      # 历史日总量无效
    assert volume_ratio([{"price": 10}], [1000]) is None  # 今日无量


def test_volume_ratio_rejects_unit_mismatch():
    # 旧库分时误存成交额（元）与手混排时，量比落在荒谬区间 → 宁缺毋错返回 None
    today = cum_pts([5] * MINUTES_PER_DAY)                # 全天累计 1200 手
    assert volume_ratio(today, [2.9e9] * 5) is None
    assert volume_ratio(cum_pts([5e7] * MINUTES_PER_DAY), [1000]) is None  # 反向混排


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"通过 {name}")
    print(f"共 {len(tests)} 项，全部通过 ✔")
