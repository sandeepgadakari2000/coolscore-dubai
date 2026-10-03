"""Shared UI for the CoolScore Streamlit app: setup, forms, result cards, charts, footer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from coolscore import config  # noqa: E402
from coolscore.billing.engine import true_monthly_cost  # noqa: E402
from coolscore.model import predict  # noqa: E402

SCORE_COLORS = {"A": "#0a8f3c", "B": "#5aa83a", "C": "#c99400", "D": "#e07040", "E": "#c93636"}
SCORE_WORDS = {"A": "very low", "B": "low", "C": "typical", "D": "high", "E": "very high"}
ERA_LABELS = {"before_2005": "Before 2005", "2005_2014": "2005–2014", "2015_2021": "2015–2021",
              "2022_plus": "2022 or later"}
SYSTEM_LABELS = {"district_cooling": "District cooling (chiller company)",
                 "building_central_plant": "Building's own chiller plant",
                 "dewa_split_ac": "Split AC on the DEWA bill", "dewa_central_ac": "Central/ducted AC on DEWA"}
PAYER_LABELS = {"tenant": "Tenant pays cooling", "landlord_chiller_free": "Chiller-free (landlord pays)",
                "service_charge": "Included in service charges"}
GLASS_LABELS = {"low": "Little glass", "medium": "Average windows", "high": "Lots of glass",
                "floor_to_ceiling": "Floor-to-ceiling glass"}
BALCONY_LABELS = {"none": "No balcony", "small": "Small balcony (~1.3 m)", "deep": "Deep balcony (2 m+)"}
OBSTRUCTION_LABELS = {"open": "Open view", "partial": "Some towers nearby", "heavy": "Close neighbouring towers"}
OCCUPANCY_LABELS = {"away_daytime": "Out during the day", "home_daytime": "Home during the day"}
SIMPLE_FACINGS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
FACING_OPTIONS = SIMPLE_FACINGS + [f"{a}+{b}" for a, b in
                                   [("N", "E"), ("E", "S"), ("S", "W"), ("W", "N"),
                                    ("NE", "SE"), ("SE", "SW"), ("SW", "NW"), ("NW", "NE")]]
DISCLAIMER = config.settings()["app"]["disclaimer"]
SIMULATED = config.settings()["app"]["simulated_label"]

CSS = """
<style>
.block-container {max-width: 860px; padding-top: 2rem;}
.cs-badge {display:inline-flex; align-items:center; justify-content:center; border-radius:12px;
  font-weight:700; color:#fff; letter-spacing:.02em;}
.cs-card {border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:1rem 1.1rem; margin:.4rem 0 1rem 0;}
.cs-muted {opacity:.72; font-size:.9rem;}
.cs-sim {display:inline-block; font-size:.75rem; padding:.1rem .5rem; border-radius:999px;
  border:1px solid rgba(128,128,128,.4); opacity:.85;}
.cs-big {font-size:1.6rem; font-weight:700; line-height:1.2;}
.cs-flag {background:rgba(250,178,25,.15); border-left:3px solid #fab219; padding:.5rem .8rem; border-radius:6px;}
@media (max-width: 640px) { .cs-big {font-size:1.3rem;} .block-container {padding-left:1rem; padding-right:1rem;} }
</style>
"""


def setup(title: str) -> None:
    st.set_page_config(page_title=f"{title} · CoolScore Dubai", page_icon="❄️", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    _secrets_to_env()


def _secrets_to_env() -> None:
    """Expose an optional Streamlit secret ANTHROPIC_API_KEY to the Anthropic SDK."""
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except (FileNotFoundError, KeyError, AttributeError):
        key = None
    except Exception:  # Streamlit raises its own error type when no secrets file exists
        key = None
    if key:
        os.environ["ANTHROPIC_API_KEY"] = str(key)


def aed(x: float) -> str:
    return f"AED {x:,.0f}"


def aed_range(r) -> str:
    return f"AED {r.p10:,.0f}–{r.p90:,.0f}"


def badge(letter: str, size: int = 56) -> str:
    return (f"<span class='cs-badge' style='background:{SCORE_COLORS[letter]};width:{size}px;height:{size}px;"
            f"font-size:{int(size * 0.55)}px' title='CoolScore {letter}: {SCORE_WORDS[letter]} cooling cost "
            f"per sq ft'>{letter}</span>")


@st.cache_resource(show_spinner=False)
def model_ready() -> bool:
    predict.load_artifact()
    return True


def _select(label, options: dict, value, key, help=None):
    keys = list(options)
    return st.selectbox(label, keys, index=keys.index(value) if value in keys else 0,
                        format_func=lambda k: options[k], key=key, help=help)


def listing_form(prefix: str, defaults: dict | None = None, optional: bool = True, compact: bool = False) -> dict:
    """Listing fields as widgets (call inside or outside st.form). Returns a listing dict."""
    d = defaults or {}
    communities = sorted(config.communities()["communities"])
    c1, c2 = st.columns(2)
    with c1:
        community = st.selectbox("Community", communities, key=f"{prefix}_community",
                                 index=communities.index(d.get("community", "Business Bay")))
        size = st.number_input("Size (sq ft)", 200, 8000, int(d.get("size_sqft", 800)), 25, key=f"{prefix}_size")
        floor = st.number_input("Floor", 1, 150, int(d.get("floor", 12)), key=f"{prefix}_floor")
        facing = st.selectbox("Main windows face", FACING_OPTIONS, key=f"{prefix}_facing",
                              index=FACING_OPTIONS.index(d.get("facing", "W")),
                              help="Corner units have two facades, e.g. W+N. Not sure? Use the direction "
                                   "helper on the Check a Unit page.")
    with c2:
        era = _select("Building completed", ERA_LABELS, d.get("era_band", "2005_2014"), f"{prefix}_era")
        beds = st.selectbox("Bedrooms", [0, 1, 2, 3, 4, 5], index=int(d.get("bedrooms", 1)),
                            format_func=lambda b: "Studio" if b == 0 else str(b), key=f"{prefix}_beds")
        total = st.number_input("Total floors in building", 1, 150, int(max(d.get("total_floors", 30), floor)),
                                key=f"{prefix}_total")
        glass = _select("Glass", GLASS_LABELS, d.get("glass", "medium"), f"{prefix}_glass")
    c3, c4 = st.columns(2)
    with c3:
        system = _select("Cooling system", SYSTEM_LABELS, d.get("system", "district_cooling"), f"{prefix}_system")
        balcony = _select("Balcony / shading", BALCONY_LABELS, d.get("balcony", "none"), f"{prefix}_balcony")
    with c4:
        payer = _select("Who pays for cooling", PAYER_LABELS, d.get("payer", "tenant"), f"{prefix}_payer")
        obstruction = _select("View", OBSTRUCTION_LABELS, d.get("obstruction", "partial"), f"{prefix}_obst",
                              help="Neighbouring towers shade the facade and cut solar heat.")
    listing = dict(community=community, era_band=era, size_sqft=float(size), bedrooms=int(beds),
                   floor=int(floor), total_floors=int(total), facing=facing, glass=glass, balcony=balcony,
                   obstruction=obstruction, system=system, payer=payer)
    if not compact:
        rent = st.number_input("Annual rent (AED, optional)", 0, 2_000_000, int(d.get("annual_rent_aed", 0)), 1000,
                               key=f"{prefix}_rent")
        listing["annual_rent_aed"] = float(rent) if rent else None
    if optional:
        with st.expander("Optional: your household (narrows the range)"):
            use = st.checkbox("Use these details", value=bool(d.get("setpoint_c")), key=f"{prefix}_use")
            hh = st.number_input("People living there", 1, 10, int(d.get("household_size", beds + 1)),
                                 key=f"{prefix}_hh")
            occ = _select("Daytime", OCCUPANCY_LABELS, d.get("occupancy", "away_daytime"), f"{prefix}_occ")
            sp = st.slider("Usual AC temperature (°C)", 20.0, 28.0, float(d.get("setpoint_c", 24.0)), 0.5,
                           key=f"{prefix}_sp")
            if use:
                listing.update(household_size=int(hh), occupancy=occ, setpoint_c=float(sp))
    return listing


def run_estimate(listing: dict):
    clean = {k: v for k, v in listing.items() if k not in ("annual_rent_aed", "price_aed")}
    return predict.estimate(clean)


def monthly_chart(est) -> go.Figure:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Bar(x=months, y=est.monthly_p50, marker_color="#2a78d6", width=0.5,
                           hovertemplate="%{x}: AED %{y:,.0f} (typical)<extra></extra>"))
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="AED / month (P50)",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,.2)", tickformat=",")
    return fig


def drivers_chart(est) -> go.Figure | None:
    drivers = [d for d in est.drivers if abs(d["aed_per_year"]) >= 1][:6]
    if not drivers:
        return None
    labels = [d["driver"] for d in drivers][::-1]
    values = [d["aed_per_year"] for d in drivers][::-1]
    colors = ["#c93636" if v > 0 else "#0a8f3c" for v in values]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=colors, width=0.5,
                           text=[f"{'+' if v > 0 else '−'}AED {abs(v):,.0f}/yr" for v in values],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:+,.0f} AED/yr<extra></extra>"))
    fig.update_layout(height=60 + 46 * len(labels), margin=dict(l=10, r=90, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="AED per year")
    fig.update_xaxes(zeroline=True, zerolinecolor="rgba(128,128,128,.5)", gridcolor="rgba(128,128,128,.15)")
    return fig


def result_card(est, rent: float | None = None) -> None:
    """The main result: score, monthly ranges, annual range, true cost, drivers, how-calculated."""
    left, right = st.columns([1, 3])
    with left:
        st.markdown(badge(est.score, 84), unsafe_allow_html=True)
        st.markdown(f"<div class='cs-muted'>CoolScore {est.score}: {SCORE_WORDS[est.score]} cooling cost "
                    f"per sq ft</div>", unsafe_allow_html=True)
    with right:
        who = {"tenant": "you pay", "landlord_chiller_free": "you pay (fans only, chiller-free)",
               "service_charge": "you pay (fans only)"}[est.listing["payer"]]
        st.markdown(f"<span class='cs-sim'>{SIMULATED}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='cs-big'>{aed_range(est.summer_month)} / month in summer</div>"
                    f"<div>{aed_range(est.winter_month)} / month in winter · "
                    f"<b>{aed_range(est.annual)}</b> a year ({who})</div>"
                    f"<div class='cs-muted'>Likely range P10–P90; typical (P50) {aed(est.annual.p50)} a year.</div>",
                    unsafe_allow_html=True)
    if rent:
        tc = true_monthly_cost(rent, est.annual.p50 / 12)
        st.markdown(f"<div class='cs-card'><b>True monthly cost ≈ {aed(tc['total'])}</b><br>"
                    f"<span class='cs-muted'>rent {aed(tc['rent'])} + cooling {aed(tc['cooling'])} (typical) + "
                    f"municipality housing fee {aed(tc['housing_fee'])} (5% of rent, on the DEWA bill). "
                    f"Other electricity and water not included.</span></div>", unsafe_allow_html=True)
        with st.expander("How is the true monthly cost calculated?"):
            st.write(f"Annual rent ÷ 12 = {aed(tc['rent'])}. Cooling = typical (P50) annual estimate ÷ 12 = "
                     f"{aed(tc['cooling'])}. Housing fee = 5% × annual rent ÷ 12 = {aed(tc['housing_fee'])} "
                     "(Dubai Municipality fee collected by DEWA; marked 'verify' in our assumptions).")
    if est.assumed:
        nice = ", ".join(a.replace("_", " ") for a in est.assumed)
        st.markdown(f"<div class='cs-flag'>Assumed because not given: <b>{nice}</b>. Change them above if you "
                    f"know better.</div>", unsafe_allow_html=True)
    fig = drivers_chart(est)
    if fig is not None:
        st.markdown("**What drives this unit's cost** (simulated difference per year)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.plotly_chart(monthly_chart(est), width="stretch", config={"displayModeBar": False})
    with st.expander("How is this calculated?"):
        st.write(est.formula)
        st.write(f"Model: gradient-boosted quantile models trained on 40,000 simulated units (hourly building "
                 f"physics on 2023–25 Dubai weather + published tariffs). Inputs used: "
                 f"{'listing facts + your household details' if est.variant == 'detailed' else 'listing facts only'}.")
        if est.listing["system"] == "district_cooling":
            st.write(f"Contracted capacity estimate ≈ {est.contracted_rt_estimate:.1f} RT (from size; real "
                     f"allocations vary) → fixed capacity charge ≈ {aed(est.capacity_aed_per_year)} a year incl. "
                     "VAT, payable even with the AC off.")
        st.write(f"CoolScore uses a standard household (bedrooms + 1 people, out by day, 24 °C) and a "
                 f"standard district-cooling tariff so units compare fairly: "
                 f"{est.intensity_aed_per_sqft:.2f} AED per sq ft per year. Grade cut-offs (AED/sq ft/yr): "
                 + ", ".join(f"{l} ≤ {c:.2f}" for l, c in zip("ABCD", est.score_cuts)) + ", E above.")
    for note in est.notes:
        st.caption(note)


def footer() -> None:
    st.divider()
    st.caption(f"{DISCLAIMER} {SIMULATED} Weather data by Open-Meteo.com (CC BY 4.0). "
               "Fictional building names only; no real portal or developer is depicted.")
