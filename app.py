from __future__ import annotations

import pandas as pd
import streamlit as st

from src.calculators import cost_for_litres, litres_for_budget, trip_estimate
from src.data import (
    FUEL_COLUMNS,
    load_component_history,
    load_official_prices,
    load_prediction_dataset,
    load_sources,
)
from src.modeling import (
    COMPONENT_FEATURES,
    evaluate_latest_cycle,
)
from src.pricing import component_shares, reconstruct_price, scenario_estimate

PROJECT_TITLE = (
    "Design and Implementation of a Component-Based Fuel Price Prediction "
    "System Using Multiple Linear Regression in Nairobi, Kenya"
)
FUEL_ORDER = ["Super Petrol", "Diesel", "Kerosene"]
COMPONENT_LABELS = {
    "Landed_Cost": "Landed cost",
    "Distribution_Storage": "Distribution and storage",
    "Margins": "Margins",
    "Stabilization_Adjustment": "Stabilization adjustment",
    "Taxes_Levies": "Taxes and levies",
}
COMPONENT_DESCRIPTIONS = {
    "Landed_Cost": "Imported product cost, freight, insurance, financing, port costs and exchange-rate effects already included in the landed value.",
    "Distribution_Storage": "Jetty handling, storage, pipeline transport, allowable losses, depot handling and Nairobi delivery.",
    "Margins": "Approved wholesale, retail investment and retail operating margins.",
    "Stabilization_Adjustment": "Signed subsidy, compensation, deficit, surplus or approved reconciliation adjustment.",
    "Taxes_Levies": "Excise, VAT and applicable statutory petroleum, road, regulatory and import-related charges.",
}


@st.cache_data
def load_project_data() -> tuple[pd.DataFrame, ...]:
    return (
        load_official_prices(),
        load_component_history(),
        load_prediction_dataset(),
        load_sources(),
    )


def money(value: float) -> str:
    return f"KSh {value:,.2f}"


def home_page() -> None:
    st.header("Component-based prediction and fuel planning")
    st.write(
        "MafutaPlan uses verified fuel-cost components to study Nairobi maximum "
        "retail prices and supports practical fuel budgeting."
    )
    st.info(
        "The prediction page uses March 2026 components to predict the next "
        "cycle, April 2026."
    )

    st.subheader("Who the system is for")
    st.write(
        "MafutaPlan is designed primarily for Nairobi transport operators and "
        "small transport businesses that need fuel-price information for "
        "budgeting and journey-cost planning."
    )
    st.write(
        "Primary users include ride-hailing drivers, taxi and matatu operators, "
        "courier businesses, and small logistics firms. Private motorists, "
        "households using kerosene, students, and researchers are secondary users."
    )
    st.subheader("User persona")
    st.write(
        "**Brian, a Nairobi ride-hailing driver**, uses MafutaPlan to view the "
        "next-cycle estimate, understand price factors, estimate weekly fuel "
        "expenses, calculate journey costs, and plan his budget."
    )


def prediction_page(
    component_history: pd.DataFrame,
    prediction_data: pd.DataFrame,
) -> None:
    st.header("April 2026 Prediction")
    st.write(
        "The model uses the latest complete component cycle, March 2026, to "
        "predict the immediately following retail-price cycle, April 2026."
    )

    evaluation = evaluate_latest_cycle(prediction_data)
    fuel = st.selectbox("Fuel product", FUEL_ORDER)
    result = evaluation.results.loc[evaluation.results["Fuel"].eq(fuel)].iloc[0]
    latest = (
        component_history.loc[component_history["Fuel"].eq(fuel)]
        .sort_values("Effective_From")
        .iloc[-1]
    )

    st.info(
        "Input cycle: latest fully verified component record, "
        f"{latest.Effective_From:%d %B %Y} to {latest.Effective_To:%d %B %Y}. "
        f"Target cycle: {result.Target_Cycle:%B %Y}."
    )

    prediction = float(result.Predicted_Retail_Price)
    official_price = float(result.Target_Retail_Price)
    error = float(result.Absolute_Error)
    columns = st.columns(3)
    columns[0].metric("Predicted April price", money(prediction))
    columns[1].metric("Official April price", money(official_price))
    columns[2].metric(
        "Absolute error",
        f"{money(error)} ({float(result.Percentage_Error):.2f}%)",
    )

    st.subheader("March component inputs")
    inputs = pd.DataFrame(
        {
            "Component": [COMPONENT_LABELS[column] for column in COMPONENT_FEATURES],
            "KSh/L": [float(latest[column]) for column in COMPONENT_FEATURES],
        }
    )
    st.dataframe(
        inputs.style.format({"KSh/L": "{:.2f}"}),
        hide_index=True,
        width="stretch",
    )

    st.link_button("Open component source", latest.PDF_URL)
    st.caption(
        f"Chronological holdout: {evaluation.training_records} training records; "
        f"{evaluation.test_records} April records; overall MAE "
        f"{evaluation.mae:.2f} KSh/L."
    )


