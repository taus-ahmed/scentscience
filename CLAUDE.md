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

Dior Sauvage EDT prediction (after source_count fix):
- Longevity: 3.6h | Sillage: 4.6/10 | Blind buy: 6.7/10 | Versatility: 7.2/10
- source_count: 2 | has_pyramid: True → quality multiplier: 1.00
- confidence_score: **0.433**

Note: source_count was incorrectly 1 due to a by_brand key-collision in import_dataset.py —
Sauvage EDT (id=1) and EDP (id=2) both normalize to `by_brand['dior']['sauvage']`; the EDP
(higher id, iterated last) stole the slot and absorbed the fra_perfumes source_count bump.
Fixed by `scripts/fix_sauvage_source_count.py` (manual patch: source_count=2, 9 accords,
fragrantica_url set). Bug is in the dedup logic for same-brand same-name-different-concentration
records — tracked as a known issue for the next import refactor.

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

### Model Performance Audit (scripts/model_audit2.py — 384 GT perfumes + 9-perfume diverse table)

#### Section 1 — Diverse Prediction Table
| Brand | Name | SC | Pyr | Long | Sill | BB | Vers | Conf | Notes coverage |
|---|---|---|---|---|---|---|---|---|---|
| Versace | Eros | 3 | real | 6.5h | 4.9 | 6.3 | 7.0 | 0.451 | 10/10 ✓ |
| Dior | Sauvage Elixir | 3 | real | 4.1h | 4.0 | 5.0 | 2.2 | 0.385 | 8/10 |
| Chanel | No 5 Parfum | 3 | real | 3.8h | 3.9 | 4.3 | 1.8 | 0.373 | 16/18 |
| Creed | Aventus For Her | 3 | real | 3.8h | 4.0 | 4.3 | 1.8 | 0.372 | 11/15 |
| YSL | Black Opium Intense | 3 | real | 3.8h | 3.9 | 4.6 | 2.0 | 0.363 | 3/8 |
| Tom Ford | Black Orchid | 3 | real | 3.5h | 4.0 | 4.6 | 2.0 | 0.366 | 12/23 |
| Jo Malone | Lime Basil Mandarin | 2 | real | 3.1h | 3.9 | 4.3 | 1.8 | 0.351 | 7/9 |
| Guerlain | Shalimar Souffle | 7 | real | 3.1h | 3.9 | 4.7 | 2.1 | 0.333 | 5/8 |
| Giorgio Armani | Acqua Di Gioia | 5 | real | 2.9h | 3.8 | 4.5 | 1.9 | 0.326 | 1/6 |

Key observation: Versace Eros (10/10 note coverage) scores highest across the board. Acqua Di Gioia
(1/6 coverage) gets the lowest confidence despite having source_count=5 — note coverage dominates.

#### Section 2 — Longevity Bucket Accuracy (384 GT perfumes)
Ground-truth distribution: Medium 211 (54.9%), Strong 141 (36.7%), Light 23 (6.0%), Very Strong 9 (2.3%)

| Class | Correct | Total | Recall |
|---|---|---|---|
| Strong | 1 | 150 | 0.7% |
| Moderate | 61 | 211 | 28.9% |
| Light | 19 | 23 | 82.6% |
| **Overall** | **81** | **384** | **21.1%** |

Confusion: 67 "Strong" perfumes predicted as Light. 150 "Moderate" perfumes predicted as Light.
Model almost never predicts Strong — strong recall is effectively 0.

NOTE: 50/50 label blend in training inflates these numbers. True generalization accuracy on
unlabeled perfumes is materially lower.

#### Section 3 — MAE on longevity_hours (384 GT perfumes)
- **MAE = 2.99h** | RMSE = 3.48h | Median AE = 2.12h | P90 AE = 5.36h
- Strong bucket: MAE = 5.03h, bias = −5.03h (systematic under-prediction)
- Moderate bucket: MAE = 1.70h, bias = −1.70h
- Light bucket: MAE = 1.53h, bias = +1.53h (slight over-prediction)
- GT range: 2.0–12.0h | Predicted range: 2.8–8.4h | **Compression: 3.35x**
- Real pyramid MAE = 2.94h (n=330) vs inferred pyramid MAE = 3.32h (n=54)

#### Section 4 — Ranked Weaknesses
1. **Range compression (3.35x)** — model predicts 2.8–8.4h; GT spans 2.0–12.0h. Extreme
   longevity never reached. Root cause: missing notes pull all predictions toward 5.0 median.
2. **Note coverage** — 313 unique notes missing from `notes_chemistry.json`; avg 28.7% of each
   perfume's notes default to 5.0. 45/384 labeled perfumes have >50% notes missing.
   Top gaps: `black currant` (45 perfumes), `pear` (38), `agarwood/oud` (26), `incense` (25),
   `tuberose` (24), `ylang-ylang` (22), `peony` (20), `jasmine sambac` (16), `coffee` (13).
3. **Strong-class blindness** — 67 strong perfumes predicted as Light (<4h), nearly all due to
   missing notes. Strong recall = 0.7%.
4. **Label leakage** — 50/50 blend inflates labeled-set accuracy; unlabeled generalization is worse.
5. **Inferred pyramids slightly worse** — +0.38h MAE vs real pyramids (3.32h vs 2.94h).

## Next Steps

1. **Expand `notes_chemistry.json`** — audit confirms 313 unique notes defaulting to 5.0.
   Priority additions (by labeled-perfume frequency): `black currant`, `pear`, `agarwood/oud`,
   `incense`, `tuberose`, `ylang-ylang`, `peony`, `jasmine sambac`, `coffee`, `olibanum`,
   `violet leaf`, `raspberry`, `gardenia`, `bulgarian rose`, `blood orange`, `heliotrope`.
   Fixing these directly resolves range compression and strong-class blindness (same root cause).
   After adding, retrain models — `python scripts/train_model.py` from `backend/`.
2. **Improve predict route model loading** — `routes/predict.py` still falls back to `seed_perfumes.json` if no pkl exists on cold deploy; update it to load from DB (matching `scripts/test_model.py`).

## Do Not Do

- **Do not attempt live Fragrantica scraping** — Cloudflare blocks it; this was already tried and abandoned.
- **Do not re-run the full importer without checking** — the import is complete and idempotent, but re-running 70k rows against a remote DB takes ~90 min. Verify `SELECT COUNT(*) FROM perfumes` ≥ 67,222 before deciding to re-run.
- **Do not skip syntax/type checks before committing** — run mypy/pyright on changed files.
- **Do not retrain models unless data has actually changed** — use `python scripts/test_model.py` from `backend/`.
