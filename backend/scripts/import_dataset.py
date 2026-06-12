"""
Multi-source perfume dataset importer.

Sources (in priority order):
  1. fra_cleaned.csv       — primary, 24k rows (note pyramids, semicolon-delimited, latin-1)
  2. fra_perfumes.csv      — secondary, 70k rows (fills accords/ratings, comma-delimited, latin-1)
  3. Perfumes_dataset.csv  — tertiary, 1k rows (adds longevity labels)

FragDB reference files:
  notes.csv    → expands notes_chemistry.json
  accords.csv  → creates accords_popularity.json

Run from backend/ directory:
  python scripts/import_dataset.py
"""

import sys
import os
import re
import csv
import json
import ast
import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from project root (one level above backend/)
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from sqlalchemy import text, select
from models.database import engine, AsyncSessionLocal, init_db
from models.perfume import Perfume

try:
    from rapidfuzz import fuzz, process as rfprocess
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATCH_SIZE = 500
FUZZY_THRESHOLD = 90.0

DATA_DIR = Path(__file__).parent.parent / "data"
DATASETS_DIR = DATA_DIR / "datasets"
NOTES_CHEM_PATH = DATA_DIR / "notes_chemistry.json"
ACCORDS_POP_PATH = DATA_DIR / "accords_popularity.json"

GROUP_TO_FAMILY = {
    "Citrus smells": "citrus",
    "Flowers": "floral",
    "White flowers": "floral",
    "Fruits, vegetables and nuts": "fresh",
    "Greens, herbs and fougeres": "green",
    "Musk, amber, animalic smells": "musky",
    "Natural and synthetic, popular and weird": "fresh",
    "Resins and balsams": "resinous",
    "Spices": "spicy",
    "Sweets and gourmand smells": "gourmand",
    "Woods and mosses": "woody",
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


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def slug_to_name(slug: str) -> str:
    """Convert URL slug to display name: 'accento-overdose-74630' → 'Accento Overdose'."""
    slug = re.sub(r"-\d+$", "", slug)
    return slug.replace("-", " ").title()


def parse_notes(s: str) -> list[str]:
    if not s or not s.strip():
        return []
    return [n.strip() for n in s.split(",") if n.strip()]


def parse_rating(s: str) -> Optional[float]:
    if not s or not s.strip():
        return None
    s = s.replace(",", ".").strip()
    try:
        v = float(s)
        return v if 0.0 <= v <= 5.0 else None
    except ValueError:
        return None


def parse_count(s: str) -> Optional[int]:
    if not s or not s.strip():
        return None
    try:
        return max(0, int(s.replace(",", "").strip()))
    except ValueError:
        return None


def map_gender(s: str) -> str:
    s = s.lower().strip()
    if s in ("men", "for men", "masculine", "male"):
        return "masculine"
    if s in ("women", "for women", "feminine", "female"):
        return "feminine"
    return "unisex"


def clean_longevity(s: str) -> str:
    s = re.sub(r"\s*:contentReference.*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s*\[.*?\]", "", s).strip()
    return s


def parse_accords_field(s: str) -> list[str]:
    if not s or not s.strip():
        return []
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list):
            return [str(x).strip() for x in result if x]
    except Exception:
        pass
    return [x.strip() for x in s.split(",") if x.strip()]


def extract_brand_name_from_url(url: str) -> tuple[str, str]:
    """
    Extract brand and perfume name from a Fragrantica URL.
    e.g. 'https://www.fragrantica.com/perfume/Dior/Sauvage-12345.html'
      → ('Dior', 'Sauvage')
    """
    try:
        path = url.rstrip("/")
        if path.endswith(".html"):
            path = path[:-5]
        parts = path.split("/")
        # parts[-2] = brand slug, parts[-1] = name slug with trailing ID
        brand_slug = parts[-2] if len(parts) >= 2 else ""
        name_slug = parts[-1] if len(parts) >= 1 else ""
        brand = brand_slug.replace("-", " ").replace("_", " ").strip()
        name = slug_to_name(name_slug)
        return brand, name
    except Exception:
        return "", ""


