"""
Financial engine for the Indian house price simulator.

Pure Python + pandas. No Streamlit and no ML code, so it can be tested alone.
Money is in RUPEES everywhere, except arguments/keys that say "lakhs".
Percent inputs are plain percents (8.5 means 8.5%).

SIGN CONVENTION in the cash-flow tables: money you receive is positive, money
you pay out is negative, so every "total" column is a simple sum of the columns before it.

WHAT IT DOES (modelled on a professional deal model, adapted to Indian housing)
    1. Upfront costs: down payment, stamp duty + registration, loan fee, renovation.
    2. A monthly cash-flow table for the holding period: rent, vacancy, maintenance,
       repairs reserve, EMI split into principal and interest, then the sale
       (sale price, selling costs, loan payoff).
    3. Return metrics: unlevered IRR (no loan), levered IRR (return on YOUR cash,
       with the loan), equity multiple, NPV, cash-on-cash, DSCR, cap rate, debt yield.
    4. A 20-year rent-vs-buy projection and its breakeven year.
    5. Sensitivity tables (interest rate, price growth, market return).

DEFAULTS AND WHY (all editable through `assumptions`; see DEFAULT_ASSUMPTIONS)
    - Loan 80% of the price (down payment 20%), 8.5% for 20 years, 0.5% processing fee.
      Banks advertise starting rates of about 7.1-7.9% for strong credit profiles;
      8.5% is a more conservative middle value. Processing fees vary by lender.
    - RBI limits the loan-to-value ratio: 90% of value for loans up to Rs 30 lakh,
      80% for Rs 30-75 lakh, 75% above Rs 75 lakh (see check_inputs).
    - Rental yield 3% of the price per year (typical Indian range 2.5-3.5%).
    - Vacancy 8% (about one month a year), rent and maintenance grow 5% a year.
    - Society maintenance Rs 3.5 per sq ft per month, repairs reserve 1% of rent.
    - Property price growth 5% a year, selling cost 2% (brokerage and similar).
    - Market return 12% a year (a Nifty-50-style index fund, before tax) for rent-vs-buy.
    - Discount rate for NPV 10%.

NOT MODELLED: income tax (home-loan interest deduction, tax on rent, capital gains),
property tax, GST on under-construction flats, loan prepayment, floating-rate changes
during the loan, brokerage when buying, women's stamp-duty concessions. Results are
planning estimates, not financial advice.
"""

import pandas as pd


# ----------------------------------------------------------------------------
# 1. Default assumptions and slider metadata
# ----------------------------------------------------------------------------
DEFAULT_ASSUMPTIONS = {
    # loan
    "down_payment_pct": 20.0,
    "annual_interest_rate_pct": 8.5,
    "loan_tenure_years": 20,
    "loan_fee_pct": 0.5,
    # purchase
    "govt_charges_override_pct": None,   # None = use the city table; a number = total % to use
    "capex_per_sqft": 0.0,               # interior / renovation cost per sq ft on day 0
    # renting it out, and running costs
    "rental_yield_pct": 3.0,
    "rent_growth_pct": 5.0,
    "vacancy_pct": 8.0,
    "maintenance_per_sqft_monthly": 3.5,
    "maintenance_growth_pct": 5.0,
    "repairs_reserve_pct": 1.0,          # % of net rent set aside for repairs
    # selling
    "hold_years": 7,
    "property_appreciation_pct": 5.0,
    "sale_cost_pct": 2.0,
    # valuation and rent-vs-buy
    "discount_rate_pct": 10.0,
    "market_return_pct": 12.0,
    "projection_years": 20,
    "deduct_sale_cost_in_net_worth": False,
}

# One entry per slider the app can show: label, group, min, max, step, help text.
ASSUMPTION_GROUPS = ["Loan", "Purchase", "Rent and running costs", "Selling", "Valuation and comparison"]

