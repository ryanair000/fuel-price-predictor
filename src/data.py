from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from .paths import (
    COMPONENT_HISTORY_PATH,
    OFFICIAL_PRICES_PATH,
    PREDICTION_DATASET_PATH,
    SOURCES_PATH,
)

PathLike = str | Path

FUEL_COLUMNS = {
    "Super Petrol": "Super_Petrol",
    "Diesel": "Diesel",
    "Kerosene": "Kerosene",
}
PRICE_COLUMNS = list(FUEL_COLUMNS.values())
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


def load_component_history(
    path: PathLike = COMPONENT_HISTORY_PATH,
    sources_path: PathLike = SOURCES_PATH,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = [
        "Effective_From",
        "Effective_To",
        "Fuel",
        *COMPONENT_COLUMNS,
        "Retail_Price",
        "Reconstructed_Price",
        "Reconstruction_Error",
        "Source_ID",
        "Source_Title",
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
    if not set(frame["Source_ID"]).issubset(_registered_source_ids(sources_path)):
        raise ValueError("Component history references an unknown Source_ID")

    calculated = frame[COMPONENT_COLUMNS].sum(axis=1).round(2)
    if (calculated - frame["Reconstructed_Price"]).abs().max() > 0.01:
        raise ValueError("Stored reconstructed prices do not match their components")
    if (calculated - frame["Retail_Price"]).abs().max() > 0.02:
        raise ValueError("Component reconstruction does not reconcile to EPRA prices")
    if frame["Reconstruction_Error"].abs().max() > 0.02:
        raise ValueError("Recorded reconstruction error exceeds the allowed tolerance")

    return frame.sort_values(["Effective_From", "Fuel"]).reset_index(drop=True)


def load_prediction_dataset(
    path: PathLike = PREDICTION_DATASET_PATH,
    sources_path: PathLike = SOURCES_PATH,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = [
        "Input_Cycle",
        "Target_Cycle",
        "Fuel",
        *COMPONENT_COLUMNS,
        "Target_Retail_Price",
        "Source_ID",
        "Verification_Status",
    ]
    _require(frame, columns, "Component prediction dataset")
    _parse_dates(frame, ("Input_Cycle", "Target_Cycle"))

    numeric = [*COMPONENT_COLUMNS, "Target_Retail_Price"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="raise")
    if frame[["Input_Cycle", "Fuel"]].duplicated().any():
        raise ValueError("Component prediction dataset contains duplicate records")
    if not set(frame["Fuel"]).issubset(FUEL_COLUMNS):
        raise ValueError("Component prediction dataset contains an unknown fuel")
    if (frame["Target_Cycle"] <= frame["Input_Cycle"]).any():
        raise ValueError("Every target cycle must follow its input cycle")
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Component prediction dataset contains infinite values")
    if not set(frame["Source_ID"]).issubset(_registered_source_ids(sources_path)):
        raise ValueError("Component prediction dataset references an unknown Source_ID")
    if frame["Verification_Status"].str.strip().eq("").any():
        raise ValueError("Every prediction record needs a verification status")

    return frame.sort_values(["Target_Cycle", "Fuel"]).reset_index(drop=True)
