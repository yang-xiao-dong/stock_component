# -*- coding: utf-8 -*-
"""组件2：股票组合视图 — 组内股票均分(等权)的分时/日K聚合 + 贡献分解

单独调试（项目根目录下运行）：python -m components.group.component
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from components.base import Component, assemble
from config import KLINE_DAYS, REFRESH, GROUP_NAME, STOCKS
from core import group_calc, stock_api

FETCH_WORKERS = 4  # 并发抓取分时/日K的线程数


class GroupApi:
    """组合视图的前端接口（窗口控制由装配层统一提供）"""

    def __init__(self, scheduler=None):
        self._lock = threading.Lock()
        self._realtime = {}   # {code: rt}
        self._minute = None   # build_group_minute 结果
        self._kline = None    # build_group_kline 结果

        self.refresh_realtime()
        if scheduler:
            scheduler.add("group.realtime", REFRESH["realtime"], self.refresh_realtime)
            scheduler.add("group.minute", REFRESH["minute"], self.refresh_minute)
            scheduler.add("group.kline", REFRESH["kline"], self.refresh_kline)

    # ---------- 数据抓取 ----------

    def refresh_realtime(self):
        data = stock_api.get_realtime_batch([s["code"] for s in STOCKS])
        if data:
            with self._lock:
                self._realtime = data

    def refresh_minute(self):
        codes = [s["code"] for s in STOCKS]
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            fetched = dict(zip(codes, ex.map(stock_api.get_minute_data, codes)))
        minute_map = {c: v for c, v in fetched.items() if v}
        if not minute_map:
            return
        with self._lock:
            prev = {c: (self._realtime.get(c) or {}).get("prev_close") for c in minute_map}
            self._minute = group_calc.build_group_minute(minute_map, prev)

    def refresh_kline(self):
        codes = [s["code"] for s in STOCKS]
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            fetched = dict(zip(codes, ex.map(lambda c: stock_api.get_kline(c, KLINE_DAYS), codes)))
        kmap = {c: v for c, v in fetched.items() if v}
        if not kmap:
            return
        with self._lock:
            self._kline = group_calc.build_group_kline(kmap, max_points=KLINE_DAYS)

    # ---------- JS 接口 ----------

    def get_group(self):
        """组合元信息"""
        return {"name": GROUP_NAME, "mode": "equal", "count": len(STOCKS), "stocks": STOCKS}

    def get_group_realtime(self):
        """组合实时概览：均分合计涨跌幅 + 涨跌家数 + 贡献分解"""
        with self._lock:
            rt = dict(self._realtime)
        rows, total = group_calc.build_contribution(rt)
        up = sum(1 for r in rows if r["change_pct"] > 0)
        down = sum(1 for r in rows if r["change_pct"] < 0)
        latest = ""
        for v in rt.values():
            if v and v.get("time") and v["time"] > latest:
                latest = v["time"]
        return {
            "time": latest,
            "change_pct": total,
            "up": up, "down": down, "flat": len(rows) - up - down,
            "stocks": rows,
        }

    def get_group_minute(self):
        """组内分时（均分平均%，含个股线）"""
        with self._lock:
            data = self._minute
        if not data:
            self.refresh_minute()
            with self._lock:
                data = self._minute
        return data

    def get_group_kline(self):
        """组内日K（均分指数蜡烛 + 个股归一线）"""
        with self._lock:
            data = self._kline
        if not data:
            self.refresh_kline()
            with self._lock:
                data = self._kline
        return data


class GroupComponent(Component):
    id = "group"
    title = f"{GROUP_NAME} · 均分"

    def create_api(self, scheduler=None):
        return GroupApi(scheduler=scheduler)


if __name__ == "__main__":
    assemble([GroupComponent()])
