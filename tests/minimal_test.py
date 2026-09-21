# -*- coding: utf-8 -*-
"""
最小化测试 - 专门验证数据加载问题
"""
import webview
import time
from stock_api import get_realtime, get_minute_data, get_kline

# 简单的API类
class SimpleApi:
    def __init__(self):
        print("API初始化完成")
    
    def get_realtime(self):
        print("调用get_realtime...")
        try:
            data = get_realtime("sh603893")
            print(f"获取数据成功: {data is not None}")
            if data:
                print(f"股票名称: {data.get('name', 'N/A')}")
                print(f"股票代码: {data.get('code', 'N/A')}")
                print(f"当前价格: {data.get('price', 'N/A')}")
            return data
        except Exception as e:
            print(f"获取数据失败: {e}")
            return None
    
    def get_minute_data(self):
        print("调用get_minute_data...")
        try:
            data = get_minute_data("sh603893")
            print(f"分时数据成功: {data is not None}, 点数: {len(data) if data else 0}")
            return data
        except Exception as e:
            print(f"分时数据失败: {e}")
            return None
    
    def get_kline(self):
        print("调用get_kline...")
        try:
            data = get_kline("sh603893", count=5)
            print(f"K线数据成功: {data is not None}, 点数: {len(data) if data else 0}")
            return data
        except Exception as e:
            print(f"K线数据失败: {e}")
            return None

def main():
    print("=== 最小化测试开始 ===")
    
    # 测试API
    api = SimpleApi()
    
    print("\n--- 测试实时数据 ---")
    realtime = api.get_realtime()
    print(f"实时数据结果: {realtime}")
    
    print("\n--- 测试分时数据 ---")
    minute = api.get_minute_data()
    print(f"分时数据结果: {minute}")
    
    print("\n--- 测试K线数据 ---")
    kline = api.get_kline()
    print(f"K线数据结果: {kline}")
    
    if realtime and minute and kline:
        print("\n✅ 所有数据获取成功！")
        print("准备创建webview窗口...")
        
        # 创建HTML界面
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>数据测试</title>
            <style>
                body {{ font-family: Arial; padding: 20px; }}
                .data {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .success {{ background: #d4edda; }}
                .error {{ background: #f8d7da; }}
            </style>
        </head>
        <body>
            <h1>数据加载测试</h1>
            <div id="realtime" class="data">实时数据加载中...</div>
            <div id="minute" class="data">分时数据加载中...</div>
            <div id="kline" class="data">K线数据加载中...</div>
            <script>
                async function loadData() {{
                    console.log('开始加载数据...');
                    
                    try {{
                        const rt = await pywebview.api.get_realtime();
                        console.log('实时数据:', rt);
                        const realtimeEl = document.getElementById('realtime');
                        if (rt) {{
                            realtimeEl.innerHTML = `<strong>✅ 实时数据</strong><br>股票: ${{rt.name}} (${{rt.code}})<br>价格: ${{rt.price}}<br>涨跌: ${{rt.change}} (${{rt.change_pct}}%)`;
                            realtimeEl.className = 'data success';
                        }} else {{
                            realtimeEl.innerHTML = '<strong>❌ 实时数据获取失败</strong>';
                            realtimeEl.className = 'data error';
                        }}
                    }} catch (e) {{
                        console.error('实时数据错误:', e);
                        document.getElementById('realtime').innerHTML = '<strong>❌ 实时数据错误: ' + e.message + '</strong>';
                        document.getElementById('realtime').className = 'data error';
                    }}
                    
                    try {{
                        const minute = await pywebview.api.get_minute_data();
                        console.log('分时数据:', minute);
                        const minuteEl = document.getElementById('minute');
                        if (minute) {{
                            minuteEl.innerHTML = `<strong>✅ 分时数据</strong><br>数据点数: ${{minute.length}}<br>最新: ${{minute[minute.length-1].time}} - ${{minute[minute.length-1].price}}`;
                            minuteEl.className = 'data success';
                        }} else {{
                            minuteEl.innerHTML = '<strong>❌ 分时数据获取失败</strong>';
                            minuteEl.className = 'data error';
                        }}
                    }} catch (e) {{
                        console.error('分时数据错误:', e);
                        document.getElementById('minute').innerHTML = '<strong>❌ 分时数据错误: ' + e.message + '</strong>';
                        document.getElementById('minute').className = 'data error';
                    }}
                    
                    try {{
                        const kline = await pywebview.api.get_kline();
                        console.log('K线数据:', kline);
                        const klineEl = document.getElementById('kline');
                        if (kline) {{
                            klineEl.innerHTML = `<strong>✅ K线数据</strong><br>数据点数: ${{kline.length}}<br>最新: ${{kline[kline.length-1].date}} - ${{kline[kline.length-1].close}}`;
                            klineEl.className = 'data success';
                        }} else {{
                            klineEl.innerHTML = '<strong>❌ K线数据获取失败</strong>';
                            klineEl.className = 'data error';
                        }}
                    }} catch (e) {{
                        console.error('K线数据错误:', e);
                        document.getElementById('kline').innerHTML = '<strong>❌ K线数据错误: ' + e.message + '</strong>';
                        document.getElementById('kline').className = 'data error';
                    }}
                }}
                
                // 页面加载完成后立即加载数据
                window.addEventListener('load', loadData);
            </script>
        </body>
        </html>
        """
        
        # 创建窗口
        window = webview.create_window(
            "数据加载测试",
            html=html_content,
            js_api=api,
            width=500,
            height=400,
            resizable=True
        )
        
        print("✅ webview窗口创建成功")
        print("如果窗口显示正常，请检查数据是否正确加载")
        print("如果看不到数据，请查看浏览器控制台的错误信息")
        
        # 启动webview
        webview.start()
        
    else:
        print("\n❌ 数据获取失败，无法创建窗口")

if __name__ == "__main__":
    main()