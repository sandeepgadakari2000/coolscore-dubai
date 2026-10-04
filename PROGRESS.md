# Progress

| Phase | Scope | Status |
|---|---|---|
| 0 | Plan + user-research kit + skeleton | ✅ Done 2026-10-03 (plan approved; D1–D8 as recommended) |
| 1 | Weather + sun | ✅ Done 2026-10-03 |
| 2 | Physics engine (5R1C) | ✅ Done 2026-10-03 |
| 3 | Billing engine | ✅ Done 2026-10-03 |
| 4 | Simulation + surrogate + CoolScore bands | ✅ Done 2026-10-03 |
| 5 | App core (Check, Compare, Investor, Methodology) | ✅ Done 2026-10-03 |
| 6 | Developer View, Listing Badge, API | ✅ Done 2026-10-03 |
| 7 | AI layer (parser, explanations, fallback) | ✅ Done 2026-10-03 |
| 8 | Business layer + real-bill validation | ✅ Done 2026-10-03 |
| 9 | Ship | ✅ Done 2026-10-03 |

## Heat X-ray (2026-10-04): the result as a picture

**Done**
- `coolscore.physics.breakdown`: a heat budget for one unit and month. It re-runs the hourly engine with each source
  switched off (sun through glass, sun on walls and roof, people and appliances, outside air and humidity; the rest is
  conduction). Shares are the average of forward and reverse switch-off orders, so the parts add up exactly. All
  8 variants run as one batch over one month: about 0.25 s, cached per unit and month.
- Heat X-ray component (`app/components/heat_xray/`): a thermal-camera cutaway with particle streams and glows sized
  by kWh per source. Sun, beam and floor patch; facade conduction; humid air at the gaps; people and appliance glow;
  the AC's cold stream. The heat budget shows % and AED per source, with the fixed capacity charge hatched separately.
  Plain comparisons: peak heat flow as people standing in the flat (117 W each, ASHRAE) and the humidity share.
- Finding it shows (typical west-facing 1-bed, August): outside air and humidity ≈ 50% of the heat, walls and glass
  24%, people 16%, sun through the glass 10%; 37% of the AC's work is drying air. In January the fixed capacity charge
  is most of the bill.
