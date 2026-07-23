"""Inventory official EPRA monthly pump-price releases and their PDF evidence.

This script discovers source pages from EPRA's press-release listing. It does not
infer component values. The inventory is the controlled input for subsequent
download, extraction, reconciliation, and manual verification.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "epra_component_source_inventory.csv"
BASE = "https://www.epra.go.ke"


def clean(value: str) -> str:
    return " ".join(value.split())


def candidate_pages(session: requests.Session) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for page_number in range(7):
        url = f"{BASE}/press-releases" + (f"?page={page_number}" if page_number else "")
        response = session.get(url, timeout=45)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select(".post-title a[href]"):
            title = clean(anchor.get_text(" ", strip=True))
            lowered = title.lower()
            if ("maximum retail" in lowered and "petroleum" in lowered) or "pump prices" in lowered:
                found[urljoin(url, anchor["href"])] = title
    return sorted(((title, url) for url, title in found.items()), key=lambda item: item[1])


def pdf_for_page(session: requests.Session, page_url: str) -> str:
    response = session.get(page_url, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[tuple[int, str]] = []
    for anchor in soup.select("a[href]"):
        href = urljoin(page_url, anchor.get("href", ""))
        if ".pdf" not in href.lower():
            continue
        label = clean(anchor.get_text(" ", strip=True)).lower()
        score = sum(term in (label + " " + href.lower()) for term in ["petroleum", "pump", "price", "retail"])
        if "national values" in label or "governance" in label:
            score -= 10
        candidates.append((score, href))
    return max(candidates, default=(0, ""))[1]


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = "MafutaPlan academic source inventory/1.0"
    rows = []
    for title, page_url in candidate_pages(session):
        years = [int(value) for value in re.findall(r"20\d{2}", title)]
        first_year = min(years) if years else None
        if first_year is not None and first_year < 2024:
            continue
        rows.append(
            {
                "Title": title,
                "Release_Page_URL": page_url,
                "PDF_URL": pdf_for_page(session, page_url),
                "Publisher": "Energy and Petroleum Regulatory Authority",
                "Accessed_On": date.today().isoformat(),
                "Extraction_Status": "Pending",
                "Verification_Status": "Pending",
                "Notes": "Official EPRA monthly release; Annex component table must be reconciled before modelling.",
            }
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    missing = sum(not row["PDF_URL"] for row in rows)
    print(f"Wrote {len(rows)} official release records to {OUTPUT}; {missing} have no discovered PDF URL.")


if __name__ == "__main__":
    main()
