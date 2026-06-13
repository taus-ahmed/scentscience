"""Quick check of Sauvage variants — confidence scores with new formula."""
import asyncio, sys, math
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
from ml.features import compute_note_coverage


async def main():
    await init_db()
    models = load_models()

    async with AsyncSessionLocal() as s:
        q = await s.execute(
            select(Perfume).where(
                Perfume.brand.ilike("%dior%"),
                Perfume.name.ilike("%sauvage%"),
            ).order_by(Perfume.source_count.desc(), Perfume.rating_count.desc())
        )
        rows = q.scalars().all()

    print(f"Found {len(rows)} Dior Sauvage variants:\n")
    print(f"  {'Name':<32} {'Conc':<8} SC  {'rating_count':>12}  {'cv_total':>8}  mult   conf")
    print("  " + "-" * 80)

    for p in rows[:10]:
        total_cv = (
            (p.season_spring_votes or 0) + (p.season_summer_votes or 0) +
            (p.season_fall_votes or 0) + (p.season_winter_votes or 0) +
            (p.occasion_daily_votes or 0) + (p.occasion_evening_votes or 0) +
            (p.occasion_sport_votes or 0) + (p.occasion_office_votes or 0) +
            (p.occasion_night_votes or 0) + (p.occasion_beach_votes or 0)
        )
        pd = {
            "name": p.name, "brand": p.brand,
            "concentration": p.concentration or "EDT",
            "top_notes": p.top_notes or [], "middle_notes": p.middle_notes or [],
            "base_notes": p.base_notes or [], "accords": p.accords or [],
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
            "rating_count": p.rating_count or 0,
            "community_longevity_label": p.community_longevity_label or "",
        }
        raw = predict(pd, models)
        has_pyr = bool(pd["top_notes"] or pd["middle_notes"] or pd["base_notes"])
        cov = compute_note_coverage(pd["top_notes"], pd["middle_notes"], pd["base_notes"])
        res = validate_predictions(
            raw, source_count=pd["source_count"], has_pyramid=has_pyr,
            has_inferred_pyramid=bool(p.has_inferred_pyramid), note_coverage=cov,
            rating_count=pd["rating_count"], total_community_votes=total_cv,
        )
        rc = p.rating_count or 0
        if rc <= 0:
            mult = 0.80
        else:
            lf = min(1.0, max(0.0, (math.log10(rc) - 1.0) / 3.0))
            mult = 0.85 + 0.35 * lf
        conc = p.concentration or "?"
        print(f"  {p.name:<32} {conc:<8} {p.source_count}   {rc:>12}   {total_cv:>8}  {mult:.3f}  {res['confidence_score']}")


if __name__ == "__main__":
    asyncio.run(main())
