from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re

import pandas as pd
import requests

EPRA_PUMP_PRICES_URL = "https://epra.go.ke/pump-prices"
EPRA_FETCH_URLS = (
    EPRA_PUMP_PRICES_URL,
    "http://epra.go.ke/pump-prices",
    "https://www.epra.go.ke/pump-prices",
)


def fetch_live_nairobi_prices(timeout: int = 12) -> pd.DataFrame:
    """Read Nairobi rows from EPRA's current public pump-price table."""
    response = None
    for url in EPRA_FETCH_URLS:
        try:
            candidate = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "MafutaPlan academic live-data refresh/1.0"},
            )
            candidate.raise_for_status()
            response = candidate
            break
        except requests.RequestException:
            continue
    if response is None:
        raise ConnectionError("EPRA's public pump-price table could not be reached")

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
