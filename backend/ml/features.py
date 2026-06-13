import logging
import numpy as np
import json
import os
from typing import Any

logger = logging.getLogger(__name__)

CONCENTRATION_MULTIPLIERS = {
    "EDC": 0.6,
    "EDT": 0.8,
    "EDP": 1.0,
    "Parfum": 1.3,
    "Extrait": 1.4,
}

FAMILIES = [
    "citrus", "woody", "floral", "oriental", "fresh", "gourmand",
    "chypre", "fougere", "aquatic", "spicy", "earthy", "green",
    "powdery", "smoky", "resinous", "musky", "animalic",
]

_notes_db: dict[str, dict] | None = None


def _load_notes_db() -> dict[str, dict]:
    global _notes_db
    if _notes_db is not None:
        return _notes_db
    path = os.path.join(os.path.dirname(__file__), "..", "data", "notes_chemistry.json")
    with open(path, "r") as f:
        notes_list = json.load(f)
    _notes_db = {n["name"].lower(): n for n in notes_list}
    return _notes_db


def _get_note(name: str) -> dict | None:
    db = _load_notes_db()
    return db.get(name.lower())


def compute_note_coverage(top: list, middle: list, base: list) -> float:
    """Return fraction of perfume's notes that have entries in notes_chemistry.json."""
    all_notes = [n for n in (top or []) + (middle or []) + (base or []) if n]
    if not all_notes:
        return 0.5  # unknown coverage — use neutral default
    db = _load_notes_db()
    known = sum(1 for n in all_notes if n.lower() in db)
    return known / len(all_notes)


def _weighted_avg(note_names: list[str], field: str, weight: float, default: float = 5.0) -> tuple[float, float]:
    total_weight = 0.0
    total_value = 0.0
    for name in note_names:
        note = _get_note(name)
        if note:
            total_value += note.get(field, default) * weight
            total_weight += weight
    return total_value, total_weight


def build_feature_vector(perfume: dict[str, Any]) -> np.ndarray:
    """
    Build a fixed-length feature vector from a perfume dict.
    The perfume dict must have: top_notes, middle_notes, base_notes,
    concentration, community_longevity_rating, community_sillage_rating,
    community_overall_rating, season_*_votes, occasion_*_votes.
    """
    top = perfume.get("top_notes", [])
    mid = perfume.get("middle_notes", [])
    base = perfume.get("base_notes", [])

    all_note_names = set(top + mid + base)
    missing = {n for n in all_note_names if not _get_note(n)}
    if missing:
        logger.warning(
            "Notes not in notes_chemistry.json (defaulting to 5.0): %s",
            sorted(missing),
        )

    fields = [
        "volatility", "heat_performance", "cold_performance",
        "humidity_performance", "dry_performance", "skin_bonding",
        "dry_skin_boost", "oily_skin_boost", "projection_strength",
    ]

    # Weighted by pyramid position: top=0.3, mid=0.5, base=0.2
    position_weights = [(top, 0.3), (mid, 0.5), (base, 0.2)]
    note_features = []
    for field in fields:
        total_val = total_w = 0.0
        for notes, w in position_weights:
            for name in notes:
                note = _get_note(name)
                if note:
                    total_val += note.get(field, 5.0) * w
                    total_w += w
        avg = total_val / total_w if total_w > 0 else 5.0
        note_features.append(avg)

    # Longevity class weighted average
    lc_total = lc_w = 0.0
    for notes, w in position_weights:
        for name in notes:
            note = _get_note(name)
            if note:
                lc_total += note.get("longevity_class", 3) * w
                lc_w += w
    note_features.append(lc_total / lc_w if lc_w > 0 else 3.0)

    # Concentration multiplier
    conc = perfume.get("concentration", "EDT")
    conc_mult = CONCENTRATION_MULTIPLIERS.get(conc, 0.8)
    note_features.append(conc_mult)

    # Family distribution
    all_notes = top + mid + base
    family_counts = {f: 0 for f in FAMILIES}
    total_notes = max(len(all_notes), 1)
    for name in all_notes:
        note = _get_note(name)
        if note:
            fam = note.get("family", "").lower()
            if fam in family_counts:
                family_counts[fam] += 1
    family_features = [family_counts[f] / total_notes for f in FAMILIES]

    # Community ratings
    community = [
        float(perfume.get("community_longevity_rating", 3.0)),
        float(perfume.get("community_sillage_rating", 3.0)),
        float(perfume.get("community_overall_rating", 3.0)),
    ]

    # Season vote distribution
    season_votes = [
        float(perfume.get("season_spring_votes", 0)),
        float(perfume.get("season_summer_votes", 0)),
        float(perfume.get("season_fall_votes", 0)),
        float(perfume.get("season_winter_votes", 0)),
    ]
    season_total = max(sum(season_votes), 1)
    season_dist = [v / season_total for v in season_votes]

    # Occasion vote distribution
    occ_votes = [
        float(perfume.get("occasion_daily_votes", 0)),
        float(perfume.get("occasion_evening_votes", 0)),
        float(perfume.get("occasion_sport_votes", 0)),
        float(perfume.get("occasion_office_votes", 0)),
        float(perfume.get("occasion_night_votes", 0)),
        float(perfume.get("occasion_beach_votes", 0)),
    ]
    occ_total = max(sum(occ_votes), 1)
    occ_dist = [v / occ_total for v in occ_votes]

    # Source reliability: normalized source_count capped at 3 → 0.33 / 0.67 / 1.0
    source_count = float(perfume.get("source_count", 1))
    source_reliability = [min(source_count, 3.0) / 3.0]

    vector = note_features + family_features + community + season_dist + occ_dist + source_reliability
    return np.array(vector, dtype=np.float32)


def apply_context_modifiers(predictions: dict, context: dict) -> dict:
    """Adjust raw model predictions based on user-supplied context."""
    if not context:
        return predictions

    skin = context.get("skin_type", "").lower()
    season = context.get("season", "").lower()
    tod = context.get("time_of_day", "").lower()

    p = dict(predictions)

    if skin == "dry":
        p["skin_dry_score"] = min(10.0, p.get("skin_dry_score", 5) * 1.15)
        p["longevity_hours"] = min(24.0, p.get("longevity_hours", 6) * 1.10)
    elif skin == "oily":
        p["skin_oily_score"] = min(10.0, p.get("skin_oily_score", 5) * 1.15)
        p["sillage_score"] = min(10.0, p.get("sillage_score", 5) * 1.10)
    elif skin == "combination":
        p["skin_combo_score"] = min(10.0, p.get("skin_combo_score", 5) * 1.10)
        p["longevity_hours"] = min(24.0, p.get("longevity_hours", 6) * 1.05)
        p["sillage_score"] = min(10.0, p.get("sillage_score", 5) * 1.05)

    season_boosts = {"spring": "season_spring", "summer": "season_summer",
                     "fall": "season_fall", "winter": "season_winter"}
    if season in season_boosts:
        key = season_boosts[season]
        p[key] = min(10.0, p.get(key, 5) * 1.12)

    tod_boosts = {"morning": "time_morning", "afternoon": "time_afternoon",
                  "evening": "time_evening", "night": "time_night"}
    if tod in tod_boosts:
        key = tod_boosts[tod]
        p[key] = min(10.0, p.get(key, 5) * 1.12)

    return p


def get_feature_dim() -> int:
    # 9 chemistry fields + longevity_class + concentration_multiplier = 11
    # + 17 family fractions + 3 community ratings + 4 season fracs + 6 occasion fracs + 1 source_reliability
    return 11 + len(FAMILIES) + 3 + 4 + 6 + 1  # 42
