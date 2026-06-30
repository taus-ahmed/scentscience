# Out-of-DB Perfume Handling — Design Document

**Date:** 2026-06-30  
**Status:** Design / Pre-implementation  
**Scope:** `backend/routes/predict.py`, new scraper/enricher modules, minor frontend change

---

## 1. Problem Statement

When a user searches for a perfume not in the 110K-record SQLite DB, the `/api/predict`
endpoint returns a 404. The user sees "Perfume not found" with no recourse. This is a
significant UX gap: launches from the last 6 months, niche houses, misspelled names, and
any of the ~30K+ perfumes not yet in our DB all hit this wall.

The goal is to return a real ML prediction — with appropriate confidence — for any perfume
the user searches, including ones we've never seen before.

---

## 2. Code Audit Summary

### 2a. Current Search Flow (`routes/predict.py`)

```
POST /api/predict
  ↓ rapidfuzz WRatio ≥40 against DB perfumes filtered by brand
  ↓ if nothing → retry with name ilike filter
  ↓ if still nothing → raise HTTP 404   ← HARD STOP HERE
  ↓ build perfume dict → ml_predict() → validate_predictions() → NLP → cache
```

The 404 is thrown at line 127-131 of `routes/predict.py`. There is no fallback.

### 2b. Feature Vector Requirements (`ml/features.py`)

`build_feature_vector()` consumes a dict with these fields:

| Field | Default | Impact |
|---|---|---|
| `top_notes`, `middle_notes`, `base_notes` | `[]` | Core chemistry (9 fields + longevity_class) |
| `accords` | `[]` | Fallback when no pyramid; also family features |
| `concentration` | `"EDT"` | Multiplier (0.6–1.4×) |
| `community_longevity_rating` | `3.0` | Community feature |
| `community_sillage_rating` | `3.0` | Community feature |
| `community_overall_rating` | `3.0` | Community feature |
| `season_*_votes` | `0` | Season distribution (4 features) |
| `occasion_*_votes` | `0` | Occasion distribution (6 features) |
| `source_count` | `1` | Source reliability scalar |

**Key insight:** The vector degrades gracefully when data is missing. With no notes and no
accords, it falls back to brand DNA prior (30% weight). With no brand DNA, it uses
all-defaults (5.0 per chemistry field). A prediction is always _possible_ — just less
confident.

### 2c. Existing Fallback Chain (inside `build_feature_vector`)

Already implemented and working:
1. Real notes → use full chemistry
2. No notes but has accords → `_notes_from_accords()` synthesizes middle notes
3. No notes, no accords, has brand → `get_brand_prior()` nudges chemistry 30%
4. Nothing → all defaults (5.0)

This means even a bare `{"name": "X", "brand": "Dior", "concentration": "EDP"}` dict
produces a valid (though lower-confidence) feature vector.

### 2d. Existing Scrapers

| Scraper | Status | Notes |
|---|---|---|
| `scrapers/fragrantica.py` | EXISTS — blocked | DataDome/Cloudflare blocks real-time use |
| `scripts/scrape_basenotes.py` | EXISTS — blocked | Cloudflare 403 pre-flight check built in |

Both scrapers are production-quality but blocked. The CLAUDE.md explicitly says: "Do not
attempt live Fragrantica scraping — Cloudflare blocks it."

---

## 3. External Data Source Evaluation

### 3a. Ranked Options

#### Rank 1 — Fragella API ⭐ RECOMMENDED PRIMARY

**What:** Commercial REST API for fragrance data. Search, match, similar endpoints.  
**Coverage:** 74,000 fragrances (curated, with ML gap-filling for longevity/sillage)  
**Data returned:** `name`, `brand`, `concentration`, `top_notes`, `middle_notes`,
`base_notes`, `accords`, `longevity`, `sillage`, `gender`, season/occasion fit scores  
**Endpoints:** `GET /fragrances?q=...`, `GET /fragrances/match?name=...&brand=...`  
**Pricing:** Free tier (exploration); production: ~$2/mo base + usage  
**Latency:** ~200–500ms (single REST call)  
**Quality:** High — curated multi-source, ML-filled gaps for known perfumes  
**Reliability:** Commercial SLA, maintained

**Verdict:** Best option for mainstream / well-known perfumes. 74K coverage handles the
vast majority of user queries. Maps cleanly onto our perfume dict schema.

