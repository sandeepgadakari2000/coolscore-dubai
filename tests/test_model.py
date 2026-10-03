"""Phase 4: scenario sampling, surrogate accuracy, CoolScore bands, estimates."""

import json
import time

import numpy as np
import pytest

from coolscore import config
from coolscore.model import predict, train
from coolscore.simulate import scenarios

LISTING = dict(community="Business Bay", era_band="2005_2014", size_sqft=800, bedrooms=1, floor=15,
               total_floors=30, facing="W", glass="high", balcony="none", obstruction="partial",
               system="district_cooling", payer="tenant")


@pytest.fixture(scope="module")
def metrics() -> dict:
    return json.loads(train.metrics_path().read_text(encoding="utf-8"))


# --- sampling -----------------------------------------------------------------

def test_latin_hypercube_has_one_point_per_stratum() -> None:
    u = scenarios.latin_hypercube(50, 4, np.random.default_rng(0))
    for j in range(4):
        assert sorted(np.floor(u[:, j] * 50).astype(int)) == list(range(50))


def test_scenarios_are_reproducible_and_valid() -> None:
    a, b = scenarios.sample(300, 11), scenarios.sample(300, 11)
    assert a.equals(b)
    assert (a["floor"] >= 1).all() and (a["floor"] <= a["total_floors"]).all()
    dewa = a["system"].isin(["dewa_split_ac", "dewa_central_ac"])
    assert (a.loc[dewa, "payer"] == "tenant").all()
    for spec in scenarios.to_specs(a.head(20)):
        spec.validate()


# --- surrogate accuracy (held-out physics runs) ------------------------------------

def test_artifact_is_small_enough_for_streamlit_cloud(metrics) -> None:
    assert train.artifact_path().exists()
    assert metrics["artifact_mb"] < config.settings()["model"]["max_artifact_mb"]


def test_fidelity_meets_target(metrics) -> None:
    fid = metrics["fidelity"]
    assert fid["annual_tenant_aed"]["r2"] >= fid["target_r2"]


def test_listing_models_are_useful_and_calibrated(metrics) -> None:
    for variant in ("listing", "detailed"):
        m = metrics["variants"][variant]["annual"]
        assert m["r2"] > 0.8
        assert 0.70 <= m["p10_p90_coverage"] <= 0.90


def test_details_narrow_the_range(metrics) -> None:
    listing = metrics["variants"]["listing"]["annual"]["median_interval_width_aed"]
    detailed = metrics["variants"]["detailed"]["annual"]["median_interval_width_aed"]
    assert detailed <= listing


# --- CoolScore bands ----------------------------------------------------------

def test_score_bands_are_monotonic_with_cost_intensity(metrics) -> None:
    cuts = metrics["score_cuts_aed_per_sqft"]
    assert cuts == sorted(cuts) and len(set(cuts)) == 4
    letters = [predict._score(x, cuts, list("ABCDE")) for x in np.linspace(cuts[0] - 1, cuts[-1] + 1, 50)]
    assert letters == sorted(letters)
    assert letters[0] == "A" and letters[-1] == "E"


# --- estimates ------------------------------------------------------------------

def test_estimate_ranges_are_ordered_and_labelled() -> None:
    e = predict.estimate(LISTING)
    for r in (e.annual, e.summer_month, e.winter_month):
        assert 0 <= r.p10 <= r.p50 <= r.p90
    assert e.summer_month.p50 > e.winter_month.p50
    assert e.score in "ABCDE" and e.simulated
    assert "contracted RT" in e.formula
    assert abs(sum(e.monthly_p50) - e.annual.p50) / e.annual.p50 < 0.15


def test_estimate_reports_assumed_fields_and_rejects_missing() -> None:
    e = predict.estimate({k: v for k, v in LISTING.items() if k not in ("glass", "obstruction")})
    assert {"glass", "obstruction"} <= set(e.assumed)
    with pytest.raises(ValueError):
        predict.estimate({k: v for k, v in LISTING.items() if k != "size_sqft"})


def test_drivers_name_the_facing_and_west_costs_more_than_north() -> None:
    e = predict.estimate(LISTING)
    facing = [d for d in e.drivers if d["driver"].startswith("W-facing")]
    assert facing and facing[0]["aed_per_year"] > 0
    assert predict.estimate({**LISTING, "facing": "N"}).annual.p50 < e.annual.p50


def test_what_if_controls_move_the_estimate_the_right_way() -> None:
    warm = predict.estimate({**LISTING, "setpoint_c": 26.0})
    cool = predict.estimate({**LISTING, "setpoint_c": 22.0})
    assert warm.variant == "detailed" and warm.annual.p50 < cool.annual.p50
    free = predict.estimate({**LISTING, "payer": "landlord_chiller_free"})
    assert free.annual.p50 < predict.estimate(LISTING).annual.p50
    assert free.landlord_annual_p50 > 0


def test_estimate_is_fast() -> None:
    predict.estimate(LISTING)  # warm the artifact cache
    t0 = time.time()
    for facing in ("N", "E", "S", "W"):
        predict.estimate({**LISTING, "facing": facing})
    assert (time.time() - t0) / 4 < 1.0
