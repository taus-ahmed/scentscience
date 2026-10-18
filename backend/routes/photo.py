"""
Photo-based perfume identification — Phase 2.

POST /api/photo/identify
  Accepts a bottle photo, calls Gemini Flash Vision via direct REST API,
  returns {brand, name, concentration, confidence} for the frontend
  confirmation form. No DB lookup, no prediction yet.

POST /api/photo/predict
  Accepts user-confirmed {brand, name, concentration}.
  1. Trigram DB search — if found, runs full ML prediction.
  2. If not found, calls Gemini to infer notes (reuses ml.gemini_infer),
     then runs the same ML pipeline, marked source="inferred".
"""

import asyncio
import base64
import json
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from config import get_settings
from limiter import limiter
from models.database import get_db
from models.perfume import Perfume
from search_utils import trgm_search

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

_VISION_MODEL = "gemini-2.5-flash"
_GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_VISION_MODEL}:generateContent"
)

# Prompt used for the search-grounded path (google_search tool enabled).
# No responseMimeType when tools are active — we parse the text ourselves.
_IDENTIFY_PROMPT_SEARCH = """Look at this perfume bottle image and use Google Search to identify exactly which perfume this is.

Search for the bottle shape, brand name, and any text visible on the bottle to find the exact product.

After searching, return ONLY a JSON object:
{"brand": "perfume house name", "name": "fragrance name (no brand)", "concentration": "EDP|EDT|Extrait|Parfum|EDC|Unknown", "confidence": 0.0-1.0}

Rules:
- Use Google Search results to confirm what you see in the image.
- NEVER return null — always give your best identified answer.
- Low confidence (0.3-0.5) if unsure, high (0.85-0.95) if the search confirms it.
- Return ONLY the JSON, no markdown."""

# Fallback prompt when search grounding is unavailable.
_IDENTIFY_PROMPT_VISION = """You are a fragrance expert. Examine this perfume bottle image carefully.

Look at ALL text on the bottle: front/back labels, embossed/engraved glass or metal, cap, box.

Return ONLY valid JSON:
{"brand": "perfume house name", "name": "fragrance name (no brand)", "concentration": "EDP|EDT|Extrait|Parfum|EDC|Unknown", "confidence": 0.0-1.0}

NEVER return null — always give your best guess. Use low confidence if unsure."""

# Keep the old name so the identify endpoint can call either version transparently.
_IDENTIFY_PROMPT = _IDENTIFY_PROMPT_SEARCH


