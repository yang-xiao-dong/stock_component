/* 组合组件图表绘制：分时盈亏图 + 日K主副面板（含各股迷你蜡烛）。
   依赖先加载 ../../assets/shared.js（$ / setupCanvas / strokeSeries / hgrid 等）。
   ui.html 只保留数据流与 DOM，本文件只管怎么画。 */

var stocks = [];      // 股票清单（ui.html init 时填充，颜色映射与色条用）
var codeColor = {};   // {code: 颜色}

const PALETTE = ['#5b8def','#ff8a65','#ba68c8','#4dd0e1','#aed581',
                 '#ffd54f','#f06292','#7986cb','#fff176','#4db6ac'];

function buildColorMap() {
  codeColor = {};
  stocks.forEach((s, i) => { codeColor[s.code] = PALETTE[i % PALETTE.length]; });
}

/* 轴刻度：万以上缩写（仅图表用） */
function fmtWan(v) {
  const a = Math.abs(v);
  return (v < 0 ? '-' : '') + (a >= 10000 ? (a / 10000).toFixed(1) + '万' : String(Math.round(a)));
}

/* ---------------- 分时（当日盈亏 ¥）：个股细线 + 组合合计加粗线 + 0轴 + 行业量能副图 ---------------- */
function drawMinute(data) {
  const { ctx, w, h } = setupCanvas();
  ctx.clearRect(0, 0, w, h);
  if (!data || !data.times || data.times.length < 2 || !data.stocks) {
    drawChartMessage(HISTORY_REPLAY ? '暂无足够分时数据（离线日期未采集）'
                                    : '暂无足够分时数据，稍后自动重试'); return;
  }

  const PR = 48, PT = 10, PB = 14;
  // 行业量能副图：组内各股分钟量合计（无量数据日期不画，价格图占满）
  const vols = data.vol_total || [];
  const hasVol = vols.some(v => v != null);
  const priceBottom = hasVol ? PT + (h - PT - PB) * 0.62 : h - PB;
  const volTagY = priceBottom + 5, volTop = priceBottom + 14, volBottom = h - PB;

  const all = [];
  data.stocks.forEach(s => s.data.forEach(v => { if (v != null) all.push(v); }));
  (data.total || []).forEach(v => { if (v != null) all.push(v); });
  if (!all.length) {
    drawChartMessage(HISTORY_REPLAY ? '暂无足够分时数据（离线日期未采集）'
                                    : '暂无足够分时数据，稍后自动重试'); return;
  }
  let max = Math.max(...all, 0), min = Math.min(...all, 0);
  const pad = (max - min) * 0.12 || 10; max += pad; min -= pad;
  const umax = max - pad, umin = min + pad;

  const N = data.times.length, cw = w - PR;
  const x = i => 2 + i / (N - 1) * (cw - 6);
  const y = v => PT + (max - v) / (max - min) * (priceBottom - PT);

  if (hasVol) hgrid(ctx, cw, priceBottom, PT, 2);   // 网格只铺价格区
  else hgrid(ctx, cw, h, PT, PB);

  // 0 轴虚线
  ctx.strokeStyle = 'rgba(255,255,255,.25)'; ctx.setLineDash([3, 3]);
  ctx.beginPath(); ctx.moveTo(0, y(0)); ctx.lineTo(cw, y(0)); ctx.stroke();
  ctx.setLineDash([]);

  // 个股当日盈亏细线
  data.stocks.forEach(s => {
    const color = codeColor[s.code]; if (!color) return;
    strokeSeries(ctx, s.data.map((v, i) => [x(i), v == null ? null : y(v)]), color, 1, 0.5);
  });

  // 组合合计线 + 相对0轴的柔和填充
  const total = data.total || [];
  let first = -1, last = -1;
  total.forEach((v, i) => { if (v != null) { if (first < 0) first = i; last = i; } });
  if (first >= 0) {
    ctx.beginPath();
    let started = false;
    total.forEach((v, i) => {
      if (v == null) return;
      if (!started) { ctx.moveTo(x(i), y(v)); started = true; } else ctx.lineTo(x(i), y(v));
    });
    ctx.lineTo(x(last), y(0)); ctx.lineTo(x(first), y(0)); ctx.closePath();
    const g = ctx.createLinearGradient(0, PT, 0, priceBottom);
    g.addColorStop(0, 'rgba(255,255,255,.10)'); g.addColorStop(1, 'rgba(255,255,255,.02)');
    ctx.fillStyle = g; ctx.fill();
    strokeSeries(ctx, total.map((v, i) => [x(i), v == null ? null : y(v)]), '#ffffff', 1.8, 0.95);
  }
  drawLineLegend(ctx, 6, PT + 7, '组合');

  // 轴标签（元）
  ctx.fillStyle = '#6b7382'; ctx.font = '9px "Segoe UI", "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText((umax > 0 ? '+' : '') + fmtWan(umax), cw + 4, y(umax) + 3);
  ctx.fillText('0', cw + 4, y(0) + 3);
  ctx.fillText(fmtWan(umin), cw + 4, y(umin) + 3);

  if (hasVol) {
    // 分隔线 + 标识 + 累计总量（红涨绿跌按组合合计方向）
    ctx.strokeStyle = 'rgba(255,255,255,.10)';
    ctx.beginPath(); ctx.moveTo(0, volTagY); ctx.lineTo(cw, volTagY); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.5)';
    ctx.fillText('行业量能·分钟量合计（红涨绿跌）', 2, volTagY + 9);
    const cum = vols.reduce((a, v) => a + (v || 0), 0);
    ctx.textAlign = 'right';
    ctx.fillText('累计 ' + fmtWan(cum) + ' 手', cw - 2, volTagY + 9);
    ctx.textAlign = 'left';

    const maxD = Math.max(...vols.filter(v => v != null)) || 1;
    ctx.globalAlpha = .8;
    vols.forEach((v, i) => {
      if (!v) return;
      const cur = total[i] != null ? total[i] : (total[i - 1] ?? 0);
      const pre = total[i - 1] ?? 0;
      ctx.fillStyle = cur >= pre ? '#ff5252' : '#26c281';
      const bh = Math.max(1, v / maxD * (volBottom - volTop));
      ctx.fillRect(x(i) - 0.6, volBottom - bh, 1.2, bh);
    });
    ctx.globalAlpha = 1;
    // 峰值参考（右轴）
    ctx.fillStyle = '#6b7382';
    ctx.fillText(fmtWan(maxD) + '手/分', cw + 4, volTop + 3);
  }

  ctx.fillText(data.times[0], 2, h - 3);
  ctx.textAlign = 'right'; ctx.fillText(data.times[N - 1], cw - 2, h - 3);
  ctx.textAlign = 'left';
}

/* ---------------- 日K：主面板 = 组合市值¥蜡烛 + 本金基准线 ----------------
   副面板（独立刻度，避免与市值蜡烛 10 倍量级差压扁）：
   'candle' = 各股一行迷你日K蜡烛（默认）；'line' = 各股较首日盈亏叠加线 */
var subMode = 'candle';
var subToggleRects = [];   // 「线|蜡烛」文字命中区（drawK 时更新）

function drawK(data) {
  const { ctx, w, h } = setupCanvas();
  ctx.clearRect(0, 0, w, h);
  if (!data || !data.candles || data.candles.length < 2) {
    drawChartMessage(HISTORY_REPLAY ? '暂无足够日K数据（窗口不足：早于上市或长期停牌）'
                                    : '暂无足够日 K 数据，稍后自动重试'); return;
  }

  const PR = 48, PT = 10, PB = 14;
  // 主面板范围：只由蜡烛与本金决定（个股线进副面板，不再拉低轴下限）
  let max = -1e9, min = 1e9;
  data.candles.forEach(b => { max = Math.max(max, b.high); min = Math.min(min, b.low); });
  const C = data.principal;
  if (C != null) { max = Math.max(max, C); min = Math.min(min, C); }
  const pad = (max - min) * 0.08 || 1; max += pad; min -= pad;

  // 副面板：各股较首日变化（首值归零），无有效数据时主面板占满整幅
  const klines = [];
  (data.stocks || []).forEach(s => {
    const base = s.data.find(v => v != null);
    if (base == null) return;
    klines.push({ code: s.code, deltas: s.data.map(v => v == null ? null : v - base),
                  bars: s.bars || null });
  });
  const hasSub = klines.length > 0;
  const kBottom = hasSub ? PT + (h - PT - PB) * 0.60 : h - PB;
  let smax = 0, smin = 0;
  if (hasSub) {
    klines.forEach(k => k.deltas.forEach(v => {
      if (v != null) { smax = Math.max(smax, v); smin = Math.min(smin, v); }
    }));
    const spad = (smax - smin) * 0.12 || 100; smax += spad; smin -= spad;
  }
  const sTop = kBottom + 12, sBottom = h - PB;

  const n = data.dates.length, cw = w - PR;
  const x = i => 2 + i / (n - 1) * (cw - 6);
  const y = v => PT + (max - v) / (max - min) * (kBottom - PT);
  const y2 = v => sTop + (smax - v) / (smax - smin) * (sBottom - sTop);

  hgrid(ctx, cw, h, PT, PB);

  // 本金基准虚线
  if (C != null && C > min && C < max) {
    ctx.strokeStyle = 'rgba(255,213,79,.4)'; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(0, y(C)); ctx.lineTo(cw, y(C)); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(255,213,79,.8)';
    ctx.font = '9px "Segoe UI", "Microsoft YaHei", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('本金', 2, y(C) - 2);
  }

  const di = {}; data.dates.forEach((d, i) => di[d] = i);
  const slot = (cw - 6) / n, bw = Math.max(1.5, slot * 0.6);
  data.candles.forEach(b => {
    const i = di[b.date]; if (i == null) return;
    const cx = x(i);
    const up = b.close >= b.open, color = up ? '#ff5252' : '#26c281';
    ctx.strokeStyle = color; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(cx, y(b.high)); ctx.lineTo(cx, y(b.low)); ctx.stroke();
    const yo = y(b.open), yc = y(b.close);
    ctx.fillStyle = color;
    ctx.fillRect(cx - bw / 2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
  });
  drawLineLegend(ctx, 6, PT + 7, '组合');

  ctx.fillStyle = '#6b7382'; ctx.font = '9px "Segoe UI", "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(fmtWan(max - pad), cw + 4, y(max - pad) + 3);
  ctx.fillText(fmtWan((max + min) / 2), cw + 4, y((max + min) / 2) + 3);
  ctx.fillText(fmtWan(min + pad), cw + 4, y(min + pad) + 3);

  if (hasSub) drawSubPanel(ctx, { w, h, cw, kBottom, sTop, sBottom, smax, smin, x, y2, klines });

  const dl = s => s && s.length >= 5 ? s.slice(5) : (s || '');
  ctx.fillText(dl(data.dates[0]), 2, h - 3);
  ctx.textAlign = 'right'; ctx.fillText(dl(data.dates[n - 1]), cw - 2, h - 3);
  ctx.textAlign = 'left';
}

/* 日K副面板：分隔线 + 个股区（迷你蜡烛 / 较首日线）+「线|蜡烛」切换 */
function drawSubPanel(ctx, g) {
  const { cw, kBottom, sTop, sBottom, klines } = g;
  ctx.strokeStyle = 'rgba(255,255,255,.10)';
  ctx.beginPath(); ctx.moveTo(0, kBottom + 5); ctx.lineTo(cw, kBottom + 5); ctx.stroke();

  const crows = klines.filter(k => k.bars && k.bars.length >= 2);
  const useCandle = subMode === 'candle' && crows.length === klines.length &&
                    crows.length > 0 && (sBottom - sTop) / crows.length >= 6;
  ctx.font = '9px "Segoe UI", "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'left';

  if (useCandle) {
    // 每股一行迷你蜡烛，各自按自身高低点缩放；行首色条对应个股颜色
    const rh = (sBottom - sTop) / crows.length;
    const maxBars = Math.max(...crows.map(k => k.bars.length));
    const slot = (cw - 10) / maxBars, bw = Math.max(1, slot * 0.6);
    crows.forEach((k, ri) => {
      const top = sTop + ri * rh;
      if (ri) {
        ctx.strokeStyle = 'rgba(255,255,255,.05)';
        ctx.beginPath(); ctx.moveTo(0, top + .5); ctx.lineTo(cw, top + .5); ctx.stroke();
      }
      const scolor = codeColor[k.code];
      if (scolor) { ctx.fillStyle = scolor; ctx.fillRect(0, top + 1, 3, rh - 2); }
      let lo = 1e9, hi = -1e9;
      k.bars.forEach(b => { lo = Math.min(lo, b.low); hi = Math.max(hi, b.high); });
      const span = (hi - lo) || 1;
      const y3 = v => top + 2 + (hi - v) / span * (rh - 4);
      k.bars.forEach((b, bi) => {
        const cx = 6 + slot * (bi + .5);
        const up = b.close >= b.open, color = up ? '#ff5252' : '#26c281';
        ctx.strokeStyle = color; ctx.lineWidth = 0.75;
        ctx.beginPath(); ctx.moveTo(cx, y3(b.high)); ctx.lineTo(cx, y3(b.low)); ctx.stroke();
        const yo = y3(b.open), yc = y3(b.close);
        ctx.fillStyle = color;
        ctx.fillRect(cx - bw / 2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
      });
    });
    ctx.fillStyle = '#6b7382';
    ctx.fillText('个股·日K', 2, kBottom + 9);
  } else {
    ctx.strokeStyle = 'rgba(255,255,255,.25)'; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(0, g.y2(0)); ctx.lineTo(cw, g.y2(0)); ctx.stroke();
    ctx.setLineDash([]);
    klines.forEach(k => {
      const color = codeColor[k.code]; if (!color) return;
      strokeSeries(ctx, k.deltas.map((v, i) => [g.x(i), v == null ? null : g.y2(v)]), color, 1, 0.55);
    });
    const { smax, smin, y2 } = g;
    ctx.fillStyle = '#6b7382';
    ctx.fillText('个股·较首日', 2, kBottom + 9);
    ctx.fillText((smax - (smax - smin) * 0.12 > 0 ? '+' : '') + fmtWan(smax - (smax - smin) * 0.12), cw + 4, y2(smax - (smax - smin) * 0.12) + 3);
    ctx.fillText('0', cw + 4, y2(0) + 3);
    ctx.fillText(fmtWan(smin + (smax - smin) * 0.12), cw + 4, y2(smin + (smax - smin) * 0.12) + 3);
  }

  // 「线 | 蜡烛」切换（面板间隔行右侧，命中区由 click 处理器读取）
  const items = [['line', '线'], ['candle', '蜡烛']];
  const activeMode = useCandle ? 'candle' : 'line';
  const totalW = items.reduce((s, [, t]) => s + ctx.measureText(t).width + 10, 0) - 10;
  let tx = cw - totalW;
  subToggleRects = [];
  items.forEach(([m, t]) => {
    const active = m === activeMode;
    const tw = ctx.measureText(t).width;
    ctx.fillStyle = active ? '#e8ebf0' : '#6b7382';
    ctx.fillText(t, tx, kBottom + 9);
    if (active) ctx.fillRect(tx, kBottom + 10.5, tw, 1);
    subToggleRects.push({ x: tx - 3, y: kBottom, w: tw + 6, h: 13, mode: m });
    tx += tw + 10;
  });
}

/* 副面板「线|蜡烛」点击切换（ui.html 的 mode 变量由其自身维护，这里只看 k 模式） */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('chart').addEventListener('click', e => {
    if (typeof mode === 'undefined' || mode !== 'k') return;
    const hit = subToggleRects.find(t =>
      e.offsetX >= t.x && e.offsetX <= t.x + t.w && e.offsetY >= t.y && e.offsetY <= t.y + t.h);
    if (hit && hit.mode !== subMode) { subMode = hit.mode; redrawChart(); }
  });
});
