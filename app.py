from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.calculators import cost_for_litres, litres_for_budget, trip_estimate
from src.data import (
    FUEL_COLUMNS,
    get_price,
    load_component_history,
    load_components,
    load_history,
    load_official_prices,
    load_sources,
)
from src.hybrid import (
    AGGREGATE_COMPONENTS,
    component_shares,
    reconstruct_price,
    scenario_estimate,
)
from src.modeling import FEATURE_COLUMNS, build_trend_chart, forecast_fuel

FUEL_CODES = {
    "Super Petrol": "PMS",
    "Diesel": "AGO",
    "Kerosene": "DPK",
}

COMPONENT_LABELS = {
    "Landed_Cost": "Landed product cost",
    "Distribution_Storage": "Distribution and storage",
    "Margins": "Wholesale and retail margins",
    "Stabilization_Adjustment": "Price stabilization",
    "Taxes_Levies": "Taxes and levies",
}


@st.cache_data
def load_project_data() -> tuple[pd.DataFrame, ...]:
    return (
        load_history(),
        load_official_prices(),
        load_components(),
        load_component_history(),
        load_sources(),
    )


@st.cache_data(show_spinner="Evaluating forecasting methods...")
def get_forecast(fuel_column: str):
    return forecast_fuel(load_history(), fuel_column)


def format_table_dates(frame: pd.DataFrame) -> pd.DataFrame:
    formatted = frame.copy()
    for column in ("Cycle", "Effective_From", "Effective_To", "Accessed_On"):
        if column in formatted.columns:
            formatted[column] = pd.to_datetime(formatted[column]).dt.strftime("%d %b %Y")
    return formatted


def show_source_link(url: str, label: str = "Open source") -> None:
    st.markdown(f"[{label}]({url})")


def overview_page(
    official: pd.DataFrame,
    current: pd.Series,
    history: pd.DataFrame,
    source_urls: dict[str, str],
) -> None:
    st.header("Official Nairobi fuel prices")
    active = current["Effective_From"].date() <= date.today() <= current["Effective_To"].date()
    status = "Active EPRA cycle" if active else "Latest verified record in the project dataset"
    st.caption(
        f"{status}: {current['Effective_From']:%d %b %Y} to "
        f"{current['Effective_To']:%d %b %Y}. Prices are maximum retail caps."
    )

    columns = st.columns(3)
    for column, fuel in zip(columns, FUEL_COLUMNS):
        with column:
            st.metric(
                f"{fuel} ({FUEL_CODES[fuel]})",
                f"KSh {get_price(official, fuel):,.2f}/L",
            )

    show_source_link(source_urls[current["Source_ID"]], "View the EPRA evidence")

    st.subheader("Price history")
    st.line_chart(
        history.set_index("Cycle")[["Super_Petrol", "Diesel", "Kerosene"]]
    )


def journey_page(
    components: pd.DataFrame,
    source_urls: dict[str, str],
) -> None:
    st.header("How the Nairobi pump price is built")
    st.caption(
        "Kenya imports refined petroleum products. The regulated price includes "
        "the landed product cost, inland distribution, margins, taxes and any "
        "approved stabilization adjustment."
    )

    steps = (
        "International procurement of refined PMS, AGO and DPK",
        "Ocean freight, insurance and financing",
        "Port handling, inspection and primary storage in Mombasa",
        "Pipeline transport and allowable losses to Nairobi",
        "Nairobi depot storage and local delivery",
        "Wholesale and retail margins",
        "Taxes and statutory levies",
        "Price stabilization adjustment",
    )
    for number, step in enumerate(steps, start=1):
        st.markdown(f"**{number}. {step}**")

    st.divider()
    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="journey_fuel")
    detail = components.loc[components["Fuel"].eq(fuel)].copy()
    grouped = detail.groupby("Category", as_index=False)["KES_Per_Litre"].sum()
    total = float(grouped["KES_Per_Litre"].sum())

    st.metric("Published retail total", f"KSh {total:,.2f}/L")
    st.caption(
        f"Component example effective {detail['Effective_From'].iloc[0]:%d %b %Y} "
        f"to {detail['Effective_To'].iloc[0]:%d %b %Y}."
    )
    st.bar_chart(grouped.set_index("Category")["KES_Per_Litre"], horizontal=True)
    st.dataframe(
        detail[["Component", "Category", "KES_Per_Litre"]].rename(
            columns={"KES_Per_Litre": "KSh per litre"}
        ),
        hide_index=True,
        width="stretch",
    )

    source_id = str(detail["Source_ID"].iloc[0])
    show_source_link(source_urls[source_id], "Open the EPRA component source")
    formula_url = source_urls.get("EPRA_FORMULA")
    if formula_url:
        show_source_link(formula_url, "Read EPRA's pump-price formula")