def weighted_rating_avg(
    existing_rating: float,
    existing_count: int,
    new_rating: float,
    new_count: int,
) -> float:
    total = existing_count + new_count
    if total == 0:
        return existing_rating
    return (existing_rating * existing_count + new_rating * new_count) / total


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def fuzzy_find(brand_norm: str, name_norm: str, by_brand: dict) -> Optional[int]:
    """Return perfume_id if a match is found above FUZZY_THRESHOLD, else None."""
    candidates = by_brand.get(brand_norm)
    if not candidates:
        return None
    if name_norm in candidates:
        return candidates[name_norm]

    if HAS_RAPIDFUZZ:
        result = rfprocess.extractOne(
            name_norm,
            list(candidates.keys()),
            scorer=fuzz.token_sort_ratio,
        )
        if result and result[1] >= FUZZY_THRESHOLD:
            return candidates[result[0]]
    else:
        matches = difflib.get_close_matches(name_norm, candidates.keys(), n=1, cutoff=FUZZY_THRESHOLD / 100.0)
        if matches:
            return candidates[matches[0]]
    return None


# ---------------------------------------------------------------------------
# DB migration
# ---------------------------------------------------------------------------

async def run_migration() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE perfumes ADD COLUMN IF NOT EXISTS source_count INTEGER DEFAULT 1"
        ))
        await conn.execute(text(
            "ALTER TABLE perfumes ADD COLUMN IF NOT EXISTS community_longevity_label VARCHAR(50)"
        ))
    print("Migration complete: source_count, community_longevity_label verified.")


# ---------------------------------------------------------------------------
# Notes chemistry expansion
# ---------------------------------------------------------------------------

