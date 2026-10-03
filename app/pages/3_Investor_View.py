"""Investor View: net yield after cooling and service charges; pricing a chiller-free offer."""

import ui
import streamlit as st

ui.setup("Investor View")
st.title("Investor view")
st.caption("Yield after the costs a listing doesn't show. Cooling figures are simulated estimates.")
ui.model_ready()

with st.form("inv"):
    listing = ui.listing_form("inv", dict(payer="landlord_chiller_free", annual_rent_aed=95000), optional=False,
                              compact=True)
    c1, c2 = st.columns(2)
    with c1:
        price = st.number_input("Purchase price (AED)", 100_000, 50_000_000, 1_400_000, 10_000)
        rent = st.number_input("Annual rent (AED)", 0, 2_000_000, 95_000, 1_000)
    with c2:
        sc_rate = st.number_input("Service charge (AED per sq ft per year)", 0.0, 100.0, 0.0, 0.5,
                                  help="Use the building's figure from its service-charge statement. "
                                       "We don't assume one.")
        other = st.number_input("Other yearly costs (AED: maintenance, management, insurance)", 0, 500_000, 0, 500)
    go = st.form_submit_button("Calculate", type="primary")

if go:
    est = ui.run_estimate(listing)
    tenant_pays = ui.run_estimate({**listing, "payer": "tenant"})
    free = ui.run_estimate({**listing, "payer": "landlord_chiller_free"})
    landlord_cooling = free.landlord_annual
    service = sc_rate * listing["size_sqft"]
    gross = rent / price
    base_costs = service + other
    net_tenant_pays = (rent - base_costs) / price
    net_free_p50 = (rent - base_costs - landlord_cooling.p50) / price
    net_free_p90 = (rent - base_costs - landlord_cooling.p90) / price

    if sc_rate == 0:
        st.markdown("<div class='cs-flag'>Service charge is 0 — enter the building's figure for a real net "
                    "yield.</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Gross yield", f"{gross:.2%}")
    m2.metric("Net yield, tenant pays cooling", f"{net_tenant_pays:.2%}")
    m3.metric("Net yield, chiller-free", f"{net_free_p50:.2%}", f"{(net_free_p50 - net_tenant_pays):+.2%} pts",
              help=f"Worst case (P90 cooling): {net_free_p90:.2%}")

    if listing["payer"] == "service_charge" and listing["system"] not in ("dewa_split_ac", "dewa_central_ac"):
        st.info(f"Cooling here is recovered through service charges, so it is an owner cost like chiller-free: "
                f"about {ui.aed(landlord_cooling.p50)} a year (simulated). Enter the service charge *excluding* "
                "cooling above, or this is counted twice.")

    st.subheader("Pricing a chiller-free offer")
    if listing["system"] in ("dewa_split_ac", "dewa_central_ac"):
        st.info("This unit's AC runs on the tenant's DEWA meter, so a chiller-free offer doesn't apply.")
    else:
        st.markdown(
            f"If you offer this unit chiller-free you take on about **{ui.aed(landlord_cooling.p50)} a year** of "
            f"cooling (range {ui.aed(landlord_cooling.p10)}–{ui.aed(landlord_cooling.p90)}). To break even, "
            f"the chiller-free rent must be at least **{ui.aed(landlord_cooling.p50)} a year higher** "
            f"({landlord_cooling.p50 / max(rent, 1):.1%} of the current rent); "
            f"{ui.aed(landlord_cooling.p90)} covers a hot-unit / heavy-use tenant."
        )
        st.caption(f"For comparison, a tenant paying cooling themselves would face about "
                   f"{ui.aed_range(tenant_pays.annual)} a year (incl. fan electricity).")
    with st.expander("How is this calculated?"):
        st.write(
            f"Gross yield = rent ÷ price. Net yield = (rent − service charge − other costs − landlord cooling) "
            f"÷ price. Service charge = {sc_rate:g} AED/sq ft × {listing['size_sqft']:,.0f} sq ft = {ui.aed(service)}. "
            "Landlord cooling = simulated cooling bill when the tenant pays it, minus the fan electricity the "
            "tenant still pays when chiller-free (difference of P10/P50/P90 estimates, approximate). "
            "Vacancy, financing, fees and taxes are not included."
        )
        st.write(est.formula)
ui.footer()