ASSUMPTION_META = {
    "down_payment_pct": {"label": "Down payment (%)", "group": "Loan", "min": 10.0, "max": 100.0, "step": 1.0,
                         "help": "Your own money as a share of the price. 100 means no loan."},
    "annual_interest_rate_pct": {"label": "Loan interest rate (%)", "group": "Loan", "min": 5.0, "max": 14.0,
                                 "step": 0.05, "help": "Yearly rate. Repo-linked rates change over time."},
    "loan_tenure_years": {"label": "Loan tenure (years)", "group": "Loan", "min": 5, "max": 30, "step": 1,
                          "help": "Length of the loan."},
    "loan_fee_pct": {"label": "Loan processing fee (% of loan)", "group": "Loan", "min": 0.0, "max": 2.0,
                     "step": 0.05, "help": "Paid to the lender on day 0, usually 0.25-1%."},
    "capex_per_sqft": {"label": "Renovation / interiors (Rs per sq ft)", "group": "Purchase", "min": 0.0,
                       "max": 3000.0, "step": 50.0, "help": "One-time cost on day 0 for a bare-shell flat."},
    "rental_yield_pct": {"label": "Gross rental yield (% of price per year)", "group": "Rent and running costs",
                         "min": 1.0, "max": 6.0, "step": 0.1, "help": "Typical Indian range is 2.5-3.5%."},
    "rent_growth_pct": {"label": "Rent growth (% per year)", "group": "Rent and running costs", "min": 0.0,
                        "max": 10.0, "step": 0.5, "help": "Rent steps up once a year."},
    "vacancy_pct": {"label": "Vacancy (% of the year empty)", "group": "Rent and running costs", "min": 0.0,
                    "max": 30.0, "step": 1.0, "help": "8% is about one empty month a year."},
    "maintenance_per_sqft_monthly": {"label": "Society maintenance (Rs per sq ft per month)",
                                     "group": "Rent and running costs", "min": 0.0, "max": 15.0, "step": 0.5,
                                     "help": "Paid by the owner every month."},
    "maintenance_growth_pct": {"label": "Maintenance growth (% per year)", "group": "Rent and running costs",
                               "min": 0.0, "max": 10.0, "step": 0.5, "help": "Yearly increase in maintenance."},
    "repairs_reserve_pct": {"label": "Repairs reserve (% of rent)", "group": "Rent and running costs",
                            "min": 0.0, "max": 10.0, "step": 0.5, "help": "Money set aside for repairs."},
    "hold_years": {"label": "Holding period (years)", "group": "Selling", "min": 1, "max": 20, "step": 1,
                   "help": "Years before selling. Used for IRR, NPV and the cash-flow table."},
    "property_appreciation_pct": {"label": "Property price growth (% per year)", "group": "Selling",
                                  "min": -5.0, "max": 15.0, "step": 0.5,
                                  "help": "The biggest driver of results. This is an assumption."},
    "sale_cost_pct": {"label": "Selling cost (% of sale price)", "group": "Selling", "min": 0.0, "max": 5.0,
                      "step": 0.25, "help": "Brokerage and other costs when you sell."},
    "discount_rate_pct": {"label": "Discount rate for NPV (%)", "group": "Valuation and comparison",
                          "min": 5.0, "max": 20.0, "step": 0.5,
                          "help": "The return you could get elsewhere. NPV above 0 beats it."},
    "market_return_pct": {"label": "Stock market return (% per year)", "group": "Valuation and comparison",
                          "min": 4.0, "max": 20.0, "step": 0.5,
                          "help": "Used for the renter's investments in rent-vs-buy. Before tax, not guaranteed."},
}


# ----------------------------------------------------------------------------
# 2. Stamp duty and registration by city (residential flat, default buyer)
#    Sources for 2026 disagree in several places, so these are estimates.
#    Check the state registration portal before relying on them.
# ----------------------------------------------------------------------------
STAMP_DUTY_TABLE = {
    # Mumbai: 5% stamp duty + 1% metro cess; registration 1% capped at Rs 30,000.
    "Mumbai": {"stamp_pct": 6.0, "registration_pct": 1.0, "other_pct": 0.0, "registration_cap": 30000},

    # Delhi: 6% stamp duty + 1% registration. One source adds a 1% MCD transfer duty
    # above Rs 25 lakh (not included). The "Delhi" data also holds Noida (Uttar Pradesh),
    # which costs more (about 8%): use govt_charges_override_pct for those.
    "Delhi": {"stamp_pct": 6.0, "registration_pct": 1.0, "other_pct": 0.0, "registration_cap": None},

    # Bangalore: 5% duty + cess + surcharge = 5.6% (homes above about Rs 45 lakh; cheaper
    # flats pay a lower slab, so this overestimates them) + registration 2% (revised Aug 2025).
    "Bangalore": {"stamp_pct": 5.6, "registration_pct": 2.0, "other_pct": 0.0, "registration_cap": None},

    # Hyderabad: sources conflict. 5.5% + 1.5% transfer duty + 0.5% registration = 7.5%
    # (cites a 2021 government order); several blogs say 4% + 1.5% + 0.5% = 6%.
    "Hyderabad": {"stamp_pct": 5.5, "registration_pct": 0.5, "other_pct": 1.5, "registration_cap": None},

    # Chennai: 7% stamp + 4% registration = 11% (most sources); two sources say 2% registration.
    "Chennai": {"stamp_pct": 7.0, "registration_pct": 4.0, "other_pct": 0.0, "registration_cap": None},

    # Kolkata: about 6% stamp + 1% registration. Some sources say 7% above Rs 1 crore.
    "Kolkata": {"stamp_pct": 6.0, "registration_pct": 1.0, "other_pct": 0.0, "registration_cap": None},
}


