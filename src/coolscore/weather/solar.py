"""Solar irradiance on vertical facades for 8 orientations (pvlib).

Per hour and orientation we store the **beam** and **sky-diffuse** irradiance
on a vertical surface (W/m², Perez anisotropic sky). Ground-reflected
irradiance depends on the albedo, which is an uncertain assumption, so it is
not baked into the cache: :func:`ground_reflected` computes it on demand from
GHI and an albedo drawn from ``config/assumptions.yaml``.

Radiation rows are preceding-hour averages, so solar geometry is evaluated at
the middle of each interval (``t - 30 min``).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

from coolscore import config

ORIENTATIONS: dict[str, float] = {
    "N": 0.0, "NE": 45.0, "E": 90.0, "SE": 135.0, "S": 180.0, "SW": 225.0, "W": 270.0, "NW": 315.0,
}
VERTICAL = 90.0


def solar_position(index: pd.DatetimeIndex, lat: float, lon: float) -> pd.DataFrame:
    """Sun position at the middle of each preceding-hour interval, re-indexed to ``index``."""
    mid = index - pd.Timedelta(minutes=30)
    sp = pvlib.solarposition.get_solarposition(mid, lat, lon)
    sp.index = index
    return sp


def facade_irradiance(weather: pd.DataFrame, lat: float, lon: float) -> pd.DataFrame:
    """Beam and sky-diffuse irradiance (W/m²) on the 8 vertical orientations.

    Returns columns ``sun_elev_deg``, ``sun_az_deg`` and ``<ORI>_beam``,
    ``<ORI>_sky`` for every orientation in :data:`ORIENTATIONS`.
    """
    sp = solar_position(weather.index, lat, lon)
    zenith = sp["apparent_zenith"]
    azimuth = sp["azimuth"]
    up = sp["apparent_elevation"] > 0
    dni = weather["dni_wm2"].where(up, 0.0)
    dhi = weather["dhi_wm2"]
    ghi = weather["ghi_wm2"]
    dni_extra = pvlib.irradiance.get_extra_radiation(weather.index)
    airmass = pvlib.atmosphere.get_relative_airmass(zenith)

    out = {"sun_elev_deg": sp["apparent_elevation"], "sun_az_deg": azimuth}
    for name, surface_az in ORIENTATIONS.items():
        aoi = pvlib.irradiance.aoi(VERTICAL, surface_az, zenith, azimuth)
        beam = (dni * np.cos(np.radians(aoi))).clip(lower=0.0)
        sky = pvlib.irradiance.perez(
            VERTICAL, surface_az, dhi, dni, dni_extra, zenith, azimuth, airmass
        ).fillna(0.0).clip(lower=0.0)
        out[f"{name}_beam"] = beam
        out[f"{name}_sky"] = sky
    df = pd.DataFrame(out, index=weather.index)
    df.index.name = "time"
    # ghi kept alongside for the on-demand ground-reflected term
    df["ghi_wm2"] = ghi
    return df


def ground_reflected(ghi: pd.Series | np.ndarray, albedo: float, tilt_deg: float = VERTICAL):
    """Isotropic ground-reflected irradiance on a tilted surface (W/m²)."""
    return ghi * albedo * (1.0 - np.cos(np.radians(tilt_deg))) / 2.0


def facade_total(fac: pd.DataFrame, orientation: str, albedo: float) -> pd.Series:
    """Beam + sky + ground-reflected irradiance on one vertical orientation."""
    return fac[f"{orientation}_beam"] + fac[f"{orientation}_sky"] + ground_reflected(
        fac["ghi_wm2"], albedo
    )


def tan_profile_angle(sun_elev_deg, sun_az_deg, facade_az_deg):
    """Tangent of the vertical shadow (profile) angle on a facade.

    Used for overhang/balcony shading: a horizontal projection of depth ``d``
    above a window shades a height ``d * tan(profile)``. Returns NaN when the
    sun is behind the facade or below the horizon.
    """
    elev = np.radians(np.asarray(sun_elev_deg, dtype=float))
    rel = np.radians(np.asarray(sun_az_deg, dtype=float) - facade_az_deg)
    cos_rel = np.cos(rel)
    with np.errstate(divide="ignore", invalid="ignore"):
        tan_p = np.tan(elev) / cos_rel
    return np.where((cos_rel > 1e-6) & (elev > 0), tan_p, np.nan)


def facade_path(site: str, year: int) -> Path:
    return config.path("raw") / "facade" / f"facade_{site}_{year}.csv.gz"


def load_facades(site: str, year: int, weather: pd.DataFrame | None = None) -> pd.DataFrame:
    """Facade irradiance for a site-year, computed from cached weather once and cached locally."""
    path = facade_path(site, year)
    if path.exists():
        df = pd.read_csv(path, index_col="time")
        df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True)).tz_convert("Asia/Dubai")
        return df
    from coolscore.weather import dataset

    if weather is None:
        weather = dataset.load_weather(site, year)
    lat, lon = dataset.site_coordinates(site)
    df = facade_irradiance(weather, lat, lon)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, float_format="%.1f", compression={"method": "gzip", "mtime": 0})
    return df
