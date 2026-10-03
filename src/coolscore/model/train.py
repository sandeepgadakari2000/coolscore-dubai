"""Train the surrogate: quantile models, a fidelity check, CoolScore bands, monthly shapes.

Run with ``python tasks.py train`` after ``tasks.py simulate``. Writes the
deployable artifact ``data/demo/coolscore_model.pkl.xz`` and metrics
``data/demo/model_metrics.json`` (both small enough for Streamlit Cloud).

Two accuracy numbers (decision D2):
- **Fidelity**: a model given *every* simulation input (including hidden
  building and behaviour variables) vs held-out physics runs. Target R² >= 0.95.
- **Listing-only / detailed**: what the app actually knows. Hidden variation
  makes perfect prediction impossible; reported with interval coverage.
"""

from __future__ import annotations

import datetime as dt
import json
import lzma
import pickle
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from coolscore import config
from coolscore.model import features as F
from coolscore.simulate import run as sim

TARGETS = {"annual": "tenant_aed_annual", "summer": "tenant_aed_m08", "winter": "tenant_aed_m01"}
HGB_PARAMS = dict(max_iter=350, learning_rate=0.07, max_leaf_nodes=31, min_samples_leaf=30,
                  l2_regularization=0.1, early_stopping=False)


def artifact_path():
    return config.path("demo") / "coolscore_model.pkl.xz"


def metrics_path():
    return config.path("demo") / "model_metrics.json"


def _model(features: list[str], quantile: float | None, seed: int) -> HistGradientBoostingRegressor:
    mono = {"size_sqft": 1}
    if "setpoint_c" in features:
        mono["setpoint_c"] = -1
    kw = dict(HGB_PARAMS, random_state=seed, categorical_features=[f for f in F.CATEGORICAL if f in features],
              monotonic_cst=mono)
    if quantile is None:
        return HistGradientBoostingRegressor(loss="squared_error", **kw)
    return HistGradientBoostingRegressor(loss="quantile", quantile=quantile, **kw)


def _metrics(y: np.ndarray, p10: np.ndarray, p50: np.ndarray, p90: np.ndarray) -> dict:
    big = y > 500  # MAPE only where the bill is material (chiller-free fan bills are tiny)
    return {
        "r2": float(r2_score(y, p50)),
        "mae_aed": float(mean_absolute_error(y, p50)),
        "mape_pct_bills_over_500": float(100 * np.mean(np.abs(p50[big] - y[big]) / y[big])),
        "p10_p90_coverage": float(np.mean((y >= p10) & (y <= p90))),
        "median_interval_width_aed": float(np.median(p90 - p10)),
    }


def reference_frame(df: pd.DataFrame) -> pd.DataFrame:
    """The same units under the standardised CoolScore conditions (decision D1)."""
    ref = config.settings()["simulation"]["score_reference"]
    out = df.copy()
    out["system"], out["payer"] = ref["system"], ref["payer"]
    out["occupancy"], out["setpoint_c"] = ref["occupancy"], ref["setpoint_c"]
    out["household_size"] = out["bedrooms"] + 1
    return out


