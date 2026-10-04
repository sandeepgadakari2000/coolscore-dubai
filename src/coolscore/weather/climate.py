"""Typical-month Dubai climate for the app's live weather scene.

Averages the cached, bias-corrected hourly weather and pvlib facade sun (2023–25)
into one typical day per month and microclimate: hourly temperature, humidity,
cloud, sun position and sun on each of the 8 facade directions, plus monthly
summaries (mean daily high/low, days above 40 °C...). The app animates these
*measured* conditions instead of stock weather art, fully offline.

Writes ``data/demo/climate_monthly.json`` (small, committed so the deployed app
has it). Run with ``python tasks.py climate`` after ``python tasks.py data``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from coolscore import config
from coolscore.physics.params import ORIENTATIONS
from coolscore.weather import dataset, solar

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def out_path() -> Path:
    return config.path("demo") / "climate_monthly.json"


def _site_frame(site: str) -> pd.DataFrame:
    albedo = config.require("physics.ground_albedo")["central"]
    frames = []
    for year in dataset.years():
        w = dataset.load_weather(site, year)
        fac = solar.load_facades(site, year, w)
        df = w[["temp_c", "rh_pct", "dewpoint_c", "cloud_pct", "wind_ms", "ghi_wm2", "dhi_wm2"]].copy()
        df["elev"] = fac["sun_elev_deg"].reindex(df.index)
        df["az"] = fac["sun_az_deg"].reindex(df.index)
        for o in ORIENTATIONS:
            df[f"fac_{o}"] = solar.facade_total(fac, o, albedo).reindex(df.index).clip(lower=0)
        frames.append(df)
    return pd.concat(frames)


def summarise(site: str) -> list[dict]:
    """Twelve typical months for one microclimate site."""
    df = _site_frame(site)
    df["month"], df["hour"], df["date"] = df.index.month, df.index.hour, df.index.date
    daily = df.groupby("date").agg(tmax=("temp_c", "max"), tmin=("temp_c", "min"))
    daily["month"] = pd.to_datetime(daily.index).month
    n_years = len(dataset.years())
    months = []
    for m in range(1, 13):
        sub, d = df[df["month"] == m], daily[daily["month"] == m]
        day = sub[sub["ghi_wm2"] > 20]
        prof = sub.groupby("hour")
        months.append({
            "month": MONTHS[m - 1],
            "tmax": round(float(d["tmax"].mean()), 1),
            "tmin": round(float(d["tmin"].mean()), 1),
            "rh": round(float(sub["rh_pct"].mean())),
            "dewpoint": round(float(sub["dewpoint_c"].mean()), 1),
            "cloud": round(float(day["cloud_pct"].mean())),
            "wind": round(float(sub["wind_ms"].mean()), 1),
            "haze": round(float(day["dhi_wm2"].sum() / max(day["ghi_wm2"].sum(), 1.0)), 2),
            "days_over_40": round(float((d["tmax"] > 40).sum()) / n_years, 1),
            "facade_kwh_day": {o: round(float(sub[f"fac_{o}"].sum()) / 1000 / (len(sub) / 24), 2)
                               for o in ORIENTATIONS},
            "hourly": {
                "temp": [round(float(x), 1) for x in prof["temp_c"].mean()],
                "rh": [round(float(x)) for x in prof["rh_pct"].mean()],
                "cloud": [round(float(x)) for x in prof["cloud_pct"].mean()],
                "elev": [round(float(x), 1) for x in prof["elev"].mean()],
                "az": [round(float(x), 1) for x in prof["az"].mean()],
                "facade": {o: [round(float(x)) for x in prof[f"fac_{o}"].mean()] for o in ORIENTATIONS},
            },
        })
    return months


def build() -> dict:
    data = {
        "source": "Typical day per month from 2023–25 hourly Open-Meteo ECMWF IFS 9 km weather, temperature and "
                  "dew point corrected to NOAA airport observations; facade sun from pvlib (Perez sky).",
        "years": dataset.years(),
        "sites": {site: summarise(site) for site in ("central", "inland")},
    }
    out_path().write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return data


def load() -> dict:
    """The committed climate summary (no weather files needed at runtime)."""
    return json.loads(out_path().read_text(encoding="utf-8"))


def site_months(community: str) -> list[dict]:
    return load()["sites"][dataset.weather_site_for(community)]


if __name__ == "__main__":
    d = build()
    aug = d["sites"]["central"][7]
    print(f"wrote {out_path().relative_to(config.ROOT)} ({out_path().stat().st_size / 1024:.0f} KB); "
          f"central Aug high {aug['tmax']} °C, W facade {aug['facade_kwh_day']['W']} kWh/m²/day")
