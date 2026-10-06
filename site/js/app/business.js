// Business Case: pricing, unit economics and a 12-month P&L you can change (all defaults are labelled assumptions).
import { $, $$, api, chrome, niceTicks, aed, esc, debounce, setBusy } from './common.js';

chrome('business');
const SPEC = [
  ['Prices (AED)', 'pricing', [
    ['broker_seat_aed_month', 'Broker seat / month', 0, 2000, 10],
    ['portal_aed_per_scored_listing_month', 'Portal: per scored listing / month', 0, 20, 0.25],
    ['developer_report_aed', 'Developer design report', 0, 500000, 1000],
    ['consumer_report_aed', 'Consumer detailed report', 0, 500, 1],
    ['pilot_fee_aed', '90-day brokerage pilot fee', 0, 200000, 1000]]],
  ['Plan', 'plan', [
    ['brokerages_month_4', 'Paying brokerages in month 4', 0, 10, 1, 'range'],
    ['new_brokerages_per_month', 'New brokerages per month', 0, 5, 1, 'range'],
    ['seats_per_brokerage', 'Seats per brokerage', 1, 60, 1, 'range'],
    ['portal_start_month', 'Portal deal starts (month; 13 = none)', 4, 13, 1, 'range'],
    ['portal_scored_listings', 'Portal listings scored', 0, 500000, 1000],
    ['monthly_churn', 'Monthly seat churn', 0, 0.2, 0.01, 'range', (v) => `${Math.round(v * 100)}%`],
    ['developer_reports_per_quarter', 'Developer reports closed per quarter', 0, 4, 1, 'range']]],
  ['Costs (AED / month)', 'costs', [
    ['part_time_sales_aed', 'Part-time sales (from month 4)', 0, 100000, 500],
    ['marketing_aed', 'Marketing', 0, 100000, 500],
    ['founder_draw_aed', 'Founder salary', 0, 100000, 1000]]],
];
const STREAMS = [['broker_seats', 'Broker seats', '#6aa7ff'], ['portal_api', 'Portal API', '#ff7a59'], ['developer_reports', 'Developer reports', '#2ec4b6'],
  ['pilot', 'Pilot', '#f5b942'], ['consumer_reports', 'Consumer reports', '#e87ba4']];
$('#legend').innerHTML = STREAMS.map(([, t, c]) => `<span style="--c:${c}">${t}</span>`).join('') + '<span class="ln">Costs</span>';
let seq = 0, last = null;

function controls(inputs) {
  $('#ctl').innerHTML = SPEC.map(([title, sec, items]) => `<h3>${title}</h3><div class="fields" style="grid-template-columns:1fr">${items.map(([k, label, lo, hi, step, kind, fmt]) => {
    const v = inputs[sec][k];
    return kind === 'range'
      ? `<label class="field"><span>${esc(label)} · <b data-out="${k}">${fmt ? fmt(v) : v}</b></span><input data-sec="${sec}" name="${k}" type="range" min="${lo}" max="${hi}" step="${step}" value="${v}"></label>`
      : `<label class="field"><span>${esc(label)}</span><input data-sec="${sec}" name="${k}" type="number" min="${lo}" max="${hi}" step="${step}" value="${v}"></label>`;
  }).join('')}</div>`).join('');
  $('#ctl').addEventListener('input', (e) => {
    const el = e.target, out = $(`[data-out="${el.name}"]`);
    if (out) { const fmt = SPEC.flatMap((s) => s[2]).find((i) => i[0] === el.name)[6]; out.textContent = fmt ? fmt(+el.value) : el.value; }
    run();
  });
}

const overrides = () => {
  const o = { pricing: {}, plan: {}, costs: {} };
  $$('#ctl input').forEach((el) => { if (el.value !== '') o[el.dataset.sec][el.name] = +el.value; });
  return o;
};