- **Tests:** 171 passing (the parts add up and respond to glass, roof and season; the AED split reconciles with the
  month's bill; chiller-free shows kWh only).

## Redesign (2026-10-04): Dubai liquid-glass UI + live climate scene

**Done**
- Design system in `app/ui.py`: Dubai dusk backdrop (desert-gold glow, Gulf turquoise, slow "liquid" light, a
  fictional skyline), frosted liquid-glass panels with a subtle eight-point-star texture, gold gradient headings,
  glowing pill buttons with a sheen, glass inputs, metrics and sidebar. Theme in `.streamlit/config.toml`.
- Live climate scene (`app/components/climate_stage/`, custom component, plain SVG/JS, no new dependency, no network):
  plays a typical day of **measured** weather for the chosen month (`tasks.py climate` →
  `data/demo/climate_monthly.json`, 33 KB). The real sun path, temperature, humidity haze, cloud and
  facade sun drive the sky, sun, beam and window glow. Sea, canal or dunes follow the community's zone. It tweens
  between states and respects reduced motion.
- `streamlit-lottie` was not used: it isn't on the approved dependency list, it would fetch third-party animation
  files at runtime, and stock animations can't show this unit's real conditions.
- Check a Unit is live: there's no submit button and every change re-estimates (about 0.5 s). There's a month picker,
  a heat-coloured monthly chart with P10–P90 whiskers, animated driver bars, and a floating live bar on phones and
  tablets. Home has a self-playing year on a sample flat and three measured facts.
- QA: every page captured at 1440 px and 390 px through a Chrome DevTools driver; no exceptions.

**Tests:** 169 passing (live-flow, scene-arguments and climate-data tests added).

## Phase 9 (2026-10-03): ship

**Done**
- Portfolio README: pitch + positioning line, real screenshots (`docs/screenshots/`), problem, gap, Mermaid
  pipeline, accuracy table with the listing-only R² shortfall stated, real-bill status, physics sanity checks,
  business case, pilot offer, API examples, run and deploy steps, limitations, links. Live-demo and video links are
  placeholders for Sandeep.
- Check a Unit: "Try an example" button and `?example=1` link (a fictional tenant-pays listing) so visitors
  without a listing see a full result in one click. The no-key parser now reads "chiller not included" as tenant pays.
- Listing Badge: "How is this calculated?" with formula and cut-offs (every AED figure now has one).
- Streamlit Community Cloud check: a fresh clone (no `data/simulated/`, no facade cache) runs all 8 pages with no
  errors; the Developer View builds its facade cache in ~5 s on first use; repo ≈ 15 MB, model 7 MB (< 50 MB).
  Deploy: main file `app/Home.py`, Python 3.13, optional `ANTHROPIC_API_KEY` secret.

**Definition of done (brief §12)**
- Paste or form → result in < 3 s with no API key: ✅ (≈ 0.5 s server-side, 1–2.5 s in the browser; tested).
- Every AED figure shows formula, inputs and range: ✅ ("How is this calculated?" on every page with AED).
- Simulated data labelled; no fabricated tariffs, quotes, bills or competitor claims: ✅ (sources in the register;
  findings template is placeholders-only, enforced by a test).
- Surrogate accuracy and physics sanity checks documented: ✅ (`model_card.md`, `docs/evidence/`).
  Listing-only R² 0.938 is below the 0.95 target by design; fidelity R² 0.996 meets it.
- Validation report runs automatically when real bills are added: ✅ (tested with synthetic rows).
- README tells the story in 60 seconds; all tests pass: ✅ 165 passing.

**Left for Sandeep (brief §13)**
- Interviews and real quotes (`docs/user-research/`), anonymised bills (`data/real_bills/`).
- Verify the 61 `verify: true` records, starting with `docs/assumptions.md` → "Verify first".
- ~~Deploy~~ Live since 2026-10-04 on Streamlit Community Cloud (link in the README; GitHub
  sandeepgadakari2000/coolscore-dubai, pushes to `main` redeploy). Still to do: record the demo, add the video link.
- Optional: PDF of the deck needs Marp (`npx @marp-team/marp-cli docs/pitch_deck.md --pdf`); not installed.

## Phase 8 (2026-10-03): business layer + real-bill validation

**Done**
- Real-bill kit: template + field guide + PII guard (Phase 0); `validation.report` runs on every app load and via
  `tasks.py validate`; it rebuilds each billed unit, compares total bill, RTh and capacity charge (MAE, MAPE,
  share within ±20 %, bias) and writes a residual calibration factor once 12+ bill-months exist per system.
  Status today: **no real bills, so real-world accuracy is not yet validated** (said on the Methodology page).
- Sanity band (an independent guide, rough, `verify: true`): simulated 1-bed and 2-bed bills fall inside;
  studio is a little low (324 vs 350–450) and 3-bed a little high (1,218 vs 900–1,200). Reported, not tuned.
- Documents: `prd.md`, `business_model.md` (recommend brokerage seats first, portal API to scale),
  `gtm_and_pilot.md` (90-day brokerage pilot, AED 15,000, metrics fixed in advance), `pitch_deck.md` (Marp,
  6 slides), `interview_prep.md` (12 hard questions), `model_card.md`, `methodology.md`, and `assumptions.md`
  (generated from the YAML registers by `tasks.py assumptions`; a test fails if it is stale).
- Business Case page: every price, plan and cost input adjustable; default plan revenue ≈ AED 353k, profit
  ≈ AED 229k, break-even month 9 (all PROPOSAL values from `assumptions.yaml` → `business`).
- App review fixes: no-key parser reads "22nd floor of 40" / "floor 9/31"; estimates cached and batched
  (Check a Unit answer ≈ 0.5 s server-side, ≈ 1–2.5 s in the browser); what-if now anchored to the result card;
  chiller-free text no longer tells the tenant they pay the capacity charge; drivers chart labels no longer
  cover the axis; Developer View coloured by A–E grade; Compare default shows "cheaper rent, dearer home";
  badge details open on tap (phones); P&L cost line visible in dark mode.

**Tests:** 160 passing.

**For Sandeep:** `docs/assumptions.md` → "Verify first"; Marp is not installed, so the deck is Markdown only
(export: `npx @marp-team/marp-cli docs/pitch_deck.md --pdf`, ask before installing).

## Phases 5–7 (2026-10-03): app, API, AI layer

**Done**
- Streamlit app (7 pages): Check a Unit (paste or form → score, monthly and annual P10–P90, true monthly cost,
  drivers, what-if, explanation, questions for the agent), Compare Units, Investor View (net yield,
  chiller-free premium), Developer View (fictional tower, physics run directly, design levers with AED per unit
  and per tower), Listing Badge demo, Business Case, Methodology & Validation. Every figure has a
  "How is this calculated?" expander; footer disclaimer on every page.
- FastAPI: `POST /score`, `POST /compare`, `GET /health`, OpenAPI docs at `/docs`.
- AI layer: Claude Haiku 4.5 parser (structured output, found/inferred/missing + evidence quote); no-key
  regex fallback; direction helper from map geometry (declines when unsure); explanations pass a number guard
  (any number not in the engine output → template instead).

**Tests:** 155 passing at the Phase 5–7 commit.

## Phase 4 (2026-10-03): simulation + surrogate

**Done**
- 40,000 Latin-hypercube scenarios (seed 42) through physics + billing in ~4 min; monthly aggregates only.
- HistGradientBoosting quantile models (P10/P50/P90, log cost) for annual, August and January tenant cost, in a
  listing-only and a with-household variant; conformal calibration → 79–80 % P10–P90 coverage on held-out runs.
- Accuracy vs held-out physics: **fidelity R² 0.996** (all inputs; target 0.95 met). Listing-only annual
  R² **0.938** (below 0.95 by design: hidden variables become the range, decision D2), MAPE 17 %;
  with household details R² 0.949, MAPE 15 %.
- CoolScore A–E at stock quintiles of standardised cost intensity: A ≤ 6.84 < B ≤ 7.36 < C ≤ 7.88 < D ≤ 8.47 < E
  (AED/sq ft/yr). Counterfactual AED drivers. Artifact ≈ 7 MB.

## Phase 3 (2026-10-03): billing engine

**Done**
- Tariffs from primary sources read on 2026-10-03: DEWA slab page (0.230/0.280/0.320/0.380 AED/kWh, fuel
  surcharge 0.060 AED/kWh for Oct 2026, 5% VAT), Empower charges page (0.568 AED/RTh, 750 AED/RT/yr billed by
  days, meter AED 50/quarter or 30/month), RSB RD10 v1.3 (consumption cap 0.643 incl. fuel surcharge, fuel
  surcharge cap 0.075, single-building plants cap 0.80 with no capacity charges, deposit ≤ 8 months of capacity),
  Al Sa'fat split-AC minimum EER 9.5 (35 °C) / 6.6 (46 °C).
- `billing.engine`: district cooling, single-building plant, DEWA split/central AC (COP falls in heat),
  payer = tenant / chiller-free / service charge; DEWA priced at the marginal slab; VAT once per payer.
- Biggest uncertainty, flagged: contracted capacity per unit (sq ft per RT, MODELLING ASSUMPTION from
  secondary sources). For a typical 1-bed, capacity (~AED 3,000/yr) outweighs consumption (~AED 2,100/yr),
  which matches risk #2.
- Typical 1-bed (800 sq ft, 2005–14, west, mid floor): district cooling ≈ AED 6,700/yr to the tenant;
  chiller-free tenant ≈ AED 850/yr (fans); DEWA split AC ≈ AED 1,700/yr.

**Tests:** 115 passing (21 new for Phase 3).

## Phase 2 (2026-10-03): physics engine

**Done**
- Researched archetypes from primary or near-primary sources: Al Sa'fat text (walls 0.57, roof 0.30, glazing
  by WWR band, 24 °C / 50% RH design, air-leakage rules), DEWA R&D 2020 paper (2014 mandate year), the
  ISO 13790 final draft (5R1C constants, Table 12, F_w, frame fraction, sky radiation), ASHRAE 1997 Ch. 28
  (occupant gains, latent factor), ASHRAE 62.2 (ventilation), a Dubai wall study (U 1.65 uninsulated) and
  manufacturer glass data. Unsourced spreads are labelled MODELLING ASSUMPTION.
