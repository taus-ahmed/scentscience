import asyncio
import difflib
import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from cachetools import TTLCache

from models.database import get_db
from models.perfume import Perfume
from models.prediction import PredictionResult
from ml.model import predict as ml_predict, load_models, train_all_models
from ml.nlp import generate_nlp_conclusion
from ml.validators import validate_predictions
from ml.features import apply_context_modifiers, compute_note_coverage
from ml.note_mapper import build_perfume_dict_from_notes, normalize_concentration
from config import get_settings
from limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

predict_cache: TTLCache = TTLCache(maxsize=1000, ttl=3600)

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
            import json as _json
            from pathlib import Path
            seed_path = Path(__file__).parent.parent / "data" / "seed_perfumes.json"
            with open(seed_path) as f:
                perfumes = _json.load(f)
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


class FromNotesRequest(BaseModel):
    name: str = "Custom Fragrance"
    brand: str = "Unknown"
    top_notes: list[str] = []
    middle_notes: list[str] = []
    base_notes: list[str] = []
    concentration: str = "EDP"
    family: Optional[str] = None


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


def _predict_cache_key(req: PredictRequest) -> str:
    data = {
        "name": req.perfume_name.lower().strip(),
        "brand": (req.brand or "").lower().strip(),
        "skin_type": (req.context.skin_type if req.context else None) or "",
        "season": (req.context.season if req.context else None) or "",
        "time_of_day": (req.context.time_of_day if req.context else None) or "",
    }
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _check_admin(request: Request) -> bool:
    """Return True if the request carries a valid admin key header."""
    provided_key = request.headers.get("x-admin-key", "")
    return bool(getattr(settings, 'admin_key', None)) and provided_key == settings.admin_key


async def _find_similar(
    name: str,
    brand: Optional[str],
    db: AsyncSession,
    limit: int = 3,
) -> list[dict]:
    """Return up to `limit` DB perfumes most similar to the searched name/brand."""
    _words = (name or "").split()
    first_word = _words[0] if _words else None
    if not first_word:
        return []

    stmt = select(Perfume).where(Perfume.name.ilike(f"%{first_word}%")).limit(60)
    res = await db.execute(stmt)
    candidates = res.scalars().all()

    if not candidates:
        # fallback: most-rated perfumes
        stmt2 = (
            select(Perfume)
            .where(Perfume.rating_count.isnot(None))
            .order_by(Perfume.rating_count.desc())
            .limit(limit)
        )
        res2 = await db.execute(stmt2)
        candidates = res2.scalars().all()

    if not candidates:
        return []

    query_str = f"{brand or ''} {name}".lower().strip()
    scored = [
        (
            p,
            difflib.SequenceMatcher(
                None, query_str, f"{p.brand or ''} {p.name}".lower().strip()
            ).ratio(),
        )
        for p in candidates
    ]
    scored.sort(key=lambda x: -x[1])

    return [
        {
            "id": p.id,
            "name": p.name,
            "brand": p.brand,
            "concentration": p.concentration,
            "similarity": round(score, 2),
        }
        for p, score in scored[:limit]
    ]


async def _run_ml_pipeline(
    perfume_dict: dict,
    name: str,
    brand: str,
    context: Optional[PredictContext],
    models: dict,
    has_real_pyramid: bool,
) -> dict:
    """Run ML models + context modifiers + validation + NLP for a perfume dict."""
    raw_predictions = ml_predict(perfume_dict, models)
    ctx_dict = context.model_dump() if context else {}
    raw_predictions = apply_context_modifiers(raw_predictions, ctx_dict)

    has_pyramid = bool(
        perfume_dict.get("top_notes")
        or perfume_dict.get("middle_notes")
        or perfume_dict.get("base_notes")
    )
    coverage = compute_note_coverage(
        perfume_dict.get("top_notes", []),
        perfume_dict.get("middle_notes", []),
        perfume_dict.get("base_notes", []),
    )
    predictions = validate_predictions(
        raw_predictions,
        source_count=1,
        has_pyramid=has_pyramid,
        has_inferred_pyramid=not has_real_pyramid,
        note_coverage=coverage,
        rating_count=0,
        total_community_votes=0,
    )
    predictions["model_version"] = settings.model_version

    nlp_conclusion, instagram_brief = await generate_nlp_conclusion(name, brand, predictions)
    predictions["nlp_conclusion"] = nlp_conclusion
    predictions["instagram_brief"] = instagram_brief
    return predictions