const run = debounce(async (first) => {
  const my = ++seq;
  setBusy($('#kpis'), true);
  try {
    const r = await api('business', first ? {} : overrides());
    if (my !== seq) return;
    if (first) controls(r.inputs);
    last = r; render(r);
  } catch (err) {
    if (my === seq) $('#kpis').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`;
  }
  if (my === seq) setBusy($('#kpis'), false);
}, 200);

function render(r) {
  const m = r.months, sum = (k) => m.reduce((a, x) => a + x[k], 0), ue = r.unit_economics;
  const rev = sum('revenue'), prof = sum('profit');
  $('#kpis').innerHTML = `
    <div class="kpi"><b>${aed(rev)}</b><span>12-month revenue</span></div>
    <div class="kpi"><b class="${prof < 0 ? 'neg' : ''}">${prof < 0 ? '−' : ''}${aed(Math.abs(prof))}</b><span>12-month profit</span></div>
    <div class="kpi hl"><b>${r.break_even ? `Month ${r.break_even}` : 'Not in year 1'}</b><span>Break-even month</span><small>first month from which monthly profit stays positive</small></div>`;
  $('#ue-seat').innerHTML = `<div class="ue"><b>${Math.round(ue.broker_seat_margin * 100)}%</b><span>gross margin</span></div>
    <p class="prose">${aed(ue.broker_seat_price)} a month; cost to serve ≈ AED ${ue.broker_seat_cost.toFixed(2)}.</p>`;
  $('#ue-list').innerHTML = `<div class="ue"><b>${Math.round(ue.listing_margin * 100)}%</b><span>gross margin</span></div>
    <p class="prose">AED ${ue.listing_price.toFixed(2)} a month for the portal; AI parsing ≈ AED ${ue.llm_cost_per_listing_aed.toFixed(3)}.</p>`;
  chart(m);
  $('#tbl').innerHTML = `<thead><tr><th>Month</th><th>Revenue</th><th>Costs</th><th>Profit</th><th>Running total</th><th>Seats</th></tr></thead><tbody>${m.map((x) => `<tr>
    <td>${x.month}</td><td class="num">${aed(x.revenue)}</td><td class="num">${aed(x.costs)}</td><td class="num">${x.profit < 0 ? '−' : ''}${aed(Math.abs(x.profit))}</td>
    <td class="num">${x.cumulative < 0 ? '−' : ''}${aed(Math.abs(x.cumulative))}</td><td class="num">${Math.round(x.seats)}</td></tr>`).join('')}</tbody>`;
}

function chart(m) {
  const root = $('#pnl'), W = Math.round(Math.max(330, Math.min(900, root.clientWidth || 760))), H = W < 520 ? 240 : 300;
  const L = W < 520 ? 44 : 56, R = 8, T = 12, B = 26;
  const ticks = niceTicks(Math.max(...m.map((x) => Math.max(x.revenue, x.costs))) || 1, 4);
  const top = Math.max(ticks.at(-1), ...m.map((x) => Math.max(x.revenue, x.costs)));
  const y = (v) => T + (1 - v / top) * (H - T - B), step = (W - L - R) / m.length, bw = step * 0.6;
  const k = (v) => (v >= 1000 ? `${+(v / 1000).toFixed(1)}k` : v);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Monthly revenue by stream against monthly costs">`;
  ticks.forEach((t) => { s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text class="axis" x="${L - 8}" y="${y(t) + 3}" text-anchor="end">${k(t)}</text>`; });
  m.forEach((x, i) => {
    const bx = L + i * step + (step - bw) / 2;
    let at = 0;
    s += `<g class="mbar" data-i="${i}"><rect x="${L + i * step}" y="${T}" width="${step}" height="${H - T - B}" fill="transparent"/>`;
    STREAMS.forEach(([key, , c], j) => {
      const v = x[key];
      if (v > 0) s += `<rect class="pb" x="${bx}" y="${y(at + v)}" width="${bw}" height="${Math.max(0.5, y(at) - y(at + v))}" fill="${c}" style="animation-delay:${i * 35 + j * 20}ms"/>`;
      at += v;
    });
    s += `<text class="axis" x="${bx + bw / 2}" y="${H - 8}" text-anchor="middle">${x.month}</text></g>`;
  });
  const pts = m.map((x, i) => `${L + (i + 0.5) * step},${y(x.costs)}`).join(' ');
  s += `<polyline class="cost-ln" points="${pts}"/>${m.map((x, i) => `<circle class="cost-pt" cx="${L + (i + 0.5) * step}" cy="${y(x.costs)}" r="3.5"/>`).join('')}`;
  root.innerHTML = `${s}</svg><div class="ctip"></div>`;
  const tip = $('.ctip', root), svg = $('svg', root);
  $$('.mbar', root).forEach((g) => {
    const i = +g.dataset.i, x = m[i];
    g.addEventListener('pointerenter', () => {
      const b = svg.getBoundingClientRect();
      tip.innerHTML = `<b>Month ${x.month}</b><br>${STREAMS.filter(([key]) => x[key] > 0).map(([key, t, c]) => `<span style="color:${c}">■</span> ${t} ${aed(x[key])}`).join('<br>')}<br>Revenue <b>${aed(x.revenue)}</b> · costs ${aed(x.costs)}`;
      tip.style.left = `${((L + (i + 0.5) * step) / W) * b.width}px`; tip.style.top = `${(y(Math.max(x.revenue, x.costs)) / H) * b.height}px`;
      tip.classList.add('on');
    });
    g.addEventListener('pointerleave', () => tip.classList.remove('on'));
  });
}

let lastW = innerWidth;
addEventListener('resize', debounce(() => { if (innerWidth !== lastW && last) { lastW = innerWidth; chart(last.months); } }, 200));
run(true);
