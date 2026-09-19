# -*- coding: utf-8 -*-
"""
模拟前端调用API
"""
import time
from widget import Api, STOCKS

def simulate_frontend_calls():
    """模拟前端调用"""
    print("=== 模拟前端API调用 ===")
    
    # 创建API实例
    api = Api()
    
    # 模拟前端轮询调用
    for i in range(3):  # 模拟3次调用
        print(f"\n--- 第 {i+1} 次调用 ---")
        
        # 获取当前股票
        current_stock = STOCKS[api.current_stock_index]
        print(f"当前股票: {current_stock['name']} ({current_stock['code']})")
        
        # 调用实时数据
        try:
            realtime = api.get_realtime()
            if realtime:
                print(f"✅ 实时数据: {realtime['name']} - {realtime['price']}")
                print(f"   涨跌: {realtime['change']} ({realtime['change_pct']}%)")
            else:
                print("❌ 实时数据: 无数据")
        except Exception as e:
            print(f"❌ 实时数据错误: {e}")
        
        # 调用分时数据
        try:
            minute_data = api.get_minute_data()
            if minute_data:
                print(f"✅ 分时数据: {len(minute_data)} 个数据点")
                if len(minute_data) > 0:
                    latest = minute_data[-1]
                    print(f"   最新: {latest['time']} - {latest['price']}")
            else:
                print("❌ 分时数据: 无数据")
        except Exception as e:
            print(f"❌ 分时数据错误: {e}")
        
        # 调用K线数据
        try:
            kline_data = api.get_kline()
            if kline_data:
                print(f"✅ K线数据: {len(kline_data)} 个数据点")
                if len(kline_data) > 0:
                    latest = kline_data[-1]
                    print(f"   最新: {latest['date']} - {latest['close']}")
            else:
                print("❌ K线数据: 无数据")
        except Exception as e:
            print(f"❌ K线数据错误: {e}")
        
        # 切换到下一个股票
        api.next_stock()
        print(f"切换到下一个股票: {STOCKS[api.current_stock_index]['name']}")
        
        # 等待一下
        time.sleep(1)
    
    print("\n=== 模拟完成 ===")

if __name__ == "__main__":
    simulate_frontend_calls()