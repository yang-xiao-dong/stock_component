# -*- coding: utf-8 -*-
"""组件装配层：组件基类、窗口级 API 路由（AppApi）与单窗口装配（assemble）。

架构分层：
    app.py（薄入口）→ components（自动发现的组件）→ core（数据/计算/窗口/调度）

组件约定：
- components/<id>/ 目录 = 一个组件：Component 子类（component.py）+ ui.html
- 组件 API 类只管数据与业务，不继承窗口控制（窗口由装配层统一提供）
- 组件 API 的公共方法在装配时挂到窗口 JS 接口上，重名冲突启动即报错
"""
from pathlib import Path
from html import escape
import threading

import webview

from config import APP_TITLE, WINDOW
from core import data_source, http_server
from core.runtime_paths import resource_path
from core.component_layout import ComponentLayoutStore
from core.scheduler import Scheduler
from core.window_utils import WindowControls


class Component:
    """组件基类：声明 id / 标题 / 界面文件与 API 工厂"""
    id = "component"
    title = "组件"
    ui = "ui.html"
    embed_height = 420  # 嵌入外壳时的 iframe 高度（px）

    @property
    def ui_path(self):
        # 打包后资源位于临时解包目录；开发时仍指向项目组件目录。
        return str(resource_path("components", self.id, self.ui))

    def create_api(self, scheduler=None):
        """创建该组件的前端 API 对象；scheduler 用于注册后台刷新任务"""
        raise NotImplementedError


class AppApi(WindowControls):
    """窗口级接口：组件切换 + 窗口控制；组件接口通过 mount() 动态挂载"""

    def __init__(self, components, layout_store=None):
        WindowControls.__init__(self, min_size=tuple(WINDOW["min"]),
                                max_size=tuple(WINDOW["max"]))
        self._components = list(components)
        self._by_id = {c.id: c for c in self._components}
        self._mounted = set()
        self._layout_store = layout_store if layout_store is not None else ComponentLayoutStore()
        self._layout_lock = threading.Lock()
        self._component_order = self._layout_store.load(list(self._by_id))

    def get_components(self):
        """组件清单（前端信息用）"""
        return [{"id": c.id, "title": c.title} for c in self._components]

    def get_component_order(self):
        with self._layout_lock:
            return list(self._component_order)

    def set_component_order(self, order):
        """保存完整排列；保存失败时保留当前顺序。"""
        with self._layout_lock:
            if not self._layout_store.save(order, list(self._by_id)):
                return False
            self._component_order = list(order)
            return True

    # ---------- 数据模式（在线/离线快照）：窗口级，作用于全部组件 ----------

    def get_data_mode(self):
        return data_source.get_mode()

    def set_data_mode(self, mode, date=None):
        """切换 online/offline；offline 需给快照日期，成功后由前端重载组件页面"""
        return data_source.set_mode(mode, date)

    def list_snapshots(self):
        return data_source.list_snapshots()

    def capture_snapshot(self):
        """抓取当前整组数据并存为当日快照"""
        return data_source.capture_today()

    def switch_component(self, comp_id):
        """在当前窗口内切换到指定组件页面"""
        comp = self._by_id.get(str(comp_id))
        if not comp or self._window is None:
            return False
        try:
            self._window.load_url(Path(comp.ui_path).as_uri())
            self._window.set_title(comp.title)
            return True
        except Exception as e:
            print(f"切换组件失败: {e}")
            return False

    def mount(self, component, api_obj):
        """把组件 API 的公共方法暴露到窗口 JS 接口（重名冲突启动即报错）"""
        for name in dir(api_obj):
            if name.startswith("_"):
                continue
            fn = getattr(api_obj, name)
            if not callable(fn):
                continue
            if name in self._mounted or hasattr(self, name):
                raise RuntimeError(f"组件 '{component.id}' 的接口 '{name}' 与已有接口重名，请加组件前缀")
            self._mounted.add(name)
            self._window.expose(fn)


def assemble(components):
    """装配并启动单窗口应用：本地静态服务 → 动态生成外壳页（上下堆叠组件，可滚动）
    → 建窗 → 挂载组件 API → 起调度器 → 进入主循环"""
    components = list(components)
    scheduler = Scheduler()
    api = AppApi(components)

    # 按发现的组件生成外壳槽位（新增组件零改动出现在窗口里）
    shell_tpl = resource_path("assets", "shell.html").read_text(encoding="utf-8")
    positions = {component_id: index for index, component_id in enumerate(api.get_component_order())}
    slots = "\n    ".join(
        f'<iframe class="slot" data-component-id="{escape(c.id, quote=True)}" '
        f'title="{escape(c.title, quote=True)}" '
        f'style="height:{c.embed_height}px;order:{positions[c.id]}" '
        f'src="/components/{escape(c.id, quote=True)}/ui.html"></iframe>'
        for c in components
    )
    shell_html = (shell_tpl
                  .replace("<!-- COMPONENT SLOTS -->", slots)
                  .replace("{{APP_TITLE}}", APP_TITLE))

    _, base_url = http_server.start(extra_files={"/assets/shell.html": shell_html.encode("utf-8")})

    window = webview.create_window(
        APP_TITLE,
        f"{base_url}/assets/shell.html",
        js_api=api,
        width=WINDOW["width"],
        height=WINDOW["height"],
        x=WINDOW["x"],
        y=WINDOW["y"],
        min_size=tuple(WINDOW["min"]),
        resizable=True,
        frameless=True,
        on_top=True,
        easy_drag=False,
        transparent=False,
    )
    api.bind(window)

    for comp in components:
        api.mount(comp, comp.create_api(scheduler=scheduler))

    # 收盘自动快照：到收盘时刻主动触发一次（已存在当日快照则跳过），完成后再布防下一天
    data_source.arm_auto_save(scheduler)

    scheduler.start()
    webview.start()
