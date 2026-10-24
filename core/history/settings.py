"""采集需求与回放参数。配置仍以 config.py 为唯一当前配置源。"""
from copy import deepcopy

import config

NAMES = ("STOCKS", "GROUP_NAME", "PRINCIPAL", "WEIGHT_MODE", "KLINE_DAYS", "ANALYSIS", "PE_COMPARE")


def current_config():
    values = {name: deepcopy(getattr(config, name)) for name in NAMES}
    values["CALCULATION_VERSION"] = 1
    return values


def requirements(settings):
    """stream -> 请求长度；组内日K统一取最大窗口，再按消费者窗口截取。"""
    needs = {}
    count = max(settings["KLINE_DAYS"], settings["ANALYSIS"]["kline_days"])
    for stock in settings["STOCKS"]:
        code = stock["code"]
        needs[f"quote:{code}"] = None
        needs[f"minute:{code}"] = None
        needs[f"kline:{code}"] = count
    pe = settings["PE_COMPARE"]
    for stock in [pe["reference"]] + list(pe["peers"]):
        code = stock["code"]
        needs[f"quote:{code}"] = None
        needs[f"close:{code}"] = pe["kline_days"]
    return needs

