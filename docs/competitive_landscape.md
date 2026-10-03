# Competitive landscape

**Status:** Phase 0 quick check, 2026-10-03. English-language web search only; app stores, Arabic-language sources and tools inside portals or brokerages were not searched.
**Verification key:** **Opened** = I read the page itself. **Snippet** = taken from search-result text only. Re-check snippets before quoting them anywhere public.

## Bottom line

- **No direct competitor found:** nothing in Dubai or the UAE predicts a *specific unit's* cooling cost from listing-level facts (facing, floor, glass, shading, building era, cooling system) *before* the rent or buy decision.
- Every Dubai tool found is a **tariff calculator**. You must already know your contracted capacity (RT), your metered ton-hours, or your AC tonnage and hours. That information comes from a bill, so these tools work after you move in.
- **Closest overlap (flagged):** one tariff calculator offers a manual "AC load factor" preset that includes a "Hot-facing/high usage" option. It's a user-chosen multiplier, not a prediction. Still, it shows that others see facing as a cost driver.
- **The pattern is proven elsewhere:** listing-level energy-cost estimates exist in the UK (EPCs, mandatory before marketing a rental) and the US (Redfin, via a partner). One US standalone provider (UtilityScore) is listed as inactive. That's a warning about standalone consumer economics, and it points the business model towards B2B (see `business_model.md`, Phase 8).

## 1. Dubai/UAE cooling-cost calculators (tariff or appliance based)

