"""Check a Unit: paste a listing or set the details; the Dubai scene and the estimate update live.

Every widget sits outside a form, so each change reruns the page (estimates are cached and take
well under a second). The climate scene keeps a stable key, so it receives new values instead of
reloading: the sun, sky, haze and window glow glide to the new unit, month or community.
"""

import ui
import streamlit as st

from coolscore.assistant import direction, explain, parser

ui.setup("Check a Unit")
ui.hero("Check a unit", "Paste a listing or set the details. The Dubai sky, the sun on your windows and the "
        "cooling estimate update as you go — no submit button.", eyebrow="Live estimate")
ui.model_ready()

# A fictional listing (no real tower, developer or portal) for visitors who don't have one to hand.
EXAMPLE = ("Bright 1 bedroom in Business Bay with full canal view. 812 sq ft on the 23rd floor of a 45-storey "
           "tower, completed 2016. West-facing living room with floor-to-ceiling windows and a small balcony. "
           "District cooling, chiller not included. AED 95,000 per year, 4 cheques.")

if "check_defaults" not in st.session_state:
    st.session_state.check_defaults = {}
    st.session_state.form_version = 0


def read_listing(text: str) -> None:
    result = parser.parse_listing(text)
    st.session_state.check_defaults = result.form_defaults()
    st.session_state.parse_result = result
    st.session_state.form_version += 1          # fresh widgets so the parsed values show


def read_typed_listing() -> None:
    if st.session_state.get("listing_text", "").strip():
        read_listing(st.session_state.listing_text)


def load_example() -> None:
    st.session_state.listing_text = EXAMPLE
    read_listing(EXAMPLE)


if st.query_params.get("example") == "1" and "example_done" not in st.session_state:
    st.session_state.example_done = True       # ?example=1 opens straight on a worked example
    load_example()
if st.session_state.pop("example_pending", False):   # the Home page's "See a worked example" button
    load_example()

# ---- start from a listing ----
with ui.glass("start"):
    c1, c2 = st.columns([3.2, 1.3], vertical_alignment="bottom")
    with c1:
        text = st.text_area("Start from a listing (optional)", height=96, key="listing_text",
                            placeholder="Paste the listing description here…")
    with c2:
        st.button("Read listing", type="primary", disabled=not text.strip(), on_click=read_typed_listing,
                  width="stretch")
        st.button("Try an example", on_click=load_example, type="tertiary", help="A fictional listing, read in one click")
        with st.popover("🧭 Facing helper", width="stretch"):
            comm = st.selectbox("Community", sorted(ui.config.communities()["communities"]), key="dir_comm",
                                index=sorted(ui.config.communities()["communities"]).index("Dubai Marina"))
            view = st.selectbox("What does the listing say the view is?", direction.VIEW_PHRASES, key="dir_view")
            hint = direction.suggest(comm, view)
            if hint:
                st.info(f"Likely facing: **{hint.facing}** ({hint.reason}). A suggestion from map geometry — "
                        "confirm at the viewing (the afternoon sun comes in from the west).")
            else:
                st.info("No reliable suggestion for this combination. At the viewing, note where the afternoon "
                        "sun comes in: that side faces west.")
    if "parse_result" in st.session_state:
        r = st.session_state.parse_result
        if r.missing:
            st.markdown("<div class='cs-flag'>Missing — please confirm: <b>"
                        + ", ".join(m.replace("_", " ") for m in r.missing) + "</b></div>", unsafe_allow_html=True)
        with st.expander(f"What we read from the listing ({r.method}) — check every field", expanded=bool(r.missing)):
            rows = [{"field": k.replace("_", " "), "value": "" if v.value is None else str(v.value),
                     "status": v.status, "from the text": v.evidence or ""} for k, v in r.fields.items()]
            st.dataframe(rows, hide_index=True, width="stretch")

# ---- the unit (left) and the live scene (right) ----
left, right = st.columns([1, 1.38], gap="medium")
with left:
    with ui.glass("inputs"):
        ui.heading("The unit", "every change updates the estimate")
        listing = ui.listing_form(f"chk{st.session_state.form_version}", st.session_state.check_defaults)

est, error = None, None
try:
    est = ui.run_estimate(listing)
except ValueError as exc:
    error = str(exc)

