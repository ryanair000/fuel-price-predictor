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
    JULY_2026_CYCLE,
    DataAvailabilityError,
    evaluate_latest_cycle,
    fit_linear_regression,
    predict_july_2026,
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


def home_page(official: pd.DataFrame) -> None:
    st.header("Component-based prediction and fuel planning")
    st.write(
        "MafutaPlan uses verified fuel-cost components to study Nairobi maximum "
        "retail prices and supports practical fuel budgeting."
    )
    st.info(
        "July 2026 is the final evaluation target. The application never uses "
        "July component values to predict July prices."
    )

    columns = st.columns(3)
    for column, fuel in zip(columns, FUEL_ORDER):
        column.metric(fuel, money(float(official[FUEL_COLUMNS[fuel]].iloc[0])))
    st.caption("Official July 2026 Nairobi maximum retail prices, shown for evaluation.")

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
        "July prediction status, understand price factors, estimate weekly fuel "
        "expenses, calculate journey costs, and plan his budget."
    )
    st.warning(
        "Academic disclaimer: MafutaPlan is not an EPRA service and does not "
        "replace an official price announcement. Station prices may be below the "
        "regulated maximum."
    )


def july_prediction_page(
    official: pd.DataFrame,
    prediction_data: pd.DataFrame,
) -> None:
    st.header("July 2026 Prediction")
    st.write(
        "Method: one pooled multiple linear regression model using the five "
        "component groups and encoded fuel type."
    )

    production_training = prediction_data.loc[
        prediction_data["Target_Cycle"] < JULY_2026_CYCLE
    ]
    model = fit_linear_regression(production_training)
    official_values = {
        fuel: float(official[FUEL_COLUMNS[fuel]].iloc[0]) for fuel in FUEL_ORDER
    }

    try:
        july = predict_july_2026(model, prediction_data).set_index("Fuel")
    except DataAvailabilityError:
        july = None

    fuel = st.selectbox("Fuel product", FUEL_ORDER)
    st.write("**Intended input cycle:** June 2026")
    st.write("**Target cycle:** July 2026")
    st.write("**Official July price:**", money(official_values[fuel]))

    if july is None:
        st.error(
            "Prediction not produced: the repository has no verified June 2026 "
            "component record. Using July components would leak target-cycle "
            "information, and using March components would change the forecast "
            "horizon without evidence."
        )
        columns = st.columns(3)
        columns[0].metric("Predicted July price", "Unavailable")
        columns[1].metric("Absolute error", "Unavailable")
        columns[2].metric("Percentage error", "Unavailable")
    else:
        prediction = float(july.loc[fuel, "Predicted_Retail_Price"])
        error = abs(prediction - official_values[fuel])
        columns = st.columns(3)
        columns[0].metric("Predicted July price", money(prediction))
        columns[1].metric("Absolute error", money(error))
        columns[2].metric(
            "Percentage error", f"{error / official_values[fuel] * 100:.2f}%"
        )

    st.subheader("Required component inputs")
    st.write(", ".join(COMPONENT_LABELS[column] for column in COMPONENT_FEATURES))
    st.warning(
        "A model estimate is not an official EPRA announcement. July official "
        "prices are held outside training and are used only for final evaluation."
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
    st.write("**Final July target:** excluded from all training.")

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
        "The component sample is small and discontinuous. June 2026 components "
        "are not verified, so July predictions cannot be released. Regulatory "
        "decisions, taxes, and stabilization can change abruptly. Results do not "
        "generalise to station-level prices and do not replace EPRA."
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
            "July 2026 Prediction",
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
        home_page(official)
    elif page == "July 2026 Prediction":
        july_prediction_page(official, prediction_data)
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
