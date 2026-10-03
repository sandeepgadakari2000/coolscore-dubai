"""Phase 2 report: archetypes, engine verification, orientation effect, stock spread.

Writes ``docs/phase2_physics.md`` and ``docs/figures/phase2_physics.html``.
Run with ``python tasks.py report-physics`` (after ``tasks.py data``).
"""

from __future__ import annotations

import time
from dataclasses import replace

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from coolscore import config
from coolscore.physics import engine
from coolscore.physics.params import ERA_TO_ARCHETYPE, ORIENTATIONS, ListingSpec, build_params
from coolscore.weather.report import GRID, INK, INK_2, MUTED, SURFACE, _fmt, _md_table

YEAR = 2024
TYPICAL = ListingSpec(community="Business Bay", era_band="2005_2014", size_sqft=800, bedrooms=1,
                      floor=15, total_floors=30, facing="N", glass="medium", balcony="none",
                      obstruction="partial")
BLUE, ORANGE = "#2a78d6", "#eb6834"


def orientation_table(site_community: str) -> pd.DataFrame:
    """Typical unit (central hidden values) facing each of the 8 directions."""
    specs = [replace(TYPICAL, community=site_community, facing=o) for o in ORIENTATIONS]
    r = engine.simulate_listings(specs, YEAR)
    summer = r.total_kwh[:, 5:8].sum(axis=1)
    df = pd.DataFrame({
        "Annual kWh_th": r.annual_kwh,
        "Annual vs N %": 100 * (r.annual_kwh / r.annual_kwh[0] - 1),
        "Jun-Aug kWh_th": summer,
        "Jun-Aug vs N %": 100 * (summer / summer[0] - 1),
        "Design peak kW": r.design_kw,
        "Peak vs N %": 100 * (r.design_kw / r.design_kw[0] - 1),
    }, index=list(ORIENTATIONS))
    return df


def stock_sample(n: int, seed: int) -> pd.DataFrame:
    """A quick random stock (all eras, sizes, floors, facings) with sampled hidden variables."""
    rng = np.random.default_rng(seed)
    eras = list(ERA_TO_ARCHETYPE)
    rows = []
    for _ in range(n):
        beds = int(rng.integers(0, 4))
        size = float(rng.uniform(*[(350, 650), (600, 1050), (950, 1600), (1300, 2400)][beds]))
        total = int(rng.integers(5, 16)) if (era := eras[rng.integers(0, 4)]) == "before_2005" else int(rng.integers(12, 60))
        f1 = ORIENTATIONS[rng.integers(0, 8)]
        facing = f1 if rng.random() > 0.25 else f"{f1}+{ORIENTATIONS[(ORIENTATIONS.index(f1) + 2) % 8]}"
        rows.append(ListingSpec(
            community="Business Bay", era_band=era, size_sqft=size, bedrooms=beds,
            floor=int(rng.integers(1, total + 1)), total_floors=total, facing=facing,
            glass=["low", "medium", "high", "floor_to_ceiling"][rng.integers(0, 4)],
            balcony=["none", "small", "deep"][rng.integers(0, 3)],
            obstruction=["open", "partial", "heavy"][rng.integers(0, 3)]))
    p = build_params(rows, rng)
    r = engine.run_site_year(p, "central", YEAR)
    return pd.DataFrame({
        "era": [s.era_band for s in rows],
        "kwh_m2": r.annual_kwh / p.floor_area_m2,
        "latent_share": r.lat_kwh.sum(axis=1) / r.annual_kwh,
        "peak_w_m2": 1000 * r.design_kw / p.floor_area_m2,
    })


