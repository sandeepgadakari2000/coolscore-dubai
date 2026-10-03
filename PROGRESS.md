# Progress

| Phase | Scope | Status |
|---|---|---|
| 0 | Plan + user-research kit + skeleton | ✅ Done 2026-10-03, **awaiting approval of the plan** |
| 1 | Weather + sun | ⏳ Waiting for "go" |
| 2 | Physics engine (5R1C) | — |
| 3 | Billing engine | — |
| 4 | Simulation + surrogate + CoolScore bands | — |
| 5 | App core (Check, Compare, Investor, Methodology) | — |
| 6 | Developer View, Listing Badge, API | — |
| 7 | AI layer (parser, explanations, fallback) | — |
| 8 | Business layer + real-bill validation | — |
| 9 | Ship | — |

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

**Open decisions (need Sandeep):** D1–D8 in `docs/phase0_plan.md` §8.

**Sandeep's to-do now:** start outreach (`docs/user-research/outreach_messages.md`); ask every tenant for typed bill figures.

## Assumption register status
All tariff, envelope and behaviour values are `null` placeholders until their phase researches them.
Only the RT→kW conversion (NIST SP 811) is filled.
