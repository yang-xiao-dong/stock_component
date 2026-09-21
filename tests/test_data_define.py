# -*- coding: utf-8 -*-
"""core/data_define 数据契约测试：序列化往返、容错、快照存取（无网络）
运行（项目根目录下）：python tests/test_data_define.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import data_define as dd


def test_quote_roundtrip():
    q = dd.RealtimeQuote(name="瑞芯微", code="sh603893", price=101.5,
                         prev_close=100.0, open=100.2, time="20260921150000",
                         change=1.5, change_pct=1.5, high=102.0, low=99.8,
                         volume=12345.0, amount=12.5)
    d = q.to_dict()
    assert set(d) == {"name", "code", "price", "prev_close", "open", "time",
                      "change", "change_pct", "high", "low", "volume", "amount"}
    q2 = dd.RealtimeQuote.from_dict(d)
    assert q2.price == 101.5 and q2.code == "sh603893" and q2.is_complete()


def test_from_dict_tolerant():
    # 缺字段 -> None；未知字段 -> 忽略（旧版本快照向前兼容）
    q = dd.RealtimeQuote.from_dict({"code": "sh603893", "future_field": 1})
    assert q.code == "sh603893" and q.price is None and not q.is_complete()
    bar = dd.KlineBar.from_dict({"date": "2026-09-21"})
    assert bar.close is None


def test_kline_minute_roundtrip():
    bars = [dd.KlineBar(date="2026-09-21", open=10, close=11, high=12, low=9)]
    assert dd.KlineBar.from_dict(bars[0].to_dict()).close == 11
    p = dd.MinutePoint(time="09:31", price=11.0, vol=123)
    assert dd.MinutePoint.from_dict(p.to_dict()).time == "09:31"


def test_group_roundtrip_nested():
    gm = dd.GroupMinute(times=["09:30", "09:31"], total=[0.0, 100.0],
                        stocks=[dd.StockSeries(code="a", data=[0.0, 100.0])])
    d = gm.to_dict()
    assert d["stocks"][0]["code"] == "a" and d["total"][1] == 100.0

    gk = dd.GroupKline(principal=100000, dates=["2026-09-21"],
                       candles=[dd.KlineBar(date="2026-09-21", open=100000,
                                            close=101000, high=102000, low=99000)],
                       stocks=[dd.StockSeries(code="a", data=[10100])],
                       shares={"a": 500.0})
    d = gk.to_dict()
    assert d["candles"][0]["close"] == 101000 and d["shares"]["a"] == 500.0

    row = dd.ContributionRow(code="a", name="A", change_pct=10.0,
                             day_pnl=500.0, value=5500.0, total_pnl=500.0)
    total = dd.ContributionTotal(principal=10000, day_pnl=500, total_value=10500,
                                 total_pnl=500, total_pct=5.0, up=1, down=0)
    assert dd.ContributionRow.from_dict(row.to_dict()).day_pnl == 500.0
    assert dd.ContributionTotal.from_dict(total.to_dict()).total_pct == 5.0


def test_snapshot_capture_save_load():
    realtime = {"a": dd.RealtimeQuote(name="A", code="a", price=11,
                                      prev_close=10, open=10, time="20260921150001",
                                      change=1, change_pct=10, high=11, low=10,
                                      volume=1, amount=1).to_dict()}
    minute = {"a": [dd.MinutePoint(time="09:30", price=10, vol=1).to_dict()]}
    kline = {"a": [dd.KlineBar(date="2026-09-21", open=10, close=11,
                               high=12, low=9).to_dict()]}

    snap = dd.MarketSnapshot.capture(realtime, minute, kline)
    assert snap.version == dd.SNAPSHOT_VERSION
    assert snap.date == "2026-09-21"
    assert snap.realtime["a"].price == 11
    assert snap.kline["a"][0].close == 11

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "snap.json")
        saved = dd.save_snapshot(snap, path)
        loaded = dd.load_snapshot(saved)
        assert loaded.realtime["a"].change_pct == 10
        assert loaded.minute["a"][0].time == "09:30"
        assert loaded.kline["a"][0].high == 12


def test_snapshot_from_dict_tolerant():
    snap = dd.MarketSnapshot.from_dict({"version": 1, "date": "2026-09-21",
                                        "realtime": {}, "minute": {}, "kline": {}})
    assert snap.date == "2026-09-21" and snap.realtime == {}
    assert dd.MarketSnapshot.from_dict(None) is None


def test_offline_recompute_from_snapshot():
    # 快照 -> 离线重算组合结构（后期离线模式的核心路径）
    from core import group_calc
    snap = dd.MarketSnapshot.from_dict({
        "date": "2026-09-21",
        "realtime": {"a": {"name": "A", "code": "a", "price": 11, "prev_close": 10,
                            "change_pct": 10.0}},
        "minute": {"a": [{"time": "09:31", "price": 11}]},
        "kline": {"a": [{"date": "2026-09-21", "open": 10, "close": 11,
                          "high": 12, "low": 9}]},
    })
    minute = {c: [p.to_dict() for p in pts] for c, pts in snap.minute.items()}
    kline = {c: [b.to_dict() for b in bars] for c, bars in snap.kline.items()}
    prev = {c: q.prev_close for c, q in snap.realtime.items()}
    out = group_calc.build_group_minute(minute, prev, None, 20000)
    assert out["total"][-1] == 2000.0          # (20000/1)/10 × (11-10)
    k = group_calc.build_group_kline(kline, 20000)
    assert k["candles"][0]["close"] == 22000.0  # 2000股 × 11


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"通过 {name}")
    print(f"共 {len(tests)} 项，全部通过 ✔")
