"""Shared pg_trgm + tokenized search helpers used by the perfumes and predict routes."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TRGM_THRESHOLD = 0.15
SHORT_QUERY_LEN = 3


async def trgm_search(
    db: AsyncSession,
    q: str,
    brand: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """
    Search perfumes by pg_trgm similarity, scoring name and brand separately
    (so a strong match on either field alone can surface a result, e.g. a
    right-name/wrong-brand query) and taking the best of the two plus the
    combined `brand || ' ' || name` similarity. OR'd with a tokenized ILIKE
    ALL match for word-order tolerance, and a prefix match for very short
    queries where trigram similarity is unreliable. Falls back to a plain
    ILIKE search if nothing matches.

    Results are ranked by similarity x (1 + log(1 + rating_count)) so
    well-known originals with real rating history outrank low-signal
    name-alike clones at similar text similarity.
    """
    q = (q or "").strip()
    if not q:
        return []

    tokens = q.split()
    token_patterns = [f"%{t}%" for t in tokens]
    brand_filter = (brand or "").strip()
    short_query = len(q) < SHORT_QUERY_LEN

    # pg_trgm's similarity() only exists on Postgres — local/dev sqlite goes
    # straight to the ILIKE fallback below.
    if db.bind.dialect.name != "postgresql":
        return await _ilike_fallback(db, q, brand_filter, limit, offset)

    prefix_clause = "OR name ILIKE :prefix_pattern OR brand ILIKE :prefix_pattern" if short_query else ""

    sql = text(f"""
        WITH matches AS (
            SELECT id, name, brand, concentration, gender_vote, rating_count,
                   GREATEST(
                       similarity(name, :q),
                       similarity(brand, :q),
                       similarity(brand || ' ' || name, :q)
                   ) AS score
            FROM perfumes
            WHERE (
                similarity(brand || ' ' || name, :q) > :threshold
                OR similarity(name, :q) > :threshold
                OR similarity(brand, :q) > :threshold
                OR (brand || ' ' || name) ILIKE ALL(:token_patterns)
                {prefix_clause}
            )
            AND (:brand_filter = '' OR brand ILIKE :brand_pattern)
        )
        SELECT id, name, brand, concentration, gender_vote, score
        FROM matches
        ORDER BY score * (1 + ln(1 + COALESCE(rating_count, 0))) DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(sql, {
        "q": q,
        "threshold": TRGM_THRESHOLD,
        "token_patterns": token_patterns,
        "prefix_pattern": f"{q}%",
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
    # No trigram similarity is available here, so rating_count alone drives
    # the same "popularity-aware" ranking as the primary path.
    fallback_sql = text("""
        SELECT id, name, brand, concentration, gender_vote, 0.0 AS score
        FROM perfumes
        WHERE (lower(brand) LIKE lower(:like) OR lower(name) LIKE lower(:like))
        AND (:brand_filter = '' OR lower(brand) LIKE lower(:brand_pattern))
        ORDER BY COALESCE(rating_count, 0) DESC
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