**Limitation:** 74K < our 110K DB; misses very niche houses. Free tier request limits may
require the paid $2/mo tier for production use.

---

#### Rank 2 — LLM Inference via Claude ⭐ RECOMMENDED SECONDARY

**What:** Prompt Claude to infer likely notes, accords, and characteristics from a perfume
name and brand. We already call Claude for NLP conclusion; this is a second structured call
earlier in the pipeline.  
**Coverage:** 100% — any name/brand Claude has seen in training  
**Data returned:** JSON with `top_notes`, `middle_notes`, `base_notes`, `accords`,
`concentration`, estimated community scores  
**Latency:** 3–8s  
**Cost:** ~$0.01–0.05 per prediction (Claude API, sonnet model)  
**Quality:** High for flagship perfumes (Dior, Chanel, YSL, Creed), medium for niche. Note
accuracy ~70–79% for known accords per published NLP research.  
**Reliability:** Claude API uptime (~99.9%)

**Verdict:** Perfect complement to Fragella. Fragella misses niche; Claude covers
everything. Quality penalty is handled by a lower confidence score and an "AI-estimated"
badge in the UI.

**Implementation note:** The prompt should request structured JSON directly. Validate
JSON output before passing to `build_feature_vector()`.

---

#### Rank 3 — FragDB Dataset (One-time bulk enrichment)

**What:** Commercial data dump — 132K Fragrantica + 220K Parfumo perfumes in CSV, full note
pyramids, accords, ratings. Snapshot from May 2026 with monthly increments.  
**Use case:** NOT for real-time lookups. For batch pre-loading to reduce out-of-DB hits.  
**Cost:** One-time purchase (pricing not public, contact-based)  
**Impact:** Could grow our DB from 110K → potentially 200K+ with rich data

**Verdict:** Excellent long-term investment but doesn't solve the real-time problem. Buy
and import as a separate Phase 11 effort. Would significantly shrink the gap where
Fragella/LLM fallbacks are needed.

---

#### Rank 4 — Apify Scrapers (Fragrantica)

**What:** Third-party Apify actors that scrape Fragrantica with residential proxies.  
**Cost:** ~$2–5 per 1,000 perfumes  
**Latency:** 10–60s per run (actor cold start + scrape + return)  
**Verdict:** Far too slow for real-time (60s latency). Fine for scheduled enrichment but
Fragella API is cheaper and faster for the same data. Skip for real-time.

---

#### Rank 5 — Fuzzy/Phonetic DB Enhancement

**What:** Improve the existing rapidfuzz matching — lower threshold, add trigram index,
phonetic (soundex/metaphone) matching.  
**Cost:** Zero  
**Coverage:** Only fixes typos and slight name variations. Doesn't help with truly missing
perfumes.  
**Verdict:** Worth doing as a small improvement but not a solution. Threshold is already
at 40 (quite generous). Diminishing returns below 35.

---

#### Rank 6 — Parfumo / Basenotes Real-time Scraping

**What:** Scrape live pages when a perfume isn't in our DB.  
**Status:** Both blocked by Cloudflare. Basenotes scraper already has a 403 pre-flight
check that exits on block.  
**Verdict:** Dead end. Do not pursue.

---

### 3b. Coverage Analysis

| Source | Coverage | Quality | Latency | Cost |
|---|---|---|---|---|
| Our DB (now) | 110K perfumes | High | 0ms | Free |
| Fragella API | 74K perfumes | High | ~400ms | ~$2/mo |
| LLM (Claude) | ~200K+ known perfumes | Medium-High | 3–8s | ~$0.02/call |
| FragDB import | 200K+ perfumes | High | 0ms (post-import) | One-time purchase |
| Apify Fragrantica | 1M+ | High | 30–60s | $2–5/1K |

Combined Fragella + LLM covers the vast majority of user queries with acceptable quality.

---

## 4. Recommended Solution: Tiered Fallback Chain

### Architecture Diagram

```
User searches "Creed Aventus Cologne"
         │
         ▼
[Tier 0] DB fuzzy match (rapidfuzz WRatio ≥40)
         │ FOUND → run existing pipeline → return result
         │ NOT FOUND ↓
         ▼
[Tier 1] Fragella API match (GET /fragrances/match?name=...&brand=...)
         │ FOUND → build ephemeral perfume dict → run ML → cache to DB → return result
         │ NOT FOUND / error ↓
         ▼
[Tier 2] LLM Inference (Claude Sonnet structured JSON call)
         │ SUCCESS → build ephemeral dict → run ML → cache to DB → return result
         │ FAILURE ↓
         ▼
[Tier 3] Graceful failure response (not a 404 — a structured 200 with error context)
```