def get_assumptions(overrides: dict = None) -> dict:
    """Defaults, replaced by any overrides. An unknown key raises an error (catches typos)."""
    assumptions = dict(DEFAULT_ASSUMPTIONS)      # copy, so the defaults never change
    if overrides is not None:
        for key in overrides:
            if key not in DEFAULT_ASSUMPTIONS:
                raise ValueError("Unknown assumption: " + str(key))
        assumptions.update(overrides)
    return assumptions


# ----------------------------------------------------------------------------
# 3. Small helpers for the app
# ----------------------------------------------------------------------------
def adjust_price_for_growth(price_lakhs: float, annual_growth_pct: float, years: float) -> float:
    """Move a model price forward in time: price * (1 + growth)^years. Used for the 2026 estimate."""
    return price_lakhs * (1 + annual_growth_pct / 100) ** years


def down_payment_pct_from_amount(price_lakhs: float, down_payment_rupees: float) -> float:
    """Turn 'I have Rs 30 lakh' into a percent of the price, kept between 0 and 100."""
    price = price_lakhs * 100000
    if price <= 0:
        return 0.0
    pct = down_payment_rupees / price * 100
    return max(0.0, min(100.0, pct))


def max_ltv_pct_for_loan(loan_amount_rupees: float) -> float:
    """RBI loan-to-value cap by loan size: 90% up to Rs 30 lakh, 80% to Rs 75 lakh, else 75%."""
    if loan_amount_rupees <= 3000000:
        return 90.0
    if loan_amount_rupees <= 7500000:
        return 80.0
    return 75.0


def check_inputs(property_price_lakhs: float, area_sqft: float, city: str,
                 assumptions: dict = None) -> list:
    """Return a list of warning texts (empty list = nothing suspicious)."""
    a = get_assumptions(assumptions)
    warnings = []

    if city not in STAMP_DUTY_TABLE:
        warnings.append("No stamp duty data for " + str(city) + ".")
    if property_price_lakhs <= 0 or area_sqft <= 0:
        warnings.append("Price and area must be above zero.")
        return warnings

    price = property_price_lakhs * 100000
    loan = price * (1 - a["down_payment_pct"] / 100)
    loan_pct = loan / price * 100
    cap = max_ltv_pct_for_loan(loan)
    if loan_pct > cap + 1e-9:
        warnings.append("A loan of " + format(loan_pct, ".0f") + "% of the price is above the usual RBI limit of "
                        + format(cap, ".0f") + "% for a loan this size. Banks may ask for a bigger down payment.")
    if a["hold_years"] > a["projection_years"]:
        warnings.append("Holding period is longer than the projection period.")
    return warnings


# ----------------------------------------------------------------------------
# 4. Loan maths
# ----------------------------------------------------------------------------
def calculate_emi(loan_amount: float, annual_rate_pct: float, tenure_years: float) -> float:
    """Monthly EMI = P * r * (1+r)^n / ((1+r)^n - 1), r = monthly rate, n = months."""
    months = int(round(tenure_years * 12))
    if loan_amount <= 0 or months <= 0:
        return 0.0

    monthly_rate = annual_rate_pct / 100 / 12
    if monthly_rate == 0:                        # zero interest: just divide equally
        return loan_amount / months

    growth = (1 + monthly_rate) ** months
    return loan_amount * monthly_rate * growth / (growth - 1)


def _loan_schedule(loan_amount: float, annual_rate_pct: float, tenure_years: float):
    """Monthly schedule as three lists (month 1 first): interest, principal, closing balance."""
    months = int(round(tenure_years * 12))
    if loan_amount <= 0 or months <= 0:
        return [0.0] * max(months, 0), [0.0] * max(months, 0), [0.0] * max(months, 0)

    emi = calculate_emi(loan_amount, annual_rate_pct, tenure_years)
    monthly_rate = annual_rate_pct / 100 / 12

    interest_list = []
    principal_list = []
    balance_list = []
    balance = loan_amount

    for month in range(months):
        interest = balance * monthly_rate
        principal = emi - interest
        if principal > balance:                   # the last payment cannot exceed what is owed
            principal = balance
        balance = balance - principal
        if balance < 0.01:
            balance = 0.0
        interest_list.append(interest)
        principal_list.append(principal)
        balance_list.append(balance)

    return interest_list, principal_list, balance_list


