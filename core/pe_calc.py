# -*- coding: utf-8 -*-
"""PE 历史折算与统计（纯函数，无网络；契约见 core/data_define/pe.py）。

口径：历史 PE 按当前 EPS-TTM 折算 —— pe(t) = close(t) × pe_now / close_now。
两个财报日之间准确；跨财报季线上会出现台阶（本折算法不含该台阶，界面注明）。
"""
from core.data_define import PePoint, PeSeries


def pe_history(closes, pe_now, last_close):
    """由收盘价序列折算历史PE。

    closes: [{"date","close"}, ...]（get_close_series 输出，最后一根为最新）
    pe_now: 当前PE-TTM；last_close: 折算锚点价（与 pe_now 同一时刻的收盘/最新价）
    亏损（pe_now≤0）或锚点缺失返回 []。
    """
    if not closes or not pe_now or pe_now <= 0 or not last_close or last_close <= 0:
        return []
    k = pe_now / last_close
    return [PePoint(date=c["date"], pe=round(c["close"] * k, 2)).to_dict()
            for c in closes if c.get("date") and isinstance(c.get("close"), (int, float))]


def pe_percentile(points):
    """当前PE（序列最后一点）在窗口内的历史分位（0-100）。

    定义：窗口内 pe ≤ 当前值 的交易日占比。不足 5 个有效点返回 None。
    """
    values = sorted(p["pe"] for p in points if isinstance(p.get("pe"), (int, float)) and p["pe"] > 0)
    if len(values) < 5 or not points:
        return None
    current = points[-1].get("pe")
    if not isinstance(current, (int, float)) or current <= 0:
        return None
    below = sum(1 for v in values if v <= current)
    return round(100.0 * below / len(values), 1)


def pe_median(points):
    """窗口PE中位数；不足 5 个有效点返回 None"""
    values = sorted(p["pe"] for p in points if isinstance(p.get("pe"), (int, float)) and p["pe"] > 0)
    if len(values) < 5:
        return None
    mid = len(values) // 2
    med = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
    return round(med, 2)


def build_pe_series(stock, quote, closes):
    """组装单只股票的 PeSeries（纯函数）。

    stock: {"code","name"}；quote: 实时行情 dict（含 pe_ttm）；closes: 收盘价序列。
    锚点用行情最新价（盘中PE与收盘序列的最后一根自然衔接）。
    """
    code, name = stock["code"], stock.get("name") or stock["code"]
    pe_now = (quote or {}).get("pe_ttm")
    series = PeSeries(code=code, name=name, pe_now=pe_now)
    if not quote:
        series.note = "暂无行情"
        return series.to_dict()
    if not pe_now or pe_now <= 0:
        series.note = "亏损或无PE"
        return series.to_dict()
    last_close = quote.get("price") or (closes[-1]["close"] if closes else None)
    points = pe_history(closes, pe_now, last_close)
    if not points:
        series.note = "收盘序列获取失败"
        return series.to_dict()
    series.points = [PePoint.from_dict(p) for p in points]
    series.percentile = pe_percentile(points)
    series.median = pe_median(points)
    return series.to_dict()
