"""Real-bill folder must never contain personal data (brief §4.5)."""

from pathlib import Path

import pandas as pd
import pytest

from coolscore.validation import pii

ROOT = Path(__file__).resolve().parents[1]
BILLS = ROOT / "data" / "real_bills"

REQUIRED_COLUMNS = {
    "community", "building_era_band", "floor_band", "facing", "size_sqft", "bedrooms",
    "cooling_system", "cooling_payer", "bill_month", "dc_total_aed", "consent",
}


def test_real_bill_folder_has_no_pii() -> None:
    problems = pii.check_folder(BILLS)
    assert problems == [], "\n".join(problems)


def test_template_has_required_columns() -> None:
    cols = set(pii.allowed_columns(BILLS))
    assert REQUIRED_COLUMNS <= cols, REQUIRED_COLUMNS - cols


def test_template_columns_are_not_pii_like() -> None:
    assert pii.pii_like_columns(pii.allowed_columns(BILLS)) == []


@pytest.mark.parametrize(
    "column",
    ["tenant_name", "Email", "phone", "unit_number", "dewa_account", "premise_no",
     "building_name", "tower", "bill_image", "emirates_id", "makani"],
)
def test_guard_flags_pii_columns(column: str) -> None:
    assert pii.pii_like_columns([column]) == [column]


@pytest.mark.parametrize(
    "value, reason",
    [("someone@example.com", "email"), ("+971 50 000 0000", "phone"),
     ("050 000 0000", "phone"), ("2000000001", "8+ digit")],
)
def test_guard_flags_pii_values(value: str, reason: str) -> None:
    df = pd.DataFrame({"community": [value]})
    hits = pii.pii_like_values(df)
    assert hits and reason in hits[0][2]


def test_guard_passes_normal_bill_values() -> None:
    df = pd.DataFrame({
        "community": ["Dubai Marina"], "bill_month": ["2025-08"], "size_sqft": ["750"],
        "dc_total_aed": ["1234.56"], "submitted_date": ["2026-10-03"], "facing": ["W+N"],
    })
    assert pii.pii_like_values(df) == []
