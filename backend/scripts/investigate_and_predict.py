"""
Investigation script:
  1. Find well-known perfumes with source_count >= 2 + real pyramids; predict each.
  2. Find one with an inferred pyramid; predict it.
  3. Investigate why Dior Sauvage has source_count=1.
"""
import sys
import csv
import re
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)

from sqlalchemy import select, text
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict
from ml.validators import validate_predictions

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"
FUZZY_THRESHOLD = 85

# ── helpers ───────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


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


def print_prediction(label: str, p_dict: dict, p_obj: Perfume, models: dict) -> None:
    raw = predict(p_dict, models)
    has_pyramid = bool(p_dict.get("top_notes") or p_dict.get("middle_notes") or p_dict.get("base_notes"))
    result = validate_predictions(
        raw,
        source_count=p_dict.get("source_count", 1),
        has_pyramid=has_pyramid,
    )
    sc = p_dict.get("source_count", 1)
    multiplier = result["confidence_score"] / (sum([
        result["longevity_hours"] / 12,
        result["sillage_score"] / 10,
        result["blind_buy_score"] / 10,
        result["versatility_score"] / 10,
    ]) / 4) if (sum([
        result["longevity_hours"] / 12,
        result["sillage_score"] / 10,
        result["blind_buy_score"] / 10,
        result["versatility_score"] / 10,
    ]) / 4) > 0 else 0

    # Derive the actual multiplier from the tiers
    if sc >= 2 and has_pyramid:
        qual_mult = 1.00
    elif sc >= 2 and not has_pyramid:
        qual_mult = 0.85
    elif sc == 1 and has_pyramid:
        qual_mult = 0.90
    else:
        qual_mult = 0.70

    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"  {p_dict['name']} ({p_dict.get('concentration','EDT')}) by {p_dict['brand']}")
    print(f"{'─'*60}")
    print(f"  Longevity:          {result['longevity_hours']:.1f}h")
    print(f"  Sillage:            {result['sillage_score']:.1f}/10")
    print(f"  Blind Buy:          {result['blind_buy_score']:.1f}/10")
    print(f"  Versatility:        {result['versatility_score']:.1f}/10")
    print(f"  Season best:        Spring={result['season_spring']:.1f}  Summer={result['season_summer']:.1f}  Fall={result['season_fall']:.1f}  Winter={result['season_winter']:.1f}")
    print(f"  Dry down:           {result.get('dry_down_character','')}")
    print(f"  source_count:       {sc}")
    print(f"  has_pyramid:        {has_pyramid}  (inferred={getattr(p_obj,'has_inferred_pyramid',False)})")
    print(f"  longevity_label:    {p_dict.get('community_longevity_label') or '(none)'}")
    print(f"  quality_multiplier: {qual_mult:.2f}")
    print(f"  confidence_score:   {result['confidence_score']:.3f}")
    all_notes = (p_dict.get("top_notes") or []) + (p_dict.get("middle_notes") or []) + (p_dict.get("base_notes") or [])
    print(f"  notes ({len(all_notes)}):           {', '.join(all_notes[:10])}{'...' if len(all_notes) > 10 else ''}")
    print(f"  accords:            {', '.join((p_dict.get('accords') or [])[:6])}")


# ── DB queries ────────────────────────────────────────────────────────────────

