"""
Retrain all 5 models on the current DB dataset and report Dior Sauvage prediction.
Loads perfumes from DB if available; falls back to seed JSON.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from sqlalchemy import select
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import train_all_models, load_models, predict
from ml.validators import validate_predictions
from ml.features import compute_note_coverage


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
        "rating_count": p.rating_count or 0,
        "community_longevity_label": p.community_longevity_label or "",
    }


async def load_perfumes_from_db() -> list[dict]:
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Perfume))
        perfumes = result.scalars().all()
        return [_perfume_to_dict(p) for p in perfumes]


def load_perfumes() -> list[dict]:
    try:
        perfumes = asyncio.run(load_perfumes_from_db())
        if len(perfumes) > 20:
            print(f"Loaded {len(perfumes)} perfumes from database.")
            return perfumes
    except Exception as e:
        print(f"DB load failed ({e}), falling back to seed JSON.")

    import json
    seed_path = Path(__file__).parent.parent / "data" / "seed_perfumes.json"
    with open(seed_path) as f:
        perfumes = json.load(f)
    print(f"Loaded {len(perfumes)} perfumes from seed JSON.")
    return perfumes


perfumes = load_perfumes()

print(f"Training on {len(perfumes)} perfumes...")
train_all_models(perfumes)

models = load_models()
print(f"Models loaded: {list(models.keys())}")

# Find Dior Sauvage — prefer EDT, fall back to any concentration
sauvage = None
for conc in ("EDT", "EDP", "Parfum"):
    candidates = [
        p for p in perfumes
        if p["name"].lower() in ("sauvage", "dior sauvage")
        and p["brand"].lower() == "dior"
        and p["concentration"] == conc
    ]
    if candidates:
        sauvage = candidates[0]
        break

if sauvage is None:
    candidates = [
        p for p in perfumes
        if "sauvage" in p["name"].lower() and p["brand"].lower() == "dior"
    ]
    sauvage = candidates[0] if candidates else perfumes[0]
    print(f"  (Using '{sauvage['name']}' by {sauvage['brand']} as test subject)")

raw = predict(sauvage, models)
has_pyramid = bool(sauvage.get("top_notes") or sauvage.get("middle_notes") or sauvage.get("base_notes"))
coverage = compute_note_coverage(
    sauvage.get("top_notes", []),
    sauvage.get("middle_notes", []),
    sauvage.get("base_notes", []),
)
total_cv = sum(
    sauvage.get(k, 0) or 0
    for k in (
        "season_spring_votes", "season_summer_votes",
        "season_fall_votes", "season_winter_votes",
        "occasion_daily_votes", "occasion_evening_votes",
        "occasion_sport_votes", "occasion_office_votes",
        "occasion_night_votes", "occasion_beach_votes",
    )
)
result = validate_predictions(
    raw,
    source_count=sauvage.get("source_count", 1),
    has_pyramid=has_pyramid,
    has_inferred_pyramid=False,
    note_coverage=coverage,
    rating_count=sauvage.get("rating_count", 0),
    total_community_votes=total_cv,
)

print(f"\nDior Sauvage ({sauvage.get('concentration', '?')}) prediction:")
print(f"  Longevity:        {result['longevity_hours']:.1f}h")
print(f"  Sillage:          {result['sillage_score']:.1f}/10")
print(f"  Blind buy:        {result['blind_buy_score']:.1f}/10")
print(f"  Versatility:      {result['versatility_score']:.1f}/10")
print(f"  Season summer:    {result['season_summer']:.1f}/10")
print(f"  Dry down:         {result['dry_down_character']}")
print(f"  source_count:     {sauvage.get('source_count', 1)}")
print(f"  has_pyramid:      {has_pyramid}")
print(f"  longevity_label:  {sauvage.get('community_longevity_label') or '(none)'}")
print(f"  confidence_score: {result['confidence_score']}")
print("Model training SUCCESS")
