# -*- coding: utf-8 -*-
"""
仅测试数据获取，不启动webview
"""
import stock_api

def test_all_stocks():
    print("=== 测试所有股票数据获取 ===")
    
    # 测试列表
    test_stocks = [
        ("瑞芯微", "sh603893"),
        ("兆易创新", "sh603986"),
        ("翱捷科技-U", "sh688082"),
        ("龙迅股份", "sh688222"),
        ("中科蓝汛", "sh688023"),
        ("乐鑫科技", "sh688018"),
        ("晶晨股份", "sh688099"),
        ("全志科技", "sz300078"),
        ("恒玄科技", "sh688608"),
        ("炬芯科技", "sh688268")
    ]
    
    success_count = 0
    fail_count = 0
    
    for name, code in test_stocks:
        print(f"\n--- 测试 {name} ({code}) ---")
        
        try:
            # 测试实时数据
            realtime = stock_api.get_realtime(code)
            if realtime:
                print(f"✅ 实时数据: {realtime['name']} - {realtime['price']} (涨跌幅: {realtime['change_pct']}%)")
                success_count += 1
            else:
                print("❌ 实时数据获取失败")
                fail_count += 1
                continue
                
        except Exception as e:
            print(f"❌ 实时数据错误: {e}")
            fail_count += 1
            continue
            
        try:
            # 测试分时数据
            minute_data = stock_api.get_minute_data(code)
            if minute_data and len(minute_data) > 0:
                print(f"✅ 分时数据: {len(minute_data)} 个数据点")
                success_count += 1
            else:
                print("❌ 分时数据获取失败")
                fail_count += 1
        except Exception as e:
            print(f"❌ 分时数据错误: {e}")
            fail_count += 1
            
        try:
            # 测试K线数据
            kline_data = stock_api.get_kline(code, count=3)
            if kline_data and len(kline_data) > 0:
                print(f"✅ K线数据: {len(kline_data)} 个数据点")
                success_count += 1
            else:
                print("❌ K线数据获取失败")
                fail_count += 1
        except Exception as e:
            print(f"❌ K线数据错误: {e}")
            fail_count += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"总计: {success_count + fail_count}")
    
    if fail_count == 0:
        print("🎉 所有股票数据获取成功！")
    else:
        print(f"⚠️  {fail_count} 个股票的数据获取失败")

if __name__ == "__main__":
    test_all_stocks()