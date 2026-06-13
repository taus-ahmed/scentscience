"""
Import Parfumo dataset into the perfumes table.

Supported input formats:
  1. Kaggle dataset (olgagmiufana1/parfumo-fragrance-dataset):
       Name, Brand, Rating, Votes, Main_Accords, Top_Notes, Middle_Notes,
       Base_Notes, Longevity, Sillage, Gender, Concentration, Year
  2. FragDB Parfumo bundle (parfumo/perfumes.csv):
       34-column FragDB Parfumo format (see README.md for field list)

Usage:
    cd backend/
    python scripts/import_parfumo.py --csv data/datasets/parfumo_dataset.csv [--dry-run]

The script fuzzy-matches on (brand, name) with a 90-token-sort-ratio threshold,
then for each match:
  - Increments source_count by 1
  - Merges note pyramid if the matched perfume has none
  - Updates community_longevity_label if Parfumo label is higher-confidence
  - Updates rating_count if Parfumo Votes > existing rating_count (additive)
  - Updates community_overall_rating if Parfumo Rating is present

Idempotent via source_count check: won't double-count if re-run (tracks
which perfumes were already updated via a run-state JSON sidecar).
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from sqlalchemy import select, func, update
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Run-state sidecar: tracks which Parfumo perfumes have already been imported
# so re-runs are fully idempotent.
RUNSTATE_PATH = Path(__file__).parent / "import_parfumo_runstate.json"

PARFUMO_LONGEVITY_MAP = {
    # Kaggle dataset string values
    "very weak":       "Light",
    "weak":            "Light",
    "moderate":        "Medium",
    "long lasting":    "Strong",
    "very long lasting": "Strong",
    "eternal":         "Strong",
    # FragDB Parfumo encoded values (integer 1-5)
    "1": "Light",
    "2": "Light",
    "3": "Medium",
    "4": "Strong",
    "5": "Strong",
}


# ── Column detection ──────────────────────────────────────────────────────────

def detect_format(headers: list[str]) -> str:
    """Return 'kaggle', 'fragdb', or 'unknown'."""
    h = {c.lower().strip() for c in headers}
    if "votes" in h and "main_accords" in h:
        return "kaggle"
    if "pid" in h and "notes_pyramid" in h:
        return "fragdb"
    # Attempt heuristic: does it have Name+Brand?
    if "name" in h and "brand" in h:
        return "kaggle"
    return "unknown"


def _col(row: dict, *candidates: str) -> str:
    """Return first non-empty matching column value, case-insensitive."""
    lower = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        val = lower.get(c.lower(), "").strip()
        if val:
            return val
    return ""


def parse_note_list(raw: str) -> list[str]:
    """Turn 'Rose, Jasmine, Bergamot' or '["Rose","Jasmine"]' into a list."""
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            items = json.loads(raw)
            return [str(i).strip() for i in items if i]
        except json.JSONDecodeError:
            pass
    return [n.strip() for n in raw.split(",") if n.strip()]


def parse_accords(raw: str) -> list[str]:
    return parse_note_list(raw)


def parse_longevity_label(raw: str) -> Optional[str]:
    if not raw:
        return None
    return PARFUMO_LONGEVITY_MAP.get(raw.lower().strip())


def extract_kaggle_row(row: dict) -> dict:
    """Normalize a Kaggle Parfumo CSV row to our internal dict."""
    name  = _col(row, "Name", "Perfume", "Fragrance")
    brand = _col(row, "Brand", "House", "Maison")

    rating_str = _col(row, "Rating", "Average_Rating", "Score")
    try:
        rating = float(rating_str) if rating_str else None
        # Parfumo uses 1-5 scale; Fragrantica uses 1-5 too — keep as-is
        if rating and rating > 5.0:
            rating = rating / 2.0  # some datasets use 1-10
    except ValueError:
        rating = None

    votes_str = _col(row, "Votes", "Rating_Count", "Num_Ratings", "Count")
    try:
        votes = int(votes_str.replace(",", "")) if votes_str else 0
    except ValueError:
        votes = 0

    top    = parse_note_list(_col(row, "Top_Notes", "Top Notes", "top_notes"))
    middle = parse_note_list(_col(row, "Middle_Notes", "Middle Notes", "heart_notes", "middle_notes"))
    base   = parse_note_list(_col(row, "Base_Notes", "Base Notes", "base_notes"))
    accords = parse_accords(_col(row, "Main_Accords", "Accords", "accords", "main_accords"))

    longevity_raw = _col(row, "Longevity", "longevity", "longevity_rating")
    longevity_label = parse_longevity_label(longevity_raw)

    concentration = _col(row, "Concentration", "Type", "concentration")

    return {
        "name": name,
        "brand": brand,
        "rating": rating,
        "votes": votes,
        "top_notes": top,
        "middle_notes": middle,
        "base_notes": base,
        "accords": accords,
        "longevity_label": longevity_label,
        "concentration": concentration,
    }


# ── Fuzzy matching ────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    return s.lower().strip()


def _match_key(brand: str, name: str) -> str:
    return f"{_normalize(brand)}||{_normalize(name)}"


def build_db_index(perfumes: list[Perfume]) -> dict[str, int]:
    """Build a fast lookup: 'brand||name' -> perfume.id."""
    return {_match_key(p.brand or "", p.name or ""): p.id for p in perfumes}


def fuzzy_match(
    brand: str,
    name: str,
    db_index: dict[str, int],
    perfumes_by_id: dict[int, Perfume],
    threshold: int = 90,
) -> Optional[Perfume]:
    """Try exact first, then token_sort_ratio fuzzy match."""
    from rapidfuzz import fuzz

    exact_key = _match_key(brand, name)
    if exact_key in db_index:
        return perfumes_by_id[db_index[exact_key]]

    query_str = f"{_normalize(brand)} {_normalize(name)}"
    best_score = 0
    best_id = None
    for key, pid in db_index.items():
        db_brand, db_name = key.split("||", 1)
        candidate_str = f"{db_brand} {db_name}"
        score = fuzz.token_sort_ratio(query_str, candidate_str)
        if score > best_score:
            best_score = score
            best_id = pid

    if best_score >= threshold and best_id is not None:
        return perfumes_by_id[best_id]
    return None


# ── DB operations ─────────────────────────────────────────────────────────────

async def load_all_perfumes() -> tuple[list[Perfume], dict[str, int], dict[int, Perfume]]:
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Perfume))
        perfumes = result.scalars().all()
    idx = build_db_index(perfumes)
    by_id = {p.id: p for p in perfumes}
    return perfumes, idx, by_id


async def apply_updates(updates: list[dict], dry_run: bool) -> None:
    """Batch-apply updates to the DB."""
    if not updates:
        return
    if dry_run:
        logger.info("[DRY RUN] Would apply %d updates", len(updates))
        return

    async with AsyncSessionLocal() as session:
        for u in updates:
            pid = u.pop("id")
            await session.execute(
                update(Perfume).where(Perfume.id == pid).values(**u)
            )
        await session.commit()
    logger.info("Applied %d updates to database", len(updates))


# ── Main logic ────────────────────────────────────────────────────────────────

def load_runstate() -> set[str]:
    if RUNSTATE_PATH.exists():
        with open(RUNSTATE_PATH) as f:
            return set(json.load(f))
    return set()


def save_runstate(seen: set[str]) -> None:
    with open(RUNSTATE_PATH, "w") as f:
        json.dump(sorted(seen), f)


async def run_import(csv_path: Path, dry_run: bool, match_threshold: int) -> None:
    logger.info("Loading all perfumes from DB…")
    _, db_index, by_id = await load_all_perfumes()
    logger.info("Loaded %d perfumes into fuzzy index", len(db_index))

    already_imported = load_runstate()
    logger.info("Runstate: %d Parfumo entries already imported", len(already_imported))

    rows_total = 0
    rows_matched = 0
    rows_skipped_runstate = 0
    rows_no_match = 0
    updates: list[dict] = []

    # Detect delimiter — Parfumo CSVs might be comma or semicolon separated
    with open(csv_path, encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        f.seek(0)
        reader = csv.DictReader(f, dialect=dialect)
        headers = reader.fieldnames or []

    fmt = detect_format(headers)
    logger.info("CSV columns (%d): %s", len(headers), headers)
    logger.info("Detected format: %s", fmt)

    if fmt == "unknown":
        logger.warning(
            "Unknown CSV format. Expected columns like 'Name', 'Brand', 'Votes', "
            "'Main_Accords'. Available: %s", headers
        )

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            rows_total += 1

            if fmt in ("kaggle", "unknown"):
                parsed = extract_kaggle_row(row)
            else:
                logger.warning("FragDB Parfumo format not yet implemented — skipping row")
                continue

            pname  = parsed["name"]
            pbrand = parsed["brand"]

            if not pname or not pbrand:
                continue

            runstate_key = f"{_normalize(pbrand)}|{_normalize(pname)}"
            if runstate_key in already_imported:
                rows_skipped_runstate += 1
                continue

            matched = fuzzy_match(pbrand, pname, db_index, by_id, match_threshold)
            if not matched:
                rows_no_match += 1
                if rows_no_match <= 20:
                    logger.debug("  NO MATCH: '%s' by '%s'", pname, pbrand)
                continue

            rows_matched += 1
            upd: dict = {"id": matched.id}

            # Always increment source_count
            upd["source_count"] = (matched.source_count or 1) + 1

            # Merge note pyramid if the matched perfume has none
            has_pyramid = bool(
                (matched.top_notes or []) +
                (matched.middle_notes or []) +
                (matched.base_notes or [])
            )
            if not has_pyramid:
                if parsed["top_notes"]:
                    upd["top_notes"] = parsed["top_notes"]
                if parsed["middle_notes"]:
                    upd["middle_notes"] = parsed["middle_notes"]
                if parsed["base_notes"]:
                    upd["base_notes"] = parsed["base_notes"]

            # Update rating_count: add Parfumo votes (independent community)
            parfumo_votes = parsed["votes"]
            if parfumo_votes > 0:
                upd["rating_count"] = (matched.rating_count or 0) + parfumo_votes

            # Update community_overall_rating if Parfumo has one and ours is default
            parfumo_rating = parsed["rating"]
            if parfumo_rating and (not matched.community_overall_rating or matched.community_overall_rating == 3.0):
                # Parfumo 1-5 scale → our 1-5 scale (same)
                upd["community_overall_rating"] = round(parfumo_rating, 2)

            # Set community_longevity_label only if we don't have one
            if parsed["longevity_label"] and not matched.community_longevity_label:
                upd["community_longevity_label"] = parsed["longevity_label"]

            # Concentration: fill if missing
            if parsed["concentration"] and not matched.concentration:
                upd["concentration"] = parsed["concentration"]

            updates.append(upd)
            already_imported.add(runstate_key)

            if rows_matched <= 5:
                logger.info(
                    "  MATCH: '%s' by '%s' → DB id=%d (sc %d→%d, votes +%d)",
                    pname, pbrand, matched.id,
                    matched.source_count or 1, upd["source_count"],
                    parfumo_votes,
                )

    logger.info(
        "\n=== IMPORT SUMMARY ===\n"
        "  CSV rows read:          %d\n"
        "  Matched & queued:       %d\n"
        "  Skipped (already done): %d\n"
        "  No match (threshold %d%%): %d",
        rows_total, rows_matched, rows_skipped_runstate, match_threshold, rows_no_match,
    )

    await apply_updates(updates, dry_run)

    if not dry_run:
        save_runstate(already_imported)
        logger.info("Runstate saved: %d total Parfumo entries imported", len(already_imported))
    else:
        logger.info("[DRY RUN] Runstate not updated")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Parfumo CSV into perfumes table")
    parser.add_argument("--csv", required=True, help="Path to Parfumo CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Parse + match but don't write to DB")
    parser.add_argument("--threshold", type=int, default=90, help="Fuzzy match threshold 0-100 (default 90)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error("File not found: %s", csv_path)
        sys.exit(1)

    asyncio.run(run_import(csv_path, args.dry_run, args.threshold))


if __name__ == "__main__":
    main()
