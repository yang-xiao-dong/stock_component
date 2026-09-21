# -*- coding: utf-8 -*-
"""唯一入口（薄壳）：自动发现组件 → 单窗口装配启动。

架构：app.py → components（自动发现）→ core（数据/计算/窗口/调度）
新增组件只需在 components/ 下建子目录（Component 子类 + ui.html），
此文件无需任何改动。装配逻辑见 components/base.py 的 assemble()。
"""
from components import discover
from components.base import assemble


def main():
    assemble(discover())


if __name__ == "__main__":
    main()
