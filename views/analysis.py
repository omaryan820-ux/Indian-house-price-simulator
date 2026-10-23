import pandas as pd
import plotly.graph_objects as go
import streamlit as st


from src.cards import inject_card_css, metric_card
from src.charts import AMBER, BLUE, LIGHT_BLUE, chart_title, heatmap, show, style
from src.formatting import (
    format_inr_short, format_inr_signed, format_multiple, format_pct,
)
from src.live_mode import MODE_LIVE, cumulative_costs, max_loan_for_emi
from src.shared import (
    cached_amortization, cached_analysis, cached_breakeven_matrix, cached_irr_matrix,
    cached_rate_sensitivity, cached_rent_vs_buy, current_case, get_income, get_mode,
)

inject_card_css()

case = current_case()
mode = get_mode()
city, area, a = case["city"], case["area"], case["assumptions"]
price = case["price_2026_lakhs"]

analysis = cached_analysis(price, area, city, a)
metrics, monthly, upfront, annual = (analysis["metrics"], analysis["monthly"],
                                     analysis["upfront"], analysis["annual"])
rvb, breakeven = cached_rent_vs_buy(price, area, city, a)

st.title("ANALYSIS")
st.caption(case["locality"].split(" | ", 1)[-1] + ", " + city + "  ·  " + str(case["bhk"]) + " BHK  ·  "
           + format(area, ",") + " sq ft  ·  Price used " + format_inr_short(price * 100000)
           + "  ·  " + mode)

if mode == MODE_LIVE:
    tab_overview, tab_rvb, tab_afford = st.tabs(["Overview", "Rent vs Buy", "Affordability"])
else:
    tab_overview, tab_rvb, tab_returns, tab_risk = st.tabs(["Overview", "Rent vs Buy", "Returns", "Risk"])


def lakh(values):
    return [v / 100000 for v in values]


# ---------------- Overview (both modes) ----------------
with tab_overview:
    months = int(round(a["loan_tenure_years"] * 12))
    total_interest = monthly["emi"] * months - upfront["loan_amount"]

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Loan amount", format_inr_short(upfront["loan_amount"]),
                    format(100 - a["down_payment_pct"], ".0f") + "% of the price")
    with c2:
        metric_card("Total interest over the loan", format_inr_short(total_interest),
                    "At " + format_pct(a["annual_interest_rate_pct"]) + " for "
                    + str(a["loan_tenure_years"]) + " years")
    with c3:
        metric_card("Total upfront cash", format_inr_short(upfront["total_upfront"]),
                    "Down payment, stamp duty and fees")

    st.write("")
    chart_title("Where your EMI goes each year (₹ lakh)")
    schedule = cached_amortization(upfront["loan_amount"], a["annual_interest_rate_pct"],
                                   a["loan_tenure_years"])
    fig = go.Figure()
    fig.add_bar(x=schedule["Year"], y=lakh(schedule["Principal_Paid"]), name="Principal", marker_color=BLUE)
    fig.add_bar(x=schedule["Year"], y=lakh(schedule["Interest_Paid"]), name="Interest", marker_color=LIGHT_BLUE)
    fig.update_layout(barmode="stack")
    show(style(fig))

    chart_title("Your stake in the home: value vs loan still owed (₹ lakh)")
    fig2 = go.Figure()
    fig2.add_scatter(x=rvb["Year"], y=lakh(rvb["Home_Value"]), name="Home value",
                     line=dict(color=BLUE, width=3))
    fig2.add_scatter(x=rvb["Year"], y=lakh(rvb["Loan_Balance"]), name="Loan still owed",
                     line=dict(color=AMBER, width=3))
    show(style(fig2, 340))
    st.caption("The gap between the lines is the part of the home that is yours. "
               "Home value grows at " + format_pct(a["property_appreciation_pct"]) + " a year (an assumption).")

# ---------------- Rent vs Buy (both modes) ----------------
with tab_rvb:
    if breakeven is None:
        st.info("At these assumptions, buying does not overtake renting within "
                + str(a["projection_years"]) + " years.")
    else:
        st.success("Buying overtakes renting in year " + str(breakeven) + ".")

    st.caption("Both start with the same cash. The buyer pays EMI and maintenance; the renter pays rent. "
               "Whoever pays less invests the difference in the market at "
               + format_pct(a["market_return_pct"]) + " a year.")

    chart_title("Net worth over time (₹ lakh)")
    fig3 = go.Figure()
    fig3.add_scatter(x=rvb["Year"], y=lakh(rvb["Net_Worth_Buying"]), name="Buying", line=dict(color=BLUE, width=3))
    fig3.add_scatter(x=rvb["Year"], y=lakh(rvb["Net_Worth_Renting"]), name="Renting", line=dict(color=AMBER, width=3))
    show(style(fig3, 420))

    chart_title("When does buying win? (breakeven year)")
    st.caption("Rows: property price growth. Columns: what your money earns in the market.")
    grid = cached_breakeven_matrix(price, area, city, a)
    text = [[("Never" if pd.isna(v) else "Year " + str(int(v))) for v in row] for row in grid.values]
    show(heatmap(grid.fillna(99), text, "Market return (% a year)", "Price growth (% a year)",
                 colorscale="Blues_r"))

