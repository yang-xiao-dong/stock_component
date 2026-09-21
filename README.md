# 股票小组件（桌面悬浮）

基于 Python + pywebview 的置顶无边框桌面小组件：**一个窗口、一个入口**，窗口内切换「个股 / 组合」两种视图，组件模块化分目录管理。

## 快速开始

```bash
pip install pywebview requests
python app.py        # 唯一入口
```

- **个股组件**：组内股票滑动/滚轮/点击切换，实时行情 + 分时 + 日K，5秒刷新
- **组合组件**：以本金为锚（¥ 为绝对度量，% 相对本金）——本金均分建仓于K线窗口首日、持有不动；组合分时（各股当日盈亏¥细线 + 组合合计¥）、组合日K（市值¥蜡烛 + 本金基准线）、持仓盈亏分解（当日/累计¥）
- 单窗口上下堆叠全部组件，窗口内滚动查看；拖标题栏移动窗口，拖边缘缩放，置顶显示
- **离线快照**：顶栏「存快照」保存当日整组数据（行情+分时+日K）到 `data/snapshots/`，「离线」可切换回看任意已存交易日的完整收盘状态，组件整体重载；交易日收盘后自动保存（幂等，不重复不覆盖）

## 目录结构

```
G:\stock\
├── app.py                  # 唯一入口（薄壳）：自动发现组件并装配启动
├── config.py               # 共享配置：股票组 + 窗口 + 刷新策略
├── core/                   # 基础层
│   ├── stock_api.py        #   腾讯行情接口
│   ├── group_calc.py       #   组合均分计算（纯函数）
│   ├── window_utils.py     #   无边框窗口控制
│   ├── scheduler.py        #   统一后台刷新调度
│   ├── http_server.py      #   本地静态服务（同源嵌入组件）
│   └── data_define/        #   数据契约（字段唯一定义 + 收盘快照）
├── components/             # 组件层（自动发现）
│   ├── base.py             #   Component 基类 + AppApi 路由 + assemble 装配
│   ├── stock/              #   组件1：个股视图
│   └── group/              #   组件2：组合视图
├── assets/                 # 前端共享资源（shell.html 外壳 + shared.css/js）
├── tests/                  # 测试与验证脚本
├── legacy/                 # 历史备份与早期调试脚本（不再维护）
└── docs/使用说明.md
```

新增组件 = `components/` 下建子目录（`Component` 子类 + `ui.html`），`app.py` 零改动自动接入；组件 API 方法重名会在启动时直接报错。

## 股票组（config.py）

瑞芯微 sh603893、兆易创新 sh603986、翱捷科技-U sh688220、龙迅股份 sh688486、中科蓝讯 sh688332、乐鑫科技 sh688018、晶晨股份 sh688099、全志科技 sz300458、恒玄科技 sh688608、炬芯科技 sh688049（代码均已通过行情接口核对；改名/换股只需编辑 `config.py`）。

## 技术要点

- 数据源：腾讯免费行情（qt.gtimg.cn / web.ifzq.gtimg.cn），实时行情整组一次批量请求
- 后端：Python 多线程定时刷新（实时5s / 分时60s / 日K600s），pywebview js_api 暴露给前端
- 前端：原生 HTML/CSS/JS + Canvas 绘图，无外部前端依赖；`group_ui.html` 直接用浏览器打开显示演示数据（预览布局用）
- 测试：`python tests/test_group_calc.py`（均分计算，无网络）

## 许可证

MIT License