@router.post("/predict")
@limiter.limit("30/minute")
async def predict_endpoint(
    request: Request,
    req: PredictRequest,
    db: AsyncSession = Depends(get_db),
):
    key = _predict_cache_key(req)
    if key in predict_cache:
        return predict_cache[key]

    # 1. Fuzzy search perfume in DB
    from rapidfuzz import process, fuzz

    stmt = select(Perfume).limit(500)
    if req.brand:
        stmt = select(Perfume).where(Perfume.brand.ilike(f"%{req.brand}%")).limit(200)
    result = await db.execute(stmt)
    perfumes = result.scalars().all()

    if not perfumes:
        stmt2 = select(Perfume).where(Perfume.name.ilike(f"%{req.perfume_name}%")).limit(200)
        result2 = await db.execute(stmt2)
        perfumes = result2.scalars().all()

    # Try fuzzy match
    matched_perfume = None
    match_score = 0
    if perfumes:
        names = [p.name for p in perfumes]
        match = process.extractOne(req.perfume_name, names, scorer=fuzz.WRatio)
        if match and match[1] >= 40:
            matched_perfume = perfumes[names.index(match[0])]
            match_score = match[1]

    # 2. Handle not-found
    if matched_perfume is None:
        is_admin = _check_admin(request)

        if is_admin and (settings.gemini_api_key or settings.groq_api_key):
            # Admin path: infer notes via AI then run full ML pipeline
            from ml.gemini_infer import infer_notes
            try:
                inferred = await infer_notes(
                    req.perfume_name,
                    req.brand or "Unknown",
                    gemini_api_key=settings.gemini_api_key,
                    groq_api_key=settings.groq_api_key,
                )
            except Exception as exc:
                logger.error("AI note inference failed: %s", exc)
                raise HTTPException(status_code=503, detail=f"AI inference failed: {exc}")

            perfume_dict = build_perfume_dict_from_notes(
                name=req.perfume_name,
                brand=req.brand or "Unknown",
                top_notes=inferred["top_notes"],
                middle_notes=inferred["middle_notes"],
                base_notes=inferred["base_notes"],
                concentration=normalize_concentration(inferred["concentration"]),
                family=inferred.get("family"),
            )

            models = await _get_models()
            predictions = await _run_ml_pipeline(
                perfume_dict=perfume_dict,
                name=req.perfume_name,
                brand=req.brand or "Unknown",
                context=req.context,
                models=models,
                has_real_pyramid=False,  # AI-inferred → inferred pyramid tier
            )

            result_out = {
                "perfume": {
                    "id": None,
                    "name": req.perfume_name,
                    "brand": req.brand or "Unknown",
                    "concentration": normalize_concentration(inferred["concentration"]),
                    "accords": [inferred["family"]] if inferred.get("family") else [],
                },
                "predictions": predictions,
                "prediction_id": None,
                "match_score": 100,
                "source": "ai_inferred",
                "inferred_notes": {
                    "top_notes": inferred["top_notes"],
                    "middle_notes": inferred["middle_notes"],
                    "base_notes": inferred["base_notes"],
                    "ai_confidence": inferred.get("confidence", "low"),
                },
            }
            return result_out

        # Regular user: return similar perfumes, no prediction
        similar = await _find_similar(req.perfume_name, req.brand, db)
        return {"not_found": True, "similar": similar, "requires_notes": True}

    # 3. Normal DB-match path
    perfume_dict = _perfume_to_dict(matched_perfume)
    models = await _get_models()
    raw_predictions = ml_predict(perfume_dict, models)

    ctx_dict = req.context.model_dump() if req.context else {}
    raw_predictions = apply_context_modifiers(raw_predictions, ctx_dict)

    has_pyramid = bool(
        matched_perfume.top_notes or matched_perfume.middle_notes or matched_perfume.base_notes
    )
    coverage = compute_note_coverage(
        matched_perfume.top_notes or [],
        matched_perfume.middle_notes or [],
        matched_perfume.base_notes or [],
    )
    total_community_votes = (
        (matched_perfume.season_spring_votes or 0)
        + (matched_perfume.season_summer_votes or 0)
        + (matched_perfume.season_fall_votes or 0)
        + (matched_perfume.season_winter_votes or 0)
        + (matched_perfume.occasion_daily_votes or 0)
        + (matched_perfume.occasion_evening_votes or 0)
        + (matched_perfume.occasion_sport_votes or 0)
        + (matched_perfume.occasion_office_votes or 0)
        + (matched_perfume.occasion_night_votes or 0)
        + (matched_perfume.occasion_beach_votes or 0)
    )
    predictions = validate_predictions(
        raw_predictions,
        source_count=matched_perfume.source_count or 1,
        has_pyramid=has_pyramid,
        has_inferred_pyramid=bool(matched_perfume.has_inferred_pyramid),
        note_coverage=coverage,
        rating_count=matched_perfume.rating_count or 0,
        total_community_votes=total_community_votes,
    )
    predictions["model_version"] = settings.model_version

    nlp_conclusion, instagram_brief = await generate_nlp_conclusion(
        matched_perfume.name, matched_perfume.brand, predictions
    )
    predictions["nlp_conclusion"] = nlp_conclusion
    predictions["instagram_brief"] = instagram_brief

    _DB_EXCLUDE = frozenset({
        "model_version", "family_features", "confidence_breakdown",
        "geo_tropical_cities", "geo_arid_cities", "geo_cold_cities",
        "geo_temperate_cities", "dry_down_character",
    })
    pred_row = PredictionResult(
        perfume_id=matched_perfume.id,
        input_context=ctx_dict,
        **{k: v for k, v in predictions.items() if k not in _DB_EXCLUDE},
        geo_tropical_cities=predictions.get("geo_tropical_cities", []),
        geo_arid_cities=predictions.get("geo_arid_cities", []),
        geo_cold_cities=predictions.get("geo_cold_cities", []),
        geo_temperate_cities=predictions.get("geo_temperate_cities", []),
        dry_down_character=predictions.get("dry_down_character", ""),
        model_version=settings.model_version,
    )
    try:
        db.add(pred_row)
        await db.commit()
        await db.refresh(pred_row)
    except Exception as _e:
        logger.warning(f"Prediction log DB save failed (non-fatal): {_e}")
        await db.rollback()

    result_out = {
        "perfume": {
            "id": matched_perfume.id,
            "name": matched_perfume.name,
            "brand": matched_perfume.brand,
            "concentration": matched_perfume.concentration,
            "accords": matched_perfume.accords,
        },
        "predictions": predictions,
        "prediction_id": pred_row.id,
        "match_score": match_score,
        "source": "db_match",
    }
    predict_cache[key] = result_out
    return result_out


@router.post("/predict/from-notes")
@limiter.limit("20/minute")
async def predict_from_notes(
    request: Request,
    req: FromNotesRequest,
):
    """
    Run a full ML prediction from user-supplied notes without a DB lookup.
    Source: 'user_notes'. Not cached, not saved to DB.
    """
    perfume_dict = build_perfume_dict_from_notes(
        name=req.name,
        brand=req.brand,
        top_notes=req.top_notes,
        middle_notes=req.middle_notes,
        base_notes=req.base_notes,
        concentration=req.concentration,
        family=req.family,
    )

    models = await _get_models()
    predictions = await _run_ml_pipeline(
        perfume_dict=perfume_dict,
        name=req.name,
        brand=req.brand,
        context=None,
        models=models,
        has_real_pyramid=True,  # user provided real notes
    )
    predictions["source"] = "user_notes"

    return {
        "perfume": {
            "id": None,
            "name": req.name,
            "brand": req.brand,
            "concentration": normalize_concentration(req.concentration),
            "accords": [req.family] if req.family else [],
        },
        "predictions": predictions,
        "prediction_id": None,
        "match_score": 100,
        "source": "user_notes",
    }