### Key Design Decisions

**Cache to DB immediately (Tier 1 & 2 hits):**  
If Fragella or LLM provides data, write it to the `perfumes` table right away. Next time
anyone searches this perfume, Tier 0 catches it. The DB grows organically from user
searches. Set `source_count=1`, `scraped_at=now()`, and a new `data_source` column
(values: `"db"`, `"fragella"`, `"llm_inferred"`).

**Never return a raw 404 for the predict endpoint:**  
A 404 breaks the UX flow. Instead, if all tiers fail, return HTTP 200 with
`{"error": "not_found", "message": "...", "suggestions": [...]}` including fuzzy name
suggestions from the DB.

**Confidence calibration for fallback tiers:**
- Tier 1 (Fragella, has notes): `source_count=1`, `has_inferred_pyramid=False` → confidence ~0.55–0.75
- Tier 2 (LLM, inferred notes): `source_count=1`, `has_inferred_pyramid=True` → confidence ~0.40–0.55
- The existing `validate_predictions()` + confidence formula already handles this naturally.
  Just pass the right `source_count` and `has_inferred_pyramid` values.

**Don't slow down Tier 0 hits:**  
The fallback chain only activates if Tier 0 (DB fuzzy match) fails. Existing behavior is
unchanged for the 99%+ of requests that hit the DB.

---

## 5. Detailed Implementation Plan

### 5a. New File: `backend/scrapers/fragella.py`

Async aiohttp client wrapping the Fragella API. Key functions:

```
async def search_fragella(name: str, brand: str | None) -> dict | None
```

- Calls `GET https://api.fragella.com/fragrances/match?name={name}&brand={brand}`
- Falls back to `GET /fragrances?q={brand} {name}` and picks top result if match fails
- Maps Fragella response fields to our perfume dict schema:
  - `fragella.notes.top` → `top_notes`
  - `fragella.notes.middle` → `middle_notes`
  - `fragella.notes.base` → `base_notes`
  - `fragella.accords` → `accords`
  - `fragella.oilType` → `concentration`
  - `fragella.longevity` → `community_longevity_rating`
  - `fragella.sillage` → `community_sillage_rating`
  - `fragella.rating` → `community_overall_rating`
  - `fragella.gender` → `gender_vote`
- Returns a perfume dict compatible with `_perfume_to_dict()` or None on failure
- Uses `FRAGELLA_API_KEY` from env/settings
- Timeout: 5s; no retry (fast-fail to Tier 2)

### 5b. New File: `backend/ml/llm_enricher.py`

Calls Claude to infer perfume characteristics when all other sources fail.

```
async def infer_perfume_from_llm(name: str, brand: str, concentration: str) -> dict | None
```

Prompt design:
```
You are a fragrance expert. Given the perfume "{brand} {name}" ({concentration}),
provide your best estimate of its fragrance profile as JSON with these exact fields:
{
  "top_notes": ["..."],     // 3-5 notes
  "middle_notes": ["..."],  // 3-6 notes  
  "base_notes": ["..."],    // 3-5 notes
  "accords": ["..."],       // 3-5 main accords
  "gender_vote": "masculine|feminine|unisex",
  "community_longevity_rating": 1.0-5.0,
  "community_sillage_rating": 1.0-5.0,
  "community_overall_rating": 1.0-5.0
}
Only output the JSON object. If you are not familiar with this perfume, make your
best inference from the brand's style and the name's semantic meaning.
```

- Reuse the existing Anthropic client from `ml/nlp.py`
- Parse and validate the JSON response; return None on invalid output
- Set `has_inferred_pyramid=True` on the resulting perfume dict

### 5c. Modify: `backend/routes/predict.py`

Replace the current hard 404 block (lines 127-136) with the tiered fallback:

