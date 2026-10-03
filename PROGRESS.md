# Progress

| Phase | Scope | Status |
|---|---|---|
| 0 | Plan + user-research kit + skeleton | ✅ Done 2026-10-03 (plan approved; D1–D8 as recommended) |
| 1 | Weather + sun | ✅ Done 2026-10-03 |
| 2 | Physics engine (5R1C) | ⏳ Waiting for "go" |
| 3 | Billing engine | — |
| 4 | Simulation + surrogate + CoolScore bands | — |
| 5 | App core (Check, Compare, Investor, Methodology) | — |
| 6 | Developer View, Listing Badge, API | — |
| 7 | AI layer (parser, explanations, fallback) | — |
| 8 | Business layer + real-bill validation | — |
| 9 | Ship | — |

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
Filled: RT→kW (NIST SP 811), ground albedo range, Open-Meteo terms, NOAA ISD source, weather bias-correction method.
All tariff, envelope and behaviour values remain `null` placeholders until their phase researches them.