def build_amortization_schedule(loan_amount: float, annual_rate_pct: float,
                                tenure_years: float) -> pd.DataFrame:
    """One row per year: Year, Principal_Paid, Interest_Paid, Closing_Balance (for the stacked bar)."""
    interest_list, principal_list, balance_list = _loan_schedule(loan_amount, annual_rate_pct, tenure_years)

    rows = []
    months = len(balance_list)
    for start in range(0, months, 12):
        end = min(start + 12, months)
        rows.append({
            "Year": start // 12 + 1,
            "Principal_Paid": sum(principal_list[start:end]),
            "Interest_Paid": sum(interest_list[start:end]),
            "Closing_Balance": balance_list[end - 1],
        })
    return pd.DataFrame(rows, columns=["Year", "Principal_Paid", "Interest_Paid", "Closing_Balance"])


# ----------------------------------------------------------------------------
# 5. IRR and NPV
# ----------------------------------------------------------------------------
def npv_from_cash_flows(rate_pct: float, cash_flows: list) -> float:
    """Net present value of yearly cash flows. The first one is year 0 (today)."""
    rate = rate_pct / 100
    total = 0.0
    for year in range(len(cash_flows)):
        total += cash_flows[year] / (1 + rate) ** year
    return total


def irr_from_cash_flows(cash_flows: list):
    """
    IRR in percent, found by bisection (keep halving the search range).
    Searches between -99% and +100%. Returns None when there is no answer there
    (for example when every cash flow is negative).
    """
    low = -0.99
    high = 1.0
    npv_low = npv_from_cash_flows(low * 100, cash_flows)
    npv_high = npv_from_cash_flows(high * 100, cash_flows)
    if npv_low * npv_high > 0:                    # same sign at both ends: no root in this range
        return None

    for step in range(200):
        middle = (low + high) / 2
        npv_middle = npv_from_cash_flows(middle * 100, cash_flows)
        if npv_low * npv_middle > 0:
            low = middle
            npv_low = npv_middle
        else:
            high = middle
    return (low + high) / 2 * 100


# ----------------------------------------------------------------------------
# 6. Upfront costs (day 0)
# ----------------------------------------------------------------------------
def calculate_upfront_costs(property_price_lakhs: float, area_sqft: float,
                            city: str, assumptions: dict = None) -> dict:
    """
    Cash needed on day 0 = down payment + stamp duty + registration + other
    government charges + loan processing fee + renovation.
    """
    a = get_assumptions(assumptions)

    price = property_price_lakhs * 100000              # lakhs -> rupees
    down_payment = price * a["down_payment_pct"] / 100
    loan_amount = price - down_payment
    loan_fee = loan_amount * a["loan_fee_pct"] / 100

    if a["govt_charges_override_pct"] is not None:
        stamp_duty = price * a["govt_charges_override_pct"] / 100
        registration = 0.0
        other_charges = 0.0
        rate_source = "override"
    else:
        if city not in STAMP_DUTY_TABLE:
            raise ValueError("No stamp duty data for city: " + str(city))
        rates = STAMP_DUTY_TABLE[city]
        stamp_duty = price * rates["stamp_pct"] / 100
        registration = price * rates["registration_pct"] / 100
        if rates["registration_cap"] is not None and registration > rates["registration_cap"]:
            registration = rates["registration_cap"]   # e.g. Mumbai caps at Rs 30,000
        other_charges = price * rates["other_pct"] / 100
        rate_source = "city table"

    capex = area_sqft * a["capex_per_sqft"]
    government_charges = stamp_duty + registration + other_charges
    total_upfront = down_payment + government_charges + loan_fee + capex

    return {
        "property_price": price,
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "loan_fee": loan_fee,
        "stamp_duty": stamp_duty,
        "registration": registration,
        "other_government_charges": other_charges,
        "government_charges_total": government_charges,
        "government_charges_pct": government_charges / price * 100 if price > 0 else 0.0,
        "government_rate_source": rate_source,
        "capex": capex,
        "total_upfront": total_upfront,
    }


# ----------------------------------------------------------------------------
# 7. Monthly cash-flow table (the heart of the model)
# ----------------------------------------------------------------------------
CASH_FLOW_COLUMNS = [
    "Month", "Year", "Gross_Rent", "Vacancy_Loss", "Net_Rent", "Maintenance", "Repairs_Reserve", "NOI",
    "Principal", "Interest", "Cash_Flow_After_Debt", "Purchase_Outlay", "Sale_Proceeds", "Sale_Costs",
    "Loan_Proceeds", "Loan_Fee", "Loan_Payoff", "Unlevered_CF", "Levered_CF",
]


