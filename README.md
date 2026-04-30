# Fuel Price Prediction System Using Machine Learning

This repository contains the final year IT research project for Ryan Alfred Nyambati. The system predicts next-month fuel prices in Kenya using a simple Linear Regression model built with historical fuel prices, USD/KES exchange rate values, crude oil prices, and lagged fuel price variables.

## Project Title

Fuel Price Prediction System Using Machine Learning

## Student Details

- Name: Ryan Alfred Nyambati
- Registration Number: SCT222-0195/2021
- Institution: Jomo Kenyatta University of Agriculture and Technology
- Department: Information Technology

## Model Inputs

The current model uses these five input features:

- `Month_num`
- `USD_KES`
- `Crude_Oil`
- `Lag_1`
- `Lag_2`

The model inputs are limited to exchange rate, crude oil price, month number, and lagged fuel prices.

## Target Variables

- `Super_Petrol`
- `Diesel`
- `Kerosene`

## Dataset Columns

The system expects `fuel_prices.csv` to contain:

```text
Date, USD_KES, Crude_Oil, Super_Petrol, Diesel, Kerosene
```

## What the System Does

- Loads the verified CSV dataset
- Converts `Date` to datetime format
- Sorts records chronologically
- Creates `Month_num`
- Creates `Lag_1` and `Lag_2` for the selected fuel type
- Trains a Linear Regression model
- Accepts expected `USD_KES` and `Crude_Oil` inputs
- Predicts the next-month fuel price
- Displays prediction results in Kenya shillings
- Displays `MAE`, `MSE`, and `R² Score`
- Displays a fuel price trend chart
- Displays the historical dataset and lagged dataset in expandable sections

## Tools Used

- Streamlit
- Pandas
- Scikit-learn
- Matplotlib

## Project Structure

```text
fuel-price-predictor/
├── app.py
├── fuel_prices.csv
├── requirements.txt
├── README.md
├── notebooks/
│   └── FuelPriceAnalysis.ipynb
├── outputs/
│   ├── charts/
│   ├── diagrams/
│   ├── screenshots/
│   └── excel_analysis.xlsx
├── docs/
│   └── Ryan_Final_Project_Report.docx
├── appendices/
└── tests/
    └── test_project.py
```

## Installation

```bash
pip install -r requirements.txt
```

## Run the App

```bash
streamlit run app.py
```

## Run the Tests

```bash
python -m unittest discover -s tests -v
```

## Notebook and Outputs

The notebook in `notebooks/FuelPriceAnalysis.ipynb` is used for data checking, descriptive statistics, and chart generation for the final report. Generated charts, screenshots, diagrams, and the Excel analysis file are stored in the `outputs/` folder.

## Repository Link

[GitHub Repository](https://github.com/ryanair000/fuel-price-predictor)
