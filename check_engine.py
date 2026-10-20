"""
Checks for src/financial_engine.py and src/formatting.py.
Run from the project root:   python check_engine.py
Each check compares the engine with an independent calculation or a known answer.
"""
import time

import numpy as np
from scipy.optimize import brentq      # independent root finder, only used for checking

from src.financial_engine import (
    calculate_emi, calculate_upfront_costs, build_amortization_schedule, build_cash_flow_table,
    build_rent_vs_buy, find_breakeven_year, irr_from_cash_flows, npv_from_cash_flows,
    run_full_analysis, build_rate_sensitivity, build_irr_matrix, build_breakeven_matrix,
    check_inputs, down_payment_pct_from_amount, adjust_price_for_growth, get_assumptions,
    STAMP_DUTY_TABLE, ASSUMPTION_META, DEFAULT_ASSUMPTIONS,
)
from src.formatting import (
    format_inr_full, format_inr_short, format_inr_signed, format_pct, format_multiple, format_years,
)

passed = 0


def check(name, condition, detail=""):
    global passed
    if not condition:
        raise AssertionError("FAILED: " + name + " " + str(detail))
    passed += 1
    print("ok  ", name, detail)


def close(x, y, tolerance=1e-6):
    return abs(x - y) <= tolerance * max(1.0, abs(y))


# --- 1. EMI against a known figure and against the closed-form balance ---------------------
emi = calculate_emi(5000000, 8.5, 20)
check("EMI 50 lakh @8.5% x 20y", round(emi) == 43391, round(emi))
check("EMI at 0% interest", close(calculate_emi(1200000, 0, 10), 10000))
check("EMI with no loan", calculate_emi(0, 8.5, 20) == 0.0)

# --- 2. Upfront costs -----------------------------------------------------------------------
up = calculate_upfront_costs(100, 1000, "Mumbai")      # Rs 1 crore
check("Mumbai upfront = 20L + 6L + 30k fee-capped reg + 40k loan fee",
      close(up["total_upfront"], 2000000 + 600000 + 30000 + 40000), up["total_upfront"])
up_override = calculate_upfront_costs(100, 1000, "Delhi", {"govt_charges_override_pct": 8.0})
check("Government charges override", close(up_override["government_charges_total"], 800000))
try:
    get_assumptions({"intrest": 9})
    _raises = False
except ValueError:
    _raises = True
check("Typo in assumption name raises", _raises)

# --- 3. Loan schedule identities --------------------------------------------------------------
schedule = build_amortization_schedule(8000000, 8.5, 20)
check("Schedule: 20 rows", len(schedule) == 20)
check("Schedule: principal repaid = loan", close(schedule["Principal_Paid"].sum(), 8000000))
check("Schedule: final balance 0", schedule["Closing_Balance"].iloc[-1] == 0.0)
check("Schedule: interest = EMI*n - loan",
      close(schedule["Interest_Paid"].sum(), calculate_emi(8000000, 8.5, 20) * 240 - 8000000, 1e-6))

# --- 4. IRR: known answers and an independent solver -----------------------------------------
check("IRR of [-100, 110]", close(irr_from_cash_flows([-100, 110]), 10.0, 1e-9))
check("IRR None when all negative", irr_from_cash_flows([-100, -5, -5]) is None)
flows = [-1000, 50, 60, -20, 80, 1200]
independent = brentq(lambda r: sum(f / (1 + r) ** t for t, f in enumerate(flows)), -0.9, 1.0) * 100
check("IRR matches scipy brentq", close(irr_from_cash_flows(flows), independent, 1e-6), (irr_from_cash_flows(flows), independent))
check("NPV at the IRR is ~0", abs(npv_from_cash_flows(irr_from_cash_flows(flows), flows)) < 1e-4)

# --- 5. Known-answer model test: no rent, no costs, all cash, 5% growth -> IRR 5% ---------------
clean = {"down_payment_pct": 100, "rental_yield_pct": 0, "maintenance_per_sqft_monthly": 0,
         "repairs_reserve_pct": 0, "sale_cost_pct": 0, "govt_charges_override_pct": 0,
         "loan_fee_pct": 0, "property_appreciation_pct": 5.0, "hold_years": 7}
res = run_full_analysis(100, 1000, "Mumbai", clean)
check("All-cash, no costs: unlevered IRR = 5%", close(res["metrics"]["unlevered_irr_pct"], 5.0, 1e-6),
      res["metrics"]["unlevered_irr_pct"])
