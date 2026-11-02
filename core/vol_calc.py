# -*- coding: utf-8 -*-
"""成交量派生计算的纯函数模块（合成数据可测，不依赖网络与数据库）。

口径约定：
- 分时点 vol 为「截至该时点的累计成交量」（手），单分钟量由相邻累计值相减得到，
  与《数据库设计》第 5 节一致，不可直接求和。
- 量比 = 当日截至此刻每分钟平均量 ÷ 近5日每分钟平均量（同时刻对同时刻），
  与行情终端通用定义一致；分钟数不足一日按已有点数计。
"""
MINUTES_PER_DAY = 240


def minute_deltas(points):
    """累计分时点 -> 单分钟成交量序列（手）。

    points: [{"vol": 累计量, ...}, ...]（契约 MinutePoint dict 列表）
    返回与 points 等长的每分钟量列表；序列不可用时返回 None：
    - 任一点 vol 缺失/非数值，视为无量可画；
    - 累计值出现回退（负差分）且总量超过末端累计量的 1%，视为数据损坏
      （误存成交额混排或旧快照异常），小幅毛刺钳为 0 不影响形态。
    """
    if not points or len(points) < 2:
        return None
    vols = []
    for p in points:
        v = p.get("vol") if isinstance(p, dict) else None
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return None
        vols.append(float(v))
    deltas, negative = [], 0.0
    for i, v in enumerate(vols):
        base = vols[i - 1] if i else 0.0
        d = v - base
        if d < 0:
            negative += -d
            d = 0.0
        deltas.append(d)
    if negative > 0.01 * max(vols[-1], 0.0):
        return None
    return deltas


def volume_ratio(today_points, past_day_totals, minutes_per_day=MINUTES_PER_DAY):
    """由库内分时折算量比（离线回放兜底；在线直接取行情字段 liang_ratio）。

    today_points: 当日累计分时点列表；past_day_totals: 近几个交易日的
    全天累计成交量列表（手，各日版本取最大累计值）。
    今日按已有点数折算分钟均量，历史按整日分钟数折算，两者相除。
    输入不足或历史均量为 0 时返回 None（前端显示 --）。
    """
    if not today_points or not past_day_totals:
        return None
    last = today_points[-1].get("vol") if isinstance(today_points[-1], dict) else None
    if not isinstance(last, (int, float)) or isinstance(last, bool) or last <= 0:
        return None
    elapsed = max(1, min(len(today_points), minutes_per_day))
    past = [float(v) for v in past_day_totals
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0]
    if not past:
        return None
    past_avg = sum(past) / len(past) / minutes_per_day
    if past_avg <= 0:
        return None
    ratio = (last / elapsed) / past_avg
    # 旧库分时可能误存成交额（元），与手量纲混排时量比会落到荒谬区间
    # （实测瑞芯微混排折算 ≈3e-5）。按经验带宽拦截，宁缺毋错：前端显示 --。
    return ratio if 0.02 <= ratio <= 100 else None
