import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

st.set_page_config(
    page_title="Kenya Fuel Price Predictor",
    page_icon="⛽",
    layout="wide"
)

st.title("Kenya Fuel Price Predictor")

st.write(
    "This system predicts future fuel prices in Kenya using USD/KES exchange rate, "
    "global crude oil price, and lagged fuel price variables."
)

@st.cache_data
def load_data():
    data = pd.read_csv("fuel_prices.csv")
    data["Date"] = pd.to_datetime(data["Date"], format="%b-%Y")
    data = data.sort_values("Date").reset_index(drop=True)
    data["Month_num"] = range(len(data))
    return data

def create_lagged_data(data, fuel_column):
    model_data = data.copy()
    model_data["Lag_1"] = model_data[fuel_column].shift(1)
    model_data["Lag_2"] = model_data[fuel_column].shift(2)
    model_data = model_data.dropna().reset_index(drop=True)
    return model_data

data = load_data()

fuel_options = {
    "Super Petrol": "Super_Petrol",
    "Diesel": "Diesel",
    "Kerosene": "Kerosene"
}

fuel_type = st.selectbox(
    "Select fuel type to predict:",
    list(fuel_options.keys())
)

fuel_column = fuel_options[fuel_type]
model_data = create_lagged_data(data, fuel_column)

usd_kes = st.number_input(
    "Enter expected USD/KES exchange rate:",
    value=float(data["USD_KES"].iloc[-1])
)

crude_oil = st.number_input(
    "Enter expected global crude oil price (USD/barrel):",
    value=float(data["Crude_Oil"].iloc[-1])
)

features = ["Month_num", "USD_KES", "Crude_Oil", "Lag_1", "Lag_2"]
X = model_data[features]
y = model_data[fuel_column]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    shuffle=False
)

model = LinearRegression()
model.fit(X_train, y_train)

lag_1 = float(data[fuel_column].iloc[-1])
lag_2 = float(data[fuel_column].iloc[-2])
next_month_num = len(data)

future_input = pd.DataFrame({
    "Month_num": [next_month_num],
    "USD_KES": [usd_kes],
    "Crude_Oil": [crude_oil],
    "Lag_1": [lag_1],
    "Lag_2": [lag_2]
})

prediction = model.predict(future_input)[0]

st.subheader(f"Predicted {fuel_type} Price for Next Month")
st.success(f"KSh {prediction:.2f}")

st.subheader("Model Evaluation")
test_predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, test_predictions)
mse = mean_squared_error(y_test, test_predictions)
r2 = r2_score(y_test, test_predictions)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Mean Absolute Error", f"{mae:.2f}")

with col2:
    st.metric("Mean Squared Error", f"{mse:.2f}")

with col3:
    st.metric("R² Score", f"{r2:.2f}")

st.subheader(f"{fuel_type} Price Trend")
st.line_chart(data.set_index("Date")[fuel_column])

st.subheader("How the Prediction Works")
st.write(
    "The model predicts the next fuel price using time, expected USD/KES exchange rate, "
    "expected global crude oil price, and previous fuel price values."
)

st.write(f"For this prediction, the model used:")
st.write(f"- Previous month {fuel_type} price: KSh {lag_1:.2f}")
st.write(f"- Price from two months ago: KSh {lag_2:.2f}")
st.write(f"- Expected USD/KES exchange rate: {usd_kes:.2f}")
st.write(f"- Expected crude oil price: USD {crude_oil:.2f} per barrel")

with st.expander("View Historical Dataset"):
    st.dataframe(data)

with st.expander(f"View Lagged Dataset for {fuel_type}"):
    st.dataframe(model_data)
