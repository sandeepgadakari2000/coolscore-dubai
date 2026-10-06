// Developer View: the fictional tower's facade graded unit by unit, and the AED impact of the design levers.
import { $, $$, api, meta, chrome, aed, esc, debounce, setBusy } from './common.js';

chrome('developer');
const M = await meta();
const T = $('#tower'), Lv = $('#levers');
const sel = (n) => $(`[name="${n}"]`, T);
sel('community').innerHTML = M.communities.map((c) => `<option${c === 'Business Bay' ? ' selected' : ''}>${esc(c)}</option>`).join('');
sel('era_band').innerHTML = Object.entries(M.labels.era_band).map(([k, t]) => `<option value="${k}"${k === '2022_plus' ? ' selected' : ''}>${esc(t)}</option>`).join('');
sel('obstruction').innerHTML = Object.entries(M.labels.obstruction).map(([k, t]) => `<option value="${k}"${k === 'partial' ? ' selected' : ''}>${esc(t)}</option>`).join('');
$('#key').innerHTML = 'ABCDE'.split('').map((g) => `<span style="--c:${M.score_colors[g]}">${g}</span>`).join('');

const lever = (n) => +$(`[name="${n}"]`, Lv).value;
const labels = () => {
  $('#floors-out').textContent = sel('floors').value;
  $('#wwr-out').textContent = `${Math.round(lever('wwr') * 100)}%`;
  $('#shgc-out').textContent = lever('shgc').toFixed(2);
  $('#depth-out').textContent = `${lever('depth').toFixed(2)} m`;
};
let seq = 0, prev = {};

const run = debounce(async () => {
  const body = { community: sel('community').value, era_band: sel('era_band').value, floors: +sel('floors').value,
    obstruction: sel('obstruction').value, wwr: lever('wwr'), shgc: lever('shgc'), depth: lever('depth') };
  const my = ++seq;
  setBusy($('#tower-card'), true);
  try {
    const r = await api('developer', body);
    if (my !== seq) return;
    render(r);
  } catch (err) {
    if (my === seq) $('#impact').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`;
  }
  if (my === seq) setBusy($('#tower-card'), false);
}, 380);

function render(r) {
  const g = $('#grid'), cols = r.facings.length;
  g.style.setProperty('--cols', cols);
  const same = g.dataset.floors === String(r.floors.length);
  if (!same) {
    // build the cells once per tower height; later runs only re-colour them, so a re-grade reads as a wave
    g.innerHTML = `<span class="tw-corner"></span>${r.facings.map((f) => `<span class="tw-col">${f}</span>`).join('')}`
      + r.floors.map((fl) => `<span class="tw-fl">${fl}</span>${r.facings.map((f) => `<button class="tw-c" data-fl="${fl}" data-f="${f}" role="gridcell"><b></b></button>`).join('')}`).join('');
    g.dataset.floors = r.floors.length;
    prev = {};
  }
  const maxFl = r.floors[0];
  $$('.tw-c', g).forEach((c) => {
    const fl = +c.dataset.fl, f = c.dataset.f, u = r.grid[fl][f], key = `${fl}${f}`;
    const changed = prev[key] && prev[key] !== u.score;
    c.style.setProperty('--c', r.colors[u.score]);
    c.style.transitionDelay = `${((maxFl - fl) * 14 + r.facings.indexOf(f) * 9)}ms`;
    c.firstChild.textContent = u.score;
    c.dataset.tip = `Floor ${fl}, ${f}-facing: CoolScore ${u.score} · ${aed(u.aed)} a year (${u.intensity.toFixed(2)} AED / sq ft)`;
    c.setAttribute('aria-label', c.dataset.tip);
    if (changed) { c.classList.remove('pop'); void c.offsetWidth; c.classList.add('pop'); }
    prev[key] = u.score;
  });
  const im = r.impact, d = Math.round(im.per_unit_mean_aed), t = Math.round(im.tower_aed);
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');
  const sign = (v) => (v > 0 ? '+' : v < 0 ? '−' : '±');
  $('#impact').innerHTML = `<h2>Against the base design</h2><p class="sub">60% glass, SHGC 0.25, no balconies · tenant cooling bills per year.</p>
    <div class="kpis">
      <div class="kpi"><b class="${cls(d)}">${sign(d)}${aed(Math.abs(d))}</b><span>Per unit / year</span></div>
      <div class="kpi"><b class="${cls(t)}">${sign(t)}${aed(Math.abs(t))}</b><span>Whole tower / year</span></div>
      <div class="kpi"><b>${im.units_improving_grade}</b><span>Units with a better grade</span><small>cooling energy ${im.kwh_th_change_pct >= 0 ? '+' : '−'}${Math.abs(im.kwh_th_change_pct).toFixed(1)}%</small></div>
    </div>`;
}

$('#grid').addEventListener('pointerover', (e) => { const c = e.target.closest('.tw-c'); if (c) $('#cell-info').textContent = c.dataset.tip; });
$('#grid').addEventListener('focusin', (e) => { const c = e.target.closest('.tw-c'); if (c) $('#cell-info').textContent = c.dataset.tip; });
[T, Lv].forEach((el) => el.addEventListener('input', () => { labels(); run(); }));
$('#reset').addEventListener('click', () => {
  Object.entries({ wwr: 0.6, shgc: 0.25, depth: 0 }).forEach(([n, v]) => { $(`[name="${n}"]`, Lv).value = v; });
  labels(); run();
});
labels();
run();
