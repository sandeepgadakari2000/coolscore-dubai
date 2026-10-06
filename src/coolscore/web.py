"""Payloads for the web app (Vercel functions + static pages): the same numbers the Streamlit pages show,
built without Streamlit so they can run in a small serverless function.

Every function takes plain dicts and returns JSON-ready dicts. The logic is lifted from ``app/ui.py`` and
the pages; keep the two in step (tests compare them on worked examples).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache

from coolscore import config
from coolscore.billing.engine import true_monthly_cost
from coolscore.model import predict
from coolscore.weather import climate, dataset

SCORE_COLORS = {"A": "#0a8f3c", "B": "#5aa83a", "C": "#c99400", "D": "#e07040", "E": "#c93636"}
SCORE_WORDS = {"A": "very low", "B": "low", "C": "typical", "D": "high", "E": "very high"}
ERA_LABELS = {"before_2005": "Before 2005", "2005_2014": "2005–2014", "2015_2021": "2015–2021", "2022_plus": "2022 or later"}
SYSTEM_LABELS = {"district_cooling": "District cooling (chiller company)", "building_central_plant": "Building's own chiller plant",
                 "dewa_split_ac": "Split AC on the DEWA bill", "dewa_central_ac": "Central/ducted AC on DEWA"}
PAYER_LABELS = {"tenant": "Tenant pays cooling", "landlord_chiller_free": "Chiller-free (landlord pays)",
                "service_charge": "Included in service charges"}
GLASS_LABELS = {"low": "Little glass", "medium": "Average windows", "high": "Lots of glass", "floor_to_ceiling": "Floor-to-ceiling glass"}
BALCONY_LABELS = {"none": "No balcony", "small": "Small balcony (~1.3 m)", "deep": "Deep balcony (2 m+)"}
OBSTRUCTION_LABELS = {"open": "Open view", "partial": "Some towers nearby", "heavy": "Close neighbouring towers"}
OCCUPANCY_LABELS = {"away_daytime": "Out during the day", "home_daytime": "Home during the day"}
SIMPLE_FACINGS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
FACING_OPTIONS = SIMPLE_FACINGS + [f"{a}+{b}" for a, b in [("N", "E"), ("E", "S"), ("S", "W"), ("W", "N"),
                                                            ("NE", "SE"), ("SE", "SW"), ("SW", "NW"), ("NW", "NE")]]
MONTHS = climate.MONTHS
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
PAYER_SHORT = {"tenant": "you pay", "landlord_chiller_free": "you pay · fans", "service_charge": "you pay · fans"}
EXAMPLE = ("Bright 1 bedroom in Business Bay with full canal view. 812 sq ft on the 23rd floor of a 45-storey "
           "tower, completed 2016. West-facing living room with floor-to-ceiling windows and a small balcony. "
           "District cooling, chiller not included. AED 95,000 per year, 4 cheques.")


def aed(x: float) -> str:
    return f"AED {x:,.0f}"


def aed_range(r) -> str:
    return f"AED {r.p10:,.0f}–{r.p90:,.0f}"


# ---------- reference data for the forms ----------

@lru_cache(maxsize=1)
def meta() -> dict:
    from coolscore.assistant import direction

    s = config.settings()["app"]
    return {
        "communities": sorted(config.communities()["communities"]),
        "labels": {"era_band": ERA_LABELS, "system": SYSTEM_LABELS, "payer": PAYER_LABELS, "glass": GLASS_LABELS,
                   "balcony": BALCONY_LABELS, "obstruction": OBSTRUCTION_LABELS, "occupancy": OCCUPANCY_LABELS},
        "facings": FACING_OPTIONS, "months": MONTHS, "month_names": MONTH_NAMES,
        "score_colors": SCORE_COLORS, "score_words": SCORE_WORDS, "score_cuts": predict.load_artifact()["score_cuts_aed_per_sqft"],
        "view_phrases": list(direction.VIEW_PHRASES), "example": EXAMPLE,
        "disclaimer": s["disclaimer"], "simulated": s["simulated_label"],
    }


def _clean(listing: dict) -> dict:
    """Drop money fields the model doesn't take and blank optional values."""
    return {k: v for k, v in listing.items() if k not in ("annual_rent_aed", "price_aed") and v not in (None, "")}


def run_estimate(listing: dict):
    return predict.estimate(_clean(listing))


def month_ranges(est) -> list[list[float]]:
    """P10/P50/P90 per month: Aug and Jan from the model's monthly quantiles, other months scale the typical shape."""
    a = est.annual
    lo, hi = (a.p10 / a.p50, a.p90 / a.p50) if a.p50 else (1.0, 1.0)
    out = [[p * lo, p, p * hi] for p in est.monthly_p50]
    out[7] = [est.summer_month.p10, est.summer_month.p50, est.summer_month.p90]
    out[0] = [est.winter_month.p10, est.winter_month.p50, est.winter_month.p90]
    return [[round(v) for v in m] for m in out]


