"""High-level physics API: listing specs (or unit parameters) in, cooling energy out."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from coolscore.physics import rc5r1c
from coolscore.physics.params import ListingSpec, UnitParams, build_params, weather_site
from coolscore.weather import dataset, solar


def run_site_year(params: UnitParams, site: str, year: int, batch_size: int = 5000,
                  keep_hourly: bool = False, solar_scale: float = 1.0) -> rc5r1c.PhysicsResult:
    """Simulate many units on one cached site-year, in memory-bounded batches."""
    weather = dataset.load_weather(site, year)
    facades = solar.load_facades(site, year, weather)
    parts = []
    for start in range(0, params.n, batch_size):
        idx = np.arange(start, min(start + batch_size, params.n))
        parts.append(rc5r1c.simulate(params.subset(idx), weather, facades, keep_hourly, solar_scale))
    if len(parts) == 1:
        return parts[0]
    return rc5r1c.PhysicsResult(**{
        name: np.concatenate([getattr(r, name) for r in parts])
        for name in ("sens_kwh", "lat_kwh", "load_x_dt_kwhk", "cooling_hours", "appliance_kwh", "peak_kw", "design_kw")
    })


def simulate_listings(specs: Iterable[ListingSpec], year: int,
                      hidden: str | np.random.Generator = "central") -> rc5r1c.PhysicsResult:
    """Simulate listings that share a weather site (same community microclimate)."""
    specs = list(specs)
    sites = {weather_site(s) for s in specs}
    if len(sites) != 1:
        raise ValueError(f"listings span several weather sites {sites}; group them first")
    return run_site_year(build_params(specs, hidden), sites.pop(), year)
