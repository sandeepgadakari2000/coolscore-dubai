"""Scenario sampling: a Latin-hypercube mix of listing facts and household details.

Each scenario is a complete :class:`~coolscore.physics.params.ListingSpec`
(including the optional household details) plus a cooling system, a payer
and a weather year. Hidden building and behaviour variables are sampled later
by :func:`coolscore.physics.params.build_params` and the billing step.
Mix weights come from ``settings.yaml`` → ``simulation.stock`` (design choices).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from coolscore import config
from coolscore.physics.params import ORIENTATIONS, ListingSpec
from coolscore.weather import dataset


def latin_hypercube(n: int, d: int, rng: np.random.Generator) -> np.ndarray:
    """``n`` points in ``[0, 1)^d``, one per stratum in every dimension."""
    u = (rng.random((n, d)) + np.arange(n)[:, None]) / n
    for j in range(d):
        u[:, j] = u[rng.permutation(n), j]
    return u


def _categorical(u: np.ndarray, weights: dict) -> np.ndarray:
    keys = list(weights)
    cdf = np.cumsum([weights[k] for k in keys], dtype=float)
    cdf /= cdf[-1]
    return np.array(keys, dtype=object)[np.searchsorted(cdf, u, side="right").clip(0, len(keys) - 1)]


def sample(n: int, seed: int) -> pd.DataFrame:
    """Sample ``n`` scenarios; returns one row per scenario."""
    rng = np.random.default_rng(seed)
    st = config.settings()["simulation"]["stock"]
    u = latin_hypercube(n, 16, rng)
    communities = list(config.communities()["communities"])
    years = dataset.years()

    era = _categorical(u[:, 0], st["era"])
    beds = _categorical(u[:, 1], {int(k): v for k, v in st["bedrooms"].items()}).astype(int)
    lo = np.array([st["size_sqft_by_bedrooms"][b][0] for b in beds], dtype=float)
    hi = np.array([st["size_sqft_by_bedrooms"][b][1] for b in beds], dtype=float)
    size = lo + u[:, 2] * (hi - lo)
    f_lo = np.array([st["total_floors_by_era"][e][0] for e in era])
    f_hi = np.array([st["total_floors_by_era"][e][1] for e in era])
    total = np.floor(f_lo + u[:, 3] * (f_hi - f_lo + 1)).astype(int)
    floor = np.clip(np.floor(1 + u[:, 4] * total).astype(int), 1, total)
    o1 = np.floor(u[:, 5] * 8).astype(int)
    corner = u[:, 6] < st["corner_share"]
    o2 = np.where(rng.random(n) < 0.5, (o1 + 2) % 8, (o1 + 6) % 8)
    facing = [f"{ORIENTATIONS[a]}+{ORIENTATIONS[b]}" if c else ORIENTATIONS[a] for a, b, c in zip(o1, o2, corner)]
    glass = np.array([_categorical(np.array([x]), st["glass_by_era"][e])[0] for x, e in zip(u[:, 7], era)])
    balcony = _categorical(u[:, 8], st["balcony"])
    obstruction = _categorical(u[:, 9], st["obstruction"])
    household = np.array([1 + int(x * (b + 2)) for x, b in zip(u[:, 10], beds)])
    occupancy = _categorical(u[:, 11], st["occupancy"])
    sp_lo, sp_hi = st["setpoint_c"]
    setpoint = np.round(sp_lo + u[:, 12] * (sp_hi - sp_lo), 1)
    system = np.array([_categorical(np.array([x]), st["system_by_era"][e])[0] for x, e in zip(u[:, 13], era)])
    payer = _categorical(u[:, 14], st["payer"])
    payer = np.where(np.isin(system, ["dewa_split_ac", "dewa_central_ac"]), "tenant", payer)
    year = np.array(years)[np.floor(u[:, 15] * len(years)).astype(int)]

    df = pd.DataFrame({
        "community": rng.choice(communities, n),
        "era_band": era, "size_sqft": np.round(size), "bedrooms": beds, "floor": floor,
        "total_floors": total, "facing": facing, "glass": glass, "balcony": balcony,
        "obstruction": obstruction, "household_size": household, "occupancy": occupancy,
        "setpoint_c": setpoint, "ramadan": rng.random(n) < st["ramadan_share"],
        "system": system, "payer": payer, "year": year,
    })
    df["weather_site"] = [dataset.weather_site_for(c) for c in df["community"]]
    return df


def to_specs(df: pd.DataFrame) -> list[ListingSpec]:
    """ListingSpecs (with household details) for the rows of a scenario table."""
    cols = ["community", "era_band", "size_sqft", "bedrooms", "floor", "total_floors", "facing", "glass",
            "balcony", "obstruction", "household_size", "occupancy", "setpoint_c", "ramadan"]
    return [ListingSpec(**{c: (v.item() if hasattr(v, "item") else v) for c, v in zip(cols, row)})
            for row in df[cols].itertuples(index=False, name=None)]