async def _gemini_vision(image_bytes: bytes, mime_type: str, prompt: str) -> dict:
    """
    Call Gemini Vision via REST API.
    Primary: uses google_search grounding so Gemini can find the product online.
    Fallback: plain vision without search (responseMimeType=json).
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    image_b64 = base64.b64encode(image_bytes).decode()

    # ── Primary path: search-grounded identification ──────────────────────────
    search_payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": image_b64}},
            ]
        }],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                _GEMINI_REST_URL,
                params={"key": api_key},
                json=search_payload,
            )
        if resp.status_code == 200:
            data = resp.json()
            logger.info("Gemini search-grounded raw response: %s", str(data)[:800])
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Strip markdown fences
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:]).rsplit("```", 1)[0].strip()
            # Extract JSON substring from the response text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(text[start:end])
                logger.info("Gemini search-grounded parsed: %s", parsed)
                return parsed
            logger.warning("No JSON in search-grounded response, falling back. text=%s", text[:300])
        else:
            logger.warning(
                "Gemini search-grounded returned %d, falling back to plain vision",
                resp.status_code,
            )
    except Exception as exc:
        logger.warning("Gemini search-grounded failed (%s), falling back to plain vision", exc)

    # ── Fallback path: plain vision with responseMimeType=json ────────────────
    plain_payload = {
        "contents": [{
            "parts": [
                {"text": _IDENTIFY_PROMPT_VISION},
                {"inline_data": {"mime_type": mime_type, "data": image_b64}},
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp2 = await client.post(
                _GEMINI_REST_URL,
                params={"key": api_key},
                json=plain_payload,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gemini Vision request timed out")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini Vision network error: {exc}")

    if resp2.status_code != 200:
        logger.error(
            "Gemini Vision fallback API error %d: %s",
            resp2.status_code, resp2.text[:400],
        )
        raise HTTPException(
            status_code=502,
            detail=f"Gemini Vision API returned HTTP {resp2.status_code}",
        )

    data2 = resp2.json()
    logger.info("Gemini vision fallback raw response: %s", str(data2)[:600])
    try:
        text2 = data2["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        logger.error("Unexpected Gemini fallback response structure: %s", str(data2)[:400])
        raise HTTPException(status_code=502, detail="Unexpected Gemini response structure")

    if text2.startswith("```"):
        text2 = "\n".join(text2.split("\n")[1:]).rsplit("```", 1)[0].strip()

    try:
        parsed2 = json.loads(text2)
        logger.info("Gemini vision fallback parsed: %s", parsed2)
        return parsed2
    except Exception as exc:
        logger.error("Gemini vision fallback JSON parse error: %s | text=%s", exc, text2[:300])
        raise HTTPException(status_code=502, detail="Could not parse Gemini vision response")


# ── Step 1: identify ──────────────────────────────────────────────────────────

@router.post("/photo/identify")
@limiter.limit("10/minute")
async def identify_from_photo(
    request: Request,
    image: UploadFile = File(...),
):
    """
    Read a bottle photo with Gemini Vision.
    Returns {brand, name, concentration, confidence} for the confirmation form.
    The frontend lets the user edit any field before confirming.
    On any Gemini failure, returns blank fields with a warning so the user
    can type manually — always reaches the confirm stage.
    """
    mime_type = image.content_type or "image/jpeg"
    if not mime_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    try:
        result = await _gemini_vision(image_bytes, mime_type, _IDENTIFY_PROMPT)
    except HTTPException as exc:
        # Re-raise only if it's a config error (503) — otherwise degrade gracefully
        if exc.status_code == 503:
            raise
        logger.warning("Vision call degraded (%s): returning blank fields", exc.detail)
        return {
            "brand":         None,
            "name":          None,
            "concentration": "Unknown",
            "confidence":    0.0,
            "warning":       exc.detail,
        }
    except Exception as exc:
        logger.error("Vision call unexpected error: %s", exc)
        return {
            "brand":         None,
            "name":          None,
            "concentration": "Unknown",
            "confidence":    0.0,
            "warning":       "Auto-identification failed — please type the name below.",
        }

    return {
        "brand":         result.get("brand"),
        "name":          result.get("name"),
        "concentration": result.get("concentration", "Unknown"),
        "confidence":    float(result.get("confidence", 0.5)),
    }


# ── Step 2: confirm → predict ─────────────────────────────────────────────────

# Concentration tokens and filler words we treat as non-identifying when
# checking whether a DB name covers the user's confirmed name.
_NAME_STOP = frozenset({
    "de", "du", "le", "la", "les", "of", "the", "a", "an", "and", "by",
    "pour", "for", "eau", "di", "del", "della",
    "edt", "edp", "extrait", "parfum", "edc",
})


def _name_covers_query(query_name: str, match_name: str) -> bool:
    """
    Return True when the DB match's name covers ≥70 % of the confirmed name's
    meaningful words, OR when the confirmed name has ≤2 meaningful words
    (short queries may be valid abbreviations, so we don't block them).

    Example of what we want to REJECT:
      query_name = "9 PM Night Out"  →  q_words = {"9", "pm", "night", "out"}
      match_name = "9 PM"            →  m_words = {"9", "pm"}
      overlap = 2/4 = 0.50 < 0.70   →  False  →  falls through to AI inference

    Example of what we want to ACCEPT:
      query_name = "Sauvage"         →  q_words = {"sauvage"}  (1 word → skip check)
      query_name = "Aventus For Her" →  q_words = {"aventus"}  ("for"/"her" ignored, 1 word)
    """
    q_words = [w for w in query_name.lower().split() if w not in _NAME_STOP]
    if len(q_words) <= 2:
        return True  # too short to distinguish; trust the trgm score
    m_words = set(w for w in match_name.lower().split() if w not in _NAME_STOP)
    overlap = sum(1 for w in q_words if w in m_words) / len(q_words)
    return overlap >= 0.70


class ConfirmRequest(BaseModel):
    brand: str
    name: str
    concentration: str = "Unknown"


@router.post("/photo/predict")
@limiter.limit("10/minute")
async def predict_from_confirmed(
    request: Request,
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    User has confirmed (and possibly corrected) the identified perfume.
    1. Trigram DB search (same engine as the autocomplete — all 110k+ perfumes).
    2a. Found → full prediction with clean DB data (source="database").
    2b. Not found → Gemini infers notes → prediction (source="inferred").
    """
    from routes.predict import _get_models, _perfume_to_dict
    from ml.model import predict as ml_predict
    from ml.validators import validate_predictions
    from ml.features import apply_context_modifiers, compute_note_coverage
    from ml.note_mapper import build_perfume_dict_from_notes, normalize_concentration
    from ml.gemini_infer import infer_notes

    brand = body.brand.strip()
    name  = body.name.strip()
    conc  = body.concentration.strip() or "Unknown"

    # ── DB lookup (trgm_search across full 110k+ table) ──────────────────────
    query = f"{brand} {name}".strip()
    matches = await trgm_search(db, query, limit=5)

    db_perfume: Optional[Perfume] = None
    if matches and matches[0].get("score", 0) >= 0.55:
        # Extra guard: the matched name must cover ≥70% of the confirmed name's
        # meaningful words.  Prevents "9 PM" (2 words) from satisfying
        # "9 PM Night Out" (4 words) even when the trgm score clears the
        # threshold.  Short queries (≤2 meaningful words) skip this check.
        if _name_covers_query(name, matches[0].get("name", "")):
            row = await db.execute(select(Perfume).where(Perfume.id == matches[0]["id"]))
            db_perfume = row.scalar_one_or_none()

    models = await _get_models()

    if db_perfume:
        # ── Found in DB ───────────────────────────────────────────────────────
        perfume_dict = _perfume_to_dict(db_perfume)
        raw = ml_predict(perfume_dict, models)
        raw = apply_context_modifiers(raw, {})

        has_pyramid = bool(db_perfume.top_notes or db_perfume.middle_notes or db_perfume.base_notes)
        coverage = compute_note_coverage(
            db_perfume.top_notes or [],
            db_perfume.middle_notes or [],
            db_perfume.base_notes or [],
        )
        predictions = validate_predictions(
            raw,
            source_count=db_perfume.source_count or 1,
            has_pyramid=has_pyramid,
            has_inferred_pyramid=bool(db_perfume.has_inferred_pyramid),
            note_coverage=coverage,
            rating_count=db_perfume.rating_count or 0,
            total_community_votes=(
                (db_perfume.season_spring_votes or 0) + (db_perfume.season_summer_votes or 0) +
                (db_perfume.season_fall_votes or 0) + (db_perfume.season_winter_votes or 0) +
                (db_perfume.occasion_daily_votes or 0) + (db_perfume.occasion_evening_votes or 0)
            ),
        )
        predictions["model_version"] = settings.model_version

        return {
            "source": "database",
            "db_match": {
                "id":            db_perfume.id,
                "name":          db_perfume.name,
                "brand":         db_perfume.brand,
                "concentration": db_perfume.concentration,
            },
            "perfume": {
                "id":            db_perfume.id,
                "name":          db_perfume.name,
                "brand":         db_perfume.brand,
                "concentration": db_perfume.concentration,
                "accords":       db_perfume.accords or [],
                "gender_vote":   db_perfume.gender_vote,
            },
            "predictions": predictions,
            "match_score": int(matches[0]["score"] * 100),
        }

    # ── Not in DB — infer notes with Gemini ───────────────────────────────────
    try:
        inferred = await infer_notes(
            name, brand,
            gemini_api_key=settings.gemini_api_key,
            groq_api_key=settings.groq_api_key,
        )
    except Exception as exc:
        logger.error("Note inference failed: %s", exc)
        return {
            "source":      "not_found",
            "db_match":    None,
            "perfume":     None,
            "predictions": None,
            "message":     f'"{name}" by {brand} is not in our database and could not be identified.',
        }

    inferred_conc = normalize_concentration(inferred.get("concentration") or conc)
    perfume_dict = build_perfume_dict_from_notes(
        name=name, brand=brand,
        top_notes=inferred["top_notes"],
        middle_notes=inferred["middle_notes"],
        base_notes=inferred["base_notes"],
        concentration=inferred_conc,
        family=inferred.get("family"),
    )

    raw = ml_predict(perfume_dict, models)
    raw = apply_context_modifiers(raw, {})
    coverage = compute_note_coverage(
        inferred["top_notes"], inferred["middle_notes"], inferred["base_notes"]
    )
    predictions = validate_predictions(
        raw,
        source_count=1,
        has_pyramid=True,
        has_inferred_pyramid=True,
        note_coverage=coverage,
        rating_count=0,
        total_community_votes=0,
    )
    predictions["model_version"] = settings.model_version

    return {
        "source": "inferred",
        "db_match": None,
        "perfume": {
            "id":            None,
            "name":          name,
            "brand":         brand,
            "concentration": inferred_conc,
            "accords":       [inferred["family"]] if inferred.get("family") else [],
            "gender_vote":   None,
        },
        "predictions": predictions,
        "inferred_notes": {
            "top_notes":     inferred["top_notes"],
            "middle_notes":  inferred["middle_notes"],
            "base_notes":    inferred["base_notes"],
            "ai_confidence": inferred.get("confidence", "low"),
        },
        "message": (
            f'"{name}" by {brand} is not in our database. '
            "Prediction is based on Gemini's knowledge of this fragrance."
        ),
        "match_score": 0,
    }
