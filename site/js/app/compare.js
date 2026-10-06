// Compare Units: 2–4 homes side by side by true monthly cost (rent + typical cooling + housing fee).
import { $, $$, api, meta, chrome, unitForm, gradeBadge, niceTicks, aed, aedR, esc, debounce, setBusy } from './common.js';

chrome('compare');
const M = await meta();
const PRESETS = [
  { community: 'Business Bay', facing: 'W', floor: 8, total_floors: 30, glass: 'floor_to_ceiling', payer: 'tenant', annual_rent_aed: 92000 },
  { community: 'Business Bay', facing: 'N', floor: 20, total_floors: 30, glass: 'medium', payer: 'landlord_chiller_free', annual_rent_aed: 96000 },
  { community: 'Jumeirah Village Circle (JVC)', facing: 'E', floor: 5, total_floors: 12, era_band: '2015_2021', annual_rent_aed: 78000 },
  { community: 'Dubai Marina', facing: 'S+W', floor: 31, total_floors: 31, annual_rent_aed: 110000 },
];
const COLORS = { rent: '#5d6b8a', cooling: '#ff7a59', housing_fee: '#b9a77f' };
let n = 2, tab = 0, seq = 0, last = null;

// four forms built once; the unit count only shows or hides them
const forms = [];
for (let i = 0; i < 4; i++) {
  const box = document.createElement('div');
  box.className = 'cmp-form'; box.id = `form-${i}`; box.setAttribute('role', 'tabpanel'); box.hidden = i !== 0;
  $('#forms').appendChild(box);
  const f = await unitForm(box, PRESETS[i], { optional: false });
  f.onChange(() => { renderTabs(); run(); });
  forms.push(f);
}

const short = (l) => `${l.community.replace(/ \(.+\)/, '')} · ${l.facing} · fl ${l.floor}`;
function renderTabs() {
  $('#tabs').innerHTML = forms.slice(0, n).map((f, i) => `<button role="tab" aria-selected="${i === tab}" class="${i === tab ? 'on' : ''}" data-i="${i}">
    <b>Unit ${i + 1}</b><small>${esc(short(f.get()))}</small></button>`).join('');
  $$('#tabs button').forEach((b) => b.addEventListener('click', () => { tab = +b.dataset.i; show(); }));
}
function show() {
  forms.forEach((f, i) => { f.root.hidden = i !== tab; });
  renderTabs();
}
$$('.seg button').forEach((b) => b.addEventListener('click', () => {
  n = +b.dataset.n; tab = Math.min(tab, n - 1);
  $$('.seg button').forEach((x) => x.setAttribute('aria-checked', x === b));
  show(); run();
}));

