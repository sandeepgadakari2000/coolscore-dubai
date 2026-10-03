"""Vectorised ISO 13790 5R1C hourly cooling engine (one thermal zone per unit).

Implements the simple hourly method of ISO 13790:2008 Annex C (equations
C.1-C.13) for many units at once: every hour is one step over numpy arrays
with one entry per unit. Ideal cooling to the setpoint (unlimited capacity),
no heating (Dubai winters are mild; temperatures float below the setpoint).

Additions outside ISO 13790 (which is sensible-only):

- **Latent load** whenever the coil runs: outdoor air entering untreated
  (infiltration + untreated ventilation) above the indoor humidity target,
  plus occupants' moisture.
- **Shading** by balconies and neighbouring towers (:mod:`.shading`).

Memory rule: hourly results are aggregated to monthly sums and daily peaks
inside the loop; full hourly arrays are only kept for small runs
(``keep_hourly=True``) used in tests and single-unit views.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from coolscore import config
from coolscore.physics import psychro, schedules, shading
from coolscore.physics.params import UnitParams
from coolscore.weather import solar

ORI = list(solar.ORIENTATIONS)


@dataclass
class PhysicsResult:
    """Aggregated cooling results, one row per unit (thermal energy, kWh_th)."""

    sens_kwh: np.ndarray          # (N, 12) sensible cooling per calendar month
    lat_kwh: np.ndarray           # (N, 12) latent cooling per calendar month
    load_x_dt_kwhk: np.ndarray    # (N, 12) sum of total load x (T_out - T_ref)+  [kWh K]
    cooling_hours: np.ndarray     # (N, 12) hours with the coil running
    appliance_kwh: np.ndarray     # (N, 12) appliance + lighting electricity (for DEWA slab position)
    peak_kw: np.ndarray           # (N,) highest hourly total load
    design_kw: np.ndarray         # (N,) 98th percentile of daily peak loads
    hourly: dict[str, np.ndarray] | None = None

    @property
    def total_kwh(self) -> np.ndarray:
        return self.sens_kwh + self.lat_kwh

    @property
    def annual_kwh(self) -> np.ndarray:
        return self.total_kwh.sum(axis=1)


@dataclass
class Network:
    """Per-unit constants of the 5R1C network and gain coefficients (all arrays)."""

    a_f: np.ndarray
    h_ve: np.ndarray
    h_is: np.ndarray
    h_w: np.ndarray
    h_ms: np.ndarray
    h_em: np.ndarray
    c_m: np.ndarray
    h1: np.ndarray
    h2: np.ndarray
    h3: np.ndarray
    frac_m: np.ndarray            # A_m / A_t
    frac_st: np.ndarray           # 1 - A_m/A_t - H_tr,w / (9.1 A_t)
    outdoor_air_m3s: np.ndarray   # untreated outdoor air reaching the unit coil


def network(p: UnitParams) -> Network:
    """5R1C conductances (W/K) and capacity (J/K) per ISO 13790 7.2 and 12.2."""
    iso = config.require("physics.iso13790_constants")
    rho_c = config.require("constants.air_volumetric_heat_capacity")
    slab = config.settings()["physics"]["slab_and_void_m"]
    a_f = p.floor_area_m2
    wall_area = (p.len1_m + p.len2_m) * p.floor_height_m
    a_win = p.wwr * wall_area
    a_op = wall_area - a_win
    volume = a_f * (p.floor_height_m - slab)
    outdoor_air = p.infiltration_ach * volume / 3600.0 + p.untreated_vent_m3s
    h_ve = rho_c * outdoor_air
    a_t = iso["lambda_at"] * a_f
    h_is = iso["h_is"] * a_t
    h_w = p.win_u * a_win
    h_op = p.wall_u * a_op + np.where(p.top_floor, p.roof_u * a_f, 0.0)
    a_m = p.am_per_af * a_f
    h_ms = iso["h_ms"] * a_m
    h_em = 1.0 / (1.0 / h_op - 1.0 / h_ms)
    h1 = 1.0 / (1.0 / h_ve + 1.0 / h_is)
    h2 = h1 + h_w
    h3 = 1.0 / (1.0 / h2 + 1.0 / h_ms)
    return Network(
        a_f=a_f, h_ve=h_ve, h_is=h_is, h_w=h_w, h_ms=h_ms, h_em=h_em, c_m=p.cm_per_af * a_f,
        h1=h1, h2=h2, h3=h3, frac_m=a_m / a_t, frac_st=1.0 - a_m / a_t - h_w / (iso["h_ms"] * a_t),
        outdoor_air_m3s=outdoor_air,
    )


class _Solar:
    """Per-unit constants and the per-hour evaluation of solar heat flow (W)."""

    def __init__(self, p: UnitParams, facades: pd.DataFrame):
        iso = config.require("physics.iso13790_constants")
        r_se = config.require("physics.external_surface_resistance")
        self.beam = np.stack([facades[f"{o}_beam"].to_numpy() for o in ORI])     # (8, T)
        self.sky = np.stack([facades[f"{o}_sky"].to_numpy() for o in ORI])
        self.ghi = facades["ghi_wm2"].to_numpy()
        elev, az = facades["sun_elev_deg"].to_numpy(), facades["sun_az_deg"].to_numpy()
        self.tanp = np.stack([solar.tan_profile_angle(elev, az, solar.ORIENTATIONS[o]) for o in ORI])

        wall = np.stack([p.len1_m, p.len2_m]) * p.floor_height_m               # (2, N)
        self.a_win = p.wwr * wall
        a_op = wall - self.a_win
        self.orient = np.stack([p.orient1, np.where(p.orient2 >= 0, p.orient2, 0)])
        g_eff = p.win_shgc * iso["f_w"] * (1.0 - iso["frame_fraction"]) * p.blind_factor
        self.win_coef = self.a_win * g_eff                                      # W per W/m2
        self.op_coef = p.opaque_absorptance * r_se * p.wall_u * a_op
        self.roof_coef = np.where(p.top_floor, p.opaque_absorptance * r_se * p.roof_u * p.floor_area_m2, 0.0)
        sky_loss = r_se * iso["h_r"] * iso["delta_theta_er"]
        self.sky_rad = (
            iso["f_r_wall"] * sky_loss * (p.wall_u * a_op.sum(axis=0) + p.win_u * self.a_win.sum(axis=0))
            + np.where(p.top_floor, iso["f_r_roof"] * sky_loss * p.roof_u * p.floor_area_m2, 0.0)
        )
        self.win_h = p.wwr * p.floor_height_m
        self.depth, self.frac, self.albedo = p.balcony_depth_m, p.balcony_frac, p.albedo
        self.tan_eps = np.tan(np.radians(p.obstruction_deg))
        open_sky = shading.diffuse_window_factor(0.0 * self.depth, self.win_h, p.obstruction_deg)
        under = shading.diffuse_window_factor(self.depth, self.win_h, p.obstruction_deg)
        self.diff_win = (1.0 - self.frac) * open_sky + self.frac * under
        self.diff_op = np.clip(1.0 - np.sin(np.radians(p.obstruction_deg)), 0.0, None)

    def at(self, t: int) -> np.ndarray:
        ground = 0.5 * self.albedo * self.ghi[t]
        total = self.roof_coef * self.ghi[t] - self.sky_rad
        for k in range(2):
            o = self.orient[k]
            beam, sky, tanp = self.beam[o, t], self.sky[o, t], self.tanp[o, t]
            beam_win = beam * shading.beam_window_factor(tanp, self.depth, self.win_h, self.frac, self.tan_eps)
            beam_op = beam * (np.nan_to_num(tanp, nan=-1.0) > self.tan_eps)
            total = total + self.win_coef[k] * (beam_win + sky * self.diff_win + ground)
            total = total + self.op_coef[k] * (beam_op + sky * self.diff_op + ground)
        return total


def simulate(p: UnitParams, weather: pd.DataFrame, facades: pd.DataFrame,
             keep_hourly: bool = False, solar_scale: float = 1.0) -> PhysicsResult:
    """Run the hourly engine for all units on one weather year.

    ``solar_scale`` multiplies every solar gain (0 removes the sun; used by
    invariant tests and the "no solar" counterfactual).
    """
    if not weather.index.equals(facades.index):
        raise ValueError("weather and facade irradiance must share the same hourly index")
    ps = config.settings()["physics"]
    people = config.require("physics.people_gains")
    lat_air = config.require("constants.latent_air_factor")
    t_ref = ps["cop_reference_temp_c"]
    wo = ps["window_opening"]

    net = network(p)
    sol = _Solar(p, facades)
    sch = schedules.build(weather.index)
    n, n_hours = p.n, len(weather)

    theta_e = weather["temp_c"].to_numpy()
    pressure_pa = weather["pressure_hpa"].to_numpy() * 100.0
    w_out = psychro.humidity_ratio_from_dewpoint(weather["dewpoint_c"].to_numpy(), pressure_pa)
    w_in = psychro.humidity_ratio_from_rh(p.setpoint_c, p.rh_target, float(pressure_pa.mean()))
    latent_air_coef = lat_air["air_density_kg_m3"] * lat_air["vapour_heat_j_kg"] * net.outdoor_air_m3s
    month = weather.index.month.to_numpy() - 1
    day = (weather.index.dayofyear.to_numpy() - 1)
    n_days = int(day.max()) + 1

    # Linear response of node temperatures to the cooling power (constant per unit).
    denom = net.c_m / 3600.0 + 0.5 * (net.h3 + net.h_em)
    d_mtot = net.h3 * net.h1 / (net.h2 * net.h_ve)
    d_mt = d_mtot / denom
    d_s = (net.h_ms * 0.5 * d_mt + net.h1 / net.h_ve) / (net.h_ms + net.h_w + net.h1)
    d_air = (net.h_is * d_s + 1.0) / (net.h_is + net.h_ve)

    sens = np.zeros((n, 12)); lat = np.zeros((n, 12)); ldt = np.zeros((n, 12)); hrs = np.zeros((n, 12))
    appl = np.zeros((n, 12))
    daily_peak = np.zeros((n, n_days))
    hourly = {k: np.zeros((n, n_hours)) for k in ("theta_air", "phi_hc", "q_lat", "phi_int", "phi_sol")} \
        if keep_hourly else None

    profile = p.profile
    sens_w = np.where(sch.resting[profile], people["resting_sensible_w"], people["awake_sensible_w"])
    lat_w = np.where(sch.resting[profile], people["resting_latent_w"], people["awake_latent_w"])
    presence = sch.presence[profile]
    appliance = sch.appliance[profile]
    away = sch.away[profile]

    theta_m_prev = np.full(n, 24.0)
    warmup = min(int(ps["warmup_hours"]), n_hours)
    for step, t in enumerate([*range(warmup), *range(n_hours)]):
        te = theta_e[t]
        phi_int = p.people * presence[:, t] * sens_w[:, t] + p.appliance_wm2 * net.a_f * appliance[:, t]
        phi_sol = solar_scale * sol.at(t)
        phi_ia = 0.5 * phi_int
        base = 0.5 * phi_int + phi_sol
        phi_m = net.frac_m * base
        phi_st = net.frac_st * base

        # ISO C.4-C.11 with phi_HC = 0
        phi_mtot = phi_m + net.h_em * te + net.h3 * (phi_st + net.h_w * te + net.h1 * (phi_ia / net.h_ve + te)) / net.h2
        theta_mt0 = (theta_m_prev * (net.c_m / 3600.0 - 0.5 * (net.h3 + net.h_em)) + phi_mtot) / denom
        theta_m0 = 0.5 * (theta_mt0 + theta_m_prev)
        theta_s0 = (net.h_ms * theta_m0 + phi_st + net.h_w * te + net.h1 * (te + phi_ia / net.h_ve)) / (
            net.h_ms + net.h_w + net.h1)
        theta_air0 = (net.h_is * theta_s0 + net.h_ve * te + phi_ia) / (net.h_is + net.h_ve)

        is_away = away[:, t]
        setpoint = p.setpoint_c + np.where(is_away & (p.away_mode == 1), p.setback_k, 0.0)
        cooling_allowed = ~(is_away & (p.away_mode == 2))
        need = cooling_allowed & (theta_air0 > setpoint)
        phi_hc = np.where(need, (setpoint - theta_air0) / d_air, 0.0)       # W, negative = cooling
        theta_m_prev = theta_mt0 + d_mt * phi_hc
        # Mild weather: occupants who open windows remove this heat with outdoor air, not the AC.
        ventilating = (p.window_opening & (presence[:, t] >= wo["min_presence"])
                       & (te <= setpoint - wo["outdoor_below_setpoint_k"]) & (te >= wo["min_outdoor_c"]))
        need = need & ~ventilating

        if step < warmup:
            continue
        cooling_w = np.where(need, -phi_hc, 0.0)
        q_lat = np.where(need, latent_air_coef * np.maximum(w_out[t] - w_in, 0.0)
                         + p.people * presence[:, t] * lat_w[:, t], 0.0)
        total_kw = (cooling_w + q_lat) / 1000.0
        m = month[t]
        sens[:, m] += cooling_w / 1000.0
        lat[:, m] += q_lat / 1000.0
        ldt[:, m] += total_kw * max(te - t_ref, 0.0)
        hrs[:, m] += need
        appl[:, m] += p.appliance_wm2 * net.a_f * appliance[:, t] / 1000.0
        np.maximum(daily_peak[:, day[t]], total_kw, out=daily_peak[:, day[t]])
        if hourly is not None:
            hourly["theta_air"][:, t] = theta_air0 + d_air * phi_hc
            hourly["phi_hc"][:, t] = np.where(need, phi_hc, 0.0)
            hourly["q_lat"][:, t] = q_lat
            hourly["phi_int"][:, t] = phi_int
            hourly["phi_sol"][:, t] = phi_sol

    return PhysicsResult(
        sens_kwh=sens, lat_kwh=lat, load_x_dt_kwhk=ldt, cooling_hours=hrs, appliance_kwh=appl,
        peak_kw=daily_peak.max(axis=1), design_kw=np.percentile(daily_peak, 98, axis=1), hourly=hourly,
    )
