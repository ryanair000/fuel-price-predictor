# Data Provenance and Refresh Protocol

## Meaning of the recorded values

The project records Nairobi maximum retail pump prices published by Kenya's Energy and Petroleum Regulatory Authority (EPRA). They are regulatory caps for the stated effective period, not a claim that every filling station charged the maximum.

## Source hierarchy

1. EPRA press releases, price tables, official reports, and official social-media announcements.
2. Kenya National Bureau of Statistics publications for independent cross-checking.
3. No third-party price series is treated as authoritative.

Every `source_id` in the data files must resolve to an HTTPS URL in `data/sources.csv`. The register records the publisher, title, publication date where available, date accessed, and a provenance note.

## Revisions

The April and May 2026 cycles were revised after their first announcement. `data/price_revisions_2026.csv` preserves both original and final values. `data/nairobi_price_history.csv` uses the final prevailing price and its actual effective date so the model represents what motorists faced.

## Automated validation

`src/data.py` rejects missing columns, non-Nairobi official rows, duplicate monthly cycles, non-contiguous history, invalid effective periods, non-positive prices, unknown source identifiers, and non-HTTPS evidence links. The tests also spot-check official values and reconcile the historical Annex III price components to the published total.

## Refresh procedure

1. Save the new official EPRA source in the source register.
2. Add the final Nairobi values and actual effective dates to the history.
3. Update the current-price file.
4. If a revision is issued, preserve both announcements in the revision audit trail and use the final prevailing value for modelling.
5. Run `python -m unittest discover -s tests -v` before publishing.

## Known archive limitation

EPRA's older web archive is not uniform: some cycles are available in statistics reports while recent mid-cycle changes were announced through official social channels. The source register therefore points to the best available first-party evidence for each group of observations and states any limitation explicitly.
