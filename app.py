import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression

# Load dataset
data = pd.read_csv("fuel_prices.csv")

# Prepare data
data["Month"] = pd.to_datetime(data["Month"])
data["Month_num"] = range(len(data))

# App title
st.title("Kenya Fuel Price Predictor")

# Fuel type selection
fuel_type = st.selectbox(
    "Select fuel type to predict:",
    ["Petrol", "Diesel", "Kerosene"]
)

# User input values
usd_kes = st.number_input(
    "Enter expected USD/KES exchange rate:",
    value=float(data["USD_KES"].iloc[-1])
)

oil_price = st.number_input(
    "Enter expected global oil price (USD/barrel):",
    value=float(data["Oil_Price_USD"].iloc[-1])
)

tax_rate = st.number_input(
    "Enter expected tax rate (%):",
    value=float(data["Tax_Rate"].iloc[-1])
)

# Train model
X = data[["Month_num", "USD_KES", "Oil_Price_USD", "Tax_Rate"]]
y = data[fuel_type]

model = LinearRegression()
model.fit(X, y)

# Predict next month
next_month_num = len(data)

future_input = pd.DataFrame({
    "Month_num": [next_month_num],
    "USD_KES": [usd_kes],
    "Oil_Price_USD": [oil_price],
    "Tax_Rate": [tax_rate]
})

prediction = model.predict(future_input)[0]

# Display data
st.subheader("Historical Dataset")
st.dataframe(data)

# Chart
st.subheader(f"{fuel_type} Price Trend")
st.line_chart(data.set_index("Month")[fuel_type])

# Prediction output
st.subheader(f"Predicted {fuel_type} Price for Next Month")
st.success(f"KSh {prediction:.2f}")

# Explanation
st.write(
    "This model predicts fuel prices using time, USD/KES exchange rate, "
    "global oil price, and tax rate as input variables."
)