"""
Five XGBoost multi-output regression models:
  performance  — proj_1hr/3hr/6hr/8hr, longevity_hours, sillage_score, peak_hour, heat_amplification
  environmental — season/climate/time scores, temp range, humidity, indoor/outdoor
  person        — skin type, age bracket, gender, personality scores
  occasion      — occasion scores, social distance index
  value         — cost_per_wear, versatility, compliment, blind_buy
"""

import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Any

from ml.features import build_feature_vector, FAMILIES
from config import get_settings

try:
    from xgboost import XGBRegressor
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

_models_dir_setting = get_settings().models_dir
MODELS_DIR = (
    Path(_models_dir_setting) if Path(_models_dir_setting).is_absolute()
    else Path(__file__).parent.parent / _models_dir_setting
)
MODEL_VERSION = "1.0.0"

TARGET_GROUPS = {
    "performance": [
        "proj_1hr", "proj_3hr", "proj_6hr", "proj_8hr",
        "longevity_hours", "sillage_score", "performance_peak_hour", "heat_amplification",
    ],
    "environmental": [
        "season_spring", "season_summer", "season_fall", "season_winter",
        "climate_tropical", "climate_arid", "climate_temperate", "climate_cold",
        "temp_optimal_min_c", "temp_optimal_max_c",
        "humidity_performance", "indoor_score", "outdoor_score",
        "time_morning", "time_afternoon", "time_evening", "time_night",
    ],
    "person": [
        "skin_dry_score", "skin_oily_score", "skin_combo_score",
        "age_18_25", "age_25_35", "age_35_50", "age_50_plus",
        "gender_masculine", "gender_feminine", "gender_unisex",
        "personality_dominant", "personality_intellectual",
        "personality_casual", "personality_romantic",
    ],
    "occasion": [
        "occ_office", "occ_date", "occ_casual", "occ_formal", "occ_sport", "occ_travel",
        "social_distance_idx",
    ],
    "value": [
        "cost_per_wear_score", "versatility_score", "compliment_score", "blind_buy_score",
    ],
}

SOCIAL_DISTANCE_MAP = {0: "intimate", 1: "personal", 2: "room", 3: "crowd"}

# Ground-truth longevity midpoints from Perfumes_dataset community_longevity_label
LONGEVITY_LABEL_HOURS = {
    "very strong": 12.0,
    "strong":       9.0,
    "medium":       5.5,
    "moderate":     5.5,
    "light–medium": 4.0,
    "light-medium": 4.0,
    "medium–strong": 7.5,
    "medium-strong": 7.5,
    "light":        2.0,
    "weak":         2.0,
}


def _model_path(group: str) -> Path:
    return MODELS_DIR / f"{group}_v{MODEL_VERSION}.pkl"


