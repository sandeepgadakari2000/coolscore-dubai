"""Developer View: facade heatmap of a fictional tower and the AED impact of design levers."""

import plotly.graph_objects as go
import ui
import streamlit as st

from coolscore.developer import TowerDesign, compare, simulate_tower
from coolscore.physics.params import ORIENTATIONS

ui.setup("Developer View")
st.title("Developer view")
st.caption("**Meridian Heights** — a fictional 1-bedroom tower. Every cell is one simulated unit "
           "(typical household, reference district-cooling tariff). Runs the physics engine directly.")
ui.model_ready()


@st.cache_data(show_spinner=False, max_entries=24)
def run(design: TowerDesign):
    return simulate_tower(design)


with st.sidebar:
    st.header("Tower")
    community = st.selectbox("Community", sorted(ui.config.communities()["communities"]),
                             index=sorted(ui.config.communities()["communities"]).index("Business Bay"))
    era = st.selectbox("Envelope standard", list(ui.ERA_LABELS), index=3, format_func=ui.ERA_LABELS.get)
    floors = st.slider("Floors", 6, 40, 24)
    obstruction = st.selectbox("Surroundings", list(ui.OBSTRUCTION_LABELS), index=1,
                               format_func=ui.OBSTRUCTION_LABELS.get)

base = TowerDesign(community=community, era_band=era, floors=floors, obstruction=obstruction, glass="high")
st.subheader("Design levers")
c1, c2, c3 = st.columns(3)
with c1:
    wwr = st.slider("Glass share of facade", 0.2, 0.9, 0.6, 0.05, help="Window-to-wall ratio. Base design: 0.60.")
with c2:
    shgc = st.slider("Glazing SHGC", 0.15, 0.6, 0.25, 0.01,
                     help="Solar heat gain coefficient of the glass (lower = more solar control).")
with c3:
    depth = st.slider("Balcony / fin depth (m)", 0.0, 3.0, 0.0, 0.25)

design = TowerDesign(**{**base.__dict__, "wwr": wwr, "shgc": shgc, "balcony_depth_m": depth})
reference = TowerDesign(**{**base.__dict__, "wwr": 0.6, "shgc": 0.25, "balcony_depth_m": 0.0})
with st.spinner("Simulating every unit hour by hour…"):
    ref_df = run(reference)
    df = run(design)

grid = df.pivot(index="floor", columns="facing", values="intensity")[list(ORIENTATIONS)].sort_index(ascending=False)
letters = df.pivot(index="floor", columns="facing", values="score")[list(ORIENTATIONS)].sort_index(ascending=False)
aed = df.pivot(index="floor", columns="facing", values="annual_aed")[list(ORIENTATIONS)].sort_index(ascending=False)
cuts = [6.0]
fig = go.Figure(go.Heatmap(
    z=grid.values, x=list(ORIENTATIONS), y=[str(f) for f in grid.index], text=letters.values,
    texttemplate="%{text}", customdata=aed.values, colorscale=[[0, "#0a8f3c"], [0.5, "#c99400"], [1, "#c93636"]],
    hovertemplate="Floor %{y}, %{x}-facing: CoolScore %{text}<br>AED %{customdata:,.0f}/yr "
                  "(%{z:.2f} AED/sq ft)<extra></extra>",
    colorbar=dict(title="AED/sq ft/yr"), xgap=2, ygap=2))
fig.update_layout(height=max(360, 22 * floors), margin=dict(l=10, r=10, t=10, b=10),
                  xaxis_title="Facade facing", yaxis_title="Floor", paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

impact = compare(ref_df, df)
m1, m2, m3 = st.columns(3)
m1.metric("Per unit vs base design", f"{impact['per_unit_mean_aed']:+,.0f} AED/yr", delta_color="inverse")
m2.metric("Whole tower", f"{impact['tower_aed']:+,.0f} AED/yr", delta_color="inverse")
m3.metric("Units with a better grade", impact["units_improving_grade"])
st.caption("Base design: 60% glass, SHGC 0.25, no balconies. Differences are simulated tenant cooling bills "
           "under the reference district-cooling tariff (capacity charge allocated by area, so most of the saving "
           "is consumption).")
with st.expander("How is this calculated?"):
    st.write("For each floor and facing, the ISO 13790 hourly engine simulates a typical "
             f"{base.size_sqft:,.0f} sq ft 1-bedroom (2 people, out by day, 24 °C) on 2024 weather, with neighbouring "
             "towers' shading falling with height and roof exposure on the top floor. Cooling energy is billed with "
             "the published district-cooling tariff (capacity + consumption + fuel surcharge + meter + fans + 5% VAT) "
             "and graded with the same A–E cut-offs as the rest of the app. Simulated, not measured.")
ui.footer()
