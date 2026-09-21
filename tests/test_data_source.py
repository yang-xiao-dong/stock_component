# -*- coding: utf-8 -*-
"""core/data_source 在线/离线数据源测试（合成快照，无网络）
运行（项目根目录下）：python tests/test_data_source.py
"""
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import data_source
from core.data_define import MarketSnapshot


def _make_snapshot(date="2026-09-18"):
    return MarketSnapshot.from_dict({
        "version": 1,
        "date": date,
        "saved_at": "2026-09-18 15:05:00",
        "realtime": {"a": {"name": "A", "code": "a", "price": 11, "prev_close": 10,
                            "open": 10, "change": 1, "change_pct": 10.0,
                            "high": 11, "low": 10, "volume": 1, "amount": 1,
                            "time": "20260918150000"}},
        "minute": {"a": [{"time": "09:30", "price": 10, "vol": 1},
                          {"time": "09:31", "price": 11, "vol": 2}]},
        "kline": {"a": [{"date": date, "open": 10, "close": 11, "high": 12, "low": 9}]},
    })


def test_mode_switch_and_getters():
    assert data_source.get_mode()["mode"] == "live" or True  # 全局状态，先复位
    data_source.set_mode("live")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "2026-09-18.json")
        from core.data_define import save_snapshot
        save_snapshot(_make_snapshot(), path)

        assert data_source.set_mode("offline", "2026-01-01") is False      # 不存在的日期
        assert data_source.set_mode("offline", path) is True               # 支持完整路径
        assert data_source.is_offline()
        m = data_source.get_mode()
        assert m == {"mode": "offline", "date": "2026-09-18"}

        q = data_source.get_realtime("a")
        assert q["price"] == 11 and q["name"] == "A"
        assert data_source.get_realtime("nope") is None
        batch = data_source.get_realtime_batch(["a", "nope"])
        assert set(batch) == {"a"}
        pts = data_source.get_minute_data("a")
        assert len(pts) == 2 and pts[1]["price"] == 11
        bars = data_source.get_kline("a", 60)
        assert bars[0]["close"] == 11

        assert data_source.set_mode("live") is True
        assert not data_source.is_offline()
        assert data_source.get_mode() == {"mode": "live", "date": None}


def test_bad_mode():
    assert data_source.set_mode("nonsense") is False


def test_should_auto_save():
    # 2026-09-21 是周一、2026-09-19 是周六
    ok_now = datetime(2026, 9, 21, 15, 30)
    assert data_source.should_auto_save(ok_now, [], "2026-09-21") is True
    # 周末不保存
    assert data_source.should_auto_save(datetime(2026, 9, 19, 16, 0), [], "2026-09-19") is False
    # 收盘缓冲时刻之前不保存
    assert data_source.should_auto_save(datetime(2026, 9, 21, 14, 59), [], "2026-09-21") is False
    assert data_source.should_auto_save(datetime(2026, 9, 21, 15, 4), [], "2026-09-21") is False
    # 已有当日快照：防重复保存/覆盖
    assert data_source.should_auto_save(ok_now, ["2026-09-21"], "2026-09-21") is False
    # 节假日（当日无新K线）与无K线数据
    assert data_source.should_auto_save(ok_now, [], "2026-09-18") is False
    assert data_source.should_auto_save(ok_now, [], None) is False


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    try:
        for name, fn in tests:
            fn()
            print(f"通过 {name}")
        print(f"共 {len(tests)} 项，全部通过 ✔")
    finally:
        data_source.set_mode("live")   # 复位全局状态，避免影响其他测试
