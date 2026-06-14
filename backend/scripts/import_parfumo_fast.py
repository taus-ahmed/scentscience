"""
Parfumo dataset importer (59,325 rows).

Source: backend/data/datasets/02_Parfumo_Perfumes.csv
Run from backend/ directory:
  python scripts/import_parfumo_fast.py
  python scripts/import_parfumo_fast.py --dry-run
  python scripts/import_parfumo_fast.py --csv path/to/other.csv
"""

import sys
import os
import re
import json
import math
import time
import argparse
import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd
import ftfy
from rapidfuzz import fuzz, process as rfprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from sqlalchemy import select, text
from models.database import engine, AsyncSessionLocal, init_db
from models.perfume import Perfume

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATCH_SIZE = 500
FUZZY_THRESHOLD = 90.0
PROGRESS_EVERY = 2000
TOTAL_ROWS = 59325

DATA_DIR = Path(__file__).parent.parent / "data"
NOTES_CHEM_PATH = DATA_DIR / "notes_chemistry.json"

CONC_MAP = {
    "eau de toilette": "EDT",
    "edt": "EDT",
    "eau de parfum": "EDP",
    "edp": "EDP",
    "parfum": "Parfum",
    "perfume": "Parfum",
    "extrait de parfum": "Extrait",
    "extrait": "Extrait",
    "eau de cologne": "EDC",
    "cologne": "EDC",
    "edc": "EDC",
}

FAMILY_DEFAULTS = {
    "citrus":    {"volatility": 9, "heat_performance": 4, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 7, "skin_bonding": 3, "dry_skin_boost": 4, "oily_skin_boost": 3, "projection_strength": 7, "longevity_class": 1},
    "floral":    {"volatility": 7, "heat_performance": 5, "cold_performance": 5, "humidity_performance": 6, "dry_performance": 5, "skin_bonding": 5, "dry_skin_boost": 5, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 2},
    "woody":     {"volatility": 4, "heat_performance": 5, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 7, "skin_bonding": 7, "dry_skin_boost": 7, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 4},
    "oriental":  {"volatility": 3, "heat_performance": 8, "cold_performance": 5, "humidity_performance": 4, "dry_performance": 7, "skin_bonding": 8, "dry_skin_boost": 7, "oily_skin_boost": 6, "projection_strength": 7, "longevity_class": 5},
    "fresh":     {"volatility": 8, "heat_performance": 4, "cold_performance": 7, "humidity_performance": 7, "dry_performance": 6, "skin_bonding": 4, "dry_skin_boost": 4, "oily_skin_boost": 4, "projection_strength": 6, "longevity_class": 2},
    "gourmand":  {"volatility": 5, "heat_performance": 6, "cold_performance": 5, "humidity_performance": 4, "dry_performance": 5, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 3},
    "green":     {"volatility": 7, "heat_performance": 4, "cold_performance": 6, "humidity_performance": 6, "dry_performance": 5, "skin_bonding": 4, "dry_skin_boost": 5, "oily_skin_boost": 4, "projection_strength": 6, "longevity_class": 2},
    "fougere":   {"volatility": 6, "heat_performance": 5, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 6, "skin_bonding": 5, "dry_skin_boost": 5, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 3},
    "resinous":  {"volatility": 3, "heat_performance": 7, "cold_performance": 5, "humidity_performance": 4, "dry_performance": 7, "skin_bonding": 8, "dry_skin_boost": 8, "oily_skin_boost": 6, "projection_strength": 7, "longevity_class": 5},
    "spicy":     {"volatility": 5, "heat_performance": 7, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 6, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 7, "longevity_class": 3},
    "musky":     {"volatility": 4, "heat_performance": 5, "cold_performance": 5, "humidity_performance": 5, "dry_performance": 5, "skin_bonding": 7, "dry_skin_boost": 6, "oily_skin_boost": 7, "projection_strength": 5, "longevity_class": 4},
    "earthy":    {"volatility": 4, "heat_performance": 5, "cold_performance": 6, "humidity_performance": 7, "dry_performance": 5, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 5, "longevity_class": 4},
    "aquatic":   {"volatility": 8, "heat_performance": 5, "cold_performance": 5, "humidity_performance": 7, "dry_performance": 5, "skin_bonding": 4, "dry_skin_boost": 4, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 2},
    "chypre":    {"volatility": 5, "heat_performance": 5, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 6, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 3},
    "powdery":   {"volatility": 5, "heat_performance": 5, "cold_performance": 5, "humidity_performance": 5, "dry_performance": 5, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 5, "longevity_class": 3},
    "smoky":     {"volatility": 4, "heat_performance": 6, "cold_performance": 5, "humidity_performance": 4, "dry_performance": 7, "skin_bonding": 7, "dry_skin_boost": 6, "oily_skin_boost": 6, "projection_strength": 7, "longevity_class": 4},
    "animalic":  {"volatility": 3, "heat_performance": 6, "cold_performance": 5, "humidity_performance": 5, "dry_performance": 6, "skin_bonding": 8, "dry_skin_boost": 7, "oily_skin_boost": 7, "projection_strength": 6, "longevity_class": 5},
}

