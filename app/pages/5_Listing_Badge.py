"""Listing Badge Demo: how a CoolScore badge could look on a (generic, unbranded) property listing."""

import ui
import streamlit as st

ui.setup("Listing Badge")
ui.hero("Listing badge", "How a CoolScore badge could sit on a property listing. A generic card with a fictional "
        "building: no real portal, developer or tower is shown.", eyebrow="For portals and brokers")
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
# An illustrated "photo" (fictional skyline at dusk) instead of a real listing photo.
PHOTO = """<svg viewBox="0 0 420 170" width="100%" height="170" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs><linearGradient id="bsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d2252"/>
  <stop offset=".55" stop-color="#7b3f72"/><stop offset="1" stop-color="#ff9455"/></linearGradient>
  <linearGradient id="bsea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3f7a"/>
  <stop offset="1" stop-color="#0c1230"/></linearGradient>
  <radialGradient id="bsun"><stop offset="0" stop-color="#fff3c4"/><stop offset=".4" stop-color="#ffb347" stop-opacity=".7"/>
  <stop offset="1" stop-color="#ff8a3d" stop-opacity="0"/></radialGradient></defs>
  <rect width="420" height="170" fill="url(#bsky)"/><circle cx="96" cy="118" r="60" fill="url(#bsun)"/>
  <circle cx="96" cy="118" r="14" fill="#fff4d6"/>
  <g fill="#1a1a3a"><rect x="10" y="70" width="26" height="70"/><rect x="40" y="88" width="20" height="52"/>
  <rect x="150" y="54" width="24" height="86"/><polygon points="150,54 162,36 174,54"/><rect x="180" y="80" width="30" height="60"/>
  <rect x="246" y="62" width="22" height="78"/><rect x="300" y="74" width="34" height="66"/><rect x="342" y="92" width="22" height="48"/>
  <rect x="372" y="60" width="26" height="80"/><rect x="384" y="44" width="3" height="16"/></g>
  <rect x="214" y="22" width="30" height="118" fill="#2a3360" stroke="rgba(255,255,255,.35)"/>
  <rect x="214" y="70" width="30" height="5" fill="#ffc35a"/><rect x="0" y="140" width="420" height="30" fill="url(#bsea)"/>
  <g stroke="rgba(255,255,255,.3)" stroke-dasharray="10 22"><path d="M0 150 H420"/><path d="M0 160 H420"/></g></svg>"""

card = f"""
<div class='cs-card cs-glass' style='max-width:440px;padding:0;overflow:hidden;margin:0'>
  <div style='position:relative'>{PHOTO}
    <span style='position:absolute;left:.6rem;bottom:.6rem;background:rgba(12,16,36,.6);border:1px solid rgba(255,255,255,.3);
      border-radius:999px;padding:.15rem .6rem;font-size:.75rem'>Illustration · fictional building</span></div>
  <div style='padding:.95rem 1.05rem 1.05rem'>
    <div style='font-size:1.35rem;font-weight:700'>AED {rent:,.0f} <span style='font-size:.85rem;
         font-weight:400;opacity:.7'>/ year</span></div>
    <div style='opacity:.82'>{beds} · {listing['size_sqft']:,.0f} sq ft · Floor {listing['floor']}</div>
    <div style='opacity:.82;margin-bottom:.7rem'>Seabreeze Residences (fictional), {listing['community']}</div>
    <details title="{tooltip}" style='border:1px solid rgba(255,255,255,.22);border-radius:14px;padding:.5rem .65rem;
      background:rgba(255,255,255,.06)'>
      <summary style='display:flex;align-items:center;gap:.65rem;cursor:pointer;list-style:none'>
        {ui.badge(est.score, 38)}
        <div style='line-height:1.25'><b>CoolScore {est.score}</b> · Est. cooling AED {low:,.0f}–{high:,.0f}/month
          <div style='font-size:.75rem;opacity:.7'>summer · simulated estimate · tap for details</div></div>
      </summary>
      <div style='font-size:.82rem;opacity:.85;margin-top:.55rem'>{tooltip}</div>
    </details>
  </div>
</div>
"""
c1, c2 = st.columns([1, 1.15], gap="large")
with c1:
    st.markdown(card, unsafe_allow_html=True)
with c2:
    with ui.glass("badge_why"):
        ui.heading("Why a portal might show it")
        st.markdown("It answers the most common unasked question (\"what will the AC cost?\"), lets buyers filter by "
                    "true cost, and gives good units a reason to stand out. Low-scoring units get a concrete fix "
                    "(blinds, film, AC temperature) instead of a vague reputation.")
        ui.heading("Rules for a fair badge")
        st.markdown("Show the range, not a single number · label it as simulated · let owners add real bills to "
                    "calibrate it · score every listing, not only the good ones.")
        with st.expander("How is this calculated?"):
            st.write(f"The badge shows the summer-month P10–P90 range (AED {low:,.0f}–{high:,.0f}) for the unit: "
                     f"{listing['size_sqft']:,.0f} sq ft, floor {listing['floor']} of {listing['total_floors']}, "
                     f"{listing['facing']}-facing. {est.formula}")
            st.write(f"CoolScore {est.score} = {est.intensity_aed_per_sqft:.2f} AED per sq ft per year under a standard "
                     "household and tariff; cut-offs " + ", ".join(f"{l} ≤ {c:.2f}" for l, c in zip("ABCD", est.score_cuts))
                     + ", E above.")
ui.footer()
