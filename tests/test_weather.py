"""Phase 1: weather cache, bias correction and facade sun (brief §4.1)."""

import json

import numpy as np
import pandas as pd
import pytest
import requests

from coolscore import config
from coolscore.weather import correction, dataset, openmeteo, solar, stations

SITES = ["central", "inland"]
ALBEDO = 0.2


def _multi_year(site: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    w = pd.concat([dataset.load_weather(site, y) for y in dataset.years()])
    f = pd.concat([solar.load_facades(site, y) for y in dataset.years()])
    return w, f


@pytest.fixture(scope="module")
def central_summer() -> dict[str, float]:
    """Mean summer (Jun-Aug) daily irradiation per orientation, kWh/m²/day."""
    _, f = _multi_year("central")
    out = {}
    for o in solar.ORIENTATIONS:
        tot = solar.facade_total(f, o, ALBEDO)
        jja = tot[tot.index.month.isin([6, 7, 8])]
        out[o] = jja.sum() / 1000 / (len(jja) / 24)
    return out


# --- cache and offline behaviour -------------------------------------------------

@pytest.mark.parametrize("site", dataset.sites())
@pytest.mark.parametrize("year", dataset.years())
def test_corrected_weather_is_cached_and_complete(site: str, year: int) -> None:
    df = dataset.load_weather(site, year)
    assert openmeteo.check_quality(df, year) == []
    assert (df["dewpoint_c"] <= df["temp_c"] + 1e-9).all()


def test_cached_data_loads_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args, **kwargs):
        raise AssertionError("network call at runtime")

    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setattr(requests.Session, "get", boom)
    w = dataset.load_weather("central", 2024)
    f = solar.load_facades("central", 2024)
    assert len(w) == len(f) == 8784


def test_metadata_records_source_and_correction() -> None:
    path = dataset.corrected_path("central", 2023).with_suffix("").with_suffix(".meta.json")
    meta = json.loads(path.read_text(encoding="utf-8"))
    assert meta["model"] == "ecmwf_ifs" and meta["licence"] == "CC BY 4.0"
    assert meta["bias_correction"]["station_isd_id"] == "41194099999"


def test_build_params_and_parse_response() -> None:
    params = openmeteo.build_params(25.19, 55.27, "2024-01-01", "2024-01-01", "ecmwf_ifs")
    assert params["models"] == "ecmwf_ifs" and params["timezone"] == "Asia/Dubai"
    assert set(params["hourly"].split(",")) == set(openmeteo.COLUMNS)
    payload = {
        "latitude": 25.2, "longitude": 55.3, "elevation": 4.0, "utc_offset_seconds": 14400,
        "hourly_units": {}, "hourly": {"time": ["2024-01-01T00:00", "2024-01-01T01:00"],
                                       **{k: [1.0, 2.0] for k in openmeteo.COLUMNS}},
    }
    df, meta = openmeteo.parse_response(payload)
    assert list(df.columns) == list(openmeteo.COLUMNS.values())
    assert str(df.index.tz) == "Asia/Dubai" and meta["grid_elevation_m"] == 4.0


def test_isd_parsing_decodes_and_drops_missing() -> None:
    from io import StringIO

    text = ('"DATE","TMP","DEW"\n"2024-07-01T10:00:00","+0412,1","+0255,1"\n'
            '"2024-07-01T10:30:00","+0415,1","+0250,1"\n"2024-07-01T11:00:00","+9999,9","+0251,1"\n')
    df = stations.parse_isd(StringIO(text))
    assert len(df) == 2  # the :30 report is dropped
    assert df.iloc[0]["temp_c"] == pytest.approx(41.2) and df.index[0].hour == 14  # UTC+4
    assert np.isnan(df.iloc[1]["temp_c"]) and df.iloc[1]["dewpoint_c"] == pytest.approx(25.1)


# --- bias correction -------------------------------------------------------------

def test_bias_correction_recovers_a_known_offset() -> None:
    idx = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz="Asia/Dubai")
    rng = np.random.default_rng(0)
    obs = pd.DataFrame({"temp_c": 30 + rng.normal(0, 1, len(idx)), "dewpoint_c": 20.0}, index=idx)
    model = obs.copy()
    night = idx.hour < 6
    model.loc[night, "temp_c"] -= 2.0
    model["rh_pct"] = 50.0
    table = correction.fit_bias(model, obs, smooth_hours=1)
    fixed = correction.apply_bias(model, table)
    assert np.allclose(fixed["temp_c"], obs["temp_c"])
    assert fixed["rh_pct"].between(0, 100).all()


