# -*- coding: utf-8 -*-
"""
完整功能测试 - 包含实际数据获取和股票切换
"""
import webview
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_api import get_realtime, get_minute_data, get_kline

# 创建HTML内容
html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>股票滑动切换测试</title>
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
  
  /* 错误提示 */
  .error {
    color: #ff5252;
    font-size: 10px;
    margin-top: 5px;
  }
</style>
</head>
<body>
<div id="card">
  <!-- 股票导航 -->
  <div class="stock-nav">
    <div class="header">
      <div id="drag">
        <span class="name"><b id="name">加载中...</b><span id="code">--</span></span>
        <span class="upd" id="upd">连接中...</span>
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
    <span class="price flat" id="price">--</span>
    <span class="chg flat" id="chg">--</span>
    <span class="status" id="status">--</span>
    <span class="tabs">
      <span class="tab on" id="tabMin">分时</span>
      <span class="tab" id="tabK">日K</span>
    </span>
  </div>
  
  <!-- 图表 -->
  <canvas id="chart"></canvas>
  
  <!-- 底部信息网格 -->
  <div class="grid">
    <div><div class="k">今开</div><div class="v" id="open">--</div></div>
    <div><div class="k">最高</div><div class="v" id="high">--</div></div>
    <div><div class="k">最低</div><div class="v" id="low">--</div></div>
    <div><div class="k">成交量</div><div class="v" id="vol">--</div></div>
    <div><div class="k">成交额</div><div class="v" id="amt">--</div></div>
  </div>
  
  <div class="error" id="error"></div>
</div>

<div class="instructions">
  <strong>滑动操作说明：</strong><br>
  🖱️ 点击股票名称直接切换 | 🖱️ 鼠标滚轮滑动浏览 | 📱 触摸滑动支持 | 🔄 数据每5秒自动更新<br>
  当前股票：<span id="stockIndicator">1 / 10</span>
</div>

<script>
const $ = id => document.getElementById(id);
let minuteCache = null, minuteAt = 0, klineCache = null, mode = 'min';
let currentStockIndex = 0;
const totalStocks = 10;

// 股票列表（与后端保持一致）
const STOCKS = [
  {"name": "瑞芯微", "code": "sh603893"},
  {"name": "兆易创新", "code": "sh603986"},
  {"name": "翱捷科技-U", "code": "sh688082"},
  {"name": "龙迅股份", "code": "sh688222"},
  {"name": "中科蓝汛", "code": "sh688023"},
  {"name": "乐鑫科技", "code": "sh688018"},
  {"name": "晶晨股份", "code": "sh688099"},
  {"name": "全志科技", "code": "sz300078"},
  {"name": "恒玄科技", "code": "sh688608"},
  {"name": "炬芯科技", "code": "sh688268"}
];

// 更新窗口标题
function updateWindowTitle(name, code) {
  document.title = `${name} ${code}`;
}

function cls(pct) { return pct > 0 ? 'up' : (pct < 0 ? 'down' : 'flat'); }
function fmtTime(t) { return t ? t.slice(8,10)+':'+t.slice(10,12)+':'+t.slice(12,14) : ''; }

function render(rt) {
  if (!rt) { 
    $('upd').textContent = '网络错误，重试中...';
    $('error').textContent = '无法获取数据，请检查网络连接';
    return; 
  }
  
  console.log('渲染数据:', rt);
  $('error').textContent = '';
  
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
  $('upd').textContent = rt.time ? fmtTime(rt.time) + ' 更新' : '无时间数据';
  
  const now = new Date(), mts = now.getHours()*60 + now.getMinutes();
  const trading = (now.getDay() >= 1 && now.getDay() <= 5) &&
    (mts >= 570 && mts <= 690 || mts >= 780 && mts <= 900);
  $('status').textContent = trading ? '● 交易中' : '已收盘';
  
  // 更新位置指示器
  $('stockIndicator').textContent = `${currentStockIndex + 1} / ${totalStocks}`;
  
  // 更新窗口标题
  updateWindowTitle(rt.name || '--', rt.code || '--');
  
  // 绘制图表
  if (mode === 'min' && minuteCache) {
    drawChart(minuteCache, rt.prev_close || rt.open || 0);
  } else if (mode === 'k' && klineCache) {
    drawKline(klineCache);
  } else {
    // 如果没有缓存数据，重新获取
    refreshData();
  }
}

