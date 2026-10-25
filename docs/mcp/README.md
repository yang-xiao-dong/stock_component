# MCP 数据本地化档案（docs/mcp/）

一次性把「只有 MCP 能拿到、过后难再生」的数据落盘为 JSON，供日后分析。**不接 UI、不改运行时逻辑**；分时救援数据经 `scripts/import_rescue_minutes.py` 幂等入库（vol 统一折算为手）。

## 文件清单（2026-10-25 采集）

| 文件 | 内容 | 来源 | 验证 |
|---|---|---|---|
| `index_valuation_monthly_2026-10-25.json` | 沪深300（2015-01起142个月）/科创50（2019-12起）/国证芯片（2019-08起）月末 PE-TTM + PB 序列 + 2026-10-23 快照 | Wind wind-index get_index_fundamentals | 沪深300 两段拼接重叠期逐值一致；Wind 自带分位数仅17样本不可用，须用序列自算 |
| `stock_valuation_monthly_2026-10-25.json` | 10 只个股月末 PE/PB 全历史（兆易/全志自上市、瑞芯微 2020-02 起），含亏损期负 PE 与停牌期同值 | Wind wind-stock get_stock_fundamentals | 1102 数据点解析/日期单调校验通过 |
| `minute_<code>_2026-08-31.json` ×10 | **8-31 全组 10 只逐分钟分时**（[HH:MM, 成交价, 该分钟成交量(股)]，238-241分钟/只） | Wind wind-stock get_stock_quote | 成交量合计与同花顺日成交量**逐只分毫不差**，收盘价全对；瑞芯微当日涨停 194.59=176.90×1.10 |
| `minute_<code>_2026-08-17.json` ×10 | **8-17 全组 10 只逐分钟分时**（同格式，238-240分钟/只） | 同上 | 同样逐只分毫不差；当日组内普涨（全志+5.5%尾盘连续大单、翱捷+5.8%放量破106） |
| `minute_rescue_sh603893_2026-08-19.json`（在 docs/） | 8-19 瑞芯微分时（首批救援） | Wind（头尾拼接） | 总量=同花顺 17,478,762 股精确一致 |
| `index_980017_monthly_kline_2015-2026.json` | 国证芯片月K 2015-01→2026-10（腾讯仅能给1根，此价格史只能来自 Wind） | Wind wind-index get_index_kline | 与月度 PE 序列 2026-06 尖峰互证 |
| `qcom_valuation_2026-10-23.json` | 高通 PE 20.29 / PB 6.79 / 市值 1878 亿美元（分位数为财年内口径，仅参考） | Wind wind-global-stock | — |

## 关键事实（分析时直接用）

- **分位数必须自算**：Wind 工具自带的分位字段样本数过小（指数层约17个、QCOM 为财年内约205个）。
- 8-17 与 8-31 均为组合级可回放日：全部 10 只分时已入库双库，离线切换到这两天可看个股分时+组合分时（行情由 1.2.7 日K还原路径提供）。
- 估值序列覆盖每只股票的完整牛熊：科创50 从 40x（2024-07 低点）到 259x（2026-06 尖峰）再回落 110x；国证芯片 32.8x（2022-09 低点）→208x（2026-05）→70.8x（2026-10-23）。
- 已知数据陷阱记录在各文件 `meta.notes`（停牌期同值、蓝讯 2026-02 起 PE 口径切换、炬芯 2026-08/09 同值等）。

## 入库命令

```bash
python scripts/import_rescue_minutes.py              # EXE 库（%LOCALAPPDATA%）
python scripts/import_rescue_minutes.py --db data/market.sqlite3   # 源码库
python scripts/import_rescue_minutes.py --dry-run    # 只校验
```

## 后续菜单（本次未做、数据不具易逝性可后补）

- 分红史 / 股本变动 / 解禁时间表（Wind get_stock_events / get_stock_equity_holders，每只 2 次调用）：永久事实，不急。
- 指数日K：科创50/沪深300 可从腾讯免费取（`sh000688`/`sh000300`），无需 MCP。
