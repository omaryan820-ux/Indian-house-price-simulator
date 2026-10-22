import streamlit as st

from src.city_data import GROWTH_RATE_PCT, YEARS_TO_2026
from src.financial_engine import (
    ASSUMPTION_META, DEFAULT_ASSUMPTIONS, adjust_price_for_growth, build_amortization_schedule,
    build_breakeven_matrix, build_irr_matrix, build_rate_sensitivity, build_rent_vs_buy,
    find_breakeven_year, run_light_analysis,
)
from src.predictor import get_amenity_levels, get_localities, predict_price


def get_saved(name, default):
    return st.session_state.setdefault("inputs", {}).get(name, default)


@st.cache_data
def cached_prediction(city, locality, bhk, area, amenity_score):
    return predict_price(city, locality, bhk, area, amenity_score)


@st.cache_data
def cached_analysis(price_lakhs, area, city, assumptions):
    return run_light_analysis(price_lakhs, area, city, assumptions)


@st.cache_data
def cached_rent_vs_buy(price_lakhs, area, city, assumptions):
    table = build_rent_vs_buy(price_lakhs, area, city, assumptions)
    return table, find_breakeven_year(table)


@st.cache_data
def cached_amortization(loan_amount, rate, tenure):
    return build_amortization_schedule(loan_amount, rate, tenure)


@st.cache_data
def cached_rate_sensitivity(price_lakhs, area, city, assumptions):
    return build_rate_sensitivity(price_lakhs, area, city, assumptions)


@st.cache_data
def cached_irr_matrix(price_lakhs, area, city, assumptions):
    return build_irr_matrix(price_lakhs, area, city, assumptions)


@st.cache_data
def cached_breakeven_matrix(price_lakhs, area, city, assumptions):
    return build_breakeven_matrix(price_lakhs, area, city, assumptions)


def current_case():
    """The flat and assumptions the user set on the Simulator page, with the 2026 price."""
    city = get_saved("city", "Bangalore")
    localities = get_localities(city)
    locality = get_saved("locality", localities[0])
    if locality not in localities:
        locality = localities[0]
    bhk = get_saved("bhk", 2)
    area = get_saved("area", 1000)

    levels = get_amenity_levels()
    choice = get_saved("amenity", "Not sure")
    if choice not in levels:
        choice = "Not sure"
        
    assumptions = dict(DEFAULT_ASSUMPTIONS)
    for name in ASSUMPTION_META:
        assumptions[name] = get_saved("a_" + name, DEFAULT_ASSUMPTIONS[name])

   

    prediction = cached_prediction(city, locality, bhk, area, levels[choice])
    model_price = adjust_price_for_growth(prediction["price_lakhs"], GROWTH_RATE_PCT[city], YEARS_TO_2026)
    asking = (get_saved("asking", 0) or 0) if get_saved("asking_on", False) else 0
    price_used = asking if asking > 0 else model_price
    return {
        "city": city, "locality": locality, "bhk": bhk, "area": area,
        "assumptions": assumptions, "price_2026_lakhs": price_used,
        "model_price_2026_lakhs": model_price, "prediction": prediction,
    }
from src.live_mode import clean_mode


def get_mode():
    """'Live in it' or 'Invest' (Invest is the default if nothing was chosen)."""
    return clean_mode(get_saved("mode", None))


def get_income():
    """Monthly take-home income, 0 if the user did not enter any."""
    return get_saved("income", 0) or 0   
    