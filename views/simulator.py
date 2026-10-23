import pandas as pd
import streamlit as st

from src.cards import inject_card_css, metric_card, range_bar, value_card, verdict_banner
from src.city_data import CITIES, CONFIDENCE, GROWTH_RATE_PCT, GROWTH_SOURCE_NOTE, YEARS_TO_2026
from src.financial_engine import ASSUMPTION_META, DEFAULT_ASSUMPTIONS, adjust_price_for_growth
from src.formatting import (
    format_inr_short, format_inr_signed, format_multiple, format_pct,
)
from src.live_mode import MODE_INVEST, MODE_LIVE, clean_mode, live_verdict
from src.predictor import get_amenity_levels, get_localities
from src.shared import cached_analysis, cached_prediction, cached_rent_vs_buy, get_saved
from src.verdicts import get_verdict
from src.asking import asking_check

inject_card_css()

LOAN_SLIDERS = ["down_payment_pct", "annual_interest_rate_pct", "loan_tenure_years"]
# Advanced sliders that matter to someone who just wants to live in the flat
LIVE_ADVANCED = ["loan_fee_pct", "capex_per_sqft", "rental_yield_pct", "rent_growth_pct",
                 "maintenance_per_sqft_monthly", "maintenance_growth_pct",
                 "property_appreciation_pct", "market_return_pct"]


# ---------- remembering inputs when the user changes page ----------
def save(name):
    st.session_state.setdefault("inputs", {})[name] = st.session_state["w_" + name]


def assumption_slider(name):
    meta = ASSUMPTION_META[name]
    label = meta["label"]
    if name == "rental_yield_pct":
        label = "Rent for a similar flat (% of price per year)"
    st.slider(
        label, min_value=meta["min"], max_value=meta["max"],
        value=get_saved("a_" + name, DEFAULT_ASSUMPTIONS[name]), step=meta["step"],
        help=meta["help"], key="w_a_" + name, on_change=save, args=("a_" + name,),
    )


# ---------- sidebar inputs ----------
with st.sidebar:
    mode_choice = st.segmented_control(
        "I want to", [MODE_LIVE, MODE_INVEST], default=clean_mode(get_saved("mode", None)),
        key="w_mode", on_change=save, args=("mode",),
    )
    mode = clean_mode(mode_choice)
    st.session_state.setdefault("inputs", {})["mode"] = mode

    st.checkbox("I have the seller's asking price", value=get_saved("asking_on", False),
                key="w_asking_on", on_change=save, args=("asking_on",))
    if st.session_state["w_asking_on"]:
        st.number_input("Asking price (₹ lakh)", min_value=1.0, max_value=100000.0,
                        value=float(get_saved("asking", 0.0)) or 50.0, step=5.0, key="w_asking",
                        on_change=save, args=("asking",),
                        help="All the finance numbers will use this price.")
        if "asking" not in st.session_state.get("inputs", {}):
            save("asking")

    st.markdown("### Your flat")
    saved_city = get_saved("city", "Bangalore")
    city = st.selectbox("City", CITIES, index=CITIES.index(saved_city), key="w_city",
                        on_change=save, args=("city",))

    localities = get_localities(city)
    saved_loc = get_saved("locality", localities[0])
    loc_index = localities.index(saved_loc) if saved_loc in localities else 0
    locality = st.selectbox("Locality", localities, index=loc_index, key="w_locality",
                            format_func=lambda name: name.split(" | ", 1)[-1],
                            on_change=save, args=("locality",))

    bhk = st.slider("BHK", 1, 5, value=get_saved("bhk", 2), key="w_bhk",
                    on_change=save, args=("bhk",))
    area = st.slider("Area (sq ft)", 300, 4000, value=get_saved("area", 1000), step=50,
                     key="w_area", on_change=save, args=("area",))

    amenity_levels = get_amenity_levels()
    amenity_choice = st.segmented_control(
        "Amenities", list(amenity_levels.keys()), default=get_saved("amenity", "Not sure"),
        key="w_amenity", on_change=save, args=("amenity",),
        help="Gym, pool, security and similar. 'Not sure' is fine; the model handles it.",
    )
    if amenity_choice is None:
        amenity_choice = "Not sure"

    st.markdown("### Loan")
    for slider_name in LOAN_SLIDERS:
        assumption_slider(slider_name)

    if mode == MODE_LIVE:
        st.number_input("Monthly take-home income (₹, optional)", min_value=0, max_value=10000000,
                        value=get_saved("income", 0), step=5000, key="w_income",
                        on_change=save, args=("income",),
                        help="Only used to show what share of your income the EMI takes.")

    with st.expander("Advanced assumptions"):
        for slider_name in ASSUMPTION_META:
            if slider_name in LOAN_SLIDERS:
                continue
            if mode == MODE_LIVE and slider_name not in LIVE_ADVANCED:
                continue
            assumption_slider(slider_name)


