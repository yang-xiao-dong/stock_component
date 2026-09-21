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
from datetime import datetime

from config import AUTO_SNAPSHOT, KLINE_DAYS, STOCKS
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


# ---------- 收盘自动保存 ----------

def should_auto_save(now, existing_dates, last_kline_date):
    """自动保存判定（纯函数）：交易日收盘后、当日尚无快照、当日确有行情"""
    if now.weekday() >= 5:            # 周末
        return False
    if (now.hour, now.minute) < (AUTO_SNAPSHOT["hour"], AUTO_SNAPSHOT["minute"]):
        return False                  # 未到收盘缓冲时刻
    today = now.strftime("%Y-%m-%d")
    if today in existing_dates:       # 已保存：避免重复保存与覆盖
        return False
    if last_kline_date != today:      # 节假日（当日无新K线）
        return False
    return True


def auto_save_tick():
    """定时任务入口：收盘后自动保存当日快照（幂等）"""
    try:
        probe = stock_api.get_kline(STOCKS[0]["code"], 3)
        last_date = probe[-1]["date"] if probe else None
        if not should_auto_save(datetime.now(), set(list_snapshots()), last_date):
            return
        r = capture_today()
        if r.get("ok"):
            print(f"[快照] 收盘自动保存 {r['date']} -> {r['path']}", flush=True)
    except Exception as e:
        print(f"[快照] 自动保存失败: {e}", flush=True)


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
