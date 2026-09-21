# -*- coding: utf-8 -*-
"""GUI 自动化测试：用真实鼠标事件测试窗口移动（顶栏）与缩放（右下手柄）。
仅开发调试用——会真实移动系统鼠标光标。前提：应用已启动（窗口标题=股票小组件）。
"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

TITLE = "股票小组件"
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000


def rect_of(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def moveto(x, y):
    sw = user32.GetSystemMetrics(0) or 1
    sh = user32.GetSystemMetrics(1) or 1
    user32.mouse_event(MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE,
                       int(x * 65535 / sw), int(y * 65535 / sh), 0, 0)


def drag(x1, y1, x2, y2, steps=8):
    moveto(x1, y1)
    time.sleep(0.15)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.15)
    for i in range(1, steps + 1):
        moveto(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
        time.sleep(0.03)
    time.sleep(0.3)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.3)


def main():
    hwnd = user32.FindWindowW(None, TITLE)
    if not hwnd:
        print("未找到窗口（应用是否已启动？）")
        return
    r0 = rect_of(hwnd)
    print(f"窗口初始: L={r0.left} T={r0.top} W={r0.right - r0.left} H={r0.bottom - r0.top}")

    # 1) 顶栏拖动 → 期望窗口左上角位移约 (+120,+60)
    cx, cy = (r0.left + r0.right) // 2, r0.top + 25
    drag(cx, cy, cx + 120, cy + 60)
    r1 = rect_of(hwnd)
    dx, dy = r1.left - r0.left, r1.top - r0.top
    print(f"移动测试: 位移=({dx},{dy})  {'OK 生效' if dx > 50 and dy > 20 else 'FAIL 未生效'}")

    # 2) 组件卡片标题栏拖动（iframe 内转发）→ 期望窗口位移约 (-60,+40)
    r1 = rect_of(hwnd)
    hx, hy = (r1.left + r1.right) // 2, r1.top + int((r1.bottom - r1.top) * 0.08)
    drag(hx, hy, hx - 60, hy + 40)
    r2 = rect_of(hwnd)
    dx2, dy2 = r2.left - r1.left, r2.top - r1.top
    print(f"卡片标题栏移动: 位移=({dx2},{dy2})  {'OK 生效' if dx2 < -30 and dy2 > 15 else 'FAIL 未生效'}")

    # 3) 右下角缩放 → 期望宽高各增约 +80/+60
    r2 = rect_of(hwnd)
    sx, sy = r2.right - 8, r2.bottom - 8
    drag(sx, sy, sx + 80, sy + 60)
    r3 = rect_of(hwnd)
    dw = (r3.right - r3.left) - (r2.right - r2.left)
    dh = (r3.bottom - r3.top) - (r2.bottom - r2.top)
    print(f"缩放测试: 增量=({dw},{dh})  {'OK 生效' if dw > 40 and dh > 30 else 'FAIL 未生效'}")


if __name__ == "__main__":
    main()
