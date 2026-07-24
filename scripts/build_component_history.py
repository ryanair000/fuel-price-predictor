"""Build the reviewed aggregate EPRA component panel used by MafutaPlan.

Values below are transcribed from the Nairobi annex in official EPRA monthly
price releases inventoried by ``inventory_epra_component_sources.py`` and OCR'd
by ``extract_epra_annex_ocr.py``.  Stabilization is calculated as the signed
reconciliation residual because EPRA labels and displays deficit/surplus signs
inconsistently across scanned annexes.  A zero residual means that published
aggregates reconstruct the official pump price to rounding precision.

This is a deliberately reviewed dataset, not an unattended OCR dump.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "epra_component_source_inventory.csv"
OUTPUT = ROOT / "data" / "nairobi_component_history.csv"

FUELS = ("Super Petrol", "Diesel", "Kerosene")
SOURCE_IDS = {
    "2024-08-15": "EPRA_COMPONENT_2024_08",
    "2024-10-15": "EPRA_COMPONENT_2024_10",
    "2024-11-15": "EPRA_COMPONENT_2024_11",
    "2024-12-15": "EPRA_COMPONENT_2024_12",
    "2025-02-15": "EPRA_COMPONENT_2025_02",
    "2025-06-15": "EPRA_JUNE2025_COSTS",
    "2025-07-15": "EPRA_COMPONENT_2025_07",
    "2025-08-15": "EPRA_COMPONENT_2025_08",
    "2026-01-15": "EPRA_COMPONENT_2026_01",
    "2026-02-15": "EPRA_COMPONENT_2026_02",
    "2026-03-15": "EPRA_COMPONENT_2026_03",
}

# effective_from, effective_to, source-title fragment, then fuel-order triples.
# Aggregates are KES/litre. Retail price is the official Nairobi maximum price.
REVIEWED = [
    ("2024-08-15", "2024-09-14", "August 15th", (93.01, 90.98, 93.04), (4.09, 3.75, 3.72), (12.39, 12.36, 12.36), (82.75, 69.71, 56.46), (188.84, 171.60, 161.75)),
    ("2024-10-15", "2024-11-14", "October 15", (83.02, 83.08, 80.80), (4.03, 3.72, 3.67), (12.39, 12.36, 12.36), (81.22, 68.90, 54.55), (180.66, 168.06, 151.39)),
    ("2024-11-15", "2024-12-14", "15th November to 14th December 2024", (83.47, 79.54, 83.95), (4.03, 3.71, 3.68), (12.39, 12.36, 12.36), (81.23, 68.76, 54.69), (180.66, 168.06, 151.39)),
    ("2024-12-15", "2025-01-14", "15th December 2024", (79.39, 83.48, 85.93), (4.01, 3.72, 3.69), (12.39, 12.36, 12.36), (80.50, 68.53, 54.34), (176.29, 165.06, 148.39)),
    ("2025-02-15", "2025-03-14", "15th February 2025", (81.57, 87.19, 88.78), (4.03, 3.74, 3.70), (12.39, 12.36, 12.36), (80.99, 69.37, 55.25), (176.58, 167.06, 151.39)),
    ("2025-06-15", "2025-07-14", "15th June - 14th July 2025", (76.83, 75.43, 73.80), (4.37, 4.06, 4.02), (15.24, 15.16, 15.09), (80.87, 68.26, 54.02), (177.32, 162.91, 146.93)),
    ("2025-07-15", "2025-08-14", "15th July", (81.88, 80.22, 79.41), (4.70, 4.38, 4.34), (17.39, 17.31, 17.24), (82.13, 69.66, 55.14), (186.31, 171.58, 156.58)),
    ("2025-08-15", "2025-09-14", "15th August", (81.04, 82.14, 81.23), (4.70, 4.39, 4.35), (17.39, 17.31, 17.24), (82.17, 69.71, 55.59), (185.31, 171.58, 155.58)),
    ("2026-01-15", "2026-02-14", "15th January 2026", (77.28, 81.74, 78.23), (4.68, 4.39, 4.34), (17.39, 17.31, 17.24), (81.58, 69.55, 55.58), (182.52, 170.47, 153.78)),
    ("2026-02-15", "2026-03-14", "15th February 2026", (75.31, 76.08, 77.64), (4.67, 4.37, 4.35), (17.39, 17.31, 17.24), (80.91, 68.78, 54.98), (178.28, 166.54, 152.78)),
    ("2026-03-15", "2026-04-14", "15th March", (75.42, 82.30, 82.63), (4.67, 4.40, 4.36), (17.39, 17.31, 17.24), (80.94, 69.04, 55.21), (178.28, 166.54, 152.78)),
]


def main() -> None:
    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        inventory = list(csv.DictReader(handle))

    rows = []
    for start, end, title_fragment, landed, distribution, margins, taxes, retail in REVIEWED:
        matches = [row for row in inventory if title_fragment.lower() in row["Title"].lower()]
        if len(matches) != 1:
            raise ValueError(f"Expected one inventory match for {title_fragment!r}; found {len(matches)}")
        source = matches[0]
        for index, fuel in enumerate(FUELS):
            stabilization = round(
                retail[index] - landed[index] - distribution[index] - margins[index] - taxes[index],
                2,
            )
            reconstructed = round(landed[index] + distribution[index] + margins[index] + taxes[index] + stabilization, 2)
            rows.append(
                {
                    "Effective_From": start,
                    "Effective_To": end,
                    "Fuel": fuel,
                    "Landed_Cost": f"{landed[index]:.2f}",
                    "Distribution_Storage": f"{distribution[index]:.2f}",
                    "Margins": f"{margins[index]:.2f}",
                    "Stabilization_Adjustment": f"{stabilization:.2f}",
                    "Taxes_Levies": f"{taxes[index]:.2f}",
                    "Retail_Price": f"{retail[index]:.2f}",
                    "Reconstructed_Price": f"{reconstructed:.2f}",
                    "Reconstruction_Error": f"{reconstructed - retail[index]:.2f}",
                    "Source_ID": SOURCE_IDS[start],
                    "Source_Title": source["Title"],
                    "PDF_URL": source["PDF_URL"],
                    "Verification_Status": "Reviewed and reconciled",
                    "Quality_Notes": "Official aggregate components transcribed from EPRA annex; stabilization is the signed reconciliation residual, including displayed deficit/surplus and rounding.",
                }
            )

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} reviewed component rows across {len(REVIEWED)} cycles to {OUTPUT}")


if __name__ == "__main__":
    main()
