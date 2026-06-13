# ScentScience

ML-powered perfume recommendation platform.

## Current Status

### ML Models
All 5 models trained on **67,222 perfumes** with full source-quality weighting:
- **performance** — how a fragrance performs (longevity, sillage)
- **environmental** — best season/weather fit
- **person** — demographic/skin-type targeting
- **occasion** — use-case matching (date, office, casual, etc.)
- **value** — price-to-quality ratio assessment

**Feature vector: 42-dimensional** (added `source_reliability` as feature 42)

Dior Sauvage EDT prediction (after pyramid inference + retrain):
- Longevity: 3.6h | Sillage: 4.6/10 | Blind buy: 6.7/10 | Versatility: 7.2/10
- source_count: 1 | has_pyramid: True → quality multiplier: 0.90
- confidence_score: **0.390**

Confidence score = `avg(all scores) / 10 * quality_multiplier`. Quality multiplier tiers:
| source_count | has_pyramid | multiplier |
|---|---|---|
| ≥ 2 | yes | 1.00 |
| ≥ 2 | no | 0.85 |
| 1 | yes | 0.90 |
| 1 | no | 0.70 |

Community longevity label blending (384 perfumes with labels):
- `longevity_hours = 0.5 * chemistry_derived + 0.5 * label_midpoint`
- Label midpoints: Very Strong→12h, Strong→9h, Medium/Moderate→5.5h, Light→2h

### Database (final — import + pyramid inference complete)
- **67,222 perfumes** in the database
- **65,874 perfumes** now have note pyramids (22,879 real + 42,995 inferred)
- **22,786 perfumes** matched by 2+ sources
- **384 perfumes** have a community longevity label (Strong/Medium/Light)
- **141 fragrance notes** in `notes_chemistry.json` (+47 from FragDB notes.csv)
- **32 accords** in `accords_popularity.json`
- `has_inferred_pyramid` (Boolean) — TRUE for the 42,995 Jaccard-inferred pyramids

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

**Perfume model columns added:**
- `source_count` (Integer, default=1) — incremented per contributing source
- `community_longevity_label` (String, nullable) — "Strong"/"Medium"/"Light" from Perfumes_dataset
- `has_inferred_pyramid` (Boolean, default=False) — set by `scripts/infer_pyramids.py`

### Audit Fixes Applied (commit e32c4b9)
- **Predict route fallback fixed** — name-similarity filter + 404 on no match
- **Async model loading with lock** — loads `.pkl` if it exists, trains only if missing
- **Combination skin type handled** — no longer crashes
- **Missing notes logged as warnings** — instead of silently failing
- **`get_feature_dim` fixed** — returns 42 (was 41 before source_reliability)
- **Dead imports removed**
- **`ClimateChart` parseFloat fix** — prevented NaN renders on the frontend

### Pyramid Inference (commit feat: note pyramid inference…)
Run `python scripts/infer_pyramids.py` from `backend/`. Idempotent — skips perfumes where
`has_inferred_pyramid=TRUE` already. Algorithm: Jaccard similarity on accord vectors (98-dim
binary, batched numpy matmul, chunks of 1000), top-5 similar reference perfumes, notes
aggregated by similarity-weighted frequency, top-15 notes re-sorted by volatility to assign
top/middle/base (5 each).

Stats: 42,995 pyramids inferred in ~90s, 0 skipped.

## Next Steps

1. **Expand `notes_chemistry.json`** — many fra_cleaned notes still default to 5.0 (e.g., `incense`, `turkish rose`, `yuzu`, `oud`). Add family-based defaults for the top ~100 most-used missing notes to improve feature vector quality.
2. **Improve predict route model loading** — `routes/predict.py` still falls back to `seed_perfumes.json` if no pkl exists on cold deploy; update it to load from DB (matching `scripts/test_model.py`).

## Do Not Do

- **Do not attempt live Fragrantica scraping** — Cloudflare blocks it; this was already tried and abandoned.
- **Do not re-run the full importer without checking** — the import is complete and idempotent, but re-running 70k rows against a remote DB takes ~90 min. Verify `SELECT COUNT(*) FROM perfumes` ≥ 67,222 before deciding to re-run.
- **Do not skip syntax/type checks before committing** — run mypy/pyright on changed files.
- **Do not retrain models unless data has actually changed** — use `python scripts/test_model.py` from `backend/`.
