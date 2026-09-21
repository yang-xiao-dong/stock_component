# -*- coding: utf-8 -*-
"""开发环境与打包后运行环境的路径约定。"""
import os
import sys
from pathlib import Path


IS_FROZEN = bool(getattr(sys, "frozen", False))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))


def resource_path(*parts):
    """返回只读程序资源路径；打包后指向 PyInstaller 解包目录。"""
    return BUNDLE_ROOT.joinpath(*parts)


def user_data_path(*parts):
    """返回持久化用户数据路径；源码运行时仍使用项目内 data/。"""
    if IS_FROZEN:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "StockWidget"
    else:
        base = PROJECT_ROOT
    return base.joinpath(*parts)
