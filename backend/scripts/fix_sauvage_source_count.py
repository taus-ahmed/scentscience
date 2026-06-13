"""
Fix: Dior Sauvage EDT (id=1) was skipped by the fra_perfumes source_count increment
because id=2 (EDP) stole its by_brand['dior']['sauvage'] slot (last-write-wins collision).

Patch id=1:
  - source_count: 1 → 2
  - accords: fill the 9 accords from fra_perfumes row (Sauvage-31861)
  - fragrantica_url: set from fra_perfumes URL

Then re-run prediction to show updated confidence_score.
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv; load_dotenv(_env)

from sqlalchemy import select
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict
from ml.validators import validate_predictions

# Data from fra_perfumes.csv row for https://www.fragrantica.com/perfume/Dior/Sauvage-31861.html
SAUVAGE_EDT_URL    = "https://www.fragrantica.com/perfume/Dior/Sauvage-31861.html"
SAUVAGE_EDT_ACCORDS = [
    "fresh spicy", "amber", "citrus", "aromatic",
    "musky", "woody", "herbal", "lavender", "warm spicy",
]


def _perfume_to_dict(p: Perfume) -> dict:
    return {
        "name": p.name,
        "brand": p.brand,
        "concentration": p.concentration or "EDT",
        "top_notes": p.top_notes or [],
        "middle_notes": p.middle_notes or [],
        "base_notes": p.base_notes or [],
        "accords": p.accords or [],
        "gender_vote": p.gender_vote or "unisex",
        "season_spring_votes": p.season_spring_votes or 0,
        "season_summer_votes": p.season_summer_votes or 0,
        "season_fall_votes": p.season_fall_votes or 0,
        "season_winter_votes": p.season_winter_votes or 0,
        "occasion_daily_votes": p.occasion_daily_votes or 0,
        "occasion_evening_votes": p.occasion_evening_votes or 0,
        "occasion_sport_votes": p.occasion_sport_votes or 0,
        "occasion_office_votes": p.occasion_office_votes or 0,
        "occasion_night_votes": p.occasion_night_votes or 0,
        "occasion_beach_votes": p.occasion_beach_votes or 0,
        "community_longevity_rating": p.community_longevity_rating or 3.0,
        "community_sillage_rating": p.community_sillage_rating or 3.0,
        "community_overall_rating": p.community_overall_rating or 3.0,
        "source_count": p.source_count or 1,
        "community_longevity_label": p.community_longevity_label or "",
    }


async def main():
    await init_db()
    models = load_models()

    async with AsyncSessionLocal() as s:
        q = await s.execute(select(Perfume).where(Perfume.id == 1))
        p = q.scalars().one()

        print(f"BEFORE fix:")
        print(f"  id={p.id}  name={p.name!r}  conc={p.concentration!r}")
        print(f"  source_count={p.source_count}")
        print(f"  accords ({len(p.accords or [])}): {p.accords}")
        print(f"  url: {p.fragrantica_url}")

        before_dict = _perfume_to_dict(p)
        before_raw  = predict(before_dict, models)
        has_pyr     = bool(before_dict.get("top_notes") or before_dict.get("middle_notes") or before_dict.get("base_notes"))
        before_res  = validate_predictions(before_raw, source_count=before_dict["source_count"], has_pyramid=has_pyr)
        print(f"  confidence BEFORE: {before_res['confidence_score']:.3f}  (multiplier=0.90, sc=1, pyramid={has_pyr})")

        print()

        # Apply the patch
        p.source_count     = 2
        p.accords          = SAUVAGE_EDT_ACCORDS
        p.fragrantica_url  = SAUVAGE_EDT_URL
        await s.commit()
        await s.refresh(p)

        print(f"AFTER fix:")
        print(f"  source_count={p.source_count}")
        print(f"  accords ({len(p.accords)}): {p.accords}")
        print(f"  url: {p.fragrantica_url}")

        after_dict = _perfume_to_dict(p)
        after_raw  = predict(after_dict, models)
        has_pyr2   = bool(after_dict.get("top_notes") or after_dict.get("middle_notes") or after_dict.get("base_notes"))
        after_res  = validate_predictions(after_raw, source_count=after_dict["source_count"], has_pyramid=has_pyr2)

        sc = after_dict["source_count"]
        if sc >= 2 and has_pyr2:
            mult = 1.00
        elif sc >= 2:
            mult = 0.85
        elif has_pyr2:
            mult = 0.90
        else:
            mult = 0.70

        print()
        print(f"Dior Sauvage EDT — FINAL PREDICTION after fix:")
        print(f"  Longevity:          {after_res['longevity_hours']:.1f}h")
        print(f"  Sillage:            {after_res['sillage_score']:.1f}/10")
        print(f"  Blind Buy:          {after_res['blind_buy_score']:.1f}/10")
        print(f"  Versatility:        {after_res['versatility_score']:.1f}/10")
        print(f"  Season best:        Spring={after_res['season_spring']:.1f}  Summer={after_res['season_summer']:.1f}  Fall={after_res['season_fall']:.1f}  Winter={after_res['season_winter']:.1f}")
        print(f"  source_count:       {sc}")
        print(f"  has_pyramid:        {has_pyr2}")
        print(f"  quality_multiplier: {mult:.2f}")
        print(f"  confidence_score:   {after_res['confidence_score']:.3f}")
        print()
        print(f"  Delta: {before_res['confidence_score']:.3f} -> {after_res['confidence_score']:.3f}  "
              f"(+{after_res['confidence_score'] - before_res['confidence_score']:.3f}  "
              f"from multiplier 0.90 -> {mult:.2f})")

asyncio.run(main())
