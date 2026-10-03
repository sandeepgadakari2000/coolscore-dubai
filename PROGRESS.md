# Progress

| Phase | Scope | Status |
|---|---|---|
| 0 | Plan + user-research kit + skeleton | ✅ Done 2026-10-03 (plan approved; D1–D8 as recommended) |
| 1 | Weather + sun | ✅ Done 2026-10-03 |
| 2 | Physics engine (5R1C) | ✅ Done 2026-10-03 |
| 3 | Billing engine | ✅ Done 2026-10-03 |
| 4 | Simulation + surrogate + CoolScore bands | 🔄 In progress |
| 5 | App core (Check, Compare, Investor, Methodology) | — |
| 6 | Developer View, Listing Badge, API | — |
| 7 | AI layer (parser, explanations, fallback) | — |
| 8 | Business layer + real-bill validation | — |
| 9 | Ship | — |

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
- Report `docs/phase1_weather_sun.md` + interactive charts `docs/figures/phase1_weather_sun.html`.
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
- Plan (`docs/phase0_plan.md`): architecture, schemas, archetypes, scenario ranges, 20 assumptions to
  verify, 10 risks, 8 decisions.
- Config: assumption register (placeholders with candidate sources), archetypes, communities
  (3 microclimates), settings. Skeleton package, `tasks.py` + Makefile, pinned requirements.
- Environment: Python 3.13.3 venv at `C:\Users\sande\.venvs\coolscore`; all allowed deps install cleanly.

**Tests:** see the latest commit message for the count. All Phase 0 tests pass.

**Decisions D1–D8** (`docs/phase0_plan.md` §8): approved as recommended on 2026-10-03.

**Sandeep's to-do now:** start outreach (`docs/user-research/outreach_messages.md`); ask every tenant for typed bill figures.

## Assumption register status
Filled: constants, weather (Phase 1), all physics and schedule records (Phase 2), archetypes A1–A4.
Still null: all billing tariffs (Phase 3), sanity bands (Phase 8), business (Phase 8), orientation literature
(paper not openable), permit-to-completion lag.