check("100% down payment: levered = unlevered", close(res["metrics"]["levered_irr_pct"], 5.0, 1e-6))
check("100% down payment: no DSCR / debt yield", res["metrics"]["dscr_year1"] is None and res["metrics"]["debt_yield_pct"] is None)
check("100% down payment: equity multiple = 1.05^7", close(res["metrics"]["levered_equity_multiple"], 1.05 ** 7, 1e-6))

# --- 6. Levered IRR rebuilt by hand (loan, zero rent) -------------------------------------------
loan_case = dict(clean, down_payment_pct=20, loan_fee_pct=0.5, annual_interest_rate_pct=9.0,
                 loan_tenure_years=20, sale_cost_pct=2.0, hold_years=7)
res = run_full_analysis(100, 1000, "Mumbai", loan_case)
price = 10000000.0
loan = 8000000.0
emi = calculate_emi(loan, 9.0, 20)
bal = loan
r = 0.09 / 12
for _ in range(84):
    bal = bal * (1 + r) - emi                      # balance after 84 payments
sale = price * 1.05 ** 7
hand_flows = [-(price - loan) - loan * 0.005] + [-emi * 12] * 6 + [-emi * 12 + sale * 0.98 - bal]
hand_irr = brentq(lambda x: sum(f / (1 + x) ** t for t, f in enumerate(hand_flows)), -0.9, 1.0) * 100
check("Levered IRR equals the hand-built calculation", close(res["metrics"]["levered_irr_pct"], hand_irr, 1e-6),
      (res["metrics"]["levered_irr_pct"], hand_irr))
check("Loan balance at exit matches closed form", close(res["metrics"]["loan_payoff_at_sale"], bal, 1e-6))

# --- 7. Cash-flow table internal consistency -------------------------------------------------
res = run_full_analysis(100, 1200, "Bangalore")
table = res["cash_flow_table"]
check("Table: Net_Rent + costs = NOI", np.allclose(table["Net_Rent"] + table["Maintenance"] + table["Repairs_Reserve"], table["NOI"]))
check("Table: levered month 0 = - equity", close(table["Levered_CF"].iloc[0], -res["metrics"]["equity_invested"]))
check("Equity invested = total upfront cash", close(res["metrics"]["equity_invested"], res["upfront"]["total_upfront"]))
check("Table rows = 1 + 12 * hold years", len(table) == 1 + 12 * 7)
check("Annual rows = 1 + hold years", len(res["annual"]) == 8)
check("Rent steps up each year", table[table["Year"] == 2]["Gross_Rent"].iloc[0] > table[table["Year"] == 1]["Gross_Rent"].iloc[0])

# --- 8. Rent vs buy invariant ------------------------------------------------------------------
zero = {"rental_yield_pct": 0.0, "rent_growth_pct": 0, "maintenance_per_sqft_monthly": 0,
        "property_appreciation_pct": 0, "market_return_pct": 0, "projection_years": 20}
path = build_rent_vs_buy(100, 1000, "Chennai", zero)
upz = calculate_upfront_costs(100, 1000, "Chennai", zero)
interest_total = calculate_emi(upz["loan_amount"], 8.5, 20) * 240 - upz["loan_amount"]
gap20 = path["Net_Worth_Renting"].iloc[-1] - path["Net_Worth_Buying"].iloc[-1]
check("Rent vs buy, everything flat: renter's lead = govt charges + loan fee + interest",
      close(gap20, upz["government_charges_total"] + upz["loan_fee"] + interest_total, 1e-6), round(gap20))
check("Rent vs buy columns", list(path.columns) == ["Year", "Net_Worth_Buying", "Net_Worth_Renting", "Home_Value", "Loan_Balance"])
check("Rent vs buy rows = 21", len(path) == 21)

# --- 9. Directional checks (the model should move the right way) -------------------------------
sens = build_rate_sensitivity(100, 1200, "Bangalore")
check("EMI rises with rate", sens["Monthly_EMI"].is_monotonic_increasing)
check("Levered IRR falls as rate rises", sens["Levered_IRR_Pct"].is_monotonic_decreasing)
check("DSCR falls as rate rises", sens["DSCR"].is_monotonic_decreasing)
matrix = build_irr_matrix(100, 1200, "Bangalore")
check("IRR matrix: rises with price growth (down each column)", all(matrix[c].is_monotonic_increasing for c in matrix.columns))
check("IRR matrix: falls with loan rate (along each row)", all(matrix.loc[i].is_monotonic_decreasing for i in matrix.index))
bem = build_breakeven_matrix(100, 1200, "Bangalore")
earlier_with_growth = all(bem[c].fillna(99).is_monotonic_decreasing for c in bem.columns)
check("Breakeven comes earlier (or equal) with higher price growth", earlier_with_growth)

