# ScentScience

ML-powered perfume recommendation platform.

## Current Status

### ML Models
All 5 models trained on **67,222 perfumes** (was 20):
- **performance** — how a fragrance performs (longevity, sillage)
- **environmental** — best season/weather fit
- **person** — demographic/skin-type targeting
- **occasion** — use-case matching (date, office, casual, etc.)
- **value** — price-to-quality ratio assessment

Dior Sauvage EDT prediction (final, 67k dataset):
- Longevity: 3.9h | Sillage: 4.7/10 | Blind buy: 6.8/10 | Versatility: 7.1/10
- confidence_score: **0.439** — note: this is `avg(all predictions)/10`, not a true ML accuracy metric. The models trained on 67k perfumes are far better calibrated than the 20-perfume seed, but the metric doesn't reflect that directly.

### Database (final — import complete)
- **67,222 perfumes** in the database
- **22,879 perfumes** have full note pyramids (from fra_cleaned primary source)
- **22,786 perfumes** matched by 2+ sources
- **384 perfumes** have a community longevity label (Strong/Medium/Light)
- **141 fragrance notes** in `notes_chemistry.json` (+47 from FragDB notes.csv)
- **32 accords** in `accords_popularity.json`

### Dataset Import — Complete (0 errors)
Multi-source import via `backend/scripts/import_dataset.py` (idempotent, safe to re-run):

| Source | Rows | Added | Updated/Matched | Errors |
|--------|------|-------|-----------------|--------|
| fra_cleaned.csv | 24,063 | 22,859 | — | 0 |
| fra_perfumes.csv | 70,103 | 44,343 | 24,095 updated | 0 |
| Perfumes_dataset.csv | 1,004 | — | 436 labeled | 0 |
| notes.csv (FragDB) | 86 | 47 new notes | — | 0 |
| accords.csv (FragDB) | 32 | 32 accords | — | 0 |

Deduplication: 1,204 fra_cleaned dupes skipped; 3 fra_perfumes skipped (no parseable URL); 568 Perfumes_dataset rows unmatched (sparse/obscure brands). Max source_count on any single record: 43.

**Model columns on Perfume:**
- `source_count` (Integer, default=1) — incremented per contributing source
- `community_longevity_label` (String, nullable) — "Strong"/"Medium"/"Light" from Perfumes_dataset

### Audit Fixes Applied (commit e32c4b9)
- **Predict route fallback fixed** — name-similarity filter + 404 on no match
- **Async model loading with lock** — loads `.pkl` if it exists, trains only if missing
- **Combination skin type handled** — no longer crashes
- **Missing notes logged as warnings** — instead of silently failing
- **`get_feature_dim` fixed** — returns 41
- **Dead imports removed**
- **`ClimateChart` parseFloat fix** — prevented NaN renders on the frontend

## Next Steps

1. **Expand `notes_chemistry.json`** — many fra_cleaned notes still default to 5.0 (e.g., `incense`, `turkish rose`, `yuzu`, `oud`). Add family-based defaults for the top ~100 most-used missing notes to improve feature vector quality.
2. **Wire `source_count` into confidence weighting** — use as a reliability multiplier in `_generate_labels()` in `ml/model.py` so records backed by 3+ sources get stronger signal.
3. **Wire `community_longevity_label` into performance model** — map Strong→5/Medium→3/Light→1 and blend with the existing `longevity_class` feature in `ml/features.py`.
4. **Improve predict route model loading** — `routes/predict.py` still falls back to `seed_perfumes.json` if no pkl exists; update it to load from DB (matching `scripts/test_model.py`).

## Do Not Do

- **Do not attempt live Fragrantica scraping** — Cloudflare blocks it; this was already tried and abandoned.
- **Do not re-run the full importer without checking** — the import is complete and idempotent, but re-running 70k rows against a remote DB takes ~90 min. Verify `SELECT COUNT(*) FROM perfumes` ≥ 67,222 before deciding to re-run.
- **Do not skip syntax/type checks before committing** — run mypy/pyright on changed files.
- **Do not retrain models unless data has actually changed** — use `python scripts/test_model.py` from `backend/`.
