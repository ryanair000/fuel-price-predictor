# MafutaPlan

MafutaPlan is a final-year BSc Information Technology project for analysing and planning around regulated fuel prices in Nairobi, Kenya.

The system uses official EPRA records to:

- display Nairobi maximum retail prices;
- explain the fuel-price build-up;
- reconstruct published prices from cost components;
- compare next-cycle forecasting methods;
- run transparent cost scenarios; and
- calculate purchase and journey costs.

## Project scope

- **Location:** Nairobi
- **Products:** Super Petrol, Diesel and Kerosene
- **Data source:** EPRA price releases, component tables and supporting first-party records
- **Forecasting:** previous-cycle baseline, linear regression, ridge regression, random forest and gradient boosting
- **Evaluation:** expanding-window model selection followed by a ten-cycle holdout

The forecast is an academic estimate. It is not an EPRA announcement and should not be treated as financial advice.

## Repository structure

```text
app.py                  Streamlit application
src/                    Data validation, modelling and calculations
data/                   Versioned project datasets and source register
tests/                  Automated project tests
notebooks/              Analysis notebook
scripts/                Data, notebook and report build tools
docs/                   Final project report
appendices/              Submission appendices
outputs/                 Charts and diagrams used in the report
```

## Run the application

Python 3.10 or later is recommended.

```bash
python -m venv .venv
```

Activate the environment, then install the runtime dependencies:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Research and report tools

The optional data-extraction, notebook and report scripts use additional packages:

```bash
python -m pip install -r requirements-dev.txt
```

Examples:

```bash
python scripts/inventory_epra_component_sources.py
python scripts/extract_epra_annex_ocr.py
python scripts/build_component_history.py
python scripts/build_notebook.py
python scripts/build_report.py
```

The OCR workflow also requires Tesseract OCR to be installed separately.

## Verify the project

```bash
python -m unittest discover -s tests -v
python -m compileall app.py src scripts tests
python -m pip check
```

## Main datasets

| File | Purpose |
|---|---|
| `data/nairobi_price_history.csv` | Continuous monthly Nairobi price history |
| `data/current_nairobi_price.csv` | Official price record used by the app |
| `data/price_components.csv` | Detailed component example for the price build-up |
| `data/nairobi_component_history.csv` | Reviewed multi-cycle component panel |
| `data/price_revisions_2026.csv` | Audit trail for revised price announcements |
| `data/sources.csv` | Source register and provenance |

See `DATA_PROVENANCE.md` for the data refresh and validation procedure.

## Limitations

- The monthly sample is small and sensitive to policy changes.
- The component panel is shorter than the retail-price history.
- Taxes, stabilization decisions, procurement timing and market shocks can cause structural breaks.
- Published values are maximum regulatory prices, not guaranteed station-level selling prices.

**Author:** Ryan Alfred Nyambati — SCT222-0195/2021, Jomo Kenyatta University of Agriculture and Technology.
