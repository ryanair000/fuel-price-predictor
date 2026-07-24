from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re

import pandas as pd
import requests

EPRA_PUMP_PRICES_URL = "https://www.epra.go.ke/pump-prices"


def fetch_live_nairobi_prices(timeout: int = 30) -> pd.DataFrame:
    """Read Nairobi rows from EPRA's current public pump-price table."""
    response = requests.get(
        EPRA_PUMP_PRICES_URL,
        timeout=timeout,
        headers={"User-Agent": "MafutaPlan academic live-data refresh/1.0"},
    )
    response.raise_for_status()

    rows: list[list[str]] = []
    table_rows = re.findall(
        r"<tr\b[^>]*>(.*?)</tr>",
        response.text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for table_row in table_rows:
        if "Nairobi" not in table_row:
            continue
        cells = []
        for cell in re.findall(
            r"<t[dh]\b[^>]*>(.*?)</t[dh]>",
            table_row,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            text = re.sub(r"<[^>]+>", " ", cell)
            cells.append(" ".join(unescape(text).split()))
        if len(cells) >= 6 and cells[2].casefold() == "nairobi":
            rows.append(cells[:6])

    if not rows:
        raise ValueError("EPRA's live table returned no Nairobi records")

    frame = pd.DataFrame(
        rows,
        columns=[
            "Effective_From",
            "Effective_To",
            "Town",
            "Super_Petrol",
            "Diesel",
            "Kerosene",
        ],
    )
    frame["Effective_From"] = pd.to_datetime(
        frame["Effective_From"], format="%d-%m-%Y", errors="raise"
    )
    frame["Effective_To"] = pd.to_datetime(
        frame["Effective_To"], format="%d-%m-%Y", errors="raise"
    )
    for column in ("Super_Petrol", "Diesel", "Kerosene"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    frame["Source_URL"] = EPRA_PUMP_PRICES_URL
    frame["Retrieved_At"] = datetime.now(timezone.utc)
    return (
        frame.drop_duplicates(subset=["Effective_From"], keep="last")
        .sort_values("Effective_From", ascending=False)
        .reset_index(drop=True)
    )