def build_cash_flow_table(property_price_lakhs: float, area_sqft: float, city: str,
                          assumptions: dict = None) -> pd.DataFrame:
    """
    Month 0 (purchase) plus one row per month of the holding period. The sale happens
    in the last month. Rent and maintenance step up once a year.
      NOI = Net_Rent + Maintenance + Repairs_Reserve      (costs are negative)
      Unlevered_CF = NOI + purchase + sale                 (what you would earn with no loan)
      Levered_CF   = Unlevered_CF + loan proceeds, fee, payments and payoff (what YOU earn)
    """
    a = get_assumptions(assumptions)
    up = calculate_upfront_costs(property_price_lakhs, area_sqft, city, a)

    price = up["property_price"]
    hold_months = int(a["hold_years"]) * 12
    interest_list, principal_list, balance_list = _loan_schedule(
        up["loan_amount"], a["annual_interest_rate_pct"], a["loan_tenure_years"])

    gross_rent_year1 = price * a["rental_yield_pct"] / 100 / 12
    maintenance_year1 = area_sqft * a["maintenance_per_sqft_monthly"]

    # month 0: you pay for the flat and the loan arrives
    purchase_outlay = -(price + up["government_charges_total"] + up["capex"])
    rows = [{
        "Month": 0, "Year": 0, "Gross_Rent": 0.0, "Vacancy_Loss": 0.0, "Net_Rent": 0.0, "Maintenance": 0.0,
        "Repairs_Reserve": 0.0, "NOI": 0.0, "Principal": 0.0, "Interest": 0.0, "Cash_Flow_After_Debt": 0.0,
        "Purchase_Outlay": purchase_outlay, "Sale_Proceeds": 0.0, "Sale_Costs": 0.0,
        "Loan_Proceeds": up["loan_amount"], "Loan_Fee": -up["loan_fee"], "Loan_Payoff": 0.0,
        "Unlevered_CF": purchase_outlay,
        "Levered_CF": purchase_outlay + up["loan_amount"] - up["loan_fee"],
    }]

    for month in range(1, hold_months + 1):
        year = (month - 1) // 12 + 1
        gross_rent = gross_rent_year1 * (1 + a["rent_growth_pct"] / 100) ** (year - 1)
        maintenance = maintenance_year1 * (1 + a["maintenance_growth_pct"] / 100) ** (year - 1)

        vacancy_loss = -gross_rent * a["vacancy_pct"] / 100
        net_rent = gross_rent + vacancy_loss
        repairs = -net_rent * a["repairs_reserve_pct"] / 100
        noi = net_rent - maintenance + repairs

        if month <= len(balance_list):
            principal = principal_list[month - 1]
            interest = interest_list[month - 1]
        else:
            principal = 0.0
            interest = 0.0
        after_debt = noi - principal - interest

        sale_proceeds = 0.0
        sale_costs = 0.0
        loan_payoff = 0.0
        if month == hold_months:                  # sell in the last month of the hold
            sale_proceeds = price * (1 + a["property_appreciation_pct"] / 100) ** a["hold_years"]
            sale_costs = -sale_proceeds * a["sale_cost_pct"] / 100
            if month <= len(balance_list):
                loan_payoff = -balance_list[month - 1]

        unlevered = noi + sale_proceeds + sale_costs
        levered = after_debt + sale_proceeds + sale_costs + loan_payoff

        rows.append({
            "Month": month, "Year": year, "Gross_Rent": gross_rent, "Vacancy_Loss": vacancy_loss,
            "Net_Rent": net_rent, "Maintenance": -maintenance, "Repairs_Reserve": repairs, "NOI": noi,
            "Principal": -principal, "Interest": -interest, "Cash_Flow_After_Debt": after_debt,
            "Purchase_Outlay": 0.0, "Sale_Proceeds": sale_proceeds, "Sale_Costs": sale_costs,
            "Loan_Proceeds": 0.0, "Loan_Fee": 0.0, "Loan_Payoff": loan_payoff,
            "Unlevered_CF": unlevered, "Levered_CF": levered,
        })

    return pd.DataFrame(rows, columns=CASH_FLOW_COLUMNS)


def build_annual_summary(cash_flow_table: pd.DataFrame) -> pd.DataFrame:
    """Add the monthly rows up into one row per year (year 0 = purchase). Adds cash-on-cash %."""
    annual = cash_flow_table.drop(columns=["Month"]).groupby("Year", as_index=False).sum()

    equity = -annual["Levered_CF"].iloc[0]                # cash you put in on day 0
    all_cash = -annual["Unlevered_CF"].iloc[0]            # cash needed with no loan

    # cash-on-cash = yearly cash flow from running the flat (not the sale) / money invested
    annual["Cash_on_Cash_Levered_Pct"] = 0.0
    annual["Cash_on_Cash_Unlevered_Pct"] = 0.0
    if equity > 0:
        annual["Cash_on_Cash_Levered_Pct"] = annual["Cash_Flow_After_Debt"] / equity * 100
    if all_cash > 0:
        annual["Cash_on_Cash_Unlevered_Pct"] = annual["NOI"] / all_cash * 100
    return annual


