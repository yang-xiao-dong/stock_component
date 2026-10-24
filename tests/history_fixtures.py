"""历史库离线合成数据，禁止请求网络。"""
from copy import deepcopy
from datetime import date, timedelta

from core.data_define.history import MarketBatch
from core.history.settings import current_config


def settings():
    out = current_config()
    out["STOCKS"] = [{"code": "sh600001", "name": "测试甲"}, {"code": "sz000002", "name": "测试乙"}]
    out["KLINE_DAYS"] = 3
    out["ANALYSIS"]["kline_days"] = 5
    out["PE_COMPARE"].update(kline_days=7, peers=deepcopy(out["STOCKS"]),
                              reference={"code": "usTEST", "name": "参照"})
    return out


class Provider:
    def __init__(self, day="2026-09-22", price=12):
        self.day, self.price = day, price
        self.adjustment = "qfq"
        self.fail = set()
        self.calls = []
        self.forbidden = False

    def _call(self, kind, code):
        if self.forbidden:
            raise AssertionError("离线模式发生网络请求")
        self.calls.append((kind, code))
        return f"{kind}:{code}" not in self.fail

    def get_quote_batches(self, codes):
        out = {}
        for code in codes:
            if not self._call("quote", code):
                continue
            row = {"code": code, "name": code, "price": self.price, "prev_close": 10,
                   "open": 10, "high": self.price+1, "low": 9, "change": self.price-10,
                   "change_pct": (self.price-10)*10, "time": self.day.replace("-", "")+"150000",
                   "volume": 100, "amount": 0.1, "pe_ttm": 20, "pb": 2, "market_cap": 100}
            out[code] = MarketBatch(code=code, kind="quote", rows=[row], raw=deepcopy(row))
        return out

    def get_minute_batch(self, code):
        if not self._call("minute", code):
            return None
        rows = [{"date": self.day, "time": "09:30", "price": 10, "vol": 5},
                {"date": self.day, "time": "15:00", "price": self.price, "vol": 10}]
        return MarketBatch(code=code, kind="minute", rows=rows, raw=deepcopy(rows))

    def _daily(self, code, kind, count):
        if not self._call(kind, code):
            return None
        days = [(date.fromisoformat(self.day)-timedelta(days=i)).isoformat() for i in range(count-1, -1, -1)]
        rows = [{"date": d, "close": self.price} for d in days]
        if kind == "kline":
            for row in rows:
                row.update(open=10, high=self.price+1, low=9)
        return MarketBatch(code=code, kind=kind, rows=rows, raw=deepcopy(rows), requested_count=count,
                           adjustment=self.adjustment if kind == "kline" else "none")

    def get_kline_batch(self, code, count):
        return self._daily(code, "kline", count)

    def get_close_batch(self, code, count):
        return self._daily(code, "close", count)
