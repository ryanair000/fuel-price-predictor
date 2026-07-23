# MafutaPlan Full Implementation and Supervisor Review

## 1. Final project identity

**Academic title:** Design and Implementation of a Hybrid Cost-Based Model for Forecasting Regulated Fuel Prices in Nairobi, Kenya

**Product name:** MafutaPlan

**Project type:** Bachelor of Science in Information Technology final project

**Selected town:** Nairobi

Nairobi is the strongest town choice because it is consistently present in EPRA notices, is widely used as the public reference market, has the best continuity for manual verification, and keeps one coherent distribution-cost path. Expanding to many towns would require a separately verified secondary-distribution history for each town and would weaken the core study.

## 2. Purpose

MafutaPlan is a source-backed decision-support system that explains, reconstructs and cautiously forecasts regulated fuel prices in Nairobi. It solves four connected problems:

1. Official price announcements state the cap but do not make the full cost chain easy to understand.
2. A pump price is not equal to crude oil price or landed product cost; it also contains freight, landing, Mombasa-to-Nairobi transport, storage, losses, margins, taxes, levies and stabilization.
3. A next-cycle estimate must be tested on future points and must not use information that would be unknown at the forecast date.
4. End users need practical purchase, budget and journey calculations in addition to a prediction.

## 3. Clients and stakeholders

### Primary users

- Nairobi private motorists planning fuel purchases and trips.
- Household and small-commercial kerosene users planning expenditure.

### Secondary users

- Matatu, taxi, delivery, transport and logistics operators.
- Small businesses whose operating costs depend on fuel.
- Students, supervisors, researchers and policy analysts reviewing price drivers.

### Evidence authority

EPRA is the regulator and authoritative source. It is not treated as the software client. KNBS, the Ministry of Energy and Petroleum, and Kenya Pipeline Company provide supporting official context.

## 4. Real petroleum journey represented by the system

Kenya's local refinery stopped processing crude oil in 2013. The operational route used in this project therefore begins with imported **refined petroleum products**, not an assumed local crude-refining process.

```text
International refined-product procurement
        ↓
FOB/product benchmark + supplier premium
        ↓
Ocean freight + insurance + financing + certification
        ↓
Mombasa port/jetty handling + inspection + allowable losses
        ↓
Primary storage in Mombasa
        ↓
Kenya Pipeline Company transport to Nairobi
        ↓
Pipeline loss + Nairobi depot/storage loss
        ↓
Delivery to retail stations
        ↓
Importer/wholesale margin + dealer/retail margin
        ↓
Excise duty + VAT + statutory levies
        ↓
Price stabilization deficit/surplus
        ↓
EPRA maximum retail pump price in Nairobi
```

The detailed EPRA cost register includes landed cost, pipeline transport, road bridging where applicable, pipeline loss, depot loss, delivery, importer margin, dealer margin, excise duty, Road Maintenance Levy, Petroleum Development Levy, Petroleum Regulatory Levy, Railway Development Levy, Anti-adulteration Levy, Merchant Shipping Levy, Import Declaration Fee, VAT and stabilization.

## 5. What is predicted and what is calculated

### A. Official-price reconstruction

This is deterministic arithmetic, not regression:

```text
Retail price = landed cost
             + distribution and storage
             + wholesale and retail margins
             + taxes and levies
             + signed stabilization adjustment
```

The reviewed dataset has 33 fuel-cycle rows from 11 official EPRA Annex cycles. Every row reconstructs the corresponding retail price with zero error after rounding.

### B. Next-cycle statistical forecast

This compares five candidates:

- Previous-cycle baseline.
- Linear regression.
- Ridge regression.
- Random forest regression.
- Gradient boosting regression.

The model-selection period uses expanding windows. The final ten cycles are held back and used only once after selection. The previous-cycle baseline currently wins for all three fuels. This is an academically acceptable result: regression was tested, but a simpler method performed better on the available sample.

### C. Cost scenario

The user may change landed-cost percentage, distribution/storage percentage, margin percentage, taxes/levies in KES per litre and stabilization in KES per litre. This is labelled a **what-if scenario**, not an EPRA prediction.

## 6. Model inputs

### Statistical forecast inputs

- Sequential month index.
- Calendar-month sine term.
- Calendar-month cosine term.
- Previous-cycle price.
- Price two cycles earlier.
- Mean of the preceding three cycles.

These values are available before the forecast target. Same-cycle future exchange rates, crude-oil averages or landed costs are excluded to prevent leakage.

### Cost-reconstruction inputs

- Landed refined-product cost.
- Distribution and storage from Mombasa to Nairobi.
- Wholesale and retail margins.
- Taxes and levies.
- Signed stabilization adjustment.

### Scenario inputs

- Fuel product.
- Reviewed EPRA component basis cycle.
- Percentage change in landed cost.
- Percentage change in distribution/storage.
- Percentage change in margins.
- Absolute tax/levy change.
- Stabilization adjustment.

### Calculator inputs

- Fuel product.
- Litres or budget.
- Complete trip distance.
- Vehicle efficiency in kilometres per litre.
- Traffic/contingency allowance.

## 7. Real datasets implemented

| File | Coverage | Role |
|---|---:|---|
| `data/nairobi_price_history.csv` | 55 monthly cycles | Forecast target and trends |
| `data/current_nairobi_price.csv` | One active cycle | Current official cards and calculators |
| `data/price_components.csv` | 53 detailed items | Item-level official cost explanation |
| `data/nairobi_component_history.csv` | 33 rows / 11 cycles | Multi-cycle reconstruction and scenarios |
| `data/epra_component_source_inventory.csv` | 23 releases | Official Annex acquisition register |
| `data/epra_annex_ocr_audit.csv` | 23 audit records | PDF, page, OCR hash and extraction status |
| `data/epra_live_nairobi_extract.csv` | 21 live rows | Independent EPRA table extract |
| `data/epra_pump_price_comparison.csv` | 21 comparisons | Live-versus-archive reconciliation |
| `data/price_revisions_2026.csv` | Four events | Original and superseded price audit |
| `data/sources.csv` | Source register | Publisher, title, URL and provenance notes |

