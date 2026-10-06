// CoolScore landing. The hero is one continuous film (media/film.mp4: five AI-generated shots of the fictional
// tower joined with dissolves) that plays as ordinary video; overlays follow the film's own clock, never the scroll.
// Every number on the page comes from data/tower.json (python tasks.py landing), never from this file.
import { TowerView } from './tower3d.js';
import { initScenes } from './scenes.js';
import { TOWER, FACINGS, FACING_WORDS, dayAt, loadAt, fmtClock } from './timeline.js';

const APP = 'https://coolscore-dubai-jvw959b8tqbsrazygcm7kk.streamlit.app';
const LINKS = { check: `${APP}/Check_a_Unit`, example: `${APP}/Check_a_Unit?example=1`, method: `${APP}/Methodology` };
const GRADE_VAR = { A: 'var(--A)', B: 'var(--B)', C: 'var(--C)', D: 'var(--D)', E: 'var(--E)' };
const GRADE_WORD = { A: 'very low', B: 'low', C: 'typical', D: 'high', E: 'very high' };
const BUDGET = [['sun_glass', '#f5b942', 'Sun through glass'], ['sun_walls', '#ff7a59', 'Sun on roof & walls'], ['people', '#e8c38a', 'People'],
  ['air', '#2ec4b6', 'Outside air'], ['conduction', '#7cc4ff', 'Through walls']];
const FOCUS = { sunrise: 'sun_glass', afternoon: 'sun_walls', evening: 'sun_glass', night: 'air' };

// The film: five 10 s shots joined by 1 s dissolves (46 s). Times below are film seconds.
const FILM_LEN = 46;
const SEG = [{ key: 'dawn', t0: 0 }, { key: 'noon', t0: 9 }, { key: 'evening', t0: 18 }, { key: 'night', t0: 27 }, { key: 'orbit', t0: 36 }];
const BEATS = [[0, 4.2], [4.2, 9.3], [9.3, 18.3], [18.3, 27.3], [27.3, 36.3], [36.3, 46.1]];
const LOCKS = [{ flat: 0, seg: 0, from: 4.8, to: 8.7 }, { flat: 1, seg: 1, from: 13.4, to: 17.9 },
  { flat: 2, seg: 2, from: 20.2, to: 26.8 }, { flat: 3, seg: 3, from: 30.9, to: 35.9 }];
