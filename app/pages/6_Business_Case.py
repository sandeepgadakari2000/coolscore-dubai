"""Business Case: pricing, unit economics and a 12-month P&L you can change."""

import plotly.graph_objects as go
import ui
import streamlit as st

from coolscore import business

ui.setup("Business Case")
st.title("Business case")
st.caption("Every default is a labelled **assumption** (our proposed prices and plan) from `config/assumptions.yaml`, "
           "not market data. Change anything.")

b = business.BusinessInputs.defaults()
with st.sidebar:
    st.header("Prices (AED)")
    b.pricing["broker_seat_aed_month"] = st.number_input("Broker seat / month", 0, 2000, int(b.pricing["broker_seat_aed_month"]), 10)
    b.pricing["portal_aed_per_scored_listing_month"] = st.number_input(
        "Portal: per scored listing / month", 0.0, 20.0, float(b.pricing["portal_aed_per_scored_listing_month"]), 0.25)
    b.pricing["developer_report_aed"] = st.number_input("Developer design report", 0, 500_000, int(b.pricing["developer_report_aed"]), 1000)
    b.pricing["consumer_report_aed"] = st.number_input("Consumer detailed report", 0, 500, int(b.pricing["consumer_report_aed"]), 1)
    b.pricing["pilot_fee_aed"] = st.number_input("90-day brokerage pilot fee", 0, 200_000, int(b.pricing["pilot_fee_aed"]), 1000)
    st.header("Plan")
    b.plan["brokerages_month_4"] = st.slider("Paying brokerages in month 4", 0, 10, int(b.plan["brokerages_month_4"]))
    b.plan["new_brokerages_per_month"] = st.slider("New brokerages per month", 0, 5, int(b.plan["new_brokerages_per_month"]))
    b.plan["seats_per_brokerage"] = st.slider("Seats per brokerage", 1, 60, int(b.plan["seats_per_brokerage"]))
    b.plan["portal_start_month"] = st.slider("Portal deal starts (month; 13 = none)", 4, 13, int(b.plan["portal_start_month"]))
    b.plan["portal_scored_listings"] = st.number_input("Portal listings scored", 0, 500_000, int(b.plan["portal_scored_listings"]), 1000)
    b.plan["monthly_churn"] = st.slider("Monthly seat churn", 0.0, 0.2, float(b.plan["monthly_churn"]), 0.01)

df = business.pnl(b)
be = business.break_even_month(df)
ue = business.unit_economics(b)
m1, m2, m3 = st.columns(3)
m1.metric("12-month revenue", ui.aed(df["revenue"].sum()))
m2.metric("12-month profit", ui.aed(df["profit"].sum()))
m3.metric("Break-even month", f"Month {be}" if be else "Not within 12 months")

fig = go.Figure()
for col, color, name in [("broker_seats", "#2a78d6", "Broker seats"), ("portal_api", "#eb6834", "Portal API"),
                         ("developer_reports", "#1baf7a", "Developer reports"), ("pilot", "#eda100", "Pilot"),
                         ("consumer_reports", "#e87ba4", "Consumer reports")]:
    fig.add_trace(go.Bar(x=df["month"], y=df[col], name=name, marker_color=color,
                         hovertemplate=name + ": AED %{y:,.0f}<extra></extra>"))
fig.add_trace(go.Scatter(x=df["month"], y=df["costs"], name="Costs", mode="lines+markers",
                         line=dict(color="#0b0b0b", width=2), hovertemplate="Costs: AED %{y:,.0f}<extra></extra>"))
fig.update_layout(barmode="stack", height=360, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Month",
                  yaxis_title="AED per month", legend=dict(orientation="h", y=-0.25),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
fig.update_xaxes(dtick=1)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.subheader("Unit economics")
c1, c2 = st.columns(2)
c1.markdown(f"**Broker seat:** {ui.aed(ue['broker_seat_price'])}/month; cost to serve ≈ "
            f"AED {ue['broker_seat_cost']:,.2f} → gross margin {ue['broker_seat_margin']:.0%}.")
c2.markdown(f"**Scored listing (portal):** AED {ue['listing_price']:.2f}/month; AI parsing ≈ "
            f"AED {ue['llm_cost_per_listing_aed']:.3f} → gross margin {ue['listing_margin']:.0%}.")
st.caption("Scoring itself is near-free (a model lookup); the main variable cost is optional AI listing parsing. "
           "The real costs are people, sales time and bill-data collection.")

with st.expander("12-month P&L table"):
    show = df[["month", "revenue", "costs", "profit", "cumulative", "seats"]].copy()
    for col in ["revenue", "costs", "profit", "cumulative"]:
        show[col] = show[col].map(lambda v: f"AED {v:,.0f}")
    show["seats"] = show["seats"].round(0).astype(int)
    st.dataframe(show, hide_index=True, width="stretch")
with st.expander("How is this calculated?"):
    st.write("Revenue = pilot fee (month 1) + broker seats × price (from month 4, with churn) + scored portal "
             "listings × price (from the portal start month) + developer reports (quarterly) + consumer reports. "
             "Costs = AI parsing per listing (Claude Haiku 4.5 list price × tokens) + fixed monthly costs + part-time "
             "sales from month 4. Founder time is unpaid in year 1. Recommendation and reasoning: docs/business_model.md.")
ui.footer()
