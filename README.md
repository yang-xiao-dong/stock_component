# 股票小组件（桌面悬浮）

基于 Python + pywebview 的置顶无边框桌面小组件：**一个窗口、一个入口**，窗口内切换「个股 / 组合」两种视图，组件模块化分目录管理。

## 快速开始

```bash
pip install -r requirements.txt
python app.py        # 唯一入口
```

## 打包与发布

项目内置 `builder` 模块，可生成无需安装 Python 的 Windows 单文件 EXE：

```bash
pip install -r requirements-build.txt
python -m builder
```

版本号统一维护在 `version.py`。默认产物为 `dist/股票小组件-v<版本>.exe`，可直接传给其他人使用；也可临时指定发布版本与输出目录：

```bash
python -m builder --version 1.1.0
python -m builder --dist-dir D:\release
```

打包器会自动发现并收集 `components/` 下的组件及其界面资源。EXE 保存的快照位于 `%LOCALAPPDATA%\StockWidget\data\snapshots`，升级或移动 EXE 不会丢失。目标电脑需为 Windows 10/11，并具备 Microsoft Edge WebView2 Runtime（通常已随系统安装）。

### 自动打包与发布（GitHub）

将完整 Git 仓库推送到 GitHub 后，内置的 `Windows 打包与自动发布` 工作流会在 `master` / `main` 推送、PR 或手动运行时执行离线测试、脚本语法检查和 Windows EXE 构建。每次成功构建的 EXE 与 `SHA256SUMS.txt` 可在 Actions 的 Artifacts 下载，保留 14 天。

默认分支自上次正式发布以来累计 **至少 5 个新功能提交**，构建成功后自动创建 GitHub Release，附带 EXE、SHA256 校验文件和自动生成的发布说明。新功能使用 `feat: 中文说明` 或 `feat(组件): 中文说明`；修复使用 `fix: 中文说明`，文档使用 `docs: 中文说明`，均不计入功能数。一次推送超过 5 个功能时会合并发布一个包含全部改动的版本；普通合并提交不重复计数，Squash 合并按最终提交计数。

计数从 `.release-policy.json` 的基线开始，历史功能不追溯；流水线功能自身计为第 1 个功能。首次自动发布为 `v1.0.1`，后续为 `v1.0.2`、`v1.0.3`。`version.py` 保留应用默认版本，流水线从上次正式发布标签计算打包版本并传给 `builder --version`，无需机器人回写主分支；需要跨大版本时可手动提高 `version.py`。只有正式发布成功才重置功能计数，草稿与预发布不计入。不要手工占用待发布的版本标签。

仓库需启用 GitHub Actions，并允许发布任务使用 `GITHUB_TOKEN` 的 `contents: write` 权限，无需另存个人 Token。若组织策略禁止此权限，需要管理员放开；标签保护规则也需允许工作流创建版本标签。首次接入需配置远程仓库并推送本地提交，只有本地 Git 提交不会触发云端流水线。

```bash
python -m builder.release  # 本地查看功能计数和下一版本，不执行发布
```

发布失败可重跑 Actions：文件先上传至草稿，全部上传成功后才公开；同一提交的草稿可续传，已公开版本不会覆盖。手动运行工作流仍遵守 5 个功能的门槛，PR 仅测试打包，不正式发布。

- **个股组件**：组内股票滑动/滚轮/点击切换，实时行情 + 分时 + 日K，5秒刷新
- **组合组件**：以本金为锚（¥ 为绝对度量，% 相对本金）——本金均分建仓于K线窗口首日、持有不动；组合分时（各股当日盈亏¥细线 + 组合合计¥）、组合日K（市值¥蜡烛 + 本金基准线）、持仓盈亏分解（当日/累计¥）
- **独立判断组件**：内部划分“长线判断”和“短线判断”。长线展示日K均线趋势及支撑压力区间；短线筛选明显回撤后收复、持续站稳的“疑似洗盘”价格形态。每 60 秒刷新，配置位于 `config.ANALYSIS`；规则和界面均封装在 `components/analysis/`，复用现有数据源、调度器和组件自动发现。
- 单窗口上下堆叠全部组件，窗口内滚动查看；拖标题栏移动窗口，拖边缘缩放，置顶显示
- 顶栏「排序」支持组件上移、下移和恢复默认；顺序自动保存，重启后保留，调整时保留组件当前状态。
- **离线快照**：顶栏「存快照」保存当日整组数据（行情+分时+日K）到 `data/snapshots/`，「离线」可切换回看任意已存交易日的完整收盘状态，组件整体重载；收盘时刻到点自动保存（幂等，不重复不覆盖）

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
│   ├── group/              #   组件2：组合视图
│   └── analysis/           #   独立判断：long_term.py / short_term.py + 界面
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
