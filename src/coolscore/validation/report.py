"""Real-bill validation: runs automatically whenever anonymised bills are in ``data/real_bills``.

For each billed unit we rebuild the unit from the bill's (anonymised) facts,
run the physics + billing engines with central hidden values on the bill's
weather year, and compare month by month:

- **consumption** (RTh) → tests the physics,
- **capacity charge** → tests the contracted-capacity assumption (when the
  bill states the unit's RT, that figure is used for the cost comparison),
- **total cooling bill** (AED) → what a tenant sees.

Metrics: MAE, MAPE, share of months within ±20 %, bias. A simple residual
calibration (median actual/predicted ratio per cooling system, once there
are enough months) is written to ``data/demo/calibration.json``.
Also compares simulated typical bills with a published rough band.
Run with ``python tasks.py validate``; the app's Methodology page calls it too.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from coolscore import config
from coolscore.billing import engine as billing
from coolscore.physics import engine
from coolscore.physics.params import ListingSpec, build_params, weather_site
from coolscore.validation import pii
from coolscore.weather import dataset

MIN_MONTHS_FOR_CALIBRATION = 12
FLOORS_FOR_BAND = {"low_rise_le10": 8, "mid_rise_11_25": 18, "high_rise_26_50": 38, "super_tall_51_plus": 60}


def bills_folder() -> Path:
    return config.path("real_bills")


def load_bills(folder: Path | None = None) -> pd.DataFrame:
    """All anonymised bill rows (every CSV except the template); PII-checked first."""
    folder = folder or bills_folder()
    problems = pii.check_folder(folder)
    if problems:
        raise ValueError("PII check failed: " + "; ".join(problems))
    frames = [pd.read_csv(p) for p in sorted(folder.glob("*.csv")) if p.name != pii.TEMPLATE_NAME]
    frames = [f for f in frames if len(f)]
    if not frames:
        return pd.DataFrame(columns=pii.allowed_columns(folder))
    df = pd.concat(frames, ignore_index=True)
    return df[df["consent"].astype(str).str.lower() == "yes"]


def _spec(u: pd.Series) -> tuple[ListingSpec, list[str]]:
    """A ListingSpec from a bill's unit facts; returns the fields we had to assume."""
    assumed = []

    def val(col, default):
        v = u.get(col)
        if pd.isna(v) or str(v).strip() in ("", "unknown"):
            assumed.append(col)
            return default
        return v

    total = FLOORS_FOR_BAND.get(val("total_floors_band", "high_rise_26_50"), 38)
    band = val("floor_band", "mid")
    floor = {"low_1_5": 3, "mid": max(1, total // 2), "high": max(1, int(total * 0.8)), "top": total}.get(band, total // 2)
    occ = val("home_daytime", "no")
    spec = ListingSpec(
        community=val("community", "Business Bay"), era_band=val("building_era_band", "2005_2014"),
        size_sqft=float(val("size_sqft", 800)), bedrooms=int(val("bedrooms", 1)), floor=int(floor),
        total_floors=int(total), facing=str(val("facing", "S")), glass=val("glass_amount", "medium"),
        balcony=val("balcony", "none"), obstruction=val("view_obstruction", "partial"),
        household_size=int(val("household_size", int(u.get("bedrooms", 1) or 1) + 1)),
        occupancy="away_daytime" if str(occ) == "no" else "home_daytime",
        setpoint_c=float(val("typical_setpoint_c", 24.0)),
    )
    return spec, assumed


def predict_bills(bills: pd.DataFrame) -> pd.DataFrame:
    """One row per bill month with predicted and actual values side by side."""
    rows = []
    years = dataset.years()
    for unit_ref, unit_rows in bills.groupby("unit_ref"):
        u = unit_rows.iloc[0]
        spec, assumed = _spec(u)
        system = u.get("cooling_system") if u.get("cooling_system") in billing.SYSTEMS else "district_cooling"
        payer = u.get("cooling_payer") if u.get("cooling_payer") in billing.PAYERS else "tenant"
        params = build_params([spec])
        for month_str, month_rows in unit_rows.groupby("bill_month"):
            ts = pd.Timestamp(str(month_str) + "-01")
            year = min(years, key=lambda y: abs(y - ts.year))
            phys = engine.run_site_year(params, weather_site(spec), year)
            bp = billing.billing_params([system], [payer], [spec.size_sqft])
            if pd.notna(u.get("contracted_capacity_rt")) and float(u["contracted_capacity_rt"]) > 0:
                bp.sqft_per_rt = np.array([spec.size_sqft / float(u["contracted_capacity_rt"])])
            b = billing.compute(phys, bp, year)
            m = ts.month - 1
            r = month_rows.iloc[0]
            vat = 1 + config.require("billing.vat_rate")
            provider_pred = (b.dc_capacity + b.dc_consumption + b.dc_fuel + b.dc_meter
                             + b.plant_consumption + b.plant_fuel)[0, m] * vat
            rows.append({
                "unit_ref": unit_ref, "bill_month": str(month_str), "system": system, "weather_year": year,
                "assumed_fields": ",".join(assumed),
                "rth_pred": float(b.rth[0, m]), "rth_actual": r.get("dc_consumption_rth"),
                "capacity_pred": float(b.dc_capacity[0, m]), "capacity_actual": r.get("dc_capacity_aed"),
                "bill_pred": float(provider_pred), "bill_actual": r.get("dc_total_aed"),
                "dewa_kwh_pred": float(b.cooling_kwh_e[0, m] + phys.appliance_kwh[0, m]),
                "dewa_kwh_actual": r.get("dewa_electricity_kwh"),
            })
    return pd.DataFrame(rows)


def _metrics(pred: pd.Series, actual: pd.Series) -> dict | None:
    ok = actual.notna() & pred.notna() & (pd.to_numeric(actual, errors="coerce") > 0)
    if ok.sum() == 0:
        return None
    a, p = pd.to_numeric(actual[ok]), pred[ok].astype(float)
    err = (p - a) / a
    return {"n_months": int(ok.sum()), "mae": float(np.mean(np.abs(p - a))), "mape_pct": float(100 * np.mean(np.abs(err))),
            "within_20pct": float(np.mean(np.abs(err) <= 0.2)), "bias_pct": float(100 * np.median(err))}


def sanity_band_check() -> list[dict]:
    """Simulated typical (P50) district-cooling tenant bills vs a published rough band, by bedrooms."""
    from coolscore.simulate import run as sim

    band = config.require("sanity_bands.typical_monthly_bills_by_bedrooms")
    try:
        data = sim.load_dataset()
    except FileNotFoundError:
        # The simulated dataset is regenerable and not committed (e.g. on Streamlit Cloud); use the copy
        # `tasks.py validate` saved with the demo artifacts.
        cached = config.path("demo") / "validation.json"
        return json.loads(cached.read_text(encoding="utf-8")).get("sanity_band", []) if cached.exists() else []
    dc = data[(data["system"] == "district_cooling") & (data["payer"] == "tenant")]
    out = []
    for beds, (lo, hi) in band.items():
        sub = dc[dc["bedrooms"] == int(beds)]
        if len(sub):
            med = float(sub["tenant_aed_annual"].median() / 12)
            out.append({"bedrooms": int(beds), "simulated_median_month_aed": round(med), "band_low": lo,
                        "band_high": hi, "inside_band": bool(lo <= med <= hi), "n": int(len(sub))})
    return out


def run(write: bool = True) -> dict:
    bills = load_bills()
    status = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "n_units": int(bills["unit_ref"].nunique()) if len(bills) else 0, "n_bill_months": int(len(bills)),
              "sanity_band": sanity_band_check()}
    if len(bills):
        comp = predict_bills(bills)
        status["consumption_rth"] = _metrics(comp["rth_pred"], comp["rth_actual"])
        status["capacity_charge"] = _metrics(comp["capacity_pred"], comp["capacity_actual"])
        status["total_bill"] = _metrics(comp["bill_pred"], comp["bill_actual"])
        status["dewa_kwh"] = _metrics(comp["dewa_kwh_pred"], comp["dewa_kwh_actual"])
        calibration = {}
        for system, g in comp.groupby("system"):
            ok = pd.to_numeric(g["bill_actual"], errors="coerce") > 0
            if ok.sum() >= MIN_MONTHS_FOR_CALIBRATION:
                calibration[system] = float(np.median(pd.to_numeric(g.loc[ok, "bill_actual"]) / g.loc[ok, "bill_pred"]))
        status["calibration_factor_by_system"] = calibration
        if write:
            comp.to_csv(config.path("demo") / "validation_comparison.csv", index=False)
    if write:
        (config.path("demo") / "validation.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        _write_markdown(status)
    return status


def _write_markdown(s: dict) -> None:
    lines = ["# Real-bill validation report", "",
             f"*Generated {s['generated']} by `python tasks.py validate` (also run by the app).*", ""]
    if s["n_units"] == 0:
        lines += ["**Status: no real bills yet.** Real-world accuracy is **not yet validated**. Add anonymised "
                  "figures to `data/real_bills/` (see its README) and re-run; this report updates automatically.", ""]
    else:
        lines += [f"**{s['n_units']} units, {s['n_bill_months']} bill months.**", "",
                  "| Comparison | Months | MAE | MAPE % | Within ±20 % | Median bias % |", "|---|---|---|---|---|---|"]
        for key, label in [("consumption_rth", "Consumption (RTh)"), ("capacity_charge", "Capacity charge (AED)"),
                           ("total_bill", "Total cooling bill (AED)"), ("dewa_kwh", "DEWA electricity (kWh)")]:
            m = s.get(key)
            if m:
                lines.append(f"| {label} | {m['n_months']} | {m['mae']:,.0f} | {m['mape_pct']:.0f} | "
                             f"{m['within_20pct']:.0%} | {m['bias_pct']:+.0f} |")
        cal = s.get("calibration_factor_by_system") or {}
        lines += ["", "Residual calibration (median actual ÷ predicted, ≥ "
                  f"{MIN_MONTHS_FOR_CALIBRATION} months): " + (", ".join(f"{k} × {v:.2f}" for k, v in cal.items())
                                                              or "not enough months yet") + ".", ""]
    if s["sanity_band"]:
        lines += ["## Sanity check against a published rough band", "",
                  "Simulated typical district-cooling bills (tenant pays, median month) vs an independent guide's "
                  "ranges (`assumptions.yaml` → `sanity_bands`; rough, unverified):", "",
                  "| Bedrooms | Simulated median AED/month | Published band | Inside? |", "|---|---|---|---|"]
        for r in s["sanity_band"]:
            lines.append(f"| {r['bedrooms'] or 'Studio'} | {r['simulated_median_month_aed']:,} | "
                         f"{r['band_low']:,}–{r['band_high']:,} | {'yes' if r['inside_band'] else 'no'} |")
    (config.ROOT / "docs" / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
