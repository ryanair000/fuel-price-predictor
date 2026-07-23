from __future__ import annotations

from urllib.parse import urlparse

import pandas as pd

from .paths import COMPONENT_HISTORY_PATH, COMPONENTS_PATH, HISTORY_PATH, OFFICIAL_PRICES_PATH, SOURCES_PATH

FUEL_COLUMNS = {"Super Petrol": "Super_Petrol", "Diesel": "Diesel", "Kerosene": "Kerosene"}
PRICE_COLUMNS = list(FUEL_COLUMNS.values())
HISTORY_COLUMNS = ["Cycle", "Effective_From", "Effective_To", *PRICE_COLUMNS, "Source_ID"]


def _require(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")
    if frame[columns].isna().any().any():
        raise ValueError(f"{label} contains blank values in required columns")


def _validate_prices(frame: pd.DataFrame, label: str) -> None:
    frame[PRICE_COLUMNS] = frame[PRICE_COLUMNS].apply(pd.to_numeric, errors="raise")
    if (frame[PRICE_COLUMNS] <= 0).any().any():
        raise ValueError(f"{label} prices must be positive")


def load_sources(path=SOURCES_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = ["Source_ID", "Publisher", "Title", "URL", "Accessed_On", "Notes"]
    _require(frame, columns, "Source register")
    if frame["Source_ID"].duplicated().any():
        raise ValueError("Source register contains duplicate Source_ID values")
    invalid = frame.loc[~frame["URL"].map(lambda value: urlparse(str(value)).scheme == "https")]
    if not invalid.empty:
        raise ValueError("Every source must use an HTTPS URL")
    frame["Accessed_On"] = pd.to_datetime(frame["Accessed_On"], errors="raise")
    return frame


def load_history(path=HISTORY_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    _require(frame, HISTORY_COLUMNS, "Nairobi price history")
    for column in ["Cycle", "Effective_From", "Effective_To"]:
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    _validate_prices(frame, "Nairobi price history")
    if frame["Cycle"].duplicated().any() or frame["Effective_From"].duplicated().any():
        raise ValueError("Nairobi price history contains duplicate cycles")
    if (frame["Effective_To"] < frame["Effective_From"]).any():
        raise ValueError("An effective period ends before it begins")
    frame = frame.sort_values("Cycle").reset_index(drop=True)
    expected = pd.date_range(frame["Cycle"].min(), frame["Cycle"].max(), freq="MS")
    if not frame["Cycle"].reset_index(drop=True).equals(pd.Series(expected, name="Cycle")):
        raise ValueError("Nairobi price history must contain one continuous row per month")
    known_sources = set(load_sources()["Source_ID"])
    if not set(frame["Source_ID"]).issubset(known_sources):
        raise ValueError("Nairobi price history references an unknown Source_ID")
    frame["Month_num"] = range(1, len(frame) + 1)
    return frame


def load_official_prices(path=OFFICIAL_PRICES_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = ["Effective_From", "Effective_To", "Town", *PRICE_COLUMNS, "Source_ID", "Status"]
    _require(frame, columns, "Current Nairobi price record")
    for column in ["Effective_From", "Effective_To"]:
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    _validate_prices(frame, "Current Nairobi price record")
    if len(frame) != 1 or frame["Town"].iloc[0] != "Nairobi":
        raise ValueError("Current official data must contain exactly one Nairobi record")
    if frame["Effective_To"].iloc[0] < frame["Effective_From"].iloc[0]:
        raise ValueError("Current official price period is invalid")
    if frame["Source_ID"].iloc[0] not in set(load_sources()["Source_ID"]):
        raise ValueError("Current official price references an unknown Source_ID")
    return frame


def load_components(path=COMPONENTS_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = ["Effective_From", "Effective_To", "Fuel", "Component", "Category", "KES_Per_Litre", "Source_ID"]
    _require(frame, columns, "Price-component dataset")
    frame["Effective_From"] = pd.to_datetime(frame["Effective_From"], errors="raise")
    frame["Effective_To"] = pd.to_datetime(frame["Effective_To"], errors="raise")
    frame["KES_Per_Litre"] = pd.to_numeric(frame["KES_Per_Litre"], errors="raise")
    if (frame["KES_Per_Litre"] < 0).any():
        raise ValueError("Price components cannot be negative")
    if frame[["Fuel", "Component"]].duplicated().any():
        raise ValueError("Price-component dataset contains duplicates")
    return frame


def load_component_history(path=COMPONENT_HISTORY_PATH) -> pd.DataFrame:
    """Load the reviewed multi-cycle aggregate EPRA cost panel."""
    frame = pd.read_csv(path)
    columns = [
        "Effective_From", "Effective_To", "Fuel", "Landed_Cost",
        "Distribution_Storage", "Margins", "Stabilization_Adjustment",
        "Taxes_Levies", "Retail_Price", "Reconstructed_Price",
        "Reconstruction_Error", "PDF_URL", "Verification_Status",
    ]
    _require(frame, columns, "Nairobi component history")
    for column in ["Effective_From", "Effective_To"]:
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    numeric = [
        "Landed_Cost", "Distribution_Storage", "Margins",
        "Stabilization_Adjustment", "Taxes_Levies", "Retail_Price",
        "Reconstructed_Price", "Reconstruction_Error",
    ]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="raise")
    if frame[["Effective_From", "Fuel"]].duplicated().any():
        raise ValueError("Nairobi component history contains duplicate fuel-cycle rows")
    if set(frame["Fuel"]) != set(FUEL_COLUMNS):
        raise ValueError("Nairobi component history must cover all three fuel products")
    if not frame["PDF_URL"].str.startswith("https://").all():
        raise ValueError("Every component-history row must link to HTTPS evidence")
    if frame["Reconstruction_Error"].abs().max() > 0.02:
        raise ValueError("Component reconstruction does not reconcile to EPRA retail prices")
    return frame.sort_values(["Effective_From", "Fuel"]).reset_index(drop=True)


def get_price(frame: pd.DataFrame, fuel: str) -> float:
    if fuel not in FUEL_COLUMNS:
        raise ValueError(f"Unknown fuel type: {fuel}")
    return float(frame[FUEL_COLUMNS[fuel]].iloc[0])
