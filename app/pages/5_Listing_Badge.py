"""Listing Badge Demo: how a CoolScore badge could look on a (generic, unbranded) property listing."""

import ui
import streamlit as st

ui.setup("Listing Badge")
st.title("Listing badge demo")
st.caption("A generic listing card with a fictional building. No real portal, developer or tower is shown.")
ui.model_ready()

with st.expander("Change the demo unit"):
    listing = ui.listing_form("badge", dict(community="Dubai Marina", facing="W", floor=18, total_floors=42,
                                            glass="floor_to_ceiling", bedrooms=1, size_sqft=780,
                                            annual_rent_aed=105000), optional=False)
est = ui.run_estimate(listing)
rent = listing.get("annual_rent_aed") or 0
beds = "Studio" if listing["bedrooms"] == 0 else f"{listing['bedrooms']} bed"
low, high = est.summer_month.p10, est.summer_month.p90
tooltip = (f"Simulated estimate from building physics and published tariffs, not a quote. Summer month: "
           f"AED {low:,.0f}–{high:,.0f}; year: AED {est.annual.p10:,.0f}–{est.annual.p90:,.0f}. "
           f"CoolScore compares cooling cost per sq ft under standard conditions (A best, E worst).")
card = f"""
<div class='cs-card' style='max-width:420px;padding:0;overflow:hidden'>
  <div style='height:170px;background:linear-gradient(135deg,#9ec5f4,#e1e0d9 60%,#f0efec);
       display:flex;align-items:flex-end;padding:.6rem'>
    <span style='background:rgba(255,255,255,.9);color:#0b0b0b;border-radius:8px;padding:.15rem .5rem;
          font-size:.8rem'>Photo placeholder</span>
  </div>
  <div style='padding:.9rem 1rem'>
    <div style='font-size:1.25rem;font-weight:700'>AED {rent:,.0f} <span style='font-size:.85rem;
         font-weight:400;opacity:.7'>/ year</span></div>
    <div style='opacity:.8'>{beds} · {listing['size_sqft']:,.0f} sq ft · Floor {listing['floor']}</div>
    <div style='opacity:.8;margin-bottom:.6rem'>Seabreeze Residences (fictional), {listing['community']}</div>
    <details title="{tooltip}" style='border:1px solid rgba(128,128,128,.3);border-radius:10px;padding:.45rem .6rem'>
      <summary style='display:flex;align-items:center;gap:.6rem;cursor:pointer;list-style:none'>
        {ui.badge(est.score, 36)}
        <div style='line-height:1.25'><b>CoolScore {est.score}</b> · Est. cooling AED {low:,.0f}–{high:,.0f}/month
          <div style='font-size:.75rem;opacity:.7'>summer · simulated estimate · tap for details</div></div>
      </summary>
      <div style='font-size:.8rem;opacity:.85;margin-top:.5rem'>{tooltip}</div>
    </details>
  </div>
</div>
"""
st.markdown(card, unsafe_allow_html=True)
with st.expander("How is this calculated?"):
    st.write(f"The badge shows the summer-month P10–P90 range (AED {low:,.0f}–{high:,.0f}) for the unit above: "
             f"{listing['size_sqft']:,.0f} sq ft, floor {listing['floor']} of {listing['total_floors']}, "
             f"{listing['facing']}-facing. {est.formula}")
    st.write(f"CoolScore {est.score} = {est.intensity_aed_per_sqft:.2f} AED per sq ft per year under a standard "
             "household and tariff; cut-offs " + ", ".join(f"{l} ≤ {c:.2f}" for l, c in zip("ABCD", est.score_cuts))
             + ", E above.")
st.markdown("**Why a portal might show it:** it answers the most common unasked question (\"what will the AC "
            "cost?\"), lets buyers filter by true cost, and gives good units a reason to stand out. Low-scoring units "
            "get a concrete fix (blinds, film, AC temperature) instead of a vague reputation.")
st.markdown("**Rules for a fair badge:** show the range, not a single number; label it as simulated; let owners "
            "add real bills to calibrate it; and score every listing, not only the good ones.")
ui.footer()
