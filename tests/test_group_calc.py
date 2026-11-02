# -*- coding: utf-8 -*-
"""group_calc 均分建仓(¥绝对度量)计算的单元测试（合成数据，无网络）
运行（项目根目录下）：python tests/test_group_calc.py
口径：本金均分建仓、持有不动；¥为绝对度量，%相对本金。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import group_calc


def near(a, b, eps=1e-6):
    return a is not None and abs(a - b) < eps


MM = {
    "a": [{"time": "09:30", "price": 10}, {"time": "09:31", "price": 11}],
    "b": [{"time": "09:30", "price": 20}, {"time": "09:31", "price": 20}],
}


def test_minute_yuan_approx_shares():
    # 本金2万均分：a 1000股、b 500股；09:31 a 涨1元 → 组合当日盈亏 +1000¥
    out = group_calc.build_group_minute(MM, {"a": 10, "b": 20}, None, 20000)
    assert out["times"] == ["09:30", "09:31"]
    a = [s for s in out["stocks"] if s["code"] == "a"][0]["data"]
    assert near(a[0], 0) and near(a[1], 1000)
    assert near(out["total"][0], 0) and near(out["total"][1], 1000)


def test_minute_with_real_shares():
    # 正式份额 a=2000股、b=0 → 09:31 合计 2000¥（b 无份额不贡献）
    out = group_calc.build_group_minute(MM, {"a": 10, "b": 20}, {"a": 2000, "b": 0}, 0)
    assert near(out["total"][1], 2000)
    b = [s for s in out["stocks"] if s["code"] == "b"][0]["data"]
    assert near(b[1], 0)


def test_minute_missing_stock_sum():
    # b 缺 09:31：绝对合计只加可得股票
    mm = {"a": MM["a"], "b": [{"time": "09:30", "price": 20}]}
    out = group_calc.build_group_minute(mm, {"a": 10, "b": 20}, {"a": 1000, "b": 500}, 0)
    assert near(out["total"][1], 1000)
    b = [s for s in out["stocks"] if s["code"] == "b"][0]["data"]
    assert b[1] is None


def test_kline_yuan_candles():
    # 本金1万均分：a 500股(建仓10)、b 250股(建仓20)
    k = {
        "a": [{"date": "1", "open": 10, "close": 11, "high": 12, "low": 9},
              {"date": "2", "open": 11, "close": 11, "high": 12, "low": 10}],
        "b": [{"date": "1", "open": 20, "close": 20, "high": 21, "low": 19},
              {"date": "2", "open": 20, "close": 22, "high": 23, "low": 20}],
    }
    out = group_calc.build_group_kline(k, 10000)
    assert near(out["shares"]["a"], 500) and near(out["shares"]["b"], 250)
    c1, c2 = out["candles"]
    assert near(c1["open"], 10000)          # 建仓日开盘 = 本金
    assert near(c1["close"], 10500)         # 500×11 + 250×20
    assert near(c1["high"], 11250)          # 500×12 + 250×21
    assert near(c1["low"], 9250)
    assert near(c2["close"], 11000)         # 500×11 + 250×22
    a = [s for s in out["stocks"] if s["code"] == "a"][0]["data"]
    assert near(a[0], 5500) and near(a[1], 5500)
    b = [s for s in out["stocks"] if s["code"] == "b"][0]["data"]
    assert near(b[0], 5000) and near(b[1], 5500)
    assert near(out["principal"], 10000)


def test_kline_trim():
    bars = lambda: [{"date": str(i), "open": 1, "close": 1.01, "high": 1.02, "low": 0.99}
                    for i in range(10)]
    out = group_calc.build_group_kline({"a": bars()}, 100, max_points=5)
    assert out["dates"] == ["5", "6", "7", "8", "9"]
    assert len(out["candles"]) == 5
    assert len(out["stocks"][0]["data"]) == 5


def test_kline_stock_bars():
    # 每只股票附带自身日K（OHLC 原样传递）；max_points 截尾时 bars 同步取尾部
    k = {
        "a": [{"date": "1", "open": 10, "close": 11, "high": 12, "low": 9},
              {"date": "2", "open": 11, "close": 13, "high": 14, "low": 10.5},
              {"date": "3", "open": 13, "close": 12, "high": 13.5, "low": 11.5}],
        "b": [{"date": "1", "open": 20, "close": 20, "high": 21, "low": 19},
              {"date": "2", "open": 20, "close": 22, "high": 23, "low": 20},
              {"date": "3", "open": 22, "close": 21, "high": 22.5, "low": 20.5}],
    }
    out = group_calc.build_group_kline(k, 10000)
    sa = [s for s in out["stocks"] if s["code"] == "a"][0]
    assert len(sa["bars"]) == 3
    assert sa["bars"][1]["date"] == "2"
    assert near(sa["bars"][1]["high"], 14) and near(sa["bars"][2]["close"], 12)
    cut = group_calc.build_group_kline(k, 10000, max_points=2)
    sb = [s for s in cut["stocks"] if s["code"] == "b"][0]
    assert len(sb["bars"]) == 2 and sb["bars"][-1]["date"] == "3"


def test_contribution_yuan():
    rt = {"a": {"name": "A", "price": 11, "prev_close": 10, "change_pct": 10.0},
          "b": {"name": "B", "price": 19.6, "prev_close": 20, "change_pct": -2.0}}
    rows, total = group_calc.build_contribution(
        rt, {"a": 500.0, "b": 250.0}, {"a": 10.0, "b": 20.0}, 10000)
    assert rows[0]["code"] == "a"
    assert near(rows[0]["day_pnl"], 500) and near(rows[0]["value"], 5500)
    assert near(rows[0]["total_pnl"], 500)
    assert near(rows[1]["day_pnl"], -100, 1e-4) and near(rows[1]["value"], 4900, 1e-4)
    assert near(rows[1]["total_pnl"], -100, 1e-4)
    assert near(total["day_pnl"], 400, 1e-4)
    assert near(total["total_value"], 10400, 1e-4)
    assert near(total["total_pnl"], 400, 1e-4)
    assert near(total["total_pct"], 4.0, 1e-4)   # 相对本金


def test_contribution_fallback_pending():
    # 无建仓数据：份额依赖字段一律 None（等日K首日建仓落地），只有涨跌幅/家数
    rt = {"a": {"name": "A", "price": 11, "prev_close": 10, "change_pct": 10.0}}
    rows, total = group_calc.build_contribution(rt, None, None, 10000)
    assert rows[0]["day_pnl"] is None and rows[0]["value"] is None
    assert rows[0]["total_pnl"] is None
    assert total["day_pnl"] is None and total["total_value"] is None
    assert total["total_pnl"] is None and total["total_pct"] is None
    assert total["up"] == 1 and total["down"] == 0


def test_contribution_no_data():
    rows, total = group_calc.build_contribution({"bad": None}, None, None, 10000)
    assert rows == [] and total is None


def test_group_minute_vol_total_aggregates_industry_volume():
    # 行业量能：各股单分钟量合计（累计量差分）；无量股不计入，序列损坏整股剔除
    m = {"a": [{"time": "09:30", "price": 10, "vol": 100},
               {"time": "09:31", "price": 11, "vol": 260}],
         "b": [{"time": "09:30", "price": 20, "vol": 50},
               {"time": "09:31", "price": 19, "vol": 80}],
         "c": [{"time": "09:30", "price": 5, "vol": None},   # 无量股
               {"time": "09:31", "price": 5, "vol": None}]}
    out = group_calc.build_group_minute(m, {"a": 10, "b": 20, "c": 5}, None, 30000)
    assert out["vol_total"] == [150.0, 190.0]
    out2 = group_calc.build_group_minute(
        {k: v for k, v in m.items() if k != "c"}, {"a": 10, "b": 20}, None, 20000)
    assert out2["vol_total"] == [150.0, 190.0]   # 无量股不影响合计


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"通过 {name}")
    print(f"共 {len(tests)} 项，全部通过 ✔")
