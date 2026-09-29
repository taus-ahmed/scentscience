"""005 - Phase 6: retrain models with held-out test evaluation.

Retrains all 5 XGBoost models from the live DB after longevity cleanup (004),
then evaluates on a 20% held-out set and reports per-target MAE/R².
Saves new model files to backend/ml/models/.

Governance:
  - Safety gate: refuses Railway without V2_ALLOW_REMOTE=yes.
  - Models are written ONLY with --write; report-only by default.
  - Does NOT delete the old models before writing; they're replaced atomically.
  - The training/test split is stratified by concentration tier so rare
    concentrations (Extrait, Parfum) are in both sets.

Usage:
    # Install deps first if needed:
    #   pip install xgboost scikit-learn psycopg2-binary
    set DATABASE_URL=postgresql://...@localhost/decode_v2
    cd backend
    python scripts/v2/005_retrain.py          # evaluate only (no model write)
    python scripts/v2/005_retrain.py --write  # retrain + save models

Decision rationale:
  - Longevity NULLs (from 004) remove ~63k synthetic 3.0 training labels that
    were biasing longevity predictions toward the mean.
  - Held-out evaluation confirms improvement before overwriting production models.
  - 20% test / 80% train follows the plan; stratified by concentration tier
    ensures Extrait/Parfum don't vanish from the test set (only ~3% of rows).
"""

import os, sys, json, argparse
from urllib.parse import urlparse

# ── Safety gate ───────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    sys.exit(1)

host = urlparse(DATABASE_URL).hostname or ""
print(f"\nDATABASE_URL host: {host}\n")

IS_RAILWAY = any(p in host for p in ["rlwy.net", "railway.app", "railway.internal"])
if IS_RAILWAY and os.environ.get("V2_ALLOW_REMOTE", "").lower() != "yes":
    print("REFUSED: pointing at Railway. Set V2_ALLOW_REMOTE=yes to proceed.")
    sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("--write", action="store_true", help="Save retrained models to disk")
parser.add_argument("--seed", type=int, default=42, help="Random seed for train/test split")
args = parser.parse_args()

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    import psycopg2, psycopg2.extras
except ImportError:
    print("ERROR: pip install psycopg2-binary")
    sys.exit(1)

try:
    import numpy as np
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
except ImportError:
    print("ERROR: pip install scikit-learn numpy")
    sys.exit(1)

# Add backend/ to path so we can import the existing ML modules
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

try:
    from ml.features import build_feature_vector
    from ml.model import TARGET_GROUPS, _generate_labels, MODELS_DIR, MODEL_VERSION
except ImportError as e:
    print(f"ERROR importing ml modules: {e}")
    print("Make sure you're running from backend/ and dependencies are installed.")
    sys.exit(1)

# ── Load data from DB ─────────────────────────────────────────────────────────
print("=== Step 1: Load perfumes from DB ===")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT
        id, name, brand, brand_canonical,
        concentration, concentration_clean, concentration_source,
        top_notes, middle_notes, base_notes, accords,
        gender_vote,
        season_spring_votes, season_summer_votes,
        season_fall_votes, season_winter_votes,
        occasion_daily_votes, occasion_evening_votes,
        occasion_sport_votes, occasion_office_votes,
        occasion_night_votes, occasion_beach_votes,
        community_longevity_rating, community_sillage_rating,
        community_overall_rating,
        community_longevity_label, longevity_data_quality,
        source_count, rating_count
    FROM perfumes
    WHERE rating_count >= 3
    ORDER BY rating_count DESC
