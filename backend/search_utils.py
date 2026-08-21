"""Shared pg_trgm + tokenized search helpers used by the perfumes and predict routes."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TRGM_THRESHOLD = 0.15


async def trgm_search(
    db: AsyncSession,
    q: str,
    brand: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """
    Search perfumes by combined `brand || ' ' || name` using pg_trgm similarity,
    OR'd with a tokenized ILIKE ALL match (so multi-word queries like
    "tom ford oud wood" match regardless of trigram score). Falls back to a
    plain ILIKE search if both approaches return nothing.
    """
    q = (q or "").strip()
    if not q:
        return []

    tokens = q.split()
    token_patterns = [f"%{t}%" for t in tokens]
    brand_filter = (brand or "").strip()

    # pg_trgm's similarity() only exists on Postgres — local/dev sqlite goes
    # straight to the ILIKE fallback below.
    if db.bind.dialect.name != "postgresql":
        return await _ilike_fallback(db, q, brand_filter, limit, offset)

    sql = text("""
        SELECT id, name, brand, concentration, gender_vote,
               similarity(brand || ' ' || name, :q) AS score
        FROM perfumes
        WHERE (
            similarity(brand || ' ' || name, :q) > :threshold
            OR (brand || ' ' || name) ILIKE ALL(:token_patterns)
        )
        AND (:brand_filter = '' OR brand ILIKE :brand_pattern)
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(sql, {
        "q": q,
        "threshold": TRGM_THRESHOLD,
        "token_patterns": token_patterns,
        "brand_filter": brand_filter,
        "brand_pattern": f"%{brand_filter}%",
        "limit": limit,
        "offset": offset,
    })
    rows = [dict(r) for r in result.mappings().all()]
    if rows:
        return rows

    # Fallback: plain ILIKE on name/brand (handles queries pg_trgm scores too low,
    # e.g. very short or heavily abbreviated input).
    return await _ilike_fallback(db, q, brand_filter, limit, offset)


async def _ilike_fallback(
    db: AsyncSession, q: str, brand_filter: str, limit: int, offset: int
) -> list[dict]:
    # lower() + LIKE instead of ILIKE so this also works on sqlite (local dev).
    fallback_sql = text("""
        SELECT id, name, brand, concentration, gender_vote, 0.0 AS score
        FROM perfumes
        WHERE (lower(brand) LIKE lower(:like) OR lower(name) LIKE lower(:like))
        AND (:brand_filter = '' OR lower(brand) LIKE lower(:brand_pattern))
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(fallback_sql, {
        "like": f"%{q}%",
        "brand_filter": brand_filter,
        "brand_pattern": f"%{brand_filter}%",
        "limit": limit,
        "offset": offset,
    })
    return [dict(r) for r in result.mappings().all()]
