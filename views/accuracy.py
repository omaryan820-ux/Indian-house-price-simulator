import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.branding import APP_NAME
from src.charts import chart_title, show, style
from src.city_data import CITIES, CONFIDENCE, GROWTH_RATE_PCT, GROWTH_SOURCE_NOTE, YEARS_TO_2026
from src.financial_engine import ASSUMPTION_META, DEFAULT_ASSUMPTIONS
from src.predictor import load_bundle
from src.storage import save_row

st.title("ACCURACY & ASSUMPTIONS")
st.caption("What this tool can and cannot tell you. Read this before trusting any number.")

# ---------- 1. model accuracy ----------
st.header("How accurate is the price estimate?")
accuracy = pd.DataFrame(load_bundle()["accuracy_table"])
if "City" in accuracy.columns:
    accuracy = accuracy.set_index("City")
accuracy = accuracy.loc[[c for c in CITIES if c in accuracy.index]]

colors = {"High": "#1D5FD0", "Medium": "#8FB6F5", "Low": "#D98A00"}
chart_title("Typical error of the price estimate, by city (%)")
fig = go.Figure(go.Bar(
    x=list(accuracy.index), y=accuracy["median_pct_error"],
    marker_color=[colors[CONFIDENCE[c]] for c in accuracy.index],
    text=[format(v, ".0f") + "%" for v in accuracy["median_pct_error"]], textposition="outside",
))
show(style(fig, 320))

table = pd.DataFrame({
    "City": list(accuracy.index),
    "Typical error": [format(v, ".1f") + "%" for v in accuracy["median_pct_error"]],
    "Test flats checked": [int(v) for v in accuracy["rows"]],
    "Confidence": [CONFIDENCE[c] for c in accuracy.index],
})
st.dataframe(table, hide_index=True)

st.markdown(
    "- **Typical error** is the middle (median) gap between the model's price and the real listing price "
    "on flats the model had never seen.\n"
    "- The **range** shown on the Simulator is wide on purpose: about 8 in 10 test flats fell inside their "
    "city's range.\n"
    "- **Where it is weak:** luxury and prime areas (for example Malabar Hill in Mumbai), unusually large or "
    "small flats, and Kolkata and Mumbai, where the data is thin and many listings have no amenity details.\n"
    "- **The data:** one public Kaggle listing dataset of about 33,000 flats in six metros, roughly "
    + str(YEARS_TO_2026) + " years old. Listing prices are asking prices, not final sale prices."
)

# ---------- 2. 2026 growth ----------
st.header("How the 2026 value is worked out")
st.write("The model's price is on the dataset's timeline. We grow it at a yearly rate for "
         + str(YEARS_TO_2026) + " years to reach 2026.")
growth_table = pd.DataFrame({
    "City": CITIES,
    "Growth used (% a year)": [format(GROWTH_RATE_PCT[c], ".1f") for c in CITIES],
})
st.dataframe(growth_table, hide_index=True)
st.markdown(
    "These rates are **our own estimates** of average growth over the period. " + GROWTH_SOURCE_NOTE +
    " Recent one-year jumps in some cities were higher, and earlier years were slower, so a single "
    "average is a simplification. Sources consulted: "
    "[PropTiger via Trade Brains (Q1 2026)](https://tradebrains.in/money/top-8-indian-cities-with-the-highest-property-price-appreciation-in-2026-mumbai-isnt-at-the-top/), "
    "[Business Today (H1 2026)](https://www.businesstoday.in/real-estate/story/property-prices-rise-across-15-indian-cities-in-h1-2026-faridabad-delhi-lead-with-18-growth-554894-2026-09-12)."
)

# ---------- 3. finance assumptions ----------
st.header("Finance assumptions")
st.write("These are the starting values. You can change most of them on the Simulator page.")
rows = []
for name, meta in ASSUMPTION_META.items():
    rows.append({"Setting": meta["label"], "Starting value": str(DEFAULT_ASSUMPTIONS[name]),
                 "What it means": meta["help"]})
st.dataframe(pd.DataFrame(rows), hide_index=True)

st.markdown(
    "**Stamp duty and registration** use our estimates per city. Published sources disagree for several "
    "cities, so check your state's current rates before you act.\n\n"
    "**Not modelled:** income tax (home-loan interest deduction, tax on rent, capital gains), property tax, "
    "GST on under-construction flats, loan prepayment, interest-rate changes during the loan, brokerage when "
    "buying, and women's stamp-duty concessions."
)

st.info(APP_NAME + " is a planning tool, not financial, legal or investment advice.")

# ---------- 4. feedback ----------
st.header("Tell us what you think")
with st.form("feedback_form", clear_on_submit=True):
    rating = st.select_slider("How useful was this?", options=[1, 2, 3, 4, 5], value=4)
    close = st.radio("Was the estimate close to a price you know?",
                     ["Haven't checked", "Yes, close", "Somewhat off", "Far off"], horizontal=True)
    comment = st.text_area("What should we improve? (optional)")
    submitted = st.form_submit_button("Send feedback", type="primary")

if submitted:
    where = save_row("feedback", [rating, close, comment])
    st.balloons()
    st.success("Thank you! Your feedback helps make this better.")
    if where == "local":
        st.caption("Saved on this computer only (Google Sheet is not connected yet).")