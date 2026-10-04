"""Where a unit's cooling load comes from: a heat budget by source, from the physics engine.

The 5R1C engine reports the total load the AC must remove. To show *where* it comes from,
we switch heat sources off one at a time and measure how much the load falls:

  sun through glass (window SHGC → 0) · sun on walls and roof (absorptance → 0) ·
  people and appliances (→ 0) · outside air and humidity (infiltration and untreated
  ventilation → ~0) · conduction through walls and glass from the hot outdoor air
  (what is left with all four removed).

Because sources interact (the thermostat, thermal mass), the drop depends on the order of
removal, so each source's share is the average of the forward and the reverse order (a two-
permutation Shapley estimate). The parts always add up exactly to the total. All eight
variants run as one batch over one month (plus a 10-day lead-in so the thermal mass is warm), so
a month costs about a quarter of a second. SIMULATED: central hidden values, 2024 weather.
"""

from __future__ import annotations

from dataclasses import fields
from functools import lru_cache

import numpy as np

import pandas as pd

from coolscore import config
from coolscore.physics import rc5r1c
from coolscore.physics.params import ListingSpec, UnitParams, build_params, weather_site
from coolscore.weather import dataset, solar

SOURCES = ("sun_glass", "sun_walls", "people", "air", "conduction")
LABELS = {"sun_glass": "Sun through the glass", "sun_walls": "Sun heating walls and roof",
          "people": "People and appliances", "air": "Outside air and humidity",
          "conduction": "Heat through walls and glass"}
REMOVE = {
    "sun_glass": {"win_shgc": 0.0},
    "sun_walls": {"opaque_absorptance": 0.0},
    "people": {"people": 0.0, "appliance_wm2": 0.0},
    "air": {"infiltration_ach": 0.01, "untreated_vent_m3s": 0.0},
}
ORDER = ("sun_glass", "sun_walls", "people", "air")
YEAR = 2024
LEAD_IN_DAYS = 10


def _stack(variants: list[UnitParams]) -> UnitParams:
    return UnitParams(**{f.name: np.concatenate([getattr(v, f.name) for v in variants]) for f in fields(UnitParams)})


def _without(base: UnitParams, removed: tuple[str, ...]) -> UnitParams:
    changes: dict = {}
    for source in removed:
        changes.update(REMOVE[source])
    return base.replace(**changes) if changes else base


@lru_cache(maxsize=4)
def _site_year(site: str, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    weather = dataset.load_weather(site, year)
    return weather, solar.load_facades(site, year, weather)


@lru_cache(maxsize=48)
def _month_window(site: str, year: int, month: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Weather and facade sun for one calendar month (0-11) plus the lead-in days before it."""
    weather, facades = _site_year(site, year)
    start = pd.Timestamp(year=year, month=month + 1, day=1, tz=weather.index.tz)
    end = start + pd.offsets.MonthBegin(1)
    keep = (weather.index >= start - pd.Timedelta(days=LEAD_IN_DAYS if month else 0)) & (weather.index < end)
    return weather[keep], facades[keep]


def heat_budget(spec: ListingSpec, month: int, year: int = YEAR) -> dict:
    """One month's cooling load by source (kWh of heat), plus the humidity share and the peak heat flow."""
    spec.validate()
    base = build_params([spec], "central")
    forward = [ORDER[:k] for k in range(len(ORDER) + 1)]                       # (), (A,), (A,B) ... (A,B,C,D)
    reverse = [tuple(reversed(ORDER))[:k] for k in range(1, len(ORDER))]       # (D,), (D,C), (D,C,B)
    variants = forward + reverse
    weather, facades = _month_window(weather_site(spec), year, month)
    res = rc5r1c.simulate(_stack([_without(base, v) for v in variants]), weather, facades, keep_hourly=True)
    total = res.total_kwh[:, month]                                            # (8,) this month only
    in_month = weather.index.month == month + 1

    def key(removed) -> tuple:
        return tuple(sorted(removed))

    by_key = {key(v): total[i] for i, v in enumerate(variants)}
    rev = tuple(reversed(ORDER))
    parts = {}
    for i, source in enumerate(ORDER):
        j = rev.index(source)
        forward_drop = by_key[key(ORDER[:i])] - by_key[key(ORDER[:i + 1])]
        reverse_drop = by_key[key(rev[:j])] - by_key[key(rev[:j + 1])]
        parts[source] = 0.5 * (forward_drop + reverse_drop)
    parts["conduction"] = by_key[key(ORDER)]
    base_total = float(by_key[()])
    # Peak heat flow on a hot afternoon of this month: the base unit's 98th-percentile daily peak.
    days = sorted(set(weather.index[in_month].dayofyear))
    load_w = -res.hourly["phi_hc"][0] + res.hourly["q_lat"][0]               # variant 0 = the unit as it is
    daily = [load_w[weather.index.dayofyear == d].max() for d in days]
    design_kw = float(np.percentile(daily, 98)) / 1000 if daily else 0.0
    people = config.require("physics.people_gains")
    person_w = people["awake_sensible_w"] + people["awake_latent_w"]
    return {
        "month": month, "kwh": {s: round(float(parts[s]), 1) for s in SOURCES}, "total_kwh": round(base_total, 1),
        "latent_share": float(res.lat_kwh[0, month] / base_total) if base_total > 1e-6 else 0.0,
        "design_kw": round(design_kw, 2), "people_equivalent": round(design_kw * 1000 / person_w, 1),
        "person_w": person_w, "year": year,
    }


def spec_from_listing(listing: dict) -> ListingSpec:
    """A ListingSpec from the app/API listing dict (defaults already filled by predict.normalise)."""
    keys = {f.name for f in fields(ListingSpec)}
    return ListingSpec(**{k: v for k, v in listing.items() if k in keys})
