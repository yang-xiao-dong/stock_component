# -*- coding: utf-8 -*-
"""使用 PyInstaller 构建可直接分发的 Windows 单文件 EXE。"""
import argparse
import os
import re
import subprocess
import sys
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


def pyinstaller_args(version=__version__, dist_dir=DEFAULT_DIST_DIR):
    """生成 PyInstaller 参数；拆出纯函数便于离线测试。"""
    display_version, numeric_version = parse_version(version)
    dist_dir = Path(dist_dir).resolve()
    work_dir = PROJECT_ROOT / "build" / "pyinstaller"
    spec_dir = PROJECT_ROOT / "build"
    version_file = write_version_info(
        PROJECT_ROOT / "build" / "generated" / "version_info.txt",
        display_version,
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


def build(version=__version__, dist_dir=DEFAULT_DIST_DIR):
    """执行构建并返回 EXE 路径。"""
    args, output = pyinstaller_args(version, dist_dir)
    command = [sys.executable, "-m", "PyInstaller", *args]
    print(f"正在构建 {PRODUCT_NAME} v{version} …", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    if not output.is_file():
        raise RuntimeError(f"构建结束但未找到产物：{output}")
    print(f"构建完成：{output}", flush=True)
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
    args = parser.parse_args(argv)
    try:
        build(args.version, args.dist_dir)
    except (ValueError, subprocess.CalledProcessError, RuntimeError) as exc:
        parser.exit(1, f"打包失败：{exc}\n")
