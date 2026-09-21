# -*- coding: utf-8 -*-
"""无边框置顶窗口的通用控制：原生拖边缩放 + 程序化调整大小，供各组件复用。

用法：Api 类继承 WindowControls，create_window 后调用 api.bind(window)。
前端即可调用 start_resize / resize_to / get_window_size。
"""
import sys

MAX_WIDTH, MAX_HEIGHT = 1600, 1200


class WindowControls:

    def __init__(self, window=None, min_size=(360, 260), max_size=(MAX_WIDTH, MAX_HEIGHT)):
        self._window = window
        self._min_size = min_size
        self._max_size = max_size
        self._hwnd = 0

    def bind(self, window):
        """窗口创建后绑定，并在页面加载完成时缓存句柄、启用拖边缩放"""
        self._window = window
        window.events.loaded += self._on_loaded
        return window

    def _on_loaded(self):
        """用 Win32 API 缓存窗口句柄并允许拖边缩放，避免访问 window.native"""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return
            self._hwnd = hwnd
            GWL_STYLE = -16
            WS_THICKFRAME = 0x00040000
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)
        except Exception:
            pass

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
            hwnd = self._hwnd or ctypes.windll.user32.GetForegroundWindow()
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
        if self._window is None:
            return False
        try:
            w = max(self._min_size[0], min(int(width), self._max_size[0]))
            h = max(self._min_size[1], min(int(height), self._max_size[1]))
            self._window.resize(w, h)
            return True
        except Exception:
            return False

    def get_window_size(self):
        if self._window is None:
            return {"width": 0, "height": 0}
        try:
            return {"width": int(self._window.width), "height": int(self._window.height)}
        except Exception:
            return {"width": 0, "height": 0}
