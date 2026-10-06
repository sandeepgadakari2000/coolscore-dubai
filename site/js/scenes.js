// "The day, flat by flat": four pinned scenes. Each one opens its film loop out of a card, reveals its words,
// then pops the flat's numbers in: grade, cost range, the August heat budget (emphasis ring: the share the
// scene is about in the accent colour, the rest in quiet greys, every part labelled), the flat's AC load
// through the day (one series, hover readout) and the readings at that hour. Motion uses GSAP + ScrollTrigger
// when they're available; without them (or with reduced motion) everything is simply shown.
import { FACING_WORDS, dayAt } from './timeline.js';

const GRADE_VAR = { A: 'var(--A)', B: 'var(--B)', C: 'var(--C)', D: 'var(--D)', E: 'var(--E)' };
const PARTS = [['sun_glass', 'Sun through glass'], ['sun_walls', 'Sun on roof & walls'], ['people', 'People & appliances'], ['air', 'Outside air & humidity'], ['conduction', 'Heat through walls']];
const FOCUS = { sunrise: 'sun_glass', afternoon: 'sun_walls', evening: 'sun_glass', night: 'air' };
const GREYS = ['#5d677e', '#48516a', '#39415a', '#6f7a93'];
const ICONS = {
  temp: '<svg viewBox="0 0 24 24"><path d="M14 14.8V5a2 2 0 1 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v7"/></svg>',
  sun: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  fan: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="8" rx="2"/><path d="M7 16c0 2 1 3 1 3M12 16v3M17 16c0 2-1 3-1 3M7 9h10"/></svg>',
  cal: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
};
const pad2 = (n) => String(n).padStart(2, '0');
const fmt = (n, d = 0) => Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const count = (to, d = 0, pre = '', post = '') => `<span class="count" data-to="${to}" data-d="${d}" data-pre="${pre}" data-post="${post}">${pre}${fmt(to, d)}${post}</span>`;

function panelHTML(f, climate) {
  const u = f.unit, focus = FOCUS[f.key], day = dayAt(f.hour, climate);
  const glass = day.elev > 0 ? Math.round(day.facade(f.facing)) : 0;
  const label = { sun_glass: 'sun through glass', sun_walls: 'sun on the roof', air: 'outside air', people: 'people', conduction: 'through walls' }[focus];
  let gi = 0;
  const parts = PARTS.map(([k, name]) => `<li class="${k === focus ? 'hl' : ''}" style="--c:${k === focus ? 'var(--accent)' : GREYS[gi++ % 4]}"><i></i>${name}<b>${f.budget_pct[k]}%</b></li>`).join('');
  return `
    <div class="p-head">
      <span class="gbadge" style="--g:${GRADE_VAR[u.score]}"><b>${u.score}</b><i class="ring"></i></span>
      <div><div class="p-k">Floor ${pad2(f.floor)} · ${FACING_WORDS[f.facing]} · CoolScore ${u.score}</div>
        <div class="p-aed">AED ${count(u.annual[0])} – ${count(u.annual[2])}</div>
        <div class="p-note">a year to cool · P10–P90 · simulated</div></div>
    </div>
    <div class="p-body">
      <div class="donut" role="img" aria-label="August cooling for this flat: ${PARTS.map(([k, n]) => `${n} ${f.budget_pct[k]}%`).join(', ')}">
        <svg viewBox="0 0 120 120"></svg>
        <div class="d-center"><b>${count(f.budget_pct[focus], 0, '', '%')}</b><span>${label}</span></div>
      </div>
      <ul class="parts" aria-hidden="true">${parts}</ul>
    </div>
    <div class="p-chart">
      <div class="pc-head"><span>This flat's AC through an August day</span><b>${f.load_kw_by_hour[f.hour].toFixed(1)} kW at ${pad2(f.hour)}:00</b></div>
      <svg viewBox="0 0 360 104" role="img" aria-label="Average August day of cooling load for this flat, between ${Math.min(...f.load_kw_by_hour).toFixed(1)} and ${Math.max(...f.load_kw_by_hour).toFixed(1)} kW; it never drops to zero"></svg>
      <div class="pc-tip"></div>
    </div>
    <div class="p-stats">
      <div class="stat">${ICONS.temp}<b>${count(day.temp, 0, '', ' °C')}</b><span>Outside</span></div>
      <div class="stat">${ICONS.sun}<b>${count(glass, 0, '', ' W/m²')}</b><span>Sun on its glass</span></div>
      <div class="stat">${ICONS.fan}<b>${count(f.load_kw_by_hour[f.hour], 1, '', ' kW')}</b><span>AC load now</span></div>
      <div class="stat">${ICONS.cal}<b>${count(u.august, 0, 'AED ')}</b><span>August bill</span></div>
    </div>`;
}