def train(data: pd.DataFrame | None = None, seed: int | None = None, progress: bool = True) -> dict:
    data = sim.load_dataset() if data is None else data
    seed = config.settings()["random_seed"] if seed is None else seed
    settings = config.settings()
    quantiles = settings["model"]["quantiles"]
    t0 = time.time()

    rng = np.random.default_rng(seed)
    r = rng.random(len(data))
    test = r < settings["simulation"]["holdout_fraction"]
    calib = (~test) & (r < settings["simulation"]["holdout_fraction"] + 0.1)   # conformal calibration split
    fit = ~test & ~calib
    X_all = F.encode(data)
    conformal: dict = {}
    models: dict = {}
    metrics: dict = {"variants": {}, "fidelity": {}}
    for variant, feats in F.VARIANTS.items():
        models[variant] = {}
        metrics["variants"][variant] = {}
        conformal[variant] = {}
        for tname, col in TARGETS.items():
            y = data[col].to_numpy()
            preds = {}
            models[variant][tname] = {}
            cal = {}
            for q in quantiles:
                m = _model(feats, q, seed).fit(X_all.loc[fit, feats], np.log1p(y[fit]))
                models[variant][tname][q] = m
                preds[q] = m.predict(X_all.loc[test, feats])
                cal[q] = m.predict(X_all.loc[calib, feats])
            # Conformalised quantile regression (Romano et al. 2019) in log space: widen P10/P90 by the
            # calibration-set quantile of the nonconformity score so held-out coverage matches nominal.
            lo_q, hi_q = quantiles[0], quantiles[-1]
            y_cal = np.log1p(y[calib])
            score = np.maximum(cal[lo_q] - y_cal, y_cal - cal[hi_q])
            level = min(1.0, (1 + 1 / calib.sum()) * (hi_q - lo_q))
            delta = float(np.quantile(score, level))
            conformal[variant][tname] = delta
            preds[lo_q], preds[hi_q] = preds[lo_q] - delta, preds[hi_q] + delta
            p = np.sort(np.expm1(np.stack([preds[q] for q in quantiles])), axis=0)
            metrics["variants"][variant][tname] = _metrics(y[test], p[0], p[1], p[2])
            if progress:
                print(f"  {variant}/{tname}: R2 {metrics['variants'][variant][tname]['r2']:.3f} "
                      f"coverage {metrics['variants'][variant][tname]['p10_p90_coverage']:.2f} "
                      f"({time.time() - t0:.0f} s)", flush=True)

    # Fidelity: all inputs, including hidden variables and the weather year.
    hidden = [c for c in sim.physics_columns() if c in data] + ["h_sqft_per_rt", "h_installed_factor",
                                                                 "h_fan_w_per_kw", "h_other_kwh_month"]
    X_fid = pd.concat([X_all[F.VARIANTS["detailed"]], data[hidden].astype(float), data[["year"]]], axis=1)
    for name, col in {"annual_tenant_aed": "tenant_aed_annual", "annual_kwh_th": "kwh_th_annual"}.items():
        y = data[col].to_numpy()
        m = HistGradientBoostingRegressor(loss="squared_error", max_iter=600, learning_rate=0.08,
                                          max_leaf_nodes=63, min_samples_leaf=20, random_state=seed,
                                          early_stopping=False,
                                          categorical_features=[f for f in F.CATEGORICAL if f in X_fid])
        m.fit(X_fid[fit | calib], np.log1p(y[fit | calib]))
        p = np.expm1(m.predict(X_fid[test]))
        metrics["fidelity"][name] = {"r2": float(r2_score(y[test], p)), "mae": float(mean_absolute_error(y[test], p))}
    metrics["fidelity"]["target_r2"] = settings["model"]["fidelity_r2_target"]

    # CoolScore bands on standardised cost intensity across the simulated stock.
    ref = F.encode(reference_frame(data))[F.VARIANTS["detailed"]]
    intensity = np.expm1(models["detailed"]["annual"][0.5].predict(ref)) / data["size_sqft"].to_numpy()
    cuts = [round(float(np.quantile(intensity, q)), 2) for q in (0.2, 0.4, 0.6, 0.8)]

    # Typical monthly shape of the tenant bill (share of annual) by system, payer and site.
    month_cols = [f"tenant_aed_m{m:02d}" for m in range(1, 13)]
    shares = data[month_cols].div(data["tenant_aed_annual"].replace(0, np.nan), axis=0)
    monthly = shares.groupby([data["system"], data["payer"], data["weather_site"]]).median()
    monthly_shares = {"|".join(k): [round(float(v), 4) for v in row] for k, row in monthly.iterrows()}

    artifact = {
        "version": 1,
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "n_scenarios": int(len(data)), "seed": seed, "quantiles": quantiles,
        "features": F.VARIANTS, "models": models, "conformal_log_delta": conformal,
        "score_cuts_aed_per_sqft": cuts, "score_letters": ["A", "B", "C", "D", "E"],
        "monthly_shares": monthly_shares,
        "label": "Trained on SIMULATED physics + billing scenarios, not real bills",
    }
    path = artifact_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with lzma.open(path, "wb", preset=6) as fh:
        pickle.dump(artifact, fh, protocol=pickle.HIGHEST_PROTOCOL)
    metrics.update({
        "n_train": int(fit.sum()), "n_calibration": int(calib.sum()), "n_test": int(test.sum()),
        "conformal_log_delta": conformal, "seconds": round(time.time() - t0, 1),
        "artifact_mb": round(path.stat().st_size / 1e6, 2), "score_cuts_aed_per_sqft": cuts,
        "stock_intensity_pctiles": {str(q): round(float(np.quantile(intensity, q)), 3) for q in (0.05, 0.5, 0.95)},
    })
    metrics_path().write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if progress:
        print(json.dumps({"fidelity": metrics["fidelity"], "artifact_mb": metrics["artifact_mb"],
                          "cuts": cuts, "seconds": metrics["seconds"]}, indent=2))
    return metrics


if __name__ == "__main__":
    train()
