"""Developer View engine: a fictional tower's facade, simulated with the physics engine directly.

Every floor × orientation is one typical unit (central hidden values, standard
household), billed under the reference district-cooling tariff so the colours
use the same CoolScore cut-offs as the rest of the app. Design levers override
glass ratio, glazing SHGC and balcony depth for the whole tower.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from coolscore.billing import engine as billing
from coolscore.model import predict
from coolscore.physics import engine
from coolscore.physics.params import ORIENTATIONS, ListingSpec, build_params, weather_site


@dataclass(frozen=True)
class TowerDesign:
    community: str = "Business Bay"
    era_band: str = "2022_plus"
    floors: int = 30
    size_sqft: float = 850.0
    bedrooms: int = 1
    glass: str = "high"
    obstruction: str = "partial"
    wwr: float | None = None            # overrides the glass category
    shgc: float | None = None           # overrides the code/archetype glazing
    balcony_depth_m: float | None = None
    year: int = 2024


def simulate_tower(d: TowerDesign) -> pd.DataFrame:
    """Annual simulated cooling (kWh_th and AED, reference tariff) per floor and orientation."""
    specs = [ListingSpec(community=d.community, era_band=d.era_band, size_sqft=d.size_sqft, bedrooms=d.bedrooms,
                         floor=f, total_floors=d.floors, facing=o, glass=d.glass,
                         balcony="small" if (d.balcony_depth_m or 0) > 0 else "none", obstruction=d.obstruction)
             for f in range(1, d.floors + 1) for o in ORIENTATIONS]
    p = build_params(specs)
    changes = {}
    if d.wwr is not None:
        changes["wwr"] = d.wwr
    if d.shgc is not None:
        changes["win_shgc"] = d.shgc
    if d.balcony_depth_m is not None:
        changes["balcony_depth_m"] = d.balcony_depth_m
        changes["balcony_frac"] = 1.0 if d.balcony_depth_m > 0 else 0.0
    if changes:
        p = p.replace(**changes)
    phys = engine.run_site_year(p, weather_site(specs[0]), d.year)
    bp = billing.billing_params(["district_cooling"] * p.n, ["tenant"] * p.n, [d.size_sqft] * p.n)
    bill = billing.compute(phys, bp, d.year)
    art = predict.load_artifact()
    annual = bill.annual("tenant_total")
    intensity = annual / d.size_sqft
    letters = [predict._score(x, art["score_cuts_aed_per_sqft"], art["score_letters"]) for x in intensity]
    return pd.DataFrame({
        "floor": [s.floor for s in specs], "facing": [s.facing for s in specs],
        "kwh_th": phys.annual_kwh, "annual_aed": annual, "intensity": intensity, "score": letters,
        "capacity_aed": bill.annual("dc_capacity") * 1.05, "design_kw": phys.design_kw,
    })


def compare(base: pd.DataFrame, alt: pd.DataFrame) -> dict:
    """AED impact of a design change, per unit (mean) and for the whole tower (per year)."""
    diff = alt["annual_aed"].to_numpy() - base["annual_aed"].to_numpy()
    return {"per_unit_mean_aed": float(np.mean(diff)), "tower_aed": float(np.sum(diff)),
            "kwh_th_change_pct": float(100 * (alt["kwh_th"].sum() / base["kwh_th"].sum() - 1)),
            "units_improving_grade": int(np.sum(alt["score"].to_numpy() < base["score"].to_numpy()))}
