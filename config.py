# -*- coding: utf-8 -*-
"""共享配置：股票组、窗口与刷新策略（所有组件的单一配置源）

每只股票可带可选 weight 字段定制权重；缺省为等权（均分，每只 1/N）。
"""

GROUP_NAME = "芯片股组合"

STOCKS = [
    {"code": "sh603893", "name": "瑞芯微"},
    {"code": "sh603986", "name": "兆易创新"},
    {"code": "sh688220", "name": "翱捷科技-U"},
    {"code": "sh688486", "name": "龙迅股份"},
    {"code": "sh688332", "name": "中科蓝讯"},
    {"code": "sh688018", "name": "乐鑫科技"},
    {"code": "sh688099", "name": "晶晨股份"},
    {"code": "sz300458", "name": "全志科技"},
    {"code": "sh688608", "name": "恒玄科技"},
    {"code": "sh688049", "name": "炬芯科技"},
]

WEIGHT_MODE = "equal"  # equal=均分；预留 custom（读各股票 weight 字段）

# 主窗口
WINDOW = {
    "width": 560,
    "height": 460,
    "x": 1100,
    "y": 80,
    "min": (420, 320),
    "max": (1600, 1200),
}
START_COMPONENT = "stock"

# 后台刷新间隔（秒）
REFRESH = {"realtime": 5, "minute": 60, "kline": 600}
KLINE_DAYS = 60  # 组合日K取的天数
