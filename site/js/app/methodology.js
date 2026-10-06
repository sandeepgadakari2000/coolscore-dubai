// Methodology & validation: accuracy, real-bill status, the assumptions register (filterable) and the limits.
import { $, $$, api, chrome, esc, debounce } from './common.js';

chrome('methodology');
const d = await api('methodology');
const m = d.metrics, v = d.validation, n0 = (x) => Math.round(x).toLocaleString('en-US');

// ---------- accuracy ----------
const rows = [];
for (const [variant, label] of [['listing', 'Listing facts only'], ['detailed', 'With household details']]) {
  for (const [target, tl] of [['annual', 'Annual cost'], ['summer', 'August'], ['winter', 'January']]) {
    const x = m.variants[variant][target];
    rows.push(`<tr><td>${label}</td><td>${tl}</td><td class="num">${x.r2.toFixed(3)}</td><td class="num">AED ${n0(x.mae_aed)}</td>
      <td class="num">${x.mape_pct_bills_over_500.toFixed(1)}%</td><td class="num"><span class="cov" style="--p:${(x.p10_p90_coverage * 100).toFixed(0)}%"></span>${Math.round(x.p10_p90_coverage * 100)}%</td></tr>`);
  }
}
$('#acc').innerHTML = `<thead><tr><th>Inputs</th><th>Target</th><th>R²</th><th>MAE</th><th>MAPE (bills &gt; AED 500)</th><th>P10–P90 coverage</th></tr></thead><tbody>${rows.join('')}</tbody>`;
const fid = m.fidelity;
$('#fidelity').innerHTML = `
  <div class="card fid"><div class="ue"><b>${fid.annual_tenant_aed.r2.toFixed(3)}</b><span>R² · annual cost</span></div>
    <div class="ue"><b>${fid.annual_kwh_th.r2.toFixed(3)}</b><span>R² · cooling energy</span></div>
    <p class="prose"><b>Fidelity</b> (model given every simulation input, i.e. how well ML reproduces the physics), target ≥ ${fid.target_r2}.
      Listing-only accuracy is lower by design: a listing can't tell you the glass spec or how the household uses the AC, so that uncertainty is shown as the range.</p></div>
  <div class="card"><div class="counts">
    <div><b>${n0(m.n_train)}</b><span>scenarios trained on</span></div>
    <div><b>${n0(m.n_calibration)}</b><span>calibrated on</span></div>
    <div><b>${n0(m.n_test)}</b><span>tested on</span></div>
    <div><b>${m.artifact_mb} MB</b><span>model file</span></div></div>
    <p class="note">The web app runs a lightweight NumPy copy of the same trees: identical predictions, no scikit-learn on the server.</p></div>`;

// ---------- real bills ----------
const band = v.sanity_band || [];
const hi = Math.max(...band.map((r) => Math.max(r.band_high, r.simulated_median_month_aed))) * 1.08 || 1;
const at = (x) => `${((100 * x) / hi).toFixed(2)}%`;
$('#bill-status').innerHTML = `${v.n_units === 0
  ? `<div class="verdict"><span class="v-k">Not yet validated</span><p><b>No real bills yet — real-world accuracy is not yet validated.</b>
      The validation report runs automatically as soon as anonymised bills are added (see data/real_bills/README.md).</p></div>`
  : `<div class="verdict ok"><span class="v-k">Validated</span><p>${v.n_units} units, ${v.n_bill_months} bill months compared.</p>
      <ul class="prose">${[['total_bill', 'Total cooling bill'], ['consumption_rth', 'Consumption (RTh)'], ['capacity_charge', 'Capacity charge']].filter(([k]) => v[k]).map(([k, t]) => {
        const x = v[k]; return `<li><b>${t}:</b> MAPE ${Math.round(x.mape_pct)}%, ${Math.round(x.within_20pct * 100)}% of months within ±20%, median bias ${x.bias_pct >= 0 ? '+' : ''}${Math.round(x.bias_pct)}% (${x.n_months} months)</li>`;
      }).join('')}</ul></div>`}
  ${band.length ? `<div class="card mt"><h2>Sanity check against a published rough band</h2>
    <p class="sub">An independent guide; rough and unverified. The band is the published range per month; the dot is our simulated median.</p>
    <div class="bands">${band.map((r) => `<div class="band-row">
      <span class="br-l">${r.bedrooms ? `${r.bedrooms} bed` : 'Studio'}</span>
      <div class="br-t"><i style="left:${at(r.band_low)};width:calc(${at(r.band_high)} - ${at(r.band_low)})"></i>
        <em class="${r.inside_band ? 'in' : 'out'}" style="left:${at(r.simulated_median_month_aed)}" title="Simulated median AED ${n0(r.simulated_median_month_aed)}"></em></div>
      <span class="br-v"><b>AED ${n0(r.simulated_median_month_aed)}</b> vs ${n0(r.band_low)}–${n0(r.band_high)} · <span class="${r.inside_band ? 'ok' : 'off'}">${r.inside_band ? 'inside' : 'outside'}</span></span>
    </div>`).join('')}</div></div>` : ''}`;

// ---------- the assumptions register ----------
const kinds = [...new Set(d.register.map((r) => r.kind))].sort();
const on = new Set(kinds);
$('#kinds').innerHTML = kinds.map((k) => `<button class="on" aria-pressed="true" data-k="${esc(k)}">${esc(k)} <small>${d.register.filter((r) => r.kind === k).length}</small></button>`).join('');
$$('#kinds button').forEach((b) => b.addEventListener('click', () => {
  const k = b.dataset.k; on.has(k) ? on.delete(k) : on.add(k);
  b.classList.toggle('on', on.has(k)); b.setAttribute('aria-pressed', on.has(k)); table();
}));
const src = (s) => (/^https?:\/\//.test(s) ? `<a href="${esc(s)}" rel="noopener" target="_blank">${esc(s.replace(/^https?:\/\/(www\.)?/, '').slice(0, 48))}${s.length > 56 ? '…' : ''}</a>` : esc(s));
function table() {
  const q = $('#q').value.trim().toLowerCase();
  const list = d.register.filter((r) => on.has(r.kind) && (!q || `${r.path} ${r.unit} ${r.source} ${r.value}`.toLowerCase().includes(q)));
  $('#reg-count').textContent = `${list.length} of ${d.register.length} assumptions`;
  $('#reg').innerHTML = `<thead><tr><th>Assumption</th><th>Value</th><th>Unit</th><th>Type</th><th>Verify</th><th>Source</th></tr></thead><tbody>${list.map((r) => `<tr>
    <td><code>${esc(r.path)}</code></td><td class="val">${esc(r.value)}</td><td class="unit">${esc(r.unit)}</td>
    <td><span class="kind k-${r.kind === 'sourced' ? 'ok' : 'warn'}">${esc(r.kind)}</span></td><td>${r.verify ? 'yes' : 'no'}</td><td class="src">${src(r.source)}</td></tr>`).join('')}</tbody>`;
}
$('#q').addEventListener('input', debounce(table, 120));
table();
