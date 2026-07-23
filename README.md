# MafutaPlan: Hybrid Nairobi Fuel-Price Decision-Support System

MafutaPlan is a Bachelor of Science in Information Technology final project focused on one defensible market: Nairobi, Kenya. It explains the complete regulated journey from imported refined petroleum product to the Nairobi pump, reconstructs official EPRA price build-ups, evaluates next-cycle forecasting methods, and supports transparent cost scenarios and personal fuel planning.

The recommended academic title is:

> Design and Implementation of a Hybrid Cost-Based Model for Forecasting Regulated Fuel Prices in Nairobi, Kenya

The complete research and implementation blueprint is in [HYBRID_PROJECT_IMPLEMENTATION_PLAN.md](HYBRID_PROJECT_IMPLEMENTATION_PLAN.md).

## Purpose and users

The project answers: **How can a source-backed information system explain, reconstruct and cautiously forecast Nairobi's regulated fuel prices without treating the international product cost as the final pump price?**

Primary clients are Nairobi motorists and household fuel users. Secondary users are transport/logistics planners, small businesses, researchers, students and policy analysts. EPRA is the authoritative data source and regulator, not the software client.

## Implemented workflows

- **Overview:** active official Nairobi price caps and the complete historical trend.
- **Fuel price journey:** refined-product procurement, ocean and landing charges, Mombasa handling, KPC pipeline transport to Nairobi, depot/delivery costs, margins, taxes and stabilization.
- **Cost reconstruction:** select a real EPRA cycle and exactly reproduce its official Nairobi retail price from five aggregate cost groups.
- **Forecast and scenarios:** compare a time-tested statistical forecast with a clearly separate EPRA-component what-if calculator.
- **Planning calculator:** calculate purchase cost, litres affordable and trip cost using the current official cap.
- **Evidence and methodology:** inspect records, source URLs, features, validation metrics and limitations.

## Real data

| Dataset | Grain and coverage | Purpose |
|---|---|---|
| `data/nairobi_price_history.csv` | 55 monthly Nairobi cycles, Jan 2022-Jul 2026 | Price trend, lags and next-cycle model |
| `data/current_nairobi_price.csv` | One active Nairobi regulatory cycle | Official app headline and calculators |
| `data/price_components.csv` | 53 detailed items for three fuels, Jun-Jul 2025 | Item-by-item supply-chain explanation |
| `data/nairobi_component_history.csv` | 33 reviewed records, 11 EPRA cycles × three fuels | Multi-cycle reconstruction and scenarios |
| `data/epra_component_source_inventory.csv` | 23 official EPRA release pages and PDFs | Source acquisition register |
| `data/epra_annex_ocr_audit.csv` | OCR fingerprint and extraction status per PDF | Reproducibility and manual-review trail |
| `data/price_revisions_2026.csv` | Published 2026 revision trail | Regulatory audit context |
| `data/sources.csv` | First-party and supporting source register | Provenance |

The component panel contains landed cost, Mombasa-to-Nairobi distribution/storage, wholesale and retail margins, taxes/levies, stabilization and the final price. Every reviewed row has an official EPRA PDF URL and zero reconstruction error after rounding.

## What is regression—and what is not

The **price forecast** compares previous-cycle persistence, linear regression, ridge regression, random forest and gradient boosting. It uses expanding-window model selection and a final untouched ten-cycle holdout. The selected method may be the simple baseline when regression does not improve out-of-sample accuracy.

The **price reconstruction** is not regression. It is the regulated identity:

```text
Nairobi pump price
= landed product cost
+ distribution and storage from Mombasa to Nairobi
+ wholesale and retail margins
+ taxes and levies
+ signed stabilization adjustment
```

The **cost scenario** changes only values the user declares. It is not presented as an EPRA forecast. Same-cycle future costs are never inserted into historical predictions, which prevents target leakage.

## Reproduce the official-source pipeline

```powershell
python scripts\inventory_epra_component_sources.py
python scripts\extract_epra_annex_ocr.py
python scripts\build_component_history.py
```

The OCR script needs Tesseract OCR. Raw PDFs, rendered images and OCR text remain under ignored `tmp/`; their hashes and official links are written to the versioned audit file. Some EPRA scans are degraded and remain explicitly marked for manual review rather than silently parsed.

## Run locally

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Verify

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py src scripts tests
python -m pip check
```

## Important limitations

- The pump-price series is only 55 monthly observations; the component panel has 11 reviewed cycles because several official annex scans are technically degraded.
- The current next-cycle model remains price-lag based. The component panel supports explanation, reconstruction and scenarios, but is not yet long or continuous enough for a strong production landed-cost regression.
- Taxes, stabilization, emergency policy changes, procurement timing and exchange-rate movements can create structural breaks.
- Published prices are maximum regulatory caps, not a promise that every station sells at exactly that price.
- This is an academic decision-support prototype, not an EPRA announcement or financial advice.

Author: Ryan Alfred Nyambati — SCT222-0195/2021, Jomo Kenyatta University of Agriculture and Technology.
