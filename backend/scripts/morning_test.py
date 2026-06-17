"""
Morning smoke test — predict 20 flagship perfumes and report PASS/WARN/FAIL by confidence.
PASS >= 0.85 | WARN 0.70-0.85 | FAIL < 0.70
"""
import sys
import asyncio
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from sqlalchemy import select
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict
from ml.validators import validate_predictions
from ml.features import compute_note_coverage

# (brand, name, concentration) — fuzzy name match used if exact fails
TARGETS = [
    ("Dior", "Sauvage", "EDT"),
    ("Dior", "Miss Dior", "EDP"),
    ("Chanel", "No 5", "EDP"),
    ("Chanel", "Bleu de Chanel", "EDT"),
    ("Chanel", "Coco Mademoiselle", "EDP"),
    ("Tom Ford", "Tobacco Vanille", None),
    ("Tom Ford", "Oud Wood", None),
    ("Tom Ford", "Lost Cherry", None),
    ("Creed", "Aventus", None),
    ("Yves Saint Laurent", "Black Opium", "EDP"),
    ("Yves Saint Laurent", "La Nuit de L'Homme", "EDT"),
    ("Giorgio Armani", "Acqua di Gio", "EDT"),
    ("Mugler", "Angel", "EDP"),
    ("Viktor&Rolf", "Flowerbomb", "EDP"),
    ("Calvin Klein", "CK One", "EDT"),
    ("Paco Rabanne", "1 Million", "EDT"),
    ("Versace", "Eros", "EDT"),
    ("Gucci", "Gucci Bloom", "EDP"),
    ("Maison Francis Kurkdjian", "Baccarat Rouge 540", "EDP"),
    ("Dior", "J'adore", "EDP"),
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
        "rating_count": p.rating_count or 0,
        "community_longevity_label": p.community_longevity_label or "",
        "has_inferred_pyramid": getattr(p, "has_inferred_pyramid", False) or False,
    }


async def fetch_perfumes(session, brand: str, name: str, conc: str | None):
    """Exact match first, then fuzzy brand+name substring."""
    brand_lower = brand.lower()
    name_lower = name.lower()

    result = await session.execute(select(Perfume))
    all_perfumes = result.scalars().all()

    # Exact match (name + brand, optional concentration)
    for p in all_perfumes:
        if p.brand and p.name:
            b_match = p.brand.lower() == brand_lower
            n_match = p.name.lower() == name_lower
            c_match = (conc is None) or (p.concentration or "EDT") == conc
            if b_match and n_match and c_match:
                return p

    # Fallback: name substring + brand match, pick best by rating_count desc
    candidates = [
        p for p in all_perfumes
        if p.brand and p.name
        and p.brand.lower() == brand_lower
        and name_lower in p.name.lower()
    ]
    if conc:
        exact_conc = [p for p in candidates if (p.concentration or "EDT") == conc]
        if exact_conc:
            candidates = exact_conc

    if candidates:
        return max(candidates, key=lambda p: p.rating_count or 0)

    # Last resort: brand match + any word from name matches, pick highest rating_count
    words = [w for w in name_lower.split() if len(w) > 3]
    last_resort = [
        p for p in all_perfumes
        if p.brand and p.name and p.brand.lower() == brand_lower
        and any(w in p.name.lower() for w in words)
    ]
    if last_resort:
        return max(last_resort, key=lambda p: p.rating_count or 0)

    return None


def _longevity_bucket(hours: float) -> str:
    if hours >= 8:
        return "Strong"
    if hours >= 4:
        return "Moderate"
    return "Light"


async def run_morning_test():
    await init_db()

    models = load_models()
    print(f"Models loaded: {list(models.keys())}\n")
    print("=" * 70)
    print("MORNING TEST — 20 flagship perfumes")
    print("=" * 70)

    results = []

    async with AsyncSessionLocal() as session:
        for brand, name, conc in TARGETS:
            p = await fetch_perfumes(session, brand, name, conc)
            if p is None:
                print(f"[MISS]  {brand} - {name} ({conc or 'any'}) — NOT FOUND IN DB")
                results.append({"status": "MISS", "conf": 0.0, "longevity": 0.0})
                continue

            pd = _perfume_to_dict(p)
            raw = predict(pd, models)

            has_pyramid = bool(pd.get("top_notes") or pd.get("middle_notes") or pd.get("base_notes"))
            coverage = compute_note_coverage(
                pd.get("top_notes", []),
                pd.get("middle_notes", []),
                pd.get("base_notes", []),
            )
            total_cv = sum(
                pd.get(k, 0) or 0
                for k in (
                    "season_spring_votes", "season_summer_votes",
                    "season_fall_votes", "season_winter_votes",
                    "occasion_daily_votes", "occasion_evening_votes",
                    "occasion_sport_votes", "occasion_office_votes",
                    "occasion_night_votes", "occasion_beach_votes",
                )
            )
            validated = validate_predictions(
                raw,
                source_count=pd.get("source_count", 1),
                has_pyramid=has_pyramid,
                has_inferred_pyramid=pd.get("has_inferred_pyramid", False),
                note_coverage=coverage,
                rating_count=pd.get("rating_count", 0),
                total_community_votes=total_cv,
            )

            conf = validated["confidence_score"]
            longevity = validated["longevity_hours"]
            sillage = validated["sillage_score"]
            blind_buy = validated["blind_buy_score"]
            versatility = validated["versatility_score"]
            bucket = _longevity_bucket(longevity)
            actual_conc = pd.get("concentration") or "?"
            sc = pd.get("source_count", 1)
            rc = pd.get("rating_count", 0)

            if conf >= 0.85:
                status = "PASS"
            elif conf >= 0.70:
                status = "WARN"
            else:
                status = "FAIL"

            results.append({"status": status, "conf": conf, "longevity": longevity})

            print(f"[{status}]  {p.brand} - {p.name} ({actual_conc})")
            print(f"  Longevity: {longevity:.1f}h ({bucket})  |  Confidence: {conf:.3f}  |  SC: {sc}  |  Ratings: {rc:,}")
            print(f"  Sillage: {sillage:.1f}  Blind Buy: {blind_buy:.1f}  Versatility: {versatility:.1f}")
            print()

    print("=" * 70)
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_warn = sum(1 for r in results if r["status"] == "WARN")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_miss = sum(1 for r in results if r["status"] == "MISS")
    found = [r for r in results if r["status"] != "MISS"]
    avg_conf = sum(r["conf"] for r in found) / len(found) if found else 0.0
    avg_long = sum(r["longevity"] for r in found) / len(found) if found else 0.0

    print(f"SUMMARY  PASS={n_pass}  WARN={n_warn}  FAIL={n_fail}  MISS={n_miss}")
    print(f"  Avg confidence: {avg_conf:.3f}  |  Avg longevity: {avg_long:.2f}h")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_morning_test())