def factors_page(component_history: pd.DataFrame) -> None:
    st.header("Factors Affecting Fuel Price")
    fuel = st.selectbox("Fuel product", FUEL_ORDER)
    latest = (
        component_history.loc[component_history["Fuel"].eq(fuel)]
        .sort_values("Effective_From")
        .iloc[-1]
    )
    st.caption(
        f"Latest verified component record: "
        f"{latest.Effective_From:%d %b %Y} to {latest.Effective_To:%d %b %Y}"
    )

    shares = component_shares(latest)
    rows = pd.DataFrame(
        [
            {
                "Component": COMPONENT_LABELS[column],
                "Value (KSh/L)": float(latest[column]),
                "Share of reconstructed price (%)": shares[column],
            }
            for column in COMPONENT_FEATURES
        ]
    )
    st.dataframe(
        rows.style.format(
            {
                "Value (KSh/L)": "{:.2f}",
                "Share of reconstructed price (%)": "{:.1f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.bar_chart(rows.set_index("Component")["Value (KSh/L)"])

    for component in COMPONENT_FEATURES:
        st.markdown(
            f"**{COMPONENT_LABELS[component]}:** "
            f"{COMPONENT_DESCRIPTIONS[component]}"
        )
    st.caption(
        "Holding other components constant, an increase raises the deterministic "
        "scenario estimate; a decrease lowers it. Stabilization may be positive "
        "or negative."
    )

    st.subheader("What-if scenario")
    landed = st.slider("Landed-cost change (%)", -25, 25, 0)
    taxes = st.number_input("Taxes and levies change (KSh/L)", value=0.0, step=0.5)
    scenario = scenario_estimate(
        latest, landed_change_pct=float(landed), tax_change=float(taxes)
    )
    columns = st.columns(3)
    columns[0].metric("Historical base", money(scenario.base_price))
    columns[1].metric("Scenario estimate", money(scenario.estimated_price))
    columns[2].metric("Change", money(scenario.change))
    st.info("This scenario uses deterministic addition. It is not a prediction.")


def reconstruction_page(component_history: pd.DataFrame) -> None:
    st.header("Price Reconstruction")
    cycles = (
        component_history["Effective_From"].drop_duplicates().sort_values(ascending=False)
    )
    cycle = st.selectbox(
        "Verified historical cycle",
        cycles,
        format_func=lambda value: pd.Timestamp(value).strftime("%d %B %Y"),
    )
    fuel = st.selectbox("Fuel product", FUEL_ORDER)
    row = component_history.loc[
        component_history["Effective_From"].eq(cycle)
        & component_history["Fuel"].eq(fuel)
    ].iloc[0]

    reconstructed = reconstruct_price(row)
    columns = st.columns(3)
    columns[0].metric("Published price", money(float(row.Retail_Price)))
    columns[1].metric("Reconstructed price", money(reconstructed))
    columns[2].metric(
        "Reconstruction error", money(reconstructed - float(row.Retail_Price))
    )

    st.dataframe(
        pd.DataFrame(
            {
                "Component": [
                    COMPONENT_LABELS[column] for column in COMPONENT_FEATURES
                ],
                "KSh/L": [float(row[column]) for column in COMPONENT_FEATURES],
            }
        ).style.format({"KSh/L": "{:.2f}"}),
        hide_index=True,
        width="stretch",
    )
    st.link_button("Open official EPRA source", row.PDF_URL)
    st.info(
        "Reconstruction adds known components from the same historical cycle. "
        "It validates the official build-up; it is not machine learning."
    )


def calculator_page(official: pd.DataFrame) -> None:
    st.header("Fuel Calculator")
    fuel = st.selectbox("Fuel product", FUEL_ORDER)
    default_price = float(official[FUEL_COLUMNS[fuel]].iloc[0])
    price = st.number_input(
        "Price per litre (KSh)", min_value=0.01, value=default_price, step=0.01
    )

    st.subheader("Fuel purchase")
    litres = st.number_input("Litres to buy", min_value=0.01, value=20.0)
    st.metric("Cost", money(cost_for_litres(litres, price)))

    st.subheader("Budget")
    budget = st.number_input("Available budget (KSh)", min_value=0.01, value=5000.0)
    st.metric("Litres available", f"{litres_for_budget(budget, price):,.2f} L")

    st.subheader("Journey")
    distance = st.number_input("Journey distance (km)", min_value=0.01, value=50.0)
    efficiency = st.number_input(
        "Vehicle efficiency (km/L)", min_value=0.01, value=12.0
    )
    contingency = st.slider("Traffic or contingency allowance (%)", 0, 100, 10)
    trip = trip_estimate(distance, efficiency, price, contingency)
    columns = st.columns(3)
    columns[0].metric("Base fuel", f"{trip['base_litres']:.2f} L")
    columns[1].metric("Fuel with allowance", f"{trip['litres']:.2f} L")
    columns[2].metric("Journey cost", money(trip["cost"]))


def methodology_page(
    prediction_data: pd.DataFrame,
    component_history: pd.DataFrame,
    sources: pd.DataFrame,
) -> None:
    st.header("Data and Methodology")
    evaluation = evaluate_latest_cycle(prediction_data)

    st.subheader("Multiple linear regression")
    st.write(
        "Multiple linear regression learns how several fuel-cost components "
        "relate to the following cycle's retail price. It assigns one coefficient "
        "to each component and adds encoded fuel-type effects."
    )
    st.code(
        "Predicted price = intercept + b1×landed cost + "
        "b2×distribution/storage + b3×margins + b4×stabilization + "
        "b5×taxes/levies + fuel-type effect"
    )
    st.caption(
        "The intercept is the starting value. A coefficient describes the model's "
        "fitted association with an input; it is not proof of causation."
    )

    columns = st.columns(4)
    columns[0].metric("Training records", evaluation.training_records)
    columns[1].metric("Test records", evaluation.test_records)
    columns[2].metric("Test MAE", money(evaluation.mae))
    columns[3].metric("Test RMSE", money(evaluation.rmse))
    st.write(
        f"**Training targets:** {evaluation.training_start:%B %Y} to "
        f"{evaluation.training_end:%B %Y}"
    )
    st.write(f"**Chronological test target:** {evaluation.test_cycle:%B %Y}")
    st.write(
        "**Forecast design:** March 2026 components predict the held-out "
        "April 2026 retail-price cycle."
    )

    st.subheader("Learned coefficients")
    st.dataframe(
        evaluation.coefficients.style.format({"Coefficient": "{:.6f}"}),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Actual versus predicted chronological test")
    results = evaluation.results.rename(
        columns={
            "Target_Retail_Price": "Actual",
            "Predicted_Retail_Price": "Predicted",
        }
    )
    st.bar_chart(results.set_index("Fuel")[["Actual", "Predicted"]])
    st.dataframe(
        results[
            ["Fuel", "Actual", "Predicted", "Absolute_Error", "Percentage_Error"]
        ].style.format(
            {
                "Actual": "{:.2f}",
                "Predicted": "{:.2f}",
                "Absolute_Error": "{:.2f}",
                "Percentage_Error": "{:.2f}%",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Data coverage and limitations")
    st.write(
        f"The reviewed panel has {len(component_history)} fuel-cycle rows across "
        f"{component_history['Effective_From'].nunique()} official cycles. The "
        f"model-ready table has {len(prediction_data)} one-cycle-ahead records."
    )
    st.warning(
        "The component sample is small and discontinuous. Regulatory decisions, "
        "taxes, and stabilization can change abruptly. Results do not generalise "
        "to station-level prices and do not replace EPRA."
    )

    st.subheader("Source register")
    st.dataframe(
        sources[["Source_ID", "Publisher", "Title", "URL"]],
        hide_index=True,
        width="stretch",
    )


def main() -> None:
    st.set_page_config(page_title="MafutaPlan", page_icon="⛽", layout="wide")
    official, component_history, prediction_data, sources = load_project_data()

    st.sidebar.title("MafutaPlan")
    st.sidebar.caption("BSc Information Technology final project")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Home",
            "Fuel Price Prediction",
            "Factors Affecting Fuel Price",
            "Price Reconstruction",
            "Fuel Calculator",
            "Data and Methodology",
        ],
    )
    st.sidebar.divider()
    st.sidebar.caption("Nairobi • Super Petrol • Diesel • Kerosene")

    st.title("MafutaPlan")
    st.caption(PROJECT_TITLE)

    if page == "Home":
        home_page()
    elif page == "Fuel Price Prediction":
        prediction_page(component_history, prediction_data)
    elif page == "Factors Affecting Fuel Price":
        factors_page(component_history)
    elif page == "Price Reconstruction":
        reconstruction_page(component_history)
    elif page == "Fuel Calculator":
        calculator_page(official)
    else:
        methodology_page(prediction_data, component_history, sources)


if __name__ == "__main__":
    main()
