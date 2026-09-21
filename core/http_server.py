# -*- coding: utf-8 -*-
"""本地静态服务：让单窗口外壳能以同源 iframe 嵌入各组件页面。

- 只监听 127.0.0.1（随机端口），仅本机可访问
- 路径白名单：只允许 assets/ 与 components/ 下的文件
"""
import http.server
import os
import threading

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ALLOWED_PREFIXES = ("/assets/", "/components/")


class _Handler(http.server.SimpleHTTPRequestHandler):

    # 由 start() 注入的虚拟文件 {url路径: bytes}（如动态生成的 shell 页）
    extra_files = {}

    def do_GET(self):
        extra = self.extra_files.get(self.path)
        if extra is not None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(extra)))
            self.end_headers()
            self.wfile.write(extra)
            return
        super().do_GET()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_ROOT, **kwargs)

    def translate_path(self, path):
        # 白名单外的路径映射到不存在的文件，返回 404
        if not any(path.startswith(p) for p in _ALLOWED_PREFIXES):
            return os.path.join(_ROOT, "__forbidden__")
        return super().translate_path(path)

    def log_message(self, *args):
        pass  # 静默访问日志


def start(extra_files=None):
    """启动静态服务，返回 (server, base_url)。extra_files 为动态生成的页面。"""
    _Handler.extra_files = {k: v for k, v in (extra_files or {}).items()}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return server, base_url
