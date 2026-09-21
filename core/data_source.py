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

from config import KLINE_DAYS, STOCKS
from core import stock_api
from core.data_define import MarketSnapshot, load_snapshot, save_snapshot
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


def capture_today():
    """抓取当前整组数据（实时+分时+日K）并存为快照，返回 {ok, date, path}"""
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
    path = save_snapshot(snap)
    return {"ok": True, "date": snap.date, "path": path}


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
            return [p.to_dict() for p in pts]
    return stock_api.get_minute_data(code)


def get_kline(code, count=KLINE_DAYS):
    if is_offline():
        with _lock:
            bars = _snapshot.kline.get(code) or []
            return [b.to_dict() for b in bars]
    return stock_api.get_kline(code, count)
