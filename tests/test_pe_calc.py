# -*- coding: utf-8 -*-
"""pe_calc PE折算与统计的单元测试（合成数据，无网络）
运行（项目根目录下）：python tests/test_pe_calc.py
口径：历史PE按当前EPS折算 pe(t)=close(t)×pe_now/last_close；分位=窗口内≤当前值的占比。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import pe_calc


def near(a, b, eps=1e-6):
    return a is not None and abs(a - b) < eps


def test_history_scale():
    # 价格翻倍 → 折算PE翻倍：close 100→200, pe_now=50 → 历史 25→50
    closes = [{"date": "2026-01-01", "close": 100.0},
              {"date": "2026-01-02", "close": 200.0}]
    pts = pe_calc.pe_history(closes, 50.0, 200.0)
    assert len(pts) == 2
    assert near(pts[0]["pe"], 25.0) and near(pts[1]["pe"], 50.0)


def test_history_anchor_latest_price():
    # 锚点用盘中最新价而非最后一根收盘：price=150, close=100, pe_now=30 → 20 与 30
    closes = [{"date": "2026-01-01", "close": 100.0}, {"date": "2026-01-02", "close": 150.0}]
    pts = pe_calc.pe_history(closes, 30.0, 150.0)
    assert near(pts[0]["pe"], 20.0)


def test_history_loss_making():
    # 亏损（pe≤0）或锚点缺失 → 空序列
    closes = [{"date": "2026-01-01", "close": 10.0}]
    assert pe_calc.pe_history(closes, -5.0, 10.0) == []
    assert pe_calc.pe_history(closes, None, 10.0) == []
    assert pe_calc.pe_history(closes, 20.0, None) == []
    assert pe_calc.pe_history([], 20.0, 10.0) == []


def test_history_skips_bad_rows():
    closes = [{"date": "2026-01-01", "close": 100.0},
              {"date": "2026-01-02"},  # 无收盘价跳过
              {"date": "2026-01-03", "close": "停牌"}]  # 非数值跳过
    pts = pe_calc.pe_history(closes, 50.0, 100.0)
    assert len(pts) == 1 and near(pts[0]["pe"], 50.0)


def test_percentile_rank():
    # 10个点升序，最后一点是最高值 → 分位100；最低值 → 10
    pts = [{"date": f"2026-01-{i:02d}", "pe": float(i)} for i in range(1, 11)]
    assert near(pe_calc.pe_percentile(pts), 100.0)
    low = [{"date": f"2026-01-{i:02d}", "pe": float(11 - i)} for i in range(1, 11)]
    assert near(pe_calc.pe_percentile(low), 10.0)
    mid = [{"date": f"2026-01-{i:02d}", "pe": 10.0} for i in range(1, 11)]
    mid[0]["pe"] = 20.0   # 20×1 + 10×9，当前(最后)=10 → 仅高于 9/10
    assert near(pe_calc.pe_percentile(mid), 90.0)


def test_percentile_insufficient():
    assert pe_calc.pe_percentile([{"date": "d", "pe": 5.0}]) is None
    assert pe_calc.pe_percentile([]) is None
    pts = [{"date": f"d{i}", "pe": float(i)} for i in range(4)]  # 4个点不足
    assert pe_calc.pe_percentile(pts) is None


def test_median():
    # 奇数个取中间，偶数个取均值
    pts = [{"date": f"d{i}", "pe": float(i)} for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    assert near(pe_calc.pe_median(pts), 5.5)
    odd = [{"date": f"d{i}", "pe": float(v)} for i, v in enumerate([3, 1, 2, 5, 4])]
    assert near(pe_calc.pe_median(odd), 3.0)
    # 非正值不参与
    neg = [{"date": f"d{i}", "pe": float(v)} for i, v in enumerate([-1, 1, 2, 3, 4, 5])]
    assert near(pe_calc.pe_median(neg), 3.0)


def test_build_series_ok():
    closes = [{"date": f"2026-01-{i:02d}", "close": 100.0 + i} for i in range(1, 11)]
    quote = {"pe_ttm": 55.0, "price": 110.0}
    s = pe_calc.build_pe_series({"code": "sh603893", "name": "瑞芯微"}, quote, closes)
    assert s["name"] == "瑞芯微" and near(s["pe_now"], 55.0)
    assert len(s["points"]) == 10 and near(s["points"][-1]["pe"], 55.0)
    assert s["percentile"] is not None and s["median"] is not None
    assert s["note"] is None


def test_build_series_degraded():
    # 无行情 / 亏损 / 无收盘序列 → 不抛异常，带备注
    s1 = pe_calc.build_pe_series({"code": "x", "name": "X"}, None, [])
    assert s1["note"] == "暂无行情" and not s1["points"]
    s2 = pe_calc.build_pe_series({"code": "x", "name": "X"}, {"pe_ttm": -3.0}, [{"date": "d", "close": 10}])
    assert s2["note"] == "亏损或无PE" and not s2["points"]
    s3 = pe_calc.build_pe_series({"code": "x", "name": "X"}, {"pe_ttm": 30.0, "price": 10.0}, None)
    assert s3["note"] == "收盘序列获取失败" and not s3["points"]


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
