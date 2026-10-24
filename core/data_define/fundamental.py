# -*- coding: utf-8 -*-
"""基本面参考数据契约（慢变外部核验数据，非行情时序；负载存于历史库 fundamental 表）。

来源：外部数据源核验后经维护脚本导入（腾讯免费接口不提供这些字段）。
不参与在线采集与回放版本切换；读取始终取每代码最新截面（as_of 最大者）。
金额单位为元（currency 标明币种），股本单位为股，比例字段为百分数数值。
本文件暂未接入 data_define.__init__ 导出，无生产消费端；字段以本文件为唯一维护处。
"""
from dataclasses import dataclass

from .common import Contract


@dataclass
class FundamentalRecord(Contract):
    code: str = None                 # 应用统一代码，如 sh603893 / usQCOM
    name: str = None                 # 证券简称
    company_name: str = None         # 公司全称
    listing_date: str = None         # 上市日期 YYYY-MM-DD
    market_board: str = None         # 上市板块：沪主板/科创板/创业板/纳斯达克
    sw_industry: str = None          # 申万行业全路径（未逐一核验时为 None）
    actual_controller: str = None    # 实际控制人（未披露为 None）
    currency: str = "CNY"
    total_shares: float = None       # 总股本（股）
    float_shares: float = None       # 流通A股（股）
    as_of: str = None                # 数据截面日 YYYY-MM-DD（必填）
    annual_period: str = None        # 最近年报期末 YYYY-MM-DD
    annual_net_profit: float = None  # 年报归母净利润（元，可为负）
    annual_revenue: float = None     # 年报营业总收入（元）
    report_period: str = None        # 最新披露报告期 YYYY-MM-DD
    report_net_profit: float = None  # 最新报告期累计归母净利润（元）
    report_net_profit_yoy_pct: float = None  # 最新报告期净利同比（%）
    net_profit_ttm: float = None     # TTM 归母净利润（元，自算）
    deducted_net_profit_ttm: float = None     # 扣非 TTM 净利润（元，可空）
    revenue_ttm: float = None        # TTM 营收（元，市值/PS 推算）
    eps_ttm: float = None
    gross_margin_pct: float = None   # 最新报告期累计毛利率（%）
    roe_pct: float = None            # 最新报告期累计 ROE（%，未年化）
    debt_ratio_pct: float = None     # 最新报告期资产负债率（%）
    beta_24m: float = None           # 24 个月贝塔
    source: str = None               # 数据来源与核验方式说明
    note: str = None                 # 口径警示（如扣非失真、股本变动）
