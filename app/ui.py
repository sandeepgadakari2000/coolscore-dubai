"""Shared UI for the CoolScore Streamlit app: the Dubai liquid-glass theme, forms, the live climate
scene, result details, charts and footer.

Design: a Dubai dusk backdrop (desert-gold glow, Gulf turquoise, slow liquid light) under frosted
"liquid glass" panels. The animated scene is a custom component (``app/components/climate_stage``)
that plays a typical day of *measured* Dubai weather for the unit; each rerun only sends new
values, so the scene, sun and numbers glide instead of reloading.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

from coolscore import config  # noqa: E402
from coolscore.billing.engine import true_monthly_cost  # noqa: E402
from coolscore.model import predict  # noqa: E402
from coolscore.weather import climate, dataset  # noqa: E402

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
MONTHS = climate.MONTHS
PAYER_SHORT = {"tenant": "you pay", "landlord_chiller_free": "you pay · fans", "service_charge": "you pay · fans"}
DISCLAIMER = config.settings()["app"]["disclaimer"]
SIMULATED = config.settings()["app"]["simulated_label"]

# Palette (Dubai dusk): night navy, desert gold, sand, Gulf turquoise, coral heat.
GOLD, SAND, TURQ, CORAL, SKY, INK = "#f5b942", "#e8c38a", "#2ec4b6", "#ff7a59", "#7cc4ff", "#f6f0e6"

# A subtle eight-point-star lattice (generic Islamic geometric motif) used as a texture on glass.
_PATTERN = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 56 56'>"
            "<g fill='none' stroke='%23ffffff' stroke-opacity='0.07' stroke-width='1'>"
            "<path d='M28 6 L34 22 L50 28 L34 34 L28 50 L22 34 L6 28 L22 22 Z'/>"
            "<rect x='16' y='16' width='24' height='24' transform='rotate(45 28 28)'/></g></svg>")
# A fictional skyline silhouette for the page backdrop (no real towers).
_SKYLINE = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 220' "
            "preserveAspectRatio='none'><path fill='%23060918' d='M0 220 L0 160 L40 160 L40 120 L70 120 L70 150 "
            "L110 150 L110 90 L125 70 L140 90 L140 140 L190 140 L190 60 L215 60 L215 140 L260 140 L260 110 L300 100 "
            "L300 150 L350 150 L350 40 L362 20 L374 40 L374 150 L420 150 L420 120 L470 120 L470 70 L500 70 L500 130 "
            "L560 130 L560 95 L590 85 L590 145 L640 145 L640 50 L660 30 L680 50 L680 140 L730 140 L730 115 L780 115 "
            "L780 75 L800 60 L820 75 L820 150 L870 150 L870 100 L910 100 L910 135 L960 135 L960 45 L975 15 L990 45 "
            "L990 140 L1040 140 L1040 110 L1080 98 L1080 150 L1130 150 L1130 70 L1160 70 L1160 130 L1210 130 "
            "L1210 90 L1240 90 L1240 145 L1290 145 L1290 55 L1310 40 L1330 55 L1330 140 L1380 140 L1380 115 "
            "L1430 115 L1430 85 L1460 85 L1460 150 L1510 150 L1510 120 L1560 120 L1560 160 L1600 160 L1600 220 Z'/>"
            "</svg>")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
:root {
  --cs-gold: #f5b942; --cs-sand: #e8c38a; --cs-turq: #2ec4b6; --cs-coral: #ff7a59; --cs-ink: #f6f0e6;
  --cs-glass: linear-gradient(135deg, rgba(255,255,255,.115), rgba(255,255,255,.04));
  --cs-edge: rgba(255,255,255,.16);
  --cs-shadow: 0 10px 40px rgba(2,4,18,.45), inset 0 1px 0 rgba(255,255,255,.18), inset 0 -1px 0 rgba(255,255,255,.04);
  --cs-blur: blur(16px) saturate(180%);
}
html, body, .stApp, .stMarkdown, p, li, label, h1, h2, h3, h4, h5, h6, button, input, textarea, select,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-baseweb="select"], [data-baseweb="tab"] {
  font-family: 'Outfit', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}
/* ---------- Dubai dusk backdrop with slow "liquid" light ---------- */
.stApp {
  background:
    radial-gradient(1200px 520px at 50% 108%, rgba(245,185,66,.30), transparent 60%),
    radial-gradient(900px 600px at 6% -10%, rgba(46,196,182,.22), transparent 60%),
    radial-gradient(900px 640px at 100% 10%, rgba(140,82,255,.20), transparent 60%),
    linear-gradient(180deg, #060918 0%, #0b1030 42%, #1a1440 72%, #2a1838 100%) !important;
  background-attachment: fixed !important;
}
.stApp::before {
  content: ""; position: fixed; inset: -20%; z-index: 0; pointer-events: none; filter: blur(70px); opacity: .55;
  background:
    radial-gradient(28% 22% at 20% 30%, rgba(255,170,90,.55), transparent 70%),
    radial-gradient(24% 20% at 80% 60%, rgba(46,196,182,.45), transparent 70%),
    radial-gradient(22% 18% at 60% 20%, rgba(255,110,140,.35), transparent 70%);
  animation: cs-liquid 26s ease-in-out infinite alternate;
}
.stApp::after {
  content: ""; position: fixed; left: 0; right: 0; bottom: 0; height: 22vh; z-index: 0; pointer-events: none;
  background: url("__SKYLINE__") bottom / 100% 100% no-repeat; opacity: .55;
  -webkit-mask-image: linear-gradient(transparent, #000 60%); mask-image: linear-gradient(transparent, #000 60%);
}
@keyframes cs-liquid { 0% { transform: translate3d(0,0,0) scale(1); } 50% { transform: translate3d(4%,-3%,0) scale(1.08); }
  100% { transform: translate3d(-3%,4%,0) scale(1.02); } }
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"] > div { background: transparent !important; }
[data-testid="stHeader"] { background: rgba(6,9,24,.35) !important; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1220px; padding-top: 2.6rem; position: relative; z-index: 1; }
/* Streamlit dims "stale" elements during a rerun; reruns here are fast and live, so keep them crisp */
[data-stale="true"], .stale-element { opacity: 1 !important; filter: none !important; transition: none !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: rgba(8,11,32,.55) !important; backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%); border-right: 1px solid rgba(255,255,255,.08); }
[data-testid="stSidebarNav"] a { border-radius: 12px; transition: background .25s, transform .25s; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08); transform: translateX(3px); }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: linear-gradient(90deg, rgba(245,185,66,.22), rgba(245,185,66,.04));
  box-shadow: inset 2px 0 0 var(--cs-gold); }

/* ---------- liquid glass surfaces ---------- */
[class*="st-key-glass"], [data-testid="stForm"], [data-testid="stExpander"] details, .cs-glass {
  position: relative; background: var(--cs-glass) !important; border: 1px solid var(--cs-edge) !important;
  border-radius: 24px !important; backdrop-filter: var(--cs-blur); -webkit-backdrop-filter: var(--cs-blur);
  box-shadow: var(--cs-shadow);
}
[class*="st-key-glass"] { padding: 1.15rem 1.25rem 1.2rem; animation: cs-rise .7s cubic-bezier(.2,.8,.2,1) both; }
[class*="st-key-glass"]::before, .cs-glass::before { content: ""; position: absolute; inset: 0; border-radius: inherit;
  pointer-events: none; background: radial-gradient(120% 70% at 0% 0%, rgba(255,255,255,.14), transparent 46%),
  url("__PATTERN__") top right / 56px 56px; -webkit-mask-image: linear-gradient(135deg, #000 0%, transparent 55%);
  mask-image: linear-gradient(135deg, #000 0%, transparent 55%); }
[data-testid="stForm"] { padding: 1.1rem 1.2rem !important; }
[data-testid="stExpander"] details { border-radius: 18px !important; box-shadow: none; }
[data-testid="stExpander"] summary:hover { color: var(--cs-gold); }
@keyframes cs-rise { from { opacity: 0; transform: translateY(14px) scale(.985); } to { opacity: 1; transform: none; } }

/* metrics as glass chips */
[data-testid="stMetric"] { background: var(--cs-glass); border: 1px solid var(--cs-edge); border-radius: 18px;
  padding: .7rem .9rem; backdrop-filter: var(--cs-blur); -webkit-backdrop-filter: var(--cs-blur);
  transition: transform .3s, box-shadow .3s; }
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(245,185,66,.12); }
[data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -.01em; }

/* inputs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-baseweb="base-input"] {
  background: rgba(255,255,255,.06) !important; border-color: rgba(255,255,255,.14) !important; border-radius: 14px !important;
  transition: border-color .25s, box-shadow .25s, background .25s; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {
  border-color: rgba(245,185,66,.7) !important; box-shadow: 0 0 0 3px rgba(245,185,66,.16), 0 0 24px rgba(245,185,66,.12);
  background: rgba(255,255,255,.09) !important; }
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea { background: transparent !important; }
[data-testid="stNumberInput"] button { background: rgba(255,255,255,.06) !important; border: 0 !important; }
[data-testid="stNumberInput"] button:hover { background: rgba(245,185,66,.25) !important; }
[data-testid="stWidgetLabel"] p { opacity: .82; font-size: .86rem; letter-spacing: .01em; }
[data-baseweb="tab-list"] { gap: .3rem; background: rgba(255,255,255,.05); padding: .3rem; border-radius: 16px; }
[data-baseweb="tab"] { border-radius: 12px !important; padding: .35rem .9rem !important; transition: background .25s; }
[data-baseweb="tab"][aria-selected="true"] { background: rgba(245,185,66,.18) !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stSlider"] [role="slider"] { box-shadow: 0 0 0 6px rgba(245,185,66,.18), 0 0 18px rgba(245,185,66,.55) !important; }

/* buttons: glass pills that glow; primary is liquid gold with a moving sheen */
.stButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button, .stDownloadButton > button {
  border-radius: 999px !important; border: 1px solid rgba(255,255,255,.2) !important;
  background: linear-gradient(135deg, rgba(255,255,255,.14), rgba(255,255,255,.05)) !important;
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); color: var(--cs-ink) !important;
  transition: transform .25s cubic-bezier(.2,.8,.2,1), box-shadow .25s, border-color .25s !important; }
.stButton > button:hover, .stFormSubmitButton > button:hover, [data-testid="stPopover"] button:hover {
  transform: translateY(-2px); border-color: rgba(245,185,66,.6) !important;
  box-shadow: 0 8px 26px rgba(245,185,66,.25), 0 0 0 1px rgba(245,185,66,.25) !important; }
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(0) scale(.98); }
.stButton > button[data-testid="stBaseButton-primary"], .stFormSubmitButton > button[data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  position: relative; overflow: hidden; color: #1a1205 !important; font-weight: 600 !important; border: 0 !important;
  background: linear-gradient(135deg, #ffd88a 0%, #f5b942 45%, #e8913a 100%) !important;
  box-shadow: 0 8px 26px rgba(245,185,66,.35), inset 0 1px 0 rgba(255,255,255,.6) !important; }
[data-testid="stBaseButton-primary"]::after, [data-testid="stBaseButton-primaryFormSubmit"]::after {
  content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%; transform: skewX(-20deg);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.55), transparent); transition: left .7s; }
[data-testid="stBaseButton-primary"]:hover::after, [data-testid="stBaseButton-primaryFormSubmit"]:hover::after { left: 130%; }
.stButton > button[data-testid="stBaseButton-tertiary"], [data-testid="stBaseButton-tertiary"] { background: transparent !important; border: 0 !important; color: var(--cs-sand) !important;
  box-shadow: none !important; text-decoration: underline; text-underline-offset: 4px; }
[class*="st-key-glass_nav"] { min-height: 158px; }
[data-testid="stPageLink"] a { border-radius: 16px; padding: .55rem .8rem; transition: background .25s, transform .25s; }
[data-testid="stPageLink"] a:hover { background: rgba(255,255,255,.08); transform: translateX(3px); }

/* data, alerts, charts */
[data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,.1); }
[data-testid="stAlert"] { border-radius: 16px !important; backdrop-filter: var(--cs-blur); -webkit-backdrop-filter: var(--cs-blur);
  background: rgba(255,255,255,.07) !important; border: 1px solid rgba(255,255,255,.14) !important; }
hr { border-color: rgba(255,255,255,.1) !important; }

/* ---------- CoolScore pieces ---------- */
.cs-hero { position: relative; margin: .2rem 0 1.4rem; animation: cs-rise .8s cubic-bezier(.2,.8,.2,1) both; }
.cs-eyebrow { display: inline-flex; align-items: center; gap: .45rem; font-size: .74rem; letter-spacing: .16em;
  text-transform: uppercase; color: var(--cs-sand); padding: .25rem .7rem; border-radius: 999px;
  background: rgba(245,185,66,.1); border: 1px solid rgba(245,185,66,.28); }
.cs-eyebrow::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cs-gold);
  box-shadow: 0 0 10px var(--cs-gold); animation: cs-pulse 2.2s ease-in-out infinite; }
@keyframes cs-pulse { 0%,100% { opacity: .5; transform: scale(.85); } 50% { opacity: 1; transform: scale(1.15); } }
.cs-title { font-size: clamp(2rem, 4.4vw, 3.4rem); font-weight: 700; line-height: 1.04; letter-spacing: -.02em;
  margin: .55rem 0 .45rem; background: linear-gradient(100deg, #fff6e4 0%, #ffd88a 40%, #f5b942 62%, #ff9d6b 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.cs-sub { font-size: 1.08rem; max-width: 760px; opacity: .84; line-height: 1.5; }
.cs-sim { display: inline-block; font-size: .74rem; padding: .18rem .65rem; border-radius: 999px; margin-top: .7rem;
  background: rgba(46,196,182,.1); border: 1px solid rgba(46,196,182,.35); color: #9ff0e6; }
.cs-badge { display: inline-flex; align-items: center; justify-content: center; border-radius: 14px; font-weight: 700;
  color: #fff; letter-spacing: .02em; box-shadow: 0 6px 20px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.35); }
.cs-muted { opacity: .72; font-size: .9rem; }
.cs-big { font-size: 1.6rem; font-weight: 700; line-height: 1.2; }
.cs-card { border: 1px solid var(--cs-edge); border-radius: 18px; padding: 1rem 1.1rem; margin: .4rem 0 1rem 0;
  background: var(--cs-glass); }
.cs-flag { background: rgba(245,185,66,.1); border: 1px solid rgba(245,185,66,.3); border-left: 3px solid var(--cs-gold);
  padding: .55rem .85rem; border-radius: 14px; }
.cs-h { font-size: 1.15rem; font-weight: 600; margin: 0 0 .5rem; letter-spacing: .01em; }
.cs-h span { display: block; opacity: .6; font-weight: 400; font-size: .84rem; margin-top: .1rem; }
.cs-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: .9rem; margin: 1rem 0; }
.cs-stat { padding: 1rem 1.1rem; border-radius: 20px; background: var(--cs-glass); border: 1px solid var(--cs-edge);
  backdrop-filter: var(--cs-blur); -webkit-backdrop-filter: var(--cs-blur); animation: cs-rise .8s both;
  transition: transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s; }
.cs-stat:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(245,185,66,.14); }
.cs-stat b { display: block; font-size: 1.9rem; font-weight: 700; color: var(--cs-gold); letter-spacing: -.02em; }
.cs-stat span { font-size: .88rem; opacity: .8; }
.cs-steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: .9rem; }
.cs-step { padding: 1rem; border-radius: 20px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1); }
.cs-step i { font-style: normal; font-size: 1.5rem; }
.cs-step b { display: block; margin: .35rem 0 .2rem; }
.cs-step span { font-size: .86rem; opacity: .78; }
.cs-cta { display: inline-flex; align-items: center; gap: .5rem; padding: .7rem 1.25rem; border-radius: 999px;
  font-weight: 600; text-decoration: none !important; margin: .2rem .5rem .2rem 0; transition: transform .25s, box-shadow .25s; }
.cs-cta.gold { color: #1a1205 !important; background: linear-gradient(135deg, #ffd88a, #f5b942 50%, #e8913a);
  box-shadow: 0 10px 30px rgba(245,185,66,.35); }
.cs-cta.glass { color: var(--cs-ink) !important; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.2); }
.cs-cta:hover { transform: translateY(-2px); box-shadow: 0 14px 34px rgba(245,185,66,.35); }
.cs-drvs { display: flex; flex-direction: column; gap: .55rem; margin-top: .3rem; }
.cs-drv { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(90px, 1fr) auto; gap: .7rem; align-items: center;
  animation: cs-rise .6s cubic-bezier(.2,.8,.2,1) both; }
.cs-drv-l { font-size: .86rem; opacity: .88; line-height: 1.25; }
.cs-drv-t { position: relative; height: 10px; border-radius: 99px; background: rgba(255,255,255,.07); }
.cs-drv-t::after { content: ""; position: absolute; left: 50%; top: -4px; bottom: -4px; width: 1px; background: rgba(255,255,255,.35); }
.cs-drv-t i { position: absolute; top: 0; bottom: 0; border-radius: 99px; transform-origin: center;
  animation: cs-grow .9s cubic-bezier(.2,.8,.2,1) both; box-shadow: 0 0 14px rgba(255,255,255,.12); }
.cs-drv b { font-size: .86rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
.cs-drv b.up { color: #ffb08f; } .cs-drv b.down { color: #8ff0e4; }
.cs-drv-key { display: flex; justify-content: space-between; font-size: .72rem; opacity: .6; margin-top: .2rem; }
@keyframes cs-grow { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }
[data-testid="stSidebar"][aria-expanded="true"] { min-width: 236px !important; max-width: 236px !important; }
.cs-livebar { display: none; }
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding-left: 1rem; padding-right: 1rem; padding-bottom: 5.5rem; }
  .cs-big { font-size: 1.3rem; } .cs-stats { grid-template-columns: 1fr; } .cs-steps { grid-template-columns: 1fr 1fr; }
  [class*="st-key-glass"] { padding: .95rem .9rem 1rem; }
}
@media (prefers-reduced-motion: reduce) {
  .stApp::before, .cs-eyebrow::before { animation: none !important; }
  [class*="st-key-glass"], .cs-hero, .cs-stat { animation: none !important; }
}
/* wide screens: keep the live scene in view while the inputs scroll */
@media (min-width: 1101px) {
  [data-testid="stColumn"]:has(.st-key-stage_col) { align-self: stretch; }
  .st-key-stage_col { position: sticky; top: 4.2rem; }
}
/* tablets and small laptops: stack the inputs above the scene, keep the live bar visible */
@media (max-width: 1100px) {
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-stage_col) { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-stage_col) > [data-testid="stColumn"] {
    flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important; }
  [data-testid="stMainBlockContainer"], .block-container { padding-bottom: 5.5rem; }
  .cs-livebar { display: flex; position: fixed; left: 50%; transform: translateX(-50%); width: min(560px, calc(100% - 20px));
    bottom: 10px; z-index: 999; align-items: center; gap: .7rem; padding: .55rem .8rem; border-radius: 20px;
    background: rgba(12,16,40,.62); border: 1px solid rgba(255,255,255,.18); backdrop-filter: blur(18px) saturate(180%);
    -webkit-backdrop-filter: blur(18px) saturate(180%); box-shadow: 0 10px 30px rgba(0,0,0,.45); font-size: .86rem; }
  .cs-livebar .cs-badge { width: 34px; height: 34px; font-size: 19px; flex: none; }
}
</style>
""".replace("__SKYLINE__", _SKYLINE).replace("__PATTERN__", _PATTERN)