def reconstruction_page(component_history: pd.DataFrame) -> None:
    st.header("Reconstruct an official price")
    st.caption(
        "Select a reviewed EPRA cycle and verify that the five aggregate cost "
        "groups reproduce the published Nairobi retail price."
    )

    cycles = sorted(component_history["Effective_From"].unique(), reverse=True)
    selected_cycle = st.selectbox(
        "EPRA component cycle",
        cycles,
        format_func=lambda value: pd.Timestamp(value).strftime("%d %B %Y"),
    )
    fuel = st.selectbox(
        "Fuel product",
        list(FUEL_COLUMNS),
        key="reconstruction_fuel",
    )
    row = component_history.loc[
        component_history["Effective_From"].eq(pd.Timestamp(selected_cycle))
        & component_history["Fuel"].eq(fuel)
    ].iloc[0]

    calculated = reconstruct_price(row)
    left, middle, right = st.columns(3)
    left.metric("Official EPRA price", f"KSh {row['Retail_Price']:.2f}/L")
    middle.metric("Reconstructed price", f"KSh {calculated:.2f}/L")
    right.metric(
        "Difference",
        f"KSh {calculated - row['Retail_Price']:+.2f}",
    )

    shares = component_shares(row)
    table = pd.DataFrame(
        {
            "Component": [COMPONENT_LABELS[column] for column in AGGREGATE_COMPONENTS],
            "KSh per litre": [float(row[column]) for column in AGGREGATE_COMPONENTS],
            "Share of price": [f"{shares[column]:.1f}%" for column in AGGREGATE_COMPONENTS],
        }
    )
    st.bar_chart(table.set_index("Component")["KSh per litre"], horizontal=True)
    st.dataframe(table, hide_index=True, width="stretch")
    show_source_link(row["PDF_URL"], "Open the EPRA release used for this record")
    st.caption(str(row["Quality_Notes"]))


def forecast_page(
    history: pd.DataFrame,
    component_history: pd.DataFrame,
) -> None:
    st.header("Forecast and scenarios")
    st.caption(
        "The statistical forecast and the component scenario are separate. "
        "Neither is an EPRA announcement."
    )

    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="forecast_fuel")
    fuel_column = FUEL_COLUMNS[fuel]
    result = get_forecast(fuel_column)

    forecast_tab, scenario_tab, methods_tab = st.tabs(
        ["Next-cycle forecast", "Cost scenario", "Method"]
    )

    with forecast_tab:
        columns = st.columns(4)
        columns[0].metric(
            f"{result.next_date:%B %Y} estimate",
            f"KSh {result.prediction:,.2f}/L",
        )
        columns[1].metric(
            "Historical error range",
            f"{result.lower:,.2f} - {result.upper:,.2f}",
        )
        columns[2].metric("Holdout MAE", f"KSh {result.mae:.2f}")
        columns[3].metric("Baseline MAE", f"KSh {result.baseline_mae:.2f}")

        st.line_chart(build_trend_chart(history, fuel_column, result))
        comparison = "beat" if result.mae < result.baseline_mae else "did not beat"
        st.info(
            f"Selected method: **{result.model_name}**. It was selected using "
            f"{result.selection_points} sequential forecasts and evaluated on "
            f"{result.validation_points} later cycles. It {comparison} the "
            "previous-cycle baseline on the holdout period."
        )
        st.warning(
            "Use this as an academic planning estimate only. Policy changes, "
            "taxes, stabilization and market shocks can move the official price."
        )

    with scenario_tab:
        basis = (
            component_history.loc[component_history["Fuel"].eq(fuel)]
            .sort_values("Effective_From")
            .iloc[-1]
        )
        st.caption(
            f"Scenario basis: reviewed EPRA components effective "
            f"{basis['Effective_From']:%d %b %Y} to "
            f"{basis['Effective_To']:%d %b %Y}."
        )

        first, second, third = st.columns(3)
        landed_change = first.slider("Landed-cost change", -30, 40, 0, format="%d%%")
        distribution_change = second.slider(
            "Distribution/storage change", -20, 30, 0, format="%d%%"
        )
        margin_change = third.slider("Margin change", -20, 30, 0, format="%d%%")

        fourth, fifth = st.columns(2)
        tax_change = fourth.number_input(
            "Tax or levy change (KSh/L)",
            value=0.0,
            step=1.0,
        )
        stabilization = fifth.number_input(
            "Stabilization adjustment (KSh/L)",
            value=float(basis["Stabilization_Adjustment"]),
            step=0.5,
        )

        scenario = scenario_estimate(
            basis,
            landed_change_pct=landed_change,
            distribution_change_pct=distribution_change,
            margin_change_pct=margin_change,
            tax_change=tax_change,
            stabilization_adjustment=stabilization,
        )

        columns = st.columns(3)
        columns[0].metric("Reviewed basis", f"KSh {scenario.base_price:.2f}/L")
        columns[1].metric("Scenario estimate", f"KSh {scenario.estimated_price:.2f}/L")
        columns[2].metric("Change", f"KSh {scenario.change:+.2f}/L")

        chart = pd.DataFrame(
            {
                "Component": [COMPONENT_LABELS[key] for key in scenario.components],
                "KSh per litre": list(scenario.components.values()),
            }
        )
        st.bar_chart(chart.set_index("Component"), horizontal=True)

    with methods_tab:
        st.markdown(
            "The project compares a previous-cycle baseline with linear regression, "
            "ridge regression, random forest and gradient boosting. Model selection "
            "uses expanding-window validation, followed by a separate ten-cycle holdout."
        )
        st.markdown("**Forecast features**")
        st.code(", ".join(FEATURE_COLUMNS))
        st.caption(
            "All features are based on the calendar or prices available before the "
            "target cycle. Same-cycle external values are excluded."
        )


