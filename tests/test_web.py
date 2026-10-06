"""The Vercel build: the NumPy copy of the model, the /api function and the static app pages."""

import itertools
import lzma
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from coolscore import config, web
from coolscore.model import features as F
from coolscore.model import lite, predict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from index import app  # noqa: E402

UNIT = {"community": "Business Bay", "size_sqft": 800, "bedrooms": 1, "floor": 15, "total_floors": 30,
        "facing": "W", "era_band": "2005_2014", "glass": "high", "system": "district_cooling", "payer": "tenant",
        "annual_rent_aed": 90000}
PAGES = ("check", "compare", "investor", "developer", "badge", "business", "methodology")


# --- the lite model -----------------------------------------------------------

@pytest.fixture(scope="module")
def models() -> tuple[dict, dict]:
    full = pickle.load(lzma.open(config.path("demo") / "coolscore_model.pkl.xz", "rb"))
    return full, lite.load()


def _rows() -> pd.DataFrame:
    """Varied units, incl. corner facings, every era, cooling setup and household detail."""
    rows = []
    combos = itertools.product(["Business Bay", "Dubai Marina", "Jumeirah Village Circle (JVC)"], ["N", "W", "S+W", "NE+SE"],
                               ["before_2005", "2015_2021", "2022_plus"], ["district_cooling", "dewa_split_ac"])
    for i, (community, facing, era, system) in enumerate(combos):
        listing = {**UNIT, "community": community, "facing": facing, "era_band": era, "system": system,
                   "floor": 1 + (i * 7) % 30, "size_sqft": 450 + (i * 97) % 1500, "glass": ["medium", "high", "floor_to_ceiling"][i % 3],
                   "payer": ["tenant", "landlord_chiller_free"][i % 2], "household_size": 1 + i % 5,
                   "occupancy": ["away_daytime", "home_daytime"][i % 2], "setpoint_c": 21 + (i % 7)}
        rows.append(predict.normalise(listing)[0])
    return F.encode(pd.DataFrame(rows))


def test_lite_model_matches_the_full_model(models) -> None:
    full, small = models
    X = _rows()
    assert small["quantiles"] == full["quantiles"] and small["features"] == full["features"]
    for variant, targets in full["models"].items():
        Xv = X[full["features"][variant]]
        for target, qs in targets.items():
            for q, model in qs.items():
                np.testing.assert_allclose(small["models"][variant][target][q].predict(Xv), model.predict(Xv),
                                           rtol=0, atol=1e-9, err_msg=f"{variant}/{target}/{q}")


def test_lite_model_handles_unknown_categories(models) -> None:
    full, small = models
    X = _rows().iloc[:3].copy()
    X.loc[X.index[0], "system"] = 99           # a categorical feature (integer codes): a code never trained on
    Xv = X[full["features"]["listing"]]
    np.testing.assert_allclose(small["models"]["listing"]["annual"][0.5].predict(Xv),
                               full["models"]["listing"]["annual"][0.5].predict(Xv), atol=1e-9)


# --- the API --------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_health_and_meta(client) -> None:
    assert client.get("/api/health").json()["status"] == "ok"
    m = client.get("/api/meta").json()
    assert "Business Bay" in m["communities"] and "S+W" in m["facings"] and len(m["months"]) == 12
    assert set(m["score_colors"]) == set("ABCDE")


def test_estimate_is_a_labelled_range(client) -> None:
    r = client.post("/api/estimate", json={"listing": UNIT, "month": 7}).json()
    a = r["estimate"]["annual"]
    assert 0 < a["p10"] <= a["p50"] <= a["p90"]
    assert len(r["month_ranges"]) == 12 and r["estimate"]["score"] in "ABCDE"
    assert r["true_cost"]["rent"] == pytest.approx(90000 / 12)
    assert r["stage"]["month"] == 7 and r["drivers"] and r["questions"]


def test_bad_input_is_a_422_not_a_crash(client) -> None:
    assert client.post("/api/estimate", json={"listing": {**UNIT, "community": "Atlantis"}}).status_code == 422
    assert client.post("/api/compare", json={"units": [UNIT]}).status_code == 422


