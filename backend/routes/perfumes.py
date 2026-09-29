import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, distinct
from typing import Optional
from cachetools import TTLCache

from models.database import get_db
from models.perfume import Perfume
from limiter import limiter
from search_utils import trgm_search

SEASON_COL = {
    "spring": "season_spring_votes",
    "summer": "season_summer_votes",
    "fall": "season_fall_votes",
    "winter": "season_winter_votes",
}

router = APIRouter()

search_cache: TTLCache = TTLCache(maxsize=500, ttl=1800)


@router.get("/perfumes")
@limiter.limit("60/minute")
async def list_perfumes(
    request: Request,
    q: Optional[str] = Query(None, description="Search by name or brand"),
    brand: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    key = hashlib.md5(
        json.dumps({"q": q or "", "brand": brand or "", "limit": limit, "offset": offset}, sort_keys=True).encode()
    ).hexdigest()
    if key in search_cache:
        return search_cache[key]

    if q:
        out = await trgm_search(db, q, brand, limit=limit, offset=offset)
    else:
        stmt = select(Perfume)
        if brand:
            stmt = stmt.where(Perfume.brand.ilike(f"%{brand}%"))
        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        perfumes = result.scalars().all()
        out = [_serialize(p) for p in perfumes]
    search_cache[key] = out
    return out


@router.get("/perfumes/browse")
@limiter.limit("60/minute")
async def browse_perfumes(
    request: Request,
    gender: Optional[str] = Query(None, description="masculine|feminine|unisex"),
    season: Optional[str] = Query(None, description="spring|summer|fall|winter"),
    accord: Optional[str] = Query(None, description="accord keyword for vibe filter"),
    brand: Optional[str] = Query(None, description="canonical brand name (exact match)"),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse endpoint for the Gender / Season / Vibe / Brand tabs.
    At most one of gender/season/accord/brand should be supplied; extras are ignored in that order.
    Results are ranked by real community votes (rating_count DESC) for stability.
    """
    key = hashlib.md5(
        json.dumps({"g": gender or "", "s": season or "", "a": accord or "", "b": brand or "",
                    "limit": limit, "offset": offset}, sort_keys=True).encode()
    ).hexdigest()
    if key in search_cache:
        return search_cache[key]

    stmt = select(Perfume)

    if brand:
        # Brand tab: use brand_canonical when available, fall back to brand ILIKE.
        stmt = stmt.where(
            (Perfume.brand_canonical == brand) | (Perfume.brand.ilike(f"%{brand}%"))
        ).order_by(Perfume.rating_count.desc())

    elif accord:
        # Vibe tab: filter by accord keyword, rank by community overall rating.
        # accords is JSON; cast to jsonb for the contains operator.
        stmt = stmt.where(
            func.cast(Perfume.accords, text("jsonb")).op("@>")(
                text(f"'[\"{accord}\"]'::jsonb")
            )
        ).where(
            Perfume.rating_count >= 5
        ).order_by(Perfume.community_overall_rating.desc(), Perfume.rating_count.desc())

    elif season and season in SEASON_COL:
        # Season tab: rank by votes for that season, require at least 5 votes.
        col = getattr(Perfume, SEASON_COL[season])
        stmt = stmt.where(col >= 5).order_by(col.desc())

    elif gender:
        # Gender tab: masculine/feminine include unisex; unisex-only is its own option.
        if gender == "masculine":
            stmt = stmt.where(Perfume.gender_vote.in_(["masculine", "unisex"]))
        elif gender == "feminine":
            stmt = stmt.where(Perfume.gender_vote.in_(["feminine", "unisex"]))
        else:
            stmt = stmt.where(Perfume.gender_vote == "unisex")
        stmt = stmt.where(Perfume.rating_count >= 5).order_by(Perfume.rating_count.desc())

    else:
        # Default: top-rated with real votes.
        stmt = stmt.where(Perfume.rating_count >= 10).order_by(Perfume.community_overall_rating.desc())

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    out = [_browse_serialize(p) for p in result.scalars().all()]
    search_cache[key] = out
    return out


@router.get("/brands")
@limiter.limit("30/minute")
async def list_brands(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return distinct canonical brand names sorted alphabetically."""
    cache_key = "brands_list"
    if cache_key in search_cache:
        return search_cache[cache_key]

    # Prefer brand_canonical; fall back to brand for rows 001 didn't touch.
    result = await db.execute(
        select(
            func.coalesce(Perfume.brand_canonical, Perfume.brand).label("brand"),
            func.count(Perfume.id).label("count"),
        )
        .group_by(func.coalesce(Perfume.brand_canonical, Perfume.brand))
        .order_by(func.coalesce(Perfume.brand_canonical, Perfume.brand))
    )
    brands = [{"brand": row.brand, "count": row.count} for row in result.all()]
    search_cache[cache_key] = brands
    return brands


def _browse_serialize(p: Perfume) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand_canonical or p.brand,
        "concentration": p.concentration_clean,
        "accords": p.accords,
        "gender_vote": p.gender_vote,
        "rating_count": p.rating_count,
        "community_overall_rating": p.community_overall_rating,
        "community_longevity_rating": p.community_longevity_rating,
    }


@router.get("/perfumes/similar")
@limiter.limit("60/minute")
async def get_similar_perfumes(
    request: Request,
    name: str = Query(..., description="Perfume name to search for"),
    brand: Optional[str] = Query(None),
    limit: int = Query(3, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Return perfumes with the most similar name/brand to the query."""
    if not name:
        return []

    query_str = f"{brand or ''} {name}".strip()
    rows = await trgm_search(db, query_str, limit=limit)

    if not rows:
        stmt2 = (
            select(Perfume)
            .where(Perfume.rating_count.isnot(None))
            .order_by(Perfume.rating_count.desc())
            .limit(limit)
        )
        res2 = await db.execute(stmt2)
        rows = [
            {"id": p.id, "name": p.name, "brand": p.brand, "concentration": p.concentration_clean, "score": 0.0}
            for p in res2.scalars().all()
        ]

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "brand": r["brand"],
            "concentration": r["concentration"],
            "similarity": round(r["score"], 2),
        }
        for r in rows[:limit]
    ]


@router.get("/perfumes/{perfume_id}")
@limiter.limit("60/minute")
async def get_perfume(request: Request, perfume_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Perfume).where(Perfume.id == perfume_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Perfume not found")
    return _serialize(p)


def _serialize(p: Perfume) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "concentration": p.concentration_clean,
        "top_notes": p.top_notes,
        "middle_notes": p.middle_notes,
        "base_notes": p.base_notes,
        "accords": p.accords,
        "gender_vote": p.gender_vote,
        "community_longevity_rating": p.community_longevity_rating,
        "community_sillage_rating": p.community_sillage_rating,
        "community_overall_rating": p.community_overall_rating,
    }
