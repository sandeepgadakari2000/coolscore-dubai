"""Airport observations (NOAA ISD) used to check the Open-Meteo weather models.

Only used offline, for model selection and the Phase 1 report. NOAA ISD
"global-hourly" data is a US-government public dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from coolscore import config

ISD_URL = "https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{station}.csv"


@dataclass(frozen=True)
class Station:
    """An ISD station with the microclimate it is compared against."""

    isd_id: str
    name: str
    lat: float
    lon: float
    compares_with: str


STATIONS: tuple[Station, ...] = (
    Station("41194099999", "Dubai International Airport", 25.255, 55.364, "central"),
    Station("41194599999", "Al Maktoum International Airport", 24.886, 55.172, "inland"),
)


def station_dir() -> Path:
    return config.path("raw") / "stations"


def parse_isd_value(field: pd.Series) -> pd.Series:
    """Decode ISD 'TMP'/'DEW' fields like '+0229,1' into °C (NaN if missing or bad quality)."""
    parts = field.astype(str).str.split(",", expand=True)
    value = pd.to_numeric(parts[0], errors="coerce")
    quality = parts[1] if parts.shape[1] > 1 else pd.Series("9", index=field.index)
    ok = (value.abs() < 9999) & quality.isin(["0", "1", "4", "5", "9", "A", "C", "M", "P", "R", "U"])
    return (value / 10.0).where(ok)


def parse_isd(csv_text_or_path: str | Path) -> pd.DataFrame:
    """Hourly (on-the-hour) temperature and dew point in Dubai local time."""
    raw = pd.read_csv(csv_text_or_path, usecols=["DATE", "TMP", "DEW"], dtype=str)
    t = pd.to_datetime(raw["DATE"], utc=True)
    df = pd.DataFrame(
        {"temp_c": parse_isd_value(raw["TMP"]).to_numpy(),
         "dewpoint_c": parse_isd_value(raw["DEW"]).to_numpy()},
        index=pd.DatetimeIndex(t).tz_convert("Asia/Dubai"),
    )
    df = df[df.index.minute == 0]
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index.name = "time"
    return df


def fetch_station_year(station: Station, year: int, force: bool = False) -> pd.DataFrame:
    """Download (once) and cache one station-year as a slim gzip CSV."""
    out = station_dir() / f"isd_{station.isd_id}_{year}.csv.gz"
    if out.exists() and not force:
        df = pd.read_csv(out, index_col="time")
        df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True)).tz_convert("Asia/Dubai")
        return df
    response = requests.get(ISD_URL.format(year=year, station=station.isd_id), timeout=180)
    response.raise_for_status()
    from io import StringIO

    df = parse_isd(StringIO(response.text))
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, float_format="%.1f", compression={"method": "gzip", "mtime": 0})
    return df


def cooling_degree_hours(temp_c: pd.Series, base_c: float = 24.0) -> float:
    """Sum of (T - base)+ over the hours present (°C·h)."""
    return float(np.clip(temp_c - base_c, 0, None).sum())


def compare(model_df: pd.DataFrame, obs_df: pd.DataFrame) -> dict[str, float]:
    """Error statistics of a model series against observations on shared hours."""
    joined = model_df[["temp_c", "dewpoint_c"]].join(
        obs_df[["temp_c", "dewpoint_c"]], lsuffix="_model", rsuffix="_obs", how="inner"
    ).dropna()
    if joined.empty:
        raise ValueError("no overlapping hours")
    out: dict[str, float] = {"hours": float(len(joined))}
    for var in ("temp_c", "dewpoint_c"):
        err = joined[f"{var}_model"] - joined[f"{var}_obs"]
        out[f"{var}_bias"] = float(err.mean())
        out[f"{var}_rmse"] = float(np.sqrt((err**2).mean()))
    out["cdh24_ratio"] = cooling_degree_hours(joined["temp_c_model"]) / cooling_degree_hours(
        joined["temp_c_obs"]
    )
    summer = joined[joined.index.month.isin([6, 7, 8])]
    daily = summer.resample("D").agg(["max", "min"])
    for src in ("model", "obs"):
        out[f"jja_mean_daily_max_{src}"] = float(daily[(f"temp_c_{src}", "max")].mean())
        out[f"jja_mean_daily_min_{src}"] = float(daily[(f"temp_c_{src}", "min")].mean())
    return out
