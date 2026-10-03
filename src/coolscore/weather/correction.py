"""Bias-correct modelled temperature and dew point against airport observations.

Reanalysis/forecast grids miss Dubai's urban night-time heat: at Dubai
International the ECMWF IFS 9 km series undercounts cooling degree-hours by
about 20% (see ``docs/evidence/weather.md``). We learn an additive
correction per (month, hour of day) from overlapping observed hours and apply
it to the microclimate sites. Radiation is not changed; relative humidity is
recomputed from the corrected temperature and dew point.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CORRECTED_VARS: tuple[str, ...] = ("temp_c", "dewpoint_c")


def fit_bias(model: pd.DataFrame, obs: pd.DataFrame, smooth_hours: int = 3) -> pd.DataFrame:
    """Mean (observed − model) per (month, hour), smoothed circularly over hours.

    Returns a frame indexed by ``(month, hour)`` with one column per corrected variable.
    """
    joined = model[list(CORRECTED_VARS)].join(
        obs[list(CORRECTED_VARS)], lsuffix="_model", rsuffix="_obs", how="inner"
    ).dropna()
    diff = pd.DataFrame(
        {v: joined[f"{v}_obs"] - joined[f"{v}_model"] for v in CORRECTED_VARS}, index=joined.index
    )
    table = diff.groupby([diff.index.month, diff.index.hour]).mean()
    table.index.names = ["month", "hour"]
    full = pd.MultiIndex.from_product([range(1, 13), range(24)], names=["month", "hour"])
    table = table.reindex(full)
    if table.isna().any().any():
        raise ValueError("bias table has empty (month, hour) cells; not enough overlap")
    if smooth_hours > 1:
        half = smooth_hours // 2
        smoothed = []
        for _, block in table.groupby(level="month"):
            vals = block.to_numpy()
            padded = np.concatenate([vals[-half:], vals, vals[:half]])
            kernel = np.ones(smooth_hours) / smooth_hours
            smoothed.append(
                np.column_stack([np.convolve(padded[:, j], kernel, "valid") for j in range(vals.shape[1])])
            )
        table = pd.DataFrame(np.vstack(smoothed), index=table.index, columns=table.columns)
    return table


def relative_humidity(temp_c, dewpoint_c):
    """Relative humidity (%) from temperature and dew point (Magnus, WMO-2008 coefficients)."""

    def es(t):
        return 6.112 * np.exp(17.62 * t / (243.12 + t))

    return 100.0 * es(dewpoint_c) / es(temp_c)


def apply_bias(weather: pd.DataFrame, table: pd.DataFrame) -> pd.DataFrame:
    """Add the (month, hour) correction, cap dew point at temperature, recompute RH."""
    out = weather.copy()
    keys = pd.MultiIndex.from_arrays([out.index.month, out.index.hour])
    shift = table.reindex(keys)
    for v in CORRECTED_VARS:
        out[v] = out[v].to_numpy() + shift[v].to_numpy()
    out["dewpoint_c"] = np.minimum(out["dewpoint_c"], out["temp_c"])
    out["rh_pct"] = relative_humidity(out["temp_c"], out["dewpoint_c"]).clip(0, 100)
    return out
