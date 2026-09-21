# -*- coding: utf-8 -*-
"""
环境检查脚本
"""
import sys
import importlib.util

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version >= (3, 7):
        print("✅ Python版本符合要求 (>= 3.7)")
        return True
    else:
        print("❌ Python版本过低，需要3.7或更高")
        return False

def check_dependencies():
    """检查依赖"""
    dependencies = ['pywebview', 'requests']
    missing = []
    
    for dep in dependencies:
        spec = importlib.util.find_spec(dep)
        if spec is None:
            missing.append(dep)
            print(f"❌ {dep} 未安装")
        else:
            print(f"✅ {dep} 已安装")
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        return False
    else:
        print("\n所有依赖都已安装")
        return True

def show_usage():
    """显示使用方法"""
    print("\n" + "="*50)
    print("使用方法:")
    print("="*50)
    print("1. 如果缺少依赖，请运行:")
    print("   pip install pywebview requests")
    print("\n2. 运行程序:")
    print("   python widget.py")
    print("\n3. 或使用启动脚本:")
    print("   python run_widget.py")
    print("="*50)

if __name__ == "__main__":
    print("="*50)
    print("环境检查")
    print("="*50)
    
    check_python_version()
    deps_ok = check_dependencies()
    
    show_usage()
    
    if deps_ok:
        print("\n环境检查通过，可以运行程序！")
    else:
        print("\n环境检查失败，请先安装缺少的依赖")