# ---------- the numbers ----------
assumptions = dict(DEFAULT_ASSUMPTIONS)
for name in ASSUMPTION_META:
    assumptions[name] = get_saved("a_" + name, DEFAULT_ASSUMPTIONS[name])

prediction = cached_prediction(city, locality, bhk, area, amenity_levels[amenity_choice])

growth = GROWTH_RATE_PCT[city]
price_2026 = adjust_price_for_growth(prediction["price_lakhs"], growth, YEARS_TO_2026)
low_2026 = adjust_price_for_growth(prediction["low_lakhs"], growth, YEARS_TO_2026)
high_2026 = adjust_price_for_growth(prediction["high_lakhs"], growth, YEARS_TO_2026)

asking = (get_saved("asking", 0) or 0) if get_saved("asking_on", False) else 0
price_used = asking if asking > 0 else price_2026

analysis = cached_analysis(price_used, area, city, assumptions)
metrics, monthly, upfront = analysis["metrics"], analysis["monthly"], analysis["upfront"]


def lakhs_text(value_lakhs):
    return format_inr_short(value_lakhs * 100000)


# ---------- page ----------
st.title("SIMULATOR")
st.caption(locality.split(" | ", 1)[-1] + ", " + city + "  ·  " + str(bhk) + " BHK  ·  "
           + format(area, ",") + " sq ft  ·  " + mode)

left, right = st.columns([1, 1.5])
with left:
    value_card("Model estimate (dataset era)", lakhs_text(prediction["price_lakhs"]),
               "From the Kaggle data, about " + str(YEARS_TO_2026) + " years old")
with right:
    value_card("2026 value", lakhs_text(price_2026),
               "Grown at " + format(growth, ".1f") + "% a year for " + str(YEARS_TO_2026)
               + " years. " + GROWTH_SOURCE_NOTE,
               accent=True, badge=CONFIDENCE[city])
    position = 50
    if high_2026 > low_2026:
        position = (price_2026 - low_2026) / (high_2026 - low_2026) * 100
    range_bar("Likely low: " + lakhs_text(low_2026), "Likely high: " + lakhs_text(high_2026), position)

st.write("")

if asking > 0:
    check_level, check_head, check_detail = asking_check(asking, price_2026, low_2026, high_2026)
    verdict_banner(check_level, check_head, check_detail)
    st.caption("The numbers below use the asking price: " + lakhs_text(asking) + ".")

months = int(round(assumptions["loan_tenure_years"] * 12))
total_interest = monthly["emi"] * months - upfront["loan_amount"]

if mode == MODE_LIVE:
    income = get_saved("income", 0) or 0
    rvb, breakeven = cached_rent_vs_buy(price_2026, area, city, assumptions)
    level, headline, detail = live_verdict(monthly, breakeven, income, assumptions)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total upfront cash", format_inr_short(upfront["total_upfront"]),
                    "Down payment, stamp duty and fees")
    with c2:
        metric_card("Monthly cost of owning", format_inr_short(monthly["monthly_outflow_self_occupied"]),
                    "EMI " + format_inr_short(monthly["emi"]) + " + maintenance "
                    + format_inr_short(monthly["maintenance"]))
    with c3:
        metric_card("Rent for a similar flat (estimate)", format_inr_short(monthly["gross_monthly_rent"]),
                    "Per month. Change it under Advanced assumptions")
    with c4:
        metric_card("Total interest over the loan", format_inr_short(total_interest),
                    "At " + format_pct(assumptions["annual_interest_rate_pct"]) + " for "
                    + str(assumptions["loan_tenure_years"]) + " years")

    verdict_banner(level, headline, detail)

    for warning in analysis["warnings"]:
        st.warning(warning)

    with st.expander("Upfront cash breakdown"):
        down_payment = upfront["property_price"] - upfront["loan_amount"]
        rows = [
            ("Down payment", format_inr_short(down_payment)),
            ("Stamp duty and registration", format_inr_short(upfront["government_charges_total"])),
            ("Loan processing fee", format_inr_short(upfront["loan_fee"])),
            ("Renovation / interiors", format_inr_short(upfront["capex"])),
            ("Total upfront cash", format_inr_short(upfront["total_upfront"])),
        ]
        st.table(pd.DataFrame(rows, columns=["Item", "Amount"]).set_index("Item"))

