# Assumptions register

*Generated from `config/assumptions.yaml` and `config/archetypes.yaml` by `python tasks.py assumptions`. Edit the YAML, not this file.*

Every real-world number CoolScore uses lives in those two files with a value, unit, source URL, the date it was checked, a `verify` flag and notes. Code reads them through `config.require()`, which refuses to run on a placeholder. Notes are shortened here; the YAML has them in full.

| Type | Meaning | Records |
|---|---|---|
| sourced | Taken from the cited source | 39 |
| MODELLING ASSUMPTION | No source gives this number; the cited source anchors it | 19 |
| PROPOSAL | CoolScore's own plan or price, not market data | 3 |
| PLACEHOLDER | Engineering estimate to replace with a measurement | 2 |
| not yet researched | `value: null`; nothing may use it | 3 |

**66 records, 61 still marked `verify: true`** (to be confirmed by Sandeep against the source).

## Verify first

These move the AED answer most and rest on the weakest evidence:

1. `billing.district_cooling.contracted_capacity_sqft_per_rt`: sets the fixed capacity charge, often the largest line on a district-cooling bill (secondary sources only).
2. `billing.district_cooling.*` tariffs, `billing.dewa.residential_electricity_slabs` and `billing.dewa.fuel_surcharge`: re-check on the provider pages before any demo (the fuel surcharge changes monthly).
3. `physics.infiltration_ach`, `physics.fresh_air_pretreated_share`, `physics.untreated_ventilation_fraction` and `physics.appliance_lighting_gain`: the biggest drivers of the latent (humidity) load.
4. Archetype envelope values (`archetypes.yaml`), especially the pre-2005 and 2005–2014 eras.
5. `business.*`: every price and plan number is a proposal to test in broker interviews.