async def main() -> None:
    await init_db()

    print("Loading models from pkl files...")
    models = load_models()
    print(f"Models loaded: {list(models.keys())}\n")

    async with AsyncSessionLocal() as session:

        # ── 1. Query Dior Sauvage exact state ─────────────────────────────────
        print("=" * 60)
        print("SECTION 1: Dior Sauvage — current DB state")
        print("=" * 60)

        q = select(Perfume).where(
            Perfume.brand.ilike("dior"),
            Perfume.name.ilike("%sauvage%"),
        )
        rows = (await session.execute(q)).scalars().all()
        print(f"\nFound {len(rows)} 'Sauvage' records under Dior:")
        for r in rows:
            top = (r.top_notes or [])
            mid = (r.middle_notes or [])
            base = (r.base_notes or [])
            print(f"  id={r.id:>6} | name='{r.name}' | conc={r.concentration:<8} | "
                  f"source_count={r.source_count} | has_inferred={r.has_inferred_pyramid} | "
                  f"notes={len(top)+len(mid)+len(base)} | accords={len(r.accords or [])} | "
                  f"url={r.fragrantica_url or '(none)'}")

        # ── 2. CSV investigation ───────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("SECTION 2: CSV investigation — Sauvage in source files")
        print("=" * 60)

        # fra_cleaned.csv
        fra_cleaned_path = DATASETS_DIR / "fra_cleaned.csv"
        if fra_cleaned_path.exists():
            matches = []
            with open(fra_cleaned_path, encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name_raw = (row.get("name") or row.get("Name") or "").strip()
                    brand_raw = (row.get("brand") or row.get("Brand") or "").strip()
                    if "sauvage" in name_raw.lower() and "dior" in brand_raw.lower():
                        matches.append(row)
            print(f"\nfra_cleaned.csv — {len(matches)} rows matching 'sauvage' + 'dior':")
            for m in matches[:8]:
                name_raw = m.get("name") or m.get("Name", "")
                brand_raw = m.get("brand") or m.get("Brand", "")
                url_raw = m.get("url") or m.get("URL", "")
                print(f"  name='{name_raw}' | brand='{brand_raw}' | normalized_name='{normalize(name_raw)}' | url={url_raw[:60]}")
        else:
            print("fra_cleaned.csv not found")

        # fra_perfumes.csv
        fra_perfumes_path = DATASETS_DIR / "fra_perfumes.csv"
        if fra_perfumes_path.exists():
            matches_fp = []
            with open(fra_perfumes_path, encoding="latin-1", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = (row.get("url") or "").strip()
                    if "sauvage" in url.lower() and "/dior/" in url.lower():
                        matches_fp.append((url, row.get("Rating Value",""), row.get("Main Accords","")))
            print(f"\nfra_perfumes.csv — {len(matches_fp)} rows with Dior+Sauvage URL:")
            for url, rating, accords in matches_fp[:8]:
                # Simulate the extract_brand_name_from_url logic
                path_str = url.rstrip("/")
                if path_str.endswith(".html"):
                    path_str = path_str[:-5]
                parts = path_str.split("/")
                brand_slug = parts[-2] if len(parts) >= 2 else ""
                name_slug = parts[-1] if len(parts) >= 1 else ""
                name_slug_clean = re.sub(r"-\d+$", "", name_slug)
                extracted_name = name_slug_clean.replace("-", " ").title()
                brand_display = brand_slug.replace("-", " ").replace("_", " ").strip()
                print(f"  url={url[:70]}")
                print(f"    -> extracted brand='{brand_display}' | extracted name='{extracted_name}'")
                print(f"    -> normalize(brand)='{normalize(brand_display)}' | normalize(name)='{normalize(extracted_name)}'")
                print(f"    -> rating={rating} | accords={accords[:60]}")
        else:
            print("fra_perfumes.csv not found")

        # ── 3. Why didn't they match? — show normalize(fra_cleaned name) ────────
        print("\n" + "=" * 60)
        print("SECTION 3: Match logic diagnosis")
        print("=" * 60)

        # What name is stored in DB for the Sauvage record
        if rows:
            s = rows[0]
            db_name_norm = normalize(s.name)
            db_brand_norm = normalize(s.brand)
            print(f"\nDB record: name='{s.name}' brand='{s.brand}'")
            print(f"  normalize(name) ='{db_name_norm}'")
            print(f"  normalize(brand)='{db_brand_norm}'")

        # ── 4. Source count distribution in DB ────────────────────────────────
        print("\n" + "=" * 60)
        print("SECTION 4: source_count distribution (all perfumes)")
        print("=" * 60)
        dist_q = await session.execute(
            text("SELECT source_count, COUNT(*) FROM perfumes GROUP BY source_count ORDER BY source_count DESC LIMIT 10")
        )
        print("\n  source_count | count")
        print("  -------------|------")
        for sc, cnt in dist_q:
            print(f"  {sc:>12}   {cnt:>6,}")

        # Also max source_count
        max_q = await session.execute(text("SELECT MAX(source_count), AVG(source_count)::numeric(6,2) FROM perfumes"))
        for mx, avg in max_q:
            print(f"\n  MAX source_count: {mx}   AVG: {avg}")

        # ── 5. Well-known perfumes with source_count >= 2 + real pyramid ──────
        print("\n" + "=" * 60)
        print("SECTION 5: Predictions — high-quality perfumes (source_count≥2, real pyramid)")
        print("=" * 60)

        target_names = [
            ("chanel", "no 5"),
            ("chanel", "no 5"),           # fallback match
            ("yves saint laurent", "black opium"),
            ("creed", "aventus"),
            ("giorgio armani", "acqua di gio"),
            ("dior", "j adore"),
            ("guerlain", "shalimar"),
            ("versace", "eros"),
            ("tom ford", "black orchid"),
            ("viktor rolf", "flowerbomb"),
        ]

        # Query all candidates at once: source_count >= 2, has some notes
        quality_q = select(Perfume).where(
            Perfume.source_count >= 2,
            Perfume.has_inferred_pyramid == False,
        )
        quality_rows = (await session.execute(quality_q)).scalars().all()

        # index by (normalize(brand), normalize(name))
        quality_idx: dict[tuple[str,str], Perfume] = {}
        for p in quality_rows:
            key = (normalize(p.brand), normalize(p.name))
            quality_idx[key] = p

        print(f"\n  Total perfumes with source_count≥2 + real pyramid: {len(quality_rows):,}")

        # Try to find each target
        found: list[Perfume] = []
        for brand_kw, name_kw in target_names:
            if len(found) >= 5:
                break
            # fuzzy search in the result set
            for p in quality_rows:
                if (brand_kw in normalize(p.brand) or normalize(p.brand) in brand_kw) and \
                   (name_kw in normalize(p.name) or normalize(p.name) in name_kw):
                    # avoid duplicates
                    if p not in found:
                        found.append(p)
                        break

        # If we're still short, fill from top-rated
        if len(found) < 5:
            top_rated = sorted(quality_rows, key=lambda p: p.community_overall_rating or 0, reverse=True)
            for p in top_rated:
                if p not in found:
                    found.append(p)
                if len(found) >= 5:
                    break

        print(f"\n  Selected {len(found)} perfumes for prediction:\n")
        for p in found:
            p_dict = _perfume_to_dict(p)
            print_prediction("source_count≥2 | real pyramid", p_dict, p, models)

        # ── 6. One inferred pyramid perfume ───────────────────────────────────
        print("\n\n" + "=" * 60)
        print("SECTION 6: Prediction — inferred pyramid (has_inferred_pyramid=True)")
        print("=" * 60)

        inferred_q = select(Perfume).where(
            Perfume.has_inferred_pyramid == True,
            Perfume.source_count >= 2,
        ).order_by(Perfume.community_overall_rating.desc()).limit(5)
        inferred_rows = (await session.execute(inferred_q)).scalars().all()

        if not inferred_rows:
            # fallback: any inferred pyramid
            inferred_q2 = select(Perfume).where(
                Perfume.has_inferred_pyramid == True,
            ).order_by(Perfume.community_overall_rating.desc()).limit(5)
            inferred_rows = (await session.execute(inferred_q2)).scalars().all()

        if inferred_rows:
            p = inferred_rows[0]
            p_dict = _perfume_to_dict(p)
            print_prediction("inferred pyramid", p_dict, p, models)
            print(f"\n  (For comparison: this perfume has source_count={p.source_count}, "
                  f"has_inferred_pyramid=True)")
        else:
            print("  No inferred pyramid perfumes found.")

        # ── 7. Fix suggestion for Sauvage ─────────────────────────────────────
        print("\n\n" + "=" * 60)
        print("SECTION 7: Should we manual-patch Dior Sauvage source_count?")
        print("=" * 60)
        if rows:
            s = rows[0]
            print(f"\n  Current state: source_count={s.source_count}, has_inferred_pyramid={s.has_inferred_pyramid}")
            print(f"  fra_perfumes.csv DID contain a Sauvage entry (shown above in Section 2).")
            print(f"  The mismatch is likely a name normalization issue:")
            print(f"    fra_cleaned stored name: '{s.name}'  → normalize='{normalize(s.name)}'")
            print(f"    fra_perfumes extracts:   'Sauvage'   → normalize='sauvage'")
            if normalize(s.name) != "sauvage":
                print(f"\n  *** MISMATCH CONFIRMED: '{normalize(s.name)}' != 'sauvage'")
                print(f"      This is why fra_perfumes failed to match and didn't bump source_count.")
            else:
                print(f"\n  Names normalize identically — check accords/rating fill logic for clues.")

    print(f"\n{'='*60}\nDone.\n")


if __name__ == "__main__":
    asyncio.run(main())