The live-table audit found 20 out of 20 comparable final Nairobi records matching. The extra live row is the original 15 April 2026 announcement; the local model correctly uses the superseding 16 April record and retains the original in the revision file.

## 8. Data-quality decisions

- Official EPRA sources control when conflicting values exist.
- Raw scanned values are never accepted automatically.
- Every reviewed component record links to the exact official PDF.
- OCR text is fingerprinted with SHA-256 for auditability.
- Degraded scans are marked for manual review and excluded rather than guessed.
- Stabilization is calculated as a signed reconciliation residual when OCR loses parentheses or sign notation.
- Future-cycle inputs are not used in historical model evaluation.
- Revisions are preserved rather than overwritten.

The main remaining data limitation is the component panel's coverage. Eleven reviewed cycles are suitable for reconstruction and exploratory component analysis but are too short and discontinuous for a strong standalone production regression of future landed cost. A continuous 36-cycle panel is the recommended minimum extension.

## 9. Application architecture

```text
Official EPRA evidence
    ├── Pump-price history
    ├── Current official cap
    ├── Annex PDFs
    ├── Source/OCR audit
    └── Revision register
            ↓
Validated Python data layer
            ↓
    ├── Reconstruction service
    ├── Scenario service
    ├── Forecast evaluation service
    └── Purchase/budget/trip calculators
            ↓
Six-workflow Streamlit interface
```

## 10. Implemented website workflows

1. **Overview** — current official cards and full historical trend.
2. **Fuel price journey** — eight-stage supply-chain explanation and detailed Annex example.
3. **Cost reconstruction** — cycle and fuel selector, exact reconstruction, component chart, shares and source link.
4. **Forecast and scenarios** — separate tabs for next-cycle statistical forecast, component scenario and the regression explanation.
5. **Planning calculator** — cost for litres, litres for budget and trip cost.
6. **Evidence and methodology** — history, component panel, features, metrics, source register and limitations.

## 11. Reproducibility scripts

| Script | Function |
|---|---|
| `scripts/inventory_epra_component_sources.py` | Discovers EPRA release pages and PDFs |
| `scripts/extract_epra_annex_ocr.py` | Downloads, renders, OCRs and fingerprints Annex pages |
| `scripts/build_component_history.py` | Builds the reviewed aggregate panel |
| `scripts/audit_epra_pump_prices.py` | Compares the live EPRA table with local history |
| `scripts/build_notebook.py` | Generates the analysis notebook |
| `scripts/build_report.py` | Generates the final project report |

## 12. Verification completed

- The analysis notebook executes top-to-bottom and stores its outputs.
- Automated tests cover files, town scope, date continuity, provenance, official spot values, detailed components, multi-cycle reconstruction, scenarios, calculators, leakage safeguards, forecasts and charts.
- The application runs on `http://localhost:8501`.
- Browser inspection confirmed the six navigation workflows, current official price cards and supervisor-facing project description render in the real app.
- Python modules and scripts are compiled before final handoff.

## 13. How to defend the project

### If asked, “Is this regression?”

Answer: “Regression is one evaluated forecasting family. The system compares linear and ridge regression with tree ensembles and a previous-cycle benchmark. The benchmark currently wins out of sample. The price build-up itself is deterministic regulated arithmetic, while scenarios are user-controlled.”

### If asked, “Why Nairobi?”

Answer: “Nairobi gives the strongest official continuity, a consistent Mombasa-to-Nairobi logistics path and a large real user base. Selecting one town removes geographical mixing and makes every cost and target comparable.”

### If asked, “Where are landing and transport costs?”

Answer: “They are explicitly represented. Landed cost covers the imported-product stage, while the distribution group covers pipeline transport from Mombasa, losses, depot storage and delivery within Nairobi. Detailed individual components are also retained for the June 2025 worked example.”

### If asked, “Why not use crude oil directly?”

Answer: “Kenya imports refined petroleum products and has not operated the Mombasa refinery since 2013. Crude price is contextual, but the regulated formula uses the cost of imported finished products plus local costs and policy terms.”

### If asked, “Why is the forecast not fully component-regression based?”

Answer: “Only 11 component cycles are currently readable and reviewed, with gaps. Using that short panel as a production regression would overstate validity. The project implements full cost reconstruction and scenarios now, retains a leakage-safe price forecast, and defines a 36-cycle data gate before upgrading landed-cost prediction.”

## 14. Best next academic extension

The best extension is not adding more towns. It is completing a continuous Nairobi Annex history of at least 36 cycles and adding lagged, timestamped external drivers that would truly have been available at each forecast origin:

- USD/KES exchange rate.
- International refined-product benchmarks for PMS, AGO and DPK.
- Freight/premium and insurance terms where published.
- Known tax/levy policy schedule.
- Stabilization regime indicator.

The upgraded study should forecast landed cost first, carry known regulated terms, provide stabilization scenarios and compare the final hybrid price with persistence and direct price regression.

## 15. Run and verify

```powershell
python -m pip install -r requirements.txt
python scripts\audit_epra_pump_prices.py
python scripts\build_component_history.py
python -m unittest discover -s tests -v
python -m compileall app.py src scripts tests
streamlit run app.py
```

Open `http://localhost:8501`.