const HEAT = [15.3, 18.4];          // the noon shot carries the (illustrative) heat view from here
const CLOCK = [[0, 5.5], [4.2, 6.4], [9, 7.5], [9.5, 12.6], [18, 13.6], [18.5, 16.5], [27, 17.9], [27.5, 21.6], [36, 22.4], [46, 22.9]];

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
// film quality by screen: 1920 for big or dense screens, 1280 otherwise (phones too: the portrait crop magnifies
// the frame), 768 only when the visitor saves data or is on a slow connection
const slowNet = navigator.connection?.saveData || /(^|-)2g|3g/.test(navigator.connection?.effectiveType || '');
const FILM_SRC = slowNet ? 'media/film-sm.mp4' : (innerWidth >= 760 && innerWidth * Math.min(devicePixelRatio || 1, 2) >= 1700) ? 'media/film-1920.mp4' : 'media/film.mp4';
const $ = (q, el = document) => el.querySelector(q);
const $$ = (q, el = document) => [...el.querySelectorAll(q)];
const aed = (n) => `AED ${Math.round(n).toLocaleString('en-US')}`;
const pad2 = (n) => String(n).padStart(2, '0');
const hour12 = (h) => `${((h + 11) % 12) + 1} ${h < 12 ? 'am' : 'pm'}`;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerpKeys = (keys, x) => {
  if (x <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) if (x <= keys[i][0]) { const [x0, y0] = keys[i - 1], [x1, y1] = keys[i]; return y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
  return keys[keys.length - 1][1];
};
for (const a of $$('[data-app]')) a.href = LINKS[a.dataset.app];

async function boot() {
  const [data, tracks] = await Promise.all([
    fetch('data/tower.json').then((r) => r.json()),
    fetch('data/tracks.json').then((r) => r.json()).catch(() => null),
  ]);
  bindText(data);
  initSmoothScroll();
  initFilm(data, tracks);
  initScenes(data, tracks, { reduced });
  initExplore(data);
  initFindings(data);
  const top = $('.top'), hero = $('#hero');
  const onScroll = () => top.classList.toggle('solid', scrollY > hero.offsetHeight * 0.6);
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
}

// ---------- 1 · the film ----------
function initFilm(data, tracks) {
  const feat = data.featured, climate = data.climate;
  const hero = $('#hero'), video = $('#film');
  const beats = $$('.beat'), buttons = $$('.fb-track button'), fill = $('.fb-fill'), play = $('.fb-play');
  const layer = $('.lock-layer'), brackets = $('.brackets'), line = $('.lock-svg line'), dot = $('.lock-svg circle');
  const tag = $('.lock-tag'), card = $('.flat-card'), badge = $('.heat-badge');
  video.src = FILM_SRC;
  let userPaused = false, visible = true, shownBeat = -1, shownLock = -1, px = 0.5, t = 0;
  // layout is measured only when it changes (never per frame, so the video keeps every frame)
  let W = hero.clientWidth, H = hero.clientHeight, beatBox = null, cardSize = [214, 92];
  const measure = () => { W = hero.clientWidth; H = hero.clientHeight; const b = beats[shownBeat]; const hr = hero.getBoundingClientRect();
    if (b) { const r = b.getBoundingClientRect(); beatBox = { right: r.right - hr.left, top: r.top - hr.top }; } cardSize = [card.offsetWidth, card.offsetHeight]; };
  new ResizeObserver(measure).observe(hero);

  const tryPlay = () => video.play().then(() => play.classList.remove('paused')).catch(() => play.classList.add('paused'));
  if (!reduced) tryPlay(); else play.classList.add('paused');
  play.addEventListener('click', () => {
    if (video.paused) { userPaused = false; tryPlay(); } else { userPaused = true; video.pause(); play.classList.add('paused'); }
    play.setAttribute('aria-label', video.paused ? 'Play film' : 'Pause film');
  });
  for (const b of buttons) b.addEventListener('click', () => { video.currentTime = +b.dataset.t; if (!userPaused) tryPlay(); });
  // save the battery: the film only plays while you can see it
  new IntersectionObserver(([e]) => {
    visible = e.isIntersecting;
    if (!visible) video.pause(); else if (!userPaused && !reduced) tryPlay();
  }, { threshold: 0.15 }).observe(hero);

  const fillCard = (f) => {
    const u = f.unit;
    card.querySelector('.fc-floor').textContent = `Floor ${pad2(f.floor)} · ${FACING_WORDS[f.facing]}`;
    const g = card.querySelector('.fc-grade'); g.textContent = u.score; g.style.background = GRADE_VAR[u.score];
    card.querySelector('.fc-aed').textContent = `${aed(u.annual[0])}–${Math.round(u.annual[2]).toLocaleString('en-US')}`;
    tag.textContent = `Flat ${f.floor}-${f.facing} · CoolScore ${u.score}`;
  };
  const rectAt = (key, ct) => {
    const arr = tracks?.[key]; if (!arr) return null;
    const f = clamp(ct * 24, 0, arr.length - 1), i = Math.floor(f), k = f - i, a = arr[i], b = arr[Math.min(arr.length - 1, i + 1)];
    return a.map((v, j) => v + (b[j] - v) * k);
  };

  function frame() {
    requestAnimationFrame(frame);
    if (!visible) return;
    t = video.currentTime || 0;
    const vw = video.videoWidth || 1152, vh = video.videoHeight || 768;
    const scale = Math.max(W / vw, H / vh), dw = vw * scale, dh = vh * scale;
    const seg = SEG.reduce((acc, s, i) => (t >= s.t0 + (i ? 0.5 : 0) ? i : acc), 0);

    // on narrow screens the crop follows the flat (or the tower) so it stays in frame
    if (W / H < vw / vh - 0.05) {
      const r = rectAt(SEG[seg].key, t - SEG[seg].t0);
      const u = r ? (r[0] + r[2]) / 2 : 0.5;
      const want = clamp((W / 2 - u * dw) / (W - dw), 0, 1);
      px += (want - px) * 0.06;
      video.style.objectPosition = `${(px * 100).toFixed(2)}% 50%`;
    } else if (px !== 0.5) { px = 0.5; video.style.objectPosition = '50% 50%'; }
    const ox = (W - dw) * px, oy = (H - dh) * 0.5;

    // text beats
    const bi = BEATS.findIndex(([a, b]) => t >= a && t < b);
    if (bi !== shownBeat) { beats.forEach((b, i) => b.classList.toggle('on', i === bi)); shownBeat = bi; setTimeout(measure, 0); }
    const ch = clamp(seg, 0, 4);
    buttons.forEach((b, i) => b.classList.toggle('on', i === ch));
    fill.style.width = `${(t / FILM_LEN) * 100}%`;
    badge.classList.toggle('on', t >= HEAT[0] && t < HEAT[1]);

    // the locked-on flat
    const li = LOCKS.findIndex((l) => t >= l.from && t < l.to);
    if (li >= 0) {
      const L = LOCKS[li];
      if (li !== shownLock) { fillCard(feat[L.flat]); shownLock = li; measure(); }
      const r = rectAt(SEG[L.seg].key, t - SEG[L.seg].t0);
      placeLock(r, ox, oy, dw, dh, W, H, Math.min(1, (t - L.from) / 0.6));
      layer.classList.add('on');
    } else layer.classList.remove('on');
  }

  function placeLock(r, ox, oy, dw, dh, W, H, lock) {
    const narrow = W < 760;
    const textRight = !narrow && beatBox ? beatBox.right + 28 : 0;
    const textTop = narrow && beatBox ? beatBox.top - 14 : H - 110;
    const top = narrow ? 112 : 92;
    let R = { left: ox + r[0] * dw, right: ox + r[2] * dw, top: oy + r[1] * dh, bottom: oy + r[3] * dh };
    R = { left: Math.max(14, R.left), right: Math.min(W - 14, R.right), top: Math.max(top - 10, R.top), bottom: Math.min(textTop - 16, R.bottom) };
    const hidden = R.right - R.left < 8 || R.bottom - R.top < 8;
    const g = (1 - lock) * 36;
    const x0 = R.left - g, x1 = R.right + g, y0 = R.top - g, y1 = R.bottom + g;
    const Lb = Math.max(8, Math.min(22, (x1 - x0) / 4, (y1 - y0) / 4));
    brackets.setAttribute('d', hidden ? '' : `M${x0} ${y0 + Lb}V${y0}H${x0 + Lb}M${x1 - Lb} ${y0}H${x1}V${y0 + Lb}M${x1} ${y1 - Lb}V${y1}H${x1 - Lb}M${x0 + Lb} ${y1}H${x0}V${y1 - Lb}`);
    tag.style.display = hidden ? 'none' : '';
    tag.style.transform = `translate(${x0}px, ${narrow ? Math.max(top - 6, y0 - 24) : Math.min(H - 130, y1 + 8)}px)`;
    const [cw, chh] = cardSize;
    let x = clamp(Math.min(R.right, W - 40) - cw, 16, W - cw - 16);
    if (textRight) x = clamp(Math.max(x, textRight), 16, W - cw - 16);
    let y = R.top - chh - 30;
    if (narrow) y = clamp(y, top, textTop - chh);
    const above = narrow ? y + chh <= R.top + 4 : y >= top;
    if (!above && !narrow) y = clamp(R.bottom + 34, top, H - 120 - chh);
    card.style.transform = `translate(${x}px, ${y}px)`;
    card.style.opacity = lock.toFixed(3);
    const lx = clamp(x + cw / 2, R.left + 12, R.right - 12), ly = above ? y0 : y1;
    line.setAttribute('x1', lx); line.setAttribute('y1', ly); line.setAttribute('x2', x + cw / 2); line.setAttribute('y2', above ? y + chh : y);
    line.style.opacity = hidden ? 0 : lock; dot.style.opacity = hidden ? 0 : 1;
    dot.setAttribute('cx', lx); dot.setAttribute('cy', ly);
  }

  // live readings, a few times a second
  setInterval(() => {
    if (!visible) return;
    const clock = lerpKeys(CLOCK, t);
    const day = dayAt(clock, climate);
    const bi = clamp(shownBeat, 0, 5);
    const f = feat[clamp(bi - 1, 0, 3)];
    $('#fb-clock').textContent = fmtClock(clock);
    $('#fb-temp').textContent = `${day.temp.toFixed(1)} °C`;
    $('#fb-ac-label').textContent = `AC · Fl ${pad2(f.floor)}`;
    $('#fb-ac').textContent = `${loadAt(f.load_kw_by_hour, clock).toFixed(1)} kW`;
  }, 200);
  requestAnimationFrame(frame);
}

// ---------- smooth scrolling (Lenis), kept in step with GSAP's ScrollTrigger ----------
function initSmoothScroll() {
  if (reduced || !window.Lenis) return;
  const lenis = new window.Lenis({ lerp: 0.085, smoothWheel: true, anchors: true });
  window.__lenis = lenis;
  if (window.gsap && window.ScrollTrigger) {
    lenis.on('scroll', window.ScrollTrigger.update);
    window.gsap.ticker.add((t) => lenis.raf(t * 1000));
    window.gsap.ticker.lagSmoothing(0);
  } else {
    const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
    requestAnimationFrame(raf);
  }
}

// ---------- 3 · explore: the 3D tower, graded ----------
function initExplore(data) {
  const units = new Map(data.units.map((u) => [`${u.floor}:${u.facing}`, u]));
  const lo = Math.min(...data.units.map((u) => u.annual[0])), hi = Math.max(...data.units.map((u) => u.annual[2]));
  let floor = 14, facing = 'W', view = null, visible = false;
  const section = $('#explore'), canvas = $('#world');
  const svg = $('#plan'), card = $('#ex-card'), range = $('#ex-range'), level = $('#ex-level');
  const NS = 'http://www.w3.org/2000/svg';
  const pt = (az, r) => [150 + r * Math.sin(az * Math.PI / 180), 150 - r * Math.cos(az * Math.PI / 180)];
  const R = 128, RC = 46;
  const wedges = FACINGS.map((f, k) => {
    const a0 = k * 45 - 22.5, a1 = k * 45 + 22.5;
    const d = [pt(a0, R), pt(a1, R), pt(a1, RC), pt(a0, RC)].map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ') + 'Z';
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', d); path.setAttribute('class', 'wedge'); path.setAttribute('tabindex', '0'); path.setAttribute('role', 'button');
    path.addEventListener('click', () => select(floor, f));
    path.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(floor, f); } });
    svg.appendChild(path);
    const [tx, ty] = pt(k * 45, 90);
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('x', tx); t.setAttribute('y', ty + 4); t.setAttribute('text-anchor', 'middle');
    svg.appendChild(t);
    return { path, t, f };
  });
  const core = document.createElementNS(NS, 'path');
  core.setAttribute('d', Array.from({ length: 8 }, (_, k) => pt(k * 45 + 22.5, RC - 6)).map((p, i) => `${i ? 'L' : 'M'}${p[0]} ${p[1]}`).join(' ') + 'Z');
  core.setAttribute('class', 'core'); svg.appendChild(core);
  const north = document.createElementNS(NS, 'path');
  north.setAttribute('d', 'M150 -6 L144 6 L156 6 Z'); north.setAttribute('class', 'north'); svg.appendChild(north);

  function render() {
    level.textContent = pad2(floor); range.value = floor;
    for (const w of wedges) {
      const u = units.get(`${floor}:${w.f}`);
      w.path.style.fill = GRADE_VAR[u.score];
      w.path.style.opacity = w.f === facing ? 1 : 0.62;
      w.path.classList.toggle('sel', w.f === facing);
      w.path.setAttribute('aria-label', `Floor ${floor}, ${FACING_WORDS[w.f]}: CoolScore ${u.score}`);
      w.t.textContent = `${w.f} · ${u.score}`;
    }
    const u = units.get(`${floor}:${facing}`);
    const pos = (v) => `${(((v - lo) / (hi - lo)) * 100).toFixed(1)}%`;
    const drivers = u.drivers.map(([label, v]) => `<li><span>${label}</span><b>${v >= 0 ? '+' : '−'}${aed(Math.abs(v))}</b></li>`).join('');
    card.innerHTML = `
      <div class="k">Level ${pad2(floor)} · ${FACING_WORDS[facing]}-facing${floor === TOWER.floors ? ' · top floor' : ''}</div>
      <div class="row2"><span class="grade" style="background:${GRADE_VAR[u.score]}">${u.score}</span>
        <span class="word">CoolScore ${u.score}<br>${GRADE_WORD[u.score]} cooling cost per sq ft</span></div>
      <div class="aed">${aed(u.annual[0])} – ${Math.round(u.annual[2]).toLocaleString('en-US')}</div>
      <div class="note">a year · P10–P90 · simulated</div>
      <div class="bar"><i style="left:${pos(u.annual[0])};width:calc(${pos(u.annual[2])} - ${pos(u.annual[0])})"></i><u style="left:${pos(u.annual[1])}"></u></div>
      <div class="bar-axis"><span>${(lo / 1000).toFixed(1)}k</span><span>median ${aed(u.annual[1])}</span><span>${(hi / 1000).toFixed(1)}k</span></div>
      <div class="note" style="margin-top:8px">August ≈ ${aed(u.august)} · vs a typical flat:</div>
      <ul class="drivers">${drivers}</ul>`;
  }
  function select(fl, fc, turn = true) { floor = clamp(fl, 1, TOWER.floors); facing = fc; render(); view?.select(floor, facing, { turn }); }
  range.addEventListener('input', () => select(+range.value, facing, false));
  for (const b of $$('.ex-step')) b.addEventListener('click', () => select(floor + +b.dataset.step, facing, false));
  const toggle = $('.ex-toggle');
  toggle.addEventListener('click', () => { const on = toggle.getAttribute('aria-pressed') !== 'true'; toggle.setAttribute('aria-pressed', on); view?.setData(on); });
  render();

  // the 3D tower is built only when you get near it, plays its arrival when it comes into view, and only draws
  // while it's on screen
  const start = () => {
    if (view) return;
    try { view = new TowerView(canvas, { mobile: matchMedia('(pointer: coarse)').matches || innerWidth < 760 }); view.setGrades(data.units); view.select(floor, facing, { turn: false }); }
    catch (err) { console.warn('3D view unavailable', err); return; }
    window.__cs = { view };                                  // for QA scripts
    addEventListener('resize', () => view.resize());
    let last = performance.now();
    const loop = (now) => {
      requestAnimationFrame(loop);
      const dt = Math.min(0.05, Math.max(0, (now - last) / 1000)); last = now;
      if (visible) view.update(dt, { frame: section.clientWidth > 1000 ? 1 : 0 });
    };
    requestAnimationFrame(loop);
  };
  new IntersectionObserver(([e]) => { if (e.isIntersecting) start(); }, { rootMargin: '700px 0px' }).observe(section);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) { start(); view?.start(); } }, { threshold: 0.35 }).observe(section);

  // drag to turn (with inertia), hover a window for its numbers, tap to pick it
  const tip = $('.ex-tip');
  let down = null, lastPick = 0;
  const ndc = (e) => { const r = canvas.getBoundingClientRect(); return [((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1, e.clientX - r.left, e.clientY - r.top]; };
  canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, last: e.clientX, moved: false }; });
  addEventListener('pointermove', (e) => {
    if (down) {
      if (Math.abs(e.clientX - down.x) > 4) down.moved = true;
      if (down.moved) { view?.drag(e.clientX - down.last); tip.classList.remove('on'); }
      down.last = e.clientX;
      return;
    }
    if (!view || e.target !== canvas || performance.now() - lastPick < 40) return;
    lastPick = performance.now();
    const [nx, ny, px, py] = ndc(e), hit = view.pick(nx, ny);
    view.hover(hit);
    canvas.style.cursor = hit ? 'pointer' : 'grab';
    if (hit) {
      const u = units.get(`${hit.floor}:${hit.facing}`);
      tip.innerHTML = `<b>Flat ${hit.floor}-${hit.facing}</b> · CoolScore ${u.score} · median ${aed(u.annual[1])}/yr`;
      tip.style.transform = `translate(${px + 14}px, ${py + 14}px)`;
      tip.classList.add('on');
    } else tip.classList.remove('on');
  });
  canvas.addEventListener('pointerleave', () => { if (!down) { view?.hover(null); tip.classList.remove('on'); } });
  addEventListener('pointerup', (e) => {
    if (down && !down.moved && view) { const [nx, ny] = ndc(e), hit = view.pick(nx, ny); if (hit) select(hit.floor, hit.facing); }
    if (down?.moved) view?.release();
    down = null;
  });
}