// emphasis ring: the scene's share in the accent, the rest grey, 2-unit gaps between parts
function drawDonut(svg, f) {
  const NS = 'http://www.w3.org/2000/svg', r = 46, C = 2 * Math.PI * r, gap = 2.4, focus = FOCUS[f.key];
  const track = document.createElementNS(NS, 'circle');
  Object.entries({ cx: 60, cy: 60, r, fill: 'none', stroke: 'rgba(255,255,255,.05)', 'stroke-width': 12 }).forEach(([k, v]) => track.setAttribute(k, v));
  svg.appendChild(track);
  let start = 0, gi = 0;
  const segs = [];
  for (const [k] of PARTS) {
    const len = Math.max(0.5, (f.budget_pct[k] / 100) * C - gap);
    const c = document.createElementNS(NS, 'circle');
    Object.entries({ cx: 60, cy: 60, r, class: `seg${k === focus ? ' hl' : ''}`, stroke: k === focus ? 'var(--accent)' : GREYS[gi++ % 4], 'stroke-dasharray': `${len} ${C}`, 'stroke-dashoffset': -start }).forEach(([a, v]) => c.setAttribute(a, v));
    c.dataset.len = len; c.dataset.c = C;
    svg.appendChild(c); segs.push(c);
    start += (f.budget_pct[k] / 100) * C;
  }
  return segs;
}

// one series over 24 hours, baseline at zero (the point: it never gets there), the scene's hour marked
function drawArea(wrap, f) {
  const svg = wrap.querySelector('svg'), tip = wrap.querySelector('.pc-tip'), NS = 'http://www.w3.org/2000/svg';
  const L = 34, Rr = 352, T = 12, B = 84, v = [...f.load_kw_by_hour, f.load_kw_by_hour[0]];
  const top = Math.ceil(Math.max(...v) + 0.5);
  const x = (h) => L + (h / 24) * (Rr - L), y = (k) => B - (k / top) * (B - T);
  const el = (tag, attrs, parent = svg) => { const e = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([a, b]) => e.setAttribute(a, b)); parent.appendChild(e); return e; };
  const defs = el('defs', {});
  const gid = `ag${f.key}`;
  const lg = el('linearGradient', { id: gid, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  el('stop', { offset: 0, 'stop-color': 'var(--accent)', 'stop-opacity': 0.42 }, lg);
  el('stop', { offset: 1, 'stop-color': 'var(--accent)', 'stop-opacity': 0 }, lg);
  for (const k of [0, top / 2, top]) {
    el('line', { class: 'grid', x1: L, x2: Rr, y1: y(k), y2: y(k) });
    el('text', { class: 'axis', x: L - 6, y: y(k) + 3, 'text-anchor': 'end' }).textContent = k === top ? `${top} kW` : k ? fmt(k, k % 1 ? 1 : 0) : '0';
  }
  for (const h of [0, 6, 12, 18, 24]) el('text', { class: 'axis', x: x(h), y: B + 13, 'text-anchor': 'middle' }).textContent = pad2(h % 24 === 0 && h ? 24 : h);
  // smooth curve through the hourly points (Catmull-Rom → cubic Bézier)
  const pts = v.map((k, h) => [x(h), y(k)]);
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    d += ` C${p1[0] + (p2[0] - p0[0]) / 6},${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6},${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]},${p2[1]}`;
  }
  const area = el('path', { d: `${d} L${x(24)},${B} L${x(0)},${B} Z`, fill: `url(#${gid})` });
  const line = el('path', { d, class: 'line' });
  const cross = el('line', { class: 'cross', x1: 0, x2: 0, y1: T, y2: B });
  const hdot = el('circle', { class: 'hdot', r: 3.5, cx: -10, cy: -10 });
  const mx = x(f.hour), my = y(f.load_kw_by_hour[f.hour]);
  const mark = el('circle', { class: 'mark', cx: mx, cy: my, r: 4.5 });
  const ml = el('text', { class: 'mlabel', x: Math.min(Rr - 30, Math.max(L + 30, mx)), y: my - 10, 'text-anchor': 'middle' });
  ml.textContent = `${pad2(f.hour)}:00 · ${f.load_kw_by_hour[f.hour].toFixed(1)} kW`;
  // hover: crosshair + tooltip on the nearest hour
  const move = (e) => {
    const r = svg.getBoundingClientRect(), sx = ((e.clientX - r.left) / r.width) * 360;
    const h = Math.max(0, Math.min(23, Math.round(((sx - L) / (Rr - L)) * 24)));
    cross.setAttribute('x1', x(h)); cross.setAttribute('x2', x(h));
    hdot.setAttribute('cx', x(h)); hdot.setAttribute('cy', y(v[h]));
    tip.innerHTML = `<b>${pad2(h)}:00</b> · ${v[h].toFixed(2)} kW`;
    tip.style.left = `${(x(h) / 360) * 100}%`;
  };
  svg.addEventListener('pointermove', move);
  svg.addEventListener('pointerdown', (e) => { wrap.classList.add('touch'); move(e); });
  svg.addEventListener('pointerleave', () => wrap.classList.remove('touch'));
  return { line, area, mark, ml };
}

