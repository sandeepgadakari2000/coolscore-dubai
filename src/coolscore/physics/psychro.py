"""Moist-air helpers for the simplified latent load."""

from __future__ import annotations

import numpy as np


def saturation_vapour_pressure_pa(t_c):
    """Saturation vapour pressure over water (Pa), Magnus form with WMO-2008 coefficients."""
    t = np.asarray(t_c, dtype=float)
    return 611.2 * np.exp(17.62 * t / (243.12 + t))


def humidity_ratio_from_dewpoint(dewpoint_c, pressure_pa):
    """Humidity ratio (kg water / kg dry air) from dew point and total pressure."""
    e = saturation_vapour_pressure_pa(dewpoint_c)
    return 0.622 * e / (np.asarray(pressure_pa, dtype=float) - e)


def humidity_ratio_from_rh(temp_c, rh_fraction, pressure_pa):
    """Humidity ratio from dry-bulb temperature and relative humidity (0-1)."""
    e = np.asarray(rh_fraction, dtype=float) * saturation_vapour_pressure_pa(temp_c)
    return 0.622 * e / (np.asarray(pressure_pa, dtype=float) - e)
