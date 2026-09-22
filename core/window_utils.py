# -*- coding: utf-8 -*-
"""无边框置顶窗口的通用控制：原生拖边缩放/移动 + 程序化调整，供各组件复用。

用法：Api 类继承 WindowControls，create_window 后调用 api.bind(window)。
前端即可调用 start_resize / start_move / resize_to / move_to / get_window_size。

窗口句柄获取：不能用 GetForegroundWindow（加载完成瞬间前台可能是其他程序，
会拿错句柄导致所有原生操作发到别的窗口），必须按进程ID+WinForms类名枚举。
"""
import os
import sys

MAX_WIDTH, MAX_HEIGHT = 1600, 1200


def _win32():
    if sys.platform != "win32":
        return None
    import ctypes
    return ctypes


def find_own_hwnd():
    """枚举本进程的可见 WinForms 顶层窗口，返回其句柄；找不到返回 0"""
    ctypes = _win32()
    if ctypes is None:
        return 0
    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        mine = os.getpid()
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _cb(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != mine or not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, buf, 64)
            if buf.value.startswith("WindowsForms"):
                found.append(hwnd)
            return True

        user32.EnumWindows(_cb, 0)
        return found[0] if found else 0
    except Exception:
        return 0


def _hwnd_pid(hwnd):
    """返回句柄所属进程ID（0 表示失败）"""
    ctypes = _win32()
    if ctypes is None or not hwnd:
        return 0
    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value
    except Exception:
        return 0


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

    def _resolve_hwnd(self):
        """取可靠的本窗口句柄：优先枚举，缓存仍有效则复用；前台窗口仅当属本进程时可用"""
        ctypes = _win32()
        if ctypes is None:
            return 0
        if self._hwnd and ctypes.windll.user32.IsWindow(self._hwnd) \
                and _hwnd_pid(self._hwnd) == os.getpid():
            return self._hwnd
        hwnd = find_own_hwnd()
        if hwnd:
            self._hwnd = hwnd
            return hwnd
        fg = ctypes.windll.user32.GetForegroundWindow()
        return fg if _hwnd_pid(fg) == os.getpid() else 0

    def _on_loaded(self):
        """页面加载完成：枚举本进程句柄并允许拖边缩放"""
        ctypes = _win32()
        if ctypes is None:
            return
        hwnd = self._resolve_hwnd()
        if not hwnd:
            return
        try:
            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_THICKFRAME = 0x00040000
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)
        except Exception:
            pass

    # ---------- 原生拖动（备用；桥接函数在 worker 线程执行，跨线程
    # SendMessage 进不了系统移动/缩放循环，前端默认走下面的程序化方案） ----------

    def start_move(self):
        """尝试原生移动（PostMessage 至 UI 线程；不保证生效）"""
        ctypes = _win32()
        if ctypes is None:
            return False
        try:
            user32 = ctypes.windll.user32
            hwnd = self._resolve_hwnd()
            if not hwnd:
                return False
            user32.PostMessageW(hwnd, 0x00A1, 2, 0)  # WM_NCLBUTTONDOWN + HTCAPTION
            return True
        except Exception:
            return False

    def start_resize(self, edge="se"):
        """尝试从指定边缘原生缩放（PostMessage；不保证生效）"""
        ctypes = _win32()
        if ctypes is None:
            return False
        hit = {
            "w": 10, "e": 11, "n": 12, "nw": 13, "ne": 14,
            "s": 15, "sw": 16, "se": 17,
        }.get(str(edge), 17)
        try:
            user32 = ctypes.windll.user32
            hwnd = self._resolve_hwnd()
            if not hwnd:
                return False
            user32.PostMessageW(hwnd, 0x00A1, hit, 0)  # WM_NCLBUTTONDOWN
            return True
        except Exception:
            return False

    # ---------- 程序化调整（原生不可用时的回退） ----------

    def close_window(self):
        """通过 pywebview 正常关闭当前绑定窗口。"""
        if self._window is None:
            return False
        try:
            self._window.destroy()
            return True
        except Exception:
            return False

    def minimize_window(self):
        """最小化当前绑定窗口，可从任务栏恢复。"""
        if self._window is None:
            return False
        try:
            self._window.minimize()
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

    def move_to(self, x, y):
        """移动窗口到屏幕绝对坐标"""
        if self._window is None:
            return False
        try:
            self._window.move(int(x), int(y))
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

    def get_window_pos(self):
        if self._window is None:
            return None
        try:
            return {"x": int(self._window.x), "y": int(self._window.y)}
        except Exception:
            return None
