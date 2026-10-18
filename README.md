# Indian House Price Simulator

An interactive Streamlit app that predicts residential property prices in Indian metropolitan cities using LightGBM, then overlays a financial simulation (upfront costs, EMI, rental yield and net monthly cash flow).

## Features

- **Price prediction:** LightGBM regressor trained on a Kaggle dataset of Indian metro housing listings (log-transformed target, native categorical handling for City and Locality).
- **Financial engine:** Down payment, stamp duty, registration charges, EMI, rental income, society maintenance and net monthly cash flow.
- **Interactive UI:** Dark-themed Streamlit dashboard with metric cards and an amortization chart.
- **Indian currency format:** All amounts shown as ₹85,50,000 or ₹1.45 Cr.

## Project Structure

```
indian-house-price-simulator/
├── data/
│   ├── raw/                  # Kaggle CSVs (not tracked)
│   └── processed/            # clean_metro_housing.parquet (not tracked)
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   └── 02_model_training.ipynb
├── src/
│   ├── __init__.py
│   └── financial_engine.py
├── artifacts/
│   └── lgbm_model.joblib
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Workflow

1. **01_data_cleaning.ipynb:** Merge city CSVs, build `Amenity_Score`, standardize prices (Lakhs) and BHK, filter outliers, downcast dtypes, save `clean_metro_housing.parquet`.
2. **02_model_training.ipynb:** Load the parquet, train LightGBM on `log1p(price_in_lakhs)`, evaluate, export `artifacts/lgbm_model.joblib`.
3. **src/financial_engine.py:** Pure Python functions for EMI, upfront costs and cash flow.
4. **app.py:** Streamlit interface that connects the model and the financial engine.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

## Data

Download the Kaggle dataset CSVs (Bangalore, Mumbai, Delhi, etc.) and place them in `data/raw/`. Data files are not included in this repository.

## Run

1. Run `notebooks/01_data_cleaning.ipynb`, then `notebooks/02_model_training.ipynb`.
2. Start the app:

```bash
streamlit run app.py
```

## Tech Stack

Python, pandas, PyArrow (Parquet), LightGBM, scikit-learn, joblib, Streamlit, Plotly.

## Disclaimer

Predictions are estimates from a historical dataset and are not financial advice. Stamp duty, rental yield and interest rates vary by state, locality and lender.
