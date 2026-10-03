"""DEWA slab pricing, used as the *marginal* cost of cooling electricity.

Cooling kWh sit on top of the household's other consumption, so they are
priced at the slabs the household actually reaches: cost(base + cooling) -
cost(base). Fixed meter charges don't change with cooling and are excluded.
"""

from __future__ import annotations

import numpy as np

from coolscore.billing.tariffs import DewaTariff


def slab_energy_charge(kwh, tariff: DewaTariff) -> np.ndarray:
    """Energy charge (AED, before fuel surcharge and VAT) for monthly consumption ``kwh``."""
    kwh = np.asarray(kwh, dtype=float)
    cost = np.zeros_like(kwh)
    lower = 0.0
    for upper, rate in zip(tariff.slab_limits, tariff.slab_rates):
        cost += rate * np.clip(np.minimum(kwh, upper) - lower, 0.0, None)
        lower = upper
    return cost


def marginal_charges(base_kwh, extra_kwh, tariff: DewaTariff) -> tuple[np.ndarray, np.ndarray]:
    """(energy, fuel surcharge) in AED, before VAT, for ``extra_kwh`` added on top of ``base_kwh``."""
    base = np.asarray(base_kwh, dtype=float)
    extra = np.asarray(extra_kwh, dtype=float)
    energy = slab_energy_charge(base + extra, tariff) - slab_energy_charge(base, tariff)
    return energy, extra * tariff.fuel_surcharge
