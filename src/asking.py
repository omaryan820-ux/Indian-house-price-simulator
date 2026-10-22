def asking_check(asking_lakhs, estimate_lakhs, low_lakhs, high_lakhs):
    """Compare the seller's price with the model's range. Returns (level, headline, detail)."""
    gap = (asking_lakhs - estimate_lakhs) / estimate_lakhs * 100
    direction = "above" if gap > 0 else "below"
    gap_text = format(abs(gap), ".0f") + "% " + direction + " our 2026 estimate"

    if asking_lakhs > high_lakhs:
        return ("amber", "Asking price is above the likely range",
                "It is " + gap_text + ". Compare with recent sales in the same building or "
                "locality before negotiating. The model has limits, so this is a prompt to check, not a verdict.")
    if asking_lakhs < low_lakhs:
        return ("amber", "Asking price is below the likely range",
                "It is " + gap_text + ". That could be a good deal, or something the model cannot see "
                "(condition, legal issues, a different size). Worth finding out why.")
    return ("blue", "Asking price is within the likely range",
            "It is " + gap_text + ". The model's error is large, so small gaps mean little.")