function setupCanvas() {
  const cv = $('chart'), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext('2d'); ctx.scale(dpr, dpr);
  return { cv, ctx, w, h };
}

function drawChart(points, prevClose) {
  const { ctx, w, h } = setupCanvas();
  if (!points || points.length < 2) return;
  const prices = points.map(p => p.price);
  let max = Math.max(...prices, prevClose), min = Math.min(...prices, prevClose);
  const pad = (max - min) * 0.1 || 0.1; max += pad; min -= pad;
  const N = 242;
  const x = i => 2 + i / (N - 1) * (w - 4);
  const y = p => 6 + (max - p) / (max - min) * (h - 12);

  // 网格
  ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75].forEach(f => {
    ctx.beginPath(); ctx.moveTo(0, h*f); ctx.lineTo(w, h*f); ctx.stroke();
  });
  
  // 昨收基准线
  ctx.strokeStyle = 'rgba(255,255,255,.18)';
  ctx.setLineDash([3,3]); ctx.beginPath();
  ctx.moveTo(0, y(prevClose)); ctx.lineTo(w, y(prevClose)); ctx.stroke();
  ctx.setLineDash([]);

  // 分时折线 + 填充
  const color = points[points.length-1].price >= prevClose ? '#ff5252' : '#26c281';
  ctx.beginPath();
  points.forEach((p, i) => { const px = x(Math.min(i, N-1)); i ? ctx.lineTo(px, y(p.price)) : ctx.moveTo(px, y(p.price)); });
  ctx.strokeStyle = color; ctx.lineWidth = 1.4; ctx.stroke();
  ctx.lineTo(x(Math.min(points.length-1, N-1)), h); ctx.lineTo(x(0), h); ctx.closePath();
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, color + '55'); g.addColorStop(1, color + '05');
  ctx.fillStyle = g; ctx.fill();
}

