# -*- coding: utf-8 -*-
"""单窗口多股票股价监控系统 — pywebview 置顶悬浮窗"""
import os
import threading
import time

import webview

import stock_api

UI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.html")

# 支持的股票列表
STOCKS = [
    {"code": "sh603893", "name": "瑞芯微"},
    {"code": "sh603986", "name": "兆易创新"},
    {"code": "sh688082", "name": "翱捷科技-U"},
    {"code": "sh688222", "name": "龙迅股份"},
    {"code": "sh688023", "name": "中科蓝汛"},
    {"code": "sh688018", "name": "乐鑫科技"},
    {"code": "sh688099", "name": "晶晨股份"},
    {"code": "sh300078", "name": "全志科技"},
    {"code": "sh688608", "name": "恒玄科技"},
    {"code": "sh688268", "name": "炬芯科技"},
]

class Api:
    """暴露给前端 JS 的接口（pywebview 自动转 JSON）"""
    
    def __init__(self):
        self.current_stock_index = 0
        self.stock_data = {}
        self.update_all_stock_data()
        
        # 后台定时更新数据
        self.update_thread = threading.Thread(target=self.background_update, daemon=True)
        self.update_thread.start()
    
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
        
        # 如果数据过期（超过10秒），重新获取
        if (code not in self.stock_data or 
            self.stock_data[code] is None or 
            time.time() - self.stock_data[code].get("timestamp", 0) > 10):
            try:
                self.stock_data[code] = stock_api.get_realtime(code)
                if self.stock_data[code]:
                    self.stock_data[code]["timestamp"] = time.time()
            except Exception:
                self.stock_data[code] = None
        
        return self.stock_data.get(code)
    
    def get_minute_data(self, code=None):
        """获取分时数据"""
        if code is None:
            code = STOCKS[self.current_stock_index]["code"]
        return stock_api.get_minute_data(code)
    
    def get_kline(self, code=None):
        """获取K线数据"""
        if code is None:
            code = STOCKS[self.current_stock_index]["code"]
        return stock_api.get_kline(code)
    
    def background_update(self):
        """后台定时更新数据"""
        while True:
            time.sleep(5)  # 每5秒更新一次
            self.update_all_stock_data()


def main():
    api = Api()
    
    window = webview.create_window(
        "瑞芯微 603893",
        UI_PATH,
        js_api=api,
        width=380,
        height=280,
        x=1100,
        y=80,
        frameless=True,
        on_top=True,
        easy_drag=True,   # 无边框窗口可直接拖动
        transparent=False,
    )
    webview.start()


if __name__ == "__main__":
    main()