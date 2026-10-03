"""Config files follow the assumption-register rules (brief §0)."""

import datetime as dt
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
RECORD_KEYS = {"value", "unit", "source", "date_checked", "verify", "notes", "phase"}


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def _records(node: Any, path: str = "") -> Iterator[tuple[str, dict]]:
    """Yield every assumption record (a mapping that has a 'value' key)."""
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
            return
        for key, child in node.items():
            yield from _records(child, f"{path}.{key}" if path else str(key))


def _all_records() -> list[tuple[str, dict]]:
    return list(_records(_load("assumptions.yaml"))) + list(
        _records(_load("archetypes.yaml"))
    )


def test_every_record_has_exactly_the_required_fields() -> None:
    records = _all_records()
    assert len(records) > 20
    for path, rec in records:
        assert set(rec) == RECORD_KEYS, f"{path}: {sorted(set(rec) ^ RECORD_KEYS)}"


def test_record_field_types() -> None:
    for path, rec in _all_records():
        assert isinstance(rec["verify"], bool), path
        assert rec["date_checked"] is None or isinstance(rec["date_checked"], dt.date), path
        assert isinstance(rec["phase"], int) and 0 <= rec["phase"] <= 9, path


def test_filled_values_cite_a_url_and_a_check_date() -> None:
    for path, rec in _all_records():
        if rec["value"] is not None:
            assert str(rec["source"]).startswith("http"), f"{path} has a value but no URL"
            assert rec["date_checked"] is not None, f"{path} has a value but no date_checked"


def test_settings_have_core_keys() -> None:
    s = _load("settings.yaml")
    assert s["llm"]["model"]
    assert s["model"]["quantiles"] == [0.1, 0.5, 0.9]
    assert s["app"]["disclaimer"].startswith("Estimates for guidance only")
    assert isinstance(s["random_seed"], int)


def test_communities_map_to_known_microclimates_inside_dubai() -> None:
    c = _load("communities.yaml")
    sites = c["microclimates"]
    assert set(sites) == {"coastal", "central", "inland"}
    for site in sites.values():
        assert 24.6 < site["lat"] < 25.4 and 54.9 < site["lon"] < 55.6
    assert set(c["communities"].values()) <= set(sites)


def test_archetype_bands_match_real_bill_template() -> None:
    a = _load("archetypes.yaml")
    bands = set(a["era_bands"])
    assert {arch["era_band"] for arch in a["archetypes"].values()} == bands
    readme = (ROOT / "data" / "real_bills" / "README.md").read_text(encoding="utf-8")
    for band in bands:
        assert f"`{band}`" in readme, band
    assert "building_era_band" in pd.read_csv(ROOT / "data/real_bills/template.csv", nrows=0)
