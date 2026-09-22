# -*- coding: utf-8 -*-
"""疑似洗盘的价格形态筛选：纯函数，不判断资金意图、不使用组合收益率。"""
import math
from datetime import datetime

from core.data_define import ShortTermAssessment


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _minute_index(value):
    """支持腾讯 HHMM 与契约 HH:MM，映射为扣除午休的交易分钟。"""
    text = str(value).replace(":", "")
    if len(text) != 4 or not text.isdigit():
        return None
    hour, minute = int(text[:2]), int(text[2:])
    if minute >= 60:
        return None
    clock = hour * 60 + minute
    if 570 <= clock <= 690:
        return clock - 570
    if 780 <= clock <= 900:
        return clock - 660
    return None


def evaluate_washout(stock, quote, minute, bars, settings, analysis_date, now=None):
    """分析当日有先后顺序的回撤、反弹及站稳，返回 ShortTermAssessment 契约字典。

    now 仅在线模式传入，用于拒绝盘中过期行情；离线按快照交易日分析。
    """
    result = ShortTermAssessment(code=stock["code"], name=stock["name"],
                       status="insufficient", reason="行情或历史数据不足")
    if not quote or not _positive(quote.get("price")):
        return result.to_dict()
    result.change_pct = quote.get("change_pct")
    result.observed_at = quote.get("time")
    try:
        observed = datetime.strptime(str(result.observed_at), "%Y%m%d%H%M%S")
    except (ValueError, TypeError):
        return result.to_dict()
    if observed.date().isoformat() != analysis_date:
        result.reason = "行情日期与分析日期不一致"
        return result.to_dict()
    if now is not None and _minute_index(now.strftime("%H%M")) is not None:
        if not 0 <= (now - observed).total_seconds() <= settings["max_quote_age_seconds"]:
            result.reason = "实时行情已过期，等待更新"
            return result.to_dict()

    # 当日日K仍在变化，趋势只使用当前交易日之前的收盘数据。
    history = {b["date"]: b["close"] for b in (bars or [])
               if b.get("date") and b["date"] < analysis_date and _positive(b.get("close"))}
    closes = [history[d] for d in sorted(history)][-settings["trend_days"]:]
    if len(closes) < settings["trend_days"] or not _positive(quote.get("prev_close")):
        result.reason = "历史日K不足，暂不判断趋势"
        return result.to_dict()

    quote_clock = observed.hour * 60 + observed.minute
    if quote_clock >= 900:
        end_index = 240
    elif 690 < quote_clock < 780:
        end_index = 120
    else:
        end_index = _minute_index(observed.strftime("%H%M"))
    points_by_time = {}
    for point in minute or []:
        index = _minute_index(point.get("time"))
        if (point.get("date") == analysis_date and index is not None
                and end_index is not None and index <= end_index and _positive(point.get("price"))):
            points_by_time[index] = (index, point["price"], str(point["time"]).replace(":", ""))
    points = [points_by_time[i] for i in sorted(points_by_time)]
    if len(points) < settings["min_points"]:
        result.reason = "当日分时不足，等待更多采样"
        return result.to_dict()
    if end_index - points[-1][0] > settings["max_minute_delay"]:
        result.reason = "分时数据滞后，等待更新"
        return result.to_dict()
    short = closes[-settings["short_trend_days"]:]
    long_ma, short_ma = sum(closes) / len(closes), sum(short) / len(short)
    result.status = "clear"
    if short_ma < long_ma or quote["prev_close"] < long_ma:
        result.reason = "近期趋势不满足筛选条件"
        return result.to_dict()

    window = [p for p in points if p[0] >= end_index - settings["lookback_minutes"]]
    peak, candidates = window[0], []
    for point in window[1:]:
        if point[1] >= peak[1]:
            peak = point
            continue
        age = end_index - point[0]
        if settings["hold_minutes"] <= age <= settings["max_recovery_minutes"]:
            candidates.append(((peak[1] - point[1]) / peak[1] * 100, peak, point))
    if not candidates:
        result.reason = "未出现回撤后收复的形态"
        return result.to_dict()
    drawdown, peak, trough = max(candidates, key=lambda item: item[0])
    current = quote["price"]
    rebound = (current - trough[1]) / trough[1] * 100
    recovery = (current - trough[1]) / (peak[1] - trough[1]) * 100
    result.peak_time = peak[2][:2] + ":" + peak[2][2:]
    result.trough_time = trough[2][:2] + ":" + trough[2][2:]
    result.drawdown_pct, result.rebound_pct, result.recovery_pct = drawdown, rebound, recovery
    if (drawdown < settings["min_drawdown_pct"] or rebound < settings["min_rebound_pct"]
            or recovery < settings["min_recovery_pct"]):
        result.reason = "回撤或收复幅度未达到预警阈值"
        return result.to_dict()
    hold = settings["hold_minutes"]
    recent = [p for p in points if end_index - hold < p[0] <= end_index]
    floor = trough[1] + (peak[1] - trough[1]) * settings["hold_recovery_pct"] / 100
    if len(recent) < hold:
        result.status, result.reason = "insufficient", "站稳阶段的分时采样不完整"
        return result.to_dict()
    if any(p[1] < floor for p in recent):
        result.reason = "反弹后尚未持续站稳"
        return result.to_dict()
    result.status = "signal"
    result.reason = (f"近期趋势向上；回撤 {drawdown:.2f}%，低点反弹 {rebound:.2f}%，"
                     f"收回跌幅 {recovery:.0f}%，已维持 {hold} 个交易分钟")
    return result.to_dict()
