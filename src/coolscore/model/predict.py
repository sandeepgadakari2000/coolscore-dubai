"""Fast estimates from the trained surrogate: ranges, CoolScore, drivers, formulas.

Used by the app, the API and the assistant. Everything runs offline from the
artifact in ``data/demo`` (no physics, no network), well under a second.
All AED values are SIMULATED estimates with a P10-P90 range.
"""

from __future__ import annotations

import lzma
import pickle
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from coolscore import config
from coolscore.model import features as F
from coolscore.weather import dataset

TARGETS = ("annual", "summer", "winter")
REQUIRED = ("community", "size_sqft", "bedrooms", "floor", "total_floors", "facing")
DEFAULTS = {  # used when a listing doesn't say; always reported back as "assumed"
    "era_band": "2005_2014", "glass": "medium", "balcony": "none", "obstruction": "partial",
    "system": "district_cooling", "payer": "tenant",
}
REFERENCE_LABELS = {
    "facing": ("N", "{v}-facing vs north-facing"),
    "glass": ("medium", "{v} glass vs medium glass"),
    "obstruction": ("open", "{v} shading from nearby towers vs an open view"),
    "balcony": ("none", "{v} balcony vs no balcony"),
    "era_band": ("2022_plus", "built {v} vs a 2022+ (Al Sa'fat) building"),
}


@lru_cache(maxsize=1)
def load_artifact(path: str | None = None) -> dict:
    p = Path(path) if path else config.path("demo") / "coolscore_model.pkl.xz"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing; run `python tasks.py simulate` and `python tasks.py train`")
    with lzma.open(p, "rb") as fh:
        return pickle.load(fh)


@dataclass
class Range:
    p10: float
    p50: float
    p90: float


@dataclass
class Estimate:
    """One unit's simulated cooling cost estimate (AED, tenant unless stated)."""

    listing: dict
    variant: str
    annual: Range
    summer_month: Range
    winter_month: Range
    monthly_p50: list[float]
    score: str
    intensity_aed_per_sqft: float
    score_cuts: list[float]
    drivers: list[dict]
    landlord_annual_p50: float
    landlord_annual: Range
    contracted_rt_estimate: float
    capacity_aed_per_year: float
    assumed: list[str]
    missing: list[str]
    formula: str
    simulated: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def normalise(listing: dict) -> tuple[dict, list[str], list[str]]:
    """Fill defaults; return (complete listing, assumed fields, missing required fields)."""
    out = {k: v for k, v in listing.items() if v is not None and v != ""}
    missing = [k for k in REQUIRED if k not in out]
    if missing:
        raise ValueError(f"missing required fields: {missing}")
    assumed = [k for k in DEFAULTS if k not in out]
    for k in assumed:
        out[k] = DEFAULTS[k]
    if out["system"] in ("dewa_split_ac", "dewa_central_ac"):
        out["payer"] = "tenant"
    if int(out["floor"]) > int(out["total_floors"]) or int(out["floor"]) < 1:
        raise ValueError("floor must be between 1 and total_floors")
    out["weather_site"] = dataset.weather_site_for(out["community"])
    details = [k for k in ("household_size", "occupancy", "setpoint_c") if k in out]
    if details:
        ref = config.settings()["simulation"]["score_reference"]
        for k, v in {"household_size": int(out["bedrooms"]) + 1, "occupancy": ref["occupancy"],
                     "setpoint_c": ref["setpoint_c"]}.items():
            if k not in out:
                out[k] = v
                assumed.append(k)
    return out, assumed, missing


def _predict(rows: list[dict], variant: str) -> dict[str, np.ndarray]:
    """{target: array (n_rows, 3)} of sorted P10/P50/P90 (AED)."""
    art = load_artifact()
    df = pd.DataFrame(rows)
    if variant == "listing":
        df = df.drop(columns=[c for c in ("household_size", "occupancy", "setpoint_c") if c in df])
    X = F.encode(df)[art["features"][variant]]
    out = {}
    qs = art["quantiles"]
    for t in TARGETS:
        logp = np.stack([art["models"][variant][t][q].predict(X) for q in qs], axis=1)
        delta = art.get("conformal_log_delta", {}).get(variant, {}).get(t, 0.0)
        logp[:, 0] -= delta   # conformal widening of P10/P90 (calibrated coverage)
        logp[:, -1] += delta
        out[t] = np.sort(np.clip(np.expm1(logp), 0.0, None), axis=1)
    return out


def _score(intensity: float, cuts: list[float], letters: list[str]) -> str:
    return letters[int(np.searchsorted(cuts, intensity, side="right"))]