# ----------------------------------------------------------------------------
# 8. Return metrics
# ----------------------------------------------------------------------------
def _metrics_from_tables(up: dict, cash_flow_table: pd.DataFrame, annual: pd.DataFrame, a: dict,
                         area_sqft: float) -> dict:
    """All headline numbers from the tables already built. Internal helper."""
    unlevered_flows = annual["Unlevered_CF"].tolist()
    levered_flows = annual["Levered_CF"].tolist()
    equity = -levered_flows[0]
    all_cash = -unlevered_flows[0]

    year1 = annual[annual["Year"] == 1].iloc[0]
    noi_year1 = year1["NOI"]
    debt_service_year1 = -(year1["Principal"] + year1["Interest"])
    net_rent_year1 = year1["Net_Rent"]

    sale_row = cash_flow_table.iloc[-1]
    sale_value = sale_row["Sale_Proceeds"]
    loan_payoff = -sale_row["Loan_Payoff"]
    loan = up["loan_amount"]

    emi = calculate_emi(loan, a["annual_interest_rate_pct"], a["loan_tenure_years"])
    maintenance_year1 = area_sqft * a["maintenance_per_sqft_monthly"]
    keep_share = (1 - a["vacancy_pct"] / 100) * (1 - a["repairs_reserve_pct"] / 100)
    break_even_rent = None
    if keep_share > 0:
        break_even_rent = (emi + maintenance_year1) / keep_share      # gross monthly rent so that cash flow = 0

    levered_years = levered_flows[1:]
    unlevered_years = unlevered_flows[1:]

    return {
        "equity_invested": equity,
        "all_cash_invested": all_cash,
        "loan_amount": loan,
        "sale_value": sale_value,
        "sale_costs": -sale_row["Sale_Costs"],
        "loan_payoff_at_sale": loan_payoff,
        "unlevered_irr_pct": irr_from_cash_flows(unlevered_flows),
        "levered_irr_pct": irr_from_cash_flows(levered_flows),
        "unlevered_equity_multiple": sum(unlevered_years) / all_cash if all_cash > 0 else None,
        "levered_equity_multiple": sum(levered_years) / equity if equity > 0 else None,
        "unlevered_total_profit": sum(unlevered_flows),
        "levered_total_profit": sum(levered_flows),
        "avg_cash_on_cash_levered_pct": annual["Cash_on_Cash_Levered_Pct"].iloc[1:].mean(),
        "avg_cash_on_cash_unlevered_pct": annual["Cash_on_Cash_Unlevered_Pct"].iloc[1:].mean(),
        "unlevered_npv": npv_from_cash_flows(a["discount_rate_pct"], unlevered_flows),
        "levered_npv": npv_from_cash_flows(a["discount_rate_pct"], levered_flows),
        "going_in_cap_rate_pct": noi_year1 / (up["property_price"] + up["government_charges_total"] + up["capex"]) * 100,
        "dscr_year1": noi_year1 / debt_service_year1 if debt_service_year1 > 0 else None,
        "debt_yield_pct": noi_year1 / loan * 100 if loan > 0 else None,
        "exit_ltv_pct": loan_payoff / sale_value * 100 if sale_value > 0 else None,
        "opex_ratio_pct": (-year1["Maintenance"] - year1["Repairs_Reserve"]) / net_rent_year1 * 100
                          if net_rent_year1 > 0 else None,
        "break_even_gross_monthly_rent": break_even_rent,
    }


def calculate_monthly_costs(property_price_lakhs: float, area_sqft: float, city: str,
                            assumptions: dict = None) -> dict:
    """Year-1 monthly numbers for the cards: EMI, maintenance, rent and cash flow."""
    a = get_assumptions(assumptions)
    up = calculate_upfront_costs(property_price_lakhs, area_sqft, city, a)
    emi = calculate_emi(up["loan_amount"], a["annual_interest_rate_pct"], a["loan_tenure_years"])
    maintenance = area_sqft * a["maintenance_per_sqft_monthly"]

    gross_rent = up["property_price"] * a["rental_yield_pct"] / 100 / 12
    net_rent = gross_rent * (1 - a["vacancy_pct"] / 100)
    repairs = net_rent * a["repairs_reserve_pct"] / 100
    noi = net_rent - maintenance - repairs

    return {
        "emi": emi,
        "maintenance": maintenance,
        "gross_monthly_rent": gross_rent,
        "expected_monthly_rent": net_rent,
        "repairs_reserve": repairs,
        "monthly_noi": noi,
        "net_monthly_cash_flow_rented": noi - emi,
        "monthly_outflow_self_occupied": emi + maintenance,
    }


