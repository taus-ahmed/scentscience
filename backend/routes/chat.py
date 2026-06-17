import re
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.database import get_db
from models.perfume import Perfume

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: dict = {}


class ChatResponse(BaseModel):
    answer: str
    perfumes: list = []
    action: str = "none"


# ── Intent patterns ───────────────────────────────────────────────────
_COMPARE = re.compile(r'\b(compare|versus|vs\.?|better|difference between|which is better)\b', re.I)
_SIMILAR = re.compile(r'\b(similar to|alternatives? to|dupe[s]? (?:of|for)?|smells? like)\b', re.I)
_RECOMMEND = re.compile(r'\b(recommend|suggest|what should|best for|should i wear|what to wear|wear tonight|wear to|looking for)\b', re.I)

OCCASION_MAP = {
    'office':  ('occasion_office_votes',  ['office', 'work', 'job interview', 'interview', 'professional', 'business']),
    'evening': ('occasion_evening_votes', ['date', 'date night', 'romantic', 'dinner', 'evening']),
    'sport':   ('occasion_sport_votes',   ['gym', 'sport', 'workout', 'athletic', 'exercise', 'running']),
    'night':   ('occasion_night_votes',   ['night out', 'club', 'party', 'bar', 'nightlife']),
    'beach':   ('occasion_beach_votes',   ['beach', 'vacation', 'holiday', 'resort', 'pool']),
    'daily':   ('occasion_daily_votes',   ['casual', 'daily', 'everyday', 'daytime']),
}

SEASON_MAP = {
    'summer': ('season_summer_votes', ['summer', 'hot weather', 'heat', 'tropical', 'warm']),
    'winter': ('season_winter_votes', ['winter', 'cold', 'freezing', 'snow']),
    'spring': ('season_spring_votes', ['spring', 'bloom']),
    'fall':   ('season_fall_votes',   ['fall', 'autumn', 'harvest']),
}

PROPERTY_MAP = {
    'Strong': ['long lasting', 'lasts all day', 'last all day', 'strong', 'beast mode', 'powerhouse', 'heavy', 'intense', 'longevity'],
    'Light':  ['light', 'subtle', 'soft', 'delicate', 'gentle', 'airy', 'skin scent'],
}

ACCORD_MAP = {
    'fresh':  ['fresh', 'citrus', 'aquatic', 'green', 'ozonic', 'clean'],
    'sweet':  ['sweet', 'gourmand', 'vanilla', 'caramel'],
    'woody':  ['woody', 'sandalwood', 'cedar', 'vetiver', 'oud'],
    'floral': ['floral', 'rose', 'jasmine', 'iris', 'peony'],
    'spicy':  ['spicy', 'pepper', 'cinnamon', 'cardamom'],
    'musky':  ['musky', 'musk', 'powdery'],
}

OCCASION_LABELS = {
    'office': 'office / professional',
    'evening': 'date night / evening',
    'sport': 'gym / sport',
    'night': 'night out',
    'beach': 'beach / vacation',
    'daily': 'everyday casual',
}


def _detect_occasion(msg: str) -> Optional[tuple[str, str]]:
    lower = msg.lower()
    for key, (col, keywords) in OCCASION_MAP.items():
        if any(kw in lower for kw in keywords):
            return key, col
    return None


def _detect_season(msg: str) -> Optional[tuple[str, str]]:
    lower = msg.lower()
    for key, (col, keywords) in SEASON_MAP.items():
        if any(kw in lower for kw in keywords):
            return key, col
    return None


def _detect_property(msg: str) -> Optional[str]:
    lower = msg.lower()
    for db_label, keywords in PROPERTY_MAP.items():
        if any(kw in lower for kw in keywords):
            return db_label
    return None


def _detect_accord(msg: str) -> Optional[str]:
    lower = msg.lower()
    for category, keywords in ACCORD_MAP.items():
        if any(kw in lower for kw in keywords):
            return category
    return None


