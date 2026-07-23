"""Audit the local Nairobi series against EPRA's live pump-price table.

EPRA's current table exposes a rolling subset rather than the full 2022-2026
research period.  This script therefore writes the live Nairobi extract and a
comparison report; it never silently deletes older locally archived cycles.
"""

from __future__ import annotations

from datetime import date
from html import unescape
from pathlib import Path
import re

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.epra.go.ke/pump-prices"
CACHE = ROOT / "tmp" / "pump.html"
LIVE_OUTPUT = ROOT / "data" / "epra_live_nairobi_extract.csv"
AUDIT_OUTPUT = ROOT / "data" / "epra_pump_price_comparison.csv"


def fetch_live() -> pd.DataFrame:
    if CACHE.exists() and date.fromtimestamp(CACHE.stat().st_mtime) == date.today():
        html = CACHE.read_text(encoding="utf-8")
    else:
        response = requests.get(URL, timeout=120, headers={"User-Agent": "MafutaPlan academic data audit/1.0"})
        response.raise_for_status()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(response.text, encoding="utf-8")
        html = response.text
    rows = []
    for table_row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        if "Nairobi" not in table_row:
            continue
        cells = []
        for cell in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", table_row, flags=re.IGNORECASE | re.DOTALL):
            text = re.sub(r"<[^>]+>", " ", cell)
            cells.append(" ".join(unescape(text).split()))
        if len(cells) >= 6 and cells[2].casefold() == "nairobi":
            rows.append(cells[:6])
    frame = pd.DataFrame(rows, columns=["Effective_From", "Effective_To", "Town", "Super_Petrol", "Diesel", "Kerosene"])
    if frame.empty:
        raise ValueError("No Nairobi rows were found in the EPRA live pump-price table")
    for column in ["Effective_From", "Effective_To"]:
        frame[column] = pd.to_datetime(frame[column], format="%d-%m-%Y", errors="raise")
    for column in ["Super_Petrol", "Diesel", "Kerosene"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame["Source_URL"] = URL
    frame["Retrieved_On"] = date.today().isoformat()
    return frame.sort_values("Effective_From").reset_index(drop=True)


def main() -> None:
    live = fetch_live()
    live.to_csv(LIVE_OUTPUT, index=False, date_format="%Y-%m-%d")
    local = pd.read_csv(ROOT / "data" / "nairobi_price_history.csv", parse_dates=["Effective_From"])
    joined = live.merge(local, on="Effective_From", how="left", suffixes=("_Live", "_Local"))
    for fuel in ["Super_Petrol", "Diesel", "Kerosene"]:
        joined[f"{fuel}_Difference"] = (joined[f"{fuel}_Live"] - joined[f"{fuel}_Local"]).round(2)
    joined["Match"] = joined[[f"{fuel}_Difference" for fuel in ["Super_Petrol", "Diesel", "Kerosene"]]].fillna(999).abs().le(0.01).all(axis=1)
    joined.to_csv(AUDIT_OUTPUT, index=False, date_format="%Y-%m-%d")
    print(f"Extracted {len(live)} live Nairobi records; {int(joined['Match'].sum())}/{len(joined)} match the archived series.")
    if not joined["Match"].all():
        mismatches = joined.loc[~joined["Match"], ["Effective_From", "Super_Petrol_Difference", "Diesel_Difference", "Kerosene_Difference"]]
        print(mismatches.to_string(index=False))


if __name__ == "__main__":
    main()
