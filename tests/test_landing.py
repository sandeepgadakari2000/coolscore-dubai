"""Landing page (site/): its data file matches the model and the film's choreography."""

import json
import re
from pathlib import Path

from coolscore import landing
from coolscore.model import predict
from coolscore.physics.params import ORIENTATIONS

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "site" / "data" / "tower.json").read_text(encoding="utf-8"))


def test_every_flat_is_scored_once() -> None:
    keys = {(u["floor"], u["facing"]) for u in DATA["units"]}
    assert len(DATA["units"]) == len(keys) == landing.TOWER["total_floors"] * len(ORIENTATIONS)
    for u in DATA["units"]:
        p10, p50, p90 = u["annual"]
        assert p10 <= p50 <= p90 and u["score"] in "ABCDE"


def test_film_stops_match_the_exported_flats() -> None:
    """timeline.js hard-codes the four stops; they must be the flats tower.json describes."""
    js = (ROOT / "site" / "js" / "timeline.js").read_text(encoding="utf-8")
    stops = re.findall(r"key: '(\w+)', start: [\d.]+, end: [\d.]+, floor: (\d+), facing: '(\w+)', hour: (\d+)", js)
    assert [(k, int(f), o, int(h)) for k, f, o, h in stops] == \
        [(s["key"], s["floor"], s["facing"], s["hour"]) for s in landing.FEATURED]
    assert [(f["key"], f["floor"], f["facing"]) for f in DATA["featured"]] == \
        [(s["key"], s["floor"], s["facing"]) for s in landing.FEATURED]


def test_featured_budgets_add_up_and_profiles_cover_a_day() -> None:
    for f in DATA["featured"]:
        assert abs(sum(f["budget_pct"].values()) - 100) <= 2
        assert len(f["load_kw_by_hour"]) == 24 and min(f["load_kw_by_hour"]) > 0


def test_exported_numbers_are_the_models() -> None:
    """Spot-check: the page shows what Check a Unit would say for the same flat."""
    f = DATA["featured"][0]
    est = predict.estimate(landing._listing(f["floor"], f["facing"]))
    assert f["unit"]["score"] == est.score
    assert f["unit"]["annual"] == [round(est.annual.p10), round(est.annual.p50), round(est.annual.p90)]
