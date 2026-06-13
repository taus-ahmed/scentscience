"""
Targeted rating_count backfill.

Reads fra_perfumes.csv and fra_cleaned.csv, builds a per-perfume lookup of
(max_rating_count, rating_value), then UPDATEs all DB records where
rating_count = 0 or NULL.  Never inserts new rows.

Run from backend/:
  python scripts/update_ratings.py
"""

import sys
import os
import re
import csv
import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from sqlalchemy import select, text
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume

try:
    from rapidfuzz import fuzz, process as rfprocess
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500
FUZZY_THRESHOLD = 90.0
DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"


# ---------------------------------------------------------------------------
# String helpers (same as import_dataset.py)
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def slug_to_name(slug: str) -> str:
    slug = re.sub(r"-\d+$", "", slug)
    return slug.replace("-", " ").title()


def parse_rating(s: str) -> Optional[float]:
    if not s or not s.strip():
        return None
    s = s.replace(",", ".").strip()
    try:
        v = float(s)
        return v if 0.0 <= v <= 5.0 else None
    except ValueError:
        return None


def parse_count(s: str) -> int:
    if not s or not s.strip():
        return 0
    try:
        return max(0, int(s.replace(",", "").strip()))
    except ValueError:
        return 0


def extract_brand_name_from_url(url: str) -> tuple[str, str]:
    try:
        path = url.rstrip("/")
        if path.endswith(".html"):
            path = path[:-5]
        parts = path.split("/")
        brand_slug = parts[-2] if len(parts) >= 2 else ""
        name_slug = parts[-1] if len(parts) >= 1 else ""
        brand = brand_slug.replace("-", " ").replace("_", " ").strip()
        name = slug_to_name(name_slug)
        return brand, name
    except Exception:
        return "", ""


# ---------------------------------------------------------------------------
# Build CSV lookup: (brand_norm, name_norm) -> {"count": int, "rating": float}
# Takes the max rating_count across both CSVs for the same perfume.
# ---------------------------------------------------------------------------

