"""Phase 2: 5R1C engine correctness and physics invariants (brief §9)."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from coolscore.physics import engine, psychro, rc5r1c, reference, schedules, shading
from coolscore.physics.params import ListingSpec, build_params
from coolscore.weather import dataset, solar

YEAR = 2024
BASE = ListingSpec(community="Business Bay", era_band="2005_2014", size_sqft=800, bedrooms=1,
                   floor=15, total_floors=30, facing="W", glass="medium", balcony="none",
                   obstruction="partial")
SUMMER = slice(5, 8)  # Jun-Aug


def _run(specs, **replace_kwargs):
    p = build_params(specs)
    if replace_kwargs:
        p = p.replace(**replace_kwargs)
    return engine.run_site_year(p, "central", YEAR)


@pytest.fixture(scope="module")
def variants() -> dict[str, float]:
    """Annual and summer loads for one-at-a-time variants of the base unit (one engine run)."""
    cases = {
        "base": BASE,
        "north": replace(BASE, facing="N"),
        "east": replace(BASE, facing="E"),
        "glass_low": replace(BASE, glass="low"),
        "glass_high": replace(BASE, glass="floor_to_ceiling"),
        "balcony_deep": replace(BASE, balcony="deep"),
        "obstruction_open": replace(BASE, obstruction="open"),
        "obstruction_heavy": replace(BASE, obstruction="heavy"),
        "top_floor": replace(BASE, floor=30),
        "mid_floor": replace(BASE, floor=15),
        "setpoint_22": replace(BASE, setpoint_c=22.0),
        "setpoint_26": replace(BASE, setpoint_c=26.0),
        "people_1": replace(BASE, household_size=1),
        "people_5": replace(BASE, household_size=5),
        "corner": replace(BASE, facing="W+N"),
        "a3_glass_low": replace(BASE, era_band="2015_2021", glass="low"),
        "a3_glass_high": replace(BASE, era_band="2015_2021", glass="floor_to_ceiling"),
    }
    names = list(cases)
    r = _run(list(cases.values()))
    out = {}
    for i, name in enumerate(names):
        out[name] = r.annual_kwh[i]
        out[name + "_summer"] = r.total_kwh[i, SUMMER].sum()
        out[name + "_peak"] = r.design_kw[i]
    return out


# --- engine correctness -------------------------------------------------------

def test_vectorised_engine_matches_literal_iso_annex_c() -> None:
    specs = [replace(BASE, facing="W+N", floor=30, era_band="before_2005"),
             replace(BASE, facing="S", balcony="deep", occupancy="home_daytime"),
             replace(BASE, facing="E", glass="floor_to_ceiling", era_band="2022_plus")]
    p = build_params(specs).replace(window_opening=False, away_mode=[0, 1, 2])
    weather = dataset.load_weather("central", YEAR).iloc[: 24 * 40]
    facades = solar.load_facades("central", YEAR).iloc[: 24 * 40]
    res = rc5r1c.simulate(p, weather, facades, keep_hourly=True)
    net = rc5r1c.network(p)
    sch = schedules.build(weather.index)
    warm = 168
    order = [*range(warm), *range(len(weather))]
    for i in range(p.n):
        scalar = reference.ScalarNetwork(
            a_f=net.a_f[i], h_ve=net.h_ve[i], h_is=net.h_is[i], h_w=net.h_w[i], h_ms=net.h_ms[i],
            h_em=net.h_em[i], c_m=net.c_m[i], frac_m=net.frac_m[i], frac_st=net.frac_st[i])
        away = sch.away[p.profile[i]]
        setpoint = p.setpoint_c[i] + np.where(away & (p.away_mode[i] == 1), p.setback_k[i], 0.0)
        allowed = ~(away & (p.away_mode[i] == 2))
        phi_int, phi_sol = res.hourly["phi_int"][i], res.hourly["phi_sol"][i]
        phis, airs = reference.run(
            scalar, [weather["temp_c"].iloc[t] for t in order], [phi_int[t] for t in order],
            [phi_sol[t] for t in order], [setpoint[t] for t in order], [bool(allowed[t]) for t in order],
            theta_m0=24.0)
        assert np.allclose(phis[warm:], res.hourly["phi_hc"][i], atol=1e-6)
        assert np.allclose(airs[warm:], res.hourly["theta_air"][i], atol=1e-9)


def test_steady_state_equals_network_conductance() -> None:
    idx = pd.date_range("2024-06-01", periods=24 * 30, freq="h", tz="Asia/Dubai")
    weather = pd.DataFrame({"temp_c": 40.0, "dewpoint_c": 10.0, "pressure_hpa": 1000.0,
                            "ghi_wm2": 0.0}, index=idx)
    facades = pd.DataFrame({"sun_elev_deg": -10.0, "sun_az_deg": 0.0, "ghi_wm2": 0.0}, index=idx)
    for o in solar.ORIENTATIONS:
        facades[f"{o}_beam"] = 0.0
        facades[f"{o}_sky"] = 0.0
    p = build_params([BASE, replace(BASE, facing="W+N", floor=30)]).replace(
        people=0.0, appliance_wm2=0.0, window_opening=False)
    res = rc5r1c.simulate(p, weather, facades, keep_hourly=True, solar_scale=0.0)
    net = rc5r1c.network(p)
    h_op = 1.0 / (1.0 / net.h_em + 1.0 / net.h_ms)
    expected = (net.h_ve + net.h_is * (net.h_w + h_op) / (net.h_w + h_op + net.h_is)) * (40.0 - 24.0)
    assert np.allclose(-res.hourly["phi_hc"][:, -1], expected, rtol=1e-6)


def test_results_are_monthly_aggregates_only() -> None:
    r = _run([BASE, replace(BASE, facing="N")])
    assert r.sens_kwh.shape == r.lat_kwh.shape == (2, 12)
    assert r.hourly is None
    assert (r.peak_kw >= r.design_kw).all()


def test_sampling_is_reproducible_with_a_seed() -> None:
    specs = [BASE] * 3 + [replace(BASE, facing="E")] * 3
    a = build_params(specs, np.random.default_rng(7))
    b = build_params(specs, np.random.default_rng(7))
    pd.testing.assert_frame_equal(a.to_frame(), b.to_frame())
    ra, rb = (engine.run_site_year(x, "central", YEAR) for x in (a, b))
    assert np.array_equal(ra.total_kwh, rb.total_kwh)


# --- §9 physics invariants ----------------------------------------------------

def test_more_glass_means_higher_load(variants) -> None:
    assert variants["glass_high"] > variants["base"] > variants["glass_low"]
    assert variants["a3_glass_high"] > variants["a3_glass_low"]


def test_west_beats_north_in_summer(variants) -> None:
    assert variants["base_summer"] > variants["north_summer"]


def test_higher_setpoint_means_lower_load(variants) -> None:
    assert variants["setpoint_22"] > variants["base"] > variants["setpoint_26"]


def test_more_shading_means_lower_load(variants) -> None:
    assert variants["balcony_deep"] < variants["base"]
    assert variants["obstruction_heavy"] < variants["base"] < variants["obstruction_open"]


def test_top_floor_at_least_mid_floor(variants) -> None:
    assert variants["top_floor"] >= variants["mid_floor"]


def test_removing_solar_gains_lowers_load() -> None:
    p = build_params([BASE, replace(BASE, facing="S")])
    with_sun = engine.run_site_year(p, "central", YEAR)
    no_sun = engine.run_site_year(p, "central", YEAR, solar_scale=0.0)
    assert (no_sun.annual_kwh < with_sun.annual_kwh).all()


def test_more_people_and_more_facade_mean_higher_load(variants) -> None:
    assert variants["people_5"] > variants["people_1"]
    assert variants["corner"] > variants["base"]


def test_west_peak_exceeds_east_peak(variants) -> None:
    assert variants["base_peak"] > variants["east_peak"]


def test_switching_ac_off_when_away_saves_energy() -> None:
    p = build_params([BASE]).replace(window_opening=False)
    keep = engine.run_site_year(p.replace(away_mode=0), "central", YEAR)
    off = engine.run_site_year(p.replace(away_mode=2), "central", YEAR)
    assert off.annual_kwh[0] < keep.annual_kwh[0]


def test_latent_load_follows_outdoor_humidity() -> None:
    r = _run([BASE])
    assert r.lat_kwh[0, 7] > 3 * r.lat_kwh[0, 0]   # humid August vs dry January


# --- building blocks ----------------------------------------------------------

def test_listing_validation() -> None:
    with pytest.raises(ValueError):
        build_params([replace(BASE, floor=31)])
    with pytest.raises(ValueError):
        build_params([replace(BASE, facing="WEST")])
    with pytest.raises(ValueError):
        build_params([replace(BASE, community="Atlantis")])


def test_code_era_glazing_uses_wwr_band_limit() -> None:
    p = build_params([replace(BASE, era_band="2015_2021", glass="medium")])  # WWR 0.40 -> band 1
    assert p.win_u[0] == pytest.approx(2.1)
    assert p.win_shgc[0] == pytest.approx(0.40 * 0.87 * 0.95)


def test_shading_helpers() -> None:
    assert shading.diffuse_window_factor(0.0, 2.0, 0.0)[0] == pytest.approx(1.0)
    deep, shallow = shading.diffuse_window_factor([2.0, 0.5], [2.0, 2.0], [0.0, 0.0])
    assert deep < shallow < 1.0
    assert shading.diffuse_window_factor(0.0, 2.0, 30.0)[0] == pytest.approx(0.5)
    assert shading.beam_window_factor(np.nan, 1.0, 2.0, 1.0, 0.0) == 0.0
    assert shading.beam_window_factor(1.0, 1.0, 2.0, 1.0, 0.0) == pytest.approx(0.5)
    assert shading.obstruction_angle_deg(100.0, 100.0, 0.0) == pytest.approx(45.0)
    assert shading.obstruction_angle_deg(100.0, 100.0, 150.0) == 0.0


def test_schedules_weekend_and_ramadan() -> None:
    idx = pd.date_range("2024-03-01", "2024-03-31 23:00", freq="h", tz="Asia/Dubai")
    sch = schedules.build(idx)
    weekday_noon = (idx.day_name() == "Monday") & (idx.hour == 12)
    weekend_noon = (idx.day_name() == "Sunday") & (idx.hour == 12)
    away = schedules.profile_id("away_daytime", False)
    assert sch.presence[away][weekday_noon].max() < sch.presence[away][weekend_noon].min()
    ramadan_afternoon = (idx.day == 18) & (idx.hour == 16)          # Monday in Ramadan 2024
    before_afternoon = (idx.day == 4) & (idx.hour == 16)            # Monday before Ramadan
    rid = schedules.profile_id("away_daytime", True)
    assert sch.presence[rid][ramadan_afternoon] > sch.presence[rid][before_afternoon]


def test_psychrometrics() -> None:
    assert psychro.humidity_ratio_from_dewpoint(20.0, 101325.0) == pytest.approx(0.0147, abs=3e-4)
    w_in = psychro.humidity_ratio_from_rh(24.0, 0.5, 101325.0)
    assert w_in == pytest.approx(0.0093, abs=3e-4)
