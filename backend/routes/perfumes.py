from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional

from models.database import get_db
from models.perfume import Perfume

router = APIRouter()


@router.get("/perfumes")
async def list_perfumes(
    q: Optional[str] = Query(None, description="Search by name or brand"),
    brand: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
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
    return [_serialize(p) for p in perfumes]


@router.get("/perfumes/{perfume_id}")
async def get_perfume(perfume_id: int, db: AsyncSession = Depends(get_db)):
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