def expand_notes_chemistry() -> int:
    with open(NOTES_CHEM_PATH) as f:
        existing = json.load(f)

    existing_names_lower = {n["name"].lower() for n in existing}
    notes_path = DATASETS_DIR / "notes.csv"

    added = 0
    try:
        with open(notes_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                name = row.get("name", "").strip()
                group = row.get("group", "").strip()
                if not name:
                    continue
                if name.lower() in existing_names_lower:
                    continue

                family = GROUP_TO_FAMILY.get(group, "fresh")
                defaults = FAMILY_DEFAULTS.get(family, FAMILY_DEFAULTS["fresh"]).copy()
                entry = {"name": name, "family": family, **defaults}
                existing.append(entry)
                existing_names_lower.add(name.lower())
                added += 1
    except FileNotFoundError:
        print(f"  WARNING: notes.csv not found at {notes_path}")
        return 0

    with open(NOTES_CHEM_PATH, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"  notes_chemistry.json: {len(existing)} total ({added} added from notes.csv)")
    return added


# ---------------------------------------------------------------------------
# Accords popularity
# ---------------------------------------------------------------------------

def build_accords_popularity() -> int:
    accords_path = DATASETS_DIR / "accords.csv"
    popularity: dict[str, int] = {}

    try:
        with open(accords_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                name = row.get("name", "").strip()
                count = row.get("fragrance_count", "0").strip()
                if name:
                    try:
                        popularity[name] = int(count)
                    except ValueError:
                        popularity[name] = 0
    except FileNotFoundError:
        print(f"  WARNING: accords.csv not found at {accords_path}")
        return 0

    with open(ACCORDS_POP_PATH, "w") as f:
        json.dump(popularity, f, indent=2, sort_keys=True)

    print(f"  accords_popularity.json: {len(popularity)} accords written.")
    return len(popularity)


# ---------------------------------------------------------------------------
# Load existing perfumes into lookup
# ---------------------------------------------------------------------------

async def load_existing_lookup(session) -> dict:
    result = await session.execute(select(Perfume.id, Perfume.brand, Perfume.name))
    by_brand: dict[str, dict[str, int]] = defaultdict(dict)
    for pid, brand, name in result:
        by_brand[normalize(brand)][normalize(name)] = pid
    return by_brand


# ---------------------------------------------------------------------------
# Primary import: fra_cleaned.csv
# ---------------------------------------------------------------------------

async def import_fra_cleaned(session, by_brand: dict) -> dict:
    path = DATASETS_DIR / "fra_cleaned.csv"
    stats = {"added": 0, "skipped_dup": 0, "errors": 0, "total_rows": 0}
    batch: list[Perfume] = []

    try:
        f = open(path, encoding="latin-1", newline="")
    except FileNotFoundError:
        print(f"  ERROR: fra_cleaned.csv not found at {path}")
        return stats

    try:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            stats["total_rows"] += 1
            try:
                # Extract brand and name
                brand_raw = (row.get("Brand") or "").strip()
                slug = (row.get("Perfume") or "").strip()
                if not brand_raw or not slug:
                    stats["errors"] += 1
                    continue

                name = slug_to_name(slug)
                brand_norm = normalize(brand_raw)
                name_norm = normalize(name)

                # Deduplicate
                if fuzzy_find(brand_norm, name_norm, by_brand) is not None:
                    stats["skipped_dup"] += 1
                    continue

                # Parse notes
                top_notes = parse_notes(row.get("Top") or "")
                middle_notes = parse_notes(row.get("Middle") or "")
                base_notes = parse_notes(row.get("Base") or "")

                # Parse accords
                accord_fields = ["mainaccord1", "mainaccord2", "mainaccord3", "mainaccord4", "mainaccord5"]
                accords = [row.get(a, "").strip() for a in accord_fields if row.get(a, "").strip()]

                # Ratings
                rating = parse_rating(row.get("Rating Value") or "")
                rating_count = parse_count(row.get("Rating Count") or "")

                # Gender
                gender = map_gender(row.get("Gender") or "")

                # Build title-case brand
                brand_display = brand_raw.replace("-", " ").title()

                p = Perfume(
                    name=name,
                    brand=brand_display,
                    concentration="EDT",
                    fragrantica_url=row.get("url") or None,
                    top_notes=top_notes,
                    middle_notes=middle_notes,
                    base_notes=base_notes,
                    accords=accords,
                    gender_vote=gender,
                    community_overall_rating=rating or 3.0,
                    source_count=1,
                )
                batch.append(p)
                by_brand[brand_norm][name_norm] = -1  # placeholder until flush
                stats["added"] += 1

                # Progress every 1000
                if stats["total_rows"] % 1000 == 0:
                    pct = stats["total_rows"]
                    print(f"  Imported {pct}/24063 fra_cleaned rows — added {stats['added']}, dupes {stats['skipped_dup']} ...")

                # Batch commit
                if len(batch) >= BATCH_SIZE:
                    session.add_all(batch)
                    await session.flush()
                    # Update lookup with real IDs
                    for p_obj in batch:
                        by_brand[normalize(p_obj.brand)][normalize(p_obj.name)] = p_obj.id
                    await session.commit()
                    batch = []

            except Exception as e:
                stats["errors"] += 1
                logger.warning("fra_cleaned row %d error: %s", stats["total_rows"], e)
    finally:
        f.close()

    # Final batch
    if batch:
        session.add_all(batch)
        await session.flush()
        for p_obj in batch:
            by_brand[normalize(p_obj.brand)][normalize(p_obj.name)] = p_obj.id
        await session.commit()

    print(f"  fra_cleaned: {stats['added']} added, {stats['skipped_dup']} dupes, {stats['errors']} errors (of {stats['total_rows']} rows)")
    return stats


# ---------------------------------------------------------------------------
# Secondary import: fra_perfumes.csv
# ---------------------------------------------------------------------------

async def import_fra_perfumes(session, by_brand: dict) -> dict:
    path = DATASETS_DIR / "fra_perfumes.csv"
    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0, "total_rows": 0}
    batch_new: list[Perfume] = []
    batch_updates: list[dict] = []  # {id, accords, rating, rating_count}

    try:
        f = open(path, encoding="latin-1", newline="")
    except FileNotFoundError:
        print(f"  ERROR: fra_perfumes.csv not found at {path}")
        return stats

    try:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_rows"] += 1
            try:
                url = (row.get("url") or "").strip()
                if not url:
                    stats["skipped"] += 1
                    continue

                brand_display, name = extract_brand_name_from_url(url)
                if not brand_display or not name:
                    stats["skipped"] += 1
                    continue

                brand_norm = normalize(brand_display)
                name_norm = normalize(name)

                # Ratings
                rating = parse_rating(row.get("Rating Value") or "")
                rating_count = parse_count(row.get("Rating Count") or "") or 0

                # Accords
                accords = parse_accords_field(row.get("Main Accords") or "")

                # Gender
                gender = map_gender(row.get("Gender") or "")

                # Try to match existing
                existing_id = fuzzy_find(brand_norm, name_norm, by_brand)

                if existing_id is not None:
                    # Update existing: fill missing accords, weighted-average rating
                    if existing_id > 0 and (accords or rating is not None):
                        batch_updates.append({
                            "id": existing_id,
                            "accords": accords,
                            "rating": rating,
                            "rating_count": rating_count,
                        })
                        stats["updated"] += 1
                else:
                    # New perfume — add even without note pyramid
                    p = Perfume(
                        name=name,
                        brand=brand_display,
                        concentration="EDT",
                        fragrantica_url=url,
                        top_notes=[],
                        middle_notes=[],
                        base_notes=[],
                        accords=accords,
                        gender_vote=gender,
                        community_overall_rating=rating or 3.0,
                        source_count=1,
                    )
                    batch_new.append(p)
                    by_brand[brand_norm][name_norm] = -1
                    stats["added"] += 1

                # Progress
                if stats["total_rows"] % 1000 == 0:
                    print(f"  Imported {stats['total_rows']}/70103 fra_perfumes rows — added {stats['added']}, updated {stats['updated']} ...")

                # Flush new records batch
                if len(batch_new) >= BATCH_SIZE:
                    session.add_all(batch_new)
                    await session.flush()
                    for p_obj in batch_new:
                        by_brand[normalize(p_obj.brand)][normalize(p_obj.name)] = p_obj.id
                    await session.commit()
                    batch_new = []

                # Flush updates batch
                if len(batch_updates) >= BATCH_SIZE:
                    await _apply_secondary_updates(session, batch_updates)
                    batch_updates = []

            except Exception as e:
                stats["errors"] += 1
                logger.warning("fra_perfumes row %d error: %s", stats["total_rows"], e)
    finally:
        f.close()

    # Final batches
    if batch_new:
        session.add_all(batch_new)
        await session.flush()
        for p_obj in batch_new:
            by_brand[normalize(p_obj.brand)][normalize(p_obj.name)] = p_obj.id
        await session.commit()

    if batch_updates:
        await _apply_secondary_updates(session, batch_updates)

    print(f"  fra_perfumes: {stats['added']} added, {stats['updated']} updated, {stats['skipped']} skipped, {stats['errors']} errors (of {stats['total_rows']} rows)")
    return stats


async def _apply_secondary_updates(session, updates: list[dict]) -> None:
    """Apply weighted rating merges and accord fills for fra_perfumes updates."""
    ids = [u["id"] for u in updates]
    result = await session.execute(
        select(Perfume).where(Perfume.id.in_(ids))
    )
    perfume_map = {p.id: p for p in result.scalars()}

    for u in updates:
        p = perfume_map.get(u["id"])
        if p is None:
            continue

        # Fill missing accords
        if u["accords"] and not p.accords:
            p.accords = u["accords"]

        # Weighted-average rating
        if u["rating"] is not None and u["rating_count"] > 0:
            existing_count = int(p.community_overall_rating * 10)  # rough weight
            p.community_overall_rating = weighted_rating_avg(
                p.community_overall_rating, existing_count,
                u["rating"], u["rating_count"],
            )

        # Increment source_count
        current = p.source_count if p.source_count is not None else 1
        p.source_count = current + 1

    await session.commit()


# ---------------------------------------------------------------------------
# Tertiary import: Perfumes_dataset.csv
# ---------------------------------------------------------------------------

async def import_perfumes_dataset(session, by_brand: dict) -> dict:
    path = DATASETS_DIR / "Perfumes_dataset.csv"
    stats = {"matched": 0, "unmatched": 0, "errors": 0, "total_rows": 0}

    # Collect all updates to apply in batches
    pending: list[tuple[int, str]] = []  # (perfume_id, longevity_label)

    try:
        f = open(path, encoding="utf-8", errors="replace", newline="")
    except FileNotFoundError:
        print(f"  ERROR: Perfumes_dataset.csv not found at {path}")
        return stats

    try:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_rows"] += 1
            try:
                brand_raw = (row.get("brand") or "").strip()
                name_raw = (row.get("perfume") or "").strip()
                longevity_raw = (row.get("longevity") or "").strip()

                if not brand_raw or not name_raw or not longevity_raw:
                    stats["unmatched"] += 1
                    continue

                longevity = clean_longevity(longevity_raw)
                if not longevity or longevity == "Longevity":
                    stats["unmatched"] += 1
                    continue

                brand_norm = normalize(brand_raw)
                name_norm = normalize(name_raw)

                # Strip concentration suffix from name if present (e.g., "Sauvage EDT" → "Sauvage")
                name_norm_clean = re.sub(r"\b(edt|edp|edc|parfum|extrait)\b", "", name_norm).strip()

                existing_id = fuzzy_find(brand_norm, name_norm_clean, by_brand)
                if existing_id is None:
                    existing_id = fuzzy_find(brand_norm, name_norm, by_brand)

                if existing_id is not None and existing_id > 0:
                    pending.append((existing_id, longevity))
                    stats["matched"] += 1
                else:
                    stats["unmatched"] += 1

                if stats["total_rows"] % 1000 == 0:
                    print(f"  Processed {stats['total_rows']}/1004 Perfumes_dataset rows ...")

                # Batch apply
                if len(pending) >= BATCH_SIZE:
                    await _apply_longevity_labels(session, pending)
                    pending = []

            except Exception as e:
                stats["errors"] += 1
                logger.warning("Perfumes_dataset row %d error: %s", stats["total_rows"], e)
    finally:
        f.close()

    if pending:
        await _apply_longevity_labels(session, pending)

    print(f"  Perfumes_dataset: {stats['matched']} matched, {stats['unmatched']} unmatched, {stats['errors']} errors (of {stats['total_rows']} rows)")
    return stats


async def _apply_longevity_labels(session, pending: list[tuple[int, str]]) -> None:
    ids = [pid for pid, _ in pending]
    result = await session.execute(select(Perfume).where(Perfume.id.in_(ids)))
    perfume_map = {p.id: p for p in result.scalars()}

    label_map = {pid: label for pid, label in pending}
    for pid, p in perfume_map.items():
        label = label_map.get(pid)
        if label:
            p.community_longevity_label = label
            current = p.source_count if p.source_count is not None else 1
            p.source_count = current + 1

    await session.commit()


# ---------------------------------------------------------------------------
# Final DB count
# ---------------------------------------------------------------------------

async def count_perfumes(session) -> int:
    result = await session.execute(text("SELECT COUNT(*) FROM perfumes"))
    return result.scalar()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 60)
    print("ScentScience Multi-Source Dataset Importer")
    print("=" * 60)

    print("\n[1/6] Initializing database schema...")
    await init_db()

    print("\n[2/6] Running column migration...")
    await run_migration()

    print("\n[3/6] Expanding notes_chemistry.json from notes.csv...")
    notes_added = expand_notes_chemistry()

    print("\n[4/6] Building accords_popularity.json from accords.csv...")
    accords_count = build_accords_popularity()

    async with AsyncSessionLocal() as session:
        existing_before = await count_perfumes(session)
        print(f"\n[5/6] Starting imports (existing: {existing_before} perfumes)")

        print("\n--- Primary: fra_cleaned.csv ---")
        by_brand = await load_existing_lookup(session)
        stats1 = await import_fra_cleaned(session, by_brand)

        print("\n--- Secondary: fra_perfumes.csv ---")
        stats2 = await import_fra_perfumes(session, by_brand)

        print("\n--- Tertiary: Perfumes_dataset.csv ---")
        stats3 = await import_perfumes_dataset(session, by_brand)

        total_after = await count_perfumes(session)

    # Print summary
    with open(NOTES_CHEM_PATH) as f:
        notes_total = len(json.load(f))

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE — Summary")
    print("=" * 60)
    print(f"  Total perfumes in DB:        {total_after}")
    print(f"  Previously in DB:            {existing_before}")
    print(f"  Added from fra_cleaned:      {stats1['added']}")
    print(f"  Added from fra_perfumes:     {stats2['added']}")
    print(f"  Updated from fra_perfumes:   {stats2['updated']}")
    print(f"  Longevity labels added:      {stats3['matched']}")
    print(f"  Notes in notes_chemistry:    {notes_total} ({notes_added} new)")
    print(f"  Accords popularity entries:  {accords_count}")
    print(f"  Errors: fra_cleaned={stats1['errors']}, fra_perfumes={stats2['errors']}, dataset={stats3['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
