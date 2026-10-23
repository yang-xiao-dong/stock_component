# -*- coding: utf-8 -*-
"""GroupApi 数据层回归测试（stub 数据源，无网络）
运行（项目根目录下）：python tests/test_group_component.py

核心不变量（数值一致性保证）：
1. 组合的每个版本只由「同一轮抓到的完整数据」原子构建——一轮里任何一只
   失败就整轮作废、沿用上一版，绝不按股票混入新旧/异源数据；
2. 相同输入重算结果逐字段一致（重启/重载/重复刷新数值不变）；
3. 快照保存→加载→重算 与直接计算完全一致（离线回看可重现）。
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.group import component as group_component  # noqa: E402
from config import PRINCIPAL, STOCKS  # noqa: E402
from core import data_define as dd  # noqa: E402
from core import group_calc  # noqa: E402

ALL = [s["code"] for s in STOCKS]


def _bars(base=10.0, n=5):
    return [{"date": f"d{i}", "open": base, "close": base + i, "high": base + i + 1, "low": base - 1}
            for i in range(n)]


class _Stub:
    """数据源桩：kline/minute 按 ok_codes 放行，其余返回 None"""

    def __init__(self, ok_codes, minute_ok=(), base=10.0):
        self.ok = set(ok_codes)
        self.minute_ok = set(minute_ok)
        self.base = base
        self.get_realtime_batch = lambda codes: {
            c: {"prev_close": 10.0, "price": 11.0} for c in self.ok}
        self.get_minute_data = (lambda code: [{"time": "09:30", "price": 10.0, "vol": 1}]
                                if code in self.minute_ok else None)
        self.get_kline = (lambda code, count=60: _bars(self.base) if code in self.ok else None)
        self.get_mode = lambda: {"mode": "live", "date": None}


def _make_api(stub):
    group_component.data_source = stub
    return group_component.GroupApi(scheduler=None)


def test_partial_kline_never_shrinks_group():
    # 只有 2 只取到日K → 拒绝重建，图表保持无数据，而不是 2 只的组合
    api = _make_api(_Stub(ALL[:2]))
    assert api.get_group_kline() is None and api._kline is None


def test_full_kline_then_partial_cycle_discards_whole_round():
    # 先集齐 → 有完整组合；随后一轮 3 只成功(且数据变了) + 7 只失败
    # → 整轮作废：成功股票的新数据也不得混入，逐字段沿用上一版
    api = _make_api(_Stub(ALL))
    api.refresh_kline()
    v1 = api.get_group_kline()
    assert v1 and len(v1["stocks"]) == len(ALL)

    group_component.data_source = _Stub(ALL[:3], base=99.0)  # 成功的 3 只数据完全不同
    api.refresh_kline()
    v2 = api.get_group_kline()
    assert json.dumps(v2, sort_keys=True) == json.dumps(v1, sort_keys=True), \
        "部分成功的一轮必须整轮作废，不得按股票混入新数据"
    assert set(api._shares) == set(ALL)


def test_share_not_inflated_by_partial_data():
    # 部分失败期间份额绝不按少数股票放大：每只份额 = 本金/N/首日开盘
    api = _make_api(_Stub(ALL))
    api.refresh_kline()
    per = PRINCIPAL / len(ALL) / 10.0  # 首日开盘价 10
    for c in ALL:
        assert abs(api._shares[c] - per) < 1e-6
    group_component.data_source = _Stub(ALL[:3])
    api.refresh_kline()
    for c in ALL:
        assert abs(api._shares[c] - per) < 1e-6


def test_rebuild_deterministic():
    # 相同输入重算两次，结果逐字段一致（重启/重复刷新数值不变）
    a1 = _make_api(_Stub(ALL))
    a1.refresh_kline()
    a2 = _make_api(_Stub(ALL))
    a2.refresh_kline()
    assert json.dumps(a1.get_group_kline(), sort_keys=True) == \
           json.dumps(a2.get_group_kline(), sort_keys=True)
    assert a1._shares == a2._shares and a1._entry == a2._entry


def test_minute_atomic_round():
    # 分时同理：缺一只整轮作废（合计线不被低估），集齐才更新
    api = _make_api(_Stub(ALL, minute_ok=ALL[:4]))
    api.refresh_minute()
    assert api._minute is None
    group_component.data_source = _Stub(ALL, minute_ok=ALL)
    api.refresh_minute()
    assert api._minute is not None


def test_snapshot_reload_recomputes_identically():
    # 快照保存→加载→离线重算 与 直接计算完全一致（重载可重现）
    kmap = {c: _bars(base=10.0 + i) for i, c in enumerate(ALL)}
    realtime = {c: dd.RealtimeQuote(name=c, code=c, price=11, prev_close=10,
                                    open=10, time="20260921150001", change=1,
                                    change_pct=10, high=11, low=10, volume=1,
                                    amount=1).to_dict() for c in ALL}
    snap = dd.MarketSnapshot.capture(realtime, {}, kmap)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "snap.json")
        dd.save_snapshot(snap, path)
        loaded = dd.load_snapshot(path)
    direct = group_calc.build_group_kline(kmap, PRINCIPAL, max_points=60)
    from_snapshot = group_calc.build_group_kline(
        {c: [b.to_dict() for b in bars] for c, bars in loaded.kline.items()},
        PRINCIPAL, max_points=60)
    assert json.dumps(from_snapshot, sort_keys=True) == json.dumps(direct, sort_keys=True)


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"通过 {name}")
        except AssertionError:
            failed += 1
            print(f"失败 {name}")
    total = len(tests)
    if failed:
        print(f"共 {total} 项，{failed} 项失败 ✘"); sys.exit(1)
    print(f"共 {total} 项，全部通过 ✔")