else:
    irr = metrics["levered_irr_pct"]
    irr_text = "n/a" if irr is None else format_pct(irr)
    shortfall = monthly["net_monthly_cash_flow_rented"]
    level, headline, detail = get_verdict(metrics, monthly, assumptions)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total upfront cash", format_inr_short(upfront["total_upfront"]),
                    "Down payment, stamp duty and fees")
    with c2:
        metric_card("Monthly EMI", format_inr_short(monthly["emi"]),
                    "Plus " + format_inr_short(monthly["maintenance"]) + " society maintenance")
    with c3:
        metric_card("Net monthly cash flow if rented out", format_inr_signed(shortfall),
                    "Rent minus EMI and running costs", tone="red" if shortfall < 0 else "neutral")
    with c4:
        metric_card("Return on your cash (IRR)", irr_text,
                    "Per year over " + str(assumptions["hold_years"]) + " years",
                    tone="red" if level == "red" else "amber")

    verdict_banner(level, headline, detail)

    for warning in analysis["warnings"]:
        st.warning(warning)

    with st.expander("Investor view: all financial numbers"):
        unlev = metrics["unlevered_irr_pct"]
        rows = [
            ("Your own cash invested", format_inr_short(metrics["equity_invested"])),
            ("Loan amount", format_inr_short(metrics["loan_amount"])),
            ("Return on your cash (levered IRR)", irr_text),
            ("Return with no loan (unlevered IRR)", "n/a" if unlev is None else format_pct(unlev)),
            ("Equity multiple", format_multiple(metrics["levered_equity_multiple"])),
            ("Net present value (levered)", format_inr_signed(metrics["levered_npv"])),
            ("Cap rate (year 1)", format_pct(metrics["going_in_cap_rate_pct"])),
            ("Debt service cover (DSCR, year 1)", format_multiple(metrics["dscr_year1"])),
            ("Debt yield", format_pct(metrics["debt_yield_pct"])),
            ("Average cash-on-cash return", format_pct(metrics["avg_cash_on_cash_levered_pct"])),
            ("Monthly rent needed to break even", format_inr_short(metrics["break_even_gross_monthly_rent"])),
            ("Sale value at end of holding period", format_inr_short(metrics["sale_value"])),
            ("Loan still to repay at sale", format_inr_short(metrics["loan_payoff_at_sale"])),
        ]
        st.table(pd.DataFrame(rows, columns=["Measure", "Value"]).set_index("Measure"))

with st.expander("How the 2026 value was calculated"):
    st.markdown(
        "1. The model predicts the price on the dataset's timeline: **"
        + lakhs_text(prediction["price_lakhs"]) + "**.\n"
        "2. We grow it at **" + format(growth, ".1f") + "% a year** for **" + str(YEARS_TO_2026)
        + " years**: " + lakhs_text(prediction["price_lakhs"]) + " × (1 + "
        + format(growth / 100, ".3f") + ")^" + str(YEARS_TO_2026) + " = **" + lakhs_text(price_2026) + "**.\n"
        "3. The range uses this city's typical model error. It is wide on purpose: "
        "about 8 in 10 test flats fell inside their city's range.\n\n"
        "The growth rate is our own estimate, not model output. " + GROWTH_SOURCE_NOTE
    )

if st.button("See full analysis →", type="primary"):
    st.switch_page("views/analysis.py")