with right:
    with st.container(key="stage_col"):
        month_name = st.select_slider("See a typical day in", options=ui.MONTHS, value="Aug", key="chk_month",
                                      help="Plays a typical day of measured Dubai weather for that month.")
        month = ui.MONTHS.index(month_name)
        ui.climate_stage(ui.stage_args(est, listing, month, message=error), key="chk_stage")
        if error:
            st.error(error)
        else:
            ui.how_calculated(est, month, listing.get("annual_rent_aed"))
ui.livebar(est, month)

if est is not None:
    if est.assumed:
        nice = ", ".join(a.replace("_", " ") for a in est.assumed)
        st.markdown(f"<div class='cs-flag'>Assumed because not given: <b>{nice}</b>. Change them above if you know "
                    "better.</div>", unsafe_allow_html=True)
        st.write("")

    d1, d2 = st.columns(2, gap="medium")
    with d1:
        with ui.glass("drivers"):
            ui.heading("What drives this unit's cost", "simulated difference per year")
            drivers = ui.drivers_html(est)
            if drivers:
                st.markdown(drivers, unsafe_allow_html=True)
            else:
                st.caption("This unit already matches the reference on every driver.")
    with d2:
        with ui.glass("months"):
            ui.heading("Month by month", "typical bill, P10–P90 whiskers, coloured by the month's heat")
            st.plotly_chart(ui.monthly_chart(est, month), width="stretch", config={"displayModeBar": False})

    with ui.glass("whatif"):
        ui.heading("What if…", "change one thing and see the simulated effect on this unit")
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            wf = st.slider("Floor", 1, int(listing["total_floors"]), int(listing["floor"]), key="wi_floor")
        with w2:
            wface = st.selectbox("Facing", ui.FACING_OPTIONS, index=ui.FACING_OPTIONS.index(listing["facing"]),
                                 key="wi_face")
        with w3:
            wsp = st.slider("AC temperature (°C)", 20.0, 28.0, float(listing.get("setpoint_c", 24.0)), 0.5,
                            key="wi_sp")
        with w4:
            wpay = st.toggle("Chiller-free", value=listing["payer"] == "landlord_chiller_free", key="wi_free",
                             disabled=listing["system"] in ("dewa_split_ac", "dewa_central_ac"))
        what_if = {**listing, "floor": wf, "facing": wface, "setpoint_c": wsp,
                   "payer": "landlord_chiller_free" if wpay else ("tenant" if listing["payer"] == "landlord_chiller_free"
                                                                   else listing["payer"])}
        what_if.setdefault("household_size", int(listing["bedrooms"]) + 1)
        what_if.setdefault("occupancy", "away_daytime")
        base_d = {**listing}
        base_d.setdefault("setpoint_c", 24.0)
        base_d.setdefault("household_size", int(listing["bedrooms"]) + 1)
        base_d.setdefault("occupancy", "away_daytime")
        base, alt = ui.run_estimate(base_d), ui.run_estimate(what_if)
        annual = ui.shifted(est.annual, alt.annual, base.annual)
        delta = annual.p50 - est.annual.p50
        m1, m2, m3 = st.columns(3)
        m1.metric("Typical annual cost", ui.aed(annual.p50), f"{delta:+,.0f} AED vs now", delta_color="inverse")
        m2.metric("Summer month", ui.aed_range(ui.shifted(est.summer_month, alt.summer_month, base.summer_month)))
        m3.metric("CoolScore", alt.score, help="The grade uses a standard household and tariff, so the AC "
                                               "temperature and who pays don't change it.")
        with st.expander("How is the what-if calculated?"):
            st.write("Both versions of the unit go through the model that includes household details (your details, "
                     "or a standard household of bedrooms + 1 people, out by day, if you didn't add them). The "
                     "difference between them is added to this unit's estimate above, so 'now' always matches the "
                     "result. Simulated, like every figure here.")

    p1, p2 = st.columns([1.35, 1], gap="medium")
    with p1:
        with ui.glass("plain"):
            ui.heading("In plain words")
            st.markdown(explain.explain(est, listing.get("annual_rent_aed")))
    with p2:
        with ui.glass("questions"):
            ui.heading("Questions to ask the agent")
            for q in explain.questions_for_agent(est):
                st.markdown(f"- {q}")
ui.footer()