_STAGE = components.declare_component("climate_stage", path=str(ROOT / "app" / "components" / "climate_stage"))


def setup(title: str) -> None:
    st.set_page_config(page_title=f"{title} · CoolScore Dubai", page_icon="❄️", layout="wide")
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


def hero(title: str, subtitle: str, eyebrow: str = "CoolScore Dubai", simulated: bool = True) -> None:
    """Page header: pulsing eyebrow, gold gradient title, subtitle and the 'simulated' label."""
    sim = f"<div class='cs-sim'>{SIMULATED}</div>" if simulated else ""
    st.markdown(f"<div class='cs-hero'><span class='cs-eyebrow'>{eyebrow}</span><div class='cs-title'>{title}</div>"
                f"<div class='cs-sub'>{subtitle}</div>{sim}</div>", unsafe_allow_html=True)


@contextmanager
def glass(key: str):
    """A frosted 'liquid glass' panel (styled through its st-key-glass_* class)."""
    with st.container(key=f"glass_{key}"):
        yield


def heading(text: str, note: str = "") -> None:
    st.markdown(f"<div class='cs-h'>{text} {f'<span>{note}</span>' if note else ''}</div>", unsafe_allow_html=True)


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
    """Load the surrogate once per server and run one estimate, so the first real answer is warm."""
    predict.load_artifact()
    predict.estimate({"community": "Business Bay", "size_sqft": 800.0, "bedrooms": 1, "floor": 12,
                      "total_floors": 30, "facing": "W"})
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
        glass_amount = _select("Glass", GLASS_LABELS, d.get("glass", "medium"), f"{prefix}_glass")
    c3, c4 = st.columns(2)
    with c3:
        system = _select("Cooling system", SYSTEM_LABELS, d.get("system", "district_cooling"), f"{prefix}_system")
        balcony = _select("Balcony / shading", BALCONY_LABELS, d.get("balcony", "none"), f"{prefix}_balcony")
    with c4:
        payer = _select("Who pays for cooling", PAYER_LABELS, d.get("payer", "tenant"), f"{prefix}_payer")
        obstruction = _select("View", OBSTRUCTION_LABELS, d.get("obstruction", "partial"), f"{prefix}_obst",
                              help="Neighbouring towers shade the facade and cut solar heat.")
    listing = dict(community=community, era_band=era, size_sqft=float(size), bedrooms=int(beds),
                   floor=int(floor), total_floors=int(total), facing=facing, glass=glass_amount, balcony=balcony,
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


# ---------- the live climate scene ----------

def month_ranges(est) -> list[list[float]]:
    """P10/P50/P90 per month. August and January use the model's own monthly quantiles; other months scale
    the typical monthly shape by the annual range (the same shape the monthly chart shows)."""
    a = est.annual
    lo, hi = (a.p10 / a.p50, a.p90 / a.p50) if a.p50 else (1.0, 1.0)
    out = [[p * lo, p, p * hi] for p in est.monthly_p50]
    out[7] = [est.summer_month.p10, est.summer_month.p50, est.summer_month.p90]
    out[0] = [est.winter_month.p10, est.winter_month.p50, est.winter_month.p90]
    return [[round(v) for v in m] for m in out]


def stage_args(est, listing: dict, month: int, mode: str = "live", message: str | None = None) -> dict:
    """Everything the climate scene needs: the site's typical months of measured weather, the unit, the result."""
    community = listing["community"]
    site = dataset.weather_site_for(community)
    unit = {"facing": str(listing["facing"]).upper().split("+"), "floor": int(listing["floor"]),
            "total_floors": int(max(listing["total_floors"], listing["floor"])),
            "glass": listing.get("glass", "medium"), "balcony": listing.get("balcony", "none"),
            "obstruction": listing.get("obstruction", "partial"), "setpoint": float(listing.get("setpoint_c", 24.0))}
    result = None
    if est is not None:
        rent = listing.get("annual_rent_aed")
        result = {"score": est.score, "colors": SCORE_COLORS, "monthly_p50": [round(x) for x in est.monthly_p50],
                  "month_ranges": month_ranges(est),
                  "annual": [round(est.annual.p10), round(est.annual.p50), round(est.annual.p90)],
                  "true_cost": round(true_monthly_cost(rent, est.annual.p50 / 12)["total"]) if rent else None,
                  "payer_short": PAYER_SHORT[est.listing["payer"]]}
    return {"mode": mode, "month": int(month), "site": site, "community": community,
            "zone": config.communities()["communities"].get(community, "central"),
            "months": climate.load()["sites"][site], "unit": unit, "result": result, "message": message}


def climate_stage(args: dict, key: str) -> None:
    """Render the animated scene. A stable key keeps the iframe alive across reruns, so changes glide."""
    _STAGE(**args, key=key, default=None)


def livebar(est, month: int) -> None:
    """Phone-only floating glass bar: the score and this month's range stay visible while you scroll."""
    if est is None:
        return
    lo, _, hi = month_ranges(est)[month]
    st.markdown(f"<div class='cs-livebar'>{badge(est.score, 34)}<div><b>AED {lo:,}–{hi:,}</b> / month in "
                f"{MONTHS[month]}<br><span class='cs-muted'>{aed_range(est.annual)} a year · simulated</span></div></div>",
                unsafe_allow_html=True)


# ---------- charts (dark glass styling) ----------

def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Outfit, sans-serif", color=INK),
                      hoverlabel=dict(bgcolor="rgba(12,16,40,.92)", bordercolor="rgba(255,255,255,.25)",
                                      font=dict(family="Outfit, sans-serif", color=INK)))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.07)", zerolinecolor="rgba(255,255,255,.25)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.07)", zerolinecolor="rgba(255,255,255,.25)")
    return fig