def heat_color(tmax: float) -> str:
    """Month bar colour from its measured average high: cool sky blue → sand gold → coral."""
    t = min(max((tmax - 24) / 18, 0), 1)
    stops = [(124, 196, 255), (245, 185, 66), (255, 107, 61)]
    a, b, k = (stops[0], stops[1], t * 2) if t < .5 else (stops[1], stops[2], (t - .5) * 2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(a, b))


def stage_args(est, listing: dict, month: int, mode: str = "live", message: str | None = None) -> dict:
    """Everything the climate scene component needs (same shape as the Streamlit component's args)."""
    community = listing["community"]
    site = dataset.weather_site_for(community)
    unit = {"facing": str(listing["facing"]).upper().split("+"), "floor": int(listing["floor"]),
            "total_floors": int(max(int(listing["total_floors"]), int(listing["floor"]))),
            "glass": listing.get("glass") or "medium", "balcony": listing.get("balcony") or "none",
            "obstruction": listing.get("obstruction") or "partial", "setpoint": float(listing.get("setpoint_c") or 24.0)}
    result = None
    if est is not None:
        rent = listing.get("annual_rent_aed")
        result = {"score": est.score, "colors": SCORE_COLORS, "monthly_p50": [round(x) for x in est.monthly_p50],
                  "month_ranges": month_ranges(est),
                  "annual": [round(est.annual.p10), round(est.annual.p50), round(est.annual.p90)],
                  "true_cost": round(true_monthly_cost(rent, est.annual.p50 / 12)["total"]) if rent else None,
                  "payer_short": PAYER_SHORT[est.listing["payer"]]}
    return {"mode": mode, "month": int(month), "site": site, "community": community,
            "zone": config.communities()["communities"].get(community, "central"),
            "months": climate.load()["sites"][site], "unit": unit, "result": result, "message": message}


def how_calculated(est, rent: float | None = None) -> list[str]:
    out = [est.formula,
           "Model: gradient-boosted quantile models trained on 40,000 simulated units (hourly building physics on "
           "2023–25 Dubai weather + published tariffs). Inputs used: "
           f"{'listing facts + your household details' if est.variant == 'detailed' else 'listing facts only'}.",
           "Monthly figures: August and January are the model's own monthly P10–P90; other months scale the typical "
           "monthly shape by the annual range. The scene plays a typical day of measured weather for that month "
           "(2023–25 hourly data corrected to Dubai airport observations); 'sun on your windows' is pvlib facade sun "
           "on your facing, before balcony shade."]
    if est.listing["system"] == "district_cooling":
        payer = {"tenant": "you pay it", "landlord_chiller_free": "the landlord pays it (chiller-free)",
                 "service_charge": "the owner pays it through the service charge"}[est.listing["payer"]]
        out.append(f"Contracted capacity estimate ≈ {est.contracted_rt_estimate:.1f} RT (from size; real allocations "
                   f"vary) → fixed capacity charge ≈ {aed(est.capacity_aed_per_year)} a year incl. VAT, payable even "
                   f"with the AC off; {payer}.")
    out.append(f"CoolScore uses a standard household (bedrooms + 1 people, out by day, 24 °C) and a standard "
               f"district-cooling tariff so units compare fairly: {est.intensity_aed_per_sqft:.2f} AED per sq ft per "
               "year. Grade cut-offs (AED/sq ft/yr): " + ", ".join(f"{l} ≤ {c:.2f}" for l, c in zip("ABCD", est.score_cuts))
               + ", E above.")
    if rent:
        tc = true_monthly_cost(rent, est.annual.p50 / 12)
        out.append(f"True monthly cost = rent {aed(tc['rent'])} + cooling {aed(tc['cooling'])} (typical, yearly "
                   f"average) + housing fee {aed(tc['housing_fee'])} (5% of rent, collected on the DEWA bill).")
    return out


