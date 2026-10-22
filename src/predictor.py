from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BUNDLE_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "lgbm_model.joblib"

# Names of the items inside your saved bundle. If a key differs, edit it here.
KEY_MODEL = "model"
KEY_FEATURES = "features"
KEY_CITY_CATS = "city_categories"
KEY_LOCALITY_CATS = "locality_categories"
KEY_RANGES = "range_ratios"            # table with low_ratio / high_ratio per city
KEY_LOCALITIES = "localities_by_city"  # {city: [locality, ...]}
KEY_AMENITY = "amenity_levels"         # optional, added in Part 3


@lru_cache(maxsize=1)
def load_bundle():
    """Load the saved model once and keep it in memory."""
    return joblib.load(BUNDLE_PATH)


def get_localities(city):
    """Locality names for a city, sorted. The bundle stores (name, count) pairs."""
    items = load_bundle()[KEY_LOCALITIES][city]
    names = []
    for item in items:
        if isinstance(item, (tuple, list)):
            names.append(item[0])
        else:
            names.append(item)
    return sorted(names)


def get_amenity_levels():
    """Amenity tier -> score. 'Not sure' is None, which the model treats as missing."""
    levels = load_bundle().get(KEY_AMENITY)
    if levels is None:
        levels = {"Not sure": None, "Basic": 3, "Standard": 6, "Premium": 10}
    return levels

def _get_ratios(ranges, city):
    """Read the city's low/high ratio whether the bundle stores a table or a dictionary."""
    if hasattr(ranges, "loc"):                      # a pandas table
        return float(ranges.loc[city, "low_ratio"]), float(ranges.loc[city, "high_ratio"])
    if city in ranges:                              # {city: {"low_ratio": .., "high_ratio": ..}}
        return float(ranges[city]["low_ratio"]), float(ranges[city]["high_ratio"])
    # {"low_ratio": {city: ..}, "high_ratio": {city: ..}}
    return float(ranges["low_ratio"][city]), float(ranges["high_ratio"][city])


def predict_price(city, locality, bhk, area, amenity_score):
    """Return the model-era price and the city's range, all in lakhs."""
    bundle = load_bundle()

    row = pd.DataFrame({
        "City": pd.Categorical([city], categories=bundle[KEY_CITY_CATS]),
        "Locality": pd.Categorical([locality], categories=bundle[KEY_LOCALITY_CATS]),
        "BHK": [bhk],
        "Area_SqFt": [area],
        "Amenity_Score": [np.nan if amenity_score is None else amenity_score],
    })
    row = row[bundle[KEY_FEATURES]]

    log_price = bundle[KEY_MODEL].predict(row)[0]
    price_lakhs = float(np.expm1(log_price))
    
    ranges = bundle[KEY_RANGES]
    low_ratio, high_ratio = _get_ratios(ranges, city)
    low = price_lakhs * low_ratio
    high = price_lakhs * high_ratio

    return {"price_lakhs": price_lakhs, "low_lakhs": low, "high_lakhs": high}
