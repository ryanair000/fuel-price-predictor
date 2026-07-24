"""Build the one-cycle-ahead component dataset from reviewed project records."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PATH = ROOT / "data" / "nairobi_component_history.csv"
HISTORY_PATH = ROOT / "data" / "nairobi_price_history.csv"
OUTPUT_PATH = ROOT / "data" / "component_prediction_dataset.csv"

FUEL_PRICE_COLUMNS = {
    "Super Petrol": "Super_Petrol",
    "Diesel": "Diesel",
    "Kerosene": "Kerosene",
}
COMPONENT_COLUMNS = [
    "Landed_Cost",
    "Distribution_Storage",
    "Margins",
    "Stabilization_Adjustment",
    "Taxes_Levies",
]


def build_dataset() -> pd.DataFrame:
    components = pd.read_csv(COMPONENT_PATH, parse_dates=["Effective_From"])
    history = pd.read_csv(HISTORY_PATH, parse_dates=["Cycle"]).set_index("Cycle")

    records: list[dict[str, object]] = []
    for row in components.itertuples(index=False):
        input_cycle = pd.Timestamp(row.Effective_From).to_period("M").to_timestamp()
        target_cycle = input_cycle + pd.DateOffset(months=1)
        if target_cycle not in history.index:
            raise ValueError(f"Missing target retail price for {target_cycle:%Y-%m}")

        record = {
            "Input_Cycle": input_cycle.date().isoformat(),
            "Target_Cycle": target_cycle.date().isoformat(),
            "Fuel": row.Fuel,
        }
        record.update({column: getattr(row, column) for column in COMPONENT_COLUMNS})
        record["Target_Retail_Price"] = history.loc[
            target_cycle, FUEL_PRICE_COLUMNS[row.Fuel]
        ]
        record["Source_ID"] = row.Source_ID
        record["Verification_Status"] = row.Verification_Status
        records.append(record)

    return pd.DataFrame(records).sort_values(["Target_Cycle", "Fuel"])


def main() -> None:
    build_dataset().to_csv(OUTPUT_PATH, index=False, float_format="%.2f")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
