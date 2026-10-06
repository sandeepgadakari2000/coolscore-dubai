// Investor View: net yield after cooling and service charges; pricing a chiller-free offer.
import { $, api, meta, chrome, unitForm, niceTicks, aed, aedR, pct, esc, debounce, setBusy } from './common.js';

chrome('investor');
await meta();
const form = await unitForm($('#unit'), { payer: 'landlord_chiller_free' }, { optional: false, compact: true });
const money = () => {
  const v = (n) => +$(`#money [name="${n}"]`).value || 0;
  return { price: v('price'), rent: v('rent'), service_charge: v('sc'), other: v('other') };
};
let seq = 0, last = null;

const run = debounce(async () => {
  const listing = form.get(), m = money(), my = ++seq;
  if (m.price < 100000) { $('#yields').innerHTML = '<p class="flag bad">Enter a purchase price of at least AED 100,000.</p>'; return; }
  setBusy($('#yields'), true);
  try {
    const r = await api('investor', { listing, ...m });
    if (my !== seq) return;
    last = { r, listing, m };
    render(r, listing, m);
  } catch (err) {
    if (my !== seq) return;
    $('#yields').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`;
  }
  setBusy($('#yields'), false);
}, 300);

const pts = (x) => `${x >= 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(2)} pts`;
function render(r, listing, m) {
  const lc = r.landlord_cooling, free = !r.dewa;
  $('#yields').innerHTML = `
    ${m.service_charge === 0 ? '<p class="flag" style="margin:0 0 14px">Service charge is 0 — enter the building\'s figure for a real net yield.</p>' : ''}
    <div class="kpis yields">
      <div class="kpi"><b>${pct(r.gross)}</b><span>Gross yield</span><small>rent / price</small></div>
      <div class="kpi"><b>${pct(r.net_tenant)}</b><span>Net · tenant pays cooling</span><small>${pts(r.net_tenant - r.gross)} vs gross</small></div>
      ${free ? `<div class="kpi hl"><b>${pct(r.net_free_p50)}</b><span>Net · chiller-free</span><small class="up">${pts(r.net_free_p50 - r.net_tenant)} · worst case ${pct(r.net_free_p90)}</small></div>`
    : '<div class="kpi"><b>—</b><span>Net · chiller-free</span><small>not possible with DEWA-billed AC</small></div>'}
    </div>
    ${r.service_charge_payer && free ? `<p class="flag mt">Cooling here is recovered through service charges, so it is an owner cost like chiller-free: about <b>${aed(lc.p50)} a year</b> (simulated). Enter the service charge <i>excluding</i> cooling, or this is counted twice.</p>` : ''}`;
  waterfall(r, m, free);
  $('#offer').innerHTML = free ? `<h2>Pricing a chiller-free offer</h2>
      <p class="sub">What you take on if the landlord pays the chiller bill.</p>
      <div class="offer-band">
        <div class="ob-track"><i style="left:0;right:0"></i><em style="left:${(100 * (lc.p50 - lc.p10) / Math.max(1, lc.p90 - lc.p10)).toFixed(1)}%"></em></div>
        <div class="ob-keys"><span>P10 ${aed(lc.p10)}</span><span><b>typical ${aed(lc.p50)}</b></span><span>P90 ${aed(lc.p90)}</span></div>
      </div>
      <p class="prose">To break even, the chiller-free rent must be at least <b>${aed(lc.p50)} a year higher</b>
        (${(100 * lc.p50 / Math.max(m.rent, 1)).toFixed(1)}% of the current rent); <b>${aed(lc.p90)}</b> covers a hot-unit / heavy-use tenant.</p>
      <p class="note">For comparison, a tenant paying cooling themselves would face about ${aedR(r.tenant_cooling)} a year (incl. fan electricity).</p>`
    : `<h2>Pricing a chiller-free offer</h2><p class="flag">This unit's AC runs on the tenant's DEWA meter, so a chiller-free offer doesn't apply.</p>`;
  $('#how').innerHTML = `<p>Gross yield = rent ÷ price. Net yield = (rent − service charge − other costs − landlord cooling) ÷ price.
    Service charge = ${m.service_charge} AED/sq ft × ${listing.size_sqft.toLocaleString('en-US')} sq ft = ${aed(r.service)}.
    Landlord cooling = simulated cooling bill when the tenant pays it, minus the fan electricity the tenant still pays when
    chiller-free (difference of P10/P50/P90 estimates, approximate). Vacancy, financing, fees and taxes are not included.</p>
    <p class="note">${esc(r.formula)}</p>`;
}

// gross → minus each cost → net; the cooling step carries its P10–P90 whisker
function waterfall(r, m, free) {
  const root = $('#fall'), W = Math.round(Math.max(330, Math.min(760, root.clientWidth || 640)));
  const H = 270, L = 44, R = 8, T = 26, B = 42;
  const sc = r.service / m.price, ot = m.other / m.price, lc = r.landlord_cooling;
  const steps = [
    { k: 'Gross', lab: ['Gross'], a: 0, b: r.gross, c: '#5d6b8a', tot: true },
    { k: 'Service charge', lab: ['Service', 'charge'], sm: ['Service'], a: r.gross - sc, b: r.gross, c: '#7d8396', d: -sc },
    { k: 'Other costs', lab: ['Other', 'costs'], sm: ['Other'], a: r.net_tenant, b: r.gross - sc, c: '#7d8396', d: -ot },
    { k: 'Net · tenant pays', lab: ['Net', 'tenant pays'], sm: ['Net', 'tenant'], a: 0, b: r.net_tenant, c: '#5d6b8a', tot: true },
  ];
  if (free) steps.push(
    { k: 'Landlord cooling', lab: ['Landlord', 'cooling'], sm: ['Cooling'], a: r.net_free_p50, b: r.net_tenant, c: '#ff7a59', d: -lc.p50 / m.price, lo: r.net_tenant - lc.p10 / m.price, hi: r.net_free_p90 },
    { k: 'Net · chiller-free', lab: ['Net', 'chiller-free'], sm: ['Net', 'free'], a: 0, b: r.net_free_p50, c: '#f5b942', tot: true });
  const lo = Math.min(0, ...steps.map((s) => Math.min(s.a, s.b, s.hi ?? 0)));
  const ticks = niceTicks(Math.max(r.gross, 1e-4) * 100, 4).map((t) => t / 100);
  const top = Math.max(ticks.at(-1), r.gross) * 1.04;
  const y = (v) => T + (top - v) / (top - lo) * (H - T - B);
  const step = (W - L - R) / steps.length, bw = Math.min(64, step * 0.56);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Yield from gross to net">`;
  ticks.forEach((t) => { s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text class="axis" x="${L - 8}" y="${y(t) + 3}" text-anchor="end">${(t * 100).toFixed(t * 100 % 1 ? 1 : 0)}%</text>`; });
  steps.forEach((st, i) => {
    const x = L + i * step + (step - bw) / 2, cx = x + bw / 2;
    const y1 = y(Math.max(st.a, st.b)), h = Math.max(2, Math.abs(y(st.a) - y(st.b)));
    s += `<rect class="wf" x="${x}" y="${y1}" width="${bw}" height="${h}" rx="4" fill="${st.c}" style="animation-delay:${i * 80}ms"><title>${st.k}: ${st.tot ? pct(st.b) : pts(st.d)}</title></rect>`;
    if (i < steps.length - 1) { const nx = L + (i + 1) * step + (step - bw) / 2, ly = y(st.tot ? st.b : st.a); s += `<line class="wf-link" x1="${x + bw}" x2="${nx}" y1="${ly}" y2="${ly}"/>`; }
    if (st.lo != null) s += `<line class="whisk" x1="${cx}" x2="${cx}" y1="${y(st.lo)}" y2="${y(st.hi)}"/><line class="whisk" x1="${cx - 4}" x2="${cx + 4}" y1="${y(st.hi)}" y2="${y(st.hi)}"/><line class="whisk" x1="${cx - 4}" x2="${cx + 4}" y1="${y(st.lo)}" y2="${y(st.lo)}"/>`;
    s += `<text class="wf-v${st.c === '#f5b942' ? ' gold' : ''}" x="${cx}" y="${y1 - 7}" text-anchor="middle">${st.tot ? pct(st.b) : (st.d ? `−${Math.abs(st.d * 100).toFixed(2)}` : '0')}</text>`;
    (W < 520 && st.sm ? st.sm : st.lab).forEach((w, j) => { s += `<text class="axis" x="${cx}" y="${H - B + 16 + j * 13}" text-anchor="middle">${esc(w)}</text>`; });
  });
  root.innerHTML = `${s}</svg>`;
}

form.onChange(run);
$('#money').addEventListener('input', run);
let lastW = innerWidth;
addEventListener('resize', debounce(() => { if (innerWidth !== lastW && last) { lastW = innerWidth; waterfall(last.r, last.m, !last.r.dewa); } }, 200));
run();
