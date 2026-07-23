from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from .paths import (
    COMPONENT_HISTORY_PATH,
    COMPONENTS_PATH,
    HISTORY_PATH,
    OFFICIAL_PRICES_PATH,
    SOURCES_PATH,
)

PathLike = str | Path

FUEL_COLUMNS = {
    "Super Petrol": "Super_Petrol",
    "Diesel": "Diesel",
    "Kerosene": "Kerosene",
}
PRICE_COLUMNS = list(FUEL_COLUMNS.values())
HISTORY_COLUMNS = [
    "Cycle",
    "Effective_From",
    "Effective_To",
    *PRICE_COLUMNS,
    "Source_ID",
]
COMPONENT_COLUMNS = [
    "Landed_Cost",
    "Distribution_Storage",
    "Margins",
    "Stabilization_Adjustment",
    "Taxes_Levies",
]


def _require(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")
    if frame[columns].isna().any().any():
        raise ValueError(f"{label} contains blank values in required columns")


def _parse_dates(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        frame[column] = pd.to_datetime(frame[column], errors="raise")


def _validate_prices(frame: pd.DataFrame, label: str) -> None:
    frame[PRICE_COLUMNS] = frame[PRICE_COLUMNS].apply(pd.to_numeric, errors="raise")
    if (frame[PRICE_COLUMNS] <= 0).any().any():
        raise ValueError(f"{label} prices must be positive")


def _registered_source_ids(path: PathLike = SOURCES_PATH) -> set[str]:
    return set(load_sources(path)["Source_ID"])


def load_sources(path: PathLike = SOURCES_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = ["Source_ID", "Publisher", "Title", "URL", "Accessed_On", "Notes"]
    _require(frame, columns, "Source register")

    if frame["Source_ID"].duplicated().any():
        raise ValueError("Source register contains duplicate Source_ID values")

    valid_https = frame["URL"].map(
        lambda value: urlparse(str(value)).scheme.lower() == "https"
    )
    if not valid_https.all():
        raise ValueError("Every source must use an HTTPS URL")

    frame["Accessed_On"] = pd.to_datetime(frame["Accessed_On"], errors="raise")
    return frame


def load_history(
    path: PathLike = HISTORY_PATH,
    sources_path: PathLike = SOURCES_PATH,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    _require(frame, HISTORY_COLUMNS, "Nairobi price history")
    _parse_dates(frame, ("Cycle", "Effective_From", "Effective_To"))
    _validate_prices(frame, "Nairobi price history")

    if frame["Cycle"].duplicated().any() or frame["Effective_From"].duplicated().any():
        raise ValueError("Nairobi price history contains duplicate cycles")
    if (frame["Effective_To"] < frame["Effective_From"]).any():
        raise ValueError("An effective period ends before it begins")

    frame = frame.sort_values("Cycle").reset_index(drop=True)
    expected = pd.date_range(frame["Cycle"].min(), frame["Cycle"].max(), freq="MS")
    if frame["Cycle"].tolist() != list(expected):
        raise ValueError("Nairobi price history must contain one continuous row per month")

    if not set(frame["Source_ID"]).issubset(_registered_source_ids(sources_path)):
        raise ValueError("Nairobi price history references an unknown Source_ID")

    frame["Month_num"] = range(1, len(frame) + 1)
    return frame


def load_official_prices(
    path: PathLike = OFFICIAL_PRICES_PATH,
    sources_path: PathLike = SOURCES_PATH,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = [
        "Effective_From",
        "Effective_To",
        "Town",
        *PRICE_COLUMNS,
        "Source_ID",
        "Status",
    ]
    _require(frame, columns, "Current Nairobi price record")
    _parse_dates(frame, ("Effective_From", "Effective_To"))
    _validate_prices(frame, "Current Nairobi price record")

    if len(frame) != 1 or frame["Town"].iloc[0] != "Nairobi":
        raise ValueError("Current official data must contain exactly one Nairobi record")
    if frame["Effective_To"].iloc[0] < frame["Effective_From"].iloc[0]:
        raise ValueError("Current official price period is invalid")
    if frame["Source_ID"].iloc[0] not in _registered_source_ids(sources_path):
        raise ValueError("Current official price references an unknown Source_ID")

    return frame


def load_components(
    path: PathLike = COMPONENTS_PATH,
    sources_path: PathLike = SOURCES_PATH,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = [
        "Effective_From",
        "Effective_To",
        "Fuel",
        "Component",
        "Category",
        "KES_Per_Litre",
        "Source_ID",
    ]
    _require(frame, columns, "Price-component dataset")
    _parse_dates(frame, ("Effective_From", "Effective_To"))
    frame["KES_Per_Litre"] = pd.to_numeric(frame["KES_Per_Litre"], errors="raise")

    if (frame["Effective_To"] < frame["Effective_From"]).any():
        raise ValueError("A component effective period ends before it begins")
    if (frame["KES_Per_Litre"] < 0).any():
        raise ValueError("Price components cannot be negative")
    if frame[["Effective_From", "Fuel", "Component"]].duplicated().any():
        raise ValueError("Price-component dataset contains duplicates")
    if not set(frame["Fuel"]).issubset(FUEL_COLUMNS):
        raise ValueError("Price-component dataset contains an unknown fuel product")
    if not set(frame["Source_ID"]).issubset(_registered_source_ids(sources_path)):
        raise ValueError("Price-component dataset references an unknown Source_ID")

    return frame.sort_values(["Effective_From", "Fuel", "Component"]).reset_index(
        drop=True
    )


def load_component_history(path: PathLike = COMPONENT_HISTORY_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = [
        "Effective_From",
        "Effective_To",
        "Fuel",
        *COMPONENT_COLUMNS,
        "Retail_Price",
        "Reconstructed_Price",
        "Reconstruction_Error",
        "PDF_URL",
        "Verification_Status",
        "Quality_Notes",
    ]
    _require(frame, columns, "Nairobi component history")
    _parse_dates(frame, ("Effective_From", "Effective_To"))

    numeric = [
        *COMPONENT_COLUMNS,
        "Retail_Price",
        "Reconstructed_Price",
        "Reconstruction_Error",
    ]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="raise")

    if (frame["Effective_To"] < frame["Effective_From"]).any():
        raise ValueError("A component-history period ends before it begins")
    if frame[["Effective_From", "Fuel"]].duplicated().any():
        raise ValueError("Nairobi component history contains duplicate fuel-cycle rows")
    if set(frame["Fuel"]) != set(FUEL_COLUMNS):
        raise ValueError("Nairobi component history must cover all three fuel products")

    fuels_per_cycle = frame.groupby("Effective_From")["Fuel"].nunique()
    if not fuels_per_cycle.eq(len(FUEL_COLUMNS)).all():
        raise ValueError("Every component cycle must include all three fuel products")

    if not frame["PDF_URL"].astype(str).str.startswith("https://").all():
        raise ValueError("Every component-history row must link to HTTPS evidence")

    calculated = frame[COMPONENT_COLUMNS].sum(axis=1).round(2)
    if (calculated - frame["Reconstructed_Price"]).abs().max() > 0.01:
        raise ValueError("Stored reconstructed prices do not match their components")
    if (calculated - frame["Retail_Price"]).abs().max() > 0.02:
        raise ValueError("Component reconstruction does not reconcile to EPRA prices")
    if frame["Reconstruction_Error"].abs().max() > 0.02:
        raise ValueError("Recorded reconstruction error exceeds the allowed tolerance")

    return frame.sort_values(["Effective_From", "Fuel"]).reset_index(drop=True)


def get_price(frame: pd.DataFrame, fuel: str) -> float:
    if fuel not in FUEL_COLUMNS:
        raise ValueError(f"Unknown fuel type: {fuel}")
    return float(frame[FUEL_COLUMNS[fuel]].iloc[0])