// gold brackets that follow the flat inside the looping clip (same optical-flow tracks as the hero)
function trackVideo(frame, video, rects) {
  const vf = frame.querySelector('.vf'), path = vf.querySelector('path'), tag = frame.querySelector('.ftag');
  let W = 1, H = 1;
  const size = () => { W = frame.clientWidth; H = frame.clientHeight; vf.setAttribute('viewBox', `0 0 ${W} ${H}`); };
  new ResizeObserver(size).observe(frame); size();
  const draw = (t) => {
    if (!rects) return;
    const fr = Math.min(rects.length - 1, Math.max(0, t * 24)), i = Math.floor(fr), k = fr - i, a = rects[i], b = rects[Math.min(rects.length - 1, i + 1)];
    const r = a.map((v, j) => v + (b[j] - v) * k);
    // the video is scaled about its centre (Ken Burns); follow that
    const sc = parseFloat(getComputedStyle(video).transform.split(',')[3]) || 1;
    const X = (u) => W / 2 + (u * W - W / 2) * sc, Y = (v) => H / 2 + (v * H - H / 2) * sc;
    const x0 = Math.max(6, X(r[0])), x1 = Math.min(W - 6, X(r[2])), y0 = Math.max(6, Y(r[1])), y1 = Math.min(H - 6, Y(r[3]));
    if (x1 - x0 < 6 || y1 - y0 < 6) { path.setAttribute('d', ''); return; }
    const l = Math.max(6, Math.min(16, (x1 - x0) / 4, (y1 - y0) / 4));
    path.setAttribute('d', `M${x0} ${y0 + l}V${y0}H${x0 + l}M${x1 - l} ${y0}H${x1}V${y0 + l}M${x1} ${y1 - l}V${y1}H${x1 - l}M${x0 + l} ${y1}H${x0}V${y1 - l}`);
    tag.style.transform = `translate(${x0}px, ${Math.min(H - 24, y1 + 6)}px)`;
  };
  if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
    const step = (now, meta) => { draw(meta.mediaTime); video.requestVideoFrameCallback(step); };
    video.requestVideoFrameCallback(step);
  } else { const loop = () => { if (!video.paused) draw(video.currentTime); requestAnimationFrame(loop); }; loop(); }
}

