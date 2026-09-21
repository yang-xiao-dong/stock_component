# -*- coding: utf-8 -*-
"""股票API测试脚本"""
import time
from stock_api import get_realtime, get_minute_data, get_kline

# 测试的股票列表
TEST_STOCKS = [
    {"code": "sh603893", "name": "瑞芯微"},
    {"code": "sh603986", "name": "兆易创新"},
    {"code": "sh688082", "name": "翱捷科技-U"},
    {"code": "sh688222", "name": "龙迅股份"},
    {"code": "sh688023", "name": "中科蓝汛"},
    {"code": "sh688018", "name": "乐鑫科技"},
    {"code": "sh688099", "name": "晶晨股份"},
    {"code": "sh300078", "name": "全志科技"},
    {"code": "sh688608", "name": "恒玄科技"},
    {"code": "sh688268", "name": "炬芯科技"},
]

def test_api():
    print("=" * 60)
    print("股票API测试报告")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试股票数量: {len(TEST_STOCKS)}")
    print()
    
    success_count = 0
    error_count = 0
    
    for stock in TEST_STOCKS:
        code = stock["code"]
        name = stock["name"]
        print(f"测试 {name} ({code}):", end="")
        
        # 测试实时数据
        realtime = get_realtime(code)
        if realtime and realtime["name"]:
            print(" ✅ 实时数据", end="")
        else:
            print(" ❌ 实时数据", end="")
            
        # 测试分时数据
        minute = get_minute_data(code)
        if minute and len(minute) > 0:
            print(" ✅ 分时数据", end="")
        else:
            print(" ❌ 分时数据", end="")
            
        # 测试K线数据
        kline = get_kline(code, count=10)
        if kline and len(kline) > 0:
            print(" ✅ K线数据")
        else:
            print(" ❌ K线数据")
            
        if realtime and realtime["name"] and minute and len(minute) > 0 and kline and len(kline) > 0:
            success_count += 1
        else:
            error_count += 1
    
    print()
    print("=" * 60)
    print(f"测试结果: {success_count}/{len(TEST_STOCKS)} 只股票正常")
    print(f"正常: {success_count} 只")
    print(f"异常: {error_count} 只")
    
    if error_count > 0:
        print("\n异常股票详情:")
        for stock in TEST_STOCKS:
            code = stock["code"]
            name = stock["name"]
            realtime = get_realtime(code)
            minute = get_minute_data(code)
            kline = get_kline(code, count=10)
            
            if not (realtime and realtime["name"] and minute and len(minute) > 0 and kline and len(kline) > 0):
                print(f"- {name}: 实时数据{'正常' if realtime and realtime['name'] else '异常'}, "
                      f"分时数据{'正常' if minute and len(minute) > 0 else '异常'}, "
                      f"K线数据{'正常' if kline and len(kline) > 0 else '异常'}")
    
    print("=" * 60)
    print("测试完成!")

if __name__ == "__main__":
    test_api()