```python
# After current fuzzy-match + 404 block, add:

if not perfumes or not match or match[1] < 40:
    # Tier 1: Fragella API
    from scrapers.fragella import search_fragella
    fragella_data = await search_fragella(req.perfume_name, req.brand)
    
    if fragella_data:
        # Write to DB async (fire-and-forget)
        asyncio.create_task(_persist_external_perfume(fragella_data, db))
        perfume_dict = fragella_data
        data_source = "fragella"
        # Synthetic Perfume-like object for validate_predictions()
        matched_perfume = _dict_to_fake_perfume(fragella_data)
    else:
        # Tier 2: LLM inference
        from ml.llm_enricher import infer_perfume_from_llm
        conc = req.context and getattr(req.context, 'concentration', None) or "EDT"
        llm_data = await infer_perfume_from_llm(req.perfume_name, req.brand or "", conc)
        
        if llm_data:
            asyncio.create_task(_persist_external_perfume(llm_data, db))
            perfume_dict = llm_data
            data_source = "llm_inferred"
            matched_perfume = _dict_to_fake_perfume(llm_data)
        else:
            # Tier 3: graceful failure
            suggestions = await _get_name_suggestions(req.perfume_name, db)
            return {
                "error": "not_found",
                "message": f"Could not find or infer data for '{req.perfume_name}'.",
                "suggestions": suggestions,
            }
```

New helpers needed in `predict.py`:

- `_dict_to_fake_perfume(d: dict) -> SimpleNamespace` — returns a duck-typed object with
  all the attributes `validate_predictions()` reads from a Perfume ORM row. Uses
  `source_count=1`, `has_inferred_pyramid=True` for LLM / `False` for Fragella with notes.
- `_persist_external_perfume(data: dict, db: AsyncSession) -> None` — async task that
  inserts a new `Perfume` row if the name+brand combo doesn't exist yet. Idempotent.
- `_get_name_suggestions(name: str, db: AsyncSession) -> list[str]` — returns top-3 fuzzy
  DB name matches even if below the predict threshold, for "Did you mean..." suggestions.

**Response envelope change:**  
Add `data_source` field to the existing predict response dict:
```json
{
  "perfume": { ... },
  "predictions": { ... },
  "prediction_id": 123,
  "match_score": 95,
  "data_source": "db" | "fragella" | "llm_inferred"
}
```

### 5d. Modify: `backend/models/perfume.py`

Add one column to `Perfume`:

```python
data_source: Mapped[str] = mapped_column(String(20), default="db", server_default="db")
```

Values: `"db"` (imported from datasets), `"fragella"` (Fragella API), `"llm_inferred"`
(Claude inference). Migration: `ALTER TABLE perfumes ADD COLUMN data_source TEXT DEFAULT 'db'`.

### 5e. Modify: `backend/config.py`

Add new settings:
```python
fragella_api_key: str = ""   # read from FRAGELLA_API_KEY env var
fragella_api_url: str = "https://api.fragella.com"
fragella_timeout_s: float = 5.0
```

### 5f. Modify: `frontend/src/pages/Dashboard.jsx`

After the prediction result is received, if `data_source !== "db"`, show a banner:

```jsx
{result.data_source === 'fragella' && (
  <div className="info-banner">
    ⚠️ This perfume was not in our database. Notes sourced from Fragella API.
    Confidence may be lower than usual.
  </div>
)}
{result.data_source === 'llm_inferred' && (
  <div className="warning-banner">
    🤖 This perfume is not in our database. Notes estimated by AI.
    Predictions are approximate — treat confidence badge accordingly.
  </div>
)}
```

The existing confidence badge (High/Medium/Low) already communicates quality; this banner
adds transparency about _why_ confidence may be lower.

### 5g. No Changes Needed

- `ml/features.py` — already handles missing notes gracefully via brand DNA / accord fallback
- `ml/validators.py` — `validate_predictions()` already uses `source_count`, `has_inferred_pyramid`, `note_coverage` to compute confidence; a Tier 2 result naturally gets lower confidence
- `ml/nlp.py` — reused as-is for NLP conclusion on the final prediction
- `routes/perfumes.py` — search endpoint stays DB-only (correct: browsing should only show real perfumes)

---

## 6. Step-by-Step Request Flow (After Implementation)

**Scenario:** User types "Creed Viking Cologne" — not in our DB.

1. **[0ms]** `POST /api/predict` received  
2. **[~5ms]** DB fuzzy match: no hits above WRatio 40  
3. **[~410ms]** Fragella API: `GET /fragrances/match?name=Viking+Cologne&brand=Creed`  
   → returns `{top_notes: ["Bergamot", "Pink Pepper", ...], accords: ["fresh", "woody", ...], ...}`  