- Finding: the post-2014 and post-2022 eras share the same legal envelope limits; Al Sa'fat adds
  thermal-bridge and air-tightness rules.
- Engine: `physics.params` (listing → unit parameters, central or sampled hidden variables),
  `physics.rc5r1c` (vectorised ISO 13790 5R1C, latent load, balcony and neighbour shading, schedules,
  away behaviour, window opening), `physics.reference` (literal ISO Annex C oracle).
- Verified: vectorised = literal ISO to 1e-6 W; steady state = analytic conductance; all six §9 invariants pass.
- Orientation (typical 1-bed, central site): north cheapest; E/W +4% in summer, +7% annually; south +11%
  annually (winter sun). **West ≈ east in energy (−0.1%)** but +2.5% in design peak, which is reported honestly
  rather than forced. Literature (window-only, snippet) points the same way with bigger numbers.
- Stock spread (2,000 sampled units): median 274 → 119 kWh_th/m²/yr from pre-2005 to 2022+; latent ≈ 35%.
- Speed: 2,000 units × 8,784 h ≈ 10 s, so 40,000 scenarios ≈ 3–4 min.

**Tests:** 94 passing (19 new for Phase 2).

**For Sandeep to verify:** `config/archetypes.yaml` and the `physics:` block of `config/assumptions.yaml`,
especially infiltration and pre-treated fresh-air shares (the biggest drivers of the latent share).

