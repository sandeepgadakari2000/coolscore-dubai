"""Phases 5-7: API contract, app smoke tests, AI layer (parser, guard, direction)."""

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from api.main import app  # noqa: E402
from coolscore.assistant import direction, explain, llm, parser  # noqa: E402
from coolscore.model import predict  # noqa: E402

UNIT = {"community": "Business Bay", "size_sqft": 800, "bedrooms": 1, "floor": 15, "total_floors": 30,
        "facing": "W", "era_band": "2005_2014", "glass": "high", "system": "district_cooling", "payer": "tenant",
        "annual_rent_aed": 90000}
LISTING_TEXT = ("Stunning 1 Bed in Business Bay | Chiller Free | Full Burj Khalifa View. Spacious 1-bedroom, "
                "812 sq ft, on the 23rd floor of a 45-storey tower completed in 2016. Floor-to-ceiling windows, "
                "large balcony. AED 98,000 per year. West-facing living room.")


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """The no-key path must work and never touch the network."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)


# --- API contract ---------------------------------------------------------------

def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_score_contract(client) -> None:
    r = client.post("/score", json=UNIT)
    assert r.status_code == 200
    body = r.json()
    assert body["coolscore"] in list("ABCDE") and body["simulated"] is True
    a = body["annual_aed"]
    assert a["p10"] <= a["p50"] <= a["p90"]
    assert body["true_monthly_cost_aed"] > UNIT["annual_rent_aed"] / 12
    assert body["drivers"] and "formula" in body and body["disclaimer"].startswith("Estimates for guidance only")


@pytest.mark.parametrize("bad", [{"facing": "WEST"}, {"floor": 40}, {"community": "Atlantis"}, {"size_sqft": -5}])
def test_score_rejects_invalid_input(client, bad) -> None:
    assert client.post("/score", json={**UNIT, **bad}).status_code == 422


def test_compare_flags_cheaper_rent_more_expensive_home(client) -> None:
    cheap_hot = {**UNIT, "era_band": "before_2005", "facing": "W+S", "floor": 30, "glass": "floor_to_ceiling",
                 "annual_rent_aed": 88000}
    dearer_free = {**UNIT, "facing": "N", "glass": "medium", "payer": "landlord_chiller_free",
                   "annual_rent_aed": 89000}
    r = client.post("/compare", json={"units": [cheap_hot, dearer_free]})
    assert r.status_code == 200
    body = r.json()
    assert body["cheapest_rent_index"] == 0 and body["cheapest_true_cost_index"] == 1
    assert body["cheaper_rent_is_more_expensive_home"] is True


def test_openapi_docs_are_generated(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/score", "/compare", "/health"} <= set(paths)


# --- App smoke tests -----------------------------------------------------------------

def _app(page: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / page), default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.mark.parametrize("page", ["Home.py", "pages/5_Listing_Badge.py", "pages/6_Business_Case.py",
                                  "pages/7_Methodology.py"])
def test_pages_render(page) -> None:
    _app(page)


def test_check_a_unit_parses_prefills_and_answers_fast() -> None:
    at = _app("pages/1_Check_a_Unit.py")
    at.text_area[0].input(LISTING_TEXT).run()
    at.button[0].click().run()
    assert at.number_input(key="chk1_size").value == 812
    t0 = time.time()
    at.button(key="FormSubmitter:check-Estimate cooling cost").click().run()
    assert time.time() - t0 < 3.0                       # brief §12: answer in under 3 s
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "AED" in text and "Questions" in " ".join(m.value for m in at.markdown) + text


@pytest.mark.parametrize("page,button", [("pages/2_Compare_Units.py", "Compare"),
                                         ("pages/3_Investor_View.py", "Calculate")])
def test_interactive_pages_run(page, button) -> None:
    at = _app(page)
    target = [b for b in at.button if b.label == button]
    target[0].click().run()
    assert not at.exception, [e.value for e in at.exception]


def test_developer_view_runs_physics() -> None:
    at = _app("pages/4_Developer_View.py")
    assert any("Whole tower" in m.label for m in at.metric)


# --- AI layer -----------------------------------------------------------------------

def test_parser_without_key_flags_status_and_evidence() -> None:
    assert not llm.available()
    r = parser.parse_listing(LISTING_TEXT)
    assert r.method.startswith("basic")
    f = r.fields
    assert f["size_sqft"].value == 812 and f["size_sqft"].status == "found" and "812" in f["size_sqft"].evidence
    assert f["payer"].value == "landlord_chiller_free"
    assert f["price_aed"].status == "missing"
    assert r.form_defaults()["era_band"] == "2015_2021"


@pytest.mark.parametrize("text,floor,total", [
    ("2 bed, 22nd floor of 40, sea view", 22, 40),
    ("Floor 9/31 in a quiet tower", 9, 31),
    ("Apartment on the 15th floor of a 45-storey tower", 15, 45),
])
def test_parser_reads_floor_and_total_floors_together(text: str, floor: int, total: int) -> None:
    f = parser.parse_listing(text).fields
    assert (f["floor"].value, f["total_floors"].value) == (floor, total)


def test_parser_reports_missing_instead_of_guessing() -> None:
    r = parser.parse_listing("Lovely apartment with great views, high floor, call now!")
    assert {"size_sqft", "floor", "facing", "community"} <= set(r.missing)
    assert r.fields["floor"].value is None   # "high floor" is not a floor number


def test_parser_schema_matches_fields() -> None:
    assert set(parser._LLMListing.model_fields) == set(parser.FIELDS)


def test_explanation_guard_blocks_invented_numbers() -> None:
    est = predict.estimate({k: v for k, v in UNIT.items() if k != "annual_rent_aed"})
    f = explain.facts(est)
    assert explain.numbers_ok(explain.template(est), f)
    assert not explain.numbers_ok("Your bill will be about AED 123,456 a year.", f)
    assert explain.explain(est) == explain.template(est)       # no key -> template
    assert explain.questions_for_agent(est)


def test_chiller_free_explanation_puts_capacity_charge_on_the_landlord() -> None:
    est = predict.estimate({**{k: v for k, v in UNIT.items() if k != "annual_rent_aed"},
                            "payer": "landlord_chiller_free"})
    f = explain.facts(est)
    text = explain.template(est)
    assert f["capacity_charge_paid_by"].startswith("landlord")
    assert "paid by the landlord" in text and "so ask for the unit's contracted capacity" not in text
    assert explain.numbers_ok(text, f)


def test_direction_helper_uses_geometry_and_declines_when_unsure() -> None:
    assert direction.suggest("Dubai Marina", "sea view").facing == "NW"
    assert direction.suggest("Dubai Creek Harbour", "Burj Khalifa view").facing == "W"
    assert direction.suggest("Downtown Dubai", "Burj Khalifa view") is None
    assert direction.suggest("Jumeirah Village Circle (JVC)", "golf view") is None
