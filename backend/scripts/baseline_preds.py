"""Quick baseline longevity predictions before retrain."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:qEKyVfuGveaaePXgdeJchyDIIKRjQUkc@tramway.proxy.rlwy.net:19043/railway")

from ml.features import build_feature_vector
import pickle, numpy as np

with open("ml/models/performance_v1.0.0.pkl", "rb") as f:
    model_bundle = pickle.load(f)
model = model_bundle["model"]
targets = model_bundle["targets"]
with open("ml/models/longevity_calibrator.pkl", "rb") as f:
    calib = pickle.load(f)
print(f"  Model targets: {targets}")


def quick_predict(name, brand, notes_top=None, notes_mid=None, notes_base=None, conc="EDT"):
    p = {
        "name": name, "brand": brand, "concentration": conc,
        "top_notes": notes_top or [], "middle_notes": notes_mid or [], "base_notes": notes_base or [],
        "community_longevity_rating": 3.0, "community_sillage_rating": 3.0,
        "community_overall_rating": 3.0,
        "season_spring_votes": 0, "season_summer_votes": 0,
        "season_fall_votes": 0, "season_winter_votes": 0,
        "occasion_daily_votes": 0, "occasion_night_votes": 0,
        "has_inferred_pyramid": False, "accords": [], "rating_count": 0, "source_count": 1,
    }
    feat = build_feature_vector(p)
    raw_arr = model.predict([feat])[0]
    long_idx = targets.index("longevity_hours") if "longevity_hours" in targets else 0
    raw = raw_arr[long_idx]
    cal = calib.predict([[raw]])[0]
    return round(float(cal), 2), round(float(raw), 2)


perfumes = [
    ("Aventus", "Creed",
     ["Bergamot", "Blackcurrant", "Apple", "Pineapple"],
     ["Birch", "Patchouli", "Rose", "Jasmine", "Guaiac Wood"],
     ["Musk", "Oak Moss", "Ambergris", "Vetiver"]),
    ("No. 5 EDP", "Chanel",
     ["Aldehydes", "Neroli", "Ylang-Ylang"],
     ["Rose", "Jasmine", "Iris"],
     ["Sandalwood", "Vetiver", "Civet", "Oakmoss", "Musk"]),
    ("Sauvage EDT", "Dior",
     ["Calabrian Bergamot", "Pepper"],
     ["Lavender", "Pink Pepper", "Vetiver", "Patchouli"],
     ["Ambroxan", "Cedar", "Labdanum"]),
    ("Cool Water EDT", "Davidoff",
     ["Mint", "Lavender", "Coriander"],
     ["Jasmine", "Geranium", "Sandalwood"],
     ["Cedar", "Musk", "Tobacco", "Oakmoss"]),
    ("Light Blue EDT", "Dolce Gabbana",
     ["Sicilian Lemon", "Apple", "Cedar"],
     ["Bamboo", "White Rose", "Jasmine"],
     ["Cedarwood", "Musk", "Amber"]),
]

label = os.environ.get("PRED_LABEL", "BEFORE")
print(f"\n=== {label} retrain ===")
print(f"  {'Perfume':<35} Calibrated   Raw")
preds = []
for name, brand, top, mid, base in perfumes:
    cal, raw = quick_predict(name, brand, top, mid, base)
    preds.append(cal)
    print(f"  {brand+' '+name:<35} {cal}h         {raw}h")

print(f"\n  Range: {min(preds):.2f}h – {max(preds):.2f}h  |  Std: {np.std(preds):.2f}h  |  Mean: {np.mean(preds):.2f}h")
