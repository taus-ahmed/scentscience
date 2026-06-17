"""
import_ledecanteur.py — Import community vote data from ledecanteur/fragrantica-perfumes

Dataset: E:/scentscience/data/kaggle_new/perfumes.csv  (131,930 rows)

Rich community data available:
  - Longevity histogram (b1-b5 vote counts) → community_longevity_label
  - Sillage histogram (b1-b4)               → community_sillage_rating
  - Season vote counts (spring/summer/autumn/winter)
  - Daypart vote counts (day/night)
  - Full note pyramids (top/middle/base)
  - Accord names + strengths
  - Rating average + vote count

Matching strategy:
  Primary:  Fragrantica integer ID extracted from fragrantica_url vs dataset `id` column
            (covers ~110K of 110K DB rows that already have fragrantica_url)
  Fallback: Fuzzy name+brand match (brand-scoped, 88% token_sort_ratio threshold)

Update policy (NEVER overwrites existing data — fills NULL/defaults only):
  - community_longevity_label  NULL    → derived from longevity_avg + min 20 votes
  - community_longevity_rating ==3.0   → longevity_avg (Fragrantica 1-5 scale, min 10 votes)
  - community_sillage_rating   ==3.0   → sillage_avg rescaled 1-4→1-5 (min 10 votes)
  - community_overall_rating   ==3.0   → rating_avg (min 5 votes)
  - rating_count               ==0     → people (total Fragrantica voters)
  - season_*_votes             all==0  → spring/summer/autumn/winter counts
  - occasion_daily_votes       ==0     → day count
  - occasion_night_votes       ==0     → night count
  - top/middle/base_notes      all []  → parsed from notes_top/notes_middle/notes_base
  - accords                    []      → accord names parsed from "name:strength|..." format
  - fragrantica_id             NULL    → dataset integer id as string

DO NOT RUN until you intend to populate the DB — see update counts from --dry-run first.

Run from backend/ directory:
  python scripts/import_ledecanteur.py --dry-run
  python scripts/import_ledecanteur.py
  python scripts/import_ledecanteur.py --limit 5000
"""

import sys
import re
import math
import time
import argparse
import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from config import get_settings

try:
    from rapidfuzz import fuzz, process as rfprocess
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    logging.warning("rapidfuzz not available — fuzzy fallback disabled")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATCH_SIZE = 500
FUZZY_THRESHOLD = 88.0
PROGRESS_EVERY = 1000

# Longevity label thresholds (Fragrantica longevity_avg scale 1-5)
# b1=very weak, b2=weak, b3=moderate, b4=long lasting, b5=eternal
LONGEVITY_STRONG_AVG = 3.7   # longevity_avg >= this → Strong
LONGEVITY_LIGHT_AVG = 2.0    # longevity_avg <= this → Light
LONGEVITY_MIN_VOTES = 20     # minimum total longevity votes to assign a label

CSV_PATH = Path(__file__).parent.parent.parent / "data" / "kaggle_new" / "perfumes.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def extract_frag_id(url: str) -> int | None:
    """Extract integer Fragrantica ID from URL like '...Brand/Name-12345.html'."""
    if not url:
        return None
    m = re.search(r"-(\d+)\.html$", url)
    return int(m.group(1)) if m else None


def parse_pipe_list(s) -> list[str]:
    """Parse pipe-separated string like 'Rose|Jasmine|Musk' → ['Rose', 'Jasmine', 'Musk']."""
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return []
    return [n.strip() for n in str(s).split("|") if n.strip()]


def parse_pipe_accords(s) -> list[str]:
    """Parse 'citrus:100|fresh spicy:47|...' → ['citrus', 'fresh spicy', ...]."""
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return []
    result = []
    for chunk in str(s).split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        result.append(chunk.split(":")[0].strip() if ":" in chunk else chunk)
    return result


def safe_int(v) -> int:
    """Convert a value that may be NaN/None to int (returns 0 for NaN/None)."""
    if v is None:
        return 0
    try:
        f = float(v)
        return 0 if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return 0