def _heat_color(tmax: float) -> str:
    """Month bar colour from its measured average high: cool sky blue → sand gold → coral."""
    t = min(max((tmax - 24) / 18, 0), 1)
    stops = [(124, 196, 255), (245, 185, 66), (255, 107, 61)]
    a, b, k = (stops[0], stops[1], t * 2) if t < .5 else (stops[1], stops[2], (t - .5) * 2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(a, b))


def monthly_chart(est, month: int | None = None, community: str | None = None) -> go.Figure:
    ranges = month_ranges(est)
    months = climate.site_months(community or est.listing["community"])
    colors = [_heat_color(m["tmax"]) for m in months]
    opacity = [1.0 if month is None or i == month else .55 for i in range(12)]
    fig = go.Figure(go.Bar(
        x=MONTHS, y=[r[1] for r in ranges], marker=dict(color=colors, opacity=opacity, cornerradius=8,
                                                       line=dict(width=[2 if i == month else 0 for i in range(12)],
                                                                 color="#fff")),
        error_y=dict(type="data", symmetric=False, array=[r[2] - r[1] for r in ranges],
                     arrayminus=[r[1] - r[0] for r in ranges], color="rgba(255,255,255,.45)", thickness=1.2, width=4),
        customdata=[[r[0], r[2], m["tmax"]] for r, m in zip(ranges, months)], width=.62,
        hovertemplate="%{x}: typical AED %{y:,.0f} (AED %{customdata[0]:,.0f}–%{customdata[1]:,.0f})"
                      "<br>average high %{customdata[2]:.1f} °C<extra></extra>"))
    _style(fig, 250)
    fig.update_yaxes(title="AED / month", tickformat=",")
    return fig


