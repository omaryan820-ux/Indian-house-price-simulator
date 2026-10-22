from src.predictor import load_bundle, predict_price, get_localities
from src.city_data import GROWTH_RATE_PCT, YEARS_TO_2026
from src.financial_engine import adjust_price_for_growth

print(list(load_bundle().keys()))
city = "Hyderabad"
loc = get_localities(city)[0]
out = predict_price(city, loc, 2, 1100, None)
print(loc, out)
print("2026 value:", adjust_price_for_growth(out["price_lakhs"], GROWTH_RATE_PCT[city], YEARS_TO_2026))