# ---------------- Affordability (live mode) ----------------
if mode == MODE_LIVE:
    with tab_afford:
        income = get_income()
        emi = monthly["emi"]

        if income > 0:
            max_emi = income * 0.40
            max_loan = max_loan_for_emi(max_emi, a["annual_interest_rate_pct"], a["loan_tenure_years"])
            c1, c2, c3 = st.columns(3)
            with c1:
                share = emi / income * 100
                metric_card("EMI as share of your income", format(share, ".0f") + "%",
                            "Banks usually prefer under 40-50%", tone="amber" if share > 50 else "neutral")
            with c2:
                metric_card("Comfortable EMI (40% of income)", format_inr_short(max_emi), "Per month")
            with c3:
                metric_card("Loan that fits that EMI", format_inr_short(max_loan),
                            "At " + format_pct(a["annual_interest_rate_pct"]) + " for "
                            + str(a["loan_tenure_years"]) + " years")
            st.write("")
        else:
            st.info("Add your monthly take-home income in the Simulator sidebar to see how the EMI "
                    "compares with it. The tables below work without it.")

        chart_title("If the loan rate changes")
        sens = cached_rate_sensitivity(price, area, city, a)
        table = pd.DataFrame({
            "Loan rate": sens["Interest_Rate_Pct"].map(lambda v: format_pct(v)),
            "Monthly EMI": sens["Monthly_EMI"].map(format_inr_short),
            "Total interest": sens["Total_Interest"].map(format_inr_short),
        })
        if income > 0:
            table["Share of income"] = [format(v / income * 100, ".0f") + "%" for v in sens["Monthly_EMI"]]
        st.dataframe(table, hide_index=True)

        chart_title("Money paid out: renting vs owning")
        costs = cumulative_costs(monthly, rvb, a, [5, 10, 15, 20])
        costs_show = pd.DataFrame({
            "Years": costs["Years"],
            "Rent paid if renting": costs["Rent paid if renting"].map(format_inr_short),
            "Paid if owning (EMI + maintenance)": costs["Paid if owning (EMI + maintenance)"].map(format_inr_short),
            "Home value minus loan owed": costs["Home value minus loan owed"].map(format_inr_short),
        })
        st.dataframe(costs_show, hide_index=True)
        st.caption("Owning also needs the upfront cash of " + format_inr_short(upfront["total_upfront"])
                   + ". Rent is an estimate from the rent-yield setting. "
                   "Not included: property tax, income tax benefits and repairs beyond maintenance.")

# ---------------- Returns and Risk (invest mode) ----------------
else:
    with tab_returns:
        irr = metrics["levered_irr_pct"]
        unlev = metrics["unlevered_irr_pct"]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Return on your cash (IRR)", "n/a" if irr is None else format_pct(irr), "With the loan")
        with c2:
            metric_card("Return with no loan", "n/a" if unlev is None else format_pct(unlev), "Unlevered IRR")
        with c3:
            metric_card("Equity multiple", format_multiple(metrics["levered_equity_multiple"]),
                        "Cash back per ₹1 put in")
        with c4:
            metric_card("Net present value", format_inr_signed(metrics["levered_npv"]),
                        "At " + format_pct(a["discount_rate_pct"]) + " discount rate")

        st.write("")
        chart_title("Cash flow by year")
        table = annual[["Year", "NOI", "Cash_Flow_After_Debt", "Levered_CF"]].copy()
        table["NOI"] = table["NOI"].map(format_inr_signed)
        table["Cash_Flow_After_Debt"] = table["Cash_Flow_After_Debt"].map(format_inr_signed)
        table["Levered_CF"] = table["Levered_CF"].map(format_inr_signed)
        table.columns = ["Year", "Rent minus costs", "After EMI", "Your total cash flow"]
        st.dataframe(table, hide_index=True)
        st.caption("Year 0 is your upfront cash going out. The last year includes the sale of the flat.")

        chart_title("Return on your cash: loan rate vs price growth")
        irr_grid = cached_irr_matrix(price, area, city, a)
        text = [[("n/a" if pd.isna(v) else format(v, ".1f") + "%") for v in row] for row in irr_grid.values]
        show(heatmap(irr_grid.fillna(-20), text, "Loan interest rate (%)", "Price growth (% a year)"))

    with tab_risk:
        for warning in analysis["warnings"]:
            st.warning(warning)

        dscr = metrics["dscr_year1"]
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Debt service cover (DSCR)", format_multiple(dscr),
                        "Rent income ÷ EMI. Below 1.0x means rent does not cover the loan.",
                        tone="red" if (dscr is not None and dscr < 1) else "neutral")
        with c2:
            metric_card("Cap rate", format_pct(metrics["going_in_cap_rate_pct"]),
                        "Yearly rent minus costs ÷ price paid")
        with c3:
            metric_card("Rent needed to break even", format_inr_short(metrics["break_even_gross_monthly_rent"]),
                        "Per month, to cover EMI and costs")

        st.write("")
        chart_title("If the loan rate changes")
        sens = cached_rate_sensitivity(price, area, city, a)
        show_table = pd.DataFrame({
            "Loan rate": sens["Interest_Rate_Pct"].map(lambda v: format_pct(v)),
            "Monthly EMI": sens["Monthly_EMI"].map(format_inr_short),
            "Total interest": sens["Total_Interest"].map(format_inr_short),
            "Monthly cash flow if rented": sens["Net_Monthly_Cash_Flow"].map(format_inr_signed),
            "DSCR": sens["DSCR"].map(format_multiple),
            "IRR": sens["Levered_IRR_Pct"].map(lambda v: "n/a" if v is None or v != v else format_pct(v)),
        })
        st.dataframe(show_table, hide_index=True)

        low_row, high_row = sens.iloc[0], sens.iloc[-1]
        st.caption("From " + format_pct(low_row["Interest_Rate_Pct"]) + " to " + format_pct(high_row["Interest_Rate_Pct"])
                   + ", the EMI moves from " + format_inr_short(low_row["Monthly_EMI"]) + " to "
                   + format_inr_short(high_row["Monthly_EMI"]) + " a month.")
        st.info("Not included: income tax, property tax, loan prepayment, rate changes during the loan. "
                "Results are planning estimates, not advice.")