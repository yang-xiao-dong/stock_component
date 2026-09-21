# -*- coding: utf-8 -*-
"""
测试webview是否能正常启动
"""
import webview
import os

# 创建一个简单的HTML页面
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Webview测试</title>
    <style>
        body { font-family: Arial; padding: 20px; text-align: center; }
        .container { max-width: 600px; margin: 0 auto; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .info { background: #d1ecf1; color: #0c5460; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 Webview测试成功！</h1>
        <div class="status success">
            <h2>✅ Webview运行正常</h2>
            <p>如果您能看到这个窗口，说明pywebview已经正确安装并运行。</p>
        </div>
        <div class="status info">
            <h3>📊 测试股票数据</h3>
            <p>支持的股票：</p>
            <ul>
                <li>瑞芯微 (603893)</li>
                <li>兆易创新 (603986)</li>
                <li>翱捷科技-U (688082)</li>
                <li>龙迅股份 (688222)</li>
                <li>中科蓝汛 (688023)</li>
                <li>乐鑫科技 (688018)</li>
                <li>晶晨股份 (688099)</li>
                <li>全志科技 (300078)</li>
                <li>恒玄科技 (688608)</li>
                <li>炬芯科技 (688268)</li>
            </ul>
        </div>
        <div class="status info">
            <h3>🔧 功能说明</h3>
            <p>这个工具可以：</p>
            <ul>
                <li>显示股票实时价格和涨跌</li>
                <li>绘制分时图和K线图</li>
                <li>支持多股票切换</li>
                <li>自动更新数据</li>
            </ul>
        </div>
        <p><strong>提示：</strong>关闭此窗口即可退出程序。</p>
    </div>
</body>
</html>
"""

def main():
    print("=== 开始Webview测试 ===")
    print("如果看到窗口弹出，说明webview正常工作")
    
    try:
        window = webview.create_window(
            "Webview测试",
            html=html_content,
            width=500,
            height=600,
            resizable=True,
            frameless=False,
            on_top=False
        )
        print("✅ Webview窗口创建成功")
        print("正在启动浏览器...")
        webview.start(debug=True)
        print("✅ Webview运行完成")
    except Exception as e:
        print(f"❌ Webview错误: {e}")
        print("\n可能的解决方案：")
        print("1. 检查是否安装了Edge浏览器")
        print("2. 尝试以管理员权限运行")
        print("3. 检查防火墙是否阻止了webview")

if __name__ == "__main__":
    main()