function drawKline(bars) {
  const { ctx, w, h } = setupCanvas();
  if (!bars || bars.length < 2) return;
  let max = -1e9, min = 1e9;
  bars.forEach(b => { max = Math.max(max, b.high); min = Math.min(min, b.low); });
  const pad = (max - min) * 0.08 || 0.1; max += pad; min -= pad;
  const y = p => 6 + (max - p) / (max - min) * (h - 12);
  const slot = (w - 4) / bars.length, bw = Math.max(1.5, slot * 0.6);

  ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75].forEach(f => {
    ctx.beginPath(); ctx.moveTo(0, h*f); ctx.lineTo(w, h*f); ctx.stroke();
  });

  bars.forEach((b, i) => {
    const cx = 2 + slot * (i + 0.5);
    const up = b.close >= b.open;
    const color = up ? '#ff5252' : '#26c281';
    // 影线
    ctx.strokeStyle = color; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(cx, y(b.high)); ctx.lineTo(cx, y(b.low)); ctx.stroke();
    // 实体
    const yo = y(b.open), yc = y(b.close);
    ctx.fillStyle = color;
    ctx.fillRect(cx - bw/2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
  });
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
      
      // 清除缓存，强制重新获取数据
      minuteCache = null;
      klineCache = null;
      
      // 调用Python API切换股票
      try {
        pywebview.api.set_stock_index(index);
      } catch (e) {
        console.error('切换股票失败:', e);
      }
      
      // 刷新数据
      refreshData();
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

// 刷新数据
async function refreshData() {
  try {
    const rt = await pywebview.api.get_realtime();
    render(rt);
    
    if (rt && (!minuteCache || Date.now() - minuteAt > 60000)) {
      minuteCache = await pywebview.api.get_minute_data();
      minuteAt = Date.now();
    }
    
    if (!klineCache) {
      klineCache = await pywebview.api.get_kline();
    }
    
  } catch (e) { 
    $('upd').textContent = '连接失败...'; 
    $('error').textContent = 'API调用失败: ' + e.message;
    console.error('刷新数据错误:', e);
  }
}

// 图表切换
document.addEventListener('DOMContentLoaded', function() {
  // 初始化滑动功能
  initStockSwiper();
  
  // 图表切换
  $('tabMin').onclick = () => { 
    mode = 'min'; 
    $('tabMin').classList.add('on'); 
    $('tabK').classList.remove('on'); 
    refreshData(); 
  };
  $('tabK').onclick = () => { 
    mode = 'k'; 
    $('tabK').classList.add('on'); 
    $('tabMin').classList.remove('on'); 
    refreshData(); 
  };
  
  // 初始刷新
  refreshData();
  
  // 每5秒刷新一次
  setInterval(refreshData, 5000);
});
</script>
</body>
</html>
"""

class TestApi:
    def __init__(self):
        self.current_stock_index = 0
        self.stock_data = {}
        print("Test API初始化完成")
    
    def set_stock_index(self, index):
        """设置当前股票索引"""
        if 0 <= index < 10:
            self.current_stock_index = index
            print(f"切换到股票: {index}")
            # 清除当前股票的缓存，强制重新获取数据
            stock_codes = [
                "sh603893", "sh603986", "sh688082", "sh688222", "sh688023",
                "sh688018", "sh688099", "sz300078", "sh688608", "sh688268"
            ]
            code = stock_codes[index]
            if code in self.stock_data:
                del self.stock_data[code]
            return True
        return False
    
    def get_realtime(self):
        """获取实时数据"""
        stock_codes = [
            "sh603893", "sh603986", "sh688082", "sh688222", "sh688023",
            "sh688018", "sh688099", "sz300078", "sh688608", "sh688268"
        ]
        code = stock_codes[self.current_stock_index]
        
        # 如果数据过期（超过10秒）或不存在，重新获取
        import time
        if (code not in self.stock_data or 
            self.stock_data[code] is None or 
            time.time() - self.stock_data[code].get("timestamp", 0) > 10):
            try:
                new_data = get_realtime(code)
                if new_data:
                    new_data["timestamp"] = time.time()
                    self.stock_data[code] = new_data
                    print(f"获取新数据: {new_data['name']} - {new_data['price']}")
                else:
                    # 如果获取失败，保留旧数据（如果有）
                    pass
            except Exception as e:
                print(f"获取实时数据失败: {e}")
                # 如果获取失败，保留旧数据（如果有）
        
        return self.stock_data.get(code)
    
    def get_minute_data(self):
        """获取分时数据"""
        stock_codes = [
            "sh603893", "sh603986", "sh688082", "sh688222", "sh688023",
            "sh688018", "sh688099", "sz300078", "sh688608", "sh688268"
        ]
        code = stock_codes[self.current_stock_index]
        try:
            data = get_minute_data(code)
            print(f"分时数据获取成功: {len(data) if data else 0} 个点")
            return data
        except Exception as e:
            print(f"分时数据获取失败: {e}")
            return None
    
    def get_kline(self):
        """获取K线数据"""
        stock_codes = [
            "sh603893", "sh603986", "sh688082", "sh688222", "sh688023",
            "sh688018", "sh688099", "sz300078", "sh688608", "sh688268"
        ]
        code = stock_codes[self.current_stock_index]
        try:
            data = get_kline(code, count=3)
            print(f"K线数据获取成功: {len(data) if data else 0} 个点")
            return data
        except Exception as e:
            print(f"K线数据获取失败: {e}")
            return None

def main():
    print("=== 完整功能测试 ===")
    print("测试内容：")
    print("1. 实际股票数据获取")
    print("2. 滑动股票切换")
    print("3. 图表显示")
    print("4. 自动刷新")
    
    try:
        api = TestApi()
        
        window = webview.create_window(
            "股票滑动测试",
            html=html_content,
            js_api=api,
            width=450,
            height=600,
            resizable=True,
            frameless=False,
            on_top=False
        )
        print("✅ 完整测试窗口创建成功")
        print("正在启动浏览器...")
        webview.start(debug=True)
        print("✅ 完整测试完成")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    main()