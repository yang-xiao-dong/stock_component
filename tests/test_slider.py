# -*- coding: utf-8 -*-
"""
测试滑动股票切换功能
"""
import webview
import os

# 创建HTML内容
html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>股票滑动测试</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; user-select: none; }
  html, body { 
    background: rgba(24, 26, 34, 0.95); 
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif; 
    min-height: 100vh;
  }
  body { padding: 20px; }
  #card {
    background: rgba(24, 26, 34, 0.92);
    border-radius: 12px;
    padding: 12px 14px 10px;
    color: #dfe3ea;
    box-shadow: 0 4px 18px rgba(0,0,0,.45);
    border: 1px solid rgba(255,255,255,.08);
    max-width: 450px;
    margin: 0 auto;
  }
  #drag { cursor: move; }
  .header { display: flex; justify-content: space-between; align-items: baseline; }
  .name { font-size: 13px; font-weight: 600; color: #aeb6c4; }
  .name b { color: #e8ebf0; font-size: 14px; margin-right: 6px; }
  .upd { font-size: 10px; color: #6b7382; }
  .main { display: flex; align-items: baseline; gap: 10px; margin: 6px 0 2px; }
  .price { font-size: 32px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .chg { font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .up { color: #ff5252; } .down { color: #26c281; } .flat { color: #aeb6c4; }
  .status { font-size: 10px; margin-left: auto; color: #6b7382; }
  canvas { width: 100%; height: 92px; display: block; margin-top: 4px; }
  .tabs { display: flex; gap: 4px; margin-left: auto; }
  .tab { font-size: 10px; padding: 1px 7px; border-radius: 8px; cursor: pointer;
         color: #6b7382; background: transparent; }
  .tab.on { color: #e8ebf0; background: rgba(255,255,255,.12); }
  
  /* 股票滑动导航 */
  .stock-nav {
    display: flex; justify-content: space-between; align-items: center; 
    margin-bottom: 8px; padding: 6px 8px; background: rgba(255,255,255,.06); 
    border-radius: 8px;
  }
  .stock-swiper {
    display: flex; gap: 6px; align-items: center;
    position: relative;
    overflow: hidden;
    border-radius: 6px;
    flex: 1;
  }
  .stock-list {
    display: flex; gap: 4px;
    transition: transform 0.3s ease;
    cursor: grab;
    min-width: 0;
  }
  .stock-list:active {
    cursor: grabbing;
  }
  .stock-item {
    background: rgba(255,255,255,.1); color: #e8ebf0; border: none;
    padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 11px;
    min-width: 80px;
    text-align: center;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .stock-item:hover { background: rgba(255,255,255,.2); }
  .stock-item.active { 
    background: rgba(255,255,255,.25); 
    color: #e8ebf0;
    font-weight: 500;
  }
  .stock-scroll-btn {
    background: rgba(255,255,255,.15); color: #e8ebf0; border: none;
    padding: 4px 8px; border-radius: 6px; cursor: pointer; font-size: 11px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }
  .stock-scroll-btn:hover { 
    background: rgba(255,255,255,.25); 
    transform: scale(1.05);
  }
  
  /* 滑动指示器 */
  .stock-indicator {
    color: #e8ebf0; font-size: 10px; font-weight: 400;
    background: rgba(255,255,255,.1); padding: 2px 6px; border-radius: 4px;
  }
  
  /* 网格 */
  .grid {
    display: grid; grid-template-columns: repeat(5, 1fr);
    margin-top: 6px; gap: 2px 6px; font-size: 10px; text-align: center;
  }
  .grid .k { color: #6b7382; font-size: 9px; }
  .grid .v { color: #c8cdd8; font-variant-numeric: tabular-nums; }
  
  /* 说明文字 */
  .instructions {
    margin-top: 20px;
    padding: 10px;
    background: rgba(255,255,255,.05);
    border-radius: 8px;
    color: #aeb6c4;
    font-size: 12px;
    text-align: center;
  }
</style>
</head>
<body>
<div id="card">
  <!-- 股票导航 -->
  <div class="stock-nav">
    <div class="header">
      <div id="drag">
        <span class="name"><b id="name">瑞芯微</b><span id="code">603893.SH</span></span>
        <span class="upd" id="upd">测试数据</span>
      </div>
    </div>
    <div class="stock-swiper" id="stockSwiper">
      <div class="stock-list" id="stockList">
        <button class="stock-item active" data-index="0">瑞芯微</button>
        <button class="stock-item" data-index="1">兆易创新</button>
        <button class="stock-item" data-index="2">翱捷科技-U</button>
        <button class="stock-item" data-index="3">龙迅股份</button>
        <button class="stock-item" data-index="4">中科蓝汛</button>
        <button class="stock-item" data-index="5">乐鑫科技</button>
        <button class="stock-item" data-index="6">晶晨股份</button>
        <button class="stock-item" data-index="7">全志科技</button>
        <button class="stock-item" data-index="8">恒玄科技</button>
        <button class="stock-item" data-index="9">炬芯科技</button>
      </div>
    </div>
  </div>
  
  <!-- 主要信息 -->
  <div class="main">
    <span class="price flat" id="price">190.04</span>
    <span class="chg flat" id="chg">+8.83 +4.87%</span>
    <span class="status" id="status">● 交易中</span>
    <span class="tabs">
      <span class="tab on" id="tabMin">分时</span>
      <span class="tab" id="tabK">日K</span>
    </span>
  </div>
  
  <!-- 图表 -->
  <canvas id="chart"></canvas>
  
  <!-- 底部信息网格 -->
  <div class="grid">
    <div><div class="k">今开</div><div class="v" id="open">183.60</div></div>
    <div><div class="k">最高</div><div class="v" id="high">192.22</div></div>
    <div><div class="k">最低</div><div class="v" id="low">183.60</div></div>
    <div><div class="k">成交量</div><div class="v" id="vol">12.52万手</div></div>
    <div><div class="k">成交额</div><div class="v" id="amt">23.56亿</div></div>
  </div>
</div>

<div class="instructions">
  <strong>滑动操作说明：</strong><br>
  🖱️ 点击股票名称直接切换 | 🖱️ 左右滚动按钮滚动列表 | ⌨️ 鼠标滚轮滑动 | 📱 触摸滑动支持<br>
  当前股票：<span id="stockIndicator">1 / 10</span>
</div>

<script>
const $ = id => document.getElementById(id);
let minuteCache = null, minuteAt = 0, klineCache = null, mode = 'min';
let currentStockIndex = 0;
const totalStocks = 10;

// 更新窗口标题
function updateWindowTitle(name, code) {
  document.title = `${name} ${code}`;
}

function cls(pct) { return pct > 0 ? 'up' : (pct < 0 ? 'down' : 'flat'); }
function fmtTime(t) { return t ? t.slice(8,10)+':'+t.slice(10,12)+':'+t.slice(12,14) : ''; }

function render(rt) {
  $('name').textContent = rt.name || '--';
  $('price').textContent = rt.price ? rt.price.toFixed(2) : '--';
  $('chg').textContent = rt.change !== undefined ? 
    (rt.change > 0 ? '+' : '') + rt.change.toFixed(2) + '  ' + 
    (rt.change_pct !== undefined ? (rt.change_pct > 0 ? '+' : '') + rt.change_pct.toFixed(2) + '%' : '--') : '--';
  $('price').className = 'price ' + cls(rt.change_pct || 0);
  $('chg').className = 'chg ' + cls(rt.change_pct || 0);
  $('open').textContent = rt.open ? rt.open.toFixed(2) : '--';
  $('high').textContent = rt.high ? rt.high.toFixed(2) : '--';
  $('low').textContent = rt.low ? rt.low.toFixed(2) : '--';
  $('vol').textContent = rt.volume ? (rt.volume / 10000).toFixed(1) + '万手' : '--';
  $('amt').textContent = rt.amount ? rt.amount.toFixed(2) + '亿' : '--';
  $('upd').textContent = '测试数据';
  
  const now = new Date(), mts = now.getHours()*60 + now.getMinutes();
  const trading = (now.getDay() >= 1 && now.getDay() <= 5) &&
    (mts >= 570 && mts <= 690 || mts >= 780 && mts <= 900);
  $('status').textContent = trading ? '● 交易中' : '已收盘';
  
  // 更新位置指示器
  $('stockIndicator').textContent = `${currentStockIndex + 1} / ${totalStocks}`;
  
  // 更新窗口标题
  updateWindowTitle(rt.name || '--', rt.code || '--');
  
  // 绘制简单的测试图表
  drawTestChart();
}

function setupCanvas() {
  const cv = $('chart'), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext('2d'); ctx.scale(dpr, d1pr);
  return { cv, ctx, w, h };
}

function drawTestChart() {
  const { ctx, w, h } = setupCanvas();
  
  // 清空画布
  ctx.clearRect(0, 0, w, h);
  
  // 绘制网格
  ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75].forEach(f => {
    ctx.beginPath(); ctx.moveTo(0, h*f); ctx.lineTo(w, h*f); ctx.stroke();
  });
  
  // 绘制示例分时线
  ctx.strokeStyle = '#ff5252'; ctx.lineWidth = 1.4;
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const x = i * (w / 9);
    const y = h * 0.3 + Math.sin(i * 0.5) * h * 0.2;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  
  // 添加文字
  ctx.fillStyle = '#aeb6c4'; ctx.font = '10px Arial';
  ctx.fillText('滑动切换股票查看不同数据', w * 0.1, h * 0.9);
}

// 滑动功能
function initStockSwiper() {
  const stockList = $('stockList');
  
  // 鼠标滚轮支持
  stockList.addEventListener('wheel', (e) => {
    e.preventDefault();
    stockList.scrollBy({
      left: e.deltaY,
      behavior: 'auto'
    });
  }, { passive: false });
  
  // 点击股票切换
  stockList.addEventListener('click', (e) => {
    if (e.target.classList.contains('stock-item')) {
      const index = parseInt(e.target.dataset.index);
      currentStockIndex = index;
      
      // 更新激活状态
      stockList.querySelectorAll('.stock-item').forEach((item, i) => {
        item.classList.toggle('active', i === index);
      });
      
      // 模拟数据变化
      updateTestData();
    }
  });
  
  // 触摸滑动支持
  let touchStartX = 0;
  
  stockList.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX;
  }, { passive: true });
  
  stockList.addEventListener('touchmove', (e) => {
    if (!touchStartX) return;
    const touchEndX = e.touches[0].clientX;
    const diffX = touchStartX - touchEndX;
    
    if (Math.abs(diffX) > 10) {
      stockList.scrollBy({
        left: diffX * 0.5,
        behavior: 'auto'
      });
    }
  }, { passive: true });
}

// 模拟数据更新
function updateTestData() {
  const testStocks = [
    { name: '瑞芯微', code: '603893.SH', price: 190.04, change: 8.83, change_pct: 4.87 },
    { name: '兆易创新', code: '603986.SH', price: 388.18, change: 20.31, change_pct: 4.95 },
    { name: '翱捷科技-U', code: '688082.SH', price: 292.77, change: 10.26, change_pct: 3.65 },
    { name: '龙迅股份', code: '688222.SH', price: 39.97, change: 2.29, change_pct: 6.08 },
    { name: '中科蓝汛', code: '688023.SH', price: 44.02, change: 1.64, change_pct: 3.87 },
    { name: '乐鑫科技', code: '688018.SH', price: 112.11, change: 7.95, change_pct: 7.61 },
    { name: '晶晨股份', code: '688099.SH', price: 88.50, change: 3.09, change_pct: 3.61 },
    { name: '全志科技', code: '300078.SZ', price: 2.68, change: 0.03, change_pct: 1.13 },
    { name: '恒玄科技', code: '688608.SH', price: 103.25, change: 7.26, change_pct: 7.55 },
    { name: '炬芯科技', code: '688268.SH', price: 138.21, change: 4.47, change_pct: 3.35 }
  ];
  
  const stock = testStocks[currentStockIndex];
  const testRt = {
    ...stock,
    open: stock.price * 0.95,
    high: stock.price * 1.05,
    low: stock.price * 0.93,
    volume: 125167,
    amount: 23.5615
  };
  
  render(testRt);
}

document.addEventListener('DOMContentLoaded', function() {
  // 初始化滑动功能
  initStockSwiper();
  
  // 初始显示
  updateTestData();
  
  // 每10秒随机切换一次（演示用）
  setInterval(() => {
    if (Math.random() > 0.7) {
      const randomIndex = Math.floor(Math.random() * totalStocks);
      currentStockIndex = randomIndex;
      
      const stockList = $('stockList');
      stockList.querySelectorAll('.stock-item').forEach((item, i) => {
        item.classList.toggle('active', i === randomIndex);
      });
      
      updateTestData();
    }
  }, 10000);
});
</script>
</body>
</html>
"""

def main():
    print("=== 测试股票滑动功能 ===")
    print("请测试以下功能：")
    print("1. 点击股票名称直接切换")
    print("2. 鼠标滚轮滑动浏览股票")
    print("3. 触摸滑动（移动设备）")
    print("4. 手动拖拽股票列表")
    
    try:
        window = webview.create_window(
            "股票滑动测试",
            html=html_content,
            width=450,
            height=600,
            resizable=True,
            frameless=False,
            on_top=False
        )
        print("✅ 滑动测试窗口创建成功")
        print("正在启动浏览器...")
        webview.start(debug=True)
        print("✅ 滑动测试完成")
    except Exception as e:
        print(f"❌ Webview错误: {e}")

if __name__ == "__main__":
    main()