| Tool | What it needs from the user | Uses facing / floor / glass? | Pre-signing for a specific unit? | Source | Check |
|---|---|---|---|---|---|
| Rent Increase UAE: Chiller Cost Calculator Dubai | Unit type, provider, **allocated RT**, AED/RTh, AED/RT/yr, **daily AC hours**, load-factor preset (4 options incl. "Hot-facing"), fees, VAT | Only via the manual preset | No: RT and hours come from the contract or bill | [link](https://rentincreaseuae.com/chiller-cost-calculator-dubai/) | Opened |
| Expat Calculator: Dubai Cooling Charges Calculator | Property type, **cooling capacity (RT)**, **monthly use (TRh)**, rates, fees, VAT | No | No | [link](https://expatcalc.com/dubai-cooling-charges-calculator/) | Opened |
| Utility Bill UAE: District Cooling Cost Calculator | Property type, built-up area, **contracted capacity (TR)**, **monthly RTh "from your cooling meter/bill"**, rates, VAT | No | No | [link](https://utilitybilluae.com/district-cooling-calculator/) | Opened |
| MyDewaBill: AC Consumption Calculator (independent, not DEWA) | **AC tonnage**, number of units, EER, **running hours**, duty cycle, slab rate, fuel surcharge, VAT | No (duty cycle only) | No | [link](https://mydewabill.com/ac-consumption-calculator/) | Opened |
| Empower (district cooling provider) online calculator and app | Positioned for **customers** to plan and monitor consumption; the app shows bills and consumption | Not known | No (customer-facing) | [press coverage](https://www.prwebme.com/customers-urged-use-empowers-online-calculator-help-plan-and-monitor-their-district-cooling), [app](https://apps.apple.com/ae/app/empower-energy-solutions/id6717020502) | Snippet. The provider charges page redirected; re-check in Phase 3 |
| AC sizing calculators (e.g., Barajeel AC) | Room size, orientation, ceiling height → BTU/tonnage | Orientation for **sizing**, not cost | No | [link](https://barajeelac.com/ac-size-calculator/) | Snippet |

## 2. Guides with average bills (by bedroom count)

| Source | What it offers | Check |
|---|---|---|
| dataHabibi: "true cost of renting" guide | A data company (building profiles, transactions); its guide gives a generic annual cooling budget range and tells readers to ask the landlord for capacity and consumption charges separately. **No per-unit estimate** | [Opened](https://datahabibi.ae/guides/true-cost-of-renting-in-dubai) |
| MyBayut / Property Finder / dubizzle blogs on district cooling providers | Explain charge types; quote tariff figures | [Bayut](https://www.bayut.com/mybayut/all-about-empower-dubai/), [Property Finder](https://www.propertyfinder.ae/blog/empower-dubai/) (Snippet) |
| Real Estate Club Dubai, Relo DXB, Citizen Zero, Sama Movers, Dubai Housing | Chiller-free versus chiller-paid comparisons with rough monthly and annual bands | Snippet. Ranges **disagree with each other**; usable only as rough sanity bands, with citations, in Phase 8 |
| Palm Observer: "best apartment orientation in Dubai" | Qualitative orientation advice ("test the 4pm sun") | Snippet (page returned 403) |

## 3. Portal features

| Feature | What it does | Check |
|---|---|---|
| "Chiller free" filter and landing pages (both major portals) | A **binary** filter: who pays, not how much the unit costs to cool | [Property Finder](https://www.propertyfinder.ae/en/ltp/chiller-free-apartments-for-rent-in-dubai), [Bayut](https://www.bayut.com/s/chiller-free-apartments-rent-dubai/) (Snippet) |
| Portal instant price/rent estimators | Valuation, not running costs | Not re-checked in this pass |

## 4. Project and investment scores

| Tool | Level | Cooling/energy? | Check |
|---|---|---|---|
| Oliva | Composite investment score for off-plan **projects** (price, yield, developer, area, risk, liquidity…) | Its own overview of Dubai scoring tools lists none that score cooling, energy or orientation | [Opened](https://joinoliva.com/en/learn/blog/property-scoring-tools-and-platforms-in-dubai). The source is a competitor's blog, so treat it as self-interested |
| REIDIN, DXBInteract and others (per the same article) | Valuations and transaction data | No | Same source |

## 5. Adjacent: sunlight tools (sun as an amenity, not a cost)

| Tool | What it does | Relevance | Check |
|---|---|---|---|
| Shadowmap Home | Global 3D sun and shadow simulation for home seekers; subscription | Sun-hours only, no AED. **Could add a cooling layer**: a partner or a future competitor | [Opened](https://shadowmap.org/solutions/shadowmap-home/home-seeker) |
| Redfin Sunscore (US), DawnScore, SunCheck | Sunlight scores for listings | US / generic; natural light framed as a positive | [Redfin](https://www.redfin.com/news/redfin-launches-sunscore-to-show-exactly-how-much-sunlight-homes-get/), [DawnScore](https://www.dawnscore.app/) (Snippet) |

Note the framing clash: in cold markets more sun is a selling point. In Dubai, west sun is a **cost**.

## 6. International precedents (the pattern works where it's adopted)

| Precedent | What it shows | Check |
|---|---|---|
| UK Energy Performance Certificate | A rating plus **estimated energy costs**; a valid EPC is needed before a rental can be marketed; portals display it | [Rightmove guide](https://www.rightmove.co.uk/guides/energy-efficiency/energy-performance-certificates/what-is-an-epc/) (Snippet) |
| Redfin energy cost estimates (US, 2023, with WattBuy) | A major portal added energy-cost estimates to listings | [Business Wire](https://www.businesswire.com/news/home/20230112005139/en/Redfin-Becomes-First-Real-Estate-Site-to-Add-Energy-Cost-Estimates-for-U.S.-Homes) (Snippet; page returned 403) |
| UtilityScore (YC S16) | An API estimating utility costs for 100M+ US homes; YC lists it as **inactive** | [YC](https://www.ycombinator.com/companies/utilityscore) (Snippet) |
| Automated efficiency models (AEMs) | Industry term for no-inspection efficiency scores; providers are mostly US | [Wikipedia](https://en.wikipedia.org/wiki/Automated_efficiency_model) (Opened) |
| US Home Energy Score | An LBNL study links higher scores to higher prices, and higher estimated bills to lower prices | [LBNL preprint](https://eta-publications.lbl.gov/sites/default/files/pigman_aceee_summer_study_2022_preprint.pdf) (Snippet) |

## 7. Regulation (opportunity and risk)

- **Al Sa'fat** (Dubai Municipality green building system) rates **buildings**, not units, and tenants don't see per-unit costs. Snippet; verify in Phase 2 when building the archetypes.
- Several sources *say* Dubai doesn't require an EPC-style disclosure for leases or resales, and that one may be coming. **Unverified.** If Dubai mandates energy labels, that's both validation and a possible official competitor. Track it.

## Our differentiation

1. **Before you sign:** inputs come from the listing or a viewing, not from a bill.
2. **Unit level:** facing, floor, glass, shading, corner/top floor, building era. Two units in the same tower get different answers.
3. **Dubai billing built in:** district cooling capacity + consumption + fuel surcharge + VAT, DEWA slabs as marginal cost, chiller-free and service-charge cases.
4. **Honest ranges:** P10–P90 from simulated hidden variation, calibrated against real bills as they arrive.
5. **B2B-ready:** an API and badge for portals and brokers, which plays to the UK and US lesson that distribution beats standalone apps.

## Open questions for the next check (Phase 8)

- App stores (UAE) and Arabic-language search.
- Whether any brokerage or portal runs an internal cooling estimate (ask brokers in interviews).
- Provider calculators: open Empower's calculator and the other providers' sites directly.
