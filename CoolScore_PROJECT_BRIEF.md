# PROJECT BRIEF: CoolScore Dubai
*Predict any Dubai apartment's cooling cost before you rent or buy it. (Working name — I may rename it.)*

---

## 0. How we work (read first)

You are my senior engineer and product partner. Build this in phases (Section 11).

- **Phase 0 is planning + validation kit only.** Show me the plan and wait for my approval before writing product code.
- **After every phase:** run all tests, update `PROGRESS.md`, commit with a clear message, summarize in 10 lines or fewer, then **stop and wait for my "go"**.
- **Dependencies:** Python 3.11+. Allowed without asking: numpy, pandas, scikit-learn, pvlib, requests, pyyaml, streamlit, plotly, fastapi, uvicorn, pydantic, anthropic, pytest. **Ask before adding anything else** (e.g., EnergyPlus, LightGBM, SHAP).
- **Never invent real-world facts:** tariffs, bills, building specs, competitor claims. Every number goes in `config/assumptions.yaml` with `value`, `unit`, `source` (URL), `date_checked`, `verify: true/false` and `notes`. If you can't find a reliable source, use a clearly marked placeholder.
- **Never fabricate user quotes or real bills.**
- **Do not scrape property portals.** Users paste listing text or fill a form.
- **Mockups use fictional names.** Real community names (e.g., Dubai Marina) are fine as locations, but don't show real towers, developers, portals or logos in the UI.
- Everything runs on a normal laptop: full pipeline in about 15 minutes or less; the app answers in under 3 seconds.
- In Phase 0, create a short `CLAUDE.md` (under 80 lines) with these rules, the architecture, and the run/test commands, so every future session keeps context.

## 1. Who I am and what this project must prove

I'm Sandeep: B.E. in Civil Engineering, MBA in Finance & Business Analytics, Duke AI Product Management certificate. I'm targeting product manager roles (AI, growth and business PM) at Dubai real estate developers, property portals and proptech firms.

This project must prove three things:
1. **Product judgement:** I found a real, unserved gap and validated it with real people.
2. **Technical depth:** building physics + ML done rigorously (my civil engineering edge).
3. **Business ownership:** I think in AED: pricing, unit economics, P&L, go-to-market.

Clarity and polish beat feature count.

## 2. The problem and the gap

- Cooling is one of the biggest living costs in Dubai, and it varies a lot between units, even in the same tower: facing direction, floor, amount of glass, shading, building age, and the cooling system and billing (district cooling with capacity + consumption charges, DEWA-billed AC, chiller-free).
- Listings show rent, not the real cost of living there.
- **What exists today** (verify each in `docs/competitive_landscape.md` with sources):
  - Appliance calculators: need AC wattage/tonnage and usage hours, which a tenant viewing a listing doesn't know. They work after you move in.
  - Cooling provider calculators: for existing customers, based on actual consumption.
  - Guides: rough averages by bedroom count.
  - Project-level investment scores: rate whole projects, not individual units.
- **The gap:** nothing predicts a specific unit's cooling cost before the rent or buy decision.
- **Positioning line** (use in README and pitch): *"Existing tools are appliance calculators that work after you move in. CoolScore predicts a specific unit's cooling cost before you sign, using building physics and Dubai's cooling tariffs."*

## 3. The product

**Input** (pasted listing text or a form): community, building age, cooling system and who pays (chiller-free or not), unit size, bedrooms, floor and total floors, facing direction(s), amount of glass, balcony/shading, rent (and price for investors). Optional: household size, home during the day or not, preferred AC temperature.

**Output:**
- Predicted cooling cost in AED: monthly (summer peak, winter low) and annual, always with a likely range (P10–P90)
- True monthly cost = rent + cooling (+ estimated DEWA share)
- **CoolScore A–E**, like an energy label
- Top drivers in AED, e.g., "west-facing: +AED X/year vs north-facing" (numbers from the model only)
- What-if controls: change floor, direction, AC temperature or chiller-free status and see the impact

| User | Use case |
|---|---|
| Tenant | Compare units by true monthly cost, not just rent |
| Buyer / investor | Net yield after cooling; price a chiller-free offer |
| Broker | Answer "how much will AC cost?" with confidence; differentiate listings |
| Property portal | CoolScore badge on listings; filter by true cost |
| Developer | Design and market lower-cooling-cost units |

## 4. Approach: physics-informed ML

