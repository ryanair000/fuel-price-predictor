from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


DATA_PATH = Path("fuel_prices.csv")
REQUIRED_COLUMNS = [
    "Date",
    "USD_KES",
    "Crude_Oil",
    "Super_Petrol",
    "Diesel",
    "Kerosene",
]
FEATURE_COLUMNS = ["Month_num", "USD_KES", "Crude_Oil", "Lag_1", "Lag_2"]
FUEL_OPTIONS = {
    "Super Petrol": "Super_Petrol",
    "Diesel": "Diesel",
    "Kerosene": "Kerosene",
}


st.set_page_config(
    page_title="Kenya Fuel Price Predictor",
    page_icon="F",
    layout="wide",
)


def validate_dataset(dataframe: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(f"The dataset is missing these required columns: {missing_list}")


@st.cache_data
def load_data() -> pd.DataFrame:
    data = pd.read_csv(DATA_PATH)
    validate_dataset(data)
    data["Date"] = pd.to_datetime(data["Date"], format="%b-%Y")
    data = data.sort_values("Date").reset_index(drop=True)
    data["Month_num"] = range(1, len(data) + 1)
    return data


def create_lagged_data(data: pd.DataFrame, fuel_column: str) -> pd.DataFrame:
    lagged_data = data.copy()
    lagged_data["Lag_1"] = lagged_data[fuel_column].shift(1)
    lagged_data["Lag_2"] = lagged_data[fuel_column].shift(2)
    return lagged_data.dropna().reset_index(drop=True)


def train_model(model_data: pd.DataFrame, fuel_column: str):
    x_values = model_data[FEATURE_COLUMNS]
    y_values = model_data[fuel_column]

    x_train, x_test, y_train, y_test = train_test_split(
        x_values,
        y_values,
        test_size=0.2,
        shuffle=False,
    )

    model = LinearRegression()
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    metrics = {
        "MAE": mean_absolute_error(y_test, predictions),
        "MSE": mean_squared_error(y_test, predictions),
        "R2": r2_score(y_test, predictions),
    }

    return model, metrics


def build_future_input(data: pd.DataFrame, fuel_column: str, usd_kes: float, crude_oil: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Month_num": [int(data["Month_num"].iloc[-1] + 1)],
            "USD_KES": [usd_kes],
            "Crude_Oil": [crude_oil],
            "Lag_1": [float(data[fuel_column].iloc[-1])],
            "Lag_2": [float(data[fuel_column].iloc[-2])],
        }
    )


def format_table_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    display_data = dataframe.copy()
    if "Date" in display_data.columns:
        display_data["Date"] = display_data["Date"].dt.strftime("%b-%Y")
    return display_data


def build_trend_chart(data: pd.DataFrame, fuel_column: str, next_month: pd.Timestamp, prediction: float) -> pd.DataFrame:
    historical_points = data[["Date", fuel_column]].rename(columns={fuel_column: "Price"})
    historical_points["Series"] = "Historical Price"

    predicted_point = pd.DataFrame(
        {
            "Date": [next_month],
            "Price": [prediction],
            "Series": ["Predicted Price"],
        }
    )

    chart_data = pd.concat([historical_points, predicted_point], ignore_index=True)
    return chart_data.pivot(index="Date", columns="Series", values="Price")


def main() -> None:
    st.title("Kenya Fuel Price Predictor")
    st.write(
        "This system predicts next-month fuel prices in Kenya using a linear regression "
        "model trained on USD/KES exchange rate data, crude oil prices, and lagged fuel prices."
    )

    data = load_data()

    selected_fuel = st.selectbox("Select fuel type to predict:", list(FUEL_OPTIONS.keys()))
    fuel_column = FUEL_OPTIONS[selected_fuel]
    model_data = create_lagged_data(data, fuel_column)

    left_column, right_column = st.columns(2)

    with left_column:
        usd_kes = st.number_input(
            "Enter expected USD/KES exchange rate:",
            min_value=0.0,
            value=float(data["USD_KES"].iloc[-1]),
            step=0.10,
        )

    with right_column:
        crude_oil = st.number_input(
            "Enter expected global crude oil price (USD/barrel):",
            min_value=0.0,
            value=float(data["Crude_Oil"].iloc[-1]),
            step=0.10,
        )

    model, metrics = train_model(model_data, fuel_column)
    future_input = build_future_input(data, fuel_column, usd_kes, crude_oil)
    prediction = float(model.predict(future_input)[0])
    next_month = data["Date"].iloc[-1] + pd.DateOffset(months=1)

    st.subheader(f"Predicted {selected_fuel} Price for {next_month.strftime('%B %Y')}")
    st.success(f"KSh {prediction:.2f} per litre")

    st.subheader("Model Evaluation")
    metric_columns = st.columns(3)
    metric_columns[0].metric("MAE", f"{metrics['MAE']:.2f}")
    metric_columns[1].metric("MSE", f"{metrics['MSE']:.2f}")
    metric_columns[2].metric("R² Score", f"{metrics['R2']:.2f}")

    st.subheader(f"{selected_fuel} Price Trend")
    st.line_chart(build_trend_chart(data, fuel_column, next_month, prediction))

    st.subheader("Prediction Inputs Used")
    st.write(
        f"The model used the latest lagged prices of KSh {data[fuel_column].iloc[-1]:.2f} and "
        f"KSh {data[fuel_column].iloc[-2]:.2f}, together with USD/KES {usd_kes:.2f} and crude oil "
        f"price USD {crude_oil:.2f} per barrel."
    )

    with st.expander("View Historical Dataset"):
        st.dataframe(format_table_dates(data), use_container_width=True)

    with st.expander(f"View Lagged Dataset for {selected_fuel}"):
        st.dataframe(format_table_dates(model_data), use_container_width=True)


if __name__ == "__main__":
    main()