# ----------------------------------------------------------------------------
# 9. Rent vs buy
# ----------------------------------------------------------------------------
def build_rent_vs_buy(property_price_lakhs: float, area_sqft: float, city: str,
                      assumptions: dict = None) -> pd.DataFrame:
    """
    Two people start with the same cash (the total upfront outflow).
      Buyer : buys the flat, pays EMI and maintenance (you live in it).
              Net worth = home value - loan balance + money invested on the side.
      Renter: puts the cash in the market and pays rent (the same rent the flat would earn,
              growing every year). Net worth = the investment pot.
    Every month, whoever pays less invests the difference in the market.
    Columns: Year, Net_Worth_Buying, Net_Worth_Renting, Home_Value, Loan_Balance.
    """
    a = get_assumptions(assumptions)
    up = calculate_upfront_costs(property_price_lakhs, area_sqft, city, a)

    price = up["property_price"]
    loan = up["loan_amount"]
    interest_list, principal_list, balance_list = _loan_schedule(
        loan, a["annual_interest_rate_pct"], a["loan_tenure_years"])
    market_monthly = (1 + a["market_return_pct"] / 100) ** (1 / 12) - 1

    def sellable_value(home_value):
        # optionally take the selling cost off the home value
        if a["deduct_sale_cost_in_net_worth"]:
            return home_value * (1 - a["sale_cost_pct"] / 100)
        return home_value

    rent_now = price * a["rental_yield_pct"] / 100 / 12
    maintenance_now = area_sqft * a["maintenance_per_sqft_monthly"]
    renter_pot = up["total_upfront"]
    buyer_pot = 0.0
    balance = loan

    rows = [{"Year": 0, "Net_Worth_Buying": sellable_value(price) - balance,
             "Net_Worth_Renting": renter_pot, "Home_Value": price, "Loan_Balance": balance}]

    for month in range(1, int(a["projection_years"]) * 12 + 1):
        if month <= len(balance_list):
            emi_paid = principal_list[month - 1] + interest_list[month - 1]
            balance = balance_list[month - 1]
        else:
            emi_paid = 0.0
            balance = 0.0

        renter_pot = renter_pot * (1 + market_monthly)       # both pots grow one month
        buyer_pot = buyer_pot * (1 + market_monthly)

        gap = emi_paid + maintenance_now - rent_now           # whoever pays less invests the gap
        if gap > 0:
            renter_pot += gap
        else:
            buyer_pot += -gap

        if month % 12 == 0:
            year = month // 12
            home_value = price * (1 + a["property_appreciation_pct"] / 100) ** year
            rows.append({"Year": year,
                         "Net_Worth_Buying": sellable_value(home_value) - balance + buyer_pot,
                         "Net_Worth_Renting": renter_pot,
                         "Home_Value": home_value, "Loan_Balance": balance})
            rent_now *= 1 + a["rent_growth_pct"] / 100
            maintenance_now *= 1 + a["maintenance_growth_pct"] / 100

    return pd.DataFrame(rows)


def find_breakeven_year(rent_vs_buy: pd.DataFrame):
    """First year after year 0 in which buying is ahead of renting, or None if it never is."""
    for position in range(1, len(rent_vs_buy)):
        if rent_vs_buy["Net_Worth_Buying"].iloc[position] >= rent_vs_buy["Net_Worth_Renting"].iloc[position]:
            return int(rent_vs_buy["Year"].iloc[position])
    return None


# ----------------------------------------------------------------------------
# 10. Sensitivity tables
# ----------------------------------------------------------------------------
def _with(a: dict, **changes) -> dict:
    """Copy of the assumptions with a few values changed."""
    new_a = dict(a)
    new_a.update(changes)
    return new_a


def build_rate_sensitivity(property_price_lakhs: float, area_sqft: float, city: str,
                           assumptions: dict = None, rates: list = None) -> pd.DataFrame:
    """How EMI, total interest, rented cash flow, DSCR and levered IRR move with the loan rate."""
    a = get_assumptions(assumptions)
    if rates is None:
        rates = [7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5]

    rows = []
    for rate in rates:
        result = _analyse(property_price_lakhs, area_sqft, city, _with(a, annual_interest_rate_pct=rate))
        loan = result["upfront"]["loan_amount"]
        months = int(round(a["loan_tenure_years"] * 12))
        emi = result["monthly"]["emi"]
        rows.append({
            "Interest_Rate_Pct": rate,
            "Monthly_EMI": emi,
            "Total_Interest": emi * months - loan,
            "Net_Monthly_Cash_Flow": result["monthly"]["net_monthly_cash_flow_rented"],
            "DSCR": result["metrics"]["dscr_year1"],
            "Levered_IRR_Pct": result["metrics"]["levered_irr_pct"],
        })
    return pd.DataFrame(rows)