def calculator_page(official: pd.DataFrame) -> None:
    st.header("Fuel planning calculator")
    st.caption("Calculations use the selected official Nairobi maximum retail price.")

    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="calculator_fuel")
    price = get_price(official, fuel)
    st.metric("Price used", f"KSh {price:.2f}/L")

    mode = st.radio(
        "Calculation",
        ["Cost for litres", "Litres for a budget", "Trip cost"],
        horizontal=True,
    )

    if mode == "Cost for litres":
        litres = st.number_input("Litres", min_value=0.1, value=20.0, step=1.0)
        st.metric("Estimated cost", f"KSh {cost_for_litres(litres, price):,.2f}")
    elif mode == "Litres for a budget":
        budget = st.number_input(
            "Budget (KSh)",
            min_value=1.0,
            value=3000.0,
            step=100.0,
        )
        st.metric("Fuel available", f"{litres_for_budget(budget, price):,.2f} L")
    else:
        first, second, third = st.columns(3)
        distance = first.number_input(
            "Complete journey distance (km)",
            min_value=0.1,
            value=100.0,
        )
        efficiency = second.number_input(
            "Vehicle efficiency (km/L)",
            min_value=0.1,
            value=12.0,
        )
        contingency = third.slider("Traffic allowance", 0, 30, 10, format="%d%%")
        result = trip_estimate(distance, efficiency, price, contingency)
        left, right = st.columns(2)
        left.metric("Fuel required", f"{result['litres']:.2f} L")
        right.metric("Estimated trip cost", f"KSh {result['cost']:,.2f}")
        st.caption("Include the return leg in the journey distance where applicable.")


def evidence_page(
    history: pd.DataFrame,
    component_history: pd.DataFrame,
    sources: pd.DataFrame,
) -> None:
    st.header("Data and methodology")
    st.caption(
        "The application uses a continuous Nairobi price history, a reviewed EPRA "
        "component panel and a first-party source register."
    )

    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="evidence_fuel")
    fuel_column = FUEL_COLUMNS[fuel]
    result = get_forecast(fuel_column)

    st.line_chart(
        history.set_index("Cycle")[[fuel_column]].rename(
            columns={fuel_column: "KSh per litre"}
        )
    )

    columns = st.columns(4)
    columns[0].metric("Selected method", result.model_name)
    columns[1].metric("Holdout MAE", f"KSh {result.mae:.2f}")
    columns[2].metric("Holdout RMSE", f"KSh {result.rmse:.2f}")
    columns[3].metric("Baseline MAE", f"KSh {result.baseline_mae:.2f}")

    st.subheader("Evaluation design")
    st.write(
        "Candidate methods are compared through expanding-window forecasts on an "
        "earlier selection period. The selected method is then evaluated on the "
        "final ten cycles."
    )
    st.caption(
        "The dataset is small and policy-sensitive, so model accuracy should be "
        "interpreted cautiously."
    )

    with st.expander("Verified Nairobi history"):
        columns_to_show = [
            "Cycle",
            "Effective_From",
            "Effective_To",
            *FUEL_COLUMNS.values(),
            "Source_ID",
        ]
        st.dataframe(
            format_table_dates(history[columns_to_show]),
            hide_index=True,
            width="stretch",
        )

    with st.expander("Reviewed component panel"):
        st.dataframe(
            format_table_dates(component_history),
            hide_index=True,
            width="stretch",
        )

    with st.expander("Source register"):
        st.dataframe(format_table_dates(sources), hide_index=True, width="stretch")


def main() -> None:
    st.set_page_config(
        page_title="MafutaPlan",
        page_icon="⛽",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    history, official, components, component_history, sources = load_project_data()
    current = official.iloc[0]
    source_urls = sources.set_index("Source_ID")["URL"].to_dict()

    st.sidebar.title("MafutaPlan")
    st.sidebar.caption("BSc IT final project")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Price build-up",
            "Cost reconstruction",
            "Forecast & scenarios",
            "Calculator",
            "Data & methodology",
        ],
    )
    st.sidebar.divider()
    st.sidebar.caption(
        "Official prices and source records come from EPRA. Forecasts and scenarios "
        "are academic estimates."
    )

    st.title("MafutaPlan")
    st.caption("Nairobi fuel-price analysis and planning")

    if page == "Overview":
        overview_page(official, current, history, source_urls)
    elif page == "Price build-up":
        journey_page(components, source_urls)
    elif page == "Cost reconstruction":
        reconstruction_page(component_history)
    elif page == "Forecast & scenarios":
        forecast_page(history, component_history)
    elif page == "Calculator":
        calculator_page(official)
    else:
        evidence_page(history, component_history, sources)


if __name__ == "__main__":
    main()
