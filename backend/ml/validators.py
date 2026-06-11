"""Cross-validate and sanity-check model predictions."""


def validate_predictions(predictions: dict) -> dict:
    """Clamp all 0-10 scores, fix logical inconsistencies."""
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

    # Confidence score: average of model-derived scores vs community expectation
    scores = [p.get(f, 5) for f in score_fields if f in p]
    p["confidence_score"] = round(sum(scores) / len(scores) / 10.0, 3) if scores else 0.5

    return p
