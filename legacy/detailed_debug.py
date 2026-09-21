# -*- coding: utf-8 -*-
"""
详细调试脚本 - 检查无数据问题
"""
import sys
import time
from stock_api import get_realtime, get_minute_data, get_kline

def test_widget_data_flow():
    """测试widget数据流"""
    print("=== Widget数据流测试 ===")
    
    # 模拟STOCKS列表
    STOCKS = [
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
    
    # 模拟Api类的行为
    class MockApi:
        def __init__(self):
            self.current_stock_index = 0
            self.stock_data = {}
            self.update_all_stock_data()
        
        def update_all_stock_data(self):
            """更新所有股票数据"""
            for stock in STOCKS:
                try:
                    self.stock_data[stock["code"]] = get_realtime(stock["code"])
                    if self.stock_data[stock["code"]]:
                        self.stock_data[stock["code"]]["timestamp"] = time.time()
                    print(f"✅ {stock['name']}: 数据获取成功")
                except Exception as e:
                    self.stock_data[stock["code"]] = None
                    print(f"❌ {stock['name']}: 错误 - {e}")
        
        def get_realtime(self, code=None):
            """获取实时数据"""
            if code is None:
                code = STOCKS[self.current_stock_index]["code"]
            
            # 检查缓存
            cached_data = self.stock_data.get(code)
            if cached_data and time.time() - cached_data.get("timestamp", 0) <= 10:
                return cached_data
            
            # 重新获取
            try:
                data = get_realtime(code)
                if data:
                    data["timestamp"] = time.time()
                    return data
            except Exception as e:
                print(f"❌ 获取实时数据失败: {e}")
            
            return None
    
    # 测试Api类
    api = MockApi()
    
    # 测试get_realtime
    print("\n--- 测试get_realtime方法 ---")
    for i, stock in enumerate(STOCKS):
        try:
            result = api.get_realtime(stock["code"])
            if result:
                print(f"✅ {stock['name']}: {result['name']} - {result['price']}")
            else:
                print(f"❌ {stock['name']}: 无数据")
        except Exception as e:
            print(f"❌ {stock['name']}: 错误 - {e}")
    
    # 测试分时数据
    print("\n--- 测试分时数据 ---")
    current_stock = STOCKS[api.current_stock_index]
    try:
        minute_data = get_minute_data(current_stock["code"])
        if minute_data:
            print(f"✅ {current_stock['name']} 分时数据: {len(minute_data)} 个点")
            if len(minute_data) > 0:
                print(f"   最新: {minute_data[-1]}")
        else:
            print(f"❌ {current_stock['name']} 分时数据: 无数据")
    except Exception as e:
        print(f"❌ {current_stock['name']} 分时数据错误: {e}")
    
    # 测试K线数据
    print("\n--- 测试K线数据 ---")
    try:
        kline_data = get_kline(current_stock["code"], count=5)
        if kline_data:
            print(f"✅ {current_stock['name']} K线数据: {len(kline_data)} 个点")
            if len(kline_data) > 0:
                print(f"   最新: {kline_data[-1]}")
        else:
            print(f"❌ {current_stock['name']} K线数据: 无数据")
    except Exception as e:
        print(f"❌ {current_stock['name']} K线数据错误: {e}")

def test_webview_integration():
    """测试webview集成"""
    print("\n=== Webview集成测试 ===")
    
    try:
        import webview
        print("✅ pywebview导入成功")
        
        # 创建测试窗口
        def test_api():
            try:
                from stock_api import get_realtime
                rt = get_realtime("sh603893")
                return rt if rt else {"error": "无数据"}
            except Exception as e:
                return {"error": str(e)}
        
        api = type('Api', (), {'get_realtime': test_api})()
        
        print("创建测试窗口...")
        window = webview.create_window(
            "测试窗口",
            html="<h1>测试窗口</h1><p>如果看到这个窗口，说明webview正常工作</p>",
            js_api=api,
            width=300,
            height=200,
        )
        
        print("✅ webview窗口创建成功")
        
        # 不实际启动窗口，只是测试创建
        print("Webview测试完成")
        
    except Exception as e:
        print(f"❌ webview测试失败: {e}")

if __name__ == "__main__":
    test_widget_data_flow()
    test_webview_integration()
    print("\n=== 调试完成 ===")