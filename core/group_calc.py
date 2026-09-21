# -*- coding: utf-8 -*-
"""组合均分聚合计算（纯函数模块，无网络、无状态，便于单测）

口径：比例是相对「原来的股本」（建仓本金）的相对度量，人民币金额才是绝对度量。
- 建仓：本金 C 均分 N 份（每份 C/N），于日K窗口首日以开盘价买入，之后持有不动
  （buy & hold，权重随价格漂移，不做每日再平衡）
- 绝对度量（¥）：组合市值、当日盈亏、累计盈亏、个股持仓市值/盈亏
- 相对度量（%）：一律相对建仓本金 C（如 累计盈亏¥ / 本金）

- build_group_minute : 分时 —— 各股当日盈亏(¥)细线 + 组合合计(¥)
- build_group_kline  : 日K —— 组合市值(¥)蜡烛 + 个股持市值(¥)细线 + 建仓份额
- build_contribution : 盈亏分解 —— 每只股票当日/累计盈亏(¥)、持仓市值(¥)

输出结构契约见 core/data_define/group.py，本模块经其构造返回值。
"""
from core.data_define import (
    ContributionRow,
    ContributionTotal,
    GroupKline,
    GroupMinute,
    KlineBar,
    StockSeries,
)


def default_shares(prev_closes, principal):
    """无建仓价时的近似份额：按昨收价把本金均分买入 {code: shares}"""
    if not prev_closes:
        return {}
    per = float(principal) / len(prev_closes)
    return {c: per / p for c, p in prev_closes.items() if p}


def calc_shares(kline_map, principal):
    """正式建仓份额：每只 C/N 于其首根K线的开盘价买入 {code: shares}"""
    if not kline_map:
        return {}
    per = float(principal) / len(kline_map)
    return {c: per / bars[0]["open"] for c, bars in kline_map.items() if bars}


def build_group_minute(minute_map, prev_closes, shares=None, principal=0.0):
    """组内分时（绝对 ¥）：各股当日盈亏 + 组合合计

    minute_map : {code: [{"time", "price"}, ...]}
    prev_closes: {code: 昨收}
    shares     : {code: 持仓份额}；缺省时按昨收均分近似（principal 必填）
    某时点缺数据的股票按可得股票合计（近似，停牌股贡献未知）。
    返回 {"times": [...], "total": [¥|None...], "stocks": [{"code", "data": [¥|None...]}]}
    """
    codes = [c for c in minute_map if prev_closes.get(c)]
    if not codes:
        return GroupMinute().to_dict()
    if not shares:
        shares = default_shares({c: prev_closes[c] for c in codes}, principal)

    series, times = {}, set()
    for code in codes:
        sh = shares.get(code, 0.0)
        pts = {}
        for p in minute_map[code]:
            t = p["time"]
            pts[t] = sh * (p["price"] - prev_closes[code])  # 当日盈亏(¥)
            times.add(t)
        series[code] = pts
    times = sorted(times)

    stocks = [StockSeries(code=c, data=[series[c].get(t) for t in times]) for c in codes]
    total = []
    for t in times:
        vals = [series[c][t] for c in codes if t in series[c]]
        total.append(sum(vals) if vals else None)
    return GroupMinute(times=times, total=total, stocks=stocks).to_dict()


def build_group_kline(kline_map, principal, max_points=None):
    """组内日K（绝对 ¥）：组合市值蜡烛 + 个股持市值线

    kline_map: {code: [{"date","open","close","high","low"}, ...]}（前复权）
    返回 {"principal", "dates", "candles":[{date,open,high,low,close}...单位¥],
          "stocks": [{"code", "data": [持市值¥|None...]}], "shares": {code: 份额}}
    """
    empty = GroupKline(principal=principal).to_dict()
    if not kline_map:
        return empty
    shares = calc_shares(kline_map, principal)
    dates = sorted(set().union(*(set(b["date"] for b in bars) for bars in kline_map.values())))
    own = {code: {b["date"]: b for b in bars} for code, bars in kline_map.items()}

    candles, lines = [], {code: [] for code in kline_map}
    for d in dates:
        present = [c for c in kline_map if d in own[c]]
        for c in kline_map:
            lines[c].append(shares[c] * own[c][d]["close"] if d in own[c] else None)
        if not present:
            continue
        candles.append(KlineBar(
            date=d,
            open=sum(shares[c] * own[c][d]["open"] for c in present),
            high=sum(shares[c] * own[c][d]["high"] for c in present),
            low=sum(shares[c] * own[c][d]["low"] for c in present),
            close=sum(shares[c] * own[c][d]["close"] for c in present),
        ))

    stocks = [StockSeries(code=c, data=lines[c]) for c in kline_map]
    if max_points and len(dates) > max_points:
        cut = len(dates) - max_points
        dates = dates[cut:]
        candles = candles[len(candles) - max_points:]
        for s in stocks:
            s.data = s.data[cut:]
    return GroupKline(principal=principal, dates=dates, candles=candles,
                      stocks=stocks, shares=shares).to_dict()


def build_contribution(realtime_map, shares=None, entry=None, principal=0.0):
    """盈亏分解（绝对 ¥ 为主）：当日/累计盈亏与持仓市值

    realtime_map: {code: rt}
    shares/entry: 建仓份额与建仓价（来自日K窗口首日）；缺省时按昨收均分近似
    当日盈亏，累计字段为 None（等待建仓数据）。
    返回 (rows, total)：rows 按 day_pnl 降序；total 含合计与相对本金百分比。
    """
    codes = [c for c in realtime_map
             if realtime_map[c] and realtime_map[c].get("change_pct") is not None]
    codes = [c for c in codes if realtime_map[c].get("price") is not None]
    if not codes:
        return [], None
    if not shares:
        prev = {c: realtime_map[c].get("prev_close") for c in codes}
        prev = {c: p for c, p in prev.items() if p}
        shares = default_shares(prev, principal)
        entry = {c: prev[c] for c in shares}

    rows = []
    for c in codes:
        rt = realtime_map[c]
        sh = shares.get(c)
        if not sh:
            continue
        prev = rt.get("prev_close")
        ent = (entry or {}).get(c)
        rows.append(ContributionRow(
            code=c,
            name=rt.get("name") or c,
            change_pct=rt["change_pct"],
            day_pnl=sh * (rt["price"] - prev) if prev is not None else None,
            value=sh * rt["price"],                            # 持仓市值(¥)
            total_pnl=sh * (rt["price"] - ent) if ent else None,  # 累计盈亏(¥)
        ))
    if not rows:
        return [], None
    rows.sort(key=lambda r: (r.day_pnl or 0.0), reverse=True)

    have_total = all(r.total_pnl is not None for r in rows)
    total_pnl = sum(r.total_pnl for r in rows) if have_total else None
    total = ContributionTotal(
        principal=principal,
        day_pnl=sum(r.day_pnl or 0.0 for r in rows),
        total_value=sum(r.value for r in rows),
        total_pnl=total_pnl,
        total_pct=(total_pnl / principal * 100.0
                   if total_pnl is not None and principal else None),
        up=sum(1 for r in rows if r.change_pct > 0),
        down=sum(1 for r in rows if r.change_pct < 0),
    )
    return [r.to_dict() for r in rows], total.to_dict()
