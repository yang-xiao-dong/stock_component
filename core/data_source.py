# -*- coding: utf-8 -*-
"""行情数据源：在线（腾讯实时）与离线（本地收盘快照）的统一取数入口。

- 组件一律通过本模块取数，不直接依赖 stock_api，模式对组件透明
- 模式切换由窗口级 API（components/base.py 的 AppApi）触发，
  切换后前端重载组件页面即可整体生效
- 快照结构契约见 core/data_define/snapshot.py
"""
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dataclasses import replace

from config import AUTO_SNAPSHOT, KLINE_DAYS, STOCKS
from core import stock_api
from core.data_define import MarketSnapshot, load_snapshot, save_snapshot, snapshot_path
from core.data_define.snapshot import SNAPSHOT_DIR

FETCH_WORKERS = 4

_lock = threading.Lock()
_snapshot = None   # MarketSnapshot | None（离线模式持有）
_mode = "live"     # live | offline
_date = None       # 离线模式对应的快照日期


# ---------- 模式管理 ----------

def get_mode():
    with _lock:
        return {"mode": _mode, "date": _date}


def is_offline():
    with _lock:
        return _mode == "offline" and _snapshot is not None


def set_mode(mode, date=None):
    """切换数据模式；offline 需给快照日期或完整文件路径，成功返回 True"""
    global _snapshot, _mode, _date
    mode = str(mode)
    with _lock:
        if mode == "live":
            _snapshot, _mode, _date = None, "live", None
            return True
        if mode != "offline":
            return False
        try:
            snap = load_snapshot(date)
        except (FileNotFoundError, OSError):
            return False
        if snap is None:
            return False
        _snapshot, _mode, _date = snap, "offline", snap.date
        return True


def list_snapshots():
    """已保存的快照日期列表（yyyy-mm-dd 升序）"""
    try:
        return sorted(f[:-5] for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json"))
    except FileNotFoundError:
        return []


def capture_today(allow_overwrite=True):
    """抓取当前整组数据（实时+分时+日K）并存为快照，返回 {ok, date, path}
    allow_overwrite=False 时，目标日期快照已存在则跳过（自动保存防覆盖用）"""
    codes = [s["code"] for s in STOCKS]
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
        minute = dict(zip(codes, ex.map(stock_api.get_minute_data, codes)))
        kline = dict(zip(codes, ex.map(lambda c: stock_api.get_kline(c, KLINE_DAYS), codes)))
    realtime = stock_api.get_realtime_batch(codes)
    if not realtime:
        return {"ok": False, "error": "实时行情获取失败，请检查网络"}
    snap = MarketSnapshot.capture(
        realtime,
        {c: v for c, v in minute.items() if v},
        {c: v for c, v in kline.items() if v},
    )
    path = snapshot_path(snap.date)
    if not allow_overwrite and os.path.exists(path):
        return {"ok": False, "skipped": "exists", "date": snap.date}
    save_snapshot(snap)
    return {"ok": True, "date": snap.date, "path": path}


# ---------- 收盘自动保存（只按时间判断，到点主动触发） ----------

def should_auto_save(now):
    """时间判定（纯函数）：周一至周五且已过收盘缓冲时刻"""
    if now.weekday() >= 5:
        return False
    return (now.hour, now.minute) >= (AUTO_SNAPSHOT["hour"], AUTO_SNAPSHOT["minute"])


def _fire_time(now):
    """下一个触发时刻（纯函数）：交易日已过收盘时刻 → 立即；否则下一个工作日的收盘时刻"""
    today_at = now.replace(hour=AUTO_SNAPSHOT["hour"], minute=AUTO_SNAPSHOT["minute"],
                           second=0, microsecond=0)
    if now.weekday() < 5 and now >= today_at:
        return now
    d = today_at
    if now >= d:
        d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def arm_auto_save(scheduler):
    """布防收盘自动保存：到点主动触发一次，完成后再自动布防下一个交易日"""
    scheduler.add_once("app.auto_snapshot", _fire_time(datetime.now()),
                       lambda: _auto_save_fired(scheduler))


def _auto_save_fired(scheduler):
    try:
        if should_auto_save(datetime.now()):
            r = capture_today(allow_overwrite=False)
            if r.get("ok"):
                print(f"[快照] 收盘自动保存 {r['date']} -> {r['path']}", flush=True)
    except Exception as e:
        print(f"[快照] 自动保存失败: {e}", flush=True)
    finally:
        arm_auto_save(scheduler)


# ---------- 取数入口（组件统一从这里拿数据） ----------

def get_realtime(code):
    if is_offline():
        with _lock:
            q = _snapshot.realtime.get(code)
            return q.to_dict() if q else None
    return stock_api.get_realtime(code)


def get_realtime_batch(codes):
    if is_offline():
        with _lock:
            return {c: q.to_dict() for c, q in _snapshot.realtime.items() if c in codes}
    return stock_api.get_realtime_batch(codes)


def get_minute_data(code):
    if is_offline():
        with _lock:
            pts = _snapshot.minute.get(code) or []
            return [replace(p, date=p.date or _snapshot.date).to_dict() for p in pts]
    return stock_api.get_minute_data(code)


def get_kline(code, count=KLINE_DAYS):
    if is_offline():
        with _lock:
            bars = _snapshot.kline.get(code) or []
            return [b.to_dict() for b in bars]
    return stock_api.get_kline(code, count)
