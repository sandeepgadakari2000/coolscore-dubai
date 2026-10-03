"""Phase 1 sanity report: weather validation, microclimates and facade sun.

Writes ``docs/phase1_weather_sun.md`` (tables) and
``docs/figures/phase1_weather_sun.html`` (interactive Plotly charts; Plotly is
loaded from its CDN so the file stays small). Run after ``tasks.py data``:
``python tasks.py report-weather``.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from coolscore import config
from coolscore.weather import correction, dataset, solar, stations

# Reference data-viz palette (validated categorical order) and chart chrome.
SERIES = {"N": "#2a78d6", "W": "#eb6834", "E": "#1baf7a", "S": "#eda100"}
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
MAIN_ORIENTATIONS = ["N", "E", "S", "W"]


def facade_stats(site: str, albedo: float) -> pd.DataFrame:
    """Per-orientation summer/winter/annual irradiation and heat coincidence (3-year means)."""
    w = pd.concat([dataset.load_weather(site, y) for y in dataset.years()])
    f = pd.concat([solar.load_facades(site, y) for y in dataset.years()])
    n_years = len(dataset.years())
    rows = {}
    for o in solar.ORIENTATIONS:
        tot = solar.facade_total(f, o, albedo)
        jja = tot[tot.index.month.isin([6, 7, 8])]
        djf = tot[tot.index.month.isin([12, 1, 2])]
        hot = jja[w.loc[jja.index, "temp_c"] > 38.0]
        rows[o] = {
            "summer_kwh_m2_day": jja.sum() / 1000 / (len(jja) / 24),
            "winter_kwh_m2_day": djf.sum() / 1000 / (len(djf) / 24),
            "annual_kwh_m2": tot.sum() / 1000 / n_years,
            "summer_weighted_temp_c": float((jja * w.loc[jja.index, "temp_c"]).sum() / jja.sum()),
            "kwh_m2_when_above_38c": hot.sum() / 1000 / n_years,
        }
    return pd.DataFrame(rows).T


def microclimate_stats() -> pd.DataFrame:
    """Cooling-relevant weather metrics per site (3-year means, corrected weather)."""
    rows = {}
    for site in dataset.sites():
        d = pd.concat([dataset.load_weather(site, y) for y in dataset.years()])
        jja = d[d.index.month.isin([6, 7, 8])]
        daily = jja["temp_c"].resample("D").agg(["max", "min"])
        n = len(dataset.years())
        rows[site] = {
            "summer_mean_daily_max_c": daily["max"].mean(),
            "summer_mean_daily_min_c": daily["min"].mean(),
            "summer_mean_dewpoint_c": jja["dewpoint_c"].mean(),
            "cooling_degree_hours_24c_per_yr": stations.cooling_degree_hours(d["temp_c"]) / n,
            "ghi_kwh_m2_per_yr": d["ghi_wm2"].sum() / 1000 / n,
        }
    return pd.DataFrame(rows).T


def _diurnal_validation(isd_id: str) -> pd.DataFrame:
    """Mean summer temperature by hour: observed, raw model, corrected model."""
    st = next(s for s in stations.STATIONS if s.isd_id == isd_id)
    model = config.settings()["weather"]["model"]
    raw = dataset._model_at_station(st, model, force=False)
    obs = pd.concat([stations.fetch_station_year(st, y) for y in dataset.years()])
    table = dataset.load_bias_table().loc[isd_id]
    fixed = correction.apply_bias(raw, table)
    out = {}
    for name, df in {"Observed": obs, "Model, raw": raw, "Model, corrected": fixed}.items():
        s = df.loc[df.index.isin(obs.dropna().index), "temp_c"]
        s = s[s.index.month.isin([6, 7, 8])]
        out[name] = s.groupby(s.index.hour).mean()
    return pd.DataFrame(out)


def _style(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": INK}, "x": 0, "xanchor": "left"},
        height=height, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": "system-ui, -apple-system, Segoe UI, sans-serif", "color": INK_2, "size": 12},
        legend={"orientation": "h", "y": -0.18, "x": 0},
        margin={"l": 60, "r": 30, "t": 60, "b": 70}, hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont={"color": MUTED})
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont={"color": MUTED})
    return fig


def figures(albedo: float) -> list[go.Figure]:
    """The three Phase 1 sanity charts."""
    figs = []

    val = _diurnal_validation("41194099999")
    f1 = go.Figure()
    for name, color, dash in [("Observed", INK, "solid"), ("Model, raw", SERIES["W"], "solid"),
                              ("Model, corrected", SERIES["N"], "solid")]:
        f1.add_trace(go.Scatter(x=val.index, y=val[name], name=name, mode="lines",
                                line={"color": color, "width": 2, "dash": dash},
                                hovertemplate="%{y:.1f} °C"))
    f1.update_xaxes(title="Hour of day (local, hour-ending)", dtick=3)
    f1.update_yaxes(title="Mean summer temperature (°C)")
    figs.append(_style(f1, "Dubai International, Jun–Aug 2023–25: the raw model misses evening and night heat", 380))

    w = pd.concat([dataset.load_weather("central", y) for y in dataset.years()])
    f = pd.concat([solar.load_facades("central", y) for y in dataset.years()])
    f2 = go.Figure()
    for o in MAIN_ORIENTATIONS:
        tot = solar.facade_total(f, o, albedo)
        monthly = tot.groupby(tot.index.month).sum() / 1000 / tot.groupby(tot.index.month).size() * 24
        f2.add_trace(go.Scatter(x=monthly.index, y=monthly.values, name=f"{o}-facing",
                                mode="lines+markers", line={"color": SERIES[o], "width": 2},
                                marker={"size": 8, "line": {"color": SURFACE, "width": 2}},
                                hovertemplate="%{y:.2f} kWh/m²/day"))
    f2.update_xaxes(title="Month", tickvals=list(range(1, 13)),
                    ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    f2.update_yaxes(title="Sun on a vertical facade (kWh/m²/day)", rangemode="tozero")
    figs.append(_style(f2, "In summer, east and west facades get about 1.8× the sun of south or north", 380))

    jja = f.index.month.isin([6, 7, 8])
    f3 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.08)
    for o in MAIN_ORIENTATIONS:
        prof = solar.facade_total(f, o, albedo)[jja]
        prof = prof.groupby(prof.index.hour).mean()
        f3.add_trace(go.Scatter(x=prof.index, y=prof.values, name=f"{o}-facing", mode="lines",
                                line={"color": SERIES[o], "width": 2}, hovertemplate="%{y:.0f} W/m²"),
                     row=1, col=1)
    temp = w.loc[jja, "temp_c"]
    temp = temp.groupby(temp.index.hour).mean()
    f3.add_trace(go.Scatter(x=temp.index, y=temp.values, name="Outdoor temperature", mode="lines",
                            line={"color": INK, "width": 2}, hovertemplate="%{y:.1f} °C"), row=2, col=1)
    f3.update_yaxes(title="Facade sun (W/m²)", row=1, col=1, rangemode="tozero")
    f3.update_yaxes(title="Temp (°C)", row=2, col=1)
    f3.update_xaxes(title="Hour of day (local, hour-ending)", dtick=3, row=2, col=1)
    figs.append(_style(f3, "West sun arrives in the hottest part of the day; east sun in the cooler morning", 520))
    return figs


def _fmt(v: float) -> str:
    """Thousands-separated; whole numbers above 100, two decimals below."""
    return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}"


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for idx, row in df.iterrows():
        lines.append(f"| {idx} | " + " | ".join(_fmt(v) for v in row.values) + " |")
    return "\n".join(lines)


def sanity_checks(fac: pd.DataFrame) -> list[tuple[str, bool, str]]:
    """The brief's §4.1 expectations, evaluated on the central site."""
    s = fac["summer_kwh_m2_day"]
    return [
        ("Summer: east and west get more sun than south", bool(min(s["E"], s["W"]) > s["S"]),
         f"E {s['E']:.2f}, W {s['W']:.2f}, S {s['S']:.2f} kWh/m²/day"),
        ("Summer: south gets less than people expect (≈ north)", bool(s["S"] < 1.15 * s["N"]),
         f"S {s['S']:.2f} vs N {s['N']:.2f} kWh/m²/day"),
        ("West sun coincides with the hottest hours (vs east)",
         bool(fac.loc["W", "kwh_m2_when_above_38c"] > fac.loc["E", "kwh_m2_when_above_38c"]),
         f"sun while > 38 °C: W {fac.loc['W', 'kwh_m2_when_above_38c']:.0f} vs "
         f"E {fac.loc['E', 'kwh_m2_when_above_38c']:.0f} kWh/m²/yr"),
        ("Winter: south facade gets the most sun",
         bool(fac["winter_kwh_m2_day"].idxmax() == "S"),
         f"S {fac.loc['S', 'winter_kwh_m2_day']:.2f} kWh/m²/day"),
        ("North gets the least sun over the year", bool(fac["annual_kwh_m2"].idxmin() == "N"),
         f"N {fac.loc['N', 'annual_kwh_m2']:.0f} kWh/m²/yr"),
    ]


