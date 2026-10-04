"""Business Case: pricing, unit economics and a 12-month P&L you can change."""

import plotly.graph_objects as go
import ui
import streamlit as st

from coolscore import business

ui.setup("Business Case")
ui.hero("Business case", "Every default is a labelled <b>assumption</b> (our proposed prices and plan) from "
        "<code>config/assumptions.yaml</code>, not market data. Change prices, plan and costs in the sidebar (tap "
        "<b>›</b> at the top left on a phone).", eyebrow="Pricing · unit economics · P&L", simulated=False)

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
    b.plan["developer_reports_per_quarter"] = st.slider("Developer reports closed per quarter", 0, 4,
                                                        int(b.plan["developer_reports_per_quarter"]))
    st.header("Costs (AED / month)")
    b.costs["part_time_sales_aed"] = st.number_input("Part-time sales (from month 4)", 0, 100_000,
                                                     int(b.costs["part_time_sales_aed"]), 500)
    b.costs["marketing_aed"] = st.number_input("Marketing", 0, 100_000, int(b.costs["marketing_aed"]), 500)
    b.costs["founder_draw_aed"] = st.number_input("Founder salary", 0, 100_000, int(b.costs["founder_draw_aed"]), 1000)

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
                         line=dict(color="#8a8a8a", width=2.5), marker=dict(color="#8a8a8a"), hovertemplate="Costs: AED %{y:,.0f}<extra></extra>"))
fig.update_layout(barmode="stack", height=380, margin=dict(l=10, r=10, t=40, b=10), xaxis_title="Month",
                  yaxis_title="AED per month", legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom"),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
fig.update_xaxes(dtick=1)
fig.update_yaxes(tickformat=",", gridcolor="rgba(128,128,128,.2)")
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
             "sales from month 4 + founder salary (0 by default: unpaid in year 1). Recommendation and reasoning: docs/business_model.md.")
ui.footer()