def drivers_html(est) -> str | None:
    """Diverging bars (coral adds cost, turquoise saves) that wrap cleanly at any width and grow in on load."""
    drivers = [d for d in est.drivers if abs(d["aed_per_year"]) >= 1][:6]
    if not drivers:
        return None
    top = max(abs(d["aed_per_year"]) for d in drivers)
    rows = []
    for i, d in enumerate(drivers):
        v = d["aed_per_year"]
        w = 50 * abs(v) / top
        side = (f"left:50%;width:{w:.1f}%;background:linear-gradient(90deg,#ff9d6b,{CORAL})" if v > 0 else
                f"left:{50 - w:.1f}%;width:{w:.1f}%;background:linear-gradient(90deg,{TURQ},#7fe3d8)")
        rows.append(f"<div class='cs-drv' style='animation-delay:{i * 70}ms'><div class='cs-drv-l'>{d['driver']}</div>"
                    f"<div class='cs-drv-t'><i style='{side}'></i></div>"
                    f"<b class='{'up' if v > 0 else 'down'}'>{'+' if v > 0 else '−'}AED {abs(v):,.0f}</b></div>")
    return ("<div class='cs-drvs'>" + "".join(rows) + "<div class='cs-drv-key'><span>← saves vs the reference</span>"
            "<span>adds per year →</span></div></div>")


