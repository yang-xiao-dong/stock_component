# -*- coding: utf-8 -*-
"""GroupApi 数据层回归测试（stub 数据源，无网络）
运行（项目根目录下）：python tests/test_group_component.py

核心不变量：任何一轮日K抓取出现部分失败时，组合结果绝不按少数股票重建
（那会把本金错分、图表缩水），而是沿用缓存/上一版完整结果。
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.group import component as group_component  # noqa: E402
from config import STOCKS  # noqa: E402


def _bars(n=5, base=10.0):
    return [{"date": f"d{i}", "open": base, "close": base + i, "high": base + i + 1, "low": base - 1}
            for i in range(n)]


class _KlineStub:
    """get_kline 桩：ok_codes 里的代码返回日K，其余返回 None"""

    def __init__(self, ok_codes):
        self.ok = set(ok_codes)
        self.calls = 0

    def __call__(self, code, count=60):
        self.calls += 1
        return _bars() if code in self.ok else None


def _make_api(kline_stub):
    ds = types.ModuleType("ds")
    ds.get_realtime_batch = lambda codes: {}
    ds.get_minute_data = lambda code: None
    ds.get_kline = kline_stub
    group_component.data_source = ds
    return group_component.GroupApi(scheduler=None)


def test_partial_kline_never_shrinks_group():
    # 只有 2 只取到日K → 拒绝重建，图表保持无数据（前端显示加载中），而不是 2 只的组合
    stub = _KlineStub([s["code"] for s in STOCKS[:2]])
    api = _make_api(stub)
    assert api.get_group_kline() is None
    assert api._kline is None


def test_full_kline_then_partial_keeps_complete():
    # 先集齐 10 只 → 有完整组合；随后一轮只有 2 只成功 → 沿用缓存，组合仍 10 只
    all_codes = [s["code"] for s in STOCKS]
    stub = _KlineStub(all_codes)
    api = _make_api(stub)
    api.refresh_kline()
    data = api.get_group_kline()
    assert data and len(data["stocks"]) == len(all_codes)
    assert set(data["shares"]) == set(all_codes)

    stub = _KlineStub(all_codes[:2])
    group_component.data_source.get_kline = stub
    api.refresh_kline()
    data2 = api.get_group_kline()
    assert data2 and len(data2["stocks"]) == len(all_codes)


def test_share_not_inflated_by_partial_data():
    # 部分失败期间份额绝不按少数股票放大：完整建仓后每只份额 = 本金/N/首日开盘
    from config import PRINCIPAL
    all_codes = [s["code"] for s in STOCKS]
    api = _make_api(_KlineStub(all_codes))
    api.refresh_kline()
    per = PRINCIPAL / len(all_codes) / 10.0  # 首日开盘价 10
    for c in all_codes:
        assert abs(api._shares[c] - per) < 1e-6
    # 一轮部分失败后份额不变
    group_component.data_source.get_kline = _KlineStub(all_codes[:3])
    api.refresh_kline()
    for c in all_codes:
        assert abs(api._shares[c] - per) < 1e-6


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
