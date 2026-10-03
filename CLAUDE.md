# CoolScore Dubai: working rules

Predicts a specific Dubai apartment's cooling cost (AED, P10–P90) before rent/purchase,
using building physics + Dubai tariffs + an ML surrogate. Full brief: `CoolScore_PROJECT_BRIEF.md`.
Plan: `docs/plan.md`. Status: `PROGRESS.md` (read it first every session).

## Process
- Build in phases (brief §11). After every phase: run all tests, update `PROGRESS.md`, commit.
  2026-10-03 Sandeep: finish Phases 3-9 without stopping between phases (one summary at the end).
- Commit as Sandeep (repo-local git config), no Claude co-author line (decision D5).
- YAML 1.1 traps: quote keys like `"2005_2014"` (int) and `"off"`/`"on"`/`"no"` (bool).
- Dependencies allowed without asking: numpy, pandas, scikit-learn, pvlib, requests, pyyaml,
  streamlit, plotly, fastapi, uvicorn, pydantic, anthropic, pytest. **Ask before anything else**
  (EnergyPlus, LightGBM, SHAP, numba, pyarrow as a direct dependency...).

## Facts and honesty
- Never invent tariffs, bills, building specs, competitor claims or user quotes.
- Every real-world number lives in `config/assumptions.yaml` (or `archetypes.yaml`) with
  value, unit, source URL, date_checked, verify, notes, phase. `value: null` = placeholder.
- Third-party blog figures are not sources; find the primary source or leave a placeholder.
- Label simulated outputs as simulated everywhere; always show ranges, never one exact number.
- Never scrape property portals. Users paste listing text or fill a form.
- UI uses fictional tower/developer names; no real portal/developer logos or brands.
- `data/real_bills/`: anonymised typed figures only, no PII, no images. The PII test must pass.
- `docs/user-research/findings_template.md` stays placeholders-only (a test enforces it).

## Architecture
```
config/            assumptions.yaml · archetypes.yaml · communities.yaml · settings.yaml
data/raw/          cached weather + facade irradiance (no API calls at app runtime)
data/simulated/    scenario + billed datasets (regenerable, gitignored)
data/demo/         small committed artifacts for the deployed app (< 50 MB total)
data/real_bills/   template.csv + anonymised bills
src/coolscore/
  weather/    Open-Meteo archive fetch/cache, pvlib facade irradiance (8 orientations)
  physics/    ISO 13790 5R1C hourly engine, numpy-vectorised over units; schedules
  billing/    district cooling, DEWA slabs (marginal), chiller-free, service charge
  simulate/   Latin-hypercube scenarios, batched runs, monthly aggregation only
  model/      HistGradientBoosting P10/P50/P90, counterfactual drivers, A–E bands
  validation/ PII guard, real-bill accuracy report, residual calibration
  assistant/  Claude listing parser, direction helper, explanations; no-key fallback
api/               FastAPI: POST /score, POST /compare, GET /health
app/               Streamlit Home.py + pages/
docs/              plan, competitive landscape, user research, business docs
tests/             pytest
```
Key design rules:
- Weather = Open-Meteo ECMWF IFS 9 km, temp/dew point bias-corrected to NOAA airport obs; read it via
  `coolscore.weather.dataset.load_weather` (offline). Coastal communities use central weather (D8).
- Radiation rows are preceding-hour means: solar geometry at t − 30 min. Facade ground term uses albedo at runtime.
- Physics: `physics.params.ListingSpec` → `build_params(specs, "central" | rng)` → `engine.run_site_year`.
  Vectorised 5R1C must match `physics.reference` (literal ISO Annex C); outputs monthly kWh_th only.
- Physics → monthly energy is cached; billing runs separately so tariff changes only re-bill + retrain.
- Never hold full hourly arrays for all scenarios: aggregate to monthly totals + peak during the run.
- CoolScore grade uses a standardised cost (unit only, decision D1); AED shown for the actual payer.
- Accuracy: fidelity R² ≥ 0.95 (all inputs) vs listing-only metrics reported honestly (D2).
- LLM never produces numbers: engine numbers are passed in; a guard rejects unknown numbers.

## Environment (this machine)
- Python 3.13 venv **outside OneDrive**: `C:\Users\sande\.venvs\coolscore`
  (`python` on PATH is 3.9, so don't use it). Create elsewhere with `py -3.13 -m venv <path>`.
- No `make` on Windows: use `tasks.py`. Marp is not installed (ask before installing).

## Commands
```
C:\Users\sande\.venvs\coolscore\Scripts\python.exe tasks.py setup     # install pinned deps
C:\Users\sande\.venvs\coolscore\Scripts\python.exe tasks.py test      # pytest -q
... tasks.py data             # fetch + correct weather, facade sun (network, ~30 s)
... tasks.py report-weather   # docs/evidence/weather.md + weather.html
... tasks.py report-physics   # docs/evidence/physics.md (orientation, archetypes, stock spread)
... tasks.py simulate (~4 min) | train (~2 min) | validate | assumptions (docs/assumptions.md)
... tasks.py app (Streamlit, :8501) | api (FastAPI, :8000, docs at /docs)
```
Pipeline budget: full `data → simulate → train` ≤ 15 min on a laptop; app answers < 3 s.