No public dataset of unit-level cooling bills exists, so:
1. **Physics engine:** hourly thermal simulation of one apartment under real Dubai weather.
2. **Simulated dataset:** tens of thousands of unit and household scenarios.
3. **ML surrogate:** learns physics + billing for instant predictions with uncertainty ranges.
4. **Calibration layer:** once real bills are collected, learn a residual correction and report real-world accuracy.

Label simulated results clearly everywhere. Show ranges, never a single "exact" number.

### 4.1 Weather and sun
- Hourly weather from the **Open-Meteo Historical Weather API** (free, no key; check its terms): temperature, humidity/dew point, global/direct/diffuse solar radiation, wind. Fetch the 3 most recent full years for 3 microclimates: coastal (Dubai Marina area), central (Downtown/Business Bay) and inland (Dubai South area). Document the approximate coordinates. Cache in `data/raw/`; never call external APIs at app runtime. Optional alternative: a Dubai typical-year EPW weather file from a reputable source.
- Solar heat on vertical facades for 8 orientations using **pvlib** (solar position + transposition, documented ground reflectance).
- **Sanity expectations (test them):** in Dubai's summer, east and west facades receive the most solar heat; south facades get less than people expect because the midday sun is almost overhead; west-facing units should cost more than east-facing ones because the west sun coincides with the hottest hours. Compare the size of the effect against published UAE studies and cite them.

### 4.2 Physics engine (one apartment = one thermal zone)
- Implement a simplified hourly method such as the **ISO 13790 5R1C model**, vectorized in numpy across many units at once.
- **Envelope:** exterior facade(s) by orientation (corner units have two), window-to-wall ratio, glazing U-value and SHGC, opaque wall U-value, roof exposure for top floors; neighbouring units treated as adiabatic.
- **Shading:** balcony/overhang depth plus an obstruction level from neighbouring towers (open / partial / heavy).
- **Internal gains with schedules:** people, appliances, lighting; UAE Saturday–Sunday weekend; optional Ramadan schedule (dated lookup, marked `verify`).
- **Infiltration/ventilation** with sensible and a simplified latent (humidity) load; Dubai's humidity matters.
- **Behaviour:** cooling setpoint default 24°C (configurable); occupancy profiles (away all day vs home all day).
- **Building archetypes by era**, e.g., older mid-rise with tinted glass, 2010s glass high-rise, recent towers built under Dubai's green building regulations (Al Sa'fat). Research typical U-values/SHGC per era and mark them `verify`.
- **Output:** hourly cooling load (kWh thermal) and peak load per unit.