# Guess note family from its name for new chemistry entries
NOTE_FAMILY_KEYWORDS = {
    "citrus": ["lemon", "bergamot", "grapefruit", "orange", "lime", "mandarin", "tangerine", "yuzu", "citrus", "cedrat"],
    "floral": ["rose", "jasmine", "lily", "violet", "iris", "peony", "magnolia", "neroli", "tuberose", "floral", "flower", "blossom", "geranium", "ylang", "osmanthus", "freesia", "orchid"],
    "woody": ["cedar", "sandalwood", "vetiver", "patchouli", "guaiac", "oud", "agarwood", "wood", "mahogany", "birch", "oak", "ebony", "teak", "bamboo"],
    "oriental": ["amber", "vanilla", "benzyl", "incense", "frankincense", "myrrh", "resin", "labdanum", "opoponax", "tonka", "balsam"],
    "fresh": ["aquatic", "marine", "sea", "water", "rain", "ozone", "cucumber", "green apple", "melon", "mint", "peppermint"],
    "gourmand": ["chocolate", "caramel", "honey", "sugar", "praline", "almond", "coconut", "vanilla", "coffee", "cream", "milk", "marshmallow", "marzipan"],
    "green": ["grass", "leaves", "fern", "moss", "herb", "basil", "sage", "thyme", "rosemary", "green", "galbanum", "oakmoss"],
    "spicy": ["pepper", "cardamom", "cinnamon", "clove", "nutmeg", "ginger", "saffron", "spice", "chili", "cumin", "coriander"],
    "musky": ["musk", "ambrette", "civet", "cashmere", "skin"],
    "resinous": ["frankincense", "benzoin", "styrax", "elemi", "copal", "dammar", "myrrh", "resin"],
    "earthy": ["vetiver", "earth", "soil", "truffle", "mushroom", "patchouli", "leather"],
    "aquatic": ["aquatic", "marine", "sea", "water", "ozonic", "oceanic", "seaweed"],
    "powdery": ["powder", "iris", "violet", "talc", "orris"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def clean_text(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    s = str(val).strip()
    if not s:
        return None
    return ftfy.fix_text(s)


def parse_notes_field(val) -> list[str]:
    s = clean_text(val)
    if not s:
        return []
    parts = [p.strip().title() for p in s.split(",")]
    return [p for p in parts if p]


def map_concentration(val) -> str:
    s = clean_text(val)
    if not s:
        return "EDT"
    return CONC_MAP.get(s.lower(), "EDT")


def infer_note_family(note_lower: str) -> str:
    for family, keywords in NOTE_FAMILY_KEYWORDS.items():
        for kw in keywords:
            if kw in note_lower:
                return family
    return "fresh"


def fuzzy_find(brand_norm: str, name_norm: str, by_brand: dict) -> Optional[int]:
    candidates = by_brand.get(brand_norm)
    if not candidates:
        return None
    if name_norm in candidates:
        return candidates[name_norm]
    result = rfprocess.extractOne(
        name_norm,
        list(candidates.keys()),
        scorer=fuzz.token_sort_ratio,
    )
    if result and result[1] >= FUZZY_THRESHOLD:
        return candidates[result[0]]
    return None


def weighted_avg(existing_rating: float, existing_count: int, new_rating: float, new_count: int) -> float:
    total = existing_count + new_count
    if total == 0:
        return existing_rating
    return (existing_rating * existing_count + new_rating * new_count) / total


# ---------------------------------------------------------------------------
# Validation pass
# ---------------------------------------------------------------------------

def run_validation(df: pd.DataFrame) -> bool:
    print("\n" + "=" * 60)
    print("VALIDATION PASS")
    print("=" * 60)
    print(f"  Total rows:          {len(df)}")
    print(f"  Rows with any notes: {(df['Top_Notes'].notna() | df['Middle_Notes'].notna() | df['Base_Notes'].notna()).sum()}")
    print(f"  Rows with ratings:   {(df['Rating_Count'].fillna(0) > 0).sum()}")
    print(f"  Unique brands:       {df['Brand'].nunique()}")

    rv = df["Rating_Value"].dropna()
    rv_max = rv.max() if len(rv) else 0.0
    rv_min = rv.min() if len(rv) else 0.0
    rv_mean = rv.mean() if len(rv) else 0.0
    print(f"  Rating_Value:        min={rv_min:.2f}, max={rv_max:.2f}, mean={rv_mean:.2f}")

    normalize_rating = rv_max > 5.0
    if normalize_rating:
        print("  Scale: 0-10 detected -> will divide by 2 to normalize to 0-5")
    else:
        print("  Scale: 0-5 -> use as-is")

    print("\n  Top 5 brands:")
    for brand, cnt in df["Brand"].value_counts().head(5).items():
        print(f"    {brand}: {cnt}")

    all_notes: list[str] = []
    for col in ["Top_Notes", "Middle_Notes", "Base_Notes"]:
        for val in df[col].dropna():
            all_notes.extend(parse_notes_field(val))
    from collections import Counter
    note_counts = Counter(all_notes)
    print("\n  Top 10 notes across all pyramids:")
    for note, cnt in note_counts.most_common(10):
        print(f"    {note}: {cnt}")

    print("=" * 60)
    return normalize_rating


# ---------------------------------------------------------------------------
# Notes chemistry expansion
# ---------------------------------------------------------------------------

def expand_notes_chemistry(new_notes: set[str]) -> int:
    with open(NOTES_CHEM_PATH, "r", encoding="utf-8") as f:
        existing: list[dict] = json.load(f)

    existing_lower = {e["name"].lower() for e in existing}
    added = 0
    for note in sorted(new_notes):
        if note.lower() in existing_lower:
            continue
        family = infer_note_family(note.lower())
        defaults = FAMILY_DEFAULTS.get(family, FAMILY_DEFAULTS["fresh"]).copy()
        existing.append({"name": note, "family": family, **defaults})
        existing_lower.add(note.lower())
        added += 1

    if added:
        with open(NOTES_CHEM_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"  notes_chemistry.json: {len(existing)} total (+{added} new from Parfumo)")
    else:
        print(f"  notes_chemistry.json: {len(existing)} total (0 new notes from Parfumo)")
    return added


# ---------------------------------------------------------------------------
# Load existing perfumes
# ---------------------------------------------------------------------------

async def load_existing_lookup(session) -> dict:
    result = await session.execute(select(Perfume.id, Perfume.brand, Perfume.name))
    by_brand: dict[str, dict[str, int]] = defaultdict(dict)
    for pid, brand, name in result:
        by_brand[normalize(brand)][normalize(name)] = pid
    return by_brand


async def count_perfumes(session) -> int:
    result = await session.execute(text("SELECT COUNT(*) FROM perfumes"))
    return result.scalar()


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------

async def import_parfumo(csv_path: Path, dry_run: bool) -> None:
    print("\n" + "=" * 60)
    print("ScentScience — Parfumo Importer")
    print("=" * 60)

    print(f"\n[1/4] Loading CSV: {csv_path}")
    df = pd.read_csv(str(csv_path))
    print(f"  Loaded {len(df)} rows")

    normalize_rating = run_validation(df)

    if dry_run:
        print("\n--dry-run: validation only, no import.")
        return

    print("\n[2/4] Initializing DB...")
    await init_db()

    print("\n[3/4] Loading existing perfume lookup...")
    async with AsyncSessionLocal() as session:
        by_brand = await load_existing_lookup(session)
        existing_before = await count_perfumes(session)
    print(f"  Existing perfumes: {existing_before}")

    print(f"\n[4/4] Importing {len(df)} rows (batch={BATCH_SIZE})...")
    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    all_new_notes: set[str] = set()
    start_time = time.time()

    batch_new: list[Perfume] = []
    batch_updates: list[dict] = []

    async def flush_new(session, batch: list[Perfume]) -> list[Perfume]:
        if not batch:
            return []
        session.add_all(batch)
        await session.flush()
        for p_obj in batch:
            by_brand[normalize(p_obj.brand)][normalize(p_obj.name)] = p_obj.id
        await session.commit()
        return []

    async def flush_updates(session, updates: list[dict]) -> list[dict]:
        if not updates:
            return []
        ids = [u["id"] for u in updates]
        result = await session.execute(select(Perfume).where(Perfume.id.in_(ids)))
        pm = {p.id: p for p in result.scalars()}
        for u in updates:
            p = pm.get(u["id"])
            if p is None:
                continue
            if u["top_notes"] and not p.top_notes:
                p.top_notes = u["top_notes"]
            if u["middle_notes"] and not p.middle_notes:
                p.middle_notes = u["middle_notes"]
            if u["base_notes"] and not p.base_notes:
                p.base_notes = u["base_notes"]
            if u["accords"] and not p.accords:
                p.accords = u["accords"]
            if u["rating"] is not None and u["rating_count"] > 0:
                existing_count = p.rating_count or 0
                existing_rating = p.community_overall_rating or 3.0
                p.community_overall_rating = weighted_avg(
                    existing_rating, existing_count,
                    u["rating"], u["rating_count"],
                )
                p.rating_count = existing_count + u["rating_count"]
            p.source_count = (p.source_count or 1) + 1
        await session.commit()
        return []

    async with AsyncSessionLocal() as session:
        for idx, row in df.iterrows():
            row_num = int(idx) + 1  # type: ignore[arg-type]
            try:
                name_raw = clean_text(row.get("Name"))
                brand_raw = clean_text(row.get("Brand"))
                if not name_raw or not brand_raw:
                    stats["skipped"] += 1
                    continue

                brand_norm = normalize(brand_raw)
                name_norm = normalize(name_raw)

                # Parse fields
                year_val = row.get("Release_Year")
                year: Optional[int] = None
                if pd.notna(year_val):
                    try:
                        year = int(float(year_val))
                    except (ValueError, TypeError):
                        pass

                concentration = map_concentration(row.get("Concentration"))

                rating_count_raw = row.get("Rating_Count")
                rating_count = int(float(rating_count_raw)) if pd.notna(rating_count_raw) and float(rating_count_raw) > 0 else 0

                rating_raw = row.get("Rating_Value")
                rating: Optional[float] = None
                if pd.notna(rating_raw) and rating_count > 0:
                    rv = float(rating_raw)
                    rating = round(rv / 2.0, 3) if normalize_rating else round(rv, 3)
                    rating = max(0.0, min(5.0, rating))

                top_notes = parse_notes_field(row.get("Top_Notes"))
                middle_notes = parse_notes_field(row.get("Middle_Notes"))
                base_notes = parse_notes_field(row.get("Base_Notes"))
                accords = parse_notes_field(row.get("Main_Accords"))

                # Collect new notes for chemistry expansion
                for note in top_notes + middle_notes + base_notes:
                    all_new_notes.add(note)

                number_raw = row.get("Number")
                frag_id: Optional[str] = None
                if pd.notna(number_raw):
                    try:
                        frag_id = f"parfumo_{int(float(number_raw))}"
                    except (ValueError, TypeError):
                        pass

                url_raw = clean_text(row.get("URL"))

                # Dedup
                existing_id = fuzzy_find(brand_norm, name_norm, by_brand)
                if existing_id is not None:
                    has_data = top_notes or middle_notes or base_notes or accords or rating is not None
                    if has_data and existing_id > 0:
                        batch_updates.append({
                            "id": existing_id,
                            "top_notes": top_notes,
                            "middle_notes": middle_notes,
                            "base_notes": base_notes,
                            "accords": accords,
                            "rating": rating,
                            "rating_count": rating_count,
                        })
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    p = Perfume(
                        name=name_raw,
                        brand=brand_raw,
                        concentration=concentration,
                        fragrantica_id=frag_id,
                        fragrantica_url=url_raw,
                        top_notes=top_notes,
                        middle_notes=middle_notes,
                        base_notes=base_notes,
                        accords=accords,
                        community_overall_rating=rating if rating is not None else 3.0,
                        rating_count=rating_count,
                        source_count=1,
                    )
                    batch_new.append(p)
                    by_brand[brand_norm][name_norm] = -1
                    stats["added"] += 1

                # Flush batches
                if len(batch_new) >= BATCH_SIZE:
                    batch_new = await flush_new(session, batch_new)
                if len(batch_updates) >= BATCH_SIZE:
                    batch_updates = await flush_updates(session, batch_updates)

                # Progress
                if row_num % PROGRESS_EVERY == 0:
                    elapsed = time.time() - start_time
                    a, u, s_, e = stats["added"], stats["updated"], stats["skipped"], stats["errors"]
                    print(f"  Processed {row_num}/{TOTAL_ROWS} — added {a}, updated {u}, skipped {s_}, errors {e} ({elapsed:.0f}s)")

            except Exception as ex:
                stats["errors"] += 1
                logger.warning("Row %d error: %s", row_num, ex)

        # Final flush
        batch_new = await flush_new(session, batch_new)
        batch_updates = await flush_updates(session, batch_updates)

        total_after = await count_perfumes(session)

    elapsed_total = time.time() - start_time

    print("\n[Post-import] Expanding notes_chemistry.json...")
    # Load existing note names to find truly new ones
    with open(NOTES_CHEM_PATH, "r", encoding="utf-8") as f:
        existing_nc: list[dict] = json.load(f)
    existing_lower = {e["name"].lower() for e in existing_nc}
    truly_new = {n for n in all_new_notes if n.lower() not in existing_lower}
    notes_added = expand_notes_chemistry(truly_new)

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"  Processed:           {TOTAL_ROWS}")
    print(f"  Added:               {stats['added']}")
    print(f"  Updated:             {stats['updated']}")
    print(f"  Skipped:             {stats['skipped']}")
    print(f"  Errors:              {stats['errors']}")
    print(f"  Perfumes in DB now:  {total_after}  (was {existing_before})")
    print(f"  Notes added:         {notes_added}")
    print(f"  Time taken:          {elapsed_total:.0f}s")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Parfumo dataset importer")
    parser.add_argument(
        "--csv",
        default=str(Path(__file__).parent.parent / "data" / "datasets" / "02_Parfumo_Perfumes.csv"),
        help="Path to Parfumo CSV file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation only, do not import",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        sys.exit(1)

    asyncio.run(import_parfumo(csv_path, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
