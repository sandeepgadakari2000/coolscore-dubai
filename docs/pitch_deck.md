---
marp: true
theme: default
paginate: true
title: CoolScore Dubai
---

<!-- Export: npx @marp-team/marp-cli docs/pitch_deck.md --pdf  (Marp is not installed in this repo) -->

# CoolScore Dubai
### Know what a Dubai apartment will cost to cool, before you sign

Sandeep Gadakari · Civil engineer + MBA (Finance & Analytics) · Duke AI Product Management

*All figures are simulated estimates unless marked otherwise.*

---

## 1. Problem

- Cooling is one of the biggest living costs in Dubai, and listings show rent only.
- It varies by unit: facing, floor, glass, shading, building age, cooling contract.
- Simulated 1-bed (800 sq ft, Business Bay, 2005–14 tower, west-facing, lots of glass, district cooling):
  **AED 5,400–8,400 a year**, of which
  **~46 % is a fixed capacity charge** paid even with the AC off.
- Tenants learn this from their first summer bill. Brokers answer "how much is the chiller?" by rule of thumb.

---

## 2. The gap

| Today | Works when? | Unit-specific? |
|---|---|---|
| Tariff and appliance calculators (need RT, ton-hours or AC tonnage) | After you move in | No |
| Provider calculators and apps | Existing customers | No |
| Guides (averages by bedroom count) | Any time | No |
| Project investment scores | Before buying | No (whole project) |

**CoolScore predicts a specific unit's cooling cost before you sign**, using building physics and Dubai's tariffs.
Abroad the pattern is proven (UK EPC cost estimates, a US portal); in Dubai it doesn't exist.

---

## 3. Product (live demo)

- Paste a listing → **CoolScore A–E**, summer and winter monthly range, true monthly cost (rent + cooling + housing fee).
- Drivers in AED ("built 2005–14 vs 2022+: +AED 1,100/yr"; "west-facing: +AED 260/yr").
- What-if: floor, facing, AC temperature, chiller-free.
- Compare units · Investor net yield · Developer facade heatmap · Listing badge · API.

[screenshot placeholder: Check a Unit result card]

---

## 4. Proof

- **Physics:** ISO 13790 hourly model on 2023–25 Dubai weather, corrected to airport observations
  (2025 holdout RMSE 2.4 → 1.3 °C); envelopes from Dubai's own rules (Al Sa'fat).
- **Surrogate:** fidelity R² **0.996**; listing-only R² **0.94**, MAPE 17 %; P10–P90 coverage **80 %** (calibrated).
- **Sanity:** typical 1-bed and 2-bed bills fall inside a published rough band.
- **Real bills:** collection kit and automatic validation report in place, **not yet validated**. That is the
  pilot's first deliverable.

---

## 5. Business model

- **Now:** brokerage seats (AED 149/agent/month, assumption) → **scale:** portal API (AED 1.50/scored listing/month,
  assumption) → developer design reports (AED 35k/project, assumption) → consumer score free.
- Scoring costs ~AED 0 per listing; AI parsing ~AED 0.02.
- Default 12-month plan: revenue ≈ AED 353k, break-even month 9 (founder unpaid; all inputs adjustable).

---

## 6. The ask: a 90-day pilot

- One brokerage, 60–120 active listings, badge vs matched controls.
- Measure enquiries per listing, lead quality, days to let, agent trust; collect 45+ anonymised bill-months.
- Pilot fee AED 15,000 (waivable for data and a case study).
- **Who should I talk to in your leasing team?**

sandeep · linkedin.com/in/sandeep-gadakari · github.com/sandeepgadakari2000