def estimate_payload(listing: dict, month: int = 7) -> dict:
    """Check a Unit: the estimate, the scene's args, the monthly chart, drivers, words and the working."""
    from coolscore.assistant import explain

    est = run_estimate(listing)
    rent = listing.get("annual_rent_aed") or None
    full = est.listing
    months = climate.site_months(full["community"])
    tc = true_monthly_cost(rent, est.annual.p50 / 12) if rent else None
    return {
        "estimate": {k: v for k, v in est.to_dict().items() if k != "listing"},
        "listing": full, "score_word": SCORE_WORDS[est.score], "score_color": SCORE_COLORS[est.score],
        "month_ranges": month_ranges(est),
        "month_colors": [heat_color(m["tmax"]) for m in months], "month_tmax": [m["tmax"] for m in months],
        "true_cost": tc, "stage": stage_args(est, {**listing, **full}, month),
        "drivers": [d for d in est.drivers if abs(d["aed_per_year"]) >= 1][:6],
        "plain": explain.explain(est, rent), "questions": explain.questions_for_agent(est),
        "how": how_calculated(est, rent), "notes": est.notes, "assumed": est.assumed,
    }


@lru_cache(maxsize=256)
def _heat_budget(spec_items: tuple, month: int) -> dict:
    from coolscore.physics.breakdown import ListingSpec, heat_budget

    return heat_budget(ListingSpec(**dict(spec_items)), month)


def heat_payload(listing: dict, month: int = 7) -> dict:
    """The heat X-ray component's args: the physics heat budget for the month, priced with the estimate."""
    from coolscore.physics.breakdown import LABELS, SOURCES, spec_from_listing

    est = run_estimate(listing)
    full = est.listing
    spec = spec_from_listing(full)
    b = _heat_budget(tuple(sorted(asdict(spec).items())), month)
    total = b["total_kwh"]
    month_p50 = month_ranges(est)[month][1]
    tenant = full["payer"] == "tenant"
    fixed = est.capacity_aed_per_year / 12 if tenant and full["system"] == "district_cooling" else 0.0
    variable = max(month_p50 - fixed, 0.0)
    sources = [{"key": k, "label": LABELS[k], "kwh": b["kwh"][k],
                "aed": round(variable * b["kwh"][k] / total) if tenant and total > 0 else None} for k in SOURCES]
    m = climate.site_months(full["community"])[month]
    note = None if tenant else f"Your landlord pays to remove this heat (≈ {aed(est.landlord_annual_p50)} a year)"
    return {"month_name": MONTH_NAMES[month], "sources": sources, "total_kwh": total,
            "latent_share": b["latent_share"], "design_kw": b["design_kw"],
            "people_equivalent": b["people_equivalent"], "month_aed": round(month_p50) if tenant else None,
            "fixed_aed": round(fixed), "payer_note": note, "setpoint": int(round(float(full.get("setpoint_c") or 24))),
            "outside_c": m["tmax"], "outside_rh": m["rh"],
            "unit": {"glass": full["glass"], "balcony": full["balcony"], "corner": "+" in str(full["facing"]),
                     "top_floor": int(full["floor"]) == int(full["total_floors"]),
                     "people": int(full.get("household_size") or int(full["bedrooms"]) + 1)}}


def _shifted(card, alt, base) -> dict:
    return {q: max(getattr(card, q) + getattr(alt, q) - getattr(base, q), 0.0) for q in ("p10", "p50", "p90")}


def whatif_payload(listing: dict, change: dict) -> dict:
    """One change applied to the unit through the household-detail model; the difference shifts the card."""
    est = run_estimate(listing)
    beds = int(listing["bedrooms"])
    base = {**listing}
    for k, v in (("setpoint_c", 24.0), ("household_size", beds + 1), ("occupancy", "away_daytime")):
        if not base.get(k):
            base[k] = v
    payer = listing.get("payer") or "tenant"
    if "chiller_free" in change:
        payer = "landlord_chiller_free" if change["chiller_free"] else ("tenant" if payer == "landlord_chiller_free" else payer)
    alt = {**base, **{k: v for k, v in change.items() if k in ("floor", "facing", "setpoint_c")}, "payer": payer}
    b, a = run_estimate(base), run_estimate(alt)
    annual = _shifted(est.annual, a.annual, b.annual)
    return {"annual": annual, "summer": _shifted(est.summer_month, a.summer_month, b.summer_month),
            "delta": annual["p50"] - est.annual.p50, "score": a.score, "score_color": SCORE_COLORS[a.score]}


def parse_payload(text: str) -> dict:
    from coolscore.assistant import parser

    r = parser.parse_listing(text)
    return {"method": r.method, "missing": r.missing, "defaults": r.form_defaults(),
            "fields": [{"field": k, "value": None if v.value is None else v.value, "status": v.status,
                        "evidence": v.evidence or ""} for k, v in r.fields.items()]}


def direction_payload(community: str, view: str) -> dict:
    from coolscore.assistant import direction

    hint = direction.suggest(community, view)
    return {"facing": hint.facing, "reason": hint.reason} if hint else {"facing": None, "reason": None}