@pytest.mark.parametrize("change", [{"size_sqft": 50}, {"size_sqft": 9000}, {"floor": 0}, {"total_floors": 200, "floor": 160},
                                    {"setpoint_c": 12}, {"household_size": 0}])
def test_out_of_range_units_are_refused_with_a_reason(client, change) -> None:
    r = client.post("/api/estimate", json={"listing": {**UNIT, **change}})
    assert r.status_code == 422 and "between" in r.json()["detail"]


def test_business_survives_a_price_of_zero(client) -> None:
    r = client.post("/api/business", json={"pricing": {"broker_seat_aed_month": 0, "portal_aed_per_scored_listing_month": 0}})
    assert r.status_code == 200
    ue = r.json()["unit_economics"]
    assert ue["broker_seat_margin"] is None and ue["listing_margin"] is None


def test_whatif_now_matches_the_estimate(client) -> None:
    est = client.post("/api/estimate", json={"listing": UNIT}).json()["estimate"]
    same = client.post("/api/whatif", json={"listing": UNIT, "change": {"floor": 15, "facing": "W", "setpoint_c": 24,
                                                                        "chiller_free": False}}).json()
    assert same["delta"] == pytest.approx(0, abs=1)
    assert same["annual"]["p50"] == pytest.approx(est["annual"]["p50"], abs=1)


def test_compare_finds_the_cheapest_home(client) -> None:
    units = [UNIT, {**UNIT, "facing": "N", "payer": "landlord_chiller_free", "annual_rent_aed": 92000}]
    r = client.post("/api/compare", json={"units": units}).json()
    totals = [u["total"] for u in r["rows"]]
    assert r["verdict"]["cheapest_true"] == int(np.argmin(totals))
    assert r["verdict"]["cheapest_rent"] == 0


def test_investor_yields_fall_with_each_cost(client) -> None:
    r = client.post("/api/investor", json={"listing": {**UNIT, "payer": "landlord_chiller_free"}, "price": 1_400_000,
                                           "rent": 95_000, "service_charge": 15, "other": 2000}).json()
    assert r["gross"] == pytest.approx(95_000 / 1_400_000)
    assert r["gross"] > r["net_tenant"] > r["net_free_p50"] >= r["net_free_p90"]


def test_badge_business_and_methodology(client) -> None:
    b = client.post("/api/badge", json={"listing": UNIT}).json()
    assert b["score"] in "ABCDE" and b["summer"]["p10"] <= b["summer"]["p90"] and len(b["cuts"]) == 4
    biz = client.post("/api/business", json={"pricing": {"broker_seat_aed_month": 200}}).json()
    assert biz["inputs"]["pricing"]["broker_seat_aed_month"] == 200 and len(biz["months"]) == 12
    meth = client.get("/api/methodology").json()
    assert meth["metrics"]["n_train"] > 0 and len(meth["register"]) > 20


def test_developer_grid_covers_the_tower(client) -> None:
    r = client.post("/api/developer", json={"floors": 8}).json()
    assert r["floors"] == list(range(8, 0, -1)) and len(r["facings"]) == 8
    assert all(r["grid"][str(f)][d]["score"] in "ABCDE" for f in r["floors"] for d in r["facings"])
    assert r["impact"]["per_unit_mean_aed"] == pytest.approx(0)   # base design vs itself


# --- the static pages -----------------------------------------------------------

def test_every_app_page_exists_and_loads_its_script() -> None:
    for page in PAGES:
        html = (ROOT / "site" / page / "index.html").read_text(encoding="utf-8")
        assert f"/js/app/{page}.js" in html and "<title>" in html
        assert (ROOT / "site" / "js" / "app" / f"{page}.js").exists()


def test_landing_links_stay_inside_the_site() -> None:
    main = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert "streamlit.app" not in main and "streamlit.app" not in html
    assert 'href="/check"' in html and 'href="/methodology"' in html


def test_web_meta_has_no_secrets() -> None:
    text = str(web.meta())
    assert "sk-ant" not in text and "api_key" not in text.lower()