def build_irr_matrix(property_price_lakhs: float, area_sqft: float, city: str, assumptions: dict = None,
                     rates: list = None, appreciations: list = None) -> pd.DataFrame:
    """Levered IRR (%) for every combination of loan rate (columns) and price growth (rows)."""
    a = get_assumptions(assumptions)
    if rates is None:
        rates = [7.5, 8.5, 9.5, 10.5]
    if appreciations is None:
        appreciations = [3.0, 5.0, 7.0, 9.0]

    table = {}
    for rate in rates:
        column = []
        for growth in appreciations:
            result = _analyse(property_price_lakhs, area_sqft, city,
                              _with(a, annual_interest_rate_pct=rate, property_appreciation_pct=growth))
            irr = result["metrics"]["levered_irr_pct"]
            column.append(float("nan") if irr is None else irr)
        table[rate] = column

    matrix = pd.DataFrame(table, index=appreciations)
    matrix.index.name = "Price_Growth_Pct"
    matrix.columns.name = "Interest_Rate_Pct"
    return matrix


def build_breakeven_matrix(property_price_lakhs: float, area_sqft: float, city: str,
                           assumptions: dict = None, appreciations: list = None,
                           market_returns: list = None) -> pd.DataFrame:
    """Rent-vs-buy breakeven year for each price growth (rows) and market return (columns). NaN = never."""
    a = get_assumptions(assumptions)
    if appreciations is None:
        appreciations = [4.0, 6.0, 8.0, 10.0]
    if market_returns is None:
        market_returns = [6.0, 8.0, 10.0, 12.0]

    table = {}
    for market in market_returns:
        column = []
        for growth in appreciations:
            path = build_rent_vs_buy(property_price_lakhs, area_sqft, city,
                                     _with(a, property_appreciation_pct=growth, market_return_pct=market))
            year = find_breakeven_year(path)
            column.append(float("nan") if year is None else year)
        table[market] = column

    matrix = pd.DataFrame(table, index=appreciations)
    matrix.index.name = "Price_Growth_Pct"
    matrix.columns.name = "Market_Return_Pct"
    return matrix


# ----------------------------------------------------------------------------
# 11. One call for the whole app
# ----------------------------------------------------------------------------
def _analyse(property_price_lakhs: float, area_sqft: float, city: str, a: dict) -> dict:
    """Upfront costs, monthly numbers, cash-flow tables and metrics. `a` must be a full assumptions dict."""
    up = calculate_upfront_costs(property_price_lakhs, area_sqft, city, a)
    cash_flow_table = build_cash_flow_table(property_price_lakhs, area_sqft, city, a)
    annual = build_annual_summary(cash_flow_table)
    return {
        "upfront": up,
        "monthly": calculate_monthly_costs(property_price_lakhs, area_sqft, city, a),
        "cash_flow_table": cash_flow_table,
        "annual": annual,
        "metrics": _metrics_from_tables(up, cash_flow_table, annual, a, area_sqft),
    }


def run_full_analysis(property_price_lakhs: float, area_sqft: float, city: str,
                      assumptions: dict = None) -> dict:
    """
    Everything the app needs in one dictionary:
      upfront, monthly, metrics            -> dicts for st.metric cards
      cash_flow_table, annual              -> tables (monthly and yearly)
      amortization                         -> stacked bar chart (principal vs interest)
      rent_vs_buy, breakeven_year          -> line chart and its headline
      rate_sensitivity, irr_matrix         -> styled tables
      warnings                             -> list of text warnings for st.warning
    """
    a = get_assumptions(assumptions)
    result = _analyse(property_price_lakhs, area_sqft, city, a)
    rent_vs_buy = build_rent_vs_buy(property_price_lakhs, area_sqft, city, a)

    result["assumptions"] = a
    result["amortization"] = build_amortization_schedule(
        result["upfront"]["loan_amount"], a["annual_interest_rate_pct"], a["loan_tenure_years"])
    result["rent_vs_buy"] = rent_vs_buy
    result["breakeven_year"] = find_breakeven_year(rent_vs_buy)
    result["rate_sensitivity"] = build_rate_sensitivity(property_price_lakhs, area_sqft, city, a)
    result["irr_matrix"] = build_irr_matrix(property_price_lakhs, area_sqft, city, a)
    result["warnings"] = check_inputs(property_price_lakhs, area_sqft, city, a)
    return result

def run_light_analysis(property_price_lakhs: float, area_sqft: float, city: str,
                       assumptions: dict = None) -> dict:
    """Fast version for the Simulator page: no sensitivity grids, no IRR matrix."""
    a = get_assumptions(assumptions)
    result = _analyse(property_price_lakhs, area_sqft, city, a)
    result["assumptions"] = a
    result["warnings"] = check_inputs(property_price_lakhs, area_sqft, city, a)
    return result