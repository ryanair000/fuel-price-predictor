# MafutaPlan

**Project title:** Design and Implementation of a Component-Based Fuel Price
Prediction System Using Multiple Linear Regression in Nairobi, Kenya

MafutaPlan is a final-year BSc Information Technology project for Nairobi
transport operators and small transport businesses that need fuel-price
information for budgeting and journey-cost planning.

The application supports four clearly separated functions:

- **Prediction:** pooled multiple linear regression using pre-target components
  and encoded fuel type.
- **Reconstruction:** deterministic addition of five known component groups from
  the same historical cycle.
- **Scenario analysis:** deterministic what-if changes to reviewed components.
- **Fuel calculations:** purchase, budget, and journey-cost formulas.

## July 2026 target and data limitation

The final target is the July 2026 Nairobi maximum retail price for Super
Petrol, Diesel, and Kerosene. July components are never used to predict July.
The intended design is:

```text
Verified June 2026 components
              ↓
Multiple linear regression
              ↓
Predicted July 2026 price
              ↓
Comparison with official July price
```

The repository currently has no verified June 2026 component record. It
therefore does **not** publish July predictions or fabricated July accuracy.
The app reports this availability decision clearly. The implemented
architecture can generate the final results when all three verified June rows
are added.

Official July 2026 evaluation prices:

| Fuel | Official Nairobi maximum |
|---|---:|
| Super Petrol | KSh 214.03/L |
| Diesel | KSh 222.86/L |
| Kerosene | KSh 191.38/L |

## Model

The only machine-learning estimator is `LinearRegression`.

Independent variables:

- `Landed_Cost`
- `Distribution_Storage`
- `Margins`
- `Stabilization_Adjustment`
- `Taxes_Levies`
- encoded `Fuel`

Target variable:

- `Target_Retail_Price`

The model-ready dataset pairs each verified input cycle with the following
retail-price target cycle. Chronological evaluation trains on 30 rows with
targets from September 2024 to March 2026 and tests on three April 2026 rows.

## Application pages

1. Home
2. July 2026 Prediction
3. Factors Affecting Fuel Price
4. Price Reconstruction
5. Fuel Calculator
6. Data and Methodology

The primary persona is Brian, a Nairobi ride-hailing driver. EPRA is the
regulator, authoritative data source, and project stakeholder—not the client.
MafutaPlan is an academic tool and does not replace official EPRA notices.

## Repository structure

```text
app.py                  Streamlit application
src/                    Validation, regression, pricing, and calculator logic
data/                   Verified datasets, source register, and audit records
tests/                  Revised unittest suite
notebooks/              Executed analysis notebook
scripts/                Dataset, notebook, evidence, and report builders
docs/                   Final project report
appendices/             Data dictionary, metrics, test cases, and project records
outputs/charts/          Final result charts
outputs/diagrams/        Architecture, conceptual, and use-case diagrams
outputs/screenshots/     Final page screenshots after manual verification
```

## Run

Python 3.10 or later is recommended.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Rebuild academic artifacts

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_model_dataset.py
python scripts/build_notebook.py
python scripts/build_report.py
```

The optional source-inventory and OCR audit scripts preserve official-evidence
work:

```bash
python scripts/inventory_epra_component_sources.py
python scripts/extract_epra_annex_ocr.py
python scripts/audit_epra_pump_prices.py
```

The OCR script additionally requires Tesseract OCR.

## Verify

```bash
python -m unittest discover -s tests -v
python -m compileall app.py src scripts tests
python -m pip check
```

## Limitations

- The component panel has 33 fuel-cycle rows across 11 discontinuous cycles.
- June 2026 components are not verified in the repository.
- Regulatory, tax, subsidy, and stabilization decisions can change abruptly.
- Small-sample coefficients are unstable and do not prove causation.
- Station prices may be below the regulatory maximum.
- The app is an academic prediction and planning tool, not an EPRA service.

**Author:** Ryan Alfred Nyambati — SCT222-0195/2021, Jomo Kenyatta
University of Agriculture and Technology.