def _generate_labels(perfume: dict, group: str) -> np.ndarray:
    """
    Derive pseudo ground-truth labels from known community data + chemistry.
    Used for initial seed training.
    """
    feat = build_feature_vector(perfume)

    # Unpack feature positions for readability
    volatility = feat[0]
    heat_perf = feat[1]
    cold_perf = feat[2]
    humidity_perf = feat[3]
    dry_perf = feat[4]
    skin_bonding = feat[5]
    dry_skin = feat[6]
    oily_skin = feat[7]
    projection = feat[8]
    longevity_class = feat[9]
    conc_mult = feat[10]
    fam_start = 11
    fam_end = fam_start + len(FAMILIES)
    fam = feat[fam_start:fam_end]  # 17 values
    community_long = feat[fam_end]
    community_sill = feat[fam_end + 1]
    community_overall = feat[fam_end + 2]
    season_spring_d = feat[fam_end + 3]
    season_summer_d = feat[fam_end + 4]
    season_fall_d = feat[fam_end + 5]
    season_winter_d = feat[fam_end + 6]
    occ_daily_d = feat[fam_end + 7]
    occ_evening_d = feat[fam_end + 8]
    occ_sport_d = feat[fam_end + 9]
    occ_office_d = feat[fam_end + 10]
    occ_night_d = feat[fam_end + 11]
    occ_beach_d = feat[fam_end + 12]

    longevity_hours = (longevity_class * 2.0 + community_long * 1.5) * conc_mult / 2.5
    sillage = (projection * 0.6 + community_sill * 2.0) * conc_mult / 2.0

    # Use 100% of the community label for labeled perfumes (was 50/50 blend)
    label_key = perfume.get("community_longevity_label", "")
    if label_key:
        label_hours = LONGEVITY_LABEL_HOURS.get(label_key.lower().strip())
        if label_hours is not None:
            longevity_hours = label_hours

    if group == "performance":
        decay = (10 - volatility) / 10.0
        proj_1hr = min(10.0, sillage * 0.9)
        proj_3hr = min(10.0, sillage * decay * 0.8)
        proj_6hr = min(10.0, sillage * (decay ** 2) * 0.6)
        proj_8hr = min(10.0, sillage * (decay ** 3) * 0.4)
        peak = 1.0 if volatility > 7 else (2.5 if volatility > 4 else 0.5)
        heat_amp = (heat_perf * 0.7 + community_overall * 0.3) * conc_mult
        return np.array([proj_1hr, proj_3hr, proj_6hr, proj_8hr,
                         longevity_hours, sillage, peak, min(10, heat_amp)])

    elif group == "environmental":
        # Season — blend community votes with note chemistry
        sp = season_spring_d * 10 * 0.6 + cold_perf * 0.4
        su = season_summer_d * 10 * 0.6 + heat_perf * 0.4
        fa = season_fall_d * 10 * 0.6 + (cold_perf + dry_perf) / 2 * 0.4
        wi = season_winter_d * 10 * 0.6 + cold_perf * 0.4
        # Climate
        tropical = (heat_perf * 0.5 + humidity_perf * 0.5) * conc_mult * 0.8
        arid = (heat_perf * 0.6 + dry_perf * 0.4) * conc_mult * 0.8
        temperate = (cold_perf + heat_perf) / 2 * conc_mult * 0.9
        cold_clim = cold_perf * conc_mult * 0.9
        # Temp range
        temp_min = max(-10, 30 - cold_perf * 3)
        temp_max = min(45, 15 + heat_perf * 3)
        hum_perf = humidity_perf * conc_mult * 0.9
        indoor = (skin_bonding * 0.5 + longevity_hours * 0.3 + projection * 0.2)
        outdoor = ((heat_perf + cold_perf) / 2 * 0.5 + projection * 0.5) * conc_mult * 0.8
        # Time of day
        tm = 5.0 + (cold_perf - 5) * 0.3
        ta = 5.0 + (heat_perf - 5) * 0.3
        te = 5.0 + projection * 0.2
        tn = 5.0 + sillage * 0.2
        return np.clip(
            [sp, su, fa, wi, tropical, arid, temperate, cold_clim,
             temp_min, temp_max, hum_perf, indoor, outdoor, tm, ta, te, tn],
            -10, 10
        )

    elif group == "person":
        dry_s = dry_skin * conc_mult * 0.9
        oily_s = oily_skin * conc_mult * 0.9
        combo_s = (dry_skin + oily_skin) / 2 * conc_mult * 0.9
        # Age — simplified heuristic
        a18 = 5 + (projection - 5) * 0.3
        a25 = community_overall * 1.5
        a35 = 5 + (longevity_hours - 6) * 0.2
        a50 = 5 + (skin_bonding - 5) * 0.3
        gv = perfume.get("gender_vote", "unisex")
        gm = 8.0 if gv == "masculine" else (4.0 if gv == "feminine" else 6.0)
        gf = 8.0 if gv == "feminine" else (4.0 if gv == "masculine" else 6.0)
        gu = 8.0 if gv == "unisex" else 5.0
        dom = projection * 0.5 + sillage * 0.5
        intell = (skin_bonding * 0.4 + longevity_hours * 0.4 + cold_perf * 0.2)
        cas = occ_daily_d * 10 * 0.6 + projection * 0.4
        rom = occ_evening_d * 10 * 0.6 + (heat_perf + sillage) / 2 * 0.4
        return np.clip(
            [dry_s, oily_s, combo_s, a18, a25, a35, a50,
             gm, gf, gu, dom, intell, cas, rom], 0, 10
        )

    elif group == "occasion":
        office = occ_office_d * 10 * 0.7 + (longevity_hours / 12 * 10) * 0.3
        date = occ_evening_d * 10 * 0.5 + (sillage + projection) / 2 * 0.5
        casual = occ_daily_d * 10 * 0.6 + (10 - projection) * 0.4
        formal = occ_evening_d * 10 * 0.5 + longevity_hours / 12 * 10 * 0.5
        sport = occ_sport_d * 10 * 0.6 + occ_beach_d * 10 * 0.4
        travel = (occ_beach_d + occ_daily_d) / 2 * 10 * 0.7 + longevity_hours / 12 * 10 * 0.3
        sd_idx = min(3.0, projection / 3.0)
        return np.clip([office, date, casual, formal, sport, travel, sd_idx], 0, 10)

    elif group == "value":
        cpw = longevity_hours / 12 * 10 * 0.5 + community_overall * 1.5 * 0.5
        vers = (season_spring_d + season_summer_d + season_fall_d + season_winter_d) * 10 * 0.5 + community_overall * 0.5
        comp = sillage * 0.4 + projection * 0.3 + community_overall * 1.5 * 0.3
        blind = community_overall * 1.5 * 0.5 + vers * 0.3 + comp * 0.2
        return np.clip([cpw, vers, comp, blind], 0, 10)

    return np.zeros(1)


