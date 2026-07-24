# Data Provenance and Refresh Protocol

## Scope

The project records Nairobi maximum retail prices and verified component
records for Super Petrol, Diesel, and Kerosene. Prices are regulatory maxima
for stated effective periods, not guaranteed station-level selling prices.

## Source hierarchy

1. EPRA press releases, annex tables, formula pages, price tables, and official
   company announcements.
2. Kenya government publications used only for independent cross-checking.
3. No third-party price series is treated as authoritative.

Every `Source_ID` must resolve to an HTTPS URL in `data/sources.csv`.
Component-history rows also retain the source title, exact PDF link,
verification status, quality note, reconstructed price, and reconstruction
error.

## Dataset roles

- `data/nairobi_component_history.csv` contains same-cycle official component
  records used for reconstruction and as the source for model inputs.
- `data/component_prediction_dataset.csv` pairs each verified input cycle with
  the following retail-price target cycle.
- `data/nairobi_price_history.csv` supplies verified following-cycle targets.
- `data/current_nairobi_price.csv` contains official July 2026 evaluation
  values.
- `data/price_revisions_2026.csv` preserves revised announcements.
- The source inventory, OCR audit, and live-table comparison files are retained
  as evidence and audit records.

## Component aggregation

The five model groups are `Landed_Cost`, `Distribution_Storage`, `Margins`,
`Stabilization_Adjustment`, and `Taxes_Levies`. They aggregate detailed
official cost lines. Detailed subcomponents are not added to the same model,
which avoids double-counting.

## One-cycle-ahead rule

For each model record:

```text
input-cycle components → following target-cycle retail price
```

The model target is `Target_Retail_Price`. July 2026 official prices are not
training inputs. A defensible July run requires verified June 2026 components
for all three fuels.

## Known gap and leakage control

The reviewed component panel currently ends with the March 2026 input cycle.
June 2026 component rows are not verified in the repository. The project
therefore blocks July prediction generation. It does not:

- use July components to predict July;
- substitute March components as a June proxy;
- interpolate missing official components;
- fill missing fields with averages; or
- fabricate coefficients, observations, predictions, or accuracy.

## Validation

`src/data.py` rejects missing required fields, invalid dates, duplicate
fuel-cycle rows, unsupported fuels, unknown source IDs, non-HTTPS links,
non-finite values, invalid input-target ordering, and component arithmetic
outside the reconstruction tolerance.

Run:

```bash
python scripts/build_model_dataset.py
python -m unittest discover -s tests -v
```

## Refresh procedure

1. Locate the official EPRA release and exact annex evidence.
2. Add a unique source record with an HTTPS URL.
3. Transcribe the component groups without estimating missing values.
4. Record effective dates, fuel, published price, verification status, and
   reconstruction fields.
5. Reconstruct the price and resolve any discrepancy against the official
   source.
6. Rebuild `component_prediction_dataset.csv`.
7. Confirm that every target follows its input and that July remains outside
   training.
8. Run all tests before publishing.