def archetype_table() -> pd.DataFrame:
    arch = config.load_yaml("archetypes.yaml")["archetypes"]
    infil = config.require("physics.infiltration_ach")
    rows = {}
    for aid, a in arch.items():
        prm = a["params"]

        def rng_txt(key):
            v = prm[key]["value"]
            return f"{v['central']} ({v['low']}–{v['high']})"
        glazing = (f"U {rng_txt('glazing_u')}, SHGC {rng_txt('glazing_shgc')}" if "glazing_u" in prm
                   else f"code by WWR band × {rng_txt('glazing_compliance')}")
        i = infil[a["era_band"]]
        rows[f"{aid} {a['label']}"] = {
            "Completed": {"before_2005": "before 2005", "2005_2014": "2005–2014", "2015_2021": "2015–2021",
                          "2022_plus": "2022+"}[a["era_band"]],
            "Wall U": rng_txt("wall_u"), "Roof U": rng_txt("roof_u"), "Glazing": glazing,
            "Infiltration ACH": f"{i['central']} ({i['low']}–{i['high']})",
        }
    return pd.DataFrame(rows).T


def _text_table(df: pd.DataFrame) -> str:
    lines = ["| | " + " | ".join(df.columns) + " |", "|---|" + "---|" * len(df.columns)]
    lines += [f"| {i} | " + " | ".join(str(v) for v in row.values) + " |" for i, row in df.iterrows()]
    return "\n".join(lines)


def _figure(orient: pd.DataFrame, stock: pd.DataFrame) -> str:
    f1 = go.Figure()
    for col, color, name in [("Annual vs N %", BLUE, "Annual"), ("Jun-Aug vs N %", ORANGE, "Jun–Aug")]:
        f1.add_trace(go.Bar(x=orient.index, y=orient[col], name=name, marker_color=color,
                            width=0.32, hovertemplate="%{y:+.1f}% vs north"))
    f1.update_layout(barmode="group", bargap=0.35)
    f1.update_yaxes(title="Cooling energy vs north-facing (%)", zeroline=True, zerolinecolor=GRID)
    f1.update_xaxes(title="Facing")
    eras = list(ERA_TO_ARCHETYPE)
    labels = ["before 2005", "2005–2014", "2015–2021", "2022+"]
    q = stock.groupby("era")["kwh_m2"].quantile([0.1, 0.5, 0.9]).unstack().reindex(eras)
    f2 = go.Figure()
    f2.add_trace(go.Bar(x=labels, y=q[0.9] - q[0.1], base=q[0.1],
                        marker_color=BLUE, width=0.18, name="P10–P90",
                        hovertemplate="P10 %{base:.0f} – P90 %{y:.0f} kWh/m²"))
    f2.add_trace(go.Scatter(x=labels, y=q[0.5], mode="markers", name="Median",
                            marker={"color": INK, "size": 10, "line": {"color": SURFACE, "width": 2}},
                            hovertemplate="median %{y:.0f} kWh/m²"))
    f2.update_yaxes(title="Cooling energy (kWh_th per m² per year)", rangemode="tozero")
    f2.update_xaxes(title="Building completed")
    summer_max, annual_max = orient["Jun-Aug vs N %"].max(), orient["Annual vs N %"].max()
    title1 = (f"Facing changes summer cooling by up to {summer_max:.0f}% and the annual total by up to "
              f"{annual_max:.0f}% (vs north)")
    for fig, title in [(f1, title1),
                       (f2, "Newer buildings need less cooling, but the spread within each era is wide")]:
        fig.update_layout(title={"text": title, "x": 0, "font": {"size": 15, "color": INK}}, height=380,
                          paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                          font={"family": "system-ui, -apple-system, Segoe UI, sans-serif", "color": INK_2},
                          legend={"orientation": "h", "y": -0.25, "x": 0}, margin={"l": 60, "r": 20, "t": 60, "b": 80})
        fig.update_yaxes(gridcolor=GRID, tickfont={"color": MUTED})
        fig.update_xaxes(tickfont={"color": MUTED})
    return f1.to_html(full_html=False, include_plotlyjs="cdn") + f2.to_html(full_html=False, include_plotlyjs=False)