def compare_payload(listings: list[dict]) -> dict:
    rows = []
    for i, listing in enumerate(listings):
        est = run_estimate(listing)
        rent = listing.get("annual_rent_aed") or 0.0
        tc = true_monthly_cost(rent, est.annual.p50 / 12)
        rows.append({"unit": f"Unit {i + 1}", "score": est.score, "score_color": SCORE_COLORS[est.score],
                     "rent": tc["rent"], "cooling": tc["cooling"], "housing_fee": tc["housing_fee"], "total": tc["total"],
                     "annual": asdict(est.annual), "formula": est.formula})
    verdict = None
    if all(listing.get("annual_rent_aed") for listing in listings):
        cheapest_rent = min(range(len(rows)), key=lambda i: rows[i]["rent"])
        cheapest_true = min(range(len(rows)), key=lambda i: rows[i]["total"])
        verdict = {"cheapest_rent": cheapest_rent, "cheapest_true": cheapest_true,
                   "gap": rows[cheapest_rent]["total"] - rows[cheapest_true]["total"]}
    return {"rows": rows, "verdict": verdict}


def investor_payload(listing: dict, price: float, rent: float, sc_rate: float, other: float) -> dict:
    est = run_estimate(listing)
    tenant_pays = run_estimate({**listing, "payer": "tenant"})
    free = run_estimate({**listing, "payer": "landlord_chiller_free"})
    lc = free.landlord_annual
    service = sc_rate * float(listing["size_sqft"])
    base_costs = service + other
    return {
        "gross": rent / price, "net_tenant": (rent - base_costs) / price,
        "net_free_p50": (rent - base_costs - lc.p50) / price, "net_free_p90": (rent - base_costs - lc.p90) / price,
        "landlord_cooling": asdict(lc), "tenant_cooling": asdict(tenant_pays.annual), "service": service,
        "dewa": listing.get("system") in ("dewa_split_ac", "dewa_central_ac"),
        "service_charge_payer": listing.get("payer") == "service_charge", "formula": est.formula,
    }


def badge_payload(listing: dict) -> dict:
    est = run_estimate(listing)
    return {"score": est.score, "score_color": SCORE_COLORS[est.score], "summer": asdict(est.summer_month),
            "annual": asdict(est.annual), "intensity": est.intensity_aed_per_sqft, "cuts": est.score_cuts,
            "formula": est.formula}


@lru_cache(maxsize=24)
def _tower(design: tuple):
    from coolscore.developer import TowerDesign, simulate_tower

    return simulate_tower(TowerDesign(**dict(design)))


def developer_payload(community: str, era: str, floors: int, obstruction: str, wwr: float, shgc: float, depth: float) -> dict:
    from coolscore.developer import compare
    from coolscore.physics.params import ORIENTATIONS

    base = dict(community=community, era_band=era, floors=int(floors), obstruction=obstruction, glass="high")
    ref = _tower(tuple(sorted({**base, "wwr": 0.6, "shgc": 0.25, "balcony_depth_m": 0.0}.items())))
    df = _tower(tuple(sorted({**base, "wwr": float(wwr), "shgc": float(shgc), "balcony_depth_m": float(depth)}.items())))
    grid = {}
    for r in df.itertuples():
        grid.setdefault(int(r.floor), {})[r.facing] = {"score": r.score, "aed": round(float(r.annual_aed)),
                                                      "intensity": round(float(r.intensity), 3)}
    return {"facings": list(ORIENTATIONS), "floors": sorted(grid, reverse=True), "grid": grid,
            "impact": compare(ref, df), "colors": SCORE_COLORS}


def business_payload(overrides: dict | None = None) -> dict:
    from coolscore import business

    b = business.BusinessInputs.defaults()
    for section in ("pricing", "plan", "costs"):
        for k, v in (overrides or {}).get(section, {}).items():
            if k in getattr(b, section):
                getattr(b, section)[k] = type(getattr(b, section)[k])(v)
    df = business.pnl(b)
    return {"inputs": {"pricing": b.pricing, "plan": b.plan, "costs": b.costs},
            "months": json.loads(df.to_json(orient="records")), "break_even": business.break_even_month(df),
            "unit_economics": business.unit_economics(b)}


def methodology_payload() -> dict:
    from coolscore import assumptions_doc
    from coolscore.validation import report as validation

    metrics = json.loads((config.path("demo") / "model_metrics.json").read_text(encoding="utf-8"))
    status = validation.run(write=False)
    reg = [{"path": r["path"], "value": json.dumps(r["value"])[:80], "unit": r["unit"], "kind": r["kind"],
            "verify": bool(r["verify"]), "source": r["source"] or ""} for r in assumptions_doc.register()]
    return {"metrics": metrics, "validation": json.loads(json.dumps(status, default=float)), "register": reg}
