#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证滑动股票切换功能的简单测试
"""
import time
import sys
from widget import Api

def test_api():
    print("=== 验证滑动股票切换功能 ===")
    
    api = Api()
    
    # 测试获取第一支股票数据
    print("\n1. 测试第一支股票数据获取...")
    stock1 = api.get_realtime()
    if stock1:
        print(f"✅ 第一支股票: {stock1['name']} ({stock1['code']})")
        print(f"   价格: {stock1['price']} 元")
        print(f"   涨跌幅: {stock1['change_pct']}%")
    else:
        print("❌ 第一支股票数据获取失败")
    
    # 测试获取第二支股票数据
    print("\n2. 测试第二支股票数据获取...")
    stock2 = api.get_realtime("sz000725")
    if stock2:
        print(f"✅ 第二支股票: {stock2['name']} ({stock2['code']})")
        print(f"   价格: {stock2['price']} 元")
        print(f"   涨跌幅: {stock2['change_pct']}%")
    else:
        print("❌ 第二支股票数据获取失败")
    
    # 测试分时数据
    print("\n3. 测试分时数据获取...")
    minute_data = api.get_minute_data()
    if minute_data:
        print(f"✅ 分时数据获取成功: {len(minute_data)} 个数据点")
    else:
        print("❌ 分时数据获取失败")
    
    # 测试切换股票索引功能
    print("\n4. 测试股票索引切换...")
    # 模拟切换到第二支股票
    if api.set_stock_index(1):
        print("✅ 股票索引切换成功")
        current_stock = api.get_realtime()
        if current_stock:
            print(f"   当前股票: {current_stock['name']} ({current_stock['code']})")
        else:
            print("❌ 切换后数据获取失败")
    else:
        print("❌ 股票索引切换失败")
    
    # 测试缓存功能
    print("\n5. 测试数据缓存...")
    first_data = api.get_realtime()
    time.sleep(2)
    second_data = api.get_realtime()
    
    if first_data and second_data and first_data == second_data:
        print("✅ 数据缓存正常工作")
    else:
        print("❌ 数据缓存可能存在问题")
    
    print("\n=== 验证完成 ===")
    return True

if __name__ == "__main__":
    test_api()