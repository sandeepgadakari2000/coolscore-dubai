"""Phase 8: real-bill validation report and business case.

The bills below are SYNTHETIC test fixtures written to a temporary folder;
they are never placed in data/real_bills.
"""

import shutil

import pandas as pd
import pytest

from coolscore import business, config
from coolscore.validation import report


@pytest.fixture
def bills_dir(tmp_path, monkeypatch):
    shutil.copy(config.path("real_bills") / "template.csv", tmp_path / "template.csv")
    original = config.path
    monkeypatch.setattr(config, "path", lambda key: tmp_path if key == "real_bills" else original(key))
    return tmp_path


def _synthetic_bills() -> pd.DataFrame:
    cols = list(pd.read_csv(config.path("real_bills") / "template.csv", nrows=0).columns)
    rows = []
    for unit, facing in [("U001", "W"), ("U002", "N")]:
        for i, month in enumerate(["2024-06", "2024-07", "2024-08"]):
            rows.append({c: None for c in cols} | {
                "record_id": f"R{len(rows) + 1:04d}", "unit_ref": unit, "submitted_date": "2026-10-03", "consent": "yes",
                "data_source": "typed_by_participant", "community": "Business Bay", "building_era_band": "2005_2014",
                "total_floors_band": "high_rise_26_50", "floor_band": "mid", "facing": facing, "size_sqft": 800,
                "bedrooms": 1, "cooling_system": "district_cooling", "cooling_payer": "tenant",
                "contracted_capacity_rt": 4, "bill_month": month, "dc_consumption_rth": 480 + 20 * i,
                "dc_capacity_aed": 255, "dc_total_aed": 600 + 10 * i})
    return pd.DataFrame(rows, columns=cols)


def test_no_bills_reports_not_yet_validated(bills_dir) -> None:
    status = report.run(write=False)
    assert status["n_units"] == 0 and "total_bill" not in status


def test_report_runs_automatically_on_added_bills(bills_dir) -> None:
    _synthetic_bills().to_csv(bills_dir / "bills.csv", index=False)
    status = report.run(write=False)
    assert status["n_units"] == 2 and status["n_bill_months"] == 6
    for key in ("consumption_rth", "capacity_charge", "total_bill"):
        m = status[key]
        assert m["n_months"] == 6 and m["mape_pct"] >= 0 and 0 <= m["within_20pct"] <= 1
    assert status["calibration_factor_by_system"] == {}      # fewer than 12 months: no calibration yet


def test_report_refuses_bills_with_personal_data(bills_dir) -> None:
    df = _synthetic_bills()
    df["tenant_name"] = "someone"
    df.to_csv(bills_dir / "bills.csv", index=False)
    with pytest.raises(ValueError, match="PII"):
        report.run(write=False)


def test_unconsented_rows_are_ignored(bills_dir) -> None:
    df = _synthetic_bills()
    df["consent"] = "no"
    df.to_csv(bills_dir / "bills.csv", index=False)
    assert report.run(write=False)["n_units"] == 0


def test_sanity_band_check_uses_published_ranges() -> None:
    rows = report.sanity_band_check()
    assert {r["bedrooms"] for r in rows} == {0, 1, 2, 3}


def test_business_case_pnl_and_unit_economics() -> None:
    b = business.BusinessInputs.defaults()
    df = business.pnl(b)
    assert len(df) == 12 and df["revenue"].sum() > 0
    assert (df["costs"] > 0).all()
    assert df["cumulative"].iloc[-1] == pytest.approx(df["profit"].sum())
    ue = business.unit_economics(b)
    assert 0 < ue["llm_cost_per_listing_aed"] < ue["listing_price"]
    assert ue["broker_seat_margin"] > 0.5


def test_break_even_responds_to_prices() -> None:
    b = business.BusinessInputs.defaults()
    b.pricing.update(broker_seat_aed_month=0, portal_aed_per_scored_listing_month=0, developer_report_aed=0,
                     consumer_report_aed=0, pilot_fee_aed=0)
    assert business.break_even_month(business.pnl(b)) is None