def how_calculated(est, month: int | None = None, rent: float | None = None) -> None:
    """The formula, inputs and range behind every figure on the result."""
    with st.expander("How is this calculated?"):
        st.write(est.formula)
        st.write("Model: gradient-boosted quantile models trained on 40,000 simulated units (hourly building "
                 "physics on 2023–25 Dubai weather + published tariffs). Inputs used: "
                 f"{'listing facts + your household details' if est.variant == 'detailed' else 'listing facts only'}.")
        if month is not None:
            st.write("Monthly figures: August and January are the model's own monthly P10–P90; other months scale the "
                     "typical monthly shape by the annual range. The scene plays a typical day of measured weather "
                     "for that month (2023–25 hourly data corrected to Dubai airport observations); 'sun on your "
                     "windows' is pvlib facade sun on your facing, before balcony shade.")
        if est.listing["system"] == "district_cooling":
            payer = {"tenant": "you pay it", "landlord_chiller_free": "the landlord pays it (chiller-free)",
                     "service_charge": "the owner pays it through the service charge"}[est.listing["payer"]]
            st.write(f"Contracted capacity estimate ≈ {est.contracted_rt_estimate:.1f} RT (from size; real "
                     f"allocations vary) → fixed capacity charge ≈ {aed(est.capacity_aed_per_year)} a year incl. "
                     f"VAT, payable even with the AC off; {payer}.")
        st.write(f"CoolScore uses a standard household (bedrooms + 1 people, out by day, 24 °C) and a "
                 f"standard district-cooling tariff so units compare fairly: "
                 f"{est.intensity_aed_per_sqft:.2f} AED per sq ft per year. Grade cut-offs (AED/sq ft/yr): "
                 + ", ".join(f"{l} ≤ {c:.2f}" for l, c in zip("ABCD", est.score_cuts)) + ", E above.")
        if rent:
            tc = true_monthly_cost(rent, est.annual.p50 / 12)
            st.write(f"True monthly cost = rent {aed(tc['rent'])} + cooling {aed(tc['cooling'])} (typical, yearly "
                     f"average) + housing fee {aed(tc['housing_fee'])} (5% of rent, collected on the DEWA bill).")
    for note in est.notes:
        st.caption(note)


def shifted(card, alt, base):
    """Apply a what-if change (alt − base, same model) to the card's own range, so the two never disagree."""
    from coolscore.model.predict import Range

    return Range(*(max(getattr(card, q) + getattr(alt, q) - getattr(base, q), 0.0) for q in ("p10", "p50", "p90")))


def footer() -> None:
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    st.divider()
    st.caption(f"{DISCLAIMER} {SIMULATED} Weather data by Open-Meteo.com (CC BY 4.0); observations NOAA NCEI. "
               "Fictional building names only; no real portal or developer is depicted.")
