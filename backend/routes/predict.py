import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from models.database import get_db
from models.perfume import Perfume
from models.prediction import PredictionResult
from ml.model import predict as ml_predict, load_models, train_all_models
from ml.nlp import generate_nlp_conclusion
from ml.validators import validate_predictions
from ml.features import apply_context_modifiers, compute_note_coverage
from config import get_settings

router = APIRouter()
settings = get_settings()

_models_cache: dict | None = None
_models_lock: asyncio.Lock | None = None


async def _get_models() -> dict:
    global _models_cache, _models_lock
    if _models_lock is None:
        _models_lock = asyncio.Lock()
    async with _models_lock:
        if _models_cache is not None:
            return _models_cache
        cache = load_models()
        if not cache:
            import json
            from pathlib import Path
            seed_path = Path(__file__).parent.parent / "data" / "seed_perfumes.json"
            with open(seed_path) as f:
                perfumes = json.load(f)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, train_all_models, perfumes)
            cache = load_models()
        _models_cache = cache
        return _models_cache


class PredictContext(BaseModel):
    skin_type: Optional[str] = None
    location: Optional[str] = None
    season: Optional[str] = None
    time_of_day: Optional[str] = None


class PredictRequest(BaseModel):
    perfume_name: str
    brand: Optional[str] = None
    context: Optional[PredictContext] = None


def _perfume_to_dict(p: Perfume) -> dict:
    return {
        "name": p.name,
        "brand": p.brand,
        "concentration": p.concentration,
        "top_notes": p.top_notes or [],
        "middle_notes": p.middle_notes or [],
        "base_notes": p.base_notes or [],
        "accords": p.accords or [],
        "gender_vote": p.gender_vote,
        "season_spring_votes": p.season_spring_votes,
        "season_summer_votes": p.season_summer_votes,
        "season_fall_votes": p.season_fall_votes,
        "season_winter_votes": p.season_winter_votes,
        "occasion_daily_votes": p.occasion_daily_votes,
        "occasion_evening_votes": p.occasion_evening_votes,
        "occasion_sport_votes": p.occasion_sport_votes,
        "occasion_office_votes": p.occasion_office_votes,
        "occasion_night_votes": p.occasion_night_votes,
        "occasion_beach_votes": p.occasion_beach_votes,
        "community_longevity_rating": p.community_longevity_rating,
        "community_sillage_rating": p.community_sillage_rating,
        "community_overall_rating": p.community_overall_rating,
        "source_count": p.source_count or 1,
        "rating_count": p.rating_count or 0,
        "community_longevity_label": p.community_longevity_label or "",
    }


@router.post("/predict")
async def predict_endpoint(req: PredictRequest, db: AsyncSession = Depends(get_db)):
    # 1. Fuzzy search perfume in DB
    from rapidfuzz import process, fuzz

    stmt = select(Perfume)
    if req.brand:
        stmt = stmt.where(Perfume.brand.ilike(f"%{req.brand}%"))
    result = await db.execute(stmt)
    perfumes = result.scalars().all()

    if not perfumes:
        # Brand filter returned nothing — retry with name filter only
        stmt2 = select(Perfume).where(Perfume.name.ilike(f"%{req.perfume_name}%"))
        result2 = await db.execute(stmt2)
        perfumes = result2.scalars().all()

    if not perfumes:
        raise HTTPException(
            status_code=404,
            detail=f"Perfume '{req.perfume_name}' not found. Check the name or brand and try again.",
        )

    names = [p.name for p in perfumes]
    match = process.extractOne(req.perfume_name, names, scorer=fuzz.WRatio)
    if not match or match[1] < 40:
        raise HTTPException(status_code=404, detail=f"Perfume '{req.perfume_name}' not found. Try a different name.")

    matched_perfume = perfumes[names.index(match[0])]
    perfume_dict = _perfume_to_dict(matched_perfume)

    # 2. Run ML models
    models = await _get_models()
    raw_predictions = ml_predict(perfume_dict, models)

    # 3. Apply user context modifiers
    ctx_dict = req.context.model_dump() if req.context else {}
    raw_predictions = apply_context_modifiers(raw_predictions, ctx_dict)

    # 4. Validate — pass data-quality signals for confidence weighting
    has_pyramid = bool(
        (matched_perfume.top_notes or matched_perfume.middle_notes or matched_perfume.base_notes)
    )
    coverage = compute_note_coverage(
        matched_perfume.top_notes or [],
        matched_perfume.middle_notes or [],
        matched_perfume.base_notes or [],
    )
    predictions = validate_predictions(
        raw_predictions,
        source_count=matched_perfume.source_count or 1,
        has_pyramid=has_pyramid,
        has_inferred_pyramid=bool(matched_perfume.has_inferred_pyramid),
        note_coverage=coverage,
        rating_count=matched_perfume.rating_count or 0,
    )
    predictions["model_version"] = settings.model_version

    # 5. NLP via Claude
    nlp_conclusion, instagram_brief = await generate_nlp_conclusion(
        matched_perfume.name, matched_perfume.brand, predictions
    )
    predictions["nlp_conclusion"] = nlp_conclusion
    predictions["instagram_brief"] = instagram_brief

    # 6. Save to DB
    pred_row = PredictionResult(
        perfume_id=matched_perfume.id,
        input_context=ctx_dict,
        **{k: v for k, v in predictions.items()
           if k not in ("model_version", "geo_tropical_cities", "geo_arid_cities",
                        "geo_cold_cities", "geo_temperate_cities", "dry_down_character")},
        geo_tropical_cities=predictions.get("geo_tropical_cities", []),
        geo_arid_cities=predictions.get("geo_arid_cities", []),
        geo_cold_cities=predictions.get("geo_cold_cities", []),
        geo_temperate_cities=predictions.get("geo_temperate_cities", []),
        dry_down_character=predictions.get("dry_down_character", ""),
        model_version=settings.model_version,
    )
    db.add(pred_row)
    await db.commit()
    await db.refresh(pred_row)

    return {
        "perfume": {
            "id": matched_perfume.id,
            "name": matched_perfume.name,
            "brand": matched_perfume.brand,
            "concentration": matched_perfume.concentration,
            "accords": matched_perfume.accords,
        },
        "predictions": predictions,
        "prediction_id": pred_row.id,
        "match_score": match[1],
    }
