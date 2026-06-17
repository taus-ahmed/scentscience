# Morning Commands — Run in Order

All overnight file edits are done. Run these in order from `E:\scentscience`.

---

## STEP 0 — Verify JSON + imports (syntax check before anything else)

```powershell
cd E:\scentscience
python -c "import json; d=json.load(open('backend/data/notes_chemistry.json',encoding='utf-8')); print(f'notes_chemistry.json OK — {len(d)} entries')"
python -c "import sys; sys.path.insert(0,'backend'); from ml.features import build_feature_vector, get_feature_dim; print(f'features.py OK — dim={get_feature_dim()}')"
python -c "import sys; sys.path.insert(0,'backend'); from ml.accord_notes import ACCORD_NOTES; print(f'accord_notes.py OK — {len(ACCORD_NOTES)} accords')"
python -c "import sys; sys.path.insert(0,'backend'); from ml.brand_dna import get_brand_prior; print('brand_dna.py OK')"
python -c "import sys; sys.path.insert(0,'backend'); from ml.validators import validate_predictions; print('validators.py OK')"
```

If any of these error, fix before proceeding.

---

## STEP 1 — Fix source counts (idempotent, safe to re-run)

```powershell
cd E:\scentscience\backend
python scripts/fix_source_counts.py
```

Expected: all 5 records already at sc=3 (nothing to do).

---

## STEP 2 — Retrain models (picks up note corrections + sc fixes)

```powershell
python scripts/test_model.py 2>&1 | Tee-Object -FilePath ..\training_log.txt
```

Takes ~2-5 min. Watch for: "Training complete" and MAE < 0.50h.
If MAE is worse than 0.39h, check training_log.txt for warnings about missing notes.

---

## STEP 3 — Recalibrate longevity (only after Step 2 succeeds)

```powershell
python scripts/calibrate_longevity.py
```

Expected output: MAE around 0.39h or better.

---

## STEP 4 — Morning smoke test (the demo)

```powershell
python scripts/morning_test.py
```

This tests 20 flagship perfumes across all categories. Expected results:
- PASS (conf >= 0.85): Sauvage EDT, Bleu de Chanel, Tobacco Vanille, Aventus, Black Opium, Angel, Chanel No 5, Tom Ford Oud/Lost Cherry, Baccarat Rouge 540
- WARN (conf 0.70-0.85): CK One, Acqua di Gio, Gucci Bloom (sc=1 records)
- MISS: any perfume not in DB (check by name in Search page)

Target: avg confidence >= 0.850, avg longevity >= 5h, MISS = 0.

---

## STEP 5 — Full audit

```powershell
python scripts/model_audit2.py
```

Target metrics (vs Phase 10b baseline):
- Bucket accuracy >= 93.0%
- Strong recall >= 86.0% (129/150)
- Moderate recall >= 96.2% (203/211)
- Light recall >= 87.0% (20/23)
- MAE <= 0.39h | RMSE <= 0.83h

---

## STEP 6 — Notes chemistry dedup check (Task 11)

Run this to find any case-duplicate entries in notes_chemistry.json:

```powershell
python -c "
import json, sys
from collections import defaultdict
notes = json.load(open('backend/data/notes_chemistry.json', encoding='utf-8'))
by_lower = defaultdict(list)
for n in notes:
    by_lower[n['name'].lower()].append(n['name'])
dupes = {k: v for k, v in by_lower.items() if len(v) > 1}
if dupes:
    print(f'{len(dupes)} case-duplicates:')
    for k, names in sorted(dupes.items()):
        print(f'  {k!r}: {names}')
else:
    print('No case-duplicates found.')
"
```

If duplicates are found, the last entry in the JSON wins (lookup uses `.lower()` keying).
For duplicates with identical chemistry, no action needed. For ones with different values,
manually keep the more accurate profile and delete the other from notes_chemistry.json.

---

## STEP 7 — Frontend build check (run if you changed any frontend files)

Overnight changes: Dashboard.jsx (null safety), Search.jsx (null guard), NLPConclusion.jsx (clipboard try-catch).

```powershell
cd E:\scentscience\frontend
npm run build
```

Expected: build succeeds, ~187KB gzipped, chunk size warning for Recharts is normal.

---

## STEP 8 — Commit everything

```powershell
cd E:\scentscience
git add backend/scripts/morning_test.py backend/scripts/fix_source_counts.py backend/scripts/fix_notes_chemistry.py
git add backend/ml/accord_notes.py backend/ml/brand_dna.py backend/ml/features.py backend/ml/validators.py
git add backend/data/notes_chemistry.json
git add frontend/src/pages/Dashboard.jsx frontend/src/pages/Search.jsx frontend/src/components/NLPConclusion.jsx
git add MORNING_COMMANDS.md CLAUDE.md
git commit -m "Phase 10b: accord mapping, brand DNA inference, 20 new notes, encoding fix, source_count corrections, frontend bug sweep"
git push origin master
```

---

## STEP 9 — Verify Railway deployment

The Railway URL is set as `VITE_API_URL` in the Railway frontend service environment variables.
Push from Step 8 triggers Railway auto-deploy (takes ~3-5 min).

To verify the API is live after deploy (replace URL with your Railway backend domain):

```powershell
# Replace with your actual Railway backend domain from the Railway dashboard
$RAILWAY_URL = "https://YOUR-BACKEND.up.railway.app"
Invoke-WebRequest "$RAILWAY_URL/health" -UseBasicParsing | Select-Object StatusCode, Content
Invoke-WebRequest "$RAILWAY_URL/api/perfumes?q=sauvage&limit=3" -UseBasicParsing | Select-Object Content
```

If you don't remember the URL: Railway dashboard → your project → backend service → Settings → Domains.

---

## Overnight changes summary

| File | Change |
|------|--------|
| `backend/ml/features.py` | UTF-8 fix, `\x99`→® normalization, accord synthesis fallback, brand DNA fallback |
| `backend/ml/accord_notes.py` | NEW — 39-accord → note profile mapping |
| `backend/ml/brand_dna.py` | NEW — brand chemistry prior (30% weight, ~10 brands) |
| `backend/ml/validators.py` | Added full formula tiers comment at top |
| `backend/data/notes_chemistry.json` | 14 profiles corrected, 5 new notes → 4,790 entries |
| `backend/scripts/fix_source_counts.py` | NEW — idempotent sc fix (already run; Sauvage EDT/EDP, Bleu, Bloom → sc=3) |
| `backend/scripts/fix_notes_chemistry.py` | NEW — utility script (already run) |
| `backend/scripts/morning_test.py` | NEW — 20-perfume demo test (J'adore EDP replaces Jo Malone) |
| `frontend/src/pages/Dashboard.jsx` | ClimateChart `?? 0` NaN safety; PersonFit Bar `?? 0` NaN safety |
| `frontend/src/pages/Search.jsx` | `setResults(data \|\| [])` null guard |
| `frontend/src/components/NLPConclusion.jsx` | try-catch on clipboard write |
| `CLAUDE.md` | Phase 10b results, Sauvage EDT confidence updated to 0.970 |

Committed: `f432c5e` (Tasks 1–7) — frontend fixes are uncommitted, run Step 7–8 above.
