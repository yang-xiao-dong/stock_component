# -*- coding: utf-8 -*-
"""
股价监控系统启动脚本
避免使用bat文件，直接用Python运行
"""
import os
import sys
import subprocess
import platform

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("错误：需要Python 3.7或更高版本")
        print(f"当前版本：{sys.version}")
        return False
    return True

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import pywebview
        print("✅ pywebview 已安装")
    except ImportError:
        print("❌ pywebview 未安装")
        return False
    
    try:
        import requests
        print("✅ requests 已安装")
    except ImportError:
        print("❌ requests 未安装")
        return False
    
    return True

def install_dependencies():
    """安装依赖"""
    print("正在安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "requests"])
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败")
        return False

def show_stock_list():
    """显示支持的股票列表"""
    print("\n" + "="*50)
    print("支持的股票列表:")
    print("="*50)
    stocks = [
        ("1", "瑞芯微", "603893"),
        ("2", "兆易创新", "603986"),
        ("3", "翱捷科技-U", "688082"),
        ("4", "龙迅股份", "688222"),
        ("5", "中科蓝汛", "688023"),
        ("6", "乐鑫科技", "688018"),
        ("7", "晶晨股份", "688099"),
        ("8", "全志科技", "300078"),
        ("9", "恒玄科技", "688608"),
        ("10", "炬芯科技", "688268"),
    ]
    
    for num, name, code in stocks:
        print(f"{num}. {name} ({code})")
    print("="*50)
    print()

def main():
    """主函数"""
    print("=" * 60)
    print("股价监控系统 - 单窗口多股票版本")
    print("=" * 60)
    
    # 检查Python版本
    if not check_python_version():
        input("按回车键退出...")
        return
    
    # 显示股票列表
    show_stock_list()
    
    # 检查依赖
    if not check_dependencies():
        print("\n检测到缺少依赖，是否自动安装？(y/n): ", end="")
        choice = input().strip().lower()
        
        if choice == 'y':
            if install_dependencies():
                print("\n依赖安装完成，正在启动程序...")
            else:
                print("\n依赖安装失败，请手动安装：")
                print("pip install pywebview requests")
                input("按回车键退出...")
                return
        else:
            print("请手动安装依赖：")
            print("pip install pywebview requests")
            input("按回车键退出...")
            return
    else:
        print("\n依赖检查完成，正在启动程序...")
    
    # 运行主程序
    try:
        # 导入并运行主程序
        from widget import main as widget_main
        
        print("启动中...")
        print("提示：")
        print("- 使用 '← 上一个'/'下一个 →' 按钮切换股票")
        print("- 点击下拉菜单查看完整股票列表")
        print("- 点击 '分时'/'日K' 切换图表")
        print("- 5秒刷新股价，60秒刷新分时数据")
        print("- 关闭窗口可退出程序")
        print()
        
        # 启动主程序
        widget_main()
        
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"\n启动失败：{e}")
        print("请检查文件是否完整")
        input("按回车键退出...")

if __name__ == "__main__":
    main()