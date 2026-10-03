"""Repo skeleton and research kit are complete (Phase 0)."""

import importlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "user-research"
QUOTE_PLACEHOLDER = "[REAL QUOTE — FILL AFTER INTERVIEW]"

SUBPACKAGES = ["weather", "physics", "billing", "simulate", "model", "validation", "assistant"]


@pytest.mark.parametrize("name", ["coolscore"] + [f"coolscore.{s}" for s in SUBPACKAGES])
def test_packages_import(name: str) -> None:
    assert importlib.import_module(name).__doc__


def test_claude_md_is_short() -> None:
    lines = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert 0 < len(lines) < 80


@pytest.mark.parametrize(
    "path",
    ["CLAUDE.md", "PROGRESS.md", "README.md", "CoolScore_PROJECT_BRIEF.md", "requirements.txt",
     "Makefile", "tasks.py", "docs/plan.md", "docs/competitive_landscape.md"],
)
def test_required_files_exist(path: str) -> None:
    assert (ROOT / path).is_file()


@pytest.mark.parametrize("persona", ["tenants", "brokers", "investors", "developers"])
def test_interview_guide_per_persona(persona: str) -> None:
    text = (RESEARCH / f"interview_guide_{persona}.md").read_text(encoding="utf-8")
    assert "consent" in text.lower()


def test_research_kit_has_outreach_bill_request_and_findings() -> None:
    for name in ["outreach_messages.md", "bill_request.md", "findings_template.md",
                 "hypotheses.md", "interview_log.csv"]:
        assert (RESEARCH / name).is_file(), name


def test_findings_contain_no_fabricated_quotes() -> None:
    """Every quoted line in the findings file is still the placeholder until real interviews."""
    text = (RESEARCH / "findings_template.md").read_text(encoding="utf-8")
    assert QUOTE_PLACEHOLDER in text
    quotes = re.findall(r'"([^"\n]{12,})"', text)
    real = [q for q in quotes if q != QUOTE_PLACEHOLDER]
    assert real == [], f"Non-placeholder quotes found: {real}"
