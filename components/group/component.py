# -*- coding: utf-8 -*-
"""组件2：股票组合视图 — 本金均分建仓，¥绝对度量（市值/当日/累计盈亏）+ 盈亏分解

口径：比例相对建仓本金，人民币金额为绝对度量（见 core/group_calc.py）。
单独调试（项目根目录下运行）：python -m components.group.component
"""
import threading
from concurrent.futures import ThreadPoolExecutor

from components.base import Component, assemble
from config import GROUP_NAME, KLINE_DAYS, PRINCIPAL, REFRESH, STOCKS
from core import data_source, group_calc

FETCH_WORKERS = 4  # 并发抓取分时/日K的线程数


class GroupApi:
    """组合视图的前端接口（窗口控制由装配层统一提供）"""

    def __init__(self, scheduler=None):
        self._lock = threading.Lock()
        self._realtime = {}       # {code: rt}
        self._minute = None       # build_group_minute 结果（¥）
        self._kline = None        # build_group_kline 结果（¥）
        self._shares = None       # 建仓份额 {code: shares}（日K窗口首日开盘价均分买入）
        self._entry = None        # 建仓价 {code: price}

        self.refresh_realtime()
        if scheduler:
            scheduler.add("group.realtime", REFRESH["realtime"], self.refresh_realtime)
            scheduler.add("group.minute", REFRESH["minute"], self.refresh_minute)
            # 日K立即预热：概览的总值/盈亏依赖日K首日建仓份额，晚加载会导致数字跳变
            scheduler.add("group.kline", REFRESH["kline"], self.refresh_kline, immediate=True)

    # ---------- 数据抓取 ----------
    #
    # 一致性约定（重算/重启/重载结果一致的前提）：
    # 组合的每个版本（日K、分时、份额、建仓价）都只由「同一轮抓取的完整数据」
    # 原子地构建。一轮里任何一只失败 → 整轮作废、沿用上一版完整结果——绝不把
    # 不同轮次（甚至不同复权源：fqkline前复权 / 备用端点不复权）的数据按股票
    # 混进同一次计算，否则建仓价与份额会随混入比例漂移，数值前后对不上。

    def refresh_realtime(self):
        data = data_source.get_realtime_batch([s["code"] for s in STOCKS])
        if data:
            with self._lock:
                self._realtime = data

    def refresh_minute(self):
        codes = [s["code"] for s in STOCKS]
        mode_key = dict(data_source.get_mode())
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            fetched = dict(zip(codes, ex.map(data_source.get_minute_data, codes)))
        # 整轮原子替换：缺一只合计线就会被低估，宁可沿用上一版完整分时
        if any(not fetched.get(c) for c in codes) or data_source.get_mode() != mode_key:
            return
        minute_map = {c: fetched[c] for c in codes}
        with self._lock:
            prev = {c: (self._realtime.get(c) or {}).get("prev_close") for c in minute_map}
            shares = dict(self._shares) if self._shares else None
        prev = {c: p for c, p in prev.items() if p}
        if not prev:
            return
        minute = group_calc.build_group_minute(minute_map, prev, shares, PRINCIPAL)
        with self._lock:
            self._minute = minute

    def refresh_kline(self):
        codes = [s["code"] for s in STOCKS]
        mode_key = dict(data_source.get_mode())
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            fetched = dict(zip(codes, ex.map(lambda c: data_source.get_kline(c, KLINE_DAYS), codes)))
        # 整轮原子替换：缺一只就整轮作废（部分数据会把本金错分给少数股票，
        # 新旧/异源数据混用会让份额漂移），沿用上一版完整结果
        if any(not fetched.get(c) for c in codes) or data_source.get_mode() != mode_key:
            return
        kmap = {c: fetched[c] for c in codes}
        data = group_calc.build_group_kline(kmap, PRINCIPAL, max_points=KLINE_DAYS)
        with self._lock:
            self._kline = data
            self._shares = data["shares"]
            self._entry = {c: kmap[c][0]["open"] for c in codes}

    # ---------- JS 接口 ----------

    def get_group(self):
        """组合元信息"""
        return {"name": GROUP_NAME, "mode": "equal", "count": len(STOCKS),
                "principal": PRINCIPAL, "stocks": STOCKS}

    def get_group_realtime(self):
        """组合实时概览：当日/累计盈亏(¥)、总市值、个股盈亏分解"""
        with self._lock:
            rt = dict(self._realtime)
            shares = dict(self._shares) if self._shares else None
            entry = dict(self._entry) if self._entry else None
        rows, total = group_calc.build_contribution(rt, shares, entry, PRINCIPAL)
        if total is None:
            return None
        latest = ""
        for v in rt.values():
            if v and v.get("time") and v["time"] > latest:
                latest = v["time"]
        out = dict(total)
        out["time"] = latest
        out["stocks"] = rows
        return out

    def get_group_minute(self):
        """组内分时（各股当日盈亏¥ + 组合合计¥）"""
        with self._lock:
            data = self._minute
        if not data:
            self.refresh_minute()
            with self._lock:
                data = self._minute
        return data

    def get_group_kline(self):
        """组内日K（组合市值¥蜡烛 + 个股持市值¥线）"""
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
    embed_height = 510

    def create_api(self, scheduler=None):
        return GroupApi(scheduler=scheduler)


if __name__ == "__main__":
    assemble([GroupComponent()])
