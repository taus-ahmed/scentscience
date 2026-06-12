# ScentScience

ML-powered perfume recommendation platform.

## Current Status

### ML Models
All 5 models trained and working:
- **performance** — how a fragrance performs (longevity, sillage)
- **environmental** — best season/weather fit
- **person** — demographic/skin-type targeting
- **occasion** — use-case matching (date, office, casual, etc.)
- **value** — price-to-quality ratio assessment

Confidence scores are currently ~43% due to limited training data (20 perfumes). This will improve significantly after dataset import.

### Database
- 20 seed perfumes in the database
- 94 fragrance notes loaded

### Audit Fixes Applied (commit e32c4b9)
- **Predict route fallback fixed** — name-similarity filter + 404 on no match (no more wrong-perfume returns)
- **Async model loading with lock** — loads `.pkl` if it exists, trains only if missing
- **Combination skin type handled** — no longer crashes or produces incorrect results
- **Missing notes logged as warnings** — instead of silently failing
- **`get_feature_dim` fixed** — returns 41 (was wrong)
- **Dead imports removed**
- **`ClimateChart` parseFloat fix** — prevented NaN renders on the frontend

## Next Steps

1. **Inspect CSV columns first** — user will place 3 Kaggle dataset CSVs in `backend/data/datasets/`. Read and print the column names from all 3 files before writing any import code.
2. **Build multi-source importer** — after columns are confirmed, build an importer that merges and deduplicates across all 3 datasets. Include a `source_count` field per perfume for use as a confidence weight in model scoring.
3. **Expand `notes_chemistry.json`** — after import, add any new notes discovered in the expanded dataset.
4. **Retrain all 5 models** — on the expanded dataset after import and note expansion are complete.

## Do Not Do

- **Do not attempt live Fragrantica scraping** — Cloudflare blocks it; this was already tried and abandoned.
- **Do not build the dataset importer until CSV columns are inspected and confirmed** — column names vary by Kaggle source; building blind will produce broken mappings.
- **Do not skip syntax/type checks before committing** — run mypy/pyright on changed files and check for obvious errors.
- **Do not retrain models unless data has actually changed** — retraining on the same 20-perfume seed set wastes time and produces identical results.
