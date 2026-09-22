# -*- coding: utf-8 -*-
"""长线判断纯函数：日K均线趋势及近期价格区间，不依赖短线规则。"""
import math
from datetime import datetime

from core.data_define import LongTermAssessment


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def evaluate_long_term(stock, quote, bars, settings, analysis_date):
    result = LongTermAssessment(code=stock["code"], name=stock["name"],
                                status="insufficient", reason="日K或行情数据不足")
    if not quote or not _positive(quote.get("price")):
        return result.to_dict()
    try:
        quote_date = datetime.strptime(str(quote.get("time")), "%Y%m%d%H%M%S").date().isoformat()
    except (ValueError, TypeError):
        return result.to_dict()
    if quote_date != analysis_date:
        result.reason = "行情日期与分析日期不一致"
        return result.to_dict()
    result.price, result.change_pct = quote["price"], quote.get("change_pct")
    # 固定使用分析日之前的日K，盘中与收盘后判断口径一致。
    history = {b["date"]: b for b in bars or [] if b.get("date") and b["date"] < analysis_date
               and all(_positive(b.get(field)) for field in ("close", "high", "low"))}
    ordered = [history[d] for d in sorted(history)]
    medium, long = settings["medium_days"], settings["long_days"]
    slope, range_days = settings["slope_days"], settings["range_days"]
    if len(ordered) < max(long, medium + slope, range_days):
        result.reason = f"完整历史日K不足 {max(long, medium + slope, range_days)} 根"
        return result.to_dict()
    closes = [b["close"] for b in ordered]
    ma_medium, ma_long = sum(closes[-medium:]) / medium, sum(closes[-long:]) / long
    previous_medium = sum(closes[-medium-slope:-slope]) / medium
    result.as_of = ordered[-1]["date"]
    result.ma_medium, result.ma_long = ma_medium, ma_long
    result.support = min(b["low"] for b in ordered[-range_days:])
    result.resistance = max(b["high"] for b in ordered[-range_days:])
    if closes[-1] >= ma_medium > ma_long and ma_medium > previous_medium:
        result.status = "uptrend"
        result.reason = f"前收盘站上 {medium} 日均线，{medium} 日均线高于 {long} 日且抬升"
    elif closes[-1] <= ma_medium < ma_long and ma_medium < previous_medium:
        result.status = "downtrend"
        result.reason = f"前收盘低于 {medium} 日均线，{medium} 日均线低于 {long} 日且下行"
    else:
        result.status = "range"
        result.reason = "均线与价格方向尚未一致，观察区间变化"
    return result.to_dict()
