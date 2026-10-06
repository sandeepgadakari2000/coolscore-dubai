// Shared pieces for the CoolScore app pages: API, nav, the unit form, the embedded scene/X-ray, charts.
export const $ = (q, el = document) => el.querySelector(q);
export const $$ = (q, el = document) => [...el.querySelectorAll(q)];
export const aed = (n) => `AED ${Math.round(n).toLocaleString('en-US')}`;
export const aedR = (r) => `AED ${Math.round(r.p10).toLocaleString('en-US')}–${Math.round(r.p90).toLocaleString('en-US')}`;
export const pct = (x, d = 2) => `${(x * 100).toFixed(d)}%`;
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const debounce = (fn, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

// ---------- API ----------
export async function api(path, body) {
  const res = await fetch(`/api/${path}`, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let data = null;
  try { data = await res.json(); } catch { /* not JSON */ }
  if (!res.ok) throw new Error(data?.detail ? (typeof data.detail === 'string' ? data.detail : 'Please check the unit details.') : `The estimate service is unavailable (${res.status}). Try again in a moment.`);
  return data;
}
let metaP = null;
export const meta = () => (metaP ||= api('meta'));

// ---------- page chrome ----------
const PAGES = [['check', 'Check a unit'], ['compare', 'Compare'], ['investor', 'Investor'], ['developer', 'Developer'], ['badge', 'Badge'], ['business', 'Business'], ['methodology', 'Method']];
export function chrome(active) {
  document.body.classList.add('app');
  const top = document.createElement('header');
  top.className = 'top app-top';
  top.innerHTML = `<a class="brand" href="/" aria-label="CoolScore home"><svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="19" r="7"/><path d="M4 19h24"/><path d="M16 5v4M7.5 9.5l2.4 2.4M24.5 9.5l-2.4 2.4"/></svg><span>CoolScore<em>Dubai</em></span></a>
    <nav class="app-nav" aria-label="App">${PAGES.map(([k, t]) => `<a href="/${k}" class="${k === active ? 'on' : ''}"${k === active ? ' aria-current="page"' : ''}>${t}</a>`).join('')}</nav>`;
  document.body.prepend(top);
  meta().then((m) => {
    const f = document.createElement('footer');
    f.className = 'app-foot';
    f.innerHTML = `<p>${esc(m.disclaimer)} ${esc(m.simulated)} Weather data by <a href="https://open-meteo.com/" rel="noopener">Open-Meteo.com</a> (CC BY 4.0); observations NOAA NCEI. Fictional building names only; no real portal or developer is depicted.</p>`;
    $('.app-main')?.appendChild(f);
  }).catch(() => {});
}

// ---------- the unit form (same fields and defaults as the Streamlit form) ----------
const opt = (o, v) => Object.entries(o).map(([k, t]) => `<option value="${esc(k)}"${k === v ? ' selected' : ''}>${esc(t)}</option>`).join('');
export async function unitForm(root, defaults = {}, { optional = true, rent = true, compact = false } = {}) {
  const m = await meta(), L = m.labels;
  const d = { community: 'Business Bay', size_sqft: 800, floor: 12, facing: 'W', era_band: '2005_2014', bedrooms: 1, total_floors: 30,
    glass: 'medium', system: 'district_cooling', balcony: 'none', payer: 'tenant', obstruction: 'partial', ...defaults };
  root.innerHTML = `
    <div class="fields">
      <label class="field"><span>Community</span><select name="community">${m.communities.map((c) => `<option${c === d.community ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select></label>
      <label class="field"><span>Building completed</span><select name="era_band">${opt(L.era_band, d.era_band)}</select></label>
      <label class="field"><span>Size (sq ft)</span><input name="size_sqft" type="number" min="200" max="8000" step="25" value="${d.size_sqft}"></label>
      <label class="field"><span>Bedrooms</span><select name="bedrooms">${[0, 1, 2, 3, 4, 5].map((b) => `<option value="${b}"${+d.bedrooms === b ? ' selected' : ''}>${b ? b : 'Studio'}</option>`).join('')}</select></label>
      <label class="field"><span>Floor</span><input name="floor" type="number" min="1" max="150" value="${d.floor}"></label>
      <label class="field"><span>Total floors in building</span><input name="total_floors" type="number" min="1" max="150" value="${Math.max(d.total_floors, d.floor)}"></label>
      <label class="field"><span>Main windows face</span><select name="facing" title="Corner units have two facades, e.g. W+N">${m.facings.map((f) => `<option${f === d.facing ? ' selected' : ''}>${f}</option>`).join('')}</select></label>
      <label class="field"><span>Glass</span><select name="glass">${opt(L.glass, d.glass)}</select></label>
      <label class="field"><span>Cooling system</span><select name="system">${opt(L.system, d.system)}</select></label>
      <label class="field"><span>Who pays for cooling</span><select name="payer">${opt(L.payer, d.payer)}</select></label>
      <label class="field"><span>Balcony / shading</span><select name="balcony">${opt(L.balcony, d.balcony)}</select></label>
      <label class="field"><span>View</span><select name="obstruction" title="Neighbouring towers shade the facade and cut solar heat.">${opt(L.obstruction, d.obstruction)}</select></label>
      ${rent && !compact ? `<label class="field wide"><span>Annual rent (AED, optional)</span><input name="annual_rent_aed" type="number" min="0" max="2000000" step="1000" value="${d.annual_rent_aed || ''}" placeholder="e.g. 95000"></label>` : ''}
    </div>
    ${optional ? `<details class="more"${d.setpoint_c ? ' open' : ''}><summary>Optional: your household (narrows the range)</summary>
      <label class="toggle" style="margin-top:12px"><input type="checkbox" name="use_household"${d.setpoint_c ? ' checked' : ''}><i></i>Use these details</label>
      <div class="fields">
        <label class="field"><span>People living there</span><input name="household_size" type="number" min="1" max="10" value="${d.household_size || (+d.bedrooms + 1)}"></label>
        <label class="field"><span>Daytime</span><select name="occupancy">${opt(L.occupancy, d.occupancy || 'away_daytime')}</select></label>
        <label class="field wide"><span>Usual AC temperature · <b class="sp-out">${(+d.setpoint_c || 24).toFixed(1)} °C</b></span><input name="setpoint_c" type="range" min="20" max="28" step="0.5" value="${d.setpoint_c || 24}"></label>
      </div></details>` : ''}`;
  const q = (n) => root.querySelector(`[name="${n}"]`);
  const sp = q('setpoint_c');
  sp?.addEventListener('input', () => { root.querySelector('.sp-out').textContent = `${(+sp.value).toFixed(1)} °C`; });
  // household details only count when switched on; touching them switches them on
  ['household_size', 'occupancy', 'setpoint_c'].forEach((n) => q(n)?.addEventListener('input', () => { q('use_household').checked = true; }));
  return {
    root,
    get() {
      const v = (n) => q(n)?.value;
      const out = {
        community: v('community'), era_band: v('era_band'), size_sqft: +v('size_sqft'), bedrooms: +v('bedrooms'),
        floor: +v('floor'), total_floors: Math.max(+v('total_floors'), +v('floor')), facing: v('facing'), glass: v('glass'),
        balcony: v('balcony'), obstruction: v('obstruction'), system: v('system'), payer: v('payer'),
      };
      if (q('annual_rent_aed')) out.annual_rent_aed = +v('annual_rent_aed') || null;
      if (q('use_household')?.checked) Object.assign(out, { household_size: +v('household_size'), occupancy: v('occupancy'), setpoint_c: +v('setpoint_c') });
      return out;
    },
    onChange(fn) { root.addEventListener('input', fn); root.addEventListener('change', fn); },
  };
}

// ---------- the original Streamlit components, embedded as they are ----------
// They listen for {type: 'streamlit:render', args} and report their height; we speak that protocol.
export function embed(iframe) {
  let ready = false, pending = null;
  // the component may announce itself before this page's code runs: its load event is a safe fallback
  const onLoad = () => { ready = true; if (pending) send(pending); };
  iframe.addEventListener('load', onLoad);
  if (iframe.contentDocument?.readyState === 'complete' && iframe.contentWindow?.location.href !== 'about:blank') onLoad();
  addEventListener('message', (e) => {
    if (e.source !== iframe.contentWindow || !e.data?.isStreamlitMessage) return;
    if (e.data.type === 'streamlit:componentReady') { ready = true; if (pending) send(pending); }
    if (e.data.type === 'streamlit:setFrameHeight') iframe.style.height = `${e.data.height}px`;
  });
  const send = (args) => iframe.contentWindow.postMessage({ type: 'streamlit:render', args }, '*');
  return { render(args) { pending = args; if (ready) send(args); } };
}

// ---------- marks ----------
export const gradeBadge = (letter, color, size = 44) => `<span class="grade" style="background:${color};color:${color};width:${size}px;height:${size}px;font-size:${Math.round(size * .6)}px"><b style="color:#fff;font-weight:400">${letter}</b></span>`;

export function driversHTML(drivers) {
  if (!drivers?.length) return '<p class="note">This unit already matches the reference on every driver.</p>';
  const top = Math.max(...drivers.map((d) => Math.abs(d.aed_per_year)));
  return `<div class="drvs">${drivers.map((d, i) => {
    const v = d.aed_per_year, w = (50 * Math.abs(v)) / top;
    const bar = v > 0 ? `left:50%;width:${w.toFixed(1)}%;background:linear-gradient(90deg,#ff9d6b,#ff7a59)` : `left:${(50 - w).toFixed(1)}%;width:${w.toFixed(1)}%;background:linear-gradient(90deg,#2ec4b6,#7fe3d8)`;
    return `<div class="drv" style="animation-delay:${i * 60}ms"><span>${esc(d.driver)}</span><div class="drv-t"><i style="${bar}"></i></div><b class="${v > 0 ? 'up' : 'down'}">${v > 0 ? '+' : '−'}${aed(Math.abs(v))}</b></div>`;
  }).join('')}<div class="drv-key"><span>← saves vs the reference</span><span>adds per year →</span></div></div>`;
}

// month-by-month: typical bill per month, P10–P90 whiskers, bars coloured by the month's measured heat
export function monthlyChart(root, { ranges, colors, tmax, months, month, onPick }) {
  const W = Math.round(Math.max(330, Math.min(720, root.clientWidth || 640))), H = W < 480 ? 220 : 250, L = W < 480 ? 40 : 52, R = 6, T = 14, B = 30;
  const top = Math.max(...ranges.map((r) => r[2])) * 1.08 || 1;
  const step = (W - L - R) / 12, bw = step * 0.62;
  const y = (v) => T + (1 - v / top) * (H - T - B);
  const ticks = niceTicks(top, 4);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Typical cooling bill by month with P10 to P90 ranges">`;
  ticks.forEach((t) => { s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text class="axis" x="${L - 8}" y="${y(t) + 3}" text-anchor="end">${t.toLocaleString('en-US')}</text>`; });
  s += `<text class="axis" x="${L - 8}" y="${T - 4}" text-anchor="end">AED</text>`;
  ranges.forEach((r, i) => {
    const x = L + i * step + (step - bw) / 2, cx = x + bw / 2, h = Math.max(1, y(0) - y(r[1]));
    const on = i === month;
    s += `<g class="mbar" data-i="${i}" style="cursor:${onPick ? 'pointer' : 'default'}"><rect x="${L + i * step}" y="${T}" width="${step}" height="${H - T - B}" fill="transparent"/>`;
    s += `<rect x="${x}" y="${y(r[1])}" width="${bw}" height="${h}" rx="4" fill="${colors[i]}" opacity="${month == null || on ? 1 : 0.55}" class="${on ? 'sel' : ''}"/>`;
    s += `<line class="whisk" x1="${cx}" x2="${cx}" y1="${y(r[2])}" y2="${y(r[0])}"/><line class="whisk" x1="${cx - 4}" x2="${cx + 4}" y1="${y(r[2])}" y2="${y(r[2])}"/><line class="whisk" x1="${cx - 4}" x2="${cx + 4}" y1="${y(r[0])}" y2="${y(r[0])}"/>`;
    s += `<text class="axis" x="${cx}" y="${H - 10}" text-anchor="middle"${on ? ' style="fill:#fff"' : ''}>${months[i]}</text></g>`;
  });
  root.innerHTML = `${s}</svg><div class="ctip"></div>`;
  const tip = $('.ctip', root), svg = $('svg', root);
  $$('.mbar', root).forEach((g) => {
    const i = +g.dataset.i, r = ranges[i];
    g.addEventListener('pointerenter', () => {
      const b = svg.getBoundingClientRect(), x = ((L + (i + 0.5) * step) / W) * b.width;
      tip.innerHTML = `<b>${months[i]}</b> · typical ${aed(r[1])}<br>${aed(r[0])}–${Math.round(r[2]).toLocaleString('en-US')} · avg high ${tmax[i].toFixed(1)} °C`;
      tip.style.left = `${x}px`; tip.style.top = `${(y(r[2]) / H) * b.height}px`; tip.classList.add('on');
    });
    g.addEventListener('pointerleave', () => tip.classList.remove('on'));
    if (onPick) g.addEventListener('click', () => onPick(i));
  });
}

export function niceTicks(max, n = 4) {
  const raw = max / n, mag = 10 ** Math.floor(Math.log10(raw || 1)), stepv = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((k) => k >= raw) || raw;
  return Array.from({ length: Math.floor(max / stepv) + 1 }, (_, i) => +(i * stepv).toFixed(6));
}

export function setBusy(el, on) { el?.classList.toggle('loading', !!on); }