### 4.3 Billing engine (Dubai-specific)
Convert cooling load to AED for each system:
- **District cooling:** consumption charge per ton-hour (1 RTh = 3.517 kWh thermal); capacity/demand charge payable even at zero usage (document how you estimate contracted capacity per unit); fuel surcharge where applicable; meter/admin fees; 5% VAT. Research published provider tariffs and the regulatory framework; cite sources; mark `verify`.
- **DEWA-billed AC** (split or central AC on the unit's own meter): electricity = cooling load ÷ efficiency (efficiency drops in extreme heat) + fan energy. Apply DEWA residential slab tariffs and fuel surcharge as the **marginal** cost on top of a baseline household consumption (an assumption). Cite sources; mark `verify`.
- **Chiller-free:** the tenant pays no district cooling charges but still pays DEWA for indoor fan coil units; the landlord bears the cooling cost (show it in the Investor View).
- **Central plant recovered through service charges:** show it as part of owner costs.

### 4.4 Simulated dataset + ML surrogate
- Sample **20,000–50,000 scenarios** (Latin hypercube or similar) across communities, archetypes, floors, orientations, glazing, shading, unit sizes, household profiles, cooling systems and weather years.
- **Memory rule:** aggregate to monthly totals and peak load during the run; never store full hourly arrays for all scenarios.
- **Targets:** annual and monthly cooling energy and AED cost per billing type.
- **Inputs:** train on features a person can actually get from a listing. Treat unknowns (exact glazing spec, household behaviour, weather year) as hidden variation so the P10–P90 range reflects real uncertainty. When the user adds optional details, use a model variant that includes them, giving a narrower range.
- **Model:** scikit-learn HistGradientBoosting, plus quantile models for P10/P50/P90. Ask before switching to LightGBM.
- **Accuracy vs held-out physics runs:** R², MAE (AED), MAPE. Target R² ≥ 0.95; tell me if it isn't met.
- **Explanations:** counterfactual drivers. Switch one feature to a reference value (north-facing, mid floor, standard glass, open view) and show the AED difference.
- **CoolScore A–E:** bands on cooling cost intensity (AED per sq ft per year) across the simulated Dubai stock. Document the cut-offs and always show the absolute AED too.

### 4.5 Real-bill validation kit (the credibility layer)
- `data/real_bills/template.csv` for anonymized bills I'll collect: community, building era band, floor band, facing, size, bedrooms, cooling system, who pays, monthly amounts. **No names, unit numbers, account numbers or bill images.** Add a test that fails if PII-like columns appear.
- A validation report that runs automatically when real bills are added: MAE, MAPE, share within ±20%, and a simple residual calibration.
- Sanity-check predictions against published ranges (e.g., typical monthly cooling bills by bedroom count from reputable guides). Treat them as rough bands and cite sources.

## 5. AI layer

- **Listing parser:** the user pastes listing text; Claude extracts structured JSON (size, beds, floor, view, chiller-free, rent, community). Anything not found is shown as "missing — please confirm"; never guess silently.
- **Direction helper:** if a listing only says "sea view" or similar, suggest a likely direction for that community and ask the user to confirm.
- **Plain-language explanation** of each result, plus a short "questions to ask the agent" list (e.g., who pays chiller charges, what the capacity charge is).
- Uses `ANTHROPIC_API_KEY` (env or Streamlit secrets) via the official Anthropic Python SDK. Keep the model name in `config/settings.yaml` (default `claude-haiku-4-5-20251001`; check Anthropic's docs for current model names). **All numbers come from the engine; the LLM never invents figures.**
- **Without a key:** manual form + template explanations, so the public demo always works at zero cost.
- Stretch goal only: Arabic output, released only after native-speaker review.

## 6. App (Streamlit, mobile-first)

1. **Check a Unit:** paste a listing or fill the form → result card with score, monthly/annual range, true monthly cost, top drivers, what-if controls
2. **Compare Units:** 2–4 units side by side; highlight when the cheaper rent turns out to be the more expensive home
3. **Investor View:** net yield after cooling and service charges (inputs); chiller-free vs not; the rent premium a chiller-free offer must earn to pay off
4. **Developer View:** facade heatmap of a fictional tower (floors × directions coloured by CoolScore) and design levers (glass ratio, glazing spec, shading, balcony depth) with AED impact per unit and for the whole tower. This view may call the physics engine directly.
5. **Listing Badge Demo:** a generic, unbranded listing card showing "CoolScore B · Est. cooling AED X–Y/month" with a tooltip
6. **Business Case:** interactive pricing, unit economics and 12-month P&L calculator (Section 8)
7. **Methodology & Validation:** physics, data, surrogate accuracy, real-bill validation status, assumptions, limitations

**Design:** clean, professional, phone-friendly; scores coloured A (green) to E (red); AED with thousands separators; a "How is this calculated?" expander on every number; footer disclaimer: *"Estimates for guidance only — not a quote from DEWA or any cooling provider."*

## 7. API (shows B2B thinking)

FastAPI service using the same model: `POST /score` (unit features → score, range, drivers), `POST /compare`, `GET /health`. Auto-generated OpenAPI docs and example requests in the README. Running locally is enough.

## 8. Product and business documents (`/docs`)

1. `prd.md`: problem, users, jobs-to-be-done, MVP scope, out of scope, success metrics, risks
2. `competitive_landscape.md`: existing tools with links, what each does and doesn't do, our differentiation; flag any direct competitor you find
3. `user-research/`: interview guides for 4 personas (tenants, brokers, investors, developers); short LinkedIn/WhatsApp outreach messages; a request message for anonymized cooling bills; findings template with `[REAL QUOTE — FILL AFTER INTERVIEW]` placeholders
4. `business_model.md`: options (portal API licence per scored listing or annual, developer design/marketing reports, broker premium reports, consumer freemium); recommend one with reasoning; unit economics; 12-month P&L; break-even. All numbers from `assumptions.yaml`, marked as assumptions.
5. `gtm_and_pilot.md`: 90-day pilot with one brokerage scoring its active listings; success metrics (inquiries per listing, lead quality, time to let, user trust survey); timeline; pilot price in AED; risks and mitigations
6. `pitch_deck.md`: 6 slides in Marp (Problem → Gap → Product demo → Proof: accuracy + validation → Business model → Pilot ask). Export to PDF if Marp CLI is available; ask before installing.
7. `interview_prep.md`: the 12 toughest questions with honest answers, including "It's simulated, so why trust it?", "How accurate is it against real bills?", "Why would a portal show a score that makes some listings look worse?" (landlord and agent resistance), and "How did you check nobody had built this?"
8. `model_card.md`, `methodology.md`, `assumptions.md`

## 9. Quality bar

**25+ pytest tests**, including:
- **Physics invariants:** more glass → higher load; west > north in summer for the same unit; higher setpoint → lower load; more shading → lower load; top floor ≥ mid floor; removing solar gains → lower load
- **Billing:** components sum to the total; capacity charge applies at zero usage; chiller-free → zero district cooling charges for the tenant but DEWA fan cost > 0; VAT applied exactly once
- Surrogate accuracy above threshold on held-out physics data
- CoolScore bands monotonic with cost intensity
- Parser output matches the schema and flags missing fields
- No PII columns in real-bill data
- API contract tests, app smoke tests, reproducibility with a fixed seed

**Code:** type hints, docstrings, small focused modules; a Makefile or scripts for `setup`, `data`, `simulate`, `train`, `test`, `app`, `api`.

**Portfolio-grade README:** one-line pitch + positioning line, screenshot placeholders, problem, gap, how it works (Mermaid diagram), accuracy table, honest validation status, business case summary, pilot offer, limitations, how to run, live demo link placeholder, and my links: linkedin.com/in/sandeep-gadakari/ · github.com/sandeepgadakari2000

## 10. Repo structure

```
coolscore/
├── CLAUDE.md
├── CoolScore_PROJECT_BRIEF.md
├── PROGRESS.md
├── README.md
├── requirements.txt
├── Makefile
├── config/            # assumptions.yaml, settings.yaml, communities.yaml, archetypes.yaml
├── data/              # raw/ (weather cache), simulated/, real_bills/, demo/
├── src/coolscore/
│   ├── weather/       # fetch + cache, solar on facades
│   ├── physics/       # 5R1C engine, archetypes, schedules
│   ├── billing/       # district cooling, DEWA, chiller-free, service charges
│   ├── simulate/      # scenario sampling, batch runs
│   ├── model/         # surrogate, quantiles, explanations, CoolScore bands
│   ├── validation/    # real-bill checks, calibration
│   └── assistant/     # listing parser, explanations, templates
├── api/               # FastAPI service
├── app/               # Streamlit Home.py + pages/
├── docs/
└── tests/
```

## 11. Phases (stop after each one)

- **Phase 0 — Plan + validation kit:** read this brief. If you have web access, run a quick competitive check for any tool that predicts unit-level cooling cost in Dubai/UAE or elsewhere, with links. Propose the architecture, data schemas, archetypes, scenario ranges, assumptions I must verify, and top risks. Create `CLAUDE.md`, `PROGRESS.md` and the skeleton. **Write the user-research kit first** so I can start interviews while you build.
- **Phase 1 — Weather + sun:** fetch and cache, facade irradiance, sanity plots.
- **Phase 2 — Physics engine:** single unit first, then vectorized; invariant tests; orientation effect checked against published studies.
- **Phase 3 — Billing engine:** all systems, with researched assumptions and sources.
- **Phase 4 — Simulation + model:** scenario dataset, surrogate, quantiles, explanations, CoolScore bands, model card.
- **Phase 5 — App core:** Check a Unit, Compare Units, Investor View, Methodology.
- **Phase 6 — Developer View, Listing Badge Demo, API.**
- **Phase 7 — AI layer:** listing parser, explanations, no-key fallback.
- **Phase 8 — Business layer:** real-bill validation kit, all documents in Section 8, Business Case page.
- **Phase 9 — Ship:** tests to 25+, README, Streamlit Community Cloud prep (secrets, demo artifacts under 50 MB), final check against Section 12.

## 12. Definition of done

- Paste a listing (or fill the form) → result in under 3 seconds; the form path works with no API key.
- Every AED figure shows its formula, inputs and range.
- Simulated data is clearly labelled; no fabricated tariffs, quotes, bills or competitor claims anywhere.
- Surrogate accuracy and physics sanity checks are documented.
- The validation report runs automatically when real bills are added.
- The README tells the whole story in 60 seconds, and all tests pass.

## 13. What I'll handle myself (don't attempt these)

- Interviews with Dubai tenants, brokers, investors and developers, and adding their real quotes
- Collecting anonymized real cooling bills for validation
- Verifying every tariff and building assumption marked `verify: true`
- Native-speaker review if Arabic is added, recording the demo, and deploying with my own accounts
