"""Guard against personal data in the real-bill folder.

Real bills must be anonymised before they enter the repo: no names, contact
details, unit/building identifiers, account numbers or images. This module
checks column names (allow-list from ``template.csv`` plus a deny-list of
PII-like patterns) and cell values (emails, phone numbers, long digit runs
that look like account or premise numbers).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

TEMPLATE_NAME = "template.csv"

# Column names that suggest personal or re-identifying data.
PII_COLUMN_PATTERNS: tuple[str, ...] = (
    r"name",
    r"e-?mail",
    r"phone|mobile|whatsapp|contact",
    r"(unit|flat|apartment|apt|villa)_?(no|num|number)",
    r"account",
    r"premise",
    r"contract_?(no|num|number|id)",
    r"iban|card",
    r"emirates_?id|passport|visa",
    r"address|street|makani|plot",
    r"building_?(name|no|num|number)|tower",
    r"ejari",
    r"image|photo|scan|attachment|file",
)

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
# UAE mobile/landline formats: +971..., 00971..., 05x xxx xxxx, 04 xxx xxxx.
PHONE_RE = re.compile(r"(\+|00)971[\s-]?\d|(?<!\d)0[2-9]\d?[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
LONG_DIGITS_RE = re.compile(r"\d{8,}")


def pii_like_columns(columns: list[str]) -> list[str]:
    """Return the column names that match any PII-like pattern."""
    flagged = []
    for col in columns:
        key = col.strip().lower()
        if any(re.search(p, key) for p in PII_COLUMN_PATTERNS):
            flagged.append(col)
    return flagged


def pii_like_values(df: pd.DataFrame) -> list[tuple[int, str, str]]:
    """Return ``(row, column, reason)`` for cells that look like personal data."""
    hits: list[tuple[int, str, str]] = []
    for col in df.columns:
        for row, cell in df[col].items():
            if pd.isna(cell):
                continue
            text = str(cell)
            if EMAIL_RE.search(text):
                hits.append((int(row), col, "email address"))
            elif PHONE_RE.search(text):
                hits.append((int(row), col, "phone number"))
            elif LONG_DIGITS_RE.search(text):
                hits.append((int(row), col, "8+ digit number (account/premise-like)"))
    return hits


def allowed_columns(folder: Path) -> list[str]:
    """Columns permitted in real-bill files: exactly those in ``template.csv``."""
    return list(pd.read_csv(folder / TEMPLATE_NAME, nrows=0).columns)


def check_bill_file(path: Path, allowed: list[str]) -> list[str]:
    """Return human-readable problems for one real-bill CSV (empty list = clean)."""
    df = pd.read_csv(path, dtype=str)
    problems = [f"{path.name}: PII-like column '{c}'" for c in pii_like_columns(list(df.columns))]
    problems += [
        f"{path.name}: column '{c}' is not in {TEMPLATE_NAME}" for c in df.columns if c not in allowed
    ]
    problems += [
        f"{path.name}: row {r} column '{c}' looks like {why}" for r, c, why in pii_like_values(df)
    ]
    return problems


def check_folder(folder: Path) -> list[str]:
    """Check every CSV in the real-bill folder, including the template itself."""
    allowed = allowed_columns(folder)
    problems: list[str] = []
    for path in sorted(folder.glob("*.csv")):
        problems += check_bill_file(path, allowed)
    return problems
