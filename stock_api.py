# -*- coding: utf-8 -*-
"""腾讯免费行情接口：实时行情 + 当日分时"""
import json
import re

import requests

CODE = "sh603893"
HEADERS = {
    "Referer": "https://gu.qq.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

session = requests.Session()
session.headers.update(HEADERS)


def get_realtime(code=CODE):
    """返回实时行情 dict，失败返回 None"""
    url = f"https://qt.gtimg.cn/q={code}"
    try:
        r = session.get(url, timeout=5)
        r.encoding = "gbk"
        m = re.search(r'"([^"]+)"', r.text)
        if not m:
            return None
        f = m.group(1).split("~")
        # 腾讯字段: 1名称 2代码 3最新价 4昨收 5今开 6成交量(手) ...
        # 30时间 31涨跌 32涨跌% 33最高 34最低 36成交量(手) 37成交额(万)
        return {
            "name": f[1],
            "code": f[2],
            "price": float(f[3]),
            "prev_close": float(f[4]),
            "open": float(f[5]),
            "time": f[30],
            "change": float(f[31]),
            "change_pct": float(f[32]),
            "high": float(f[33]),
            "low": float(f[34]),
            "volume": float(f[36]),        # 手
            "amount": float(f[37]) / 10000,  # 亿元
        }
    except Exception:
        return None


def get_kline(code=CODE, count=60, period="day"):
    """返回日K线 [{"date","open","close","high","low","vol"}, ...] 前复权，失败返回 None"""
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?param={code},{period},,,{count},qfq")
    try:
        r = session.get(url, timeout=5)
        data = r.json()["data"][code]
        rows = data.get("qfq" + period) or data.get(period)
        return [
            {"date": row[0], "open": float(row[1]), "close": float(row[2]),
             "high": float(row[3]), "low": float(row[4])}
            for row in rows if len(row) >= 5
        ]
    except Exception:
        return None


def get_minute_data(code=CODE):
    """返回当日分时 [( 'HH:MM', price ), ...] 和均价线，失败返回 None"""
    url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={code}"
    try:
        r = session.get(url, timeout=5)
        data = r.json()
        minute = data["data"][code]["data"]["data"]
        points = []
        for row in minute:
            t, price, _, vol = row.split(" ")
            points.append({"time": t[:5], "price": float(price), "vol": float(vol)})
        return points
    except Exception:
        return None


if __name__ == "__main__":
    print(json.dumps(get_realtime(), ensure_ascii=False, indent=2))
    pts = get_minute_data()
    print(f"分时点数: {len(pts) if pts else 0}", pts[:3] if pts else "")
