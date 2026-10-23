# -*- coding: utf-8 -*-
"""PE对比组件：参照公司（高通）+ 对比组历史PE折线，评价当前PE高低。

数据流：实时行情取当前PE-TTM → 收盘价序列按当前EPS折算历史PE → 分位数统计。
单独调试（项目根目录下运行）：python -m components.pe_compare.component
"""
import threading
import time
from datetime import datetime

from components.base import Component, assemble
from config import PE_COMPARE, REFRESH
from core import data_source, pe_calc
from core.data_define import PeCompareBoard, PeSeries


class PeCompareApi:
    def __init__(self, scheduler=None):
        self._lock = threading.Lock()
        self._board = None
        self._source_key = None
        self._next_scan = 0
        self._close_cache = {}   # code -> (cached_at, closes)
        if scheduler:
            scheduler.add("pe_compare.scan", min(5, PE_COMPARE["refresh_seconds"]),
                          self._refresh, immediate=True)

    @staticmethod
    def _mode_key():
        mode = data_source.get_mode()
        return mode["mode"], mode["date"] or datetime.now().date().isoformat()

    def _closes_for(self, code):
        """收盘序列（带 kline 级缓存）"""
        cached_at, closes = self._close_cache.get(code, (0, None))
        if closes and time.monotonic() - cached_at < REFRESH["kline"]:
            return closes
        closes = data_source.get_close_series(code, PE_COMPARE["kline_days"])
        if closes:
            self._close_cache[code] = (time.monotonic(), closes)
        return closes

    def _series_for(self, stock, quotes, is_reference=False):
        quote = quotes.get(stock["code"])
        series = pe_calc.build_pe_series(stock, quote, self._closes_for(stock["code"]))
        series["is_reference"] = is_reference
        return series

    def _refresh(self):
        key = self._mode_key()
        if key == self._source_key and time.monotonic() < self._next_scan:
            return
        if key != self._source_key:
            self._close_cache.clear()
        ref_cfg = PE_COMPARE["reference"]
        all_stocks = [ref_cfg] + list(PE_COMPARE["peers"])
        try:
            quotes = data_source.get_realtime_batch([s["code"] for s in all_stocks])
            reference = self._series_for(ref_cfg, quotes, is_reference=True)
            peers = [self._series_for(s, quotes) for s in PE_COMPARE["peers"]]
            ready = sum(1 for p in peers if p["points"])
            message = (f"{ready}/{len(peers)} 只有历史序列 · 参照 {reference['name']}"
                       + (f" PE {reference['pe_now']:.1f}" if reference.get("pe_now") else " 暂无PE"))
            board = PeCompareBoard(mode=key[0], date=key[1], status="ready",
                                   updated_at=datetime.now().isoformat(timespec="seconds"),
                                   message=message, window_days=PE_COMPARE["kline_days"],
                                   reference=PeSeries.from_dict(reference),
                                   peers=[PeSeries.from_dict(p) for p in peers])
        except Exception:
            board = PeCompareBoard(mode=key[0], date=key[1], status="error",
                                   updated_at=datetime.now().isoformat(timespec="seconds"),
                                   message="PE数据获取失败，稍后自动重试", window_days=PE_COMPARE["kline_days"])
        # 切换快照期间完成的旧请求不污染当前模式
        if key != self._mode_key():
            self._close_cache.clear()
            return
        with self._lock:
            self._board = board.to_dict()
            self._source_key = key
            self._next_scan = time.monotonic() + PE_COMPARE["refresh_seconds"]

    def get_pe_compare(self):
        key = self._mode_key()
        with self._lock:
            if self._board is not None and key == self._source_key:
                return self._board
        return PeCompareBoard(mode=key[0], date=key[1], status="loading",
                               message="正在获取PE数据…", window_days=PE_COMPARE["kline_days"]).to_dict()


class PeCompareComponent(Component):
    id = "pe_compare"
    title = "PE对比"
    embed_height = 500

    def create_api(self, scheduler=None):
        return PeCompareApi(scheduler=scheduler)


if __name__ == "__main__":
    assemble([PeCompareComponent()])
