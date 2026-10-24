# -*- coding: utf-8 -*-
"""组件1：个股视图 — 组内股票滑动切换，实时行情 + 分时 + 日K

单独调试（项目根目录下运行）：python -m components.stock.component
"""

from components.base import Component, assemble
from config import REFRESH, STOCKS
from core import data_source


class StockApi:
    """组件只保存选择状态；行情缓存统一由数据源管理，避免切换后串日期。"""
    def __init__(self, scheduler=None):
        self.current_stock_index = 0
        self._source_key = None
        if scheduler:
            scheduler.add("stock.realtime", REFRESH["realtime"], self.update_all_stock_data, immediate=True)

    def get_stocks(self):
        key = data_source.context_key()
        if key != self._source_key:
            self.current_stock_index = 0
            self._source_key = key
        return data_source.get_config("STOCKS", STOCKS)

    def update_all_stock_data(self):
        return data_source.get_realtime_batch([s["code"] for s in self.get_stocks()])

    def get_current_stock(self):
        stocks = self.get_stocks()
        return stocks[self.current_stock_index % len(stocks)] if stocks else None

    def get_current_stock_index(self):
        self.get_stocks()
        return self.current_stock_index

    def set_current_stock_index(self, index):
        if 0 <= index < len(self.get_stocks()):
            self.current_stock_index = index
            return True
        return False

    def next_stock(self):
        stocks = self.get_stocks()
        self.current_stock_index = (self.current_stock_index + 1) % max(1, len(stocks))
        return self.current_stock_index

    def prev_stock(self):
        stocks = self.get_stocks()
        self.current_stock_index = (self.current_stock_index - 1) % max(1, len(stocks))
        return self.current_stock_index

    def get_realtime(self, code=None):
        code = code or (self.get_current_stock() or {}).get("code")
        return data_source.get_realtime(code) if code else None

    def get_minute_data(self, code=None):
        code = code or (self.get_current_stock() or {}).get("code")
        return data_source.get_minute_data(code) if code else None

    def get_kline(self, code=None):
        code = code or (self.get_current_stock() or {}).get("code")
        return data_source.get_kline(code) if code else None

    def set_stock_index(self, index):
        return self.set_current_stock_index(index)


class StockComponent(Component):
    id = "stock"
    title = "个股行情"
    embed_height = 400

    def create_api(self, scheduler=None):
        return StockApi(scheduler=scheduler)


if __name__ == "__main__":
    assemble([StockComponent()])
