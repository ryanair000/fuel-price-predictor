from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURE_COLUMNS = ["Month_num", "Month_sin", "Month_cos", "Lag_1", "Lag_2", "Rolling_3"]


@dataclass
class ForecastResult:
    fuel_column: str
    model_name: str
    prediction: float
    lower: float
    upper: float
    mae: float
    rmse: float
    baseline_mae: float
    selection_mae: float
    selection_points: int
    validation_points: int
    empirical_coverage: float
    next_date: pd.Timestamp


def create_lagged_data(data: pd.DataFrame, fuel_column: str) -> pd.DataFrame:
    if fuel_column not in data:
        raise ValueError(f"Unknown fuel column: {fuel_column}")
    frame = data.copy()
    frame["Month_sin"] = np.sin(2 * np.pi * frame["Cycle"].dt.month / 12)
    frame["Month_cos"] = np.cos(2 * np.pi * frame["Cycle"].dt.month / 12)
    frame["Lag_1"] = frame[fuel_column].shift(1)
    frame["Lag_2"] = frame[fuel_column].shift(2)
    frame["Rolling_3"] = frame[fuel_column].shift(1).rolling(3).mean()
    return frame.dropna().reset_index(drop=True)


def _candidates() -> dict[str, object]:
    return {
        "Linear regression": LinearRegression(),
        "Ridge regression": Ridge(alpha=10.0),
        "Random forest": RandomForestRegressor(n_estimators=20, min_samples_leaf=3, random_state=42, n_jobs=1),
        "Gradient boosting": GradientBoostingRegressor(n_estimators=30, max_depth=2, learning_rate=0.06, random_state=42),
    }


def _walk_forward(frame: pd.DataFrame, fuel_column: str, model: object, min_train: int) -> tuple[np.ndarray, np.ndarray]:
    actual, predicted = [], []
    for index in range(min_train, len(frame)):
        train, test = frame.iloc[:index], frame.iloc[[index]]
        fitted = clone(model).fit(train[FEATURE_COLUMNS], train[fuel_column])
        actual.append(float(test[fuel_column].iloc[0]))
        predicted.append(float(fitted.predict(test[FEATURE_COLUMNS])[0]))
    return np.asarray(actual), np.asarray(predicted)


def forecast_fuel(data: pd.DataFrame, fuel_column: str, min_train: int = 24, holdout_points: int = 10) -> ForecastResult:
    frame = create_lagged_data(data, fuel_column)
    selection_end = len(frame) - holdout_points
    if selection_end <= min_train + 5 or holdout_points < 6:
        raise ValueError("Insufficient observations for model selection and final holdout testing")
    selection_actual = frame[fuel_column].iloc[min_train:selection_end].to_numpy(dtype=float)
    selection_baseline = frame["Lag_1"].iloc[min_train:selection_end].to_numpy(dtype=float)
    scores: list[tuple[float, str, object | None]] = [
        (float(mean_absolute_error(selection_actual, selection_baseline)), "Previous-cycle baseline", None)
    ]
    for name, candidate in _candidates().items():
        y_true, predictions = _walk_forward(frame, fuel_column, candidate, min_train)
        selection_count = selection_end - min_train
        scores.append((float(mean_absolute_error(y_true[:selection_count], predictions[:selection_count])), name, candidate))
    selection_mae, best_name, best_model = min(scores, key=lambda item: item[0])
    actual = frame[fuel_column].iloc[selection_end:].to_numpy(dtype=float)
    baseline_predictions = frame["Lag_1"].iloc[selection_end:].to_numpy(dtype=float)
    if best_model is None:
        best_predictions = baseline_predictions
    else:
        all_actual, all_predictions = _walk_forward(frame, fuel_column, best_model, selection_end)
        actual, best_predictions = all_actual, all_predictions
    best_mae = float(mean_absolute_error(actual, best_predictions))
    baseline_mae = float(mean_absolute_error(actual, baseline_predictions))
    residuals = actual - best_predictions
    next_cycle = data["Cycle"].iloc[-1] + pd.DateOffset(months=1)
    next_month_num = int(data["Month_num"].iloc[-1] + 1)
    future = pd.DataFrame({
        "Month_num": [next_month_num],
        "Month_sin": [np.sin(2 * np.pi * next_cycle.month / 12)],
        "Month_cos": [np.cos(2 * np.pi * next_cycle.month / 12)],
        "Lag_1": [float(data[fuel_column].iloc[-1])],
        "Lag_2": [float(data[fuel_column].iloc[-2])],
        "Rolling_3": [float(data[fuel_column].iloc[-3:].mean())],
    })
    if best_model is None:
        prediction = float(future["Lag_1"].iloc[0])
    else:
        prediction = float(clone(best_model).fit(frame[FEATURE_COLUMNS], frame[fuel_column]).predict(future)[0])
    lower_q, upper_q = np.quantile(residuals, [0.1, 0.9])
    lower, upper = max(0.0, prediction + float(lower_q)), prediction + float(upper_q)
    covered = np.mean((actual >= best_predictions + lower_q) & (actual <= best_predictions + upper_q))
    return ForecastResult(
        fuel_column=fuel_column, model_name=best_name, prediction=prediction, lower=lower, upper=upper,
        mae=best_mae, rmse=float(mean_squared_error(actual, best_predictions) ** 0.5), baseline_mae=baseline_mae,
        selection_mae=selection_mae, selection_points=selection_end - min_train,
        validation_points=len(actual), empirical_coverage=float(covered), next_date=next_cycle,
    )


def build_trend_chart(data: pd.DataFrame, fuel_column: str, result: ForecastResult) -> pd.DataFrame:
    history = data[["Cycle", fuel_column]].rename(columns={fuel_column: "Historical"}).set_index("Cycle")
    forecast = pd.Series([float(data[fuel_column].iloc[-1]), result.prediction], index=[data["Cycle"].iloc[-1], result.next_date], name="Forecast")
    return history.join(forecast, how="outer")
