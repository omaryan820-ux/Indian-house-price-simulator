"""
Display helpers for the Streamlit app. They only turn numbers into text.

    format_inr_full(8550000)      -> "₹85,50,000"
    format_inr_short(14500000)    -> "₹1.45 Cr"
    format_inr_signed(-250000)    -> "-₹2.50 L"   (+ sign for positive values)
    format_pct(6.0595)            -> "6.06%"
    format_multiple(1.524)        -> "1.52x"
    format_years(None)            -> "Not within the period"

Indian digit grouping: the last 3 digits form one group, then groups of 2
(1,00,000 = 1 lakh, 1,00,00,000 = 1 crore).
Every function accepts None (or NaN) and returns "n/a" instead of failing.
"""


def _is_missing(value) -> bool:
    """True for None and for NaN (NaN is the only number that is not equal to itself)."""
    return value is None or value != value


def format_inr_full(amount: float) -> str:
    """Full Indian grouping, e.g. 8550000 -> ₹85,50,000."""
    if _is_missing(amount):
        return "n/a"

    sign = "-" if amount < 0 else ""
    digits = str(int(round(abs(amount))))

    if len(digits) <= 3:
        return sign + "₹" + digits

    last_three = digits[-3:]          # the final 3 digits stay together
    rest = digits[:-3]                # everything before them is grouped in 2s

    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])   # take 2 digits from the right
        rest = rest[:-2]
    if rest != "":
        groups.insert(0, rest)

    return sign + "₹" + ",".join(groups) + "," + last_three


def format_inr_short(amount: float) -> str:
    """Short form: crore (Cr) from 1,00,00,000, lakh (L) from 1,00,000, else full."""
    if _is_missing(amount):
        return "n/a"

    sign = "-" if amount < 0 else ""
    size = abs(amount)

    if size >= 10000000:
        return sign + "₹" + format(size / 10000000, ".2f") + " Cr"
    if size >= 100000:
        return sign + "₹" + format(size / 100000, ".2f") + " L"
    return format_inr_full(amount)


def format_inr_signed(amount: float) -> str:
    """Short form with an explicit + for gains, for cash-flow and difference cards."""
    if _is_missing(amount):
        return "n/a"
    text = format_inr_short(amount)
    if amount > 0:
        return "+" + text
    return text


def format_pct(value: float, decimals: int = 2) -> str:
    """6.0595 -> '6.06%'. The input is already in percent."""
    if _is_missing(value):
        return "n/a"
    return format(value, "." + str(decimals) + "f") + "%"


def format_multiple(value: float) -> str:
    """1.524 -> '1.52x' (equity multiple)."""
    if _is_missing(value):
        return "n/a"
    return format(value, ".2f") + "x"


def format_years(year, none_text: str = "Not within the period") -> str:
    """Breakeven year as text; None means it never happened in the projection."""
    if _is_missing(year):
        return none_text
    return "Year " + str(int(year))
