"""Cost-based reconstruction and transparent scenario analysis.

The functions in this module do not pretend that user-entered scenarios are
official EPRA forecasts.  They implement the regulated arithmetic explicitly so
each estimate can be explained component by component.
"""

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
    """Return the pump-price sum of EPRA's five published aggregate groups."""
    return round(sum(float(row[column]) for column in AGGREGATE_COMPONENTS), 2)


def component_shares(row: pd.Series | dict[str, float]) -> dict[str, float]:
    """Return component shares of the reconstructed price as percentages."""
    total = reconstruct_price(row)
    if total <= 0:
        raise ValueError("Reconstructed price must be positive")
    return {column: float(row[column]) / total * 100 for column in AGGREGATE_COMPONENTS}


def scenario_estimate(
    row: pd.Series | dict[str, float],
    *,
    landed_change_pct: float = 0.0,
    distribution_change_pct: float = 0.0,
    margin_change_pct: float = 0.0,
    tax_change: float = 0.0,
    stabilization_adjustment: float | None = None,
) -> ScenarioResult:
    """Apply transparent what-if changes to one reviewed EPRA component row.

    Percentage changes are multiplicative. ``tax_change`` is an absolute
    KES/litre policy change, while stabilization can be explicitly overridden.
    """
    if landed_change_pct < -100 or distribution_change_pct < -100 or margin_change_pct < -100:
        raise ValueError("Percentage reductions cannot be below -100%")
    components = {
        "Landed_Cost": float(row["Landed_Cost"]) * (1 + landed_change_pct / 100),
        "Distribution_Storage": float(row["Distribution_Storage"]) * (1 + distribution_change_pct / 100),
        "Margins": float(row["Margins"]) * (1 + margin_change_pct / 100),
        "Stabilization_Adjustment": (
            float(row["Stabilization_Adjustment"])
            if stabilization_adjustment is None
            else float(stabilization_adjustment)
        ),
        "Taxes_Levies": float(row["Taxes_Levies"]) + float(tax_change),
    }
    if any(value < 0 for name, value in components.items() if name != "Stabilization_Adjustment"):
        raise ValueError("Scenario produces a negative cost component")
    base = reconstruct_price(row)
    estimate = round(sum(components.values()), 2)
    return ScenarioResult(base, estimate, round(estimate - base, 2), components)


def reconstruction_audit(frame: pd.DataFrame) -> pd.DataFrame:
    """Recalculate every row and expose differences from official retail price."""
    result = frame.copy()
    result["Calculated_Price"] = result.apply(reconstruct_price, axis=1)
    result["Calculated_Error"] = (result["Calculated_Price"] - result["Retail_Price"]).round(2)
    return result
