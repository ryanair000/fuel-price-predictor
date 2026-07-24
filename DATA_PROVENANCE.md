# Data Provenance and Refresh Protocol

## Scope

The project records Nairobi maximum retail prices and verified components for
Super Petrol, Diesel, and Kerosene. Prices are regulatory maxima for stated
effective periods, not guaranteed station prices.

## Sources

EPRA press releases, annex tables, formula pages, and public price tables are
the authoritative sources. Every `Source_ID` resolves to an HTTPS URL in
`data/sources.csv`. Component rows retain their exact PDF link, verification
status, quality note, reconstructed price, and reconstruction error.

## Dataset roles

- `data/nairobi_component_history.csv`: verified component records.
- `data/component_prediction_dataset.csv`: each input cycle paired with its
  following retail-price target cycle.
- `data/nairobi_price_history.csv`: verified following-cycle targets.
- `data/current_nairobi_price.csv`: the official July 2026 local snapshot.
- `data/price_revisions_2026.csv`: preserved revised announcements.

The five non-overlapping model groups are landed cost, distribution and
storage, margins, stabilization adjustment, and taxes and levies.

## Forecast rule

Each model record follows:

```text
input-cycle components -> following-cycle retail price
```

The latest complete component cycle is March 2026, so the current forecast
uses March inputs for the immediately following April 2026 target. April is
held out of training and used to measure prediction error.

The Home page separately reads observed Nairobi retail prices from EPRA's
public pump-price table. The response is cached for one hour and displays its
effective period and retrieval time. Live retail prices are not inserted into
the component model.

## Validation and refresh

`src/data.py` checks required fields, dates, duplicates, fuels, source IDs,
HTTPS evidence, numeric values, cycle ordering, and reconstruction arithmetic.

To refresh the verified component dataset:

1. Locate the official EPRA release and exact annex.
2. Add its HTTPS source record.
3. Transcribe all five component groups without estimating missing values.
4. Record dates, fuel, price, verification status, and reconstruction fields.
5. Resolve any reconstruction discrepancy against the official source.
6. Rebuild the model dataset, notebook, and report.
7. Compile the project before publishing.