// ---------- the comparison ----------
const run = debounce(async () => {
  const units = forms.slice(0, n).map((f) => f.get()), my = ++seq;
  setBusy($('#cards'), true);
  try {
    const r = await api('compare', { units });
    if (my !== seq) return;
    last = { r, units };
    render(r, units);
  } catch (err) {
    if (my !== seq) return;
    $('#verdict').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`;
  }
  setBusy($('#cards'), false);
}, 350);

function render(r, units) {
  const rows = r.rows, v = r.verdict;
  if (!v) $('#verdict').innerHTML = '<p class="flag">Add the annual rent for every unit to compare true monthly costs.</p>';
  else if (v.cheapest_rent !== v.cheapest_true) {
    $('#verdict').innerHTML = `<div class="verdict"><span class="v-k">The cheapest rent is not the cheapest home</span>
      <p><b>Unit ${v.cheapest_rent + 1}</b> has the lowest rent, but <b>Unit ${v.cheapest_true + 1}</b> costs about
      <b class="gold">${aed(v.gap)} less per month</b> once cooling and the housing fee are added (typical estimates).</p></div>`;
  } else {
    $('#verdict').innerHTML = `<div class="verdict ok"><span class="v-k">Clear winner</span>
      <p><b>Unit ${v.cheapest_rent + 1}</b> has both the cheapest rent and the lowest true monthly cost.</p></div>`;
  }
  $('#cards').style.setProperty('--n', rows.length);
  $('#cards').innerHTML = rows.map((u, i) => {
    const l = units[i], tags = [];
    if (v && i === v.cheapest_true) tags.push('<span class="tag gold">Lowest true cost</span>');
    if (v && i === v.cheapest_rent && v.cheapest_rent !== v.cheapest_true) tags.push('<span class="tag">Cheapest rent</span>');
    const part = (k, t) => `<li><i style="background:${COLORS[k]}"></i>${t}<b>${aed(u[k])}</b></li>`;
    return `<article class="card cmp-card${v && i === v.cheapest_true ? ' best' : ''}" style="animation-delay:${i * 70}ms">
      <header>${gradeBadge(u.score, u.score_color, 46)}<div><h3>Unit ${i + 1}</h3><p>${esc(short(l))}</p></div></header>
      <div class="tags">${tags.join('')}</div>
      <div class="cmp-total"><b>${l.annual_rent_aed ? aed(u.total) : aed(u.cooling)}</b><span>${l.annual_rent_aed ? 'True cost / month' : 'Cooling / month · add rent for the true cost'}</span></div>
      <ul class="cmp-parts">${part('rent', 'Rent')}${part('cooling', 'Cooling, typical')}${part('housing_fee', 'Housing fee')}</ul>
      <p class="note">Cooling ${aedR(u.annual)} a year · CoolScore ${u.score} (${esc(M.score_words[u.score])}) · simulated</p>
    </article>`;
  }).join('');
  stack(rows, units);
  $('#formulas').innerHTML = rows.map((u, i) => `<p class="note">Unit ${i + 1}: ${esc(u.formula)}</p>`).join('');
}

// stacked horizontal bars, one per unit; the total sits at the end of each bar
function stack(rows, units) {
  const root = $('#stack'), W = Math.round(Math.max(330, Math.min(1200, root.clientWidth || 900)));
  const L = W < 480 ? 58 : 76, R = W < 480 ? 70 : 96, rowH = 46, bh = 24, T = 6, H = T + rows.length * rowH + 22;
  const ticks = niceTicks(Math.max(...rows.map((u) => u.rent + u.cooling + u.housing_fee)) || 1, W < 480 ? 3 : 5);
  const top = Math.max(ticks.at(-1), ...rows.map((u) => u.rent + u.cooling + u.housing_fee));
  const x = (val) => L + (val / top) * (W - L - R);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Monthly cost per unit: rent, cooling and housing fee">`;
  ticks.forEach((t) => { s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${T}" y2="${H - 20}"/><text class="axis" x="${x(t)}" y="${H - 5}" text-anchor="middle">${t >= 1000 ? `${+(t / 1000).toFixed(1)}k` : t}</text>`; });
  rows.forEach((u, i) => {
    const y = T + i * rowH + (rowH - bh) / 2;
    let at = 0;
    s += `<text class="axis lab" x="${L - 10}" y="${y + bh / 2 + 4}" text-anchor="end">Unit ${i + 1}</text>`;
    ['rent', 'cooling', 'housing_fee'].forEach((k) => {
      const w = x(at + u[k]) - x(at);
      if (w > 0.5) s += `<rect class="seg-r" x="${x(at)}" y="${y}" width="${w}" height="${bh}" fill="${COLORS[k]}" style="animation-delay:${i * 90}ms"><title>Unit ${i + 1} · ${k.replace('_', ' ')}: ${aed(u[k])}</title></rect>`;
      if (k === 'cooling' && w > 64) s += `<text class="in" x="${x(at) + w / 2}" y="${y + bh / 2 + 4}" text-anchor="middle">${aed(u[k]).replace('AED ', '')}</text>`;
      at += u[k];
    });
    s += `<text class="tot" x="${x(at) + 8}" y="${y + bh / 2 + 4}">${units[i].annual_rent_aed ? aed(at) : aed(u.cooling)}</text>`;
  });
  root.innerHTML = `${s}</svg>`;
}

let lastW = innerWidth;   // re-draw only when the width changes (phones fire resize while scrolling)
addEventListener('resize', debounce(() => { if (innerWidth !== lastW && last) { lastW = innerWidth; stack(last.r.rows, last.units); } }, 200));
renderTabs();
run();
