"""CoolScore Dubai: Streamlit entry point. Run: ``python tasks.py app``."""

import ui
import streamlit as st

ui.setup("Home")

st.title("CoolScore Dubai")
st.markdown("#### Know what a Dubai apartment will cost to cool *before* you rent or buy it.")
st.markdown(
    "Existing tools are appliance calculators that work after you move in. **CoolScore predicts a specific "
    "unit's cooling cost before you sign**, using building physics and Dubai's cooling tariffs."
)
st.markdown(f"<span class='cs-sim'>{ui.SIMULATED}</span>", unsafe_allow_html=True)

st.write("")
c1, c2 = st.columns(2)
with c1:
    st.page_link("pages/1_Check_a_Unit.py", label="Check a unit", icon="🔎")
    st.caption("Paste a listing or fill a form: CoolScore A–E, monthly and annual AED range, true monthly cost.")
    st.page_link("pages/2_Compare_Units.py", label="Compare units", icon="⚖️")
    st.caption("2–4 units side by side. Spot when the cheaper rent is the more expensive home.")
    st.page_link("pages/3_Investor_View.py", label="Investor view", icon="📈")
    st.caption("Net yield after cooling and service charges; what a chiller-free offer really costs.")
with c2:
    st.page_link("pages/4_Developer_View.py", label="Developer view", icon="🏢")
    st.caption("Facade heatmap of a fictional tower and the AED impact of glass, glazing and shading.")
    st.page_link("pages/5_Listing_Badge.py", label="Listing badge demo", icon="🏷️")
    st.caption("How a CoolScore badge could look on a property listing.")
    st.page_link("pages/6_Business_Case.py", label="Business case", icon="💼")
    st.caption("Pricing, unit economics and a 12-month P&L you can change.")
st.page_link("pages/7_Methodology.py", label="Methodology & validation", icon="📐")
st.caption("Physics, data, model accuracy, real-bill validation status, assumptions and limitations.")

st.subheader("How it works")
st.markdown(
    "1. **Building physics.** An hourly heat-balance model (ISO 13790) of one apartment under real 2023–25 "
    "Dubai weather, with facing, floor, glass, shading, building era, household and humidity.\n"
    "2. **Dubai billing.** District cooling capacity + consumption charges, DEWA slabs, chiller-free and "
    "service-charge cases, VAT, from published tariffs.\n"
    "3. **Fast surrogate.** 40,000 simulated units train quantile models that answer in under a second with a "
    "likely range (P10–P90), not a single 'exact' number.\n"
    "4. **Real bills next.** As anonymised bills arrive, a validation report measures real-world accuracy."
)
ui.footer()
ui.model_ready()  # warm the model while the visitor reads, so "Check a unit" answers fast
