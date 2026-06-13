"""Cross-validate and sanity-check model predictions."""


def validate_predictions(
    predictions: dict,
    source_count: int = 1,
    has_pyramid: bool = False,
    has_inferred_pyramid: bool = False,
    note_coverage: float = 0.5,
    rating_count: int = 0,
) -> dict:
    """
    Clamp all 0-10 scores, fix logical inconsistencies, compute confidence.

    confidence_score is DATA-QUALITY based:
      base(0.10) + source_count(0-0.25) + pyramid_type(0-0.25) + note_coverage(0-0.30)
      × rating_count_multiplier(0.85-1.05)
      Max ~0.945 for a perfectly documented, highly-rated fragrance.

    Args:
        source_count: number of contributing data sources
        has_pyramid: True if perfume has any note pyramid (real or inferred)
        has_inferred_pyramid: True if pyramid was inferred (not originally provided)
        note_coverage: fraction of notes found in notes_chemistry.json (0-1)
        rating_count: number of community ratings for this perfume
    """
    score_fields = [
        "proj_1hr", "proj_3hr", "proj_6hr", "proj_8hr",
        "sillage_score", "heat_amplification",
        "season_spring", "season_summer", "season_fall", "season_winter",
        "climate_tropical", "climate_arid", "climate_temperate", "climate_cold",
        "humidity_performance", "indoor_score", "outdoor_score",
        "time_morning", "time_afternoon", "time_evening", "time_night",
        "skin_dry_score", "skin_oily_score", "skin_combo_score",
        "age_18_25", "age_25_35", "age_35_50", "age_50_plus",
        "gender_masculine", "gender_feminine", "gender_unisex",
        "personality_dominant", "personality_intellectual",
        "personality_casual", "personality_romantic",
        "occ_office", "occ_date", "occ_casual", "occ_formal", "occ_sport", "occ_travel",
        "cost_per_wear_score", "versatility_score", "compliment_score", "blind_buy_score",
    ]

    p = dict(predictions)
    for field in score_fields:
        if field in p:
            p[field] = float(max(0.0, min(10.0, p[field])))

    # Projection should be non-increasing over time
    p1 = p.get("proj_1hr", 8)
    p3 = p.get("proj_3hr", 7)
    p6 = p.get("proj_6hr", 5)
    p8 = p.get("proj_8hr", 3)
    p["proj_3hr"] = min(p3, p1)
    p["proj_6hr"] = min(p6, p["proj_3hr"])
    p["proj_8hr"] = min(p8, p["proj_6hr"])

    # Longevity clamp
    p["longevity_hours"] = float(max(0.5, min(24.0, p.get("longevity_hours", 6))))

    # Temp range sanity
    t_min = p.get("temp_optimal_min_c", 10)
    t_max = p.get("temp_optimal_max_c", 25)
    if t_max <= t_min:
        p["temp_optimal_max_c"] = t_min + 10

    # ── Data-quality confidence (replaces avg-of-scores formula) ────────────
    # base: every prediction gets at least 0.10
    conf = 0.10

    # source_count contribution: 0.05 (sc=1) → 0.25 (sc≥6)
    sc = max(1, source_count or 1)
    if sc >= 6:
        conf += 0.25
    elif sc >= 4:
        conf += 0.22
    elif sc == 3:
        conf += 0.18
    elif sc == 2:
        conf += 0.13
    else:  # sc == 1
        conf += 0.05

    # pyramid type: 0.00 (none) / 0.15 (inferred) / 0.25 (real)
    if has_pyramid and not has_inferred_pyramid:
        conf += 0.25   # real note pyramid — highest quality
    elif has_pyramid and has_inferred_pyramid:
        conf += 0.15   # inferred pyramid — moderate quality
    # else: no pyramid → 0.00

    # note coverage: up to 0.30
    cov = max(0.0, min(1.0, note_coverage))
    conf += cov * 0.30

    # rating_count multiplier: community validation signal
    rc = rating_count or 0
    if rc > 1000:
        rating_mult = 1.05
    elif rc >= 200:
        rating_mult = 1.00
    elif rc >= 50:
        rating_mult = 0.95
    else:
        rating_mult = 0.85

    p["confidence_score"] = round(min(conf * rating_mult, 0.95), 3)

    return p
