"""Methodology & Validation: physics, data, accuracy, real-bill status, assumptions, limitations."""

import json

import pandas as pd
import ui
import streamlit as st

from coolscore import assumptions_doc, config
from coolscore.validation import report as validation

ui.setup("Methodology")
ui.hero("Methodology & validation", "How an estimate is made, how accurate the model is against the physics, "
        "where real-bill validation stands, every assumption with its source, and the limits.", eyebrow="Open book")


@st.cache_data(show_spinner=False, ttl=600)
def validation_status() -> dict:
    return validation.run(write=False)


metrics = json.loads((config.path("demo") / "model_metrics.json").read_text(encoding="utf-8"))

st.header("1. How an estimate is made")
st.markdown(
    "- **Weather:** hourly 2023–25 weather for Dubai (Open-Meteo, ECMWF IFS 9 km), temperature and humidity "
    "corrected to Dubai International and Al Maktoum airport observations (NOAA). The raw model ran 1.8 °C too "
    "cool at night in the city; corrected, the error on unseen 2025 data fell from 2.4 to 1.3 °C.\n"
    "- **Sun on facades:** pvlib solar geometry and sky model for 8 orientations. In summer, east and west "
    "facades get about 1.8× the sun of south or north; west sun arrives in the hottest hours.\n"
    "- **Physics:** the ISO 13790 hourly model of one apartment (walls, glass, roof for top floors, thermal mass), "
    "plus humidity (latent) load, balcony and neighbour shading, household schedules (UAE weekend, optional "
    "Ramadan) and AC habits. Building envelopes by era follow Dubai's rules (2003 insulation rules, Green Building "
    "Regulations compulsory from 2014, Al Sa'fat).\n"
    "- **Billing:** published tariffs: district cooling capacity (AED/RT/year, charged even at zero use) + "
    "consumption + fuel surcharge + meter fee; DEWA slabs as the marginal cost of AC electricity; chiller-free and "
    "service-charge cases; 5% VAT once.\n"
    "- **Surrogate:** 40,000 simulated units train gradient-boosted quantile models (P10/P50/P90) on what a "
    "listing tells you; unknowns (exact glass, air leakage, habits, weather year) become the range. Intervals are "
    "conformally calibrated so 80% of held-out cases fall inside P10–P90.\n"
    "- **CoolScore A–E:** cost per sq ft per year under a *standard* household and district-cooling tariff, cut at "
    "the 20/40/60/80th percentiles of the simulated stock, so it rates the unit, not the contract.")

st.header("2. Model accuracy (vs held-out physics runs)")
rows = []
for variant, label in [("listing", "Listing facts only"), ("detailed", "With household details")]:
    for target, tlabel in [("annual", "Annual cost"), ("summer", "August"), ("winter", "January")]:
        m = metrics["variants"][variant][target]
        rows.append({"Inputs": label, "Target": tlabel, "R²": f"{m['r2']:.3f}", "MAE (AED)": f"{m['mae_aed']:,.0f}",
                     "MAPE % (bills > AED 500)": f"{m['mape_pct_bills_over_500']:.1f}",
                     "P10–P90 coverage": f"{m['p10_p90_coverage']:.0%}"})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
fid = metrics["fidelity"]
st.markdown(f"**Fidelity** (model given every simulation input, i.e. how well ML reproduces the physics): "
            f"R² = **{fid['annual_tenant_aed']['r2']:.3f}** for annual cost and "
            f"**{fid['annual_kwh_th']['r2']:.3f}** for cooling energy (target ≥ {fid['target_r2']}). "
            "Listing-only accuracy is lower by design: a listing can't tell you the glass spec or how the "
            "household uses the AC, so that uncertainty is shown as the range.")
st.caption(f"Trained on {metrics['n_train']:,} scenarios, calibrated on {metrics['n_calibration']:,}, "
           f"tested on {metrics['n_test']:,}. Model file {metrics['artifact_mb']} MB.")

st.header("3. Real-bill validation")
status = validation_status()
if status["n_units"] == 0:
    st.warning("**No real bills yet — real-world accuracy is not yet validated.** The validation report runs "
               "automatically as soon as anonymised bills are added (see data/real_bills/README.md).")
else:
    st.success(f"{status['n_units']} units, {status['n_bill_months']} bill months compared.")
    for key, label in [("total_bill", "Total cooling bill"), ("consumption_rth", "Consumption (RTh)"),
                       ("capacity_charge", "Capacity charge")]:
        m = status.get(key)
        if m:
            st.markdown(f"- **{label}:** MAPE {m['mape_pct']:.0f}%, {m['within_20pct']:.0%} of months within ±20%, "
                        f"median bias {m['bias_pct']:+.0f}% ({m['n_months']} months)")
if status["sanity_band"]:
    st.markdown("**Sanity check against a published rough band** (independent guide; rough and unverified):")
    st.dataframe(pd.DataFrame([{
        "Bedrooms": r["bedrooms"] or "Studio", "Simulated median AED/month": f"{r['simulated_median_month_aed']:,}",
        "Published band": f"{r['band_low']:,}–{r['band_high']:,}", "Inside": "yes" if r["inside_band"] else "no"}
        for r in status["sanity_band"]]), hide_index=True, width="stretch")

st.header("4. Assumptions register")
st.caption("Every real-world number with its source and whether it still needs verification. Values marked "
           "MODELLING ASSUMPTION / PLACEHOLDER / PROPOSAL have no primary source and are the first things real bills "
           "and interviews should test.")


reg = [{"Assumption": r["path"], "Value": json.dumps(r["value"])[:80], "Unit": r["unit"], "Type": r["kind"],
        "Verify": "yes" if r["verify"] else "no", "Source": r["source"] or ""} for r in assumptions_doc.register()]
reg_df = pd.DataFrame(reg)
kind = st.multiselect("Show", sorted(reg_df["Type"].unique()), default=sorted(reg_df["Type"].unique()))
st.dataframe(reg_df[reg_df["Type"].isin(kind)], hide_index=True, width="stretch",
             column_config={"Source": st.column_config.LinkColumn("Source")})

st.header("5. Limitations")
st.markdown(
    "- **Simulated, not measured.** Until real bills arrive, accuracy is accuracy against physics, not reality.\n"
    "- **Contracted capacity** (the fixed district-cooling charge) is estimated from size; real allocations vary and "
    "often dominate the bill. Ask for the unit's RT.\n"
    "- **One-zone apartment model**; neighbours are assumed conditioned; reflections from glass towers are ignored.\n"
    "- **Weather** is a 9 km model corrected to airports; Marina sea breezes and street canyons are not resolved.\n"
    "- **Behaviour** (AC temperature, blinds, leaving AC on) can move a bill more than the building does.\n"
    "- **Tariffs** change (fuel surcharge monthly); providers other than the published reference may differ.")
st.caption("Attribution: weather data by Open-Meteo.com (CC BY 4.0); observations from NOAA NCEI ISD. Full write-ups: "
           "docs/methodology.md, docs/model_card.md, docs/evidence/.")
ui.footer()