def build_csv_lookup() -> dict[tuple[str, str], dict]:
    lookup: dict[tuple[str, str], dict] = {}

    # --- fra_cleaned.csv (semicolon delimited) ---
    path1 = DATASETS_DIR / "fra_cleaned.csv"
    fra_cleaned_rows = 0
    fra_cleaned_with_count = 0
    try:
        with open(path1, encoding="latin-1", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                fra_cleaned_rows += 1
                brand_raw = (row.get("Brand") or "").strip()
                slug = (row.get("Perfume") or "").strip()
                if not brand_raw or not slug:
                    continue
                name = slug_to_name(slug)
                key = (normalize(brand_raw), normalize(name))
                count = parse_count(row.get("Rating Count") or "")
                rating = parse_rating(row.get("Rating Value") or "")
                if count > 0:
                    fra_cleaned_with_count += 1
                    existing = lookup.get(key)
                    if existing is None or count > existing["count"]:
                        lookup[key] = {"count": count, "rating": rating or 3.0}
    except FileNotFoundError:
        print(f"  WARNING: fra_cleaned.csv not found at {path1}")

    print(f"  fra_cleaned.csv:  {fra_cleaned_rows} rows, {fra_cleaned_with_count} with rating_count>0")

    # --- fra_perfumes.csv (comma delimited, URL-based) ---
    path2 = DATASETS_DIR / "fra_perfumes.csv"
    fra_perfumes_rows = 0
    fra_perfumes_with_count = 0
    try:
        with open(path2, encoding="latin-1", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fra_perfumes_rows += 1
                url = (row.get("url") or "").strip()
                if not url:
                    continue
                brand_display, name = extract_brand_name_from_url(url)
                if not brand_display or not name:
                    continue
                key = (normalize(brand_display), normalize(name))
                count = parse_count(row.get("Rating Count") or "")
                rating = parse_rating(row.get("Rating Value") or "")
                if count > 0:
                    fra_perfumes_with_count += 1
                    existing = lookup.get(key)
                    if existing is None or count > existing["count"]:
                        lookup[key] = {"count": count, "rating": rating or 3.0}
    except FileNotFoundError:
        print(f"  WARNING: fra_perfumes.csv not found at {path2}")

    print(f"  fra_perfumes.csv: {fra_perfumes_rows} rows, {fra_perfumes_with_count} with rating_count>0")
    print(f"  Combined unique keys in CSV lookup: {len(lookup)}")
    return lookup


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def fuzzy_find(brand_norm: str, name_norm: str, by_brand: dict) -> Optional[tuple[str, str]]:
    """Return (brand_norm, name_norm) key from csv_lookup if found above threshold."""
    candidates = by_brand.get(brand_norm)
    if not candidates:
        return None
    if name_norm in candidates:
        return (brand_norm, name_norm)

    if HAS_RAPIDFUZZ:
        result = rfprocess.extractOne(
            name_norm,
            list(candidates),
            scorer=fuzz.token_sort_ratio,
        )
        if result and result[1] >= FUZZY_THRESHOLD:
            return (brand_norm, result[0])
    else:
        matches = difflib.get_close_matches(name_norm, candidates, n=1, cutoff=FUZZY_THRESHOLD / 100.0)
        if matches:
            return (brand_norm, matches[0])
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 60)
    print("ScentScience — Rating Count Backfill")
    print("=" * 60)

    print("\n[1/4] Building CSV lookup from both sources...")
    csv_lookup = build_csv_lookup()

    # Build brand-indexed lookup for fuzzy matching
    csv_by_brand: dict[str, set[str]] = defaultdict(set)
    for (b, n) in csv_lookup:
        csv_by_brand[b].add(n)

    await init_db()

    async with AsyncSessionLocal() as session:
        print("\n[2/4] Loading DB records with rating_count = 0 or NULL...")
        result = await session.execute(
            select(Perfume.id, Perfume.brand, Perfume.name, Perfume.rating_count)
            .where(
                (Perfume.rating_count == 0) | (Perfume.rating_count.is_(None))
            )
        )
        zero_rating_rows = result.all()
        print(f"  Records with rating_count=0/NULL: {len(zero_rating_rows)}")

        # Check Sauvage before update
        sav_result = await session.execute(
            select(Perfume).where(
                Perfume.brand.ilike("%dior%"),
                Perfume.name.ilike("%sauvage%"),
            ).order_by(Perfume.source_count.desc()).limit(3)
        )
        sav_rows = sav_result.scalars().all()
        print(f"\n  Dior Sauvage records before update:")
        for s in sav_rows:
            print(f"    id={s.id}  name={s.name!r}  rating_count={s.rating_count}  source_count={s.source_count}")

        print("\n[3/4] Matching and updating...")
        matched = 0
        unmatched = 0
        skipped_already_set = 0
        batch_ids: list[int] = []
        batch_updates: list[dict] = []

        for pid, brand, name, current_count in zero_rating_rows:
            brand_norm = normalize(brand)
            name_norm = normalize(name)

            csv_key = fuzzy_find(brand_norm, name_norm, csv_by_brand)
            if csv_key is not None:
                data = csv_lookup[csv_key]
                if data["count"] > 0:
                    batch_updates.append({
                        "id": pid,
                        "rating_count": data["count"],
                        "rating_value": data["rating"],
                    })
                    matched += 1
                else:
                    unmatched += 1
            else:
                unmatched += 1

            # Flush batch
            if len(batch_updates) >= BATCH_SIZE:
                await _flush_batch(session, batch_updates)
                print(f"    Flushed batch — matched so far: {matched}")
                batch_updates = []

        # Final batch
        if batch_updates:
            await _flush_batch(session, batch_updates)

        print(f"\n  Matched and updated: {matched}")
        print(f"  No CSV data found:   {unmatched}")

        # Check Sauvage after update
        await session.refresh(sav_rows[0]) if sav_rows else None
        print(f"\n[4/4] Dior Sauvage records after update:")
        sav_result2 = await session.execute(
            select(Perfume).where(
                Perfume.brand.ilike("%dior%"),
                Perfume.name.ilike("%sauvage%"),
            ).order_by(Perfume.source_count.desc()).limit(5)
        )
        for s in sav_result2.scalars().all():
            print(f"    id={s.id}  name={s.name!r}  rating_count={s.rating_count}  source_count={s.source_count}  overall={s.community_overall_rating:.2f}")

        # Overall stats
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM perfumes WHERE rating_count > 0")
        )
        total_with_ratings = count_result.scalar()
        count_result2 = await session.execute(
            text("SELECT COUNT(*) FROM perfumes WHERE rating_count > 1000")
        )
        total_1k = count_result2.scalar()
        print(f"\n  Records with rating_count > 0:    {total_with_ratings}")
        print(f"  Records with rating_count > 1000: {total_1k}")

    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)


async def _flush_batch(session, updates: list[dict]) -> None:
    if not updates:
        return
    ids = [u["id"] for u in updates]
    result = await session.execute(
        select(Perfume).where(Perfume.id.in_(ids))
    )
    perfume_map = {p.id: p for p in result.scalars()}
    for u in updates:
        p = perfume_map.get(u["id"])
        if p is None:
            continue
        p.rating_count = u["rating_count"]
        if u["rating_value"] and u["rating_value"] > 0:
            p.community_overall_rating = u["rating_value"]
    await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
