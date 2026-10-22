# Proforma: Indian House Price Simulator

**Live app: https://proforma-analysis.streamlit.app/**

Estimate a flat's price in six Indian metros, then see what it really costs to own it, finance it, rent it out or compare it with renting. Built for people doing their own analysis, with no broker, no builder and nothing to sell.

## What it does
- **Price estimate** from a machine-learning model, with a likely range and a confidence level per city.
- **2026 value:** the dataset is about six years old, so prices are grown at city-wise yearly rates (our own estimates, shown in the app).
- **Two modes:** *Live in it* (monthly cost, rent comparison, affordability) and *Invest* (IRR, NPV, DSCR, cash flow, sensitivity grids).
- **Seller's asking price:** enter the price you were quoted and every finance number uses it, with a check against the model's range.
- **Compare** two flats or two loans side by side.
- **Accuracy & Assumptions** page with per-city error, sources, assumptions and a feedback form.

## How it works
1. `notebooks/01_data_cleaning.ipynb`: cleans a Kaggle dataset of about 33,000 listings (Bangalore, Chennai, Delhi NCR, Hyderabad, Kolkata, Mumbai).
2. `notebooks/02_model_training.ipynb`: trains a LightGBM model on log price, checks it against a locality baseline, and saves the model and settings to `artifacts/`.
3. `src/financial_engine.py`: monthly cash-flow engine (EMI, stamp duty, rent, vacancy, maintenance, sale), levered and unlevered IRR, NPV, DSCR, rent-vs-buy and sensitivity tables.
4. `app.py` and `views/`: the Streamlit app.

## Accuracy, honestly
Typical error is about 12% in Hyderabad and about 37% in Kolkata (about 25% overall). The model is **not reliable for luxury or prime areas**, unusually large or small flats, or where data is thin. Treat prices as rough ranges. Stamp duty and growth rates are estimates, and tax is not modelled. This is a planning tool, not financial, legal or investment advice.

## Project structure
```
app.py            app entry point and navigation
views/            one file per page
src/              prediction, finance engine, charts, cards, helpers
notebooks/        data cleaning and model training
artifacts/        saved model
assets/           logo and illustration
.streamlit/       theme (config.toml)
```

## Run it locally
```
pip install -r requirements.txt
streamlit run app.py
```
Feedback is saved to a Google Sheet when `.streamlit/secrets.toml` is set up, and to a local CSV otherwise.

## Tech
Python, pandas, LightGBM, scikit-learn, Streamlit, Plotly, gspread.

## Data
Listing data from https://www.kaggle.com/datasets/ruchi798/housing-prices-in-metropolitan-areas-of-india/data. 
Market growth figures consulted: PropTiger (Q1 2026) and Business Today (H1 2026).

Built by Om Aryan.