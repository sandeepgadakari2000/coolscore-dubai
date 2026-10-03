"""Hourly occupancy schedules: presence, resting hours and appliance factors.

Profiles come from ``settings.yaml`` (design choices); the weekend and Ramadan
dates come from ``assumptions.yaml``. Schedules are built once per weather
year as small arrays ``[n_profiles, n_hours]`` and indexed per unit.

Profile ids: ``0`` away in the daytime, ``1`` home in the daytime; add ``2``
for the Ramadan variant (``2`` = away + Ramadan, ``3`` = home + Ramadan).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from coolscore import config

OCCUPANCY = ("away_daytime", "home_daytime")
N_PROFILES = 4


def profile_id(occupancy: str, ramadan: bool) -> int:
    """Index of a schedule profile."""
    return OCCUPANCY.index(occupancy) + (2 if ramadan else 0)


@dataclass(frozen=True)
class Schedules:
    """Per-profile hourly arrays for one weather year."""

    presence: np.ndarray        # [profile, hour] share of household at home
    resting: np.ndarray         # [profile, hour] bool, occupants at resting gains
    appliance: np.ndarray       # [profile, hour] multiplier on mean appliance gains
    away: np.ndarray            # [profile, hour] bool, nobody home


def _ramadan_mask(index: pd.DatetimeIndex) -> np.ndarray:
    dates = config.require("schedules.ramadan_dates")
    mask = np.zeros(len(index), dtype=bool)
    year_dates = dates.get(index[0].year) or dates.get(str(index[0].year))
    if year_dates:
        start, end = (pd.Timestamp(d).date() for d in year_dates)
        days = np.array(index.date)
        mask = (days >= start) & (days <= end)
    return mask


def _iso_appliance_shape(hours: np.ndarray) -> np.ndarray:
    """ISO 13790 Table G.7 living-area profile, normalised to a daily mean of 1."""
    prof = config.require("physics.appliance_lighting_gain")["profile_w_m2"]
    day, evening, night = prof["07-17"], prof["17-23"], prof["23-07"]
    shape = np.where((hours >= 7) & (hours < 17), day, np.where((hours >= 17) & (hours < 23), evening, night))
    mean = (10 * day + 6 * evening + 8 * night) / 24.0
    return shape / mean


def build(index: pd.DatetimeIndex) -> Schedules:
    """Build all profiles for the hours in ``index`` (local Dubai time)."""
    ps = config.settings()["physics"]
    weekend_names = set(config.require("schedules.uae_weekend"))
    hours = index.hour.to_numpy()
    day_names = index.day_name().to_numpy()
    is_weekend = np.isin(day_names, list(weekend_names))
    is_friday = day_names == "Friday"
    in_ramadan = _ramadan_mask(index)
    shape = _iso_appliance_shape(hours)
    base = ps["appliance_base_share"]
    threshold = ps["away_threshold"]

    presence = np.empty((N_PROFILES, len(index)))
    resting = np.empty((N_PROFILES, len(index)), dtype=bool)
    for occ_i, occ in enumerate(OCCUPANCY):
        p = {k: np.asarray(v, dtype=float) for k, v in ps["presence"][occ].items()}
        normal = np.where(is_weekend, p["weekend"][hours],
                          np.where(is_friday, p["friday"][hours], p["workday"][hours]))
        ramadan_day = np.where(is_weekend, p["weekend"][hours], p["ramadan_workday"][hours])
        presence[occ_i] = normal
        presence[occ_i + 2] = np.where(in_ramadan, ramadan_day, normal)
        rest_normal = np.isin(hours, ps["resting_hours"])
        rest_ramadan = np.isin(hours, ps["ramadan_resting_hours"])
        resting[occ_i] = rest_normal
        resting[occ_i + 2] = np.where(in_ramadan, rest_ramadan, rest_normal)

    appliance = shape * (base + (1.0 - base) * presence)
    return Schedules(presence=presence, resting=resting, appliance=appliance, away=presence < threshold)
