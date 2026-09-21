# -*- coding: utf-8 -*-
"""调试API数据加载问题"""
import time
from stock_api import get_realtime, get_minute_data, get_kline

def test_single_stock():
    print("=== 单个股票API测试 ===")
    
    # 测试瑞芯微
    stock_code = "sh603893"
    stock_name = "瑞芯微"
    
    print(f"测试 {stock_name} ({stock_code}):")
    
    # 测试实时数据
    print("1. 测试实时数据...")
    try:
        realtime = get_realtime(stock_code)
        if realtime:
            print(f"   ✅ 实时数据获取成功")
            print(f"   名称: {realtime.get('name', 'N/A')}")
            print(f"   价格: {realtime.get('price', 'N/A')}")
            print(f"   涨跌: {realtime.get('change_pct', 'N/A')}%")
            print(f"   时间: {realtime.get('time', 'N/A')}")
        else:
            print("   ❌ 实时数据获取失败")
    except Exception as e:
        print(f"   ❌ 实时数据错误: {e}")
    
    # 测试分时数据
    print("\n2. 测试分时数据...")
    try:
        minute_data = get_minute_data(stock_code)
        if minute_data:
            print(f"   ✅ 分时数据获取成功，共 {len(minute_data)} 个数据点")
            if len(minute_data) > 0:
                print(f"   最新数据: {minute_data[-1]}")
        else:
            print("   ❌ 分时数据获取失败")
    except Exception as e:
        print(f"   ❌ 分时数据错误: {e}")
    
    # 测试K线数据
    print("\n3. 测试K线数据...")
    try:
        kline_data = get_kline(stock_code, count=5)
        if kline_data:
            print(f"   ✅ K线数据获取成功，共 {len(kline_data)} 个数据点")
            if len(kline_data) > 0:
                print(f"   最新数据: {kline_data[-1]}")
        else:
            print("   ❌ K线数据获取失败")
    except Exception as e:
        print(f"   ❌ K线数据错误: {e}")

def test_network_connection():
    print("\n=== 网络连接测试 ===")
    
    import requests
    try:
        # 测试腾讯股票接口
        url = "https://qt.gtimg.cn/q=sh603893"
        response = requests.get(url, timeout=10)
        print(f"✅ 网络连接正常")
        print(f"   响应状态: {response.status_code}")
        print(f"   响应大小: {len(response.text)} 字符")
        
        # 检查响应内容
        if "瑞芯微" in response.text:
            print("   ✅ 响应内容包含股票名称")
        else:
            print("   ❌ 响应内容异常")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络连接失败: {e}")

if __name__ == "__main__":
    test_single_stock()
    test_network_connection()
    print("\n=== 调试完成 ===")