# --- 10. Warnings, helpers, cities ---------------------------------------------------------------
check("Warning for 95% loan", len(check_inputs(100, 1000, "Mumbai", {"down_payment_pct": 5})) == 1)
check("Warns at 20% down on 1 crore (80L loan is above the 75% cap for loans over 75L)",
      len(check_inputs(100, 1000, "Mumbai", {"down_payment_pct": 20})) == 1)
check("No warning at 25% down on 1 crore", check_inputs(100, 1000, "Mumbai", {"down_payment_pct": 25}) == [])
check("Down payment helper", close(down_payment_pct_from_amount(100, 3000000), 30.0))
check("Growth adjustment", close(adjust_price_for_growth(100, 5, 6), 100 * 1.05 ** 6))
check("Slider metadata keys exist in defaults", all(k in DEFAULT_ASSUMPTIONS for k in ASSUMPTION_META))
for city in STAMP_DUTY_TABLE:
    out = run_full_analysis(75, 1000, city)
    check("City runs: " + city,
          out["upfront"]["total_upfront"] > out["upfront"]["down_payment"] and len(out["rent_vs_buy"]) == 21,
          format_pct(out["metrics"]["levered_irr_pct"]))

# --- 11. Speed (the app reruns this on every slider move) ----------------------------------------
start = time.time()
for _ in range(5):
    run_full_analysis(100, 1200, "Bangalore")
per_run = (time.time() - start) / 5
check("run_full_analysis is fast enough for a slider", per_run < 1.0, str(round(per_run * 1000)) + " ms per run")

# --- 12. Formatting ------------------------------------------------------------------------------
check("format full", format_inr_full(8550000) == "₹85,50,000" and format_inr_full(123) == "₹123"
      and format_inr_full(100000000) == "₹10,00,00,000" and format_inr_full(-1234567) == "-₹12,34,567")
check("format short", format_inr_short(14500000) == "₹1.45 Cr" and format_inr_short(8550000) == "₹85.50 L"
      and format_inr_short(-250000) == "-₹2.50 L" and format_inr_short(99999) == "₹99,999")
check("format signed", format_inr_signed(250000) == "+₹2.50 L" and format_inr_signed(-250000) == "-₹2.50 L")
check("format None-safe", format_inr_full(None) == "n/a" and format_pct(None) == "n/a" and format_multiple(float("nan")) == "n/a")
check("format pct, multiple, years", format_pct(6.0595) == "6.06%" and format_multiple(1.524) == "1.52x"
      and format_years(None) == "Not within the period" and format_years(7) == "Year 7")

print("\nAll", passed, "checks passed.")

# --- Show a sample result so you can eyeball it -----------------------------------------------
res = run_full_analysis(100, 1200, "Bangalore")
m = res["metrics"]
print("\nSample: Rs 1 crore, 1200 sq ft, Bangalore, defaults")
print("Total upfront cash :", format_inr_short(res["upfront"]["total_upfront"]))
print("Monthly EMI        :", format_inr_full(res["monthly"]["emi"]))
print("Net monthly cash flow if rented out :", format_inr_signed(res["monthly"]["net_monthly_cash_flow_rented"]))
print("Unlevered IRR      :", format_pct(m["unlevered_irr_pct"]))
print("Levered IRR        :", format_pct(m["levered_irr_pct"]))
print("Levered multiple   :", format_multiple(m["levered_equity_multiple"]))
print("Levered NPV @10%   :", format_inr_signed(m["levered_npv"]))
print("DSCR year 1        :", None if m["dscr_year1"] is None else round(m["dscr_year1"], 2))
print("Going-in cap rate  :", format_pct(m["going_in_cap_rate_pct"]))
print("Break-even rent    :", format_inr_full(m["break_even_gross_monthly_rent"]), "per month (yours:", format_inr_full(res["monthly"]["gross_monthly_rent"]) + ")")
print("Rent-vs-buy        :", format_years(res["breakeven_year"]))
print("\nLevered IRR (%) by price growth (rows) and loan rate (columns):")
print(res["irr_matrix"].round(1))
print("\nBreakeven year, price growth (rows) x market return (columns); NaN = never:")
print(bem)
