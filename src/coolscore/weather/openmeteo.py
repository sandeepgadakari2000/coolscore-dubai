"""Fetch and cache hourly weather from the Open-Meteo Historical Weather API.

The API is called only by the offline ``tasks.py data`` step. Downstream code
reads the bias-corrected product via :func:`coolscore.weather.dataset.load_weather`,
which never touches the network.

Conventions
-----------
- Timestamps are local Dubai time (UTC+4, no daylight saving), tz-aware.
- Radiation values are **averages over the preceding hour** (Open-Meteo
  convention), so solar geometry for row ``t`` is evaluated at ``t - 30 min``.
- Open-Meteo data is CC BY 4.0; the free API is for non-commercial use.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from coolscore import config

ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Dubai"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com/"

# API variable -> our column name
COLUMNS: dict[str, str] = {
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "rh_pct",
    "dew_point_2m": "dewpoint_c",
    "surface_pressure": "pressure_hpa",
    "wind_speed_10m": "wind_ms",
    "shortwave_radiation": "ghi_wm2",
    "direct_radiation": "bhi_wm2",
    "diffuse_radiation": "dhi_wm2",
    "direct_normal_irradiance": "dni_wm2",
    "cloud_cover": "cloud_pct",
}

# Plausibility bounds for Dubai (inclusive); used by check_quality.
BOUNDS: dict[str, tuple[float, float]] = {
    "temp_c": (0.0, 55.0),
    "rh_pct": (0.0, 100.0),
    "dewpoint_c": (-30.0, 35.0),
    "pressure_hpa": (950.0, 1050.0),
    "wind_ms": (0.0, 40.0),
    "ghi_wm2": (0.0, 1400.0),
    "bhi_wm2": (0.0, 1300.0),
    "dhi_wm2": (0.0, 800.0),
    "dni_wm2": (0.0, 1400.0),
    "cloud_pct": (0.0, 100.0),
}


@dataclass(frozen=True)
class Site:
    """A point where weather is fetched."""

    name: str
    lat: float
    lon: float


def configured_sites() -> list[Site]:
    """The microclimate sites from ``config/communities.yaml``."""
    return [Site(k, v["lat"], v["lon"]) for k, v in config.communities()["microclimates"].items()]


def weather_dir() -> Path:
    return config.path("raw") / "weather"


def cache_path(model: str, site: str, year: int) -> Path:
    return weather_dir() / f"openmeteo_{model}_{site}_{year}.csv.gz"


def build_params(lat: float, lon: float, start: str, end: str, model: str) -> dict[str, str | float]:
    """Query parameters for one archive request."""
    return {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(COLUMNS),
        "timezone": TIMEZONE,
        "wind_speed_unit": "ms",
        "models": model,
    }


def parse_response(payload: dict) -> tuple[pd.DataFrame, dict]:
    """Turn an API JSON payload into a tidy DataFrame plus grid metadata."""
    hourly = payload["hourly"]
    index = pd.DatetimeIndex(pd.to_datetime(hourly["time"])).tz_localize(TIMEZONE)
    df = pd.DataFrame({ours: hourly[api] for api, ours in COLUMNS.items()}, index=index)
    df.index.name = "time"
    meta = {
        "grid_lat": payload.get("latitude"),
        "grid_lon": payload.get("longitude"),
        "grid_elevation_m": payload.get("elevation"),
        "utc_offset_seconds": payload.get("utc_offset_seconds"),
        "units": payload.get("hourly_units"),
    }
    return df.astype(float), meta


def fetch(lat: float, lon: float, start: str, end: str, model: str,
          session: requests.Session | None = None) -> tuple[pd.DataFrame, dict]:
    """Call the archive API once (network)."""
    params = build_params(lat, lon, start, end, model)
    response = (session or requests).get(ENDPOINT, params=params, timeout=120)
    response.raise_for_status()
    df, meta = parse_response(response.json())
    meta.update(
        endpoint=ENDPOINT, model=model, request_lat=lat, request_lon=lon,
        retrieved=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        licence="CC BY 4.0", attribution=ATTRIBUTION,
    )
    return df, meta


def save_year(df: pd.DataFrame, meta: dict, model: str, site: str, year: int) -> Path:
    """Write one site-year to the gzip CSV cache with a metadata sidecar."""
    out = cache_path(model, site, year)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, float_format="%.2f", compression={"method": "gzip", "mtime": 0})
    out.with_suffix("").with_suffix(".meta.json").write_text(
        json.dumps({**meta, "site": site, "year": year}, indent=2), encoding="utf-8"
    )
    return out


def load_raw(site: str, year: int, model: str | None = None) -> pd.DataFrame:
    """Read one cached raw (uncorrected) site-year; never calls the network."""
    model = model or config.settings()["weather"]["model"]
    src = cache_path(model, site, year)
    if not src.exists():
        raise FileNotFoundError(f"{src.name} not cached; run `python tasks.py data` first")
    df = pd.read_csv(src, index_col="time")
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True)).tz_convert(TIMEZONE)
    return df


def load_meta(site: str, year: int, model: str | None = None) -> dict:
    model = model or config.settings()["weather"]["model"]
    sidecar = cache_path(model, site, year).with_suffix("").with_suffix(".meta.json")
    return json.loads(sidecar.read_text(encoding="utf-8"))


def expected_hours(year: int) -> int:
    return 8784 if pd.Timestamp(year=year, month=12, day=31).dayofyear == 366 else 8760


def check_quality(df: pd.DataFrame, year: int) -> list[str]:
    """Return problems with one site-year (empty list = passes)."""
    problems: list[str] = []
    if len(df) != expected_hours(year):
        problems.append(f"{len(df)} rows, expected {expected_hours(year)}")
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        problems.append("time index not strictly increasing")
    steps = df.index.to_series().diff().dropna().unique()
    if len(steps) != 1 or steps[0] != pd.Timedelta(hours=1):
        problems.append("time step is not a constant 1 hour")
    missing = df.isna().sum()
    for col, n in missing[missing > 0].items():
        problems.append(f"{col}: {n} missing values")
    for col, (lo, hi) in BOUNDS.items():
        bad = ((df[col] < lo) | (df[col] > hi)).sum()
        if bad:
            problems.append(f"{col}: {bad} values outside [{lo}, {hi}]")
    return problems


def fetch_sites(sites: list[Site], years: list[int], model: str, force: bool = False) -> list[Path]:
    """Fetch every site for the full year range (one request per site) and cache per year."""
    written: list[Path] = []
    with requests.Session() as session:
        for site in sites:
            if not force and all(cache_path(model, site.name, y).exists() for y in years):
                continue
            df, meta = fetch(site.lat, site.lon, f"{min(years)}-01-01", f"{max(years)}-12-31",
                             model, session)
            for year in years:
                part = df[df.index.year == year]
                problems = check_quality(part, year)
                if problems:
                    raise ValueError(f"{site.name} {year}: " + "; ".join(problems))
                written.append(save_year(part, meta, model, site.name, year))
    return written
