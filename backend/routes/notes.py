from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from models.database import get_db
from models.perfume import Note

router = APIRouter()


@router.get("/notes")
async def list_notes(
    family: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Note)
    if family:
        stmt = stmt.where(Note.family == family.lower())
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    notes = result.scalars().all()
    return [_serialize(n) for n in notes]


def _serialize(n: Note) -> dict:
    return {
        "id": n.id,
        "name": n.name,
        "family": n.family,
        "volatility": n.volatility,
        "heat_performance": n.heat_performance,
        "cold_performance": n.cold_performance,
        "humidity_performance": n.humidity_performance,
        "skin_bonding": n.skin_bonding,
        "projection_strength": n.projection_strength,
        "longevity_class": n.longevity_class,
    }
