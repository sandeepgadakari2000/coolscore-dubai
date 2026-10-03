"""The canonical Dubai weather product and the offline build that creates it.

Product: Open-Meteo ECMWF IFS 9 km hourly weather for each microclimate site,
temperature and dew point bias-corrected per (month, hour) to the nearest
airport observations (NOAA ISD). Stored as committed gzip CSVs in
``data/raw/weather/dubai_<site>_<year>.csv.gz``; :func:`load_weather` reads
them without any network access.

Run the build with ``python tasks.py data``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from coolscore import config
from coolscore.weather import correction, openmeteo, solar, stations


def weather_settings() -> dict:
    return config.settings()["weather"]


def sites() -> list[str]:
    return list(config.communities()["microclimates"])


def years() -> list[int]:
    return list(weather_settings()["years"])


def weather_site_for(community: str) -> str:
    """Weather site used for a community (via its microclimate and the D8 merge)."""
    c = config.communities()
    return c["weather_site"][c["communities"][community]]


def site_coordinates(site: str) -> tuple[float, float]:
    s = config.communities()["microclimates"][site]
    return float(s["lat"]), float(s["lon"])


def corrected_path(site: str, year: int) -> Path:
    return openmeteo.weather_dir() / f"dubai_{site}_{year}.csv.gz"


def summary_path() -> Path:
    return openmeteo.weather_dir() / "phase1_summary.json"


def bias_table_path() -> Path:
    return openmeteo.weather_dir() / "bias_correction.csv"


def load_weather(site: str, year: int) -> pd.DataFrame:
    """Bias-corrected hourly weather for one site-year (local cache only)."""
    src = corrected_path(site, year)
    if not src.exists():
        raise FileNotFoundError(f"{src.name} missing; run `python tasks.py data`")
    df = pd.read_csv(src, index_col="time")
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True)).tz_convert(openmeteo.TIMEZONE)
    return df


def load_bias_table() -> pd.DataFrame:
    return pd.read_csv(bias_table_path(), dtype={"station": str}, index_col=["station", "month", "hour"])


def _station(isd_id: str) -> stations.Station:
    return next(s for s in stations.STATIONS if s.isd_id == isd_id)


def _model_at_station(station: stations.Station, model: str, force: bool) -> pd.DataFrame:
    """Raw model series at the station coordinates (cached, used only to fit the correction)."""
    path = openmeteo.weather_dir() / "validation" / f"{model}_{station.isd_id}.csv.gz"
    if path.exists() and not force:
        df = pd.read_csv(path, index_col="time")
        df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True)).tz_convert(openmeteo.TIMEZONE)
        return df
    ys = years()
    df, _ = openmeteo.fetch(station.lat, station.lon, f"{min(ys)}-01-01", f"{max(ys)}-12-31", model)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, float_format="%.2f", compression={"method": "gzip", "mtime": 0})
    return df


def holdout_stats(model_df: pd.DataFrame, obs_df: pd.DataFrame, test_year: int,
                  smooth_hours: int) -> dict[str, dict[str, float]]:
    """Fit the correction on other years, score raw vs corrected on ``test_year``."""
    train = model_df.index.year != test_year
    table = correction.fit_bias(model_df[train], obs_df[obs_df.index.year != test_year], smooth_hours)
    test_model = model_df[~train]
    test_obs = obs_df[obs_df.index.year == test_year]
    return {
        "raw": stations.compare(test_model, test_obs),
        "corrected": stations.compare(correction.apply_bias(test_model, table), test_obs),
    }


def build(force: bool = False) -> dict:
    """Fetch, correct and cache all site-years; compute facade irradiance; write a summary."""
    ws = weather_settings()
    model = ws["model"]
    if not model:
        raise ValueError("settings.yaml weather.model is not set")
    bc = ws["bias_correction"]
    ys = years()

    openmeteo.fetch_sites(openmeteo.configured_sites(), ys, model, force=force)

    summary: dict = {"model": model, "years": ys, "stations": {}, "sites": {}}
    tables = []
    for isd_id in sorted(set(bc["site_station"].values())):
        st = _station(isd_id)
        model_df = _model_at_station(st, model, force)
        obs = pd.concat([stations.fetch_station_year(st, y, force=force) for y in ys])
        table = correction.fit_bias(model_df, obs, bc["smooth_hours"])
        tables.append(table.assign(station=isd_id).reset_index())
        summary["stations"][isd_id] = {
            "name": st.name,
            "lat": st.lat,
            "lon": st.lon,
            "obs_first": str(obs.index.min()),
            "obs_last": str(obs.index.max()),
            "in_sample_raw": stations.compare(model_df, obs),
            "in_sample_corrected": stations.compare(correction.apply_bias(model_df, table), obs),
            "holdout": holdout_stats(model_df, obs, bc["holdout_year"], bc["smooth_hours"]),
        }
    all_tables = pd.concat(tables).set_index(["station", "month", "hour"])
    all_tables.round(3).to_csv(bias_table_path())

    for site in sites():
        isd_id = bc["site_station"][site]
        table = all_tables.loc[isd_id]
        lat, lon = site_coordinates(site)
        summary["sites"][site] = {"lat": lat, "lon": lon, "station": isd_id}
        for year in ys:
            raw = openmeteo.load_raw(site, year, model)
            fixed = correction.apply_bias(raw, table)
            problems = openmeteo.check_quality(fixed, year)
            if problems:
                raise ValueError(f"{site} {year} after correction: {problems}")
            out = corrected_path(site, year)
            fixed.to_csv(out, float_format="%.2f", compression={"method": "gzip", "mtime": 0})
            meta = openmeteo.load_meta(site, year, model)
            meta["bias_correction"] = {
                "station_isd_id": isd_id,
                "station_name": _station(isd_id).name,
                "method": "additive per (month, hour), circular 3-h smoothing; RH recomputed",
                "corrected_vars": list(correction.CORRECTED_VARS),
            }
            meta["grid_lat_lon"] = [meta.get("grid_lat"), meta.get("grid_lon")]
            out.with_suffix("").with_suffix(".meta.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )
            fac_path = solar.facade_path(site, year)
            if fac_path.exists():
                fac_path.unlink()
            solar.load_facades(site, year, fixed)
            summary["sites"][site][str(year)] = {
                "grid": meta["grid_lat_lon"],
                "mean_temp_c": round(float(fixed["temp_c"].mean()), 2),
                "cdh24": round(stations.cooling_degree_hours(fixed["temp_c"])),
                "ghi_kwh_m2": round(float(fixed["ghi_wm2"].sum()) / 1000),
            }

    summary_path().write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import sys

    result = build(force="--force" in sys.argv)
    print(json.dumps({k: v for k, v in result.items() if k != "stations"}, indent=2))
