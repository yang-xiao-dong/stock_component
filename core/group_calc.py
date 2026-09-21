# -*- coding: utf-8 -*-
"""组合均分聚合计算（纯函数模块，无网络、无状态，便于单测）

均分（等权）规则：每只股票权重相同；某时点/某日缺数据的股票不参与，
其余股票在其内部重新均分。

- build_group_minute: 组内分时 —— 各股相对昨收涨跌幅的等权平均
- build_group_kline : 组内日K —— 等权指数（每日等权平均涨跌幅累乘，基准100），
                      并由平均 OHLC 涨跌幅还原出指数K线
- build_contribution: 贡献分解 —— 每只股票的权重与当日贡献点数
"""

BASE_INDEX = 100.0


def _weights_of(codes, weights=None):
    """归一化权重：默认均分；传入 weights={code: w} 时按比例归一"""
    if not codes:
        return {}
    if weights:
        total = float(sum(weights.get(c, 0) for c in codes)) or 1.0
        return {c: float(weights.get(c, 0)) / total for c in codes}
    n = len(codes)
    return {c: 1.0 / n for c in codes}


def build_group_minute(minute_map, prev_closes, weights=None):
    """组内分时聚合（单位：%，相对各自昨收）

    minute_map:  {code: [{"time": "09:30", "price": 12.3}, ...]}
    prev_closes: {code: 昨收价}
    返回 {"times": [...], "avg": [pct|None...],
          "stocks": [{"code", "data": [pct|None...]}]}
    """
    codes = [c for c in minute_map if prev_closes.get(c)]
    if not codes:
        return {"times": [], "avg": [], "stocks": []}

    series, times = {}, set()
    for code in codes:
        pts = {}
        for p in minute_map[code]:
            t = p["time"]
            pts[t] = (p["price"] / prev_closes[code] - 1.0) * 100.0
            times.add(t)
        series[code] = pts
    times = sorted(times)

    stocks = [{"code": c, "data": [series[c].get(t) for t in times]} for c in codes]
    avg = []
    for t in times:
        avail = [c for c in codes if t in series[c]]
        if not avail:
            avg.append(None)
            continue
        wa = _weights_of(avail, weights)
        avg.append(sum(wa[c] * series[c][t] for c in avail))
    return {"times": times, "avg": avg, "stocks": stocks}


def build_group_kline(kline_map, weights=None, base=BASE_INDEX, max_points=None):
    """组内日K聚合：等权指数 + 指数K线 + 各股归一指数线（基准=base）

    kline_map: {code: [{"date","open","close","high","low"}, ...]}（前复权）
    返回 {"dates": [...],
          "candles": [{"date","open","high","low","close"}...],
          "stocks": [{"code", "data": [index|None...]}]}
    """
    if not kline_map:
        return {"dates": [], "candles": [], "stocks": []}

    dates = sorted(set().union(*(set(b["date"] for b in bars) for bars in kline_map.values())))
    own = {code: {b["date"]: b for b in bars} for code, bars in kline_map.items()}

    prev_close = {code: None for code in kline_map}   # 昨收（窗口首日以当日开盘价代替）
    own_idx = {code: None for code in kline_map}      # 个股归一指数
    idx = base
    candles, lines = [], {code: [] for code in kline_map}

    for d in dates:
        day = {}
        for code in kline_map:
            b = own[code].get(d)
            if not b:
                lines[code].append(None)
                continue
            pc = prev_close[code] if prev_close[code] is not None else b["open"]
            day[code] = {
                "o": b["open"] / pc - 1.0, "h": b["high"] / pc - 1.0,
                "l": b["low"] / pc - 1.0, "c": b["close"] / pc - 1.0,
            }
            prev_close[code] = b["close"]
            # 个股线：首日同样以开盘价为基准应用当日收益，与指数蜡烛口径一致
            own_idx[code] = (base if own_idx[code] is None else own_idx[code]) * (1.0 + day[code]["c"])
            lines[code].append(own_idx[code])

        if day:
            wa = _weights_of(list(day), weights)
            mo = sum(wa[c] * day[c]["o"] for c in day)
            mh = sum(wa[c] * day[c]["h"] for c in day)
            ml = sum(wa[c] * day[c]["l"] for c in day)
            mc = sum(wa[c] * day[c]["c"] for c in day)
            mh = max(mh, mo, mc)  # 均分后钳回合法蜡烛
            ml = min(ml, mo, mc)
            prev_idx = idx
            idx = prev_idx * (1.0 + mc)
            candles.append({
                "date": d,
                "open": prev_idx * (1.0 + mo),
                "high": prev_idx * (1.0 + mh),
                "low": prev_idx * (1.0 + ml),
                "close": idx,
            })

    stocks = [{"code": c, "data": lines[c]} for c in kline_map]
    if max_points and len(dates) > max_points:
        cut = len(dates) - max_points
        dates = dates[cut:]
        candles = candles[len(candles) - max_points:]
        for s in stocks:
            s["data"] = s["data"][cut:]
    return {"dates": dates, "candles": candles, "stocks": stocks}


def build_contribution(realtime_map, weights=None):
    """贡献分解：权重均分时每只贡献 change_pct/N 个百分点

    realtime_map: {code: {"name","change_pct",...}}
    返回 (rows, total)：rows 按 contribution 降序，total=组合合计涨跌幅(%)
    """
    codes = [c for c in realtime_map
             if realtime_map[c] and realtime_map[c].get("change_pct") is not None]
    if not codes:
        return [], 0.0
    w = _weights_of(codes, weights)
    rows = []
    for c in codes:
        rt = realtime_map[c]
        rows.append({
            "code": c,
            "name": rt.get("name") or c,
            "weight": w[c] * 100.0,          # 百分比
            "change_pct": rt["change_pct"],
            "contribution": rt["change_pct"] * w[c],
        })
    rows.sort(key=lambda r: r["contribution"], reverse=True)
    total = sum(r["contribution"] for r in rows)
    return rows, total