def _formula(system: str, payer: str) -> str:
    dc = "billing.district_cooling."
    vat = config.require("billing.vat_rate")
    if system == "district_cooling":
        text = (f"District cooling = capacity (contracted RT × AED {config.require(dc + 'capacity_charge'):,.0f}/yr, "
                f"charged even with zero use) + consumption (RTh × AED {config.require(dc + 'consumption_charge')}) "
                f"+ fuel surcharge (RTh × AED {config.require(dc + 'fuel_surcharge')}) + meter fee, "
                f"plus fan-coil electricity on DEWA; {vat:.0%} VAT.")
    elif system == "building_central_plant":
        text = (f"Building chiller plant = consumption (RTh × up to AED {config.require(dc + 'single_building_consumption_cap')}) "
                f"+ fuel surcharge; no capacity charge (RSB rule); fan electricity on DEWA; {vat:.0%} VAT.")
    else:
        text = ("DEWA-billed AC = cooling energy ÷ AC efficiency (lower in extreme heat), priced at the DEWA slab "
                f"your household reaches + fuel surcharge; {vat:.0%} VAT.")
    if payer == "landlord_chiller_free":
        text += " Chiller-free: the landlord pays the cooling bill; you still pay the fan electricity."
    elif payer == "service_charge":
        text += " Cooling recovered through service charges: the owner pays it; you pay the fan electricity."
    return text + " RTh = simulated cooling energy ÷ 3.517 kWh. Range = P10–P90 over 40,000 simulated scenarios."


def estimate(listing: dict) -> Estimate:
    """Simulated cooling-cost estimate for one listing (dict of listing fields)."""
    full, assumed, missing = normalise(listing)
    art = load_artifact()
    variant = "detailed" if "setpoint_c" in full else "listing"
    ref_cfg = config.settings()["simulation"]["score_reference"]

    rows: list[dict] = [full]
    labels: list[str] = []
    for key, (ref_value, label) in REFERENCE_LABELS.items():
        if key == "facing" and str(full["facing"]).upper() == "N":
            continue
        if full.get(key) != ref_value:
            rows.append({**full, key: ref_value})
            nice = str(full[key]).replace("_", " ").replace("2005 2014", "2005–2014").replace(
                "2015 2021", "2015–2021").replace("before 2005", "before 2005")
            labels.append(label.format(v=nice))
    mid = max(1, round(int(full["total_floors"]) / 2))
    if int(full["floor"]) != mid:
        rows.append({**full, "floor": mid})
        top = " (top floor, roof above)" if int(full["floor"]) == int(full["total_floors"]) else ""
        labels.append(f"floor {full['floor']} of {full['total_floors']}{top} vs a mid floor")
    if variant == "detailed" and float(full["setpoint_c"]) != ref_cfg["setpoint_c"]:
        rows.append({**full, "setpoint_c": ref_cfg["setpoint_c"]})
        labels.append(f"AC set to {float(full['setpoint_c']):g} °C vs 24 °C")
    rows.append({**full, "payer": "tenant"})
    rows.append({**full, "payer": "landlord_chiller_free"})

    pred = _predict(rows, variant)
    ann = pred["annual"]
    drivers = sorted(
        ({"driver": lab, "aed_per_year": float(ann[0, 1] - ann[1 + i, 1])} for i, lab in enumerate(labels)),
        key=lambda d: -abs(d["aed_per_year"]))
    provider_billed = full["system"] in ("district_cooling", "building_central_plant")
    landlord_q = np.clip(ann[-2] - ann[-1], 0.0, None) if provider_billed else np.zeros(3)
    landlord = float(landlord_q[1])

    ref_row = {**full, "system": ref_cfg["system"], "payer": ref_cfg["payer"], "occupancy": ref_cfg["occupancy"],
               "setpoint_c": ref_cfg["setpoint_c"], "household_size": int(full["bedrooms"]) + 1}
    std = _predict([ref_row], "detailed")["annual"][0, 1]
    intensity = float(std / float(full["size_sqft"]))
    cuts = art["score_cuts_aed_per_sqft"]

    key = "|".join([full["system"], full["payer"], full["weather_site"]])
    shares = art["monthly_shares"].get(key) or [1 / 12] * 12
    monthly = [float(ann[0, 1] * s) for s in shares]

    sqft_per_rt = config.require("billing.district_cooling.contracted_capacity_sqft_per_rt")["central"]
    rt = float(full["size_sqft"]) / sqft_per_rt
    vat = config.require("billing.vat_rate")
    capacity = rt * config.require("billing.district_cooling.capacity_charge") * (1 + vat) \
        if full["system"] == "district_cooling" else 0.0
    notes = []
    if full["system"] == "district_cooling":
        notes.append("Ask the agent for the unit's contracted capacity (RT): it sets a fixed charge "
                     "payable even when the AC is off.")
    return Estimate(
        listing=full, variant=variant,
        annual=Range(*map(float, ann[0])), summer_month=Range(*map(float, pred["summer"][0])),
        winter_month=Range(*map(float, pred["winter"][0])), monthly_p50=monthly,
        score=_score(intensity, cuts, art["score_letters"]), intensity_aed_per_sqft=intensity, score_cuts=cuts,
        drivers=drivers, landlord_annual_p50=landlord, landlord_annual=Range(*map(float, np.sort(landlord_q))),
        contracted_rt_estimate=rt, capacity_aed_per_year=capacity,
        assumed=assumed, missing=missing, formula=_formula(full["system"], full["payer"]), notes=notes,
    )


def estimate_many(listings: list[dict]) -> list[Estimate]:
    return [estimate(listing) for listing in listings]