def train_all_models(perfumes: list[dict] | None = None) -> None:
    """Train all 5 models on provided perfumes or load seed data."""
    if perfumes is None:
        seed_path = Path(__file__).parent.parent / "data" / "seed_perfumes.json"
        with open(seed_path) as f:
            perfumes = json.load(f)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X = np.array([build_feature_vector(p) for p in perfumes])

    # Upweight the 384 labeled perfumes so they carry equal total weight to all
    # unlabeled perfumes — prevents XGBoost regressing purely to chemistry median.
    n_labeled = sum(1 for p in perfumes if p.get("community_longevity_label"))
    n_unlabeled = len(perfumes) - n_labeled
    label_weight = (n_unlabeled / n_labeled) if n_labeled > 0 else 1.0
    sample_weights = np.array([
        label_weight if p.get("community_longevity_label") else 1.0
        for p in perfumes
    ])

    for group, targets in TARGET_GROUPS.items():
        Y = np.array([_generate_labels(p, group) for p in perfumes])

        if XGB_AVAILABLE:
            from xgboost import XGBRegressor
            from sklearn.multioutput import MultiOutputRegressor
            base = XGBRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0,
            )
            model = MultiOutputRegressor(base, n_jobs=-1)
        else:
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.multioutput import MultiOutputRegressor
            base = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
            model = MultiOutputRegressor(base, n_jobs=-1)

        model.fit(X, Y, sample_weight=sample_weights)
        model.target_names = targets

        path = _model_path(group)
        with open(path, "wb") as f:
            pickle.dump({"model": model, "targets": targets, "version": MODEL_VERSION}, f)
        print(f"Trained and saved: {path}")


_CALIBRATOR_PATH = MODELS_DIR / "longevity_calibrator.pkl"
_longevity_calibrator: Any = None


def _load_calibrator() -> Any | None:
    global _longevity_calibrator
    if _longevity_calibrator is not None:
        return _longevity_calibrator
    if _CALIBRATOR_PATH.exists():
        with open(_CALIBRATOR_PATH, "rb") as f:
            _longevity_calibrator = pickle.load(f)
    return _longevity_calibrator


def load_models() -> dict[str, Any]:
    models = {}
    for group in TARGET_GROUPS:
        path = _model_path(group)
        if path.exists():
            with open(path, "rb") as f:
                models[group] = pickle.load(f)
    return models


def predict(perfume: dict, models: dict | None = None, skip_calibration: bool = False) -> dict:
    """Run all 5 models and return a flat prediction dict."""
    if models is None:
        models = load_models()
        if not models:
            train_all_models([perfume])
            models = load_models()

    feat = build_feature_vector(perfume).reshape(1, -1)
    result: dict[str, Any] = {}

    for group, data in models.items():
        model = data["model"]
        targets = data["targets"]
        preds = model.predict(feat)[0]
        for name, val in zip(targets, preds):
            result[name] = float(np.clip(val, 0, 10))

    # Convert social_distance_idx to label
    sd_idx = int(round(result.pop("social_distance_idx", 1)))
    result["social_distance"] = SOCIAL_DISTANCE_MAP.get(sd_idx, "personal")

    # Temp range not clipped to 0-10
    result["temp_optimal_min_c"] = float(result.get("temp_optimal_min_c", 10))
    result["temp_optimal_max_c"] = float(result.get("temp_optimal_max_c", 25))

    # Longevity hours not clipped to 10
    raw_long = float(np.clip(result.get("longevity_hours", 6), 0, 24))
    if not skip_calibration:
        cal = _load_calibrator()
        if cal is not None:
            import numpy as _np
            raw_long = float(cal.predict([raw_long])[0])
    result["longevity_hours"] = float(np.clip(raw_long, 0.5, 24.0))

    # Dry down character from note chemistry
    result["dry_down_character"] = _describe_dry_down(perfume)

    # Geo city recommendations
    result.update(_geo_cities(result))

    return result


def _describe_dry_down(perfume: dict) -> str:
    base = perfume.get("base_notes", [])
    if not base:
        return "Clean and subtle"
    names = ", ".join(base[:3])
    if any(n.lower() in ("oud", "patchouli", "leather") for n in base):
        return f"Dark and animalic — {names} dominate"
    if any(n.lower() in ("vanilla", "tonka bean", "benzoin") for n in base):
        return f"Warm and gourmand — {names} linger"
    if any(n.lower() in ("cedarwood", "sandalwood", "vetiver") for n in base):
        return f"Dry woody finish — {names} anchor the scent"
    if any(n.lower() in ("musk", "ambroxan", "white musk") for n in base):
        return f"Soft skin-like finish — {names} blend with skin"
    return f"Soft and clean — {names}"


def _geo_cities(result: dict) -> dict:
    tropical = result.get("climate_tropical", 5)
    arid = result.get("climate_arid", 5)
    cold = result.get("climate_cold", 5)
    temperate = result.get("climate_temperate", 5)

    return {
        "geo_tropical_cities": ["Miami", "Singapore", "Bangkok", "Lagos"] if tropical > 6 else ["Miami"],
        "geo_arid_cities": ["Dubai", "Phoenix", "Riyadh", "Las Vegas"] if arid > 6 else ["Dubai"],
        "geo_cold_cities": ["Moscow", "Stockholm", "Toronto", "Oslo"] if cold > 6 else ["Stockholm"],
        "geo_temperate_cities": ["London", "Paris", "New York", "Tokyo"] if temperate > 6 else ["London", "Paris"],
    }
