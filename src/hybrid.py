"""Fuel-price reconstruction and scenario calculations."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

AGGREGATE_COMPONENTS = [
    "Landed_Cost",
    "Distribution_Storage",
    "Margins",
    "Stabilization_Adjustment",
    "Taxes_Levies",
]


@dataclass(frozen=True)
class ScenarioResult:
    base_price: float
    estimated_price: float
    change: float
    components: dict[str, float]


def reconstruct_price(row: pd.Series | dict[str, float]) -> float:
    """Sum the five aggregate EPRA price components."""
    return round(sum(float(row[column]) for column in AGGREGATE_COMPONENTS), 2)


def component_shares(row: pd.Series | dict[str, float]) -> dict[str, float]:
    """Calculate each component's percentage share of the reconstructed price."""
    total = reconstruct_price(row)
    if total <= 0:
        raise ValueError("Reconstructed price must be positive")
    return {
        column: float(row[column]) / total * 100
        for column in AGGREGATE_COMPONENTS
    }


def scenario_estimate(
    row: pd.Series | dict[str, float],
    *,
    landed_change_pct: float = 0.0,
    distribution_change_pct: float = 0.0,
    margin_change_pct: float = 0.0,
    tax_change: float = 0.0,
    stabilization_adjustment: float | None = None,
) -> ScenarioResult:
    """Apply user-supplied changes to one reviewed component record."""
    percentage_changes = (
        landed_change_pct,
        distribution_change_pct,
        margin_change_pct,
    )
    if any(change < -100 for change in percentage_changes):
        raise ValueError("Percentage reductions cannot be below -100%")

    components = {
        "Landed_Cost": float(row["Landed_Cost"]) * (1 + landed_change_pct / 100),
        "Distribution_Storage": float(row["Distribution_Storage"])
        * (1 + distribution_change_pct / 100),
        "Margins": float(row["Margins"]) * (1 + margin_change_pct / 100),
        "Stabilization_Adjustment": (
            float(row["Stabilization_Adjustment"])
            if stabilization_adjustment is None
            else float(stabilization_adjustment)
        ),
        "Taxes_Levies": float(row["Taxes_Levies"]) + float(tax_change),
    }

    non_stabilization = (
        value
        for name, value in components.items()
        if name != "Stabilization_Adjustment"
    )
    if any(value < 0 for value in non_stabilization):
        raise ValueError("Scenario produces a negative cost component")

    base_price = reconstruct_price(row)
    estimated_price = round(sum(components.values()), 2)
    return ScenarioResult(
        base_price=base_price,
        estimated_price=estimated_price,
        change=round(estimated_price - base_price, 2),
        components=components,
    )


def reconstruction_audit(frame: pd.DataFrame) -> pd.DataFrame:
    """Recalculate all rows and compare them with the official retail price."""
    result = frame.copy()
    result["Calculated_Price"] = result.apply(reconstruct_price, axis=1)
    result["Calculated_Error"] = (
        result["Calculated_Price"] - result["Retail_Price"]
    ).round(2)
    return result
