# -*- coding: utf-8 -*-
"""group_calc 均分聚合的单元测试（合成数据，无网络）
运行（项目根目录下）：python tests/test_group_calc.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import group_calc


def test_minute_equal_weight():
    # 两只股票：a 当日 +10%，b 持平 → 均分平均 +5%
    minute_map = {
        "a": [{"time": "09:30", "price": 10}, {"time": "09:31", "price": 11}],
        "b": [{"time": "09:30", "price": 20}, {"time": "09:31", "price": 20}],
    }
    out = group_calc.build_group_minute(minute_map, {"a": 10, "b": 20})
    assert out["times"] == ["09:30", "09:31"]
    line_a = [s for s in out["stocks"] if s["code"] == "a"][0]["data"]
    assert abs(line_a[1] - 10.0) < 1e-9
    assert abs(out["avg"][0] - 0.0) < 1e-9
    assert abs(out["avg"][1] - 5.0) < 1e-9


def test_minute_missing_stock_reaveraged():
    # b 缺 09:31 → 该时点只有 a，在可用股票内重新均分 = a 自己的值
    minute_map = {
        "a": [{"time": "09:30", "price": 11}, {"time": "09:31", "price": 11}],
        "b": [{"time": "09:30", "price": 20}],
    }
    out = group_calc.build_group_minute(minute_map, {"a": 10, "b": 20})
    assert abs(out["avg"][1] - 10.0) < 1e-9
    line_b = [s for s in out["stocks"] if s["code"] == "b"][0]["data"]
    assert line_b[1] is None


def test_kline_index_and_candles():
    # 首日以开盘价为基准：a +10% b 0% → +5%；次日 a 0% b +10% → 再 +5%
    k = {
        "a": [{"date": "1", "open": 10, "close": 11, "high": 12, "low": 9},
              {"date": "2", "open": 11, "close": 11, "high": 12, "low": 10}],
        "b": [{"date": "1", "open": 20, "close": 20, "high": 21, "low": 19},
              {"date": "2", "open": 20, "close": 22, "high": 23, "low": 20}],
    }
    out = group_calc.build_group_kline(k)
    assert out["dates"] == ["1", "2"]
    c1, c2 = out["candles"][0], out["candles"][1]
    assert abs(c1["close"] - 105.0) < 1e-9
    assert abs(c2["close"] - 110.25) < 1e-9
    assert c2["high"] >= max(c2["open"], c2["close"])
    assert c2["low"] <= min(c2["open"], c2["close"])
    line_a = [s for s in out["stocks"] if s["code"] == "a"][0]["data"]
    line_b = [s for s in out["stocks"] if s["code"] == "b"][0]["data"]
    assert abs(line_a[0] - 110.0) < 1e-9   # 首日 a +10%（以开盘价为基准）
    assert abs(line_a[1] - 110.0) < 1e-9   # 次日 a 持平
    assert abs(line_b[0] - 100.0) < 1e-9
    assert abs(line_b[1] - 110.0) < 1e-9


def test_kline_trim():
    bars = lambda: [{"date": str(i), "open": 1, "close": 1.01, "high": 1.02, "low": 0.99}
                    for i in range(10)]
    out = group_calc.build_group_kline({"a": bars()}, max_points=5)
    assert len(out["dates"]) == 5
    assert out["dates"] == ["5", "6", "7", "8", "9"]
    assert len(out["candles"]) == 5
    assert len(out["stocks"][0]["data"]) == 5


def test_contribution():
    rt = {"a": {"name": "A", "change_pct": 10.0}, "b": {"name": "B", "change_pct": -2.0}}
    rows, total = group_calc.build_contribution(rt)
    assert abs(total - 4.0) < 1e-9                      # (10-2)/2
    assert abs(rows[0]["contribution"] - 5.0) < 1e-9    # 贡献 = 涨跌幅 × 1/N
    assert abs(rows[0]["weight"] - 50.0) < 1e-9         # 均分权重
    assert rows[0]["code"] == "a"


def test_contribution_skips_bad_data():
    rt = {"a": {"name": "A", "change_pct": 6.0}, "bad": None}
    rows, total = group_calc.build_contribution(rt)
    assert len(rows) == 1
    assert abs(total - 6.0) < 1e-9


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"通过 {name}")
    print(f"共 {len(tests)} 项，全部通过 ✔")
