/* 公共前端工具：pywebview 桥接、格式化、Canvas 基础绘制、窗口缩放与视图切换。
   页面需先引入本文件，再写自己的逻辑；页面需提供 redrawChart() 供窗口缩放后重绘。 */

const $ = id => document.getElementById(id);

function api() {
  return (window.pywebview && pywebview.api) ? pywebview.api : null;
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

/* 「均分」图例（白色加粗线） */
function drawAvgLegend(ctx, x, y) {
  ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.8;
  ctx.beginPath(); ctx.moveTo(x, y - 3); ctx.lineTo(x + 10, y - 3); ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,.75)';
  ctx.font = '9px "Segoe UI", "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('均分', x + 13, y);
}

/* ---------- 窗口缩放（拖边原生缩放 + 程序化回退） ---------- */

function bindResize() {
  const dirs = {
    n: {x:0,y:-1}, s:{x:0,y:1}, w:{x:-1,y:0}, e:{x:1,y:0},
    nw:{x:-1,y:-1}, ne:{x:1,y:-1}, sw:{x:-1,y:1}, se:{x:1,y:1}
  };
  document.querySelectorAll('[data-resize]').forEach(el => {
    el.addEventListener('pointerdown', async e => {
      e.preventDefault();
      e.stopPropagation();
      const py = api();
      if (!py) return;
      try {
        if (py.start_resize && await py.start_resize(el.dataset.resize)) return;
      } catch (err) { console.error(err); }
      if (!py.resize_to || !py.get_window_size) return;
      const dir = dirs[el.dataset.resize] || dirs.se;
      const size = await py.get_window_size();
      const sx = e.screenX, sy = e.screenY;
      const w0 = size.width, h0 = size.height;
      const move = ev => {
        py.resize_to(w0 + dir.x * (ev.screenX - sx), h0 + dir.y * (ev.screenY - sy));
      };
      const up = () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', up);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
    });
  });
  window.addEventListener('resize', () => {
    clearTimeout(bindResize._t);
    bindResize._t = setTimeout(redrawChart, 40);
  });
}

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
