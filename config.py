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

# 组合本金（元）：均分建仓于日K窗口首日开盘价、持有不动。
# 组合组件中所有 ¥ 金额都是绝对度量，百分比一律相对该本金。
PRINCIPAL = 100000.0

# 主窗口（外壳页上下堆叠组件，窗口内滚动）
APP_TITLE = "股票小组件"
WINDOW = {
    "width": 560,
    "height": 780,
    "x": 1100,
    "y": 60,
    "min": (420, 480),
    "max": (1600, 1600),
}

# 后台刷新间隔（秒）。realtime 15s：免费行情本就数秒级更新，5s 与 15s 观感
# 无差别，但行情快照的抓取/入库写放大差 3 倍（采样资产仍有 4 点/分钟）。
REFRESH = {"realtime": 15, "minute": 60, "kline": 600}
KLINE_DAYS = 60  # 组合日K取的天数

# PE对比组件：参照公司（虚线，不参与排名）+ 对比组历史PE折线与分位。
# 历史PE按当前EPS-TTM折算（约一年窗口）；对比组默认与股票组 STOCKS 完全一致，
# 不缩减数量；如需单独增减对比名单，改 peers 为股票列表即可。
PE_COMPARE = {
    "refresh_seconds": 60,   # 当前PE刷新间隔
    "kline_days": 250,       # 历史窗口（交易日）
    "reference": {"code": "usQCOM", "name": "高通"},  # 美股延迟行情，代码不带后缀
    "peers": list(STOCKS),
}

# 独立判断组件：长线趋势与短线回撤收复形态，互不依赖组合本金。
ANALYSIS = {
    "refresh_seconds": 60,
    "kline_days": 120,
    "long_term": {
        "medium_days": 20,
        "long_days": 60,
        "slope_days": 5,
        "range_days": 20,
    },
    "short_term": {
        "trend_days": 20,
        "short_trend_days": 5,
        "min_points": 30,
        "lookback_minutes": 90,
        "max_recovery_minutes": 45,
        "hold_minutes": 5,
        "min_drawdown_pct": 3.0,
        "min_rebound_pct": 2.0,
        "min_recovery_pct": 60.0,
        "hold_recovery_pct": 50.0,
        "max_minute_delay": 5,
        "max_quote_age_seconds": 180,
    },
}

# 收盘自动快照：到收盘缓冲时刻主动触发保存一次，完成后再布防下一个交易日；
# 启动时若已过该时刻立即补一次。只按时间判断，当日快照已存在则跳过（不覆盖）
AUTO_SNAPSHOT = {
    "hour": 15,   # 收盘 15:00 + 缓冲
    "minute": 5,
}
