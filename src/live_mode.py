import pandas as pd

from src.formatting import format_inr_short

MODE_LIVE = "Live in it"
MODE_INVEST = "Invest"


def clean_mode(value):
    """Anything except 'Live in it' (including None) means the investor view."""
    if value == MODE_LIVE:
        return MODE_LIVE
    return MODE_INVEST


def live_verdict(monthly, breakeven_year, income, assumptions):
    """Calm, non-investor summary. Returns (level, headline, detail); level is 'blue' or 'amber'."""
    own = monthly["monthly_outflow_self_occupied"]
    rent = monthly["gross_monthly_rent"]
    emi = monthly["emi"]
    years = assumptions["projection_years"]

    headline = "Owning costs about " + format_inr_short(own) + " a month"
    detail = "Renting a similar flat is estimated at about " + format_inr_short(rent) + " a month. "
    if breakeven_year is None:
        detail += ("On these assumptions buying does not overtake renting financially within "
                   + str(years) + " years. Owning also means a home that is yours and a loan that ends. ")
    else:
        detail += "Buying overtakes renting financially in year " + str(breakeven_year) + ". "

    level = "blue"
    if income is not None and income > 0:
        share = emi / income * 100
        detail += ("Your EMI is about " + format(share, ".0f") + "% of your monthly income; "
                   "banks usually prefer it under 40-50%.")
        if share > 50:
            level = "amber"
    return level, headline, detail


def max_loan_for_emi(max_emi, annual_rate_pct, tenure_years):
    """Biggest loan whose EMI stays within max_emi."""
    monthly_rate = annual_rate_pct / 1200
    months = int(round(tenure_years * 12))
    if monthly_rate == 0:
        return max_emi * months
    return max_emi * (1 - (1 + monthly_rate) ** (-months)) / monthly_rate


def cumulative_costs(monthly, rent_vs_buy, assumptions, years_list):
    """Money paid out by year if you rent vs if you own, plus what you own at that point."""
    rent_now = monthly["gross_monthly_rent"]
    maintenance_now = monthly["maintenance"]
    emi = monthly["emi"]
    tenure_months = int(round(assumptions["loan_tenure_years"] * 12))

    rows = []
    for years in years_list:
        if years > assumptions["projection_years"]:
            continue
        rent_paid = 0.0
        maintenance_paid = 0.0
        for k in range(years):
            rent_paid += rent_now * 12 * (1 + assumptions["rent_growth_pct"] / 100) ** k
            maintenance_paid += maintenance_now * 12 * (1 + assumptions["maintenance_growth_pct"] / 100) ** k
        emi_paid = emi * min(years * 12, tenure_months)

        row = rent_vs_buy[rent_vs_buy["Year"] == years].iloc[0]
        rows.append({
            "Years": years,
            "Rent paid if renting": rent_paid,
            "Paid if owning (EMI + maintenance)": emi_paid + maintenance_paid,
            "Home value minus loan owed": row["Home_Value"] - row["Loan_Balance"],
        })
    return pd.DataFrame(rows)