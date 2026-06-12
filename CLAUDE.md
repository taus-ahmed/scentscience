# ScentScience

ML-powered perfume recommendation platform.

## Current Status

### ML Models
All 5 models trained on **26,879 perfumes** (was 20):
- **performance** — how a fragrance performs (longevity, sillage)
- **environmental** — best season/weather fit
- **person** — demographic/skin-type targeting
- **occasion** — use-case matching (date, office, casual, etc.)
- **value** — price-to-quality ratio assessment

Dior Sauvage EDT prediction after retraining:
- Longevity: 3.7h | Sillage: 4.6/10 | Blind buy: 6.6/10 | Versatility: 7.2/10
- confidence_score: 0.442 — note: this is `avg(all predictions)/10`, not a true ML accuracy metric. The models trained on 26k+ perfumes are far better calibrated than the 20-perfume seed, but the metric doesn't reflect that directly.

### Database
- **29,000+ perfumes** in the database (fra_perfumes import still in progress, see below)
- **22,879 perfumes** have full note pyramids (from fra_cleaned primary source)
- **141 fragrance notes** in `notes_chemistry.json` (+47 from FragDB notes.csv)
- **32 accords** in `accords_popularity.json` (new reference file)

### Dataset Import (commit: this session)
Multi-source import from `backend/scripts/import_dataset.py`:

| Source | Rows | Status | Contribution |
|--------|------|--------|-------------|
| fra_cleaned.csv | 24,063 | ✅ Complete | ~22,879 perfumes with note pyramids |
| fra_perfumes.csv | 70,103 | ⏳ ~50% done (still running) | New perfumes + accord/rating fill |
| Perfumes_dataset.csv | 1,004 | ⏳ Pending fra_perfumes | Longevity labels |
| notes.csv (FragDB) | 86 | ✅ Complete | 47 new notes added |
| accords.csv (FragDB) | 32 | ✅ Complete | accords_popularity.json created |

The fra_perfumes import runs against a remote Railway DB (~1,000 rows/min). It will complete in the background. Once done, run `python scripts/import_dataset.py` again — it will skip already-imported records (fuzzy dedup) and pick up where it left off, or simply wait for the running OS process (PID was 10584) to finish.

**Model columns added to Perfume:**
- `source_count` (Integer, default=1) — incremented per source that contributed to a record
- `community_longevity_label` (String, nullable) — "Strong"/"Medium"/"Light" from Perfumes_dataset

### Audit Fixes Applied (commit e32c4b9)
- **Predict route fallback fixed** — name-similarity filter + 404 on no match (no more wrong-perfume returns)
- **Async model loading with lock** — loads `.pkl` if it exists, trains only if missing
- **Combination skin type handled** — no longer crashes or produces incorrect results
- **Missing notes logged as warnings** — instead of silently failing
- **`get_feature_dim` fixed** — returns 41 (was wrong)
- **Dead imports removed**
- **`ClimateChart` parseFloat fix** — prevented NaN renders on the frontend

## Next Steps

1. **Wait for fra_perfumes import to complete** — it's running as OS process or re-run `python scripts/import_dataset.py` (idempotent, fuzzy dedup prevents double-inserts). Final DB size expected: ~90k+ perfumes.
2. **After fra_perfumes + Perfumes_dataset complete** — re-run `python scripts/test_model.py` to retrain on the full dataset (~90k perfumes). The note-pyramid-free fra_perfumes records will still contribute community rating signals.
3. **Expand `notes_chemistry.json` further** — many notes from fra_cleaned are still missing (defaulting to 5.0). Consider scraping property data or using family-based defaults for the top 200 most-used notes.
4. **Wire `source_count` into confidence weighting** — in `ml/features.py` or `ml/validators.py`, use `source_count` as a reliability weight when generating training labels.
5. **Wire `community_longevity_label` into performance model** — map Strong→high/Medium→mid/Light→low and use as an additional ground-truth signal in `_generate_labels()`.

## Do Not Do

- **Do not attempt live Fragrantica scraping** — Cloudflare blocks it; this was already tried and abandoned.
- **Do not re-run the importer on fra_cleaned before checking DB count** — fra_cleaned is already fully imported; re-running only wastes time deduplicating 24k rows.
- **Do not skip syntax/type checks before committing** — run mypy/pyright on changed files and check for obvious errors.
- **Do not retrain models unless data has actually changed** — use `python scripts/test_model.py` after any new import batch completes.
