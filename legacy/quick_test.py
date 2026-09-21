# -*- coding: utf-8 -*-
"""
快速测试脚本
"""
import sys
import os

print("=== 股价监控系统快速测试 ===")
print()

# 检查文件是否存在
files = ['widget.py', 'ui.html', 'stock_api.py', 'test_widget_api.py']
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file} 不存在")

print()

# 测试API
try:
    from stock_api import get_realtime
    rt = get_realtime()
    if rt:
        print(f"✅ API测试成功: {rt['name']} ({rt['code']})")
        print(f"   价格: {rt['price']:.2f}")
        print(f"   涨跌: {rt['change_pct']:.2f}%")
    else:
        print("❌ API测试失败")
except Exception as e:
    print(f"❌ API测试错误: {e}")

print()
print("=== 测试完成 ===")
print()
print("运行方式:")
print("python widget.py          # 直接运行")
print("python run_widget.py      # 使用启动脚本")