**Next (Phase 3):** billing engine with primary-source tariffs (DEWA slabs and fuel surcharge, district cooling
capacity and consumption, VAT), DEWA AC electricity via COP and the stored load × (T − 35 °C) term, chiller-free
and service-charge cases.

## Phase 1 (2026-10-03): weather + sun

**Done**
- Open-Meteo archive fetch and cache, 3 sites × 2023–25, ECMWF IFS 9 km (`coolscore.weather.openmeteo`).
  ERA5 was rejected because it puts all three sites in one 0.25° grid cell.
- Validated against NOAA ISD airport observations (`weather.stations`). Raw IFS runs 1.8 °C cool at
  Dubai International (misses evening and night urban heat; cooling degree-hours 0.80× observed).
- Bias correction per (month, hour) for temperature and dew point (`weather.correction`). On the unseen
  2025 holdout: Dubai International RMSE 2.38 → 1.31 °C, cooling degree-hours 0.81 → 1.02×. Caveat: the
  Al Maktoum dew-point correction doesn't carry over (holdout bias +0.36 → +0.90 °C).
- **D8 decided by data:** coastal ≈ central (about 1% cooling degree-hours, 0.2 °C dew point), so coastal
  communities use the central weather. Inland stays separate (about 13% fewer cooling degree-hours).
- Facade sun for 8 orientations with pvlib (Perez sky; ground term computed at runtime from albedo 0.12–0.40).
- Sanity checks pass: summer E/W 3.4 vs S 1.84 vs N 1.88 kWh/m²/day; while above 38 °C, west gets 34%
  more sun than east; winter south is highest; north is lowest annually.
- Report `docs/evidence/weather.md` + interactive charts `docs/evidence/weather.html`.
- Assumptions filled: ground albedo range, Open-Meteo terms, NOAA source, bias-correction method.

**Tests:** 75 passing (26 new for Phase 1). `tasks.py data` takes about 30 s.

**Next (Phase 2):** 5R1C engine (single unit → vectorised), archetype envelope values from primary sources,
schedules, invariant tests, orientation effect vs published UAE studies.

## Phase 0 (2026-10-03)

**Done**
- User-research kit (written first): hypotheses with pass/fail thresholds and decision rules,
  4 interview guides, outreach messages (LinkedIn/WhatsApp), bill request, findings template, interview log.
- Real-bill template (`data/real_bills/template.csv`) + field guide + PII guard (`coolscore.validation.pii`).
- Competitive check (`docs/competitive_landscape.md`): no direct Dubai competitor found; all local
  tools need RT, RTh or AC tonnage from a bill. Closest overlap: one calculator's manual "hot-facing" preset.
- Plan (`docs/plan.md`): architecture, schemas, archetypes, scenario ranges, 20 assumptions to
  verify, 10 risks, 8 decisions.
- Config: assumption register (placeholders with candidate sources), archetypes, communities
  (3 microclimates), settings. Skeleton package, `tasks.py` + Makefile, pinned requirements.
- Environment: Python 3.13.3 venv at `C:\Users\sande\.venvs\coolscore`; all allowed deps install cleanly.

**Tests:** see the latest commit message for the count. All Phase 0 tests pass.

**Decisions D1–D8** (`docs/plan.md` §8): approved as recommended on 2026-10-03.

**Sandeep's to-do now:** start outreach (`docs/user-research/outreach_messages.md`); ask every tenant for typed bill figures.

## Assumption register status
66 records (`docs/assumptions.md`): 39 sourced, 19 modelling assumptions, 3 proposals, 2 placeholders,
3 not yet researched (orientation-literature figure, GHI published range, permit-to-completion lag; none is
used by the engine). 61 are still `verify: true`.
