from src.formatting import format_pct


def get_verdict(metrics, monthly, assumptions):
    """Return (level, headline, detail). Level is 'red', 'amber' or 'green'."""
    irr = metrics["levered_irr_pct"]
    shortfall = monthly["net_monthly_cash_flow_rented"]
    emi = monthly["emi"]
    rent = monthly["expected_monthly_rent"]
    discount = assumptions["discount_rate_pct"]

    rent_cover = 0
    if emi > 0:
        rent_cover = rent / emi * 100

    if irr is None or irr < 6:
        level = "red"
        headline = "Weak as an investment at these assumptions"
    elif irr >= discount and shortfall >= 0:
        level = "green"
        headline = "Looks sound on paper at these assumptions"
    else:
        level = "amber"
        headline = "Mixed: depends on price growth"

    irr_text = "not defined"
    if irr is not None:
        irr_text = format_pct(irr)

    detail = (
        "Return on your own cash (IRR) is " + irr_text + " a year. "
        "Expected rent covers about " + format(rent_cover, ".0f") + "% of the EMI, "
        "so renting it out would not pay for the loan. "
        "If you plan to live in it, compare with renting on the Analysis page."
    )
    if shortfall >= 0:
        detail = (
            "Return on your own cash (IRR) is " + irr_text + " a year, "
            "and expected rent covers the EMI and running costs."
        )
    return level, headline, detail