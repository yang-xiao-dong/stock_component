/* 公共前端工具：pywebview 桥接、格式化、Canvas 基础绘制、窗口缩放。
   页面需先引入本文件，再写自己的逻辑；页面需提供 redrawChart() 供窗口缩放后重绘。
   嵌入模式（被外壳 shell.html 以同源 iframe 加载）自动回退到父页面桥接。 */

const $ = id => document.getElementById(id);

const EMBEDDED = window.parent !== window;
if (EMBEDDED) document.documentElement.classList.add('embedded');

function api() {
  if (window.pywebview && window.pywebview.api) return window.pywebview.api;
  if (EMBEDDED && window.parent && window.parent.pywebview && window.parent.pywebview.api) {
    return window.parent.pywebview.api;
  }
  return null;
}

/* 桥接就绪回调：已就绪立即执行；嵌入模式轮询父页面；独立打开监听 pywebviewready */
function whenBridgeReady(cb) {
  if (api()) { cb(); return; }
  if (EMBEDDED) {
    const timer = setInterval(() => {
      if (api()) { clearInterval(timer); cb(); }
    }, 250);
    return;
  }
  window.addEventListener('pywebviewready', () => cb());
}

function cls(pct) { return pct > 0 ? 'up' : (pct < 0 ? 'down' : 'flat'); }
function fmtPct(v) { return v == null ? '--' : ((v > 0 ? '+' : '') + v.toFixed(2) + '%'); }
function fmtTime(t) { return t ? t.slice(8,10)+':'+t.slice(10,12)+':'+t.slice(12,14) : ''; }
function fmtCode(code) {
  if (!code) return '--';
  const raw = String(code);
  if (raw.includes('.')) return raw.toUpperCase();
  if (raw.startsWith('sh')) return raw.slice(2) + '.SH';
  if (raw.startsWith('sz')) return raw.slice(2) + '.SZ';
  return raw;
}
function isTrading() {
  const n = new Date(), m = n.getHours() * 60 + n.getMinutes();
  return (n.getDay() >= 1 && n.getDay() <= 5) && ((m >= 570 && m <= 690) || (m >= 780 && m <= 900));
}

/* ---------- Canvas 基础 ---------- */

function setupCanvas() {
  const cv = $('chart'), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext('2d'); ctx.scale(dpr, dpr);
  return { cv, ctx, w, h };
}

function drawChartMessage(message) {
  const { ctx, w, h } = setupCanvas();
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#aeb6c4';
  ctx.font = '12px "Segoe UI", "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(message, w / 2, h / 2, Math.max(1, w - 16));
}

function hgrid(ctx, w, h, PT, PB) {
  ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75].forEach(f => {
    const gy = PT + (h - PT - PB) * f;
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
  });
}

/* 折线（支持 null 断点跳过） */
function strokeSeries(ctx, pts, color, width, alpha) {
  ctx.save();
  ctx.globalAlpha = alpha == null ? 1 : alpha;
  ctx.strokeStyle = color; ctx.lineWidth = width;
  ctx.beginPath();
  let started = false;
  pts.forEach(p => {
    if (p[1] == null) { started = false; return; }
    if (!started) { ctx.moveTo(p[0], p[1]); started = true; }
    else ctx.lineTo(p[0], p[1]);
  });
  ctx.stroke();
  ctx.restore();
}

/* 白色加粗线图例（组合/均分等主线说明） */
function drawLineLegend(ctx, x, y, label) {
  ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.8;
  ctx.beginPath(); ctx.moveTo(x, y - 3); ctx.lineTo(x + 10, y - 3); ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,.75)';
  ctx.font = '9px "Segoe UI", "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(label, x + 13, y);
}

/* ---------- 窗口缩放（程序化：pointermove 逐步 resize_to） ----------
   不用原生 WM 消息：桥接函数在 worker 线程执行，跨线程进不了系统缩放循环。 */
function bindResize() {
  const dirs = {
    n: {x:0,y:-1}, s:{x:0,y:1}, w:{x:-1,y:0}, e:{x:1,y:0},
    nw:{x:-1,y:-1}, ne:{x:1,y:-1}, sw:{x:-1,y:1}, se:{x:1,y:1}
  };
  document.querySelectorAll('[data-resize]').forEach(el => {
    el.addEventListener('pointerdown', async e => {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      const py = api();
      if (!py || !py.get_window_size || !py.resize_to) return;
      try { el.setPointerCapture(e.pointerId); } catch (_) {}
      const dir = dirs[el.dataset.resize] || dirs.se;
      const size = await py.get_window_size();
      if (!size || !size.width) return;
      const cx = e.clientX, cy = e.clientY;
      const w0 = size.width, h0 = size.height;
      const move = ev => {
        py.resize_to(w0 + dir.x * (ev.clientX - cx), h0 + dir.y * (ev.clientY - cy));
      };
      const up = ev => {
        el.removeEventListener('pointermove', move);
        el.removeEventListener('pointerup', up);
        try { el.releasePointerCapture(ev.pointerId); } catch (_) {}
      };
      el.addEventListener('pointermove', move);
      el.addEventListener('pointerup', up);
    });
  });
  window.addEventListener('resize', () => {
    clearTimeout(bindResize._t);
    if (typeof redrawChart === 'function') bindResize._t = setTimeout(redrawChart, 40);
  });
}

/* ---------- 窗口移动（嵌入模式，程序化） ----------
   pywebview 的拖动区机制只在顶层文档生效；被外壳嵌入时，组件卡片标题栏的
   按下事件转为程序化窗口移动（pointermove 逐步 move_to，绝对坐标）。
   独立打开时由 pywebview 内置机制处理。 */
function forwardWindowMove() {
  if (!EMBEDDED) return;
  document.querySelectorAll('.pywebview-drag-region').forEach(el => {
    el.addEventListener('pointerdown', async e => {
      if (e.button !== 0) return;
      if (e.target.closest('button, .tab, .vs, a, input, .nav-btn, .stock-item')) return;
      const py = api();
      if (!py || !py.get_window_pos || !py.move_to) return;
      e.preventDefault();
      try { el.setPointerCapture(e.pointerId); } catch (_) {}
      const p0 = await py.get_window_pos();
      if (!p0 || p0.x == null) return;
      const cx = e.clientX, cy = e.clientY;
      const move = ev => { py.move_to(p0.x + ev.clientX - cx, p0.y + ev.clientY - cy); };
      const up = ev => {
        el.removeEventListener('pointermove', move);
        el.removeEventListener('pointerup', up);
        try { el.releasePointerCapture(ev.pointerId); } catch (_) {}
      };
      el.addEventListener('pointermove', move);
      el.addEventListener('pointerup', up);
    });
  });
}
document.addEventListener('DOMContentLoaded', forwardWindowMove);

/* ---------- 「个股 | 组合」视图切换 ---------- */

function bindViewSwitch() {
  document.querySelectorAll('.vs').forEach(el => {
    el.addEventListener('click', async e => {
      e.stopPropagation();
      if (el.classList.contains('on')) return;
      const py = api();
      if (!py || !py.switch_component) return;  // 浏览器预览（演示模式）下不可切换
      const upd = $('upd');
      if (upd) upd.textContent = '切换中…';
      try { await py.switch_component(el.dataset.view); }
      catch (err) { console.error(err); if (upd) upd.textContent = '切换失败'; }
    });
  });
}
