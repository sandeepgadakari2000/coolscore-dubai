// Listing Badge: how a CoolScore badge could look on a generic, unbranded listing card.
import { $, api, chrome, unitForm, gradeBadge, esc, debounce, setBusy } from './common.js';

chrome('badge');
const form = await unitForm($('#unit'), { community: 'Dubai Marina', facing: 'W', floor: 18, total_floors: 42, glass: 'floor_to_ceiling',
  bedrooms: 1, size_sqft: 780, annual_rent_aed: 105000 }, { optional: false });
const n0 = (v) => Math.round(v).toLocaleString('en-US');
let seq = 0;

const run = debounce(async () => {
  const l = form.get(), my = ++seq;
  setBusy($('#listing'), true);
  try {
    const r = await api('badge', { listing: l });
    if (my !== seq) return;
    render(r, l);
  } catch (err) {
    if (my === seq) $('#ls-body').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`;
  }
  if (my === seq) setBusy($('#listing'), false);
}, 300);

function render(r, l) {
  const beds = l.bedrooms ? `${l.bedrooms} bed` : 'Studio', s = r.summer;
  const tip = `Simulated estimate from building physics and published tariffs, not a quote. Summer month: AED ${n0(s.p10)}–${n0(s.p90)}; year: AED ${n0(r.annual.p10)}–${n0(r.annual.p90)}. CoolScore compares cooling cost per sq ft under standard conditions (A best, E worst).`;
  $('#ls-body').innerHTML = `
    <div class="ls-price">${l.annual_rent_aed ? `AED ${n0(l.annual_rent_aed)} <span>/ year</span>` : '<span>Price on request</span>'}</div>
    <div class="ls-facts">${beds} · ${n0(l.size_sqft)} sq ft · Floor ${l.floor}</div>
    <div class="ls-addr">Seabreeze Residences (fictional), ${esc(l.community)}</div>
    <details class="cs-badge" style="--g:${r.score_color}">
      <summary>${gradeBadge(r.score, r.score_color, 40)}
        <div><b>CoolScore ${r.score}</b> · Est. cooling AED ${n0(s.p10)}–${n0(s.p90)}/month
        <small>summer · simulated estimate · tap for details</small></div></summary>
      <p>${esc(tip)}</p>
    </details>`;
  $('#row').innerHTML = `<div class="ls-row">
      <img src="/media/evening.jpg" alt="" width="84" height="56">
      <div class="ls-row-t"><b>${l.annual_rent_aed ? `AED ${n0(l.annual_rent_aed)}/yr` : 'Price on request'}</b><span>${beds} · ${n0(l.size_sqft)} sq ft · ${esc(l.community)}</span></div>
      <span class="cs-chip" style="--g:${r.score_color}" title="${esc(tip)}"><i>${r.score}</i>AED ${n0(s.p10)}–${n0(s.p90)}/mo · sim.</span>
    </div>`;
  $('#how').innerHTML = `<p>The badge shows the summer-month P10–P90 range (AED ${n0(s.p10)}–${n0(s.p90)}) for the unit: ${n0(l.size_sqft)} sq ft,
    floor ${l.floor} of ${l.total_floors}, ${l.facing}-facing. ${esc(r.formula)}</p>
    <p>CoolScore ${r.score} = ${r.intensity.toFixed(2)} AED per sq ft per year under a standard household and tariff; cut-offs
    ${r.cuts.map((c, i) => `${'ABCD'[i]} ≤ ${c.toFixed(2)}`).join(', ')}, E above.</p>`;
}

form.onChange(run);
run();
