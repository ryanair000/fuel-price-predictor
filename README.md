# MafutaPlan

MafutaPlan is a BSc Information Technology final project for Nairobi transport
operators and small businesses. It combines a component-based fuel-price model
with price explanations, reconstruction, and fuel-budget calculators.

## Forecast

The model uses the latest complete verified component cycle in the repository:
15 March to 14 April 2026. Those component values predict the immediately
following April 2026 retail-price cycle.

The pooled `LinearRegression` model uses:

- landed cost;
- distribution and storage;
- margins;
- stabilization adjustment;
- taxes and levies; and
- encoded fuel type.

April is kept out of training and used as a chronological holdout. The app
shows predicted and official April prices and their errors for Super Petrol,
Diesel, and Kerosene.

## Live data

The Home page reads Nairobi pump prices from EPRA's public pump-price table.
It displays the effective period and retrieval time and caches the response for
one hour. This observed retail-price feed is separate from the component model.

## Pages

1. Home
2. Fuel Price Prediction
3. Factors Affecting Fuel Price
4. Price Reconstruction
5. Fuel Calculator
6. Data and Methodology

## Run

Python 3.10 or later is recommended.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Rebuild artifacts

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_model_dataset.py
python scripts/build_notebook.py
python scripts/build_report.py
```

## Limitations

- The component panel has 33 fuel-cycle rows across 11 discontinuous cycles.
- Regulatory, tax, subsidy, and stabilization decisions can change abruptly.
- Small-sample coefficients are unstable and do not prove causation.
- Station prices may be below the regulatory maximum.
- MafutaPlan is an academic tool, not an EPRA service.

**Author:** Ryan Alfred Nyambati - SCT222-0195/2021, Jomo Kenyatta University
of Agriculture and Technology.
