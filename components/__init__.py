# -*- coding: utf-8 -*-
"""组件包：自动发现子目录中的 Component 子类

新增组件 = 在 components/ 下建一个子目录（Component 子类 + ui.html），
无需改动 app.py，装配时自动发现并挂载。
"""
import importlib
import pkgutil

from .base import AppApi, Component, assemble  # noqa: F401


def discover():
    """扫描 components/ 下所有组件子包，返回其中 Component 子类的实例。

    约定：每个组件子包（如 stock/、group/）在 component.py 中定义
    Component 子类，这里直接导入该模块并扫描。
    """
    found = []
    for m in pkgutil.iter_modules(__path__):
        if not m.ispkg:
            continue  # base.py 等基础设施模块不是组件
        try:
            module = importlib.import_module(f"{__name__}.{m.name}.component")
        except ImportError:
            continue
        for attr in dir(module):
            obj = getattr(module, attr)
            if (isinstance(obj, type) and issubclass(obj, Component)
                    and obj is not Component
                    and obj.__module__ == module.__name__):
                found.append(obj())
    return found