// ---------- text bound to data ----------
function bindText(data) {
  const f = Object.fromEntries(data.featured.map((x) => [x.key, x]));
  const c = data.climate, hr = c.hourly;
  const sample = (arr, x) => { const i = Math.floor(x), t = x - i; return arr[i % 24] + (arr[(i + 1) % 24] - arr[i % 24]) * t; };
  const peakHour = (p) => p.indexOf(Math.max(...p));
  const g = data.spread.grades;
  const V = {
    'sunrise.temp': `${Math.round(sample(hr.temp, 7))} °C`,
    'sunrise.sun_glass': `${f.sunrise.budget_pct.sun_glass}%`,
    'afternoon.elev': `${Math.round(sample(hr.elev, 13.5))}°`,
    'afternoon.temp': `${Math.round(sample(hr.temp, 13))} °C`,
    hot_days: `${Math.round(c.days_over_40)}`,
    'afternoon.grade': f.afternoon.unit.score,
    'evening.wm2': `${Math.max(...hr.facade.W)} W/m²`,
    'evening.peak': hour12(peakHour(f.evening.load_kw_by_hour)),
    'night.temp_big': `${Math.round(sample(hr.temp, 22))} °C`,
    'night.kw': `${f.night.load_kw_by_hour[22].toFixed(1)} kW of heat`,
    'night.rh': `${Math.round(sample(hr.rh, 22))}%`,
    'night.air': `${f.night.budget_pct.air}%`,
    'night.p50': aed(data.spread.lowest.annual[1]),
    'spread.grades': g.length > 1 ? `${g[0]} to ${g[g.length - 1]}` : g[0],
    'spread.lo': aed(data.spread.lowest.annual[1]),
    'spread.hi': aed(data.spread.highest.annual[1]),
    simulated: data.simulated_label,
    disclaimer: data.disclaimer,
  };
  for (const el of $$('[data-v]')) if (V[el.dataset.v] !== undefined) el.textContent = V[el.dataset.v];
}

