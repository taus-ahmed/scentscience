import difflib
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from cachetools import TTLCache

from models.database import get_db
from models.perfume import Perfume
from limiter import limiter

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

    stmt = select(Perfume)
    if q:
        stmt = stmt.where(
            or_(Perfume.name.ilike(f"%{q}%"), Perfume.brand.ilike(f"%{q}%"))
        )
    if brand:
        stmt = stmt.where(Perfume.brand.ilike(f"%{brand}%"))
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    perfumes = result.scalars().all()
    out = [_serialize(p) for p in perfumes]
    search_cache[key] = out
    return out


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

    first_word = name.split()[0]
    stmt = select(Perfume).where(Perfume.name.ilike(f"%{first_word}%")).limit(60)
    res = await db.execute(stmt)
    candidates = res.scalars().all()

    if not candidates:
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
        "concentration": p.concentration,
        "top_notes": p.top_notes,
        "middle_notes": p.middle_notes,
        "base_notes": p.base_notes,
        "accords": p.accords,
        "gender_vote": p.gender_vote,
        "community_longevity_rating": p.community_longevity_rating,
        "community_sillage_rating": p.community_sillage_rating,
        "community_overall_rating": p.community_overall_rating,
    }
