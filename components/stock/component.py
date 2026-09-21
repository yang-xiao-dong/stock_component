# -*- coding: utf-8 -*-
"""组件1：个股视图 — 组内股票滑动切换，实时行情 + 分时 + 日K

单独调试（项目根目录下运行）：python -m components.stock.component
"""
import time

from components.base import Component, assemble
from config import REFRESH, STOCKS
from core import stock_api


class StockApi:
    """个股视图的前端接口（窗口控制由装配层统一提供）"""

    def __init__(self, scheduler=None):
        self.current_stock_index = 0
        self.stock_data = {}
        self.update_all_stock_data()
        if scheduler:
            scheduler.add("stock.realtime", REFRESH["realtime"], self.update_all_stock_data)

    def update_all_stock_data(self):
        """更新所有股票数据"""
        for stock in STOCKS:
            try:
                self.stock_data[stock["code"]] = stock_api.get_realtime(stock["code"])
            except Exception:
                self.stock_data[stock["code"]] = None

    def get_stocks(self):
        """获取股票列表"""
        return STOCKS

    def get_current_stock(self):
        """获取当前股票"""
        return STOCKS[self.current_stock_index]

    def get_current_stock_index(self):
        """获取当前股票索引"""
        return self.current_stock_index

    def set_current_stock_index(self, index):
        """设置当前股票索引"""
        if 0 <= index < len(STOCKS):
            self.current_stock_index = index
            return True
        return False

    def next_stock(self):
        """切换到下一个股票"""
        self.current_stock_index = (self.current_stock_index + 1) % len(STOCKS)
        return self.current_stock_index

    def prev_stock(self):
        """切换到上一个股票"""
        self.current_stock_index = (self.current_stock_index - 1) % len(STOCKS)
        return self.current_stock_index

    def get_realtime(self, code=None):
        """获取实时数据，如果code为None则返回当前股票"""
        if code is None:
            code = STOCKS[self.current_stock_index]["code"]

        # 如果数据过期（超过10秒）或不存在，重新获取
        if (code not in self.stock_data or
            self.stock_data[code] is None or
            time.time() - self.stock_data[code].get("timestamp", 0) > 10):
            try:
                new_data = stock_api.get_realtime(code)
                if new_data:
                    new_data["timestamp"] = time.time()
                    self.stock_data[code] = new_data
                else:
                    # 如果获取失败，保留旧数据（如果有）
                    pass
            except Exception as e:
                # 如果获取失败，保留旧数据（如果有）
                print(f"获取实时数据失败: {e}")

        return self.stock_data.get(code)

    def get_minute_data(self, code=None):
        """获取分时数据"""
        if code is None:
            code = STOCKS[self.current_stock_index]["code"]
        try:
            return stock_api.get_minute_data(code)
        except Exception as e:
            print(f"获取分时数据失败: {e}")
            return None

    def get_kline(self, code=None):
        """获取K线数据"""
        if code is None:
            code = STOCKS[self.current_stock_index]["code"]
        try:
            return stock_api.get_kline(code)
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return None

    def set_stock_index(self, index):
        """设置当前股票索引"""
        if 0 <= index < len(STOCKS):
            self.current_stock_index = index
            # 清除当前股票的缓存，强制重新获取数据
            code = STOCKS[self.current_stock_index]["code"]
            if code in self.stock_data:
                del self.stock_data[code]
            return True
        return False


class StockComponent(Component):
    id = "stock"
    title = "个股行情"

    def create_api(self, scheduler=None):
        return StockApi(scheduler=scheduler)


if __name__ == "__main__":
    assemble([StockComponent()])