def write_report() -> None:
    central = orientation_table("Business Bay")
    inland = orientation_table("Dubai South")
    t0 = time.time()
    stock = stock_sample(2000, seed=42)
    secs = time.time() - t0
    by_era = stock.groupby("era").agg(
        units=("kwh_m2", "size"),
        p10_kwh_m2=("kwh_m2", lambda s: s.quantile(0.1)),
        median_kwh_m2=("kwh_m2", "median"),
        p90_kwh_m2=("kwh_m2", lambda s: s.quantile(0.9)),
        median_latent_share=("latent_share", "median"),
        median_peak_w_m2=("peak_w_m2", "median"),
    ).reindex(list(ERA_TO_ARCHETYPE))
    by_era.columns = ["Units", "P10 kWh/m²", "Median kWh/m²", "P90 kWh/m²", "Latent share", "Median design peak W/m²"]

    out_dir = config.ROOT / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase2_physics.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
        "initial-scale=1'><title>Phase 2 physics</title><style>body{background:#fcfcfb;color:#0b0b0b;"
        "font-family:system-ui,-apple-system,'Segoe UI',sans-serif;max-width:980px;margin:24px auto;padding:0 16px}"
        "p{color:#52514e}</style></head><body><h1>CoolScore Phase 2: physics engine</h1><p>Simulated thermal "
        "cooling energy (not bills). Typical unit: 800 sq ft 1-bedroom, 2005–2014 tower, floor 15 of 30, medium "
        "glass, partial obstruction, central hidden values, 2024 central-site weather. Tables: "
        "docs/phase2_physics.md.</p>" + _figure(central, stock) + "</body></html>", encoding="utf-8")

    c = central
    md = f"""# Phase 2: physics engine

*Generated by `python tasks.py report-physics` · **simulated thermal energy, not bills** · charts:
[docs/figures/phase2_physics.html](figures/phase2_physics.html)*

## Engine

- **Model:** ISO 13790:2008 simple hourly method (5R1C, Annex C), one thermal zone per apartment, neighbours
  adiabatic, ideal cooling to the setpoint. Vectorised in numpy: one step per hour across all units.
- **Envelope:** facade(s) by orientation (corners have two), window-to-wall ratio, glazing U and SHGC
  (ISO F_w 0.90, frame fraction 0.20), opaque walls with sol-air absorption and sky radiation (ISO Eq. 46–47),
  roof for top-floor units.
- **Shading:** balcony as an overhang (profile-angle geometry) over part of the window width; neighbouring
  towers as a horizon angle that falls with height. Both reduce beam and sky-diffuse sun (2-D view factors).
- **Air and moisture:** infiltration and untreated ventilation at outdoor conditions (sensible + latent);
  centrally pre-treated fresh air is not on the unit meter. Latent load counted whenever the coil runs.
- **Gains and behaviour:** ASHRAE occupant gains (72/45 W awake, 66/31 W resting); appliances with the ISO
  13790 Table G.7 residential profile; away/home profiles with the Saturday–Sunday weekend and a Friday half day;
  optional Ramadan schedule; behaviour when away (keep setpoint / 3 K setback / off); window opening in mild weather.
- **Outputs per unit:** monthly sensible and latent kWh_th, monthly load × (T_out − 35 °C)⁺ (for AC efficiency in
  Phase 3), cooling hours, peak and design (98th percentile daily) load. Hourly arrays are never stored for big runs.

**Verification** (`tests/test_physics.py`): the vectorised engine reproduces a literal, line-by-line implementation of
ISO 13790 Annex C (two trial runs + interpolation, Eq. C.13) to within 1e-6 W on corner, top-floor, setback and
AC-off units; at steady state the cooling load equals the network's analytic conductance × ΔT; all six invariants
from brief §9 pass (more glass ↑, west > north in summer, higher setpoint ↓, more shading ↓, top ≥ mid floor,
no sun ↓), plus more people ↑, corner ↑, AC off when away ↓, latent follows humidity.

**Speed:** 2,000 sampled units × 8,784 hours took {secs:.0f} s, including sampling. That puts 40,000 scenarios at about
{40 * secs / 2 / 60:.0f} minutes, inside the 15-minute pipeline budget.

## Archetypes (central value and simulated range)

{_text_table(archetype_table())}

Sources and caveats for every value are in `config/archetypes.yaml` and `config/assumptions.yaml`. Values marked
**MODELLING ASSUMPTION** there (thermal-bridge allowances, infiltration, pre-treated fresh-air shares) are the first
things real bills should test. The newest two eras share the same legal envelope limits (compulsory since 2014,
kept by Al Sa'fat). Al Sa'fat adds thermal-bridge elimination and air-leakage testing, which is what separates A4.

## Orientation effect (typical unit, central values)

Central site (Business Bay weather):

{_md_table(c)}

Inland site (Dubai South weather):

{_md_table(inland)}

**Reading it:**

- **North is cheapest.** West- and east-facing need about {c.loc['W', 'Jun-Aug vs N %']:.0f}% more cooling than
  north in Jun–Aug, and about {c.loc['W', 'Annual vs N %']:.0f}% more over the year.
- **South leads the annual ranking** (+{c.loc['S', 'Annual vs N %']:.0f}%) because of low winter sun on a sealed,
  air-conditioned unit. In summer, south is no worse than north, which matches Phase 1.
- **West vs east is small in energy.** Over the year west comes to {c.loc['W', 'Annual kWh_th'] / c.loc['E', 'Annual kWh_th'] * 100 - 100:+.1f}%
  against east. West's afternoon sun does coincide with the heat (Phase 1). But with a fixed setpoint, cooling
  energy mostly adds up the gains whatever their timing, and the building's mass delays east's morning gains into
  the hot midday. West shows up instead in the **design peak** ({c.loc['W', 'Design peak kW'] / c.loc['E', 'Design peak kW'] * 100 - 100:+.1f}% vs east),
  which matters for district-cooling capacity and for AC efficiency on DEWA-billed systems (Phase 3).
- **Against the literature:** a 2024 UAE study (*Buildings* 14(4):876, search snippet; paper not opened) reports
  east- and west-facing *windows* using about 35–41% more August cooling than north- and south-facing ones, and
  north windows 36% less annual energy. Our whole-unit summer differences are much smaller (E/W about
  {c.loc[['E', 'W'], 'Jun-Aug vs N %'].mean():.0f}% above N/S) but point the
  same way (E/W > N ≈ S in summer; north lowest annually). Walls, internal gains and outdoor-air latent load
  (~{by_era['Latent share'].median():.0%} of the total) dilute a window-only effect. If real bills show bigger
  orientation gaps, the first suspects are blind use, infiltration and the latent share.

## Spread across a random stock (2,000 sampled units, central-site weather)

{_md_table(by_era)}

These are thermal kWh at the unit coil, before any tariff. For scale: 200 kWh_th/m² a year is about 57 RTh/m²
(5.3 RTh per sq ft). Billing in Phase 3 turns them into AED.

## Limitations

- One thermal zone per apartment; no room-by-room comfort; adiabatic neighbours (no heat from a hot corridor or an
  unoccupied unit next door).
- 2-D shading geometry; neighbouring towers are not specular reflectors (glass towers can reflect sun *into* a unit).
- Behaviour (setpoint, away mode, blinds, window opening) is sampled, not observed; it can move a bill more than the
  building does. Optional household details in the app narrow this.
- Ideal, unlimited cooling: real AC can't hold 24 °C during some peaks, which slightly lowers real consumption.
"""
    (config.ROOT / "docs" / "phase2_physics.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_report()
    print("wrote docs/phase2_physics.md and docs/figures/phase2_physics.html")
