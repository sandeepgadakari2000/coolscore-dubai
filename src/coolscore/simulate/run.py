"""Build the simulated dataset: scenarios → physics → bills → ``data/simulated``.

Run with ``python tasks.py simulate``. Every row is a SIMULATED unit-year
(labelled so in the file); nothing here is a real bill.

Memory rule: physics runs in batches per (weather site, year) and returns
monthly aggregates only, so peak memory stays small even for 40,000 units.
"""

from __future__ import annotations

import json
import time
from dataclasses import fields

import numpy as np
import pandas as pd

from coolscore import config
from coolscore.billing import engine as billing
from coolscore.physics import engine
from coolscore.physics.params import UnitParams, build_params
from coolscore.simulate import scenarios

MONTHS = range(1, 13)


def dataset_path():
    return config.path("simulated") / "dataset.csv.gz"


def run(n: int | None = None, seed: int | None = None, progress: bool = True) -> pd.DataFrame:
    """Simulate ``n`` scenarios (defaults from settings) and return the dataset."""
    sim = config.settings()["simulation"]
    n = n or sim["n_scenarios"]
    seed = config.settings()["random_seed"] if seed is None else seed
    t0 = time.time()
    df = scenarios.sample(n, seed)
    rng = np.random.default_rng(seed + 1)
    params = build_params(scenarios.to_specs(df), rng)
    hidden = params.to_frame().add_prefix("h_")

    out = {k: np.zeros((n, 12)) for k in ("sens", "lat", "ldt", "hours", "appl")}
    peak, design = np.zeros(n), np.zeros(n)
    for (site, year), idx in df.groupby(["weather_site", "year"]).indices.items():
        res = engine.run_site_year(params.subset(idx), site, int(year), batch_size=sim["batch_size"])
        out["sens"][idx], out["lat"][idx], out["ldt"][idx] = res.sens_kwh, res.lat_kwh, res.load_x_dt_kwhk
        out["hours"][idx], out["appl"][idx] = res.cooling_hours, res.appliance_kwh
        peak[idx], design[idx] = res.peak_kw, res.design_kw
        if progress:
            print(f"  physics {site} {year}: {len(idx)} units, {time.time() - t0:.0f} s elapsed", flush=True)

    bills = {"tenant": np.zeros((n, 12)), "landlord": np.zeros((n, 12))}
    contracted = np.zeros(n)
    bp_all = billing.billing_params(df["system"].tolist(), df["payer"].tolist(), df["size_sqft"].to_numpy(),
                                    np.random.default_rng(seed + 2))
    for year, idx in df.groupby("year").indices.items():
        from coolscore.physics.rc5r1c import PhysicsResult

        phys = PhysicsResult(sens_kwh=out["sens"][idx], lat_kwh=out["lat"][idx], load_x_dt_kwhk=out["ldt"][idx],
                             cooling_hours=out["hours"][idx], appliance_kwh=out["appl"][idx],
                             peak_kw=peak[idx], design_kw=design[idx])
        bp = billing.BillingParams(**{f.name: getattr(bp_all, f.name)[idx] for f in fields(billing.BillingParams)})
        b = billing.compute(phys, bp, int(year))
        bills["tenant"][idx], bills["landlord"][idx], contracted[idx] = b.tenant_total, b.landlord_total, b.contracted_rt

    data = pd.concat([df.reset_index(drop=True), hidden], axis=1)
    data["h_sqft_per_rt"] = bp_all.sqft_per_rt
    data["h_installed_factor"] = bp_all.installed_factor
    data["h_fan_w_per_kw"] = bp_all.fan_w_per_kw
    data["h_other_kwh_month"] = bp_all.other_kwh_month
    total = out["sens"] + out["lat"]
    for m in MONTHS:
        data[f"kwh_th_m{m:02d}"] = total[:, m - 1]
        data[f"tenant_aed_m{m:02d}"] = bills["tenant"][:, m - 1]
        data[f"landlord_aed_m{m:02d}"] = bills["landlord"][:, m - 1]
    data["kwh_th_annual"] = total.sum(axis=1)
    data["latent_share"] = out["lat"].sum(axis=1) / np.maximum(total.sum(axis=1), 1e-9)
    data["peak_kw"], data["design_kw"], data["contracted_rt"] = peak, design, contracted
    data["tenant_aed_annual"] = bills["tenant"].sum(axis=1)
    data["landlord_aed_annual"] = bills["landlord"].sum(axis=1)
    data["simulated"] = True
    elapsed = time.time() - t0
    if progress:
        print(f"simulated {n} scenarios in {elapsed:.0f} s")

    out_path = dataset_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(out_path, index=False, float_format="%.4g", compression={"method": "gzip", "mtime": 0})
    out_path.with_name("dataset_meta.json").write_text(json.dumps({
        "n": n, "seed": seed, "seconds": round(elapsed, 1), "label": "SIMULATED - not real bills",
        "columns": len(data.columns)}, indent=2), encoding="utf-8")
    return data


def load_dataset() -> pd.DataFrame:
    return pd.read_csv(dataset_path())


def physics_columns() -> list[str]:
    return ["h_" + f.name for f in fields(UnitParams)]


if __name__ == "__main__":
    run()
