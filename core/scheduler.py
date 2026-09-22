# -*- coding: utf-8 -*-
"""统一后台刷新调度器：单守护线程按各自间隔执行注册的任务。

取代"每个组件自己开线程"的旧做法：全应用一个调度线程、一张任务表，
任务异常被捕获打印，不会中断调度。
"""
import threading
import time


class Scheduler:

    def __init__(self, tick=1.0):
        self._tasks = []              # [{name, interval, fn, next}]
        self._stop = threading.Event()
        self._thread = None
        self._tick = tick

    def add(self, name, interval, fn, immediate=False):
        """注册周期任务；immediate=True 时调度启动后立即执行一次"""
        now = time.time()
        self._tasks.append({
            "name": name,
            "interval": float(interval),
            "fn": fn,
            "next": now if immediate else now + float(interval),
        })

    def add_once(self, name, when, fn):
        """注册一次性任务：到点执行一次后自动移除；when 为 datetime 或 time.time() 秒"""
        if hasattr(when, "timestamp"):
            when = when.timestamp()
        self._tasks.append({
            "name": name,
            "interval": 0.0,
            "fn": fn,
            "next": float(when),
            "once": True,
        })

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            now = time.time()
            for task in list(self._tasks):
                if now >= task["next"]:
                    try:
                        task["fn"]()
                    except Exception as e:
                        print(f"[{task['name']}] 执行失败: {e}")
                    if task.get("once"):
                        self._tasks.remove(task)
                    else:
                        task["next"] = time.time() + task["interval"]
            self._stop.wait(self._tick)
