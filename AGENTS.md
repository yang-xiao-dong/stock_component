# AGENTS.md — 股票小组件开发约定

面向 AI 助手与开发者的项目约定。使用者文档见 README.md 与 docs/使用说明.md，两者不重复本文内容。

## 项目概览
- Python + pywebview 桌面置顶股票小组件：单窗口外壳上下堆叠组件（iframe），窗口内滚动
- 数据源：腾讯免费行情（实时批量 / 分时 / 日K）
- config.py 是单一配置源：股票组、本金 PRINCIPAL、窗口尺寸、刷新间隔

## 常用命令
```bash
python app.py                         # 唯一入口
python -m components.stock.component  # 组件1单独调试
python -m components.group.component  # 组件2单独调试
python tests/test_group_calc.py       # 单元测试（离线、无网络）
python tests/test_data_define.py      # 数据契约测试（往返/容错/快照存取）
python tests/test_history_store.py    # 历史库事务、版本、旧快照导入、备份迁移
python tests/test_history_service.py  # 在线/离线一致性、断网重启、配置与缓存隔离
python tests/gui_drag_test.py         # GUI 自动化（会移动真实鼠标；默认不运行，仅用户明确要求时用）
pip install pywebview requests        # 依赖
# 后台日志：源码运行 logs/app.log；EXE 在 %LOCALAPPDATA%\StockWidget\logs\（窗口版无控制台，排错先看这里）
```

## 架构分层
app.py（薄入口：发现+装配）→ components/（组件，自动发现）→ core/（基础层）→ assets/（共享前端）

- `components/<id>/`：一个组件 = component.py（Component 子类）+ ui.html；外壳 shell.html 按发现结果动态生成 iframe 槽位
- `core/`：stock_api（行情抓取）、group_calc（组合计算，纯函数）、window_utils（窗口控制）、scheduler（统一后台刷新）、http_server（127.0.0.1 静态服务，供同源 iframe 嵌入）、data_define（数据契约，见下）、data_source（在线/离线统一数据源，见下）
- `assets/`：shell.html（外壳）、shared.css / shared.js（公共样式与工具：桥接穿透、格式化、Canvas 基础、缩放与移动绑定）

