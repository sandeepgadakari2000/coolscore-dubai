# PRD: CoolScore Dubai

**One line:** predict a specific Dubai apartment's cooling cost *before* someone rents or buys it.
**Owner:** Sandeep Gadakari · **Status:** MVP built (simulated); real-bill validation and user interviews in progress.

## 1. Problem

Cooling is one of the largest living costs in Dubai, and it varies a lot between units in the same tower:
facing, floor, glass, shading, building age, cooling system and contract. Listings show rent, not the cost of
living there. Tenants find out from their first summer bill. Brokers get asked "how much is the chiller?" and
answer from rules of thumb. Investors price chiller-free offers by feel.

Our own simulation shows how big the hidden part is. For an 800 sq ft 1-bed in a 2005–2014 district-cooled
Business Bay tower (west-facing, lots of glass, floor 15 of 30, tenant pays), cooling runs **AED 5,400–8,400 a year** (P10–P90), and **~46 % of that is a fixed capacity charge** that has
nothing to do with how the tenant behaves.

## 2. Gap (see `competitive_landscape.md`)

Existing Dubai tools are tariff or appliance calculators that need your contracted RT, your metered ton-hours or
your AC's tonnage. They only work **after** you move in. Guides give averages by bedroom count. Project scores rate
whole projects. Listing-level energy-cost estimates exist abroad (UK EPCs, a US portal), but not in Dubai and not
for district cooling.

## 3. Users and jobs to be done

| User | Job to be done | What CoolScore gives |
|---|---|---|
| Tenant | "Help me pick the flat that's actually cheaper to live in." | True monthly cost = rent + cooling + housing fee; A–E grade; drivers |
| Buyer / investor | "Tell me my net yield, and whether a chiller-free offer pays off." | Net yield after cooling and service charges; the rent premium chiller-free needs |
| Broker | "Answer 'how much is the AC?' with confidence and stand out." | Per-unit estimate with range and formula; badge for listings |
| Portal | "Help users filter by true cost." | API: score, range, drivers per listing |
| Developer | "Design and market lower-cooling-cost units." | Facade heatmap, AED impact of glass, glazing and shading |

## 4. MVP scope (built)

- Check a Unit (paste listing or form), Compare Units, Investor View, Developer View, Listing Badge demo,
  Business Case, Methodology & Validation (Streamlit, works on phones, no API key needed).
- FastAPI `/score`, `/compare`, `/health`.
- Physics (ISO 13790 hourly) → Dubai billing → 40,000-scenario surrogate with calibrated P10–P90 ranges.
- Optional Claude listing parser and explanations, with a guard against invented numbers.
- Real-bill collection kit, PII guard and an automatic validation report.

## 5. Out of scope (for now)

Scraping portals; real-time smart-meter data; villas and townhouses; non-Dubai emirates; heating; individual room
comfort; Arabic UI (later, only after native-speaker review); any claim of measured accuracy before real bills.

## 6. Success metrics

| Stage | Metric | Target |
|---|---|---|
| Discovery (now) | Interviews done per `user-research/hypotheses.md`; H1, H2, H5 pass | 10 tenants, 5 brokers |
| Credibility | Real bill-months collected; total-bill MAPE; share of months within ±20 % | 15 units × 3 months; MAPE ≤ 20 %; ≥ 60 % within ±20 % |
| Pilot (brokerage) | Enquiries per listing with badge vs without; lead quality; days to let; trust survey | see `gtm_and_pilot.md` |
| Product | Time to answer; share of estimates with no assumed fields | < 3 s (met); > 70 % |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Simulated, not measured | Range plus "simulated" label everywhere; bill kit; validation report on the Methodology page |
| Contracted capacity unknown (the biggest single line on district-cooling bills) | Explicit assumption; "ask the agent" prompt; bills record the RT |
| Landlords and brokers resist scores that make some units look worse | Opt-in pilot; "true cost" framing; fixes, not blame (`interview_prep.md` Q3) |
| Tariffs change | All tariffs in one register; re-bill and retrain in minutes |
| Weather-data licence for commercial use | Open-Meteo's free tier is non-commercial; switch to a paid plan or direct ERA5/IFS for commercial launch |
