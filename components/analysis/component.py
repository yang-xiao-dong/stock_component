# -*- coding: utf-8 -*-
"""独立判断组件：仅通过现有数据源和调度器接入应用。"""
import threading
import time
from datetime import datetime

from components.base import Component, assemble
from config import ANALYSIS, REFRESH, STOCKS
from core import data_source
from core.data_define import AnalysisBoard, LongTermAssessment, ShortTermAssessment
from .long_term import evaluate_long_term
from .short_term import evaluate_washout


class AnalysisApi:
    def __init__(self, scheduler=None):
        self._lock = threading.Lock()
        self._board = None
        self._source_key = None
        self._next_scan = 0
        self._kline_cache = {}
        if scheduler:
            scheduler.add("analysis.scan", min(5, ANALYSIS["refresh_seconds"]),
                          self._refresh, immediate=True)

    @staticmethod
    def _mode_key():
        mode = data_source.get_mode()
        return mode["mode"], mode["date"] or datetime.now().date().isoformat()

    def _refresh(self):
        key = self._mode_key()
        if key == self._source_key and time.monotonic() < self._next_scan:
            return
        if key != self._source_key:
            self._kline_cache.clear()
        try:
            quotes = data_source.get_realtime_batch([s["code"] for s in STOCKS])
            long_items, short_items = [], []
            for stock in STOCKS:
                code = stock["code"]
                quote, bars = None, None
                try:
                    quote = quotes.get(code)
                    if not quote:
                        long_items.append(LongTermAssessment(code=code, name=stock["name"],
                                                            status="insufficient", reason="暂无实时行情").to_dict())
                        short_items.append(ShortTermAssessment(code=code, name=stock["name"],
                                                               status="insufficient", reason="暂无实时行情").to_dict())
                        continue
                    cached_at, bars = self._kline_cache.get(code, (0, None))
                    if not bars or time.monotonic() - cached_at >= REFRESH["kline"]:
                        bars = data_source.get_kline(code, ANALYSIS["kline_days"])
                        if bars:
                            self._kline_cache[code] = (time.monotonic(), bars)
                    long_items.append(evaluate_long_term(stock, quote, bars, ANALYSIS["long_term"], key[1]))
                except Exception:
                    long_items.append(LongTermAssessment(code=code, name=stock["name"], status="insufficient",
                                                         reason="日K获取失败，等待下次扫描").to_dict())
                try:
                    minute = data_source.get_minute_data(code)
                    short_items.append(evaluate_washout(stock, quote, minute, bars, ANALYSIS["short_term"],
                                                        analysis_date=key[1],
                                                        now=datetime.now() if key[0] == "live" else None))
                except Exception:
                    short_items.append(ShortTermAssessment(code=code, name=stock["name"], status="insufficient",
                                                           reason="分时获取失败，等待下次扫描").to_dict())
            board = AnalysisBoard(mode=key[0], date=key[1], status="ready",
                               updated_at=datetime.now().isoformat(timespec="seconds"),
                               message="价格趋势与形态判断", long_term=long_items, short_term=short_items)
        except Exception:
            board = AnalysisBoard(mode=key[0], date=key[1], status="error",
                               updated_at=datetime.now().isoformat(timespec="seconds"),
                               message="判断数据获取失败，稍后自动重试", long_term=[], short_term=[])
        # 切换快照期间完成的旧请求不污染当前模式，也不保留旧信号。
        if key != self._mode_key():
            self._kline_cache.clear()
            return
        with self._lock:
            self._board = board.to_dict()
            self._source_key = key
            self._next_scan = time.monotonic() + ANALYSIS["refresh_seconds"]

    def get_analysis(self):
        key = self._mode_key()
        with self._lock:
            if self._board is not None and key == self._source_key:
                return self._board
        return AnalysisBoard(mode=key[0], date=key[1], status="loading",
                             message="正在分析长短线数据…", long_term=[], short_term=[]).to_dict()


class AnalysisComponent(Component):
    id = "analysis"
    title = "长短线判断"
    embed_height = 350

    def create_api(self, scheduler=None):
        return AnalysisApi(scheduler=scheduler)


if __name__ == "__main__":
    assemble([AnalysisComponent()])
