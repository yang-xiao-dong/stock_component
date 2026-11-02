# -*- coding: utf-8 -*-
"""组件唯一数据入口：在线自动入库，历史回放严格离线。存储实现封装在 core/history。"""
import os
import json
import logging
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import AUTO_SNAPSHOT, KLINE_DAYS
from core import stock_api, vol_calc
from core.data_define.quote import RealtimeQuote
from core.data_define.snapshot import SNAPSHOT_DIR
from core.data_define.history import DataModePreference
from core.runtime_paths import user_data_path
from core.history.store import HistoryStore
from core.history.service import HistoryService
from core.history.legacy import import_directories, import_snapshot

_service = None
_init_lock = threading.Lock()
_mode_lock = threading.Lock()
logger = logging.getLogger(__name__)


def initialize():
    global _service
    with _init_lock:
        if _service is None:
            store = HistoryStore(user_data_path("data", "market.sqlite3"))
            directories = [SNAPSHOT_DIR]
            if os.environ.get("LOCALAPPDATA"):
                directories.append(Path(os.environ["LOCALAPPDATA"]) / "StockWidget" / "data" / "snapshots")
            import_directories(store, directories)
            service = HistoryService(store, stock_api)
            try:
                preference = DataModePreference.from_dict(json.loads(
                    store.path.with_name("history_mode.json").read_text(encoding="utf-8")))
                if preference and preference.mode == "offline":
                    if not service.set_mode("offline", preference.date):
                        logger.warning("已保存的离线日期不可用：%s", preference.date)
            except (OSError, ValueError, TypeError):
                pass
            _service = service
    return _service


def get_mode():
    return _service.mode() if _service else {"mode": "live", "date": None}


def context_key():
    """包括切换代数，同一日期重新加载也会使组件缓存失效。"""
    return _service.context_key() if _service else (0, "live", None)


def get_config(name, default):
    return _service.config(name, default) if _service else deepcopy(default)


def is_offline():
    return get_mode()["mode"] == "offline"


def set_mode(mode, date=None):
    if mode not in ("live", "offline"):
        return False
    if mode == "live" and _service is None:
        return True
    service = initialize()
    if mode == "offline" and date and (os.path.isabs(str(date)) or str(date).endswith(".json")):
        try:
            date = import_snapshot(service.store, date)
        except (OSError, ValueError, TypeError, KeyError):
            return False
    with _mode_lock:
        if not service.set_mode(mode, date):
            return False
        target = service.store.path.with_name("history_mode.json")
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(prefix="history-mode-", suffix=".tmp", dir=target.parent)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(DataModePreference(**service.mode()).to_dict(), stream, ensure_ascii=False)
            os.replace(temporary, target)
        except OSError as exc:
            logger.warning("数据模式偏好保存失败（当前切换已生效）：%s", exc)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return True


def list_snapshots():
    """兼容原窗口接口；现在返回数据库已有数据的交易日。"""
    return initialize().store.dates()


def get_history_status():
    return initialize().status()


def capture_today(allow_overwrite=True):
    service = initialize()
    if not allow_overwrite:
        now = datetime.now(timezone(timedelta(hours=8)))
        context = service.store.replay(now.date().isoformat())
        if context and not context.missing and context.saved_at:
            saved = datetime.fromisoformat(context.saved_at).astimezone(now.tzinfo)
            if saved.date() == now.date() and (saved.hour, saved.minute) >= (AUTO_SNAPSHOT["hour"], AUTO_SNAPSHOT["minute"]):
                return {"ok": False, "skipped": "exists", "date": context.date}
    return service.collect(force=True)


def collect_history():
    return initialize().collect()


def should_auto_save(now):
    return now.weekday() < 5 and (now.hour, now.minute) >= (AUTO_SNAPSHOT["hour"], AUTO_SNAPSHOT["minute"])


def _fire_time(now, initial=True):
    today_at = now.replace(hour=AUTO_SNAPSHOT["hour"], minute=AUTO_SNAPSHOT["minute"], second=0, microsecond=0)
    if initial and now.weekday() < 5 and now >= today_at:
        return now
    day = today_at
    if now >= day:
        day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def arm_auto_save(scheduler, initial=True):
    now = datetime.now(timezone(timedelta(hours=8)))
    scheduler.add_once("app.auto_snapshot", _fire_time(now, initial), lambda: _auto_save_fired(scheduler))


def _auto_save_fired(scheduler):
    try:
        if not is_offline():
            capture_today(allow_overwrite=False)
    finally:
        arm_auto_save(scheduler, initial=False)


def get_realtime(code):
    quote = get_realtime_batch([code]).get(code)
    if quote or not is_offline():
        return quote
    return _replay_quote_from_history(code)


def _replay_quote_from_history(code):
    """离线回放无当日行情快照时，由库内当日事实还原可显示行情。

    行情快照当日不采集即永久缺失，估值与成交额在库内无处可取，保持缺失
    （前端显示 --，不用其他日期补）。今开/最高/最低/收盘与昨收基准来自同日
    及前一交易日的日K行；成交量取当日分时末点累计（库内 minute.vol 统一为
    手，外部源为股时在入库处折算）。仅个股视图的单点查询走此回退，批量接口
    保持原样，组合/PE/分析组件的回放口径不受影响。
    """
    service = initialize()
    date = get_mode()["date"]
    bars = service.series("kline", code) or []
    index = next((i for i, bar in enumerate(bars) if bar.get("date") == date), None)
    if not index or not all(bars[index].get(key) for key in ("open", "close")) \
            or not bars[index - 1].get("close"):
        return None
    bar, previous = bars[index], bars[index - 1]
    minute = service.series("minute", code) or []
    change = bar["close"] - previous["close"]
    ratio = vol_calc.volume_ratio(minute, service.minute_day_totals(code, date))
    return RealtimeQuote(
        name=_stock_name(code), code=code,
        price=bar["close"], prev_close=previous["close"],
        open=bar["open"], high=bar.get("high"), low=bar.get("low"),
        time=date.replace("-", "") + "150000",
        change=round(change, 2), change_pct=round(change / previous["close"] * 100, 2),
        volume=minute[-1].get("vol") if minute else None,
        liang_ratio=round(ratio, 2) if ratio else None,
    ).to_dict()


def _stock_name(code):
    for stock in get_config("STOCKS", []):
        if stock.get("code") == code:
            return stock.get("name")
    return None


def get_realtime_batch(codes):
    return initialize().quotes(list(codes))


def get_minute_data(code):
    return initialize().series("minute", code) or None


def get_kline(code, count=None):
    count = count if count is not None else get_config("KLINE_DAYS", KLINE_DAYS)
    return initialize().series("kline", code, count) or None


def get_close_series(code, count=250):
    return initialize().series("close", code, count) or None


def get_prev_close(code):
    """昨收基准：在线取行情快照；离线回放无快照时取收盘序列的前一交易日。

    历史日期的行情快照不可再生（当日不采即永久缺失），分时图基准改由
    已回补的收盘序列提供——救援入库的历史分时因此可正常绘制。
    """
    quote = get_realtime(code)
    if quote and quote.get("prev_close"):
        return quote["prev_close"]
    if is_offline():
        closes = get_close_series(code, 2) or []
        if len(closes) >= 2:
            return closes[-2]["close"]
    return None
