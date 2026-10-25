# -*- coding: utf-8 -*-
"""使用 PyInstaller 构建可直接分发的 Windows 单文件 EXE。"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from version import __version__


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIST_DIR = PROJECT_ROOT / "dist"
PRODUCT_NAME = "股票小组件"
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\.([0-9]+))?$")


def parse_version(value):
    """校验发布版本，并返回展示文本与 Windows 四段版本号。"""
    match = _VERSION_RE.fullmatch(str(value).strip())
    if not match:
        raise ValueError("版本号必须是 1.2.3 或 1.2.3.4 格式")
    numbers = tuple(int(v or 0) for v in match.groups())
    if any(v > 65535 for v in numbers):
        raise ValueError("版本号每一段必须在 0 到 65535 之间")
    return str(value).strip(), numbers


def discover_component_modules(root=PROJECT_ROOT):
    """发现所有组件模块，供 PyInstaller 收集动态导入。"""
    components_dir = Path(root) / "components"
    return [
        f"components.{path.parent.name}.component"
        for path in sorted(components_dir.glob("*/component.py"))
        if (path.parent / "ui.html").is_file()
    ]


def git_build_id():
    """构建唯一标识（GKI 式）：(短哈希, 完整哈希, 工作区是否含未提交改动)。

    版本号 + git 哈希（+dirty 标记）合起来唯一对应一次构建的源码状态；
    非 git 环境退化为占位符。
    """
    def run(*cmd):
        try:
            return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True,
                                  text=True, encoding="utf-8", errors="ignore").stdout.strip()
        except OSError:
            return ""
    full = run("git", "rev-parse", "HEAD")
    short = run("git", "rev-parse", "--short", "HEAD") or "nogit"
    dirty = bool(run("git", "status", "--porcelain"))
    return short, full, dirty


def display_version(version, short, dirty):
    """展示版本，如 1.2.6+g719d4e9 或 1.2.6+g719d4e9+dirty。"""
    return f"{version}+g{short}" + ("+dirty" if dirty else "")


BUILD_TABLE = PROJECT_ROOT / "docs" / "发布版本.md"
TABLE_HEADER = "| 展示版本 | git | 工作区 | 构建时间 | 备注 |"


def append_build_record(version, display, full_hash, dirty, note="", path=BUILD_TABLE):
    """发布对照表：builder 每次构建自动追加一行（表在库内长期维护）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if TABLE_HEADER not in existing:
        with path.open("a", encoding="utf-8") as stream:
            stream.write("# 发布对照表（builder 每次构建自动追加；展示版本 ↔ git 唯一对应）\n\n"
                         + TABLE_HEADER + "\n")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"| {display} | {full_hash[:12] or 'nogit'} | "
                     f"{'含未提交改动' if dirty else '干净'} | "
                     f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {note} |\n")


def write_version_info(path, display_version, numeric_version):
    """生成 Windows 文件属性中的产品/文件版本信息。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dotted = ".".join(str(v) for v in numeric_version)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric_version}, prodvers={numeric_version},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('080404B0', [
      StringStruct('CompanyName', '{PRODUCT_NAME}'),
      StringStruct('FileDescription', '{PRODUCT_NAME}'),
      StringStruct('FileVersion', '{dotted}'),
      StringStruct('InternalName', 'StockWidget'),
      StringStruct('OriginalFilename', '{PRODUCT_NAME}.exe'),
      StringStruct('ProductName', '{PRODUCT_NAME}'),
      StringStruct('ProductVersion', '{display_version}')])]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])]
)"""
    path.write_text(content, encoding="utf-8")
    return path


def pyinstaller_args(version=__version__, dist_dir=DEFAULT_DIST_DIR, display=None):
    """生成 PyInstaller 参数；拆出纯函数便于离线测试。display 为含构建标识的展示版本。"""
    display_version, numeric_version = parse_version(version)
    dist_dir = Path(dist_dir).resolve()
    work_dir = PROJECT_ROOT / "build" / "pyinstaller"
    spec_dir = PROJECT_ROOT / "build"
    version_file = write_version_info(
        PROJECT_ROOT / "build" / "generated" / "version_info.txt",
        display or display_version,
        numeric_version,
    )
    exe_name = f"{PRODUCT_NAME}-v{display_version}"
    args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", exe_name,
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--specpath", str(spec_dir),
        "--paths", str(PROJECT_ROOT),
        "--add-data", f"{PROJECT_ROOT / 'assets'}{os.pathsep}assets",
        "--add-data", f"{PROJECT_ROOT / 'components'}{os.pathsep}components",
        "--version-file", str(version_file),
        "--exclude-module", "tests",
    ]
    for module in discover_component_modules():
        args.extend(("--hidden-import", module))
    args.append(str(PROJECT_ROOT / "app.py"))
    return args, dist_dir / f"{exe_name}.exe"


def build(version=__version__, dist_dir=DEFAULT_DIST_DIR, note=""):
    """执行构建并返回 EXE 路径。产物带 git 唯一标识并登记发布对照表。"""
    short, full, dirty = git_build_id()
    display = display_version(version, short, dirty)
    if dirty:
        print(f"警告：工作区含未提交改动，本构建标识为 {display}；"
              f"要版本↔提交严格对应，请先提交再打包", flush=True)
    build_info = PROJECT_ROOT / "assets" / "build_info.json"
    build_info.write_text(json.dumps({
        "version": version, "display": display, "git": full, "short": short,
        "dirty": dirty, "built_at": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    args, output = pyinstaller_args(version, dist_dir, display)
    command = [sys.executable, "-m", "PyInstaller", *args]
    print(f"正在构建 {PRODUCT_NAME} {display} …", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    if not output.is_file():
        raise RuntimeError(f"构建结束但未找到产物：{output}")
    append_build_record(version, display, full, dirty, note)
    print(f"构建完成：{output}（{display}）", flush=True)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="构建版本化的股票小组件单文件 EXE")
    parser.add_argument(
        "--version", default=__version__,
        help=f"发布版本，默认读取 version.py（当前 {__version__}）",
    )
    parser.add_argument(
        "--dist-dir", type=Path, default=DEFAULT_DIST_DIR,
        help="产物目录，默认 dist/",
    )
    parser.add_argument("--note", default="", help="本次构建备注（写入发布对照表）")
    args = parser.parse_args(argv)
    try:
        build(args.version, args.dist_dir, args.note)
    except (ValueError, subprocess.CalledProcessError, RuntimeError) as exc:
        parser.exit(1, f"打包失败：{exc}\n")
