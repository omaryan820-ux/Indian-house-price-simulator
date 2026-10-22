# Yearly price growth (%) used to bring dataset-era prices to 2026.
# These are OUR ESTIMATES, averaged over about 6 years. Recent one-year jumps
# were higher (PropTiger Q1 2026, Business Today H1 2026), earlier years were slower.
GROWTH_RATE_PCT = {
    "Mumbai": 7.0,
    "Delhi": 8.0,
    "Bangalore": 8.0,
    "Hyderabad": 8.0,
    "Chennai": 5.0,
    "Kolkata": 5.0,
}

# Years between the dataset era and 2026 (the dataset is about 6 years old)
YEARS_TO_2026 = 6

GROWTH_SOURCE_NOTE = (
    "Our own estimate of average yearly growth, informed by PropTiger (Q1 2026) "
    "and Business Today (H1 2026) market reports."
)

# Confidence from the test accuracy of each city
CONFIDENCE = {
    "Hyderabad": "High",
    "Delhi": "Medium",
    "Chennai": "Medium",
    "Bangalore": "Medium",
    "Mumbai": "Low",
    "Kolkata": "Low",
}

CITIES = ["Bangalore", "Chennai", "Delhi", "Hyderabad", "Kolkata", "Mumbai"]