"""Compare Units: 2-4 units side by side by true monthly cost."""

import pandas as pd
import plotly.graph_objects as go
import ui
import streamlit as st

from coolscore.billing.engine import true_monthly_cost

ui.setup("Compare Units")
st.title("Compare units")
st.caption("Rent is only part of the cost. Compare what each home really costs per month.")
ui.model_ready()

n = st.segmented_control("Units to compare", [2, 3, 4], default=2)
presets = [
    dict(community="Business Bay", facing="W", floor=8, total_floors=30, glass="floor_to_ceiling",
         payer="tenant", annual_rent_aed=92000),
    dict(community="Business Bay", facing="N", floor=20, total_floors=30, glass="medium",
         payer="landlord_chiller_free", annual_rent_aed=96000),
    dict(community="Jumeirah Village Circle (JVC)", facing="E", floor=5, total_floors=12, era_band="2015_2021",
         annual_rent_aed=78000),
    dict(community="Dubai Marina", facing="S+W", floor=31, total_floors=31, annual_rent_aed=110000),
]
listings = []
tabs = st.tabs([f"Unit {i + 1}" for i in range(n or 2)])
for i, tab in enumerate(tabs):
    with tab:
        listing = ui.listing_form(f"cmp{i}", presets[i], optional=False)
        listings.append(listing)

if st.button("Compare", type="primary"):
    rows, ests = [], []
    for i, listing in enumerate(listings):
        try:
            est = ui.run_estimate(listing)
        except ValueError as exc:
            st.error(f"Unit {i + 1}: {exc}")
            st.stop()
        rent = listing.get("annual_rent_aed") or 0.0
        tc = true_monthly_cost(rent, est.annual.p50 / 12)
        ests.append(est)
        rows.append({"Unit": f"Unit {i + 1}", "CoolScore": est.score, "Rent / month": tc["rent"],
                     "Cooling / month (typical)": tc["cooling"], "Housing fee / month": tc["housing_fee"],
                     "True cost / month": tc["total"],
                     "Cooling range / year": ui.aed_range(est.annual)})
    df = pd.DataFrame(rows)
    if all(listing.get("annual_rent_aed") for listing in listings):
        cheapest_rent = df["Rent / month"].idxmin()
        cheapest_true = df["True cost / month"].idxmin()
        if cheapest_rent != cheapest_true:
            gap = df.loc[cheapest_rent, "True cost / month"] - df.loc[cheapest_true, "True cost / month"]
            st.warning(f"**{df.loc[cheapest_rent, 'Unit']} has the cheapest rent but is not the cheapest home.** "
                       f"{df.loc[cheapest_true, 'Unit']} costs about {ui.aed(gap)} less per month once cooling "
                       "and the housing fee are added (typical estimates).")
        else:
            st.success(f"{df.loc[cheapest_rent, 'Unit']} has both the cheapest rent and the lowest true cost.")
    else:
        st.info("Add the annual rent for every unit to compare true monthly costs.")

    fig = go.Figure()
    for col, color in [("Rent / month", "#2a78d6"), ("Cooling / month (typical)", "#eb6834"),
                       ("Housing fee / month", "#1baf7a")]:
        fig.add_trace(go.Bar(y=df["Unit"], x=df[col], name=col.replace(" / month", ""), orientation="h",
                             marker_color=color, width=0.5, hovertemplate="%{y}: AED %{x:,.0f}<extra></extra>"))
    fig.update_layout(barmode="stack", height=120 + 60 * len(df), margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", traceorder="normal"),
                      xaxis_title="AED per month", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickformat=",")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    show = df.copy()
    for c in ["Rent / month", "Cooling / month (typical)", "Housing fee / month", "True cost / month"]:
        show[c] = show[c].map(lambda v: f"AED {v:,.0f}")
    st.dataframe(show, hide_index=True, width="stretch")
    with st.expander("How is this calculated?"):
        st.write("True cost per month = annual rent ÷ 12 + typical (P50) simulated cooling ÷ 12 + Dubai "
                 "Municipality housing fee (5% of rent ÷ 12). Cooling ranges are P10–P90. Other electricity, "
                 "water and service charges are not included.")
        for i, est in enumerate(ests):
            st.caption(f"Unit {i + 1}: {est.formula}")
ui.footer()
