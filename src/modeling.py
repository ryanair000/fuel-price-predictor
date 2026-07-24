from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

COMPONENT_FEATURES = [
    "Landed_Cost",
    "Distribution_Storage",
    "Margins",
    "Stabilization_Adjustment",
    "Taxes_Levies",
]
FUEL_EFFECT_COLUMNS = ["Fuel_Diesel", "Fuel_Kerosene"]
MODEL_FEATURES = [*COMPONENT_FEATURES, *FUEL_EFFECT_COLUMNS]
TARGET_COLUMN = "Target_Retail_Price"
JULY_2026_CYCLE = pd.Timestamp("2026-07-01")


class DataAvailabilityError(ValueError):
    """Raised when verified pre-target inputs are not available."""


@dataclass(frozen=True)
class ModelEvaluation:
    model: LinearRegression
    coefficients: pd.DataFrame
    results: pd.DataFrame
    training_start: pd.Timestamp
    training_end: pd.Timestamp
    test_cycle: pd.Timestamp
    training_records: int
    test_records: int
    mae: float
    rmse: float


def design_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Encode the five component groups and fuel type for pooled regression."""
    required = [*COMPONENT_FEATURES, "Fuel"]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"Model data is missing: {', '.join(missing)}")

    matrix = frame[COMPONENT_FEATURES].astype(float).copy()
    matrix["Fuel_Diesel"] = frame["Fuel"].eq("Diesel").astype(int)
    matrix["Fuel_Kerosene"] = frame["Fuel"].eq("Kerosene").astype(int)
    return matrix[MODEL_FEATURES]


def fit_linear_regression(frame: pd.DataFrame) -> LinearRegression:
    if len(frame) < len(MODEL_FEATURES) + 1:
        raise ValueError("Too few records to fit the linear regression model")
    model = LinearRegression()
    model.fit(design_matrix(frame), frame[TARGET_COLUMN].astype(float))
    return model


def coefficient_table(model: LinearRegression) -> pd.DataFrame:
    values = [float(model.intercept_), *[float(value) for value in model.coef_]]
    return pd.DataFrame(
        {
            "Term": ["Intercept", *MODEL_FEATURES],
            "Coefficient": values,
        }
    )


def evaluate_latest_cycle(frame: pd.DataFrame) -> ModelEvaluation:
    """Train chronologically and reserve the latest complete target cycle."""
    data = frame.sort_values(["Target_Cycle", "Fuel"]).reset_index(drop=True)
    cycles = data["Target_Cycle"].drop_duplicates().sort_values()
    if len(cycles) < 2:
        raise ValueError("At least two target cycles are required for evaluation")

    test_cycle = pd.Timestamp(cycles.iloc[-1])
    training = data.loc[data["Target_Cycle"] < test_cycle]
    testing = data.loc[data["Target_Cycle"].eq(test_cycle)]
    if set(testing["Fuel"]) != {"Super Petrol", "Diesel", "Kerosene"}:
        raise ValueError("The chronological test cycle must contain all three fuels")

    model = fit_linear_regression(training)
    predictions = model.predict(design_matrix(testing))
    results = testing[["Input_Cycle", "Target_Cycle", "Fuel", TARGET_COLUMN]].copy()
    results["Predicted_Retail_Price"] = predictions
    results["Absolute_Error"] = (
        results["Predicted_Retail_Price"] - results[TARGET_COLUMN]
    ).abs()
    results["Percentage_Error"] = (
        results["Absolute_Error"] / results[TARGET_COLUMN] * 100
    )

    return ModelEvaluation(
        model=model,
        coefficients=coefficient_table(model),
        results=results.reset_index(drop=True),
        training_start=pd.Timestamp(training["Target_Cycle"].min()),
        training_end=pd.Timestamp(training["Target_Cycle"].max()),
        test_cycle=test_cycle,
        training_records=len(training),
        test_records=len(testing),
        mae=float(mean_absolute_error(results[TARGET_COLUMN], predictions)),
        rmse=float(np.sqrt(mean_squared_error(results[TARGET_COLUMN], predictions))),
    )


def predict_for_cycle(
    model: LinearRegression,
    frame: pd.DataFrame,
    target_cycle: pd.Timestamp,
) -> pd.DataFrame:
    target = pd.Timestamp(target_cycle)
    inputs = frame.loc[frame["Target_Cycle"].eq(target)].copy()
    if set(inputs["Fuel"]) != {"Super Petrol", "Diesel", "Kerosene"}:
        raise DataAvailabilityError(
            f"Verified pre-target component inputs are unavailable for "
            f"{target:%B %Y}."
        )
    inputs["Predicted_Retail_Price"] = model.predict(design_matrix(inputs))
    return inputs[
        ["Input_Cycle", "Target_Cycle", "Fuel", "Predicted_Retail_Price"]
    ].reset_index(drop=True)


def predict_july_2026(
    model: LinearRegression,
    frame: pd.DataFrame,
) -> pd.DataFrame:
    return predict_for_cycle(model, frame, JULY_2026_CYCLE)