def safe_float(v) -> float | None:
    """Return float or None if NaN/None."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def derive_longevity_label(longevity_avg, total_votes: int) -> str | None:
    """Map Fragrantica longevity average to Strong/Medium/Light label."""
    if total_votes < LONGEVITY_MIN_VOTES:
        return None
    avg = safe_float(longevity_avg)
    if avg is None:
        return None
    if avg >= LONGEVITY_STRONG_AVG:
        return "Strong"
    if avg <= LONGEVITY_LIGHT_AVG:
        return "Light"
    return "Medium"


def scale_sillage(sillage_avg) -> float | None:
    """Rescale Fragrantica sillage 1-4 → 1-5 to match our DB scale."""
    avg = safe_float(sillage_avg)
    if avg is None:
        return None
    return round(1.0 + (avg - 1.0) * (4.0 / 3.0), 3)


def _is_default_float(val, default: float = 3.0, tol: float = 0.001) -> bool:
    """True if val is None or equals the default (within floating-point tolerance)."""
    if val is None:
        return True
    try:
        return abs(float(val) - default) < tol
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# Batch flush
# ---------------------------------------------------------------------------

def _flush_batch(cur, updates: list[dict]) -> int:
    """Execute one UPDATE per record. Returns number flushed."""
    flushed = 0
    for upd in updates:
        db_id = upd["id"]
        fields = {k: v for k, v in upd.items() if k != "id"}
        if not fields:
            continue
        set_clauses = ", ".join(f"{col} = %({col})s" for col in fields)
        fields["id"] = db_id
        cur.execute(f"UPDATE perfumes SET {set_clauses} WHERE id = %(id)s", fields)
        flushed += 1
    return flushed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Import community data from ledecanteur Fragrantica dataset")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be updated without writing")
    parser.add_argument("--limit", type=int, default=0, help="Cap DB rows processed (0=all, for testing)")
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="Path to perfumes.csv")
    args = parser.parse_args()

    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # ------------------------------------------------------------------
    # Step 1: Load ledecanteur dataset
    # ------------------------------------------------------------------
    print(f"[1/4] Loading {args.csv} ...")
    t0 = time.time()
    df = pd.read_csv(args.csv)
    print(f"      {len(df):,} rows loaded in {time.time()-t0:.1f}s")

    # ------------------------------------------------------------------
    # Step 2: Build lookups
    # ------------------------------------------------------------------
    print("[2/4] Building lookups ...")
    ld_by_id: dict[int, object] = {}
    ld_by_brand: dict[str, dict[str, object]] = defaultdict(dict)

    for row in df.itertuples(index=False):
        fid = int(row.id)
        ld_by_id[fid] = row
        if HAS_RAPIDFUZZ:
            brand_n = normalize(str(row.brand))
            name_n = normalize(str(row.name))
            ld_by_brand[brand_n][name_n] = row

    print(f"      {len(ld_by_id):,} entries by Fragrantica ID")
    if HAS_RAPIDFUZZ:
        print(f"      {len(ld_by_brand):,} brands indexed for fuzzy fallback")

    # ------------------------------------------------------------------
    # Step 3: Load DB records
    # ------------------------------------------------------------------
    print("[3/4] Loading perfumes from DB ...")
    t0 = time.time()
    cur.execute("""
        SELECT id, name, brand,
               fragrantica_url, fragrantica_id,
               community_longevity_label,
               community_longevity_rating,
               community_sillage_rating,
               community_overall_rating,
               rating_count,
               season_spring_votes, season_summer_votes,
               season_fall_votes, season_winter_votes,
               occasion_daily_votes, occasion_night_votes,
               top_notes, middle_notes, base_notes, accords
        FROM perfumes
        ORDER BY id
    """)
    db_rows = cur.fetchall()
    total_db = len(db_rows)
    if args.limit:
        db_rows = db_rows[:args.limit]
    print(f"      {total_db:,} DB rows ({len(db_rows):,} will be processed)")

    # ------------------------------------------------------------------
    # Step 4: Match & build updates
    # ------------------------------------------------------------------
    print(f"[4/4] Matching and building updates (dry_run={args.dry_run}) ...")

    stats = {
        "matched_by_id": 0,
        "matched_by_fuzzy": 0,
        "no_match": 0,
        "updated_frag_id": 0,
        "updated_longevity_label": 0,
        "updated_longevity_rating": 0,
        "updated_sillage_rating": 0,
        "updated_overall_rating": 0,
        "updated_rating_count": 0,
        "updated_season_votes": 0,
        "updated_occasion_votes": 0,
        "updated_notes": 0,
        "updated_accords": 0,
        "total_updates": 0,
        "total_flushed": 0,
    }

    batch_updates: list[dict] = []
    t0 = time.time()

    for i, row in enumerate(db_rows):
        db_id = row["id"]
        db_name = row["name"] or ""
        db_brand = row["brand"] or ""
        db_url = row["fragrantica_url"] or ""
        db_frag_id = row["fragrantica_id"]

        # --- Match ---
        ld = None
        extracted_id = extract_frag_id(db_url)
        if extracted_id is not None:
            ld = ld_by_id.get(extracted_id)
            if ld is not None:
                stats["matched_by_id"] += 1

        if ld is None and HAS_RAPIDFUZZ and db_brand:
            brand_n = normalize(db_brand)
            name_n = normalize(db_name)
            brand_dict = ld_by_brand.get(brand_n, {})
            if brand_dict:
                result = rfprocess.extractOne(
                    name_n, list(brand_dict.keys()),
                    scorer=fuzz.token_sort_ratio
                )
                if result and result[1] >= FUZZY_THRESHOLD:
                    ld = brand_dict[result[0]]
                    stats["matched_by_fuzzy"] += 1

        if ld is None:
            stats["no_match"] += 1
            continue

        # --- Compute candidate updates ---
        upd: dict = {"id": db_id}

        # fragrantica_id
        if not db_frag_id:
            upd["fragrantica_id"] = str(int(ld.id))
            stats["updated_frag_id"] += 1

        # Precompute NaN-safe integer fields from dataset row
        lv_b1 = safe_int(ld.longevity_b1)
        lv_b2 = safe_int(ld.longevity_b2)
        lv_b3 = safe_int(ld.longevity_b3)
        lv_b4 = safe_int(ld.longevity_b4)
        lv_b5 = safe_int(ld.longevity_b5)
        total_lv = lv_b1 + lv_b2 + lv_b3 + lv_b4 + lv_b5

        sil_b1 = safe_int(ld.sillage_b1)
        sil_b2 = safe_int(ld.sillage_b2)
        sil_b3 = safe_int(ld.sillage_b3)
        sil_b4 = safe_int(ld.sillage_b4)
        total_sil = sil_b1 + sil_b2 + sil_b3 + sil_b4

        lv_avg = safe_float(ld.longevity_avg)
        sil_avg = safe_float(ld.sillage_avg)
        rat_avg = safe_float(ld.rating_avg)
        people = safe_int(ld.people)
        vote_count = safe_int(ld.vote_count)

        ld_spring = safe_int(ld.spring)
        ld_summer = safe_int(ld.summer)
        ld_autumn = safe_int(ld.autumn)
        ld_winter = safe_int(ld.winter)
        ld_day = safe_int(ld.day)
        ld_night = safe_int(ld.night)

        # community_longevity_label
        if not row["community_longevity_label"]:
            label = derive_longevity_label(lv_avg, total_lv)
            if label:
                upd["community_longevity_label"] = label
                stats["updated_longevity_label"] += 1

        # community_longevity_rating
        if _is_default_float(row["community_longevity_rating"]):
            if lv_avg is not None and total_lv >= 10:
                upd["community_longevity_rating"] = round(lv_avg, 3)
                stats["updated_longevity_rating"] += 1

        # community_sillage_rating (rescale 1-4 → 1-5)
        if _is_default_float(row["community_sillage_rating"]):
            scaled_sil = scale_sillage(sil_avg)
            if scaled_sil is not None and total_sil >= 10:
                upd["community_sillage_rating"] = scaled_sil
                stats["updated_sillage_rating"] += 1

        # community_overall_rating
        if _is_default_float(row["community_overall_rating"]):
            if rat_avg is not None and vote_count >= 5:
                upd["community_overall_rating"] = round(rat_avg, 3)
                stats["updated_overall_rating"] += 1

        # rating_count
        if (row["rating_count"] or 0) == 0:
            if people > 0:
                upd["rating_count"] = people
                stats["updated_rating_count"] += 1

        # Season votes — only fill if all four are 0
        spring = row["season_spring_votes"] or 0
        summer = row["season_summer_votes"] or 0
        fall = row["season_fall_votes"] or 0
        winter = row["season_winter_votes"] or 0
        if spring == 0 and summer == 0 and fall == 0 and winter == 0:
            total_season = ld_spring + ld_summer + ld_autumn + ld_winter
            if total_season > 0:
                upd["season_spring_votes"] = ld_spring
                upd["season_summer_votes"] = ld_summer
                upd["season_fall_votes"] = ld_autumn
                upd["season_winter_votes"] = ld_winter
                stats["updated_season_votes"] += 1

        # Occasion votes (day → daily, night → night)
        if (row["occasion_daily_votes"] or 0) == 0 and (row["occasion_night_votes"] or 0) == 0:
            if ld_day > 0 or ld_night > 0:
                upd["occasion_daily_votes"] = ld_day
                upd["occasion_night_votes"] = ld_night
                stats["updated_occasion_votes"] += 1

        # Notes pyramid — only fill if ALL three lists are empty
        cur_top = row["top_notes"] or []
        cur_mid = row["middle_notes"] or []
        cur_base = row["base_notes"] or []
        if not cur_top and not cur_mid and not cur_base:
            new_top = parse_pipe_list(ld.notes_top)
            new_mid = parse_pipe_list(ld.notes_middle)
            new_base = parse_pipe_list(ld.notes_base)
            # Fall back to flat notes (stored in middle) if no pyramid
            if not (new_top or new_mid or new_base):
                flat = parse_pipe_list(ld.notes_flat)
                new_mid = flat
            if new_top or new_mid or new_base:
                upd["top_notes"] = psycopg2.extras.Json(new_top)
                upd["middle_notes"] = psycopg2.extras.Json(new_mid)
                upd["base_notes"] = psycopg2.extras.Json(new_base)
                stats["updated_notes"] += 1

        # Accords — only fill if empty
        cur_accords = row["accords"] or []
        if not cur_accords:
            new_accords = parse_pipe_accords(ld.accords)
            if new_accords:
                upd["accords"] = psycopg2.extras.Json(new_accords)
                stats["updated_accords"] += 1

        # Only queue if something actually changed beyond id
        if len(upd) > 1:
            batch_updates.append(upd)
            stats["total_updates"] += 1

        # Progress log
        if (i + 1) % PROGRESS_EVERY == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(db_rows) - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i+1:,}/{len(db_rows):,}] "
                f"matched={stats['matched_by_id']+stats['matched_by_fuzzy']:,} "
                f"labels={stats['updated_longevity_label']:,} "
                f"seasons={stats['updated_season_votes']:,} "
                f"notes={stats['updated_notes']:,} "
                f"pending={len(batch_updates):,} "
                f"ETA={eta/60:.1f}m"
            )

        # Flush
        if len(batch_updates) >= BATCH_SIZE and not args.dry_run:
            stats["total_flushed"] += _flush_batch(cur, batch_updates)
            conn.commit()
            batch_updates = []

    # Final flush
    if batch_updates and not args.dry_run:
        stats["total_flushed"] += _flush_batch(cur, batch_updates)
        conn.commit()

    conn.close()

    print()
    print("=" * 60)
    print(f"  {'DRY RUN — no changes written' if args.dry_run else 'IMPORT COMPLETE'}")
    print("=" * 60)
    col_w = max(len(k) for k in stats)
    for k, v in stats.items():
        print(f"  {k:<{col_w}} : {v:>12,}")

    if args.dry_run:
        print()
        print("Re-run without --dry-run to apply these updates.")


if __name__ == "__main__":
    main()
