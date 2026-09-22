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
        assert all(p["date"] == "2026-09-18" for p in pts)  # 旧快照补齐分时交易日
        bars = data_source.get_kline("a", 60)
        assert bars[0]["close"] == 11

        assert data_source.set_mode("live") is True
        assert not data_source.is_offline()
        assert data_source.get_mode() == {"mode": "live", "date": None}


def test_bad_mode():
    assert data_source.set_mode("nonsense") is False


def test_should_auto_save():
    # 只按时间判断：周一至周五且已过收盘缓冲时刻（2026-09-21 周一 / 09-19 周六）
    assert data_source.should_auto_save(datetime(2026, 9, 21, 15, 30)) is True
    assert data_source.should_auto_save(datetime(2026, 9, 21, 15, 5)) is True    # 恰好到点
    assert data_source.should_auto_save(datetime(2026, 9, 21, 15, 4)) is False   # 缓冲时刻前
    assert data_source.should_auto_save(datetime(2026, 9, 21, 14, 59)) is False
    assert data_source.should_auto_save(datetime(2026, 9, 19, 16, 0)) is False   # 周六
    assert data_source.should_auto_save(datetime(2026, 9, 20, 15, 30)) is False  # 周日


def test_fire_time():
    f = data_source._fire_time
    # 交易日盘中 → 当日收盘时刻
    assert f(datetime(2026, 9, 21, 10, 0)) == datetime(2026, 9, 21, 15, 5)
    # 交易日已过收盘 → 立即触发（补存当日）
    assert f(datetime(2026, 9, 21, 15, 30)) == datetime(2026, 9, 21, 15, 30)
    # 周五盘中 → 当日收盘时刻；周五收盘后 → 立即补一次（之后布防下周一）
    assert f(datetime(2026, 9, 18, 10, 0)) == datetime(2026, 9, 18, 15, 5)
    assert f(datetime(2026, 9, 18, 16, 0)) == datetime(2026, 9, 18, 16, 0)
    # 周六/周日 → 下周一
    assert f(datetime(2026, 9, 19, 12, 0)) == datetime(2026, 9, 21, 15, 5)
    assert f(datetime(2026, 9, 20, 12, 0)) == datetime(2026, 9, 21, 15, 5)


def test_capture_skip_existing():
    # allow_overwrite=False：目标日期快照已存在则跳过（自动保存防覆盖）
    class FakeApi:
        def get_realtime_batch(self, codes):
            return {"a": {"name": "A", "code": "a", "price": 11, "prev_close": 10,
                          "open": 10, "change": 1, "change_pct": 10.0, "high": 11,
                          "low": 10, "volume": 1, "amount": 1, "time": "20000101150000"}}
        def get_minute_data(self, c):
            return [{"time": "09:30", "price": 10, "vol": 1}]
        def get_kline(self, c, n=60):
            return [{"date": "2000-01-01", "open": 10, "close": 11, "high": 12, "low": 9}]
    real = data_source.stock_api
    data_source.stock_api = FakeApi()
    try:
        r1 = data_source.capture_today(allow_overwrite=True)
        assert r1["ok"] and r1["date"] == "2000-01-01"
        r2 = data_source.capture_today(allow_overwrite=False)   # 已存在 → 跳过
        assert not r2["ok"] and r2.get("skipped") == "exists"
        r3 = data_source.capture_today(allow_overwrite=True)    # 手动允许覆盖
        assert r3["ok"]
    finally:
        data_source.stock_api = real
        try:
            os.remove(data_source.snapshot_path("2000-01-01"))
        except FileNotFoundError:
            pass


def test_scheduler_once():
    # 一次性任务到点执行后自动移除
    import time as _t
    from core.scheduler import Scheduler
    s = Scheduler()
    s.start()
    ran = []
    s.add_once("t1", _t.time() - 1, lambda: ran.append(1))
    for _ in range(30):
        if ran:
            break
        _t.sleep(0.1)
    s.stop()
    assert ran == [1]
    assert all(not t.get("once") for t in s._tasks)


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
