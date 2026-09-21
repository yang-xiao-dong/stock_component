# -*- coding: utf-8 -*-
"""瑞芯微(603893)股价桌面小组件 — pywebview 置顶悬浮窗"""
import os
import threading

import webview

import stock_api

UI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.html")


class Api:
    """暴露给前端 JS 的接口（pywebview 自动转 JSON）"""

    def get_realtime(self):
        return stock_api.get_realtime()

    def get_minute_data(self):
        return stock_api.get_minute_data()

    def get_kline(self):
        return stock_api.get_kline()


def main():
    api = Api()
    window = webview.create_window(
        "瑞芯微 603893",
        UI_PATH,
        js_api=api,
        width=340,
        height=252,
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
