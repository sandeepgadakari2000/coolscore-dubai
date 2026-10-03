"""Readable view of the assumption registers: ``docs/assumptions.md``.

The YAML files stay the single source of truth; this module flattens them into
one table per section so a reviewer can see every real-world number, its type
(sourced / modelling assumption / placeholder / proposal), whether it still
needs verifying, and where it came from. Regenerate with
``python tasks.py assumptions`` (a test fails if the committed file is stale).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator

from coolscore import config

FILES = ("assumptions.yaml", "archetypes.yaml")
KINDS = ("MODELLING ASSUMPTION", "PLACEHOLDER", "PROPOSAL")
OUT = config.ROOT / "docs" / "assumptions.md"


def records(node, path: str = "") -> Iterator[tuple[str, dict]]:
    """Yield ``(dotted path, record)`` for every assumption record in a parsed YAML tree."""
    if isinstance(node, dict):
        if "value" in node and "source" in node:
            yield path, node
            return
        for k, v in node.items():
            yield from records(v, f"{path}.{k}" if path else str(k))


def kind(rec: dict) -> str:
    """Sourced, one of KINDS (from the notes), or 'not yet researched' for a null value."""
    if rec["value"] is None:
        return "not yet researched"
    note = str(rec.get("notes") or "")
    return next((k for k in KINDS if k in note), "sourced")


def register() -> list[dict]:
    """One row per record across both registers."""
    rows = []
    for file in FILES:
        for path, rec in records(config.load_yaml(file)):
            rows.append({"file": file, "path": path, "section": path.split(".")[0], "kind": kind(rec), **rec})
    return rows


def _cell(x, limit: int) -> str:
    text = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    text = " ".join(str(text).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render() -> str:
    """The full Markdown document (deterministic, so it can be checked in tests)."""
    rows = register()
    counts = Counter(r["kind"] for r in rows)
    to_verify = sum(1 for r in rows if r["verify"])
    lines = [
        "# Assumptions register",
        "",
        "*Generated from `config/assumptions.yaml` and `config/archetypes.yaml` by `python tasks.py assumptions`. "
        "Edit the YAML, not this file.*",
        "",
        "Every real-world number CoolScore uses lives in those two files with a value, unit, source URL, the date it "
        "was checked, a `verify` flag and notes. Code reads them through `config.require()`, which refuses to run on "
        "a placeholder. Notes are shortened here; the YAML has them in full.",
        "",
        "| Type | Meaning | Records |",
        "|---|---|---|",
        f"| sourced | Taken from the cited source | {counts['sourced']} |",
        f"| MODELLING ASSUMPTION | No source gives this number; the cited source anchors it | "
        f"{counts['MODELLING ASSUMPTION']} |",
        f"| PROPOSAL | CoolScore's own plan or price, not market data | {counts['PROPOSAL']} |",
        f"| PLACEHOLDER | Engineering estimate to replace with a measurement | {counts['PLACEHOLDER']} |",
        f"| not yet researched | `value: null`; nothing may use it | {counts['not yet researched']} |",
        "",
        f"**{len(rows)} records, {to_verify} still marked `verify: true`** (to be confirmed by Sandeep against the "
        "source).",
        "",
        "## Verify first",
        "",
        "These move the AED answer most and rest on the weakest evidence:",
        "",
        "1. `billing.district_cooling.contracted_capacity_sqft_per_rt`: sets the fixed capacity charge, often the "
        "largest line on a district-cooling bill (secondary sources only).",
        "2. `billing.district_cooling.*` tariffs, `billing.dewa.residential_electricity_slabs` and "
        "`billing.dewa.fuel_surcharge`: re-check on the provider pages before any demo (the fuel surcharge changes "
        "monthly).",
        "3. `physics.infiltration_ach`, `physics.fresh_air_pretreated_share`, `physics.untreated_ventilation_fraction` "
        "and `physics.appliance_lighting_gain`: the biggest drivers of the latent (humidity) load.",
        "4. Archetype envelope values (`archetypes.yaml`), especially the pre-2005 and 2005–2014 eras.",
        "5. `business.*`: every price and plan number is a proposal to test in broker interviews.",
        "",
    ]
    sections: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        sections.setdefault((r["file"], r["section"]), []).append(r)
    for (file, section), recs in sections.items():
        lines += [f"## {section} (`{file}`)", "",
                  "| Assumption | Value | Unit | Type | Verify | Checked | Source | Notes |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in recs:
            name = r["path"].split(".", 1)[1] if "." in r["path"] else r["path"]
            src = f"[link]({r['source']})" if r["source"] else "—"
            lines.append(
                f"| `{name}` | {_cell(r['value'], 70) if r['value'] is not None else '—'} | {_cell(r['unit'], 50)} | "
                f"{r['kind']} | {'yes' if r['verify'] else 'no'} | {r['date_checked'] or '—'} | {src} | "
                f"{_cell(r.get('notes') or '', 160)} |")
        lines.append("")
    return "\n".join(lines)


def write() -> None:
    OUT.write_text(render(), encoding="utf-8")


if __name__ == "__main__":
    write()
    print(f"wrote {OUT.relative_to(config.ROOT)}")