## 数据契约（唯一维护处：core/data_define/）
- 所有跨层数据结构的字段**只在 core/data_define/ 定义**，按数据域分文件：quote（实时行情）/ kline（日K）/ minute（分时）/ stock（股票条目）/ group（组合聚合）/ snapshot（收盘快照）
- 生产端（stock_api / group_calc）必须经契约构造输出（`to_dict()`）；前端字段名以契约为准
- 改字段流程：先改 data_define → 同步生产端与前端 → 补测试（tests/test_data_define.py）
- `from_dict` 容错（缺失字段为 None、未知字段忽略），保证旧版本快照仍可加载
- **历史库唯一维护处 core/history/**：SQLite 永久保存采集数据和不可变版本；表结构、字段含义、索引、口径、版本迁移和维护命令见 [docs/数据库设计.md](docs/数据库设计.md)。修改前必须阅读；禁止覆写历史事实或拼接不同前复权版本。MarketSnapshot 保留为旧 JSON 兼容契约，启动时导入旧快照并保留原文件。
- **数据源统一入口 core/data_source.py**：组件一律经它取数（不直接 import stock_api 或数据库）；在线先入库再读回，离线固定数据版本、不联网。新增数据字段在 data_define/history.py 或所属域定义；新增采集需求在 history/settings.py 汇总。模式切换通过 context_key 失效后端缓存，历史计算参数经 get_config 读取。
- 后台 history.collect 汇总全部组件数据需求，收盘自动保存到点主动触发并布防下一工作日。缺失数据明确提示，不能用今天的数据或其他复权口径补成完整历史。

## 新增组件流程
1. `components/<id>/component.py`：Component 子类（声明 id / title / embed_height），`create_api(scheduler)` 返回 API 对象；后台刷新任务用 `scheduler.add()` 注册，**不要自开线程**
2. `ui.html`：引入 `../../assets/shared.css` 与 `shared.js`；卡片标题栏保留 `pywebview-drag-region` 类（嵌入时由 forwardWindowMove 转发拖动）
3. API 方法名带组件前缀（如 `get_group_*`）；与其他组件重名会在启动时直接报错
4. app.py 零改动，重启即自动出现在窗口里

## 业务口径
- 组合 = 本金 PRINCIPAL 均分建仓于日K窗口首日开盘价，持有不动（份额计算见 core/group_calc.py）
- **¥ 是绝对度量；百分比一律相对建仓本金**
- 个股行情涨跌幅按用户要求直接显示接口原始 `change_pct`（相对昨收价）；组合收益率仍相对建仓本金。
- 修改 config.py 股票列表后，必须用行情接口逐一核对名称与代码（历史上 10 只里有 6 只代码与名称对不上）

## 技术约束（踩过的坑）
- pywebview 桥接函数在 **worker 线程**执行：窗口移动/缩放禁用跨线程 WM 消息（进不了系统移动/缩放循环），统一走程序化 `move_to` / `resize_to`（shared.js 已封装好绑定）
- 取窗口句柄**禁用 GetForegroundWindow**（会拿到别的窗口），用 `core.window_utils.find_own_hwnd()`（按进程ID + WinForms 类名枚举）
- iframe 内的事件不会冒泡到外壳文档：组件页桥接一律用 shared.js 的 `api()`（自动穿透父页面）+ `whenBridgeReady()`
- `legacy/` 是历史归档，不要修改；`stock_dashboard` 是被系统占用的空目录，删不掉，忽略
- git 的 LF/CRLF 警告是换行转换提示，可忽略

## 测试与验证分工
- 单元测试（tests/test_group_calc.py）必须通过后再交付；新增计算逻辑必须配套测试（合成数据、不依赖网络）
- 提交/打包前的离线测试按**流水线同款清单全量**跑（`.github/workflows/windows-release.yml`「离线回归测试」列出的全部套件）——只跑改动相关测试曾让带 bug 的版本发布出去（2026-11-02 high/low 漏转 float 事故）
- **AI 弹窗自验**：界面类改动后 AI 运行 `python app.py` 打开窗口亲自查看渲染与报错上屏，并核对 `logs/app.log` 无新增异常；这是交用户前的第一道关，不是替用户做验证
- **窗口拖动、缩放等交互操作与最终界面验收由用户手动进行，不要替用户做**；不要主动运行真实鼠标自动化（gui_drag_test.py），除非用户明确要求
- 弹窗自验通过后重启交用户验证，等用户确认结果

## Git 约定
- **每次重构、每个新功能、每个修复 = 一个独立提交；不要把多个不相关改动揉进一次提交**
- 完成修改并通过相应验证后自动进行本地 Git 提交；界面/交互类改动仍按下文等待用户验证。
- 提交信息用中文，说明「做了什么 + 为什么」
- 新功能提交使用 `feat: 中文说明` 或 `feat(组件): 中文说明`；修复使用 `fix: 中文说明`，文档使用 `docs: 中文说明`。GitHub 流水线累计 5 个尚未发布的 feat 提交后自动打包发布，规则见 README.md。
- 界面/交互类改动先经用户验证，再提交
- `__pycache__` 已由 .gitignore 排除，不要提交


## 开发节奏：先讨论、先验证、后打包（2026-11-02 事故固化）
- **新功能先讨论定案再动手**：呈现方式、数据口径、降级行为在讨论中定死，结论落到 docs/（呈现方案见《成交量呈现设计》、字段格式见《数据接口契约》）再写代码；讨论认可了方案 ≠ 免除验证
- **验证未过不打包**：打包 EXE / 推送触发发布的前置条件 = 全量离线测试通过 + AI 弹窗自验通过 + **用户界面确认**，三者缺一不可
- **发布未核对不算结束**：推送后确认流水线绿灯、核对 Release 产物与《发布版本》对照表登记；上游接口故障（如腾讯 fqkline 501）造成的 WARNING 要与本程序 bug 区分，如实说明