// ---------- findings: big numbers that count up when they come into view ----------
function initFindings(data) {
  const pct = (k) => data.featured.map((f) => f.budget_pct[k]);
  const air = pct('air'), sun = pct('sun_glass'), g = data.spread.grades;
  const V = {
    'spread.gap': { to: [data.spread.highest.annual[1] - data.spread.lowest.annual[1]], fmt: ([n]) => `${n.toLocaleString('en-US')}<span class="u">AED</span>` },
    'night.air_pct': { to: [Math.min(...air), Math.max(...air)], fmt: ([a, b]) => `${a}–${b}<span class="u">%</span>` },
    'evening.sun_pct': { to: [Math.min(...sun), Math.max(...sun)], fmt: ([a, b]) => `${a}–${b}<span class="u">%</span>` },
    grades: { to: null, fmt: () => `${g[0]}–${g[g.length - 1]}` },
  };
  const els = $$('[data-count]');
  for (const el of els) { const v = V[el.dataset.count]; el.innerHTML = v.fmt(v.to ? v.to : []); }
  const run = (el) => {
    const v = V[el.dataset.count]; if (!v.to || reduced) return;
    const t0 = performance.now();
    const tick = (now) => {
      const k = Math.min(1, (now - t0) / 1400), e = 1 - (1 - k) ** 3;
      el.innerHTML = v.fmt(v.to.map((n) => Math.round(n * e)));
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { run(e.target); io.unobserve(e.target); } }), { threshold: 0.6 });
  els.forEach((el) => io.observe(el));
}

boot().catch((err) => console.error(err));
