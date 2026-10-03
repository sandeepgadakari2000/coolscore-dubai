"""Load project configuration and enforce the assumption-register rules.

Real-world numbers are read through :func:`require`, which refuses to hand
out a placeholder (``value: null``). A pipeline stage therefore cannot run on
an unresearched number by accident.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


class MissingAssumptionError(RuntimeError):
    """Raised when code needs an assumption whose value is still a placeholder."""


@lru_cache(maxsize=None)
def load_yaml(name: str) -> dict:
    """Parse ``config/<name>`` (cached; config files are read-only at runtime)."""
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def settings() -> dict:
    """Pipeline and app settings (design choices, not facts)."""
    return load_yaml("settings.yaml")


def communities() -> dict:
    """Microclimate sites and the community -> microclimate mapping."""
    return load_yaml("communities.yaml")


def record(path: str, file: str = "assumptions.yaml") -> dict:
    """Return the full assumption record at a dotted ``path``, e.g. ``physics.ground_albedo``."""
    node: Any = load_yaml(file)
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"{file}: no record at '{path}'")
        node = node[key]
    if not isinstance(node, dict) or "value" not in node:
        raise KeyError(f"{file}: '{path}' is not an assumption record")
    return node


def require(path: str, file: str = "assumptions.yaml") -> Any:
    """Return an assumption's value, refusing placeholders."""
    rec = record(path, file)
    if rec["value"] is None:
        raise MissingAssumptionError(
            f"{file}: '{path}' is still a placeholder (phase {rec.get('phase')}). "
            "Research it and fill value/source/date_checked before running this stage."
        )
    return rec["value"]


def path(key: str) -> Path:
    """Absolute path for a ``settings.paths`` entry."""
    return ROOT / settings()["paths"][key]
