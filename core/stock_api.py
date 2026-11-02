# -*- coding: utf-8 -*-
"""腾讯免费行情接口：实时行情 + 当日分时 + 日K（输出经 core/data_define 契约构造）"""
import json
import logging
import re
from datetime import datetime

import requests

from core.data_define import KlineBar, MinutePoint, RealtimeQuote
from core.data_define.history import ClosePoint, MarketBatch

CODE = "sh603893"
HEADERS = {
    "Referer": "https://gu.qq.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

session = requests.Session()
session.headers.update(HEADERS)
logger = logging.getLogger(__name__)
CHART_BASE_URLS = (
    "https://proxy.finance.qq.com/ifzqgtimg",
    "https://web.ifzq.gtimg.cn",
)


def _get_chart_data(path, params):
    """腾讯图表接口：优先使用财经入口，失败时回退到原入口。"""
    for base_url in CHART_BASE_URLS:
        try:
            response = session.get(f"{base_url}{path}", params=params, timeout=5)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code", 0) != 0 or not payload.get("data"):
                raise ValueError("行情接口未返回有效数据")
            return payload["data"]
        except (requests.RequestException, ValueError) as exc:
            logger.warning("图表数据获取失败 (%s%s): %s", base_url, path, exc)
    return {}


def _opt_float(f, idx):
    """可选字段转 float：越界/空串/非数值（如美股该位置是公司名）返回 None"""
    try:
        v = f[idx]
        v = v.strip() if isinstance(v, str) else v
        return float(v) if v not in (None, "") else None
    except (IndexError, ValueError, TypeError):
        return None


def _parse_fields(f):
    """解析腾讯行情字段为 dict（字段契约见 core/data_define/quote.py）
    腾讯字段: 1名称 2代码(美股带后缀如QCOM.OQ) 3最新价 4昨收 5今开 6成交量(手) ...
    30时间 31涨跌 32涨跌% 33最高 34最低 36成交量(手) 37成交额(万)
    39市盈率TTM 45总市值 46市净率(仅A股) 49量比(仅A股) 52市盈率动(仅A股) 53市盈率静(仅A股)
    """
    quote_time = f[30].strip()
    if "-" in quote_time:
        # 腾讯美股返回 ISO 日期时间，A股返回紧凑时间；契约统一为市场本地十四位时间。
        quote_time = datetime.fromisoformat(quote_time).strftime("%Y%m%d%H%M%S")
    return RealtimeQuote(
        name=f[1],
        code=f[2],
        price=float(f[3]),
        prev_close=float(f[4]),
        open=float(f[5]),
        time=quote_time,
        change=float(f[31]),
        change_pct=float(f[32]),
        high=f[33],
        low=f[34],
        volume=float(f[36]),          # 手
        amount=float(f[37]) / 10000,  # 亿元
        pe_ttm=_opt_float(f, 39),
        market_cap=_opt_float(f, 45),
        pb=_opt_float(f, 46),
        liang_ratio=_opt_float(f, 49),
        pe_dynamic=_opt_float(f, 52),
        pe_static=_opt_float(f, 53),
    ).to_dict()


def get_realtime(code=CODE):
    """返回实时行情 dict，失败返回 None"""
    return get_realtime_batch([code]).get(code)


def get_realtime_batch(codes):
    """批量实时行情 {code: dict}，一次请求取整组；失败返回 {}"""
    return {code: batch.rows[0] for code, batch in get_quote_batches(codes).items()}


def get_quote_batches(codes):
    """保留原始字段，按响应变量名匹配股票，缺一只也不会导致后续代码错位。"""
    if not codes:
        return {}
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    try:
        r = session.get(url, timeout=6)
        r.encoding = "gbk"
        out = {}
        for code, raw in re.findall(r'v_([^=\s]+)="([^"]*)"', r.text):
            if code not in codes:
                continue
            f = raw.split("~")
            if len(f) > 37:
                try:
                    quote = _parse_fields(f)
                    quote["code"] = code
                    out[code] = MarketBatch(code=code, kind="quote", rows=[quote], raw=raw)
                except (ValueError, IndexError):
                    continue
        return out
    except Exception:
        return {}


def _get_simple_kline(code, count, period="day", end=None):
    """备用日K端点 /appstock/app/kline/kline（不复权）。
    fqkline 端点上游故障（如 2026-10 全线 501）时的降级路径；美股此端点只回
    首尾两根标记，不可用，仅作 A/港股降级。end 传 YYYY-MM-DD 取该日（含）之前。"""
    data = _get_chart_data("/appstock/app/kline/kline",
                           {"param": f"{code},{period},,{end or ''},{count}"})
    return (data.get(code) or {}).get(period) or []


def get_kline(code=CODE, count=60, period="day", end=None):
    """返回日K线 [{"date","open","close","high","low"}, ...] 前复权，失败返回 None。

    end 传 YYYY-MM-DD 时取该日（含）之前的窗口，供历史回补向前翻页。"""
    batch = get_kline_batch(code, count, period, end)
    return batch.rows if batch else None


def get_kline_batch(code=CODE, count=60, period="day", end=None):
    rows = None
    adjustment = "qfq"
    try:
        data = _get_chart_data("/appstock/app/fqkline/get", {
            "param": f"{code},{period},,{end or ''},{count},qfq",
        })[code]
        rows = data.get("qfq" + period)
        if not rows:
            rows, adjustment = data.get(period), "none"
    except Exception:
        rows = None
    if not rows and not code.startswith("us"):
        # 降级：备用端点（不复权，分红除权日会有小幅跳变，好过无数据）
        rows = _get_simple_kline(code, count, period, end)
        adjustment = "none"
    if not rows:
        return None
    bars = [
        KlineBar(date=row[0], open=float(row[1]), close=float(row[2]),
                 high=float(row[3]), low=float(row[4]),
                 vol=_opt_float(row, 5)).to_dict()   # 手；备用端点/旧源个别行缺列为 None
        for row in rows if len(row) >= 5
    ]
    return MarketBatch(code=code, kind="kline", adjustment=adjustment, rows=bars,
                       raw=rows, requested_count=count)


def get_minute_data(code=CODE):
    """返回当日分时 [{"time","price","vol"}, ...]，失败返回 None"""
    batch = get_minute_batch(code)
    return batch.rows if batch else None


def get_minute_batch(code=CODE):
    try:
        data = _get_chart_data("/appstock/app/minute/query", {"code": code})
        minute = data[code]["data"]["data"]
        raw_date = data[code]["data"].get("date")
        trade_date = (datetime.strptime(str(raw_date).replace("-", ""), "%Y%m%d")
                      .date().isoformat() if raw_date else None)
        points = []
        for row in minute:
            t, price, vol, _ = row.split()
            t = t.replace(":", "")
            points.append(MinutePoint(time=f"{t[:2]}:{t[2:4]}", price=float(price),
                                      vol=float(vol), date=trade_date).to_dict())
        return MarketBatch(code=code, kind="minute", rows=points, raw=data[code])
    except Exception:
        return None


def get_minute_history_batches(code=CODE):
    """最近约5个交易日的逐日历史分时（腾讯 day/query 端点，窗口硬上限5天，
    date/p 参数均无效——实测仅返回最近5日，更早需走 Wind 救援）。

    返回按日拆分的 MarketBatch 列表：每日单独成批，dataset 末端日期=该交易日，
    供离线回放按日精确定位；行格式与当日分时一致（第3项为累计成交量）。
    """
    try:
        data = _get_chart_data("/appstock/app/day/query", {"code": code})
        days = (data.get(code) or {}).get("data") or []
    except Exception:
        return []
    batches = []
    for group in days:
        try:
            trade_date = datetime.strptime(str(group.get("date")), "%Y%m%d").date().isoformat()
            points = []
            for row in group.get("data", []):
                parts = row.split()
                if len(parts) < 3:
                    continue
                t = parts[0].replace(":", "")
                points.append(MinutePoint(time=f"{t[:2]}:{t[2:4]}", price=float(parts[1]),
                                          vol=float(parts[2]), date=trade_date).to_dict())
            if points:
                batches.append(MarketBatch(code=code, kind="minute", rows=points, raw=group))
        except (ValueError, KeyError, TypeError):
            continue
    return batches


def get_close_series(code, count=250, end=None):
    """收盘价序列 [{"date","close"}, ...]，供 PE 历史折算（真实收盘价，非复权K线）。

    - A股（sh/sz）：fqkline 端点不带 qfq 参数 → 不复权
    - 美股（usXXX）：日K仅支持专用 usfqkline 端点 + 带后缀代码（usQCOM → usQCOM.OQ），
      且仅前复权可用（接口限制，折算误差约等于股息率）；后缀代码由实时行情字段2推导
    - end 传 YYYY-MM-DD 时取该日（含）之前的窗口，供历史回补向前翻页
    """
    batch = get_close_batch(code, count, end)
    return batch.rows if batch else None


def get_close_batch(code, count=250, end=None):
    try:
        if code.startswith("us"):
            symbol = code[2:]
            if "." not in symbol:
                quote = get_quote_batches([code]).get(code)
                if not quote:
                    return None
                symbol = quote.raw.split("~")[2]  # 原始供应商代码，如 QCOM.OQ
            data = _get_chart_data("/appstock/app/usfqkline/get",
                                   {"param": f"us{symbol},day,,{end or ''},{count},qfq"})
            rows = (data.get(f"us{symbol}") or {}).get("qfqday") or []
        else:
            data = _get_chart_data("/appstock/app/fqkline/get",
                                   {"param": f"{code},day,,{end or ''},{count},"})
            rows = (data.get(code) or {}).get("day") or []
            if not rows:
                rows = _get_simple_kline(code, count, end=end)
        out = []
        for row in rows:
            if len(row) >= 3:
                try:
                    out.append(ClosePoint(date=row[0], close=float(row[2])).to_dict())
                except (TypeError, ValueError):
                    continue
        return MarketBatch(code=code, kind="close", adjustment="qfq" if code.startswith("us") else "none",
                           rows=out, raw=rows, requested_count=count) if out else None
    except Exception:
        return None


if __name__ == "__main__":
    print(json.dumps(get_realtime(), ensure_ascii=False, indent=2))
    pts = get_minute_data()
    print(f"分时点数: {len(pts) if pts else 0}", pts[:3] if pts else "")
    closes = get_close_series("usQCOM", 5)
    print("高通收盘序列:", closes)
