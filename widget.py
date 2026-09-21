# -*- coding: utf-8 -*-
"""单窗口多股票股价监控系统 — pywebview 置顶悬浮窗"""
import os
import sys
import threading
import time

import webview

import stock_api

MIN_WIDTH, MIN_HEIGHT = 360, 260
DEFAULT_WIDTH, DEFAULT_HEIGHT = 500, 380

UI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.html")

_WINDOW = None
_HWND = 0

# 支持的股票列表
STOCKS = [
    {"code": "sh603893", "name": "瑞芯微"},
    {"code": "sh603986", "name": "兆易创新"},
    {"code": "sh688082", "name": "翱捷科技-U"},
    {"code": "sh688222", "name": "龙迅股份"},
    {"code": "sh688023", "name": "中科蓝汛"},
    {"code": "sh688018", "name": "乐鑫科技"},
    {"code": "sh688099", "name": "晶晨股份"},
    {"code": "sz300078", "name": "全志科技"},
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

    def background_update(self):
        """后台定时更新数据"""
        while True:
            time.sleep(5)  # 每5秒更新一次
            self.update_all_stock_data()

    def start_resize(self, edge="se"):
        """无边框窗口：从指定边缘开始原生缩放"""
        if sys.platform != "win32":
            return False
        hit = {
            "w": 10, "e": 11, "n": 12, "nw": 13, "ne": 14,
            "s": 15, "sw": 16, "se": 17,
        }.get(str(edge), 17)
        try:
            import ctypes
            hwnd = _HWND or ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return False
            user32 = ctypes.windll.user32
            user32.ReleaseCapture()
            user32.SendMessageW(hwnd, 0x00A1, hit, 0)  # WM_NCLBUTTONDOWN
            return True
        except Exception:
            return False

    def resize_to(self, width, height):
        """按像素调整窗口大小（不访问 native 句柄）"""
        if _WINDOW is None:
            return False
        try:
            w = max(MIN_WIDTH, min(int(width), 1600))
            h = max(MIN_HEIGHT, min(int(height), 1200))
            _WINDOW.resize(w, h)
            return True
        except Exception:
            return False

    def get_window_size(self):
        if _WINDOW is None:
            return {"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT}
        try:
            return {"width": int(_WINDOW.width), "height": int(_WINDOW.height)}
        except Exception:
            return {"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT}


def _enable_frameless_resize(*_args):
    """用 Win32 API 缓存窗口句柄并允许拖边缩放，避免访问 window.native"""
    global _HWND
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return
        _HWND = hwnd
        GWL_STYLE = -16
        WS_THICKFRAME = 0x00040000
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)
    except Exception:
        pass


def main():
    global _WINDOW
    api = Api()

    window = webview.create_window(
        "瑞芯微 603893",
        UI_PATH,
        js_api=api,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        x=1100,
        y=80,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        resizable=True,
        frameless=True,
        on_top=True,
        easy_drag=False,
        transparent=False,
    )
    _WINDOW = window
    window.events.loaded += _enable_frameless_resize
    webview.start()


if __name__ == "__main__":
    main()