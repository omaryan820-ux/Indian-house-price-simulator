import html

import plotly.graph_objects as go
import streamlit as st


from src.charts import AMBER, BLUE, chart_title, show, style
from src.city_data import CITIES, CONFIDENCE, GROWTH_RATE_PCT, YEARS_TO_2026
from src.financial_engine import ASSUMPTION_META, adjust_price_for_growth
from src.formatting import (
    format_inr_short, format_inr_signed, format_multiple, format_pct, format_years,
)
from src.live_mode import MODE_LIVE
from src.predictor import get_localities
from src.shared import (
    cached_analysis, cached_prediction, cached_rent_vs_buy, current_case, get_mode, get_saved,
)

st.markdown("""
<style>
.cmp { width:100%; border-collapse:collapse; margin-top:0.5rem; }
.cmp th { text-align:left; padding:0.6rem 0.8rem; background:#F2F6FD; color:#111827; }
.cmp td { padding:0.6rem 0.8rem; border-bottom:1px solid #E5E7EB; color:#1F2937; }
.cmp td.best { background:#E6EFFD; color:#143F8C; font-weight:700; }
</style>
""", unsafe_allow_html=True)

mode = get_mode()
base = current_case()["assumptions"]


# ---------- remembering the page's inputs ----------
def cget(name, default):
    return st.session_state.setdefault("compare", {}).get(name, default)


def csave(name):
    st.session_state.setdefault("compare", {})[name] = st.session_state["c_" + name]


def flat_inputs(label, key, default_city, default_loc_index):
    """City, locality, BHK and area for one option. Returns a dict."""
    st.markdown("**" + label + "**")
    saved_city = cget(key + "_city", default_city)
    city = st.selectbox("City", CITIES, index=CITIES.index(saved_city), key="c_" + key + "_city",
                        on_change=csave, args=(key + "_city",))
    localities = get_localities(city)
    saved_loc = cget(key + "_loc", None)
    if saved_loc in localities:
        loc_index = localities.index(saved_loc)
    else:
        loc_index = min(default_loc_index, len(localities) - 1)
    locality = st.selectbox("Locality", localities, index=loc_index, key="c_" + key + "_loc",
                            format_func=lambda n: n.split(" | ", 1)[-1],
                            on_change=csave, args=(key + "_loc",))
    bhk = st.slider("BHK", 1, 5, value=cget(key + "_bhk", get_saved("bhk", 2)), key="c_" + key + "_bhk",
                    on_change=csave, args=(key + "_bhk",))
    area = st.slider("Area (sq ft)", 300, 4000, value=cget(key + "_area", get_saved("area", 1000)),
                     step=50, key="c_" + key + "_area", on_change=csave, args=(key + "_area",))
    return {"city": city, "locality": locality, "bhk": bhk, "area": area}


def loan_inputs(key, title):
    """Down payment, rate and tenure sliders. Returns a dict of assumption overrides."""
    st.markdown("**" + title + "**")
    columns = st.columns(3)
    result = {}
    for column, name in zip(columns, ["down_payment_pct", "annual_interest_rate_pct", "loan_tenure_years"]):
        meta = ASSUMPTION_META[name]
        with column:
            result[name] = st.slider(meta["label"], min_value=meta["min"], max_value=meta["max"],
                                     value=cget(key + "_" + name, base[name]), step=meta["step"],
                                     key="c_" + key + "_" + name, on_change=csave, args=(key + "_" + name,))
    return result


# ---------- page ----------
st.title("COMPARE")
st.caption("Two flats side by side. " + ("Showing the living view." if mode == MODE_LIVE
                                         else "Showing the investor view.") +
           " Switch the goal on the Simulator page.")

base_city = get_saved("city", "Bangalore")
col_a, col_b = st.columns(2)
with col_a:
    flat_a = flat_inputs("Option A", "A", base_city, 0)
with col_b:
    flat_b = flat_inputs("Option B", "B", base_city, 1)

loan_a = loan_inputs("A", "Loan")
different_loan = st.checkbox("Different loan terms for Option B", key="c_diff_loan",
                             value=cget("diff_loan", False), on_change=csave, args=("diff_loan",))
loan_b = loan_a
if different_loan:
    loan_b = loan_inputs("B", "Loan for Option B")


# ---------- calculations ----------
def evaluate(flat, loan):
    assumptions = dict(base)
    assumptions.update(loan)
    prediction = cached_prediction(flat["city"], flat["locality"], flat["bhk"], flat["area"], None)
    growth = GROWTH_RATE_PCT[flat["city"]]
    price = adjust_price_for_growth(prediction["price_lakhs"], growth, YEARS_TO_2026)
    analysis = cached_analysis(price, flat["area"], flat["city"], assumptions)
    rvb, breakeven = cached_rent_vs_buy(price, flat["area"], flat["city"], assumptions)
    months = int(round(assumptions["loan_tenure_years"] * 12))
    return {
        "flat": flat, "price": price, "analysis": analysis, "rvb": rvb, "breakeven": breakeven,
        "interest": analysis["monthly"]["emi"] * months - analysis["upfront"]["loan_amount"],
        "assumptions": assumptions,
    }


a = evaluate(flat_a, loan_a)
b = evaluate(flat_b, loan_b)


def pick(value_a, value_b, higher_is_better):
    """'A', 'B' or None (tie or not comparable). A missing value counts as worst."""
    if value_a is None and value_b is None:
        return None
    if value_a is None:
        return "B"
    if value_b is None:
        return "A"
    if abs(value_a - value_b) < 1e-9:
        return None
    if higher_is_better:
        return "A" if value_a > value_b else "B"
    return "A" if value_a < value_b else "B"


def sqft_price(option):
    return option["price"] * 100000 / option["flat"]["area"]


def breakeven_value(option):
    return 999 if option["breakeven"] is None else option["breakeven"]


rows = []   # (label, text A, text B, winner)
rows.append(("2026 value", format_inr_short(a["price"] * 100000), format_inr_short(b["price"] * 100000),
             pick(a["price"], b["price"], False) if mode == MODE_LIVE else None))
rows.append(("Price per sq ft", format_inr_short(sqft_price(a)), format_inr_short(sqft_price(b)),
             pick(sqft_price(a), sqft_price(b), False) if mode == MODE_LIVE else None))
rows.append(("Model confidence", CONFIDENCE[a["flat"]["city"]], CONFIDENCE[b["flat"]["city"]], None))

ua, ub = a["analysis"]["upfront"], b["analysis"]["upfront"]
ma, mb = a["analysis"]["monthly"], b["analysis"]["monthly"]
xa, xb = a["analysis"]["metrics"], b["analysis"]["metrics"]

rows.append(("Total upfront cash", format_inr_short(ua["total_upfront"]), format_inr_short(ub["total_upfront"]),
             pick(ua["total_upfront"], ub["total_upfront"], False)))
rows.append(("Monthly EMI", format_inr_short(ma["emi"]), format_inr_short(mb["emi"]),
             pick(ma["emi"], mb["emi"], False)))

if mode == MODE_LIVE:
    own_a, own_b = ma["monthly_outflow_self_occupied"], mb["monthly_outflow_self_occupied"]
    extra_a, extra_b = own_a - ma["gross_monthly_rent"], own_b - mb["gross_monthly_rent"]
    rows.append(("Monthly cost of owning (EMI + maintenance)", format_inr_short(own_a), format_inr_short(own_b),
                 pick(own_a, own_b, False)))
    rows.append(("Estimated rent for a similar flat", format_inr_short(ma["gross_monthly_rent"]),
                 format_inr_short(mb["gross_monthly_rent"]), None))
    rows.append(("Extra monthly cost of owning vs renting", format_inr_signed(extra_a), format_inr_signed(extra_b),
                 pick(extra_a, extra_b, False)))
    rows.append(("Total interest over the loan", format_inr_short(a["interest"]), format_inr_short(b["interest"]),
                 pick(a["interest"], b["interest"], False)))
    rows.append(("Buying overtakes renting", format_years(a["breakeven"], "Not in 20 years"),
                 format_years(b["breakeven"], "Not in 20 years"),
                 pick(breakeven_value(a), breakeven_value(b), False)))
else:
    def irr_text(m):
        return "n/a" if m["levered_irr_pct"] is None else format_pct(m["levered_irr_pct"])

    rows.append(("Net monthly cash flow if rented out", format_inr_signed(ma["net_monthly_cash_flow_rented"]),
                 format_inr_signed(mb["net_monthly_cash_flow_rented"]),
                 pick(ma["net_monthly_cash_flow_rented"], mb["net_monthly_cash_flow_rented"], True)))
    rows.append(("Return on your cash (IRR)", irr_text(xa), irr_text(xb),
                 pick(xa["levered_irr_pct"], xb["levered_irr_pct"], True)))
    rows.append(("Equity multiple", format_multiple(xa["levered_equity_multiple"]),
                 format_multiple(xb["levered_equity_multiple"]),
                 pick(xa["levered_equity_multiple"], xb["levered_equity_multiple"], True)))
    rows.append(("Net present value", format_inr_signed(xa["levered_npv"]), format_inr_signed(xb["levered_npv"]),
                 pick(xa["levered_npv"], xb["levered_npv"], True)))
    rows.append(("Debt service cover (DSCR)", format_multiple(xa["dscr_year1"]), format_multiple(xb["dscr_year1"]),
                 pick(xa["dscr_year1"], xb["dscr_year1"], True)))
    rows.append(("Cap rate", format_pct(xa["going_in_cap_rate_pct"]), format_pct(xb["going_in_cap_rate_pct"]),
                 pick(xa["going_in_cap_rate_pct"], xb["going_in_cap_rate_pct"], True)))
    rows.append(("Total interest over the loan", format_inr_short(a["interest"]), format_inr_short(b["interest"]),
                 pick(a["interest"], b["interest"], False)))

# ---------- summary line ----------
wins_a = [r[0] for r in rows if r[3] == "A"]
wins_b = [r[0] for r in rows if r[3] == "B"]
st.write("")
st.markdown("**Option A leads on " + str(len(wins_a)) + " measures, Option B on " + str(len(wins_b)) + ".**")

gap = abs(a["price"] - b["price"]) / max(a["price"], b["price"]) * 100
if gap < 15:
    st.info("The two prices differ by only " + format(gap, ".0f") + "%, which is within the model's "
            "typical error. Treat the prices as similar and decide on the other rows.")
low_cities = [c for c in {a["flat"]["city"], b["flat"]["city"]} if CONFIDENCE[c] == "Low"]
if low_cities:
    st.warning("Model confidence is low for " + ", ".join(sorted(low_cities))
               + ". Differences in price there can be noise.")

# ---------- table ----------
table = ['<table class="cmp"><tr><th></th><th>Option A</th><th>Option B</th></tr>']
table.append('<tr><td><b>Flat</b></td><td>' + html.escape(a["flat"]["locality"].split(" | ", 1)[-1] + ", "
             + a["flat"]["city"]) + '</td><td>' + html.escape(b["flat"]["locality"].split(" | ", 1)[-1] + ", "
             + b["flat"]["city"]) + '</td></tr>')
for label, text_a, text_b, winner in rows:
    cls_a = ' class="best"' if winner == "A" else ""
    cls_b = ' class="best"' if winner == "B" else ""
    table.append("<tr><td>" + html.escape(label) + "</td><td" + cls_a + ">" + html.escape(text_a)
                 + "</td><td" + cls_b + ">" + html.escape(text_b) + "</td></tr>")
table.append("</table>")
st.markdown("".join(table), unsafe_allow_html=True)
st.caption("Blue marks the better value in each row. Prices are 2026 estimates; "
           "amenities are left on 'Not sure' for both flats.")

# ---------- chart ----------
st.write("")
chart_title("Net worth if you buy, over time (₹ lakh)")
fig = go.Figure()
fig.add_scatter(x=a["rvb"]["Year"], y=[v / 100000 for v in a["rvb"]["Net_Worth_Buying"]],
                name="Option A", line=dict(color=BLUE, width=3))
fig.add_scatter(x=b["rvb"]["Year"], y=[v / 100000 for v in b["rvb"]["Net_Worth_Buying"]],
                name="Option B", line=dict(color=AMBER, width=3))
show(style(fig, 380))