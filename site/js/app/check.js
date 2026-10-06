// Check a Unit: listing → live estimate, the climate scene, heat X-ray, drivers, months, what-if, plain words.
import { $, $$, api, meta, chrome, unitForm, embed, gradeBadge, driversHTML, monthlyChart, aed, aedR, esc, debounce, setBusy } from './common.js';

chrome('check');
const M = await meta();
const stage = embed($('#stage')), xray = embed($('#xray'));
let form, month = 7, last = null, seq = 0;

const md = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').split(/\n{2,}/).map((p) => p.trim().startsWith('- ')
  ? `<ul>${p.split('\n').map((l) => `<li>${l.replace(/^- /, '')}</li>`).join('')}</ul>` : `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');

async function build(defaults) {
  form = await unitForm($('#unit'), defaults);
  form.onChange(debounce(update, 280));
  update();
}

// ---------- the estimate ----------
async function update() {
  const listing = form.get(), my = ++seq;
  setBusy($('#result'), true);
  let r;
  try { r = await api('estimate', { listing, month }); }
  catch (err) {
    if (my !== seq) return;
    setBusy($('#result'), false);
    $('#result').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`;
    return;
  }
  if (my !== seq) return;
  last = { r, listing };
  setBusy($('#result'), false);
  renderResult(r, listing);
  stage.render(r.stage);
  $('#how').innerHTML = r.how.map((t) => `<p>${esc(t)}</p>`).join('') + r.notes.map((n) => `<p class="note">${esc(n)}</p>`).join('');
  $('#assumed').innerHTML = r.assumed.length ? `<p class="flag">Assumed because not given: <b>${r.assumed.map((a) => a.replace(/_/g, ' ')).join(', ')}</b>. Change them above if you know better.</p>` : '';
  $('#drivers').innerHTML = driversHTML(r.drivers);
  renderMonths();
  $('#plain').innerHTML = md(r.plain);
  $('#questions').innerHTML = r.questions.map((q) => `<li>${esc(q)}</li>`).join('');
  syncWhatIf(listing);
  heat();
  whatif();
}

function renderResult(r, listing) {
  const e = r.estimate, mr = r.month_ranges[month];
  const tc = r.true_cost;
  $('#result').innerHTML = `
    <div class="res-head">${gradeBadge(e.score, r.score_color, 62)}
      <div><div class="k">CoolScore ${e.score} · ${esc(r.score_word)} cooling cost per sq ft</div>
        <div class="big">${aedR(e.annual)} <span style="font-size:.5em;color:var(--ink-3)">a year</span></div>
        <div class="small">P10–P90 · typical ${aed(e.annual.p50)} · ${e.variant === 'detailed' ? 'with your household' : 'listing facts only'} · simulated</div></div></div>
    <div class="kpis mt">
      <div class="kpi"><b>${aed(mr[0])}–${Math.round(mr[2]).toLocaleString('en-US')}</b><span>${M.month_names[month]} bill</span></div>
      ${month === 7 ? `<div class="kpi"><b>${e.intensity_aed_per_sqft.toFixed(2)}</b><span>AED / sq ft / year</span></div>`
    : `<div class="kpi"><b>${aedR(e.summer_month)}</b><span>August (peak)</span></div>`}
      <div class="kpi"><b>${aedR(e.winter_month)}</b><span>January</span></div>
      ${tc ? `<div class="kpi"><b>${aed(tc.total)}</b><span>True cost / month</span><small>rent + cooling + housing fee</small></div>`
    : `<div class="kpi"><b>${e.intensity_aed_per_sqft.toFixed(2)}</b><span>AED / sq ft / year</span><small>standard household</small></div>`}
    </div>`;
  const lb = $('#livebar');
  lb.innerHTML = `${gradeBadge(e.score, r.score_color, 36)}<div><b>AED ${mr[0].toLocaleString('en-US')}–${mr[2].toLocaleString('en-US')}</b> / month in ${M.months[month]}<span>${aedR(e.annual)} a year · simulated</span></div>`;
}

function renderMonths() {
  const r = last.r;
  monthlyChart($('#months'), { ranges: r.month_ranges, colors: r.month_colors, tmax: r.month_tmax, months: M.months, month, onPick: setMonth });
}

function setMonth(i) {
  month = i;
  $('#month').value = i; $('#month-out').textContent = M.months[i];
  if (!last) return;
  stage.render({ ...last.r.stage, month: i });
  renderResult(last.r, last.listing);
  renderMonths();
  heat();
}
$('#month').addEventListener('input', (e) => setMonth(+e.target.value));

// ---------- heat X-ray (physics, a bit slower: its own request) ----------
const heat = debounce(async () => {
  if (!last) return;
  $('#xray-month').textContent = M.month_names[month];
  setBusy($('#xray-card'), true);
  try { xray.render(await api('heat', { listing: last.listing, month })); } catch { /* the card keeps the last picture */ }
  setBusy($('#xray-card'), false);
}, 150);

// ---------- what if ----------
const wf = $('#wi-floor'), wface = $('#wi-face'), wsp = $('#wi-sp'), wfree = $('#wi-free');
wface.innerHTML = M.facings.map((f) => `<option>${f}</option>`).join('');
function syncWhatIf(l) {
  wf.max = l.total_floors; wf.value = Math.min(+wf.value || l.floor, l.total_floors);
  if (!syncWhatIf.done || syncWhatIf.key !== JSON.stringify(l)) {
    wf.value = l.floor; wface.value = l.facing; wsp.value = l.setpoint_c || 24; wfree.checked = l.payer === 'landlord_chiller_free';
    syncWhatIf.done = true; syncWhatIf.key = JSON.stringify(l);
  }
  const dewa = l.system === 'dewa_split_ac' || l.system === 'dewa_central_ac';
  wfree.disabled = dewa; $('#wi-free-l').textContent = dewa ? 'Not with DEWA-billed AC' : 'Landlord pays cooling';
  $('#wi-floor-out').textContent = wf.value; $('#wi-sp-out').textContent = `${(+wsp.value).toFixed(1)} °C`;
}
const whatif = debounce(async () => {
  if (!last) return;
  $('#wi-floor-out').textContent = wf.value; $('#wi-sp-out').textContent = `${(+wsp.value).toFixed(1)} °C`;
  const change = { floor: +wf.value, facing: wface.value, setpoint_c: +wsp.value, chiller_free: wfree.checked && !wfree.disabled };
  try {
    const w = await api('whatif', { listing: last.listing, change });
    const d = Math.round(w.delta);
    $('#whatif').innerHTML = `
      <div class="kpi"><b>${aed(w.annual.p50)}</b><span>Typical annual cost</span><small class="${d > 0 ? 'up' : d < 0 ? 'down' : ''}">${d > 0 ? '+' : d < 0 ? '−' : '±'}${aed(Math.abs(d)).replace('AED ', 'AED ')} vs now</small></div>
      <div class="kpi"><b>${aedR(w.summer)}</b><span>Summer month</span></div>
      <div class="kpi"><b style="color:${w.score_color}">${w.score}</b><span>CoolScore</span><small>the grade uses a standard household and tariff</small></div>`;
  } catch (err) { $('#whatif').innerHTML = `<p class="flag bad">${esc(err.message)}</p>`; }
}, 200);
$$('#whatif-controls input, #whatif-controls select').forEach((el) => el.addEventListener('input', whatif));

// ---------- listings ----------
const text = $('#listing-text'), readBtn = $('#read');
text.addEventListener('input', () => { readBtn.disabled = !text.value.trim(); });
async function readListing(t) {
  readBtn.classList.add('busy');
  try {
    const p = await api('parse', { text: t });
    $('#parse-out').innerHTML = `${p.missing.length ? `<p class="flag mt">Missing — please confirm: <b>${p.missing.map((m) => m.replace(/_/g, ' ')).join(', ')}</b></p>` : ''}
      <details class="how"${p.missing.length ? ' open' : ''}><summary>What we read from the listing (${esc(p.method)}) — check every field</summary>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Field</th><th>Value</th><th>Status</th><th>From the text</th></tr></thead><tbody>
      ${p.fields.map((f) => `<tr><td>${esc(f.field.replace(/_/g, ' '))}</td><td>${esc(f.value ?? '')}</td><td>${esc(f.status)}</td><td>${esc(f.evidence)}</td></tr>`).join('')}</tbody></table></div></details>`;
    await build(p.defaults);
  } catch (err) { $('#parse-out').innerHTML = `<p class="flag bad mt">${esc(err.message)}</p>`; }
  readBtn.classList.remove('busy');
}
readBtn.addEventListener('click', () => readListing(text.value));
$('#example').addEventListener('click', () => { text.value = M.example; readBtn.disabled = false; readListing(M.example); });

// ---------- facing helper ----------
const hc = $('#h-comm'), hv = $('#h-view');
hc.innerHTML = M.communities.map((c) => `<option${c === 'Dubai Marina' ? ' selected' : ''}>${esc(c)}</option>`).join('');
hv.innerHTML = M.view_phrases.map((v) => `<option>${esc(v)}</option>`).join('');
async function hint() {
  const h = await api('direction', { community: hc.value, view: hv.value }).catch(() => ({}));
  $('#h-out').innerHTML = h.facing
    ? `Likely facing: <b>${h.facing}</b> (${esc(h.reason)}). A suggestion from map geometry — confirm at the viewing (the afternoon sun comes in from the west). <button class="link-btn" id="h-use">Use ${h.facing}</button>`
    : 'No reliable suggestion for this combination. At the viewing, note where the afternoon sun comes in: that side faces west.';
  $('#h-use')?.addEventListener('click', () => { const s = $('#unit [name="facing"]'); s.value = h.facing; s.dispatchEvent(new Event('change', { bubbles: true })); });
}
[hc, hv].forEach((el) => el.addEventListener('change', hint));
$('#helper-toggle').addEventListener('click', (e) => {
  const open = $('#helper').hidden; $('#helper').hidden = !open; e.target.setAttribute('aria-expanded', open); if (open) hint();
});

// phone: show the live bar once the result card scrolls away
new IntersectionObserver(([en]) => $('#livebar').classList.toggle('on', !en.isIntersecting && !!last), { threshold: 0 }).observe($('#result'));

if (new URLSearchParams(location.search).get('example') === '1') { text.value = M.example; readBtn.disabled = false; readListing(M.example); }
else build({});
