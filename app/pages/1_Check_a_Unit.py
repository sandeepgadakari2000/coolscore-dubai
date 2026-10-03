"""Check a Unit: paste a listing or fill the form → CoolScore, ranges, drivers, what-if."""

import ui
import streamlit as st

from coolscore.assistant import direction, explain, parser

ui.setup("Check a Unit")
st.title("Check a unit")
st.caption("Paste a listing or fill the form. Answers are simulated estimates with a likely range.")
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
    st.session_state.pop("check_listing", None)


def load_example() -> None:
    st.session_state.listing_text = EXAMPLE
    read_listing(EXAMPLE)
    st.session_state.auto_estimate = True


if st.query_params.get("example") == "1" and "example_done" not in st.session_state:
    st.session_state.example_done = True       # ?example=1 opens straight on a worked example
    load_example()

tab_paste, tab_dir = st.tabs(["Paste a listing (optional)", "Not sure which way it faces?"])
with tab_paste:
    text = st.text_area("Listing text", height=140, placeholder="Paste the listing description here…",
                        key="listing_text")
    if st.button("Read listing", disabled=not text.strip()):
        with st.spinner("Reading the listing…"):
            read_listing(text)
        st.rerun()
    st.button("No listing to hand? Try an example", on_click=load_example, type="tertiary")
    if "parse_result" in st.session_state:
        r = st.session_state.parse_result
        st.caption(f"Read with: {r.method}. Check every field below; nothing is guessed silently.")
        rows = [{"field": k.replace("_", " "), "value": "" if v.value is None else str(v.value),
                 "status": v.status, "from the text": v.evidence or ""} for k, v in r.fields.items()]
        st.dataframe(rows, hide_index=True, width="stretch")
        if r.missing:
            st.markdown("<div class='cs-flag'>Missing — please confirm: <b>"
                        + ", ".join(m.replace("_", " ") for m in r.missing) + "</b></div>", unsafe_allow_html=True)
with tab_dir:
    comm = st.selectbox("Community", sorted(ui.config.communities()["communities"]), key="dir_comm",
                        index=sorted(ui.config.communities()["communities"]).index("Dubai Marina"))
    view = st.selectbox("What does the listing say the view is?", direction.VIEW_PHRASES, key="dir_view")
    hint = direction.suggest(comm, view)
    if hint:
        st.info(f"Likely facing: **{hint.facing}** ({hint.reason}). This is a suggestion from map geometry — "
                "please confirm at the viewing (check where the sun sets: west).")
    else:
        st.info("No reliable suggestion for this combination. At the viewing, note where the afternoon sun "
                "comes in: that side faces west.")

with st.form("check"):
    listing = ui.listing_form(f"chk{st.session_state.form_version}", st.session_state.check_defaults)
    submitted = st.form_submit_button("Estimate cooling cost", type="primary")
submitted = submitted or st.session_state.pop("auto_estimate", False)

if submitted or "check_listing" in st.session_state:
    if submitted:
        st.session_state.check_listing = listing
    listing = st.session_state.check_listing
    try:
        est = ui.run_estimate(listing)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    st.subheader("Result")
    ui.result_card(est, listing.get("annual_rent_aed"))

    st.subheader("What if…")
    st.caption("Change one thing and see the simulated effect (same unit otherwise).")
    w1, w2 = st.columns(2)
    with w1:
        wf = st.slider("Floor", 1, int(listing["total_floors"]), int(listing["floor"]), key="wi_floor")
        wface = st.selectbox("Facing", ui.FACING_OPTIONS, index=ui.FACING_OPTIONS.index(listing["facing"]),
                             key="wi_face")
    with w2:
        wsp = st.slider("AC temperature (°C)", 20.0, 28.0, float(listing.get("setpoint_c", 24.0)), 0.5, key="wi_sp")
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
                 "result card. Simulated, like every figure here.")

    st.subheader("In plain words")
    st.markdown(explain.explain(est, listing.get("annual_rent_aed")))
    st.markdown("**Questions to ask the agent**")
    for q in explain.questions_for_agent(est):
        st.markdown(f"- {q}")
ui.footer()
