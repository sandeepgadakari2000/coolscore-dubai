"""Literal, single-unit ISO 13790 Annex C implementation (test oracle).

Written to mirror the standard's text line by line - two trial runs with
Φ_HC = 0 and Φ_HC = 10 W/m² (C.4 steps 1-3), linear interpolation (C.13),
then a final run with the required power - rather than for speed. The
vectorised engine in :mod:`.rc5r1c` must reproduce it to rounding error.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScalarNetwork:
    """5R1C constants for one unit (W/K, J/K, m²)."""

    a_f: float
    h_ve: float
    h_is: float
    h_w: float
    h_ms: float
    h_em: float
    c_m: float
    frac_m: float
    frac_st: float


def _temperatures(net: ScalarNetwork, theta_m_prev: float, theta_e: float, phi_int: float,
                  phi_sol: float, phi_hc: float) -> tuple[float, float, float, float]:
    """Equations C.1-C.11 for one hour; returns (θm,t, θm, θs, θair)."""
    h1 = 1.0 / (1.0 / net.h_ve + 1.0 / net.h_is)                       # C.6
    h2 = h1 + net.h_w                                                  # C.7
    h3 = 1.0 / (1.0 / h2 + 1.0 / net.h_ms)                             # C.8
    phi_ia = 0.5 * phi_int                                             # C.1
    phi_m = net.frac_m * (0.5 * phi_int + phi_sol)                     # C.2
    phi_st = net.frac_st * (0.5 * phi_int + phi_sol)                   # C.3
    theta_sup = theta_e
    phi_mtot = (phi_m + net.h_em * theta_e
                + h3 * (phi_st + net.h_w * theta_e + h1 * ((phi_ia + phi_hc) / net.h_ve + theta_sup)) / h2)  # C.5
    theta_mt = ((theta_m_prev * (net.c_m / 3600.0 - 0.5 * (h3 + net.h_em)) + phi_mtot)
                / (net.c_m / 3600.0 + 0.5 * (h3 + net.h_em)))          # C.4
    theta_m = 0.5 * (theta_mt + theta_m_prev)                          # C.9
    theta_s = ((net.h_ms * theta_m + phi_st + net.h_w * theta_e + h1 * (theta_sup + (phi_ia + phi_hc) / net.h_ve))
               / (net.h_ms + net.h_w + h1))                            # C.10
    theta_air = (net.h_is * theta_s + net.h_ve * theta_sup + phi_ia + phi_hc) / (net.h_is + net.h_ve)  # C.11
    return theta_mt, theta_m, theta_s, theta_air


def run(net: ScalarNetwork, theta_e: list[float], phi_int: list[float], phi_sol: list[float],
        setpoint: list[float], cooling_allowed: list[bool], theta_m0: float) -> tuple[list[float], list[float]]:
    """Hour-by-hour ideal cooling; returns (Φ_HC list in W, θair list in °C)."""
    theta_m_prev = theta_m0
    phis, airs = [], []
    for te, pi, ps_, sp, allowed in zip(theta_e, phi_int, phi_sol, setpoint, cooling_allowed):
        mt0, _, _, air0 = _temperatures(net, theta_m_prev, te, pi, ps_, 0.0)            # step 1
        if not allowed or air0 <= sp:
            phis.append(0.0); airs.append(air0); theta_m_prev = mt0
            continue
        phi10 = -10.0 * net.a_f                                                           # step 2 (cooling)
        _, _, _, air10 = _temperatures(net, theta_m_prev, te, pi, ps_, phi10)
        phi_un = phi10 * (sp - air0) / (air10 - air0)                                     # C.13
        mt, _, _, air = _temperatures(net, theta_m_prev, te, pi, ps_, phi_un)            # step 3
        phis.append(phi_un); airs.append(air); theta_m_prev = mt
    return phis, airs