export function initScenes(data, tracks, { reduced = false } = {}) {
  const G = window.gsap, ST = window.ScrollTrigger, Split = window.SplitText;
  const motion = !!(G && ST) && !reduced;
  if (motion) G.registerPlugin(ST, ...(Split ? [Split] : []));
  const wide = () => innerWidth > 1000;
  const scenes = [...document.querySelectorAll('.scene')];

  scenes.forEach((scene) => {
    const f = data.featured[+scene.dataset.flat];
    const panel = scene.querySelector('.panel'), frame = scene.querySelector('.frame'), video = frame.querySelector('video');
    const media = scene.querySelector('.media');
    panel.innerHTML = panelHTML(f, data.climate);
    const segs = drawDonut(panel.querySelector('.donut svg'), f);
    const chart = drawArea(panel.querySelector('.p-chart'), f);
    frame.querySelector('.ftag').textContent = `Flat ${f.floor}-${f.facing} · CoolScore ${f.unit.score}`;
    // wrap the frame so pointer tilt and scroll motion don't fight over one transform
    const tilt = document.createElement('div'); tilt.className = 'tilt';
    frame.parentNode.insertBefore(tilt, frame); tilt.appendChild(frame);
    trackVideo(frame, video, tracks?.[scene.dataset.clip]);

    // the loop plays only near the viewport
    new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { if (!video.getAttribute('src')) video.src = video.dataset.src; if (!reduced) video.play().catch(() => {}); }
      else video.pause();
    }, { rootMargin: '25% 0px' }).observe(scene);

    // pointer tilt with a moving glare
    if (motion && matchMedia('(pointer: fine)').matches) {
      const rx = G.quickTo(tilt, 'rotationX', { duration: 0.6, ease: 'power3' }), ry = G.quickTo(tilt, 'rotationY', { duration: 0.6, ease: 'power3' });
      media.addEventListener('pointermove', (e) => {
        const r = frame.getBoundingClientRect(), px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
        ry((px - 0.5) * 9); rx((0.5 - py) * 7);
        frame.style.setProperty('--gx', `${px * 100}%`); frame.style.setProperty('--gy', `${py * 100}%`);
      });
      media.addEventListener('pointerleave', () => { rx(0); ry(0); });
    }

    if (!motion) { frame.classList.add('locked'); return; }

    // the entrance: a timeline that plays when the scene arrives and rewinds if you scroll back above it
    const title = scene.querySelector('.st'), lede = scene.querySelector('.sl');
    const tWords = Split ? new Split(title, { type: 'words', mask: 'words' }).words : [title];
    const lWords = Split ? new Split(lede, { type: 'words' }).words : [lede];
    const counters = [...panel.querySelectorAll('.count')];
    const tl = G.timeline({ paused: true, defaults: { ease: 'expo.out' } });
    tl.fromTo(frame, { clipPath: 'inset(12% 9% 12% 9% round 40px)' }, { clipPath: 'inset(0% 0% 0% 0% round 22px)', duration: 1.5 }, 0)
      .from(video, { opacity: 0, duration: 1.0, ease: 'power2.out' }, 0.05)
      .from(frame.querySelector('.chip'), { y: -18, autoAlpha: 0, duration: 0.7 }, 0.55)
      .from(scene.querySelector('.ghost'), { autoAlpha: 0, duration: 1.6, ease: 'power2.out' }, 0)
      .from(scene.querySelector('.eyebrow'), { x: -28, autoAlpha: 0, duration: 0.8 }, 0.15)
      .from(tWords, { yPercent: 115, duration: 1.05, stagger: 0.055 }, 0.22)
      .from(lWords, { y: 14, autoAlpha: 0, filter: 'blur(6px)', duration: 0.7, stagger: 0.012 }, 0.45)
      .from(panel, { y: 46, scale: 0.95, autoAlpha: 0, filter: 'blur(10px)', duration: 0.95, ease: 'back.out(1.4)' }, 0.62)
      .from(panel.querySelector('.gbadge'), { scale: 0, rotation: -60, duration: 1.1, ease: 'elastic.out(1, 0.55)' }, 0.95)
      .fromTo(panel.querySelector('.ring'), { scale: 1, autoAlpha: 0.9 }, { scale: 2.5, autoAlpha: 0, duration: 1.2, ease: 'power2.out' }, 1.05)
      .from(panel.querySelectorAll('.parts li'), { x: 18, autoAlpha: 0, duration: 0.55, stagger: 0.06 }, 1.2)
      .from(panel.querySelectorAll('.stat'), { y: 22, scale: 0.88, autoAlpha: 0, duration: 0.75, stagger: 0.08, ease: 'back.out(1.8)' }, 1.45)
      .from(media.querySelector('figcaption'), { y: 14, autoAlpha: 0, duration: 0.9 }, 1.3)
      .call(() => frame.classList.add('locked'), null, 1.4);
    segs.forEach((c, i) => tl.fromTo(c, { attr: { 'stroke-dasharray': `0 ${c.dataset.c}` } }, { attr: { 'stroke-dasharray': `${c.dataset.len} ${c.dataset.c}` }, duration: 0.75, ease: 'power3.out' }, 1.0 + i * 0.11));
    const len = chart.line.getTotalLength();
    tl.fromTo(chart.line, { strokeDasharray: len, strokeDashoffset: len }, { strokeDashoffset: 0, duration: 1.5, ease: 'power2.inOut' }, 1.15)
      .from(chart.area, { autoAlpha: 0, duration: 0.9, ease: 'power2.out' }, 1.75)
      .from([chart.mark, chart.ml], { scale: 0, autoAlpha: 0, transformOrigin: '50% 50%', duration: 0.6, ease: 'back.out(3)' }, 2.3);
    counters.forEach((el) => {
      const to = +el.dataset.to, d = +el.dataset.d, o = { v: 0 };
      tl.to(o, { v: to, duration: 1.4, ease: 'power3.out', onUpdate: () => { el.textContent = `${el.dataset.pre}${fmt(o.v, d)}${el.dataset.post}`; } }, 1.0);
    });
    ST.create({ trigger: scene, start: wide() ? 'top 45%' : 'top 75%', onEnter: () => tl.play(), onLeaveBack: () => { tl.reverse(); frame.classList.remove('locked'); } });

    // while pinned: the clip slowly pushes in, the big time drifts, the card floats; then it hands over to the next
    if (wide()) {
      G.timeline({ scrollTrigger: { trigger: scene, start: 'top bottom', end: 'bottom top', scrub: 1.2 } })
        .fromTo(video, { scale: 1.2 }, { scale: 1.02, ease: 'none' }, 0)
        .fromTo(scene.querySelector('.ghost'), { xPercent: 10 }, { xPercent: -16, ease: 'none' }, 0)
        .fromTo(media, { y: 60 }, { y: -40, ease: 'none' }, 0);
      G.to(scene.querySelector('.scene-grid'), { autoAlpha: 0.15, scale: 0.94, filter: 'blur(8px)', ease: 'power1.in',
        scrollTrigger: { trigger: scene, start: 'bottom 122%', end: 'bottom 96%', scrub: true } });
    }
  });

  // the day rail: where you are in the day, and a way to jump
  const rail = document.querySelector('.day-rail');
  if (rail && scenes.length) {
    const links = [...rail.querySelectorAll('a')], fill = rail.querySelector('.dr-fill');
    const set = () => {
      const first = scenes[0].getBoundingClientRect(), last = scenes[scenes.length - 1].getBoundingClientRect();
      const span = last.bottom - first.top - innerHeight, p = Math.min(1, Math.max(0, -first.top / Math.max(1, span)));
      rail.classList.toggle('on', first.top < innerHeight * 0.5 && last.bottom > innerHeight * 0.5);
      fill.style.height = `${p * 100}%`;
      const i = scenes.findIndex((s) => { const r = s.getBoundingClientRect(); return r.top <= innerHeight * 0.5 && r.bottom > innerHeight * 0.5; });
      links.forEach((a, j) => a.classList.toggle('on', j === i));
    };
    addEventListener('scroll', set, { passive: true }); set();
    links.forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      const s = scenes[+a.dataset.to], top = s.getBoundingClientRect().top + scrollY + innerHeight * 0.35;
      if (window.__lenis) window.__lenis.scrollTo(top, { duration: 1.4 }); else scrollTo({ top, behavior: 'smooth' });
    }));
  }
}
