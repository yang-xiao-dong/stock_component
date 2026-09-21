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
python tests/gui_drag_test.py         # GUI 自动化（会移动真实鼠标；默认不运行，仅用户明确要求时用）
pip install pywebview requests        # 依赖
```

## 架构分层
app.py（薄入口：发现+装配）→ components/（组件，自动发现）→ core/（基础层）→ assets/（共享前端）

- `components/<id>/`：一个组件 = component.py（Component 子类）+ ui.html；外壳 shell.html 按发现结果动态生成 iframe 槽位
- `core/`：stock_api（行情抓取）、group_calc（组合计算，纯函数）、window_utils（窗口控制）、scheduler（统一后台刷新）、http_server（127.0.0.1 静态服务，供同源 iframe 嵌入）
- `assets/`：shell.html（外壳）、shared.css / shared.js（公共样式与工具：桥接穿透、格式化、Canvas 基础、缩放与移动绑定）

## 新增组件流程
1. `components/<id>/component.py`：Component 子类（声明 id / title / embed_height），`create_api(scheduler)` 返回 API 对象；后台刷新任务用 `scheduler.add()` 注册，**不要自开线程**
2. `ui.html`：引入 `../../assets/shared.css` 与 `shared.js`；卡片标题栏保留 `pywebview-drag-region` 类（嵌入时由 forwardWindowMove 转发拖动）
3. API 方法名带组件前缀（如 `get_group_*`）；与其他组件重名会在启动时直接报错
4. app.py 零改动，重启即自动出现在窗口里

## 业务口径
- 组合 = 本金 PRINCIPAL 均分建仓于日K窗口首日开盘价，持有不动（份额计算见 core/group_calc.py）
- **¥ 是绝对度量；百分比一律相对建仓本金**
- 修改 config.py 股票列表后，必须用行情接口逐一核对名称与代码（历史上 10 只里有 6 只代码与名称对不上）

## 技术约束（踩过的坑）
- pywebview 桥接函数在 **worker 线程**执行：窗口移动/缩放禁用跨线程 WM 消息（进不了系统移动/缩放循环），统一走程序化 `move_to` / `resize_to`（shared.js 已封装好绑定）
- 取窗口句柄**禁用 GetForegroundWindow**（会拿到别的窗口），用 `core.window_utils.find_own_hwnd()`（按进程ID + WinForms 类名枚举）
- iframe 内的事件不会冒泡到外壳文档：组件页桥接一律用 shared.js 的 `api()`（自动穿透父页面）+ `whenBridgeReady()`
- `legacy/` 是历史归档，不要修改；`stock_dashboard` 是被系统占用的空目录，删不掉，忽略
- git 的 LF/CRLF 警告是换行转换提示，可忽略

## 测试与验证分工
- 单元测试（tests/test_group_calc.py）必须通过后再交付；新增计算逻辑必须配套测试（合成数据、不依赖网络）
- **窗口拖动、缩放等交互操作与一切界面/交互验证由用户手动进行，不要替用户做**；不要主动运行真实鼠标自动化（gui_drag_test.py），除非用户明确要求
- 改动完成后重启 `python app.py` 交由用户验证，等用户确认结果

## Git 约定
- **每次重构、每个新功能、每个修复 = 一个独立提交；不要把多个不相关改动揉进一次提交**
- 提交信息用中文，说明「做了什么 + 为什么」
- 界面/交互类改动先经用户验证，再提交
- `__pycache__` 已由 .gitignore 排除，不要提交