def _extract_names(msg: str) -> list[str]:
    quoted = re.findall(r'"([^"]+)"', msg)
    if quoted:
        return quoted

    # Compare: X vs Y
    m = re.search(r'(?:compare\s+)?(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:\?|\.|$)', msg, re.I)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]

    # Compare X and Y
    m = re.search(r'compare\s+(.+?)\s+and\s+(.+?)(?:\?|\.|$)', msg, re.I)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]

    # Similar to / like / alternatives to X
    m = re.search(
        r'(?:similar to|like|alternatives? to|dupe[s]? (?:of|for)?|smells? like)\s+(.+?)(?:\?|\.|$)',
        msg, re.I
    )
    if m:
        return [m.group(1).strip()]

    return []


def _serialize(p: Perfume) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "concentration": p.concentration,
        "accords": p.accords or [],
        "community_longevity_label": p.community_longevity_label,
        "community_longevity_rating": p.community_longevity_rating,
        "community_overall_rating": p.community_overall_rating,
    }


async def _fuzzy_find(name: str, db: AsyncSession) -> Optional[Perfume]:
    from rapidfuzz import process, fuzz
    from sqlalchemy import or_

    stmt = select(Perfume).where(
        or_(Perfume.name.ilike(f"%{name}%"), Perfume.brand.ilike(f"%{name}%"))
    ).limit(100)
    result = await db.execute(stmt)
    perfumes = result.scalars().all()
    if not perfumes:
        return None
    names = [p.name for p in perfumes]
    match = process.extractOne(name, names, scorer=fuzz.WRatio)
    if not match or match[1] < 40:
        return None
    return perfumes[names.index(match[0])]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    msg = req.message.strip()

    is_compare = bool(_COMPARE.search(msg))
    is_similar = bool(_SIMILAR.search(msg))
    is_recommend = bool(_RECOMMEND.search(msg))

    # ── Compare ───────────────────────────────────────────────────────
    if is_compare:
        names = _extract_names(msg)
        if len(names) >= 2:
            p1 = await _fuzzy_find(names[0], db)
            p2 = await _fuzzy_find(names[1], db)
            if p1 and p2:
                acc1 = {a.lower() for a in (p1.accords or [])}
                acc2 = {a.lower() for a in (p2.accords or [])}
                shared = acc1 & acc2
                only1 = acc1 - acc2
                only2 = acc2 - acc1

                long1 = p1.community_longevity_rating or 3.0
                long2 = p2.community_longevity_rating or 3.0
                longer = p1.name if long1 >= long2 else p2.name

                def fmt(s): return ", ".join(sorted(s)[:4]) if s else "none"

                answer = (
                    f"**{p1.name}** ({p1.brand}) vs **{p2.name}** ({p2.brand})\n\n"
                    f"Shared character: {fmt(shared)}\n"
                    f"{p1.name} uniquely: {fmt(only1)}\n"
                    f"{p2.name} uniquely: {fmt(only2)}\n\n"
                    f"Longevity community rating — {p1.name}: {long1:.1f}/5 · "
                    f"{p2.name}: {long2:.1f}/5 → **{longer}** tends to last longer.\n\n"
                    f"Click either card to run a full ML prediction."
                )
                return ChatResponse(answer=answer, perfumes=[_serialize(p1), _serialize(p2)], action="compare")

            missing = names[0] if not p1 else names[1]
            return ChatResponse(
                answer=f"I couldn't find **\"{missing}\"** in the database. Check the spelling or try putting names in quotes.",
                action="compare",
            )

        return ChatResponse(
            answer='Try: "Compare Sauvage vs Bleu de Chanel" or use quotes like "Chanel No 5" vs "Miss Dior".',
            action="compare",
        )

    # ── Similar ───────────────────────────────────────────────────────
    if is_similar:
        names = _extract_names(msg)
        if names:
            ref = await _fuzzy_find(names[0], db)
            if ref and ref.accords:
                ref_accords = {a.lower() for a in ref.accords}

                stmt = (
                    select(Perfume)
                    .where(Perfume.id != ref.id, Perfume.source_count >= 2)
                    .order_by(desc(Perfume.community_overall_rating))
                    .limit(2000)
                )
                result = await db.execute(stmt)
                candidates = result.scalars().all()

                def jaccard(p):
                    pa = {a.lower() for a in (p.accords or [])}
                    if not pa:
                        return 0.0
                    return len(ref_accords & pa) / len(ref_accords | pa)

                scored = sorted(((p, jaccard(p)) for p in candidates if jaccard(p) > 0), key=lambda x: x[1], reverse=True)
                top = [p for p, _ in scored[:5]]

                acc_str = ", ".join(list(ref_accords)[:4])
                answer = (
                    f"Alternatives to **{ref.name}** by {ref.brand} "
                    f"(known for {acc_str}) — these share the closest accord profiles:"
                )
                return ChatResponse(answer=answer, perfumes=[_serialize(p) for p in top], action="search")

            if ref:
                return ChatResponse(
                    answer=f"Found **{ref.name}** but it has no accord data to match against. Try another fragrance.",
                    action="search",
                )
            return ChatResponse(
                answer=f'I couldn\'t find "{names[0]}" in the database. Try the full name.',
                action="search",
            )

        return ChatResponse(
            answer='Which fragrance are you looking for alternatives to? Try: "What\'s similar to Chanel No 5?"',
            action="search",
        )

    # ── Recommend / Occasion / Season / Property ──────────────────────
    occasion = _detect_occasion(msg)
    season = _detect_season(msg)
    prop = _detect_property(msg)
    accord_cat = _detect_accord(msg)

    if occasion or season or prop or accord_cat or is_recommend:
        stmt = select(Perfume).where(Perfume.source_count >= 2)
        context_parts: list[str] = []

        if prop:
            stmt = stmt.where(Perfume.community_longevity_label == prop)
            context_parts.append(f"{prop.lower()} longevity")

        if occasion:
            occ_key, occ_col = occasion
            stmt = stmt.order_by(desc(getattr(Perfume, occ_col)))
            context_parts.append(OCCASION_LABELS.get(occ_key, occ_key))
        elif season:
            sea_key, sea_col = season
            stmt = stmt.order_by(desc(getattr(Perfume, sea_col)))
            context_parts.append(sea_key)
        else:
            stmt = stmt.order_by(desc(Perfume.community_overall_rating))

        if accord_cat:
            context_parts.append(f"{accord_cat} character")

        stmt = stmt.limit(500)
        result = await db.execute(stmt)
        candidates = result.scalars().all()

        if accord_cat:
            kws = ACCORD_MAP[accord_cat]
            candidates = [
                p for p in candidates
                if p.accords and any(any(kw in a.lower() for kw in kws) for a in p.accords)
            ]

        top = candidates[:5]
        context_str = " + ".join(context_parts) if context_parts else "top-rated"

        if top:
            answer = (
                f"Top picks for **{context_str}**:\n\n"
                f"Click any card to run a full ML prediction on the Dashboard."
            )
        else:
            answer = (
                "No strong matches found. Try rephrasing — e.g. "
                "\"best for office\", \"long lasting floral\", or \"fresh summer fragrance\"."
            )

        return ChatResponse(answer=answer, perfumes=[_serialize(p) for p in top], action="recommend")

    # ── Fallback ──────────────────────────────────────────────────────
    return ChatResponse(
        answer=(
            "I'm ScentScience's fragrance guide. Try asking:\n\n"
            "• \"Best perfume for a job interview\"\n"
            "• \"What lasts all day in summer?\"\n"
            "• \"Compare Sauvage vs Bleu de Chanel\"\n"
            "• \"What's similar to Chanel No 5?\"\n"
            "• \"Recommend something fresh and woody\"\n"
            "• \"I want something long lasting for a night out\""
        ),
        action="none",
    )