def write_report() -> None:
    albedo = config.require("physics.ground_albedo")["central"]
    summary = json.loads(dataset.summary_path().read_text(encoding="utf-8"))
    fac = facade_stats("central", albedo)
    micro = microclimate_stats()
    checks = sanity_checks(fac)

    figs = figures(albedo)
    out_dir = config.ROOT / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = [figs[0].to_html(full_html=False, include_plotlyjs="cdn")]
    parts += [fg.to_html(full_html=False, include_plotlyjs=False) for fg in figs[1:]]
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' "
        "content='width=device-width,initial-scale=1'><title>Phase 1 weather and sun</title>"
        f"<style>body{{background:{SURFACE};color:{INK};font-family:system-ui,-apple-system,'Segoe UI',"
        "sans-serif;max-width:980px;margin:24px auto;padding:0 16px}p{color:#52514e}</style></head><body>"
        "<h1>CoolScore Phase 1: weather and sun</h1><p>Simulation inputs, not bills. Weather: "
        "Open-Meteo ECMWF IFS 9 km (CC BY 4.0), bias-corrected to NOAA ISD airport observations. "
        "Facade sun: pvlib, Perez sky, ground albedo "
        f"{albedo:.2f}. Tables: docs/phase1_weather_sun.md.</p>" + "".join(parts) + "</body></html>"
    )
    (out_dir / "phase1_weather_sun.html").write_text(page, encoding="utf-8")

    stn_rows = []
    for isd_id, st in summary["stations"].items():
        for label, key in [("raw, all hours", "in_sample_raw"), ("corrected, all hours", "in_sample_corrected")]:
            stn_rows.append((f"{st['name']}: {label}", st[key]))
        for label in ("raw", "corrected"):
            stn_rows.append((f"{st['name']}: **{label}, 2025 holdout**", st["holdout"][label]))
    stn = pd.DataFrame({k: v for k, v in stn_rows}).T[
        ["temp_c_bias", "temp_c_rmse", "dewpoint_c_bias", "dewpoint_c_rmse", "cdh24_ratio",
         "jja_mean_daily_max_model", "jja_mean_daily_max_obs", "jja_mean_daily_min_model",
         "jja_mean_daily_min_obs"]
    ]
    stn.columns = ["T bias °C", "T RMSE °C", "Td bias °C", "Td RMSE °C", "CDH24 model/obs",
                   "Summer max model", "Summer max obs", "Summer min model", "Summer min obs"]

    micro_tbl = micro.copy()
    micro_tbl.columns = ["Summer mean daily max °C", "Summer mean daily min °C", "Summer mean dew point °C",
                         "Cooling degree-hours >24 °C /yr", "GHI kWh/m²/yr"]
    fac_tbl = fac.copy()
    fac_tbl.columns = ["Summer kWh/m²/day", "Winter kWh/m²/day", "Annual kWh/m²",
                       "Summer sun-weighted outdoor temp °C", "Sun while >38 °C, kWh/m²/yr"]

    check_lines = "\n".join(f"| {name} | {'✅ pass' if ok else '❌ FAIL'} | {detail} |"
                            for name, ok, detail in checks)
    grids = {s: summary["sites"][s][str(dataset.years()[0])]["grid"] for s in dataset.sites()}
    md = f"""# Phase 1: weather and sun

*Generated by `python tasks.py report-weather` · simulation inputs, not bills · charts:
[docs/figures/phase1_weather_sun.html](figures/phase1_weather_sun.html)*

## Data

| Item | Choice |
|---|---|
| Weather source | Open-Meteo Historical Weather API, model **ECMWF IFS 9 km** (`ecmwf_ifs`), hourly, {dataset.years()[0]}–{dataset.years()[-1]}; CC BY 4.0, free tier non-commercial |
| Why not ERA5 | ERA5 (0.25°) maps all three sites to the same grid cell (25.0 N, 55.25 E) |
| Sites (requested → model grid cell) | coastal 25.080, 55.140 → {grids['coastal']} · central 25.190, 55.270 → {grids['central']} · inland 24.900, 55.160 → {grids['inland']} |
| Radiation convention | preceding-hour mean; solar geometry at mid-interval. Check: DNI × cos(zenith) reproduces beam-horizontal within 0.3% (sun > 10°) |
| Observations | NOAA ISD hourly: Dubai International (41194099999), Al Maktoum International (41194599999); files end 2025-08-25 |
| Bias correction | additive per (month, hour), 3-h circular smoothing, on temperature and dew point; RH recomputed; radiation unchanged. Coastal uses the Dubai International correction (no coastal station, an assumption) |
| Facade sun | pvlib: solar position (SPA), Perez sky diffuse, isotropic ground reflection with albedo {albedo:.2f} (range 0.12–0.40 in `assumptions.yaml`), 8 vertical orientations |

## 1. Weather model vs airport observations

{_md_table(stn)}

Reading: raw IFS runs **{-summary['stations']['41194099999']['in_sample_raw']['temp_c_bias']:.1f} °C too cool** at Dubai International, mostly from late afternoon through the night (summer mean daily minimum
{summary['stations']['41194099999']['in_sample_raw']['jja_mean_daily_min_model']:.1f} vs {summary['stations']['41194099999']['in_sample_raw']['jja_mean_daily_min_obs']:.1f} °C observed), so it undercounts cooling degree-hours by about
{100 * (1 - summary['stations']['41194099999']['in_sample_raw']['cdh24_ratio']):.0f}%. Corrected on 2023–24 and tested on unseen 2025 hours, the error falls
to {summary['stations']['41194099999']['holdout']['corrected']['temp_c_rmse']:.2f} °C RMSE with cooling degree-hours at
{summary['stations']['41194099999']['holdout']['corrected']['cdh24_ratio']:.2f}× observed. **Honest caveat:** at Al Maktoum, the dew-point correction does not
carry over to 2025 (holdout bias {summary['stations']['41194599999']['holdout']['raw']['dewpoint_c_bias']:+.2f} → {summary['stations']['41194599999']['holdout']['corrected']['dewpoint_c_bias']:+.2f} °C): humidity varies year to year
more than the correction can capture. Treat inland latent loads as ±1 °C dew point uncertain.

## 2. Microclimates (corrected weather, 3-year means) → decision D8

{_md_table(micro_tbl)}

Coastal and central differ by about 1% in cooling degree-hours, 0.2 °C in summer dew point and 1.5% in sun, which is
below the weather data's own error. **Decision:** coastal communities use the central weather
(`config/communities.yaml` → `weather_site`); inland stays separate (cooler nights, hotter days, ~13% fewer
cooling degree-hours). A 9 km grid cannot resolve Marina sea-breeze effects; that limitation is documented.

## 3. Sun on facades (central site, albedo {albedo:.2f})

{_md_table(fac_tbl)}

## 4. Sanity checks (brief §4.1)

| Expectation | Result | Numbers |
|---|---|---|
{check_lines}

Published context (sanity bands, not inputs): annual GHI here is {micro['ghi_kwh_m2_per_yr'].min():,.0f}–{micro['ghi_kwh_m2_per_yr'].max():,.0f} kWh/m² per year. Search
results attribute ~2,000–2,100 kWh/m² for Dubai to DEWA's Shams Dubai guidelines and 2,100–2,300 kWh/m² across
the UAE to the UAE Solar Atlas (neither page could be opened; see `assumptions.yaml` → `ghi_published_range`). How
much this solar pattern changes **cooling cost** by orientation is checked against published UAE studies in Phase 2.

## Limitations

- The 9 km model grid smooths neighbourhood effects (sea breeze, street canyons). Neighbouring towers are
  modelled as obstruction in Phase 2, not here.
- The bias correction assumes 2023–25 model errors repeat; it fixes average (month, hour) error, not day-to-day error.
- Dust and haze are whatever the model contains; no local radiation measurements were available to check them.
"""
    (config.ROOT / "docs" / "phase1_weather_sun.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_report()
    print("wrote docs/phase1_weather_sun.md and docs/figures/phase1_weather_sun.html")
