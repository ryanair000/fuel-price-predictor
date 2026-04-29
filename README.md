# Fuel Price Predictor

A Streamlit application that predicts next-month fuel prices in Kenya using a Linear Regression model trained on historical Nairobi fuel prices, USD/KES exchange rate, global crude oil price, and lagged fuel price variables.

## Features

- Predicts Super Petrol, Diesel, and Kerosene prices
- Uses lagged variables: previous month price and price from two months earlier
- Accepts expected USD/KES exchange rate and crude oil price inputs
- Displays prediction, model evaluation metrics, trend chart, historical dataset, and lagged dataset

## Requirements

- Python 3.10+
- pip

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Dataset Columns

The system expects `fuel_prices.csv` to contain:

```text
Date, USD_KES, Crude_Oil, Super_Petrol, Diesel, Kerosene
```