def test_holdout_shows_correction_helps_at_dubai_international() -> None:
    s = json.loads(dataset.summary_path().read_text(encoding="utf-8"))["stations"]["41194099999"]
    raw, fixed = s["holdout"]["raw"], s["holdout"]["corrected"]
    assert fixed["temp_c_rmse"] < raw["temp_c_rmse"]
    assert abs(fixed["cdh24_ratio"] - 1) < abs(raw["cdh24_ratio"] - 1)
    assert abs(fixed["cdh24_ratio"] - 1) < 0.05


# --- radiation conventions -------------------------------------------------------

def test_radiation_is_preceding_hour_mean() -> None:
    w = dataset.load_weather("central", 2024)
    peak_hour = w["ghi_wm2"].groupby(w.index.hour).mean().idxmax()
    assert peak_hour == 13  # interval 12-13 contains solar noon (~12:20 in Dubai)
    sp = solar.solar_position(w.index, *dataset.site_coordinates("central"))
    up = (sp["apparent_elevation"] > 10).to_numpy()
    beam = (w["dni_wm2"].to_numpy() * np.cos(np.radians(sp["apparent_zenith"].to_numpy())))[up]
    assert beam.sum() / w["bhi_wm2"].to_numpy()[up].sum() == pytest.approx(1.0, abs=0.03)


def test_annual_ghi_is_plausible_for_dubai() -> None:
    for site in SITES:
        w, _ = _multi_year(site)
        assert 1900 < w["ghi_wm2"].sum() / 1000 / len(dataset.years()) < 2400


def test_ground_reflected_geometry() -> None:
    assert solar.ground_reflected(1000.0, 0.2) == pytest.approx(100.0)
    assert solar.ground_reflected(1000.0, 0.2, tilt_deg=0.0) == pytest.approx(0.0)


def test_profile_angle_helper() -> None:
    assert solar.tan_profile_angle(45.0, 270.0, 270.0) == pytest.approx(1.0)
    assert np.isnan(solar.tan_profile_angle(45.0, 90.0, 270.0))  # sun behind the facade
    assert np.isnan(solar.tan_profile_angle(-5.0, 270.0, 270.0))  # sun below horizon


# --- §4.1 sanity expectations ----------------------------------------------------

def test_summer_east_and_west_beat_south(central_summer: dict[str, float]) -> None:
    assert central_summer["E"] > 1.5 * central_summer["S"]
    assert central_summer["W"] > 1.5 * central_summer["S"]


def test_summer_south_is_no_better_than_north(central_summer: dict[str, float]) -> None:
    assert central_summer["S"] < 1.15 * central_summer["N"]


@pytest.mark.parametrize("site", SITES)
def test_west_sun_coincides_with_heat(site: str) -> None:
    w, f = _multi_year(site)
    hot = (w["temp_c"] > 38.0) & w.index.month.isin([6, 7, 8])
    west = solar.facade_total(f, "W", ALBEDO)[hot].sum()
    east = solar.facade_total(f, "E", ALBEDO)[hot].sum()
    assert west > 1.15 * east


def test_winter_south_gets_most_sun_and_north_least_annually() -> None:
    _, f = _multi_year("central")
    winter = {o: solar.facade_total(f, o, ALBEDO)[f.index.month.isin([12, 1, 2])].sum()
              for o in solar.ORIENTATIONS}
    annual = {o: solar.facade_total(f, o, ALBEDO).sum() for o in solar.ORIENTATIONS}
    assert max(winter, key=winter.get) == "S"
    assert min(annual, key=annual.get) == "N"
    assert annual["E"] == pytest.approx(annual["W"], rel=0.03)


# --- config plumbing -------------------------------------------------------------

def test_every_community_has_cached_weather() -> None:
    cached = {p.name.split("_")[1] for p in openmeteo.weather_dir().glob("dubai_*.csv.gz")}
    for community in config.communities()["communities"]:
        assert dataset.weather_site_for(community) in cached
    assert dataset.weather_site_for("Dubai Marina") == "central"


def test_require_refuses_placeholders() -> None:
    assert config.require("physics.ground_albedo")["central"] == pytest.approx(0.2)
    with pytest.raises(config.MissingAssumptionError):
        config.require("billing.district_cooling.consumption_charge")
