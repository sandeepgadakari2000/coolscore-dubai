"""CoolScore Dubai: Streamlit entry point. Run: ``python tasks.py app``."""

import ui
import streamlit as st

from coolscore.weather import climate

ui.setup("Home")
ui.model_ready()

# A sample flat for the self-playing scene (fictional; the same unit the README quotes).
DEMO = {"community": "Business Bay", "era_band": "2005_2014", "size_sqft": 800.0, "bedrooms": 1, "floor": 15,
        "total_floors": 30, "facing": "W", "glass": "high", "balcony": "none", "obstruction": "partial",
        "system": "district_cooling", "payer": "tenant", "annual_rent_aed": 90000.0}
demo = ui.run_estimate(DEMO)
aug = climate.site_months("Business Bay")[7]
west = aug["hourly"]["facade"]["W"]
peak_hour = max(range(24), key=lambda h: west[h])
capacity_share = demo.capacity_aed_per_year / demo.annual.p50

hero, scene = st.columns([1, 1.25], gap="large", vertical_alignment="center")
with hero:
    ui.hero("Know what a Dubai flat costs to cool — before you sign.",
            "Existing tools are appliance calculators that work after you move in. <b>CoolScore predicts a "
            "specific unit's cooling cost before you sign</b>, using building physics, a year of measured Dubai "
            "weather and the city's cooling tariffs.", eyebrow="Dubai · cooling cost, unit by unit")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("✨ See a worked example", type="primary", width="stretch"):
            st.session_state["example_pending"] = True
            st.switch_page("pages/1_Check_a_Unit.py")
    with b2:
        st.page_link("pages/1_Check_a_Unit.py", label="Check your own unit →", width="stretch")
with scene:
    ui.climate_stage(ui.stage_args(demo, DEMO, month=7, mode="tour"), key="home_tour")
    st.caption("A year of Dubai weather, one typical day per month (measured 2023–25), on a west-facing 1-bed on "
               "floor 15 of 30 in Business Bay (fictional tower). Watch the afternoon sun reach the windows.")

st.markdown(
    "<div class='cs-stats'>"
    f"<div class='cs-stat'><b>{aug['tmax']:.1f} °C</b><span>average August afternoon high in central Dubai "
    f"(2023–25, corrected to airport observations)</span></div>"
    f"<div class='cs-stat'><b>{max(west):,.0f} W/m²</b><span>of sun on a west-facing facade at {peak_hour}:00 in "
    f"August, just as it hits 40 °C outside</span></div>"
    f"<div class='cs-stat'><b>~{capacity_share:.0%}</b><span>of this sample flat's district-cooling bill is a "
    f"fixed capacity charge, payable even with the AC off (simulated)</span></div>"
    "</div>", unsafe_allow_html=True)

st.write("")
ui.heading("Explore", "seven views, one model")
PAGES = [
    ("pages/1_Check_a_Unit.py", "Check a unit", "🔎", "Paste a listing or set the details: CoolScore A–E, monthly and "
     "annual AED range, true monthly cost — live, with the Dubai sky on your windows."),
    ("pages/2_Compare_Units.py", "Compare units", "⚖️", "2–4 units side by side. Spot when the cheaper rent is the "
     "more expensive home."),
    ("pages/3_Investor_View.py", "Investor view", "📈", "Net yield after cooling and service charges, and what a "
     "chiller-free offer really costs."),
    ("pages/4_Developer_View.py", "Developer view", "🏢", "Facade heatmap of a fictional tower and the AED impact of "
     "glass, glazing and shading."),
    ("pages/5_Listing_Badge.py", "Listing badge", "🏷️", "How a CoolScore badge could look on a property listing."),
    ("pages/6_Business_Case.py", "Business case", "💼", "Pricing, unit economics and a 12-month P&L you can change."),
    ("pages/7_Methodology.py", "Methodology & validation", "📐", "Physics, data, model accuracy, real-bill status, "
     "assumptions and limitations."),
]
for row in range(0, len(PAGES), 3):
    cols = st.columns(3, gap="medium")
    for col, (page, label, icon, text) in zip(cols, PAGES[row:row + 3]):
        with col:
            with ui.glass(f"nav_{row}_{label.split()[0].lower()}"):
                st.page_link(page, label=f"**{label}**", icon=icon)
                st.caption(text)

st.write("")
with ui.glass("how"):
    ui.heading("How it works", "physics first, then machine learning, then real bills")
    st.markdown(
        "<div class='cs-steps'>"
        "<div class='cs-step'><i>☀️</i><b>Measured weather</b><span>Hourly 2023–25 Dubai weather, corrected to "
        "airport observations; sun on 8 facade directions.</span></div>"
        "<div class='cs-step'><i>🏢</i><b>Building physics</b><span>An hourly ISO 13790 heat balance of one flat: "
        "facing, floor, glass, shade, era, humidity, household.</span></div>"
        "<div class='cs-step'><i>🧾</i><b>Dubai billing</b><span>District-cooling capacity + consumption, DEWA "
        "slabs, chiller-free and service-charge cases, VAT.</span></div>"
        "<div class='cs-step'><i>⚡</i><b>Instant ranges</b><span>40,000 simulated flats train quantile models "
        "that answer in under a second with P10–P90.</span></div>"
        "</div>", unsafe_allow_html=True)
ui.footer()