## constants (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `rt_to_kw_thermal` | 3.516853 | kW thermal per refrigeration ton (so 1 RTh = 3.51… | sourced | no | 2026-10-03 | [link](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9) | Definition, not a tariff. NIST SP 811 Appendix B.9 lists ton of refrigeration (12 000 Btu_IT/h) = 3.516 853 E+03 W. |
| `air_volumetric_heat_capacity` | 1200 | J/(m3 K) | sourced | no | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | ISO 13790 Eq. 21: rho_a c_a = 1 200 J/(m3 K). |
| `latent_air_factor` | {"air_density_kg_m3": 1.2, "vapour_heat_j_kg": 2500000} | latent W = density x airflow (m3/s) x vapour_heat… | sourced | no | 2026-10-03 | [link](https://www.tagengineering.ca/wp-content/uploads/2015/01/1997-Fundamentals_28.pdf) | 1997 ASHRAE Fundamentals Ch. 28 Eq. 23: q_l = 60 x 0.075 x 1076 Q W = 4840 Q W (Btu/h, cfm); 0.075 lb/ft3 = 1.2 kg/m3 and 1076 Btu/lb = 2.50 MJ/kg (vapour at 7… |

## billing (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `vat_rate` | 0.05 | fraction of the bill (applied once, to the bill t… | sourced | yes | 2026-10-03 | [link](https://www.dewa.gov.ae/en/consumer/billing/slab-tariff) | DEWA slab-tariff page: '5% VAT is applicable on these tariffs'. Empower charges page: 'Each Charge/Service ... is subjected for VAT of 5%'. |
| `dewa.residential_electricity_slabs` | [{"upto_kwh": 2000, "aed_per_kwh": 0.23}, {"upto_kwh": 4000, "aed_per… | AED per kWh by monthly consumption slab (resident… | sourced | yes | 2026-10-03 | [link](https://www.dewa.gov.ae/en/consumer/billing/slab-tariff) | Read on DEWA's page (last updated 16 May 2026): 0-2000 kWh 0.230, 2001-4000 0.280, 4001-6000 0.320, 6001+ 0.380 AED/kWh. |
| `dewa.fuel_surcharge` | 0.06 | AED per kWh | sourced | yes | 2026-10-03 | [link](https://www.dewa.gov.ae/en/consumer/billing/slab-tariff) | 'Fuel Surcharge - October 2026: Electricity D 0.060/kWh'. Varies with fuel prices; re-check monthly. |
| `dewa.meter_service_charge` | {"type_1": 5, "type_2": 6, "type_3": 35} | AED per month (fixed; not part of the marginal co… | sourced | yes | 2026-10-03 | [link](https://www.dewa.gov.ae/en/consumer/billing/slab-tariff) | Shown only in the estimated DEWA share of the true monthly cost. |
| `dewa.housing_fee_rate` | 0.05 | fraction of annual rent, billed monthly through D… | sourced | yes | 2026-10-03 | [link](https://www.engelvoelkers.com/ae/en/resources/housing-fee-dubai) | Dubai Municipality housing fee, 5% of annual rent collected monthly on the DEWA bill (several guides agree; search snippets, no government page opened). Used o… |
| `dewa.other_household_kwh` | {"low": 100, "central": 200, "high": 300} | kWh per month (water heating, cooking etc., on to… | PLACEHOLDER | yes | — | — | PLACEHOLDER: no published Dubai breakdown found. Only positions the cooling kWh within DEWA's slabs (marginal pricing); it is never billed as cooling. |
| `district_cooling.consumption_charge` | 0.568 | AED per RTh (ton-hour) | sourced | yes | 2026-10-03 | [link](https://www.empower.ae/customer-care/charges-explanation/) | Empower charges page: 'at a rate of AED 0.568 fils per RT per hour' (reads as AED 0.568/RTh). Other providers may differ; the app lets users override with thei… |
| `district_cooling.capacity_charge` | 750 | AED per RT per year, billed monthly by days in mo… | sourced | yes | 2026-10-03 | [link](https://www.empower.ae/customer-care/charges-explanation/) | Empower: 'AED 750 per Refrigeration Ton (RT) per annum, billed monthly in advance, based on the number of days in the month'; example 6 RT x 750 = 4,500/yr; th… |
| `district_cooling.fuel_surcharge` | 0.075 | AED per RTh | sourced | yes | 2026-10-03 | [link](https://rsbdubai.gov.ae/media/baufmpnp/rd10-tariffs-v14.pdf) | RSB RD10 v1.3 (17-09-2025): fuel surcharge cap AED 0.075/TRh; consumption tariff cap 0.643/TRh 'inclusive of Fuel Surcharge' = 0.568 + 0.075. Empower passes DE… |
| `district_cooling.meter_admin_fee` | {"low": 16.67, "central": 16.67, "high": 30} | AED per month | sourced | yes | 2026-10-03 | [link](https://www.empower.ae/customer-care/charges-explanation/) | Empower meter maintenance AED 50 per 3 months or AED 30 per month depending on location; RSB RD10 caps third-party billing-services fees at AED 30/month. |
| `district_cooling.single_building_consumption_cap` | 0.8 | AED per RTh (no capacity charge allowed) | sourced | yes | 2026-10-03 | [link](https://rsbdubai.gov.ae/media/baufmpnp/rd10-tariffs-v14.pdf) | RD10: 'Consumption Tariff for Single Building District Cooling Systems' cap 0.80 AED/TRh plus fuel surcharge cap 0.075; 'No Capacity Charges are allowed to be… |
| `district_cooling.deposit_cap_months` | 8 | months of capacity charges (refundable deposit, m… | sourced | yes | 2026-10-03 | [link](https://rsbdubai.gov.ae/media/baufmpnp/rd10-tariffs-v14.pdf) | RD10: deposits 'Must not exceed 8 months of Capacity Charges unless otherwise approved'. Shown as a move-in cost note. |
| `district_cooling.contracted_capacity_sqft_per_rt` | {"low": 150, "central": 200, "high": 300} | sq ft of unit area per contracted RT | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://utilitybilluae.com/district-cooling-cost-uae/) | MODELLING ASSUMPTION, the most important one in billing. Secondary guides (search snippets) quote typical contracted loads of 2-4 RT for studios, 3-5 RT for 1-… |
| `equipment.split_ac_min_eer` | {"t1_35c": 9.5, "t3_46c": 6.6} | EER (Btu/h per W) at T1 (35 C) and T3 (46 C) rati… | sourced | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat Reference Table 502.01(2): air-cooled split systems < 65,000 Btu/h minimum 9.5 EER (T1, ARI 210/240) and 6.6 EER (T3, ISO 5151). COP = EER / 3.412. T… |
| `equipment.installed_efficiency_factor` | {"low": 0.7, "central": 0.85, "high": 1.0} | multiplier on the minimum-standard COP (age, main… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | MODELLING ASSUMPTION anchored on the Al Sa'fat minimum: installed, ageing units in older buildings may perform below the rated minimum. |
| `equipment.fcu_fan_power` | {"low": 18, "central": 25, "high": 40} | W of fan power per kW of installed cooling capaci… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://feta.co.uk/client/files/HEVAC/1734700807-HEVAC_POS_SFP_for_fan_coil_units_Iss2.pdf) | MODELLING ASSUMPTION: UK guidance limits fan-coil specific fan power to 0.3-0.5 W/(l/s) (FETA/HEVAC statement, Approved Document L, search snippets); times ~60… |

## physics (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `ground_albedo` | {"low": 0.12, "central": 0.2, "high": 0.4} | fraction (broadband ground reflectance) | sourced | yes | 2026-10-03 | [link](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_ground_diffuse.html) | pvlib docs: 'typically 0.1-0.4 for bare or vegetated ground'; pvlib SURFACE_ALBEDOS (citing PVsyst and Loutzenhiser et al. 2007, Solar Energy 81:254-267) lists… |
| `iso13790_constants` | {"h_is": 3.45, "lambda_at": 4.5, "h_ms": 9.1, "f_w": 0.9, "frame_frac… | h_is, h_ms, h_r W/m2K; delta_theta_er K; others d… | sourced | yes | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | ISO/FDIS 13790:2007 (approval draft of ISO 13790:2008). Eq. 9 h_is=3.45, a_t=4.5; 12.2.2 h_ms=9.1; 11.4.2 F_w=0.90 (non-scattering glazing); frame fraction 'fo… |
| `thermal_mass_class` | {"medium": {"am_per_af": 2.5, "cm_per_af": 165000}, "heavy": {"am_per… | Am in m2 per m2 floor; Cm in J/K per m2 floor | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | ISO/FDIS 13790:2007 Table 12, simple hourly method. Concrete-frame apartments are sampled between 'medium' and 'heavy' (furnishings and gypsum ceilings decoupl… |
| `external_surface_resistance` | 0.04 | m2K/W | sourced | yes | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | ISO 13790 Eq. 46-47 take R_se from ISO 6946; 0.04 m2K/W is the ISO 6946 value for normal exposure (ISO 6946 itself not opened). |
| `opaque_solar_absorptance` | {"low": 0.3, "central": 0.5, "high": 0.7} | fraction | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | MODELLING ASSUMPTION: light-to-medium facade finishes. ISO 13790 Eq. 46 defines how absorptance enters; it gives no default. |
| `window_shading_reduction` | {"low": 0.6, "central": 0.8, "high": 1.0} | multiplier on glazing g-value (internal blinds/cu… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | ISO 13790 Table G.2 gives reduction factors 0.20-0.95 for internal curtains/blinds when closed. Time-averaged residential use is a MODELLING ASSUMPTION (1.0 =… |
| `sc_to_shgc` | 0.87 | SHGC per unit shading coefficient | sourced | yes | 2026-10-03 | [link](https://www.witpress.com/Secure/elibrary/papers/SC20/SC20008FU1.pdf) | Rodriguez-Ubinas et al. 2020 (DEWA R&D; WIT Trans. Ecol. Env. 249, doi:10.2495/SC200081) Table 4 lists the Al Sa'fat SC limits as SHGC ~0.35/0.28/0.22, i.e. SH… |
| `infiltration_ach` | {"before_2005": {"low": 0.4, "central": 0.7, "high": 1.0}, "2005_2014… | air changes per hour (natural infiltration, annua… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | MODELLING ASSUMPTION. Anchor: Al Sa'fat 501.05 limits air leakage to 10 m3/h per m2 of envelope at 50 Pa (buildings >= 1 MW cooling) and 501.06 requires a leak… |
| `fresh_air_pretreated_share` | {"before_2005": 0.2, "2005_2014": 0.5, "2015_2021": 0.9, "2022_plus":… | probability that outdoor air is pre-treated centr… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat 501.03: new air-conditioned buildings must have a central ventilation system supplying fresh air, hence ~1.0 for recent stock. Shares for older bands… |
| `untreated_ventilation_fraction` | {"low": 0.25, "central": 0.5, "high": 0.75} | fraction of the ASHRAE 62.2 whole-dwelling rate e… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/62_2_2013_m_20151109.pdf) | How much of the ASHRAE 62.2 rate reaches the unit coil untreated (kitchen/bath exhaust make-up air) in buildings without central pre-treatment is a MODELLING A… |
| `ashrae_622_ventilation` | {"per_m2_floor_ls": 0.15, "per_person_ls": 3.5} | L/s; Qtot = per_m2 x A_floor + per_person x (bedr… | sourced | no | 2026-10-03 | [link](https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/62_2_2013_m_20151109.pdf) | ASHRAE 62.2 Eq. 4.1b (SI), read in the official addendum m PDF. Al Sa'fat 401.01 requires ASHRAE 62 compliance. |
| `indoor_humidity_target` | {"low": 0.45, "central": 0.5, "high": 0.55} | relative humidity fraction at the cooling setpoint | sourced | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat 501.03 indoor design condition: 24 C dry bulb, relative humidity 50 +/- 5%. |
| `people_gains` | {"awake_sensible_w": 72, "awake_latent_w": 45, "resting_sensible_w":… | W per person (adjusted adult male/female mix) | sourced | yes | 2026-10-03 | [link](https://www.tagengineering.ca/wp-content/uploads/2015/01/1997-Fundamentals_28.pdf) | 1997 ASHRAE Fundamentals Ch. 28 Table 3: 'Seated, very light work - offices, hotels, apartments' 245 Btu/h sensible, 155 Btu/h latent (72 W / 45 W); 'Seated at… |
| `appliance_lighting_gain` | {"low": 1.5, "central": 3.0, "high": 5.0, "profile_w_m2": {"07-17": 8… | W/m2 daily mean (appliances + lighting, sensible)… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sysecol2.ethz.ch/OptiControl/LiteratureOC/ISO_07_FDIS_13790_ApprovalDraft.pdf) | ISO 13790 Table G.7 (residential, occupants + appliances): living room + kitchen 8 W/m2 (07-17), 20 (17-23), 2 (23-07), mean 9; other rooms mean 2.7-3.8. The s… |
| `orientation_effect_literature` | — | percent cooling difference by orientation (publis… | not yet researched | yes | — | [link](https://doi.org/10.3390/buildings14040876) | Left null: paper could not be opened. Search snippet of 'Smarter Window Selection for Smarter Energy Consumption: The Case of the UAE' (Buildings 2024, 14(4) 8… |

## schedules (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `uae_weekend` | ["Saturday", "Sunday"] | weekend days (Friday afternoon off for the federa… | sourced | yes | 2026-10-03 | [link](https://www.aljazeera.com/economy/2021/12/7/uae-announces-changes-to-workweek-for-employees-of-govt-sector) | From 1 Jan 2022 the federal government moved to a Saturday-Sunday weekend with a Friday half day; private-sector adoption varied (search snippets of the announ… |
| `ramadan_dates` | {"2023": ["2023-03-23", "2023-04-20"], "2024": ["2024-03-11", "2024-0… | first and last day of Ramadan (inclusive) | sourced | yes | 2026-10-03 | [link](https://en.wikipedia.org/wiki/Ramadan) | 2024 and 2025 from Wikipedia's Umm al-Qura table (opened); 2023 from Al Arabiya's expected dates (search snippet). UAE moon-sighting can shift dates by a day.… |

## data_sources (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `open_meteo_terms` | {"endpoint": "https://archive-api.open-meteo.com/v1/archive", "model"… | licence summary | sourced | yes | 2026-10-03 | [link](https://open-meteo.com/en/terms) | Read 2026-10-03: free API is for non-commercial use only (<10,000 calls/day); data licensed CC BY 4.0 with attribution. Commercial use needs a paid plan. Attri… |
| `noaa_isd_observations` | {"stations": {"41194099999": "Dubai International", "41194599999": "A… | station list | sourced | no | 2026-10-03 | [link](https://www.ncei.noaa.gov/data/global-hourly/access/) | NOAA Integrated Surface Database hourly observations (US government open data), used only to bias-correct and validate model temperature and dew point. Station… |
| `weather_bias_correction` | {"method": "additive per month x hour", "vars": ["temp_c", "dewpoint_… | method | sourced | yes | 2026-10-03 | [link](https://www.ncei.noaa.gov/data/global-hourly/access/) | Assumption: the Dubai International correction also applies to the coastal (Marina) cell, which has no station. Holdout 2025 results in docs/evidence/weather.m… |
| `ghi_published_range` | — | kWh/m2/yr global horizontal irradiation | not yet researched | yes | — | [link](https://www.researchgate.net/publication/320076428_The_UAE_Solar_Atlas) | Left null because neither source could be opened. Sanity band only. Search snippets: UAE Solar Atlas reports 2100-2300 kWh/m2 GHI across the UAE; DEWA Shams Du… |

## sanity_bands (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `typical_monthly_bills_by_bedrooms` | {"0": [350, 450], "1": [450, 600], "2": [650, 850], "3": [900, 1200]} | AED per month, district cooling, tenant-paid (rou… | sourced | yes | 2026-10-03 | [link](https://utilitybilluae.com/district-cooling-cost-uae/) | Independent calculator site (no publication date): 'Studio AED 350-450, 1-bedroom AED 450-600, 2-bedroom AED 650-850, 3-bedroom AED 900-1,200'; it also quotes… |

## business (`assumptions.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `usd_to_aed` | 3.67 | AED per USD | sourced | yes | 2026-10-03 | [link](https://www.witpress.com/Secure/elibrary/papers/SC20/SC20008FU1.pdf) | Rodriguez-Ubinas et al. 2020 Table 2 note: '3.67 Dirhams = USD $1' (the dirham is pegged to the US dollar). |
| `llm_price_per_mtok_usd` | {"model": "claude-haiku-4-5", "input": 1.0, "output": 5.0} | USD per million tokens | sourced | yes | 2026-10-03 | [link](https://platform.claude.com/docs/en/about-claude/pricing) | Claude Haiku 4.5 list price from Anthropic's model table (cached 2026-09-25 in the Claude API reference). Used for the per-listing AI parsing cost. |
| `tokens_per_listing_parse` | {"input": 2000, "output": 600} | tokens per parsed listing (system prompt + listin… | PLACEHOLDER | yes | — | — | PLACEHOLDER: engineering estimate for a ~150-word listing; measure from response.usage once live. |
| `pricing` | {"broker_seat_aed_month": 149, "brokerage_min_seats": 10, "portal_aed… | AED | PROPOSAL | yes | — | — | PROPOSAL: CoolScore's own launch prices (not market data). Broker seat priced well below typical listing-portal subscription costs a brokerage already pays; va… |
| `plan_12m` | {"pilot_months": 3, "brokerages_month_4": 2, "new_brokerages_per_mont… | counts per month (12-month plan) | PROPOSAL | yes | — | — | PROPOSAL: a deliberately modest plan for a solo founder; every number is an input on the Business Case page. |
| `costs_month` | {"hosting_aed": 400, "tools_and_data_aed": 300, "legal_and_privacy_ae… | AED per month | PROPOSAL | yes | — | — | PROPOSAL: placeholder costs (founder unpaid in year 1; part-time sales from the first paid month). Replace with real quotes. |

## regulation_milestones (`archetypes.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `dm_thermal_insulation_rules` | 2003 | year issued | sourced | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat 101.03 revokes 'Administrative Resolution No. 66, of the year 2003, approving Regulations on the Technical Specifications for Thermal Insulation Syst… |
| `green_building_regulations_mandatory` | 2014 | year compulsory for all new buildings | sourced | yes | 2026-10-03 | [link](https://www.witpress.com/Secure/elibrary/papers/SC20/SC20008FU1.pdf) | Rodriguez-Ubinas et al. 2020 (DEWA R&D): DEWA and DM introduced the Green Building Regulations and Specifications in 2011, mandatory first for government build… |
| `al_safat_mandatory` | {"launched": 2016, "silver_mandatory": 2020} | year | sourced | yes | 2026-10-03 | [link](https://www.witpress.com/Secure/elibrary/papers/SC20/SC20008FU1.pdf) | Launch per Rodriguez-Ubinas et al. 2020. Silver Sa'fa mandatory for all buildings under Administrative Resolution 154 of 2020 (search snippet; resolution not o… |
| `permit_to_completion_lag` | — | years | not yet researched | yes | — | — | Not needed by the engine (bands are fixed); left as a placeholder until a source on Dubai tower delivery times is found. |

## glazing_code_limits (`archetypes.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `glazing_code_limits` | [{"wwr_max": 0.4, "u": 2.1, "sc": 0.4}, {"wwr_max": 0.6, "u": 1.9, "s… | u in W/m2K (summer U-value, max); sc = shading co… | sourced | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat 501.01 B (Bronze/Silver): WWR <= 40%: U 2.1, SC 0.4; 40-60%: U 1.9, SC 0.32; >= 60%: U 1.9, SC 0.25. Same values listed with a 2014 mandate year by R… |

## archetypes (`archetypes.yaml`)

| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |
|---|---|---|---|---|---|---|---|
| `A1.params.wall_u` | {"low": 1.4, "central": 1.65, "high": 2.2} | W/m2K | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.avestia.com/CSEE2017_Proceedings/files/paper/AWSPT/AWSPT_127.pdf) | Touqan, Taleb & Salameh 2017 (CSEE'17, doi:10.11159/awspt17.127): Dubai base-case 20 cm concrete block wall U = 1.65 W/m2K (uninsulated). Range around it is a… |
| `A1.params.roof_u` | {"low": 0.44, "central": 0.7, "high": 1.2} | W/m2K | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sciencedirect.com/science/article/abs/pii/S037877881100449X) | Friess et al. 2012 (Energy and Buildings 44:26-32), search snippet: 2001/2003 legislation set roofs to U = 0.44. Older roofs above that limit are a MODELLING A… |
| `A1.params.glazing_u` | {"low": 5.5, "central": 5.8, "high": 5.9} | W/m2K | sourced | yes | 2026-10-03 | [link](https://www.viridianglass.com/wp-content/uploads/2024/03/Viridian-Performance-Data-Single-Glazing.pdf) | Manufacturer data for 6 mm single tinted float glass: U 5.8 (grey, bronze), 5.5-5.7 for other single products. |
| `A1.params.glazing_shgc` | {"low": 0.36, "central": 0.58, "high": 0.66} | fraction | sourced | yes | 2026-10-03 | [link](https://www.viridianglass.com/wp-content/uploads/2024/03/Viridian-Performance-Data-Single-Glazing.pdf) | Same data: 6 mm grey 0.58, light grey 0.66, bronze 0.65, dark 'SuperGrey' 0.36. |
| `A2.params.wall_u` | {"low": 0.57, "central": 0.9, "high": 1.3} | W/m2K (effective, including thermal bridges) | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sciencedirect.com/science/article/abs/pii/S037877881100449X) | Friess et al. 2012 (snippet): the 2003 limit is U 0.57 met with insulated block, but the reinforced-concrete frame typically stays uninsulated and over half th… |
| `A2.params.roof_u` | {"low": 0.3, "central": 0.44, "high": 0.6} | W/m2K | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.sciencedirect.com/science/article/abs/pii/S037877881100449X) | 2003 roof limit 0.44 (Friess et al. 2012, snippet); spread is a MODELLING ASSUMPTION. |
| `A2.params.glazing_u` | {"low": 2.1, "central": 2.8, "high": 3.3} | W/m2K | sourced | yes | 2026-10-03 | [link](https://www.sciencedirect.com/science/article/abs/pii/S037877881100449X) | Friess et al. 2012 (snippet): 2003 rules capped glazing U at 3.28 for glazing-to-wall < 40% and 2.1 above 40%. |
| `A2.params.glazing_shgc` | {"low": 0.25, "central": 0.35, "high": 0.46} | fraction | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.viridianglass.com/wp-content/uploads/2024/03/Viridian-Performance-Data-Single-Glazing.pdf) | MODELLING ASSUMPTION for reflective/tinted coated glazing of the period, anchored on manufacturer data for coated tinted glass (SHGC 0.37-0.46) and the later A… |
| `A3.params.wall_u` | {"low": 0.57, "central": 0.75, "high": 1.0} | W/m2K (effective, including thermal bridges) | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.witpress.com/Secure/elibrary/papers/SC20/SC20008FU1.pdf) | Limit 0.57 (Rodriguez-Ubinas et al. 2020 Table 3). Thermal-bridge allowance above the limit is a MODELLING ASSUMPTION (Friess et al. 2012 describe uninsulated… |
| `A3.params.roof_u` | {"low": 0.25, "central": 0.3, "high": 0.3} | W/m2K | sourced | yes | 2026-10-03 | [link](https://www.witpress.com/Secure/elibrary/papers/SC20/SC20008FU1.pdf) | Roof limit 0.30 W/m2K. |
| `A3.params.glazing_compliance` | {"low": 0.8, "central": 0.95, "high": 1.1} | multiplier on the code SHGC limit for the unit's… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Code limits from glazing_code_limits. Values below 1 = better than code; above 1 = non-compliance. Spread is a MODELLING ASSUMPTION. |
| `A4.params.wall_u` | {"low": 0.45, "central": 0.57, "high": 0.65} | W/m2K (effective) | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat 501.01 A wall limit 0.57 (Silver); 501.02 requires thermal bridges to be eliminated or insulated, so the effective value sits near the limit. Spread… |
| `A4.params.roof_u` | {"low": 0.25, "central": 0.3, "high": 0.3} | W/m2K | sourced | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Al Sa'fat 501.01 A roof limit 0.3 W/m2K. |
| `A4.params.glazing_compliance` | {"low": 0.75, "central": 0.9, "high": 1.0} | multiplier on the code SHGC limit for the unit's… | MODELLING ASSUMPTION | yes | 2026-10-03 | [link](https://www.wkcgroup.com/wp-content/uploads/2023/04/Al-Safat-Dubai-Green-Building-Evaluation-System.pdf) | Compliance assumed (Silver mandatory, tested). Spread is a MODELLING ASSUMPTION. |