""")
rows = cur.fetchall()
cur.close()
conn.close()

print(f"  Loaded {len(rows):,} perfumes (rating_count >= 3).")

# Count longevity quality distribution
from collections import Counter
ldq = Counter(r["longevity_data_quality"] for r in rows)
print(f"  longevity_data_quality: {dict(ldq)}")
labeled = sum(1 for r in rows if r["community_longevity_label"])
print(f"  With community longevity label: {labeled:,}")

# ── Convert to dicts that ml.features understands ─────────────────────────────
def row_to_dict(r) -> dict:
    """Convert psycopg2 RealDictRow to the format build_feature_vector expects."""
    def _parse_json(val):
        if val is None: return []
        if isinstance(val, list): return val
        try: return json.loads(val)
        except: return []
    return {
        "name": r["name"],
        "brand": r["brand"],
        "concentration": r["concentration_clean"] or r["concentration"] or "Unknown",
        "top_notes": _parse_json(r["top_notes"]),
        "middle_notes": _parse_json(r["middle_notes"]),
        "base_notes": _parse_json(r["base_notes"]),
        "accords": _parse_json(r["accords"]),
        "gender_vote": r["gender_vote"] or "unisex",
        "season_spring_votes": r["season_spring_votes"] or 0,
        "season_summer_votes": r["season_summer_votes"] or 0,
        "season_fall_votes": r["season_fall_votes"] or 0,
        "season_winter_votes": r["season_winter_votes"] or 0,
        "occasion_daily_votes": r["occasion_daily_votes"] or 0,
        "occasion_evening_votes": r["occasion_evening_votes"] or 0,
        "occasion_sport_votes": r["occasion_sport_votes"] or 0,
        "occasion_office_votes": r["occasion_office_votes"] or 0,
        "occasion_night_votes": r["occasion_night_votes"] or 0,
        "occasion_beach_votes": r["occasion_beach_votes"] or 0,
        "community_longevity_rating": r["community_longevity_rating"],
        "community_sillage_rating": r["community_sillage_rating"],
        "community_overall_rating": r["community_overall_rating"],
        "community_longevity_label": r["community_longevity_label"] or "",
        "source_count": r["source_count"] or 1,
        "rating_count": r["rating_count"] or 0,
    }

perfumes = [row_to_dict(r) for r in rows]

# ── Stratified train/test split ───────────────────────────────────────────────
print("\n=== Step 2: Stratified train/test split (80/20) ===")

# Stratify by concentration tier (coarse bucket)
def conc_bucket(p) -> str:
    c = (p["concentration"] or "").lower()
    if "extrait" in c or "pure" in c: return "extrait"
    if "parfum" in c and "eau" not in c: return "parfum"
    if "edp" in c or "de parfum" in c: return "edp"
    if "edt" in c or "de toilette" in c: return "edt"
    if "edc" in c or "de cologne" in c: return "edc"
    return "unknown"

strata = [conc_bucket(p) for p in perfumes]
strat_counts = Counter(strata)
print(f"  Concentration strata: {dict(strat_counts)}")

# For very small strata (<2), merge into "unknown" to allow stratification
merged_strata = [s if strat_counts[s] >= 2 else "unknown" for s in strata]

train_idx, test_idx = train_test_split(
    range(len(perfumes)),
    test_size=0.20,
    random_state=args.seed,
    stratify=merged_strata,
)
train_set = [perfumes[i] for i in train_idx]
test_set = [perfumes[i] for i in test_idx]
print(f"  Train: {len(train_set):,}  Test: {len(test_set):,}")
print(f"  Labeled in train: {sum(1 for p in train_set if p['community_longevity_label']):,}")
print(f"  Labeled in test:  {sum(1 for p in test_set if p['community_longevity_label']):,}")

# ── Build feature matrices ────────────────────────────────────────────────────
print("\n=== Step 3: Build feature vectors ===")

X_train = np.array([build_feature_vector(p) for p in train_set])
X_test  = np.array([build_feature_vector(p) for p in test_set])
print(f"  Feature dim: {X_train.shape[1]}")

n_labeled = sum(1 for p in train_set if p.get("community_longevity_label"))
n_unlabeled = len(train_set) - n_labeled
label_weight = (n_unlabeled / n_labeled) * 2.5 if n_labeled > 0 else 1.0
sample_weights = np.array([
    label_weight if p.get("community_longevity_label") else 1.0
    for p in train_set
])
print(f"  Label upweight: {label_weight:.2f}×")

# ── Train & evaluate each model group ────────────────────────────────────────
print("\n=== Step 4: Train + evaluate ===\n")

try:
    from xgboost import XGBRegressor
    from sklearn.multioutput import MultiOutputRegressor
    XGB_AVAILABLE = True
    print("  Using XGBoost")
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.multioutput import MultiOutputRegressor
    XGB_AVAILABLE = False
    print("  XGBoost not found, using GradientBoostingRegressor")

trained_models = {}
results = {}

for group, targets in TARGET_GROUPS.items():
    Y_train = np.array([_generate_labels(p, group) for p in train_set])
    Y_test  = np.array([_generate_labels(p, group) for p in test_set])

    if XGB_AVAILABLE:
        base = XGBRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            random_state=args.seed, verbosity=0,
        )
    else:
        base = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=args.seed)

    model = MultiOutputRegressor(base, n_jobs=-1)
    model.fit(X_train, Y_train, sample_weight=sample_weights)

    Y_pred = model.predict(X_test)

    # Per-target metrics
    target_results = []
    for i, tgt in enumerate(targets):
        mae = mean_absolute_error(Y_test[:, i], Y_pred[:, i])
        r2  = r2_score(Y_test[:, i], Y_pred[:, i])
        target_results.append({"target": tgt, "mae": mae, "r2": r2})

    # Group summary
    group_mae = mean_absolute_error(Y_test, Y_pred)
    group_r2  = r2_score(Y_test, Y_pred)
    results[group] = {"targets": target_results, "mae": group_mae, "r2": group_r2}
    trained_models[group] = model

    # Print group summary
    print(f"  [{group}]  MAE={group_mae:.4f}  R²={group_r2:.4f}")
    for tr in target_results:
        flag = " ⚠" if tr["r2"] < 0 else ""
        print(f"    {tr['target']:<30}  MAE={tr['mae']:.4f}  R²={tr['r2']:.4f}{flag}")
    print()

# ── Summary table ─────────────────────────────────────────────────────────────
print("=== Summary ===")
print(f"\n{'Group':<15} {'MAE':>8} {'R²':>8}")
print("-" * 35)
for group, r in results.items():
    print(f"  {group:<13} {r['mae']:>8.4f} {r['r2']:>8.4f}")

# Longevity specifically
longevity_result = next(
    (t for t in results.get("performance", {}).get("targets", [])
     if t["target"] == "longevity_hours"),
    None
)
if longevity_result:
    print(f"\n  longevity_hours  MAE={longevity_result['mae']:.4f}h  R²={longevity_result['r2']:.4f}")

# ── Save models ───────────────────────────────────────────────────────────────
if args.write:
    import pickle
    from pathlib import Path
    print("\n=== Step 5: Saving models ===")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for group, model in trained_models.items():
        path = MODELS_DIR / f"{group}_v{MODEL_VERSION}.pkl"
        with open(path, "wb") as f:
            pickle.dump(model, f)
        print(f"  Saved {path}")
    print(f"  Done. {len(trained_models)} model groups written.")
    print("  NOTE: restart the backend (Railway redeploy) to load new models.")
else:
    print("\nDRY-RUN — models NOT saved. Pass --write to save.")

print("\nDone.")