4. **[async, non-blocking]** Background task writes Perfume row to DB (`data_source="fragella"`)  
5. **[~415ms]** `build_feature_vector()` runs on Fragella dict  
6. **[~420ms]** `ml_predict()` runs 5 XGBoost models  
7. **[~425ms]** `apply_context_modifiers()` applies user context  
8. **[~430ms]** `validate_predictions()` computes confidence:  
   - `source_count=1` → `+0.05`  
   - `has_inferred_pyramid=False` (Fragella has real notes) → `+0.25` (real pyramid)  
   - `note_coverage` depends on how many of Fragella's notes match `notes_chemistry.json`  
   - `rating_count=0` → `rating_mult=0.85`  
   - Likely confidence: **~0.55–0.70** → shows as "Medium" badge  
9. **[~3–5s]** NLP conclusion generated by Claude (same as always)  
10. **[~5s total]** Response returned with `data_source: "fragella"`, banner shown in UI

**Scenario B: Fragella also can't find it (very niche perfume)**

After step 3 returns nothing, steps 4–10 repeat using LLM inference instead:
- Confidence: **~0.40–0.55** → shows as "Low" badge  
- UI shows "🤖 Notes estimated by AI" banner  
- Total latency: ~8–12s (Fragella timeout + LLM call + NLP)  

---

## 7. Frontend Loading State

Current state: "Predict" button is disabled during fetch. No visual feedback beyond that.

Recommended improvement (simple, one-file change in Dashboard.jsx):

```jsx
// Add status text below the predict button
const [fetchStatus, setFetchStatus] = useState(null);

// Before API call:
setFetchStatus("Searching database...");
// After DB miss detected (can't easily know from frontend — better: just show steps on timeout)
// If response takes > 1s:
setTimeout(() => setFetchStatus("Checking external sources..."), 1000);
// If response takes > 4s:
setTimeout(() => setFetchStatus("Generating AI-based estimate..."), 4000);
```

This doesn't require any backend signaling — just progressive text that matches the
timing of the tier chain.

---

## 8. Failure Handling

| Failure | Handling |
|---|---|
| Fragella API key missing | Log warning, skip to Tier 2 |
| Fragella 429 rate limit | Skip to Tier 2, don't retry |
| Fragella 5xx | Skip to Tier 2 |
| Fragella returns perfume with empty notes | Still use it (accord fallback kicks in) |
| LLM returns invalid JSON | Skip to Tier 3 |
| LLM returns plausible but wrong notes | Lower confidence; user sees Low badge |
| DB write fails (duplicate race) | Catch IntegrityError, ignore |
| Both Tier 1 & 2 fail | Return Tier 3 structured 200 with suggestions |

---

## 9. Implementation Order

1. `backend/config.py` — add `fragella_api_key` setting (5 min)
2. `backend/scrapers/fragella.py` — async Fragella client (1–2 hrs)
3. `backend/models/perfume.py` + migration — add `data_source` column (30 min)
4. `backend/ml/llm_enricher.py` — LLM inference function (1 hr)
5. `backend/routes/predict.py` — tiered fallback chain (2–3 hrs, most complex)
6. `frontend/src/pages/Dashboard.jsx` — banner + loading text (30 min)
7. Test end-to-end: search "Creed Viking Cologne", verify prediction + DB write
8. Test Fragella failure mode: set wrong API key, verify LLM fallback fires
9. Test LLM failure mode: search an obviously nonsense name, verify Tier 3 response

**Total estimated effort:** ~6–8 hours of implementation + testing.

---

## 10. Future Improvements (Out of Scope Now)

- **FragDB import (Phase 11):** Purchase and import FragDB's 132K Fragrantica dataset,
  growing our DB to ~200K well-covered perfumes and dramatically reducing Tier 1/2 hits.
- **Scheduled enrichment:** Nightly job that batches all `data_source="llm_inferred"`
  perfumes and re-enriches them with Fragella data when available.
- **User correction:** Allow users to submit note corrections for LLM-inferred perfumes.
- **Confidence decay:** Lower confidence further if `scraped_at` is > 6 months old
  (important for seasonal perfumes or reformulations).
- **Expand brand DNA:** Wire `initialize_brand_dna()` to the full DB rather than the 384
  seed perfumes. This would improve Tier 2 quality since the LLM notes would benefit from
  a richer brand prior.
