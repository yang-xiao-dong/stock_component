# -*- coding: utf-8 -*-
"""后台文件日志：窗口版 EXE（--windowed）无控制台，stderr/stdout 为 None，
Python 异常与 logging 输出全部丢失。统一落到用户数据目录 logs/ 下：

- 源码运行：项目 data/logs/app.log + 控制台双写
- EXE：%LOCALAPPDATA%/StockWidget/logs/app.log；stderr 重定向 stderr.log
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from core.runtime_paths import user_data_path


def setup(log_name="app"):
    """装配时调用一次；返回日志文件路径。重复调用无副作用。"""
    directory = user_data_path("logs")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{log_name}.log"
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handlers = [handler]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
    if sys.stderr is None:
        # 窗口版 EXE：traceback 默认打向 None 会丢/抛错，重定向到文件留痕
        stream = open(directory / "stderr.log", "a", buffering=1, encoding="utf-8", errors="replace")
        sys.stderr = stream
        sys.stdout = stream
    logging.getLogger(__name__).info("日志就绪：%s", path)
    return path
