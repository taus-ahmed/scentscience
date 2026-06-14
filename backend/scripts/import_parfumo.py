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
import re
import sys
from collections import defaultdict
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

    rating_str = _col(row, "Rating_Value", "Rating", "Average_Rating", "Score")
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

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
# Concentration suffixes — only stripped when name is verbose (contains brand or year)
_CONC_SUFFIXES = re.compile(
    r"\s+(eau\s+de\s+(parfum|toilette|cologne)|lotion\s+apr[eè]s.rasage"
    r"|lotion\s+avant.rasage|lotion|very\s+cool\s+spray|concentr[eé][e]?"
    r"|solid|body\s+spray)\b.*$",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    return s.lower().strip()


def _clean_parfumo_name(name: str, brand: str) -> str:
    """Strip embedded brand/year/concentration from verbose Parfumo names.

    Only modifies names that contain the brand or a 4-digit year — clean names
    like 'Sauvage Elixir' or 'Black Opium' are returned unchanged.

    'Sauvage Dior 2015 Eau de Toilette' → 'Sauvage'
    'Joop! Homme Joop! 1989 Eau de Toilette' → 'Joop! Homme'
    'Sauvage Elixir' → 'Sauvage Elixir'  (unchanged)
    """
    brand_norm = brand.strip()
    has_year = bool(_YEAR_RE.search(name))
    has_brand = bool(re.search(r"\s+" + re.escape(brand_norm), name, re.IGNORECASE))

    if not has_year and not has_brand:
        return name  # already clean

    s = name.strip()
    s = _CONC_SUFFIXES.sub("", s).strip()
    s = _YEAR_RE.sub("", s).strip()
    brand_pattern = r"\s+" + re.escape(brand_norm) + r"\s*$"
    s = re.sub(brand_pattern, "", s, flags=re.IGNORECASE).strip()
    return s or name  # fall back to original if we stripped everything


def _match_key(brand: str, name: str) -> str:
    return f"{_normalize(brand)}||{_normalize(name)}"


def build_db_index(
    perfumes: list[Perfume],
) -> tuple[dict[str, int], dict[str, list[tuple[str, int]]]]:
    """Build two indexes:
      - exact_index: 'brand||name' -> perfume.id  (O(1) lookup)
      - brand_index: normalized_brand -> [(normalized_name, id), ...]  (brand-scoped fuzzy)
    """
    exact_index: dict[str, int] = {}
    brand_index: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for p in perfumes:
        b = _normalize(p.brand or "")
        n = _normalize(p.name or "")
        exact_index[f"{b}||{n}"] = p.id
        brand_index[b].append((n, p.id))

    return exact_index, brand_index


def fuzzy_match(
    brand: str,
    name: str,
    exact_index: dict[str, int],
    brand_index: dict[str, list[tuple[str, int]]],
    perfumes_by_id: dict[int, Perfume],
    threshold: int = 90,
) -> Optional[Perfume]:
    """Try exact match first, then brand-scoped token_sort_ratio fuzzy match.

    Scopes fuzzy search to the same brand, reducing candidates from 67k → ~10-100.
    Also tries with the cleaned name (brand/year/concentration stripped).
    """
    from rapidfuzz import fuzz

    brand_norm = _normalize(brand)
    name_norm = _normalize(name)
    clean_name = _normalize(_clean_parfumo_name(name, brand))

    # 1. Exact match on original name
    exact_key = f"{brand_norm}||{name_norm}"
    if exact_key in exact_index:
        return perfumes_by_id[exact_index[exact_key]]

    # 2. Exact match on cleaned name
    if clean_name != name_norm:
        clean_key = f"{brand_norm}||{clean_name}"
        if clean_key in exact_index:
            return perfumes_by_id[exact_index[clean_key]]

    # 3. Brand-scoped fuzzy match (only entries with the same brand)
    candidates = brand_index.get(brand_norm, [])
    if not candidates:
        return None

    best_score = 0
    best_id = None
    for db_name, pid in candidates:
        score = fuzz.token_sort_ratio(clean_name, db_name)
        if score > best_score:
            best_score = score
            best_id = pid

    if best_score >= threshold and best_id is not None:
        return perfumes_by_id[best_id]
    return None


# ── DB operations ─────────────────────────────────────────────────────────────

async def load_all_perfumes() -> tuple[
    list[Perfume],
    dict[str, int],
    dict[str, list[tuple[str, int]]],
    dict[int, Perfume],
]:
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Perfume))
        perfumes = result.scalars().all()
    exact_idx, brand_idx = build_db_index(perfumes)
    by_id = {p.id: p for p in perfumes}
    return perfumes, exact_idx, brand_idx, by_id


async def apply_updates(updates: list[dict], dry_run: bool) -> None:
    """Batch-apply updates using bulk SQL to avoid per-row round-trips.

    Uses PostgreSQL unnest() arrays so the entire update is 3-5 queries total
    instead of 16,000 individual round-trips.
    """
    if not updates:
        return
    if dry_run:
        logger.info("[DRY RUN] Would apply %d updates", len(updates))
        return

    from sqlalchemy import text

    sc_ids: list[int] = []
    rc_pairs: list[tuple[int, int]] = []   # (id, new_rating_count)
    cor_pairs: list[tuple[int, float]] = []  # (id, community_overall_rating)
    label_pairs: list[tuple[int, str]] = []  # (id, community_longevity_label)
    conc_pairs: list[tuple[int, str]] = []   # (id, concentration)
    # JSON array fields — rare (only unlabeled perfumes without pyramids); keep individual
    json_updates: list[dict] = []

    for u in updates:
        pid = u["id"]
        sc_ids.append(pid)
        if "rating_count" in u:
            rc_pairs.append((pid, int(u["rating_count"])))
        if "community_overall_rating" in u:
            cor_pairs.append((pid, float(u["community_overall_rating"])))
        if "community_longevity_label" in u:
            label_pairs.append((pid, u["community_longevity_label"]))
        if "concentration" in u:
            conc_pairs.append((pid, u["concentration"]))
        if any(f in u for f in ("top_notes", "middle_notes", "base_notes")):
            json_updates.append({k: v for k, v in u.items()
                                  if k in ("id", "top_notes", "middle_notes", "base_notes")})

    async with AsyncSessionLocal() as session:
        # 1. Bulk source_count increment via unnest — one query
        if sc_ids:
            await session.execute(
                text(
                    "UPDATE perfumes SET source_count = source_count + 1"
                    " WHERE id = ANY(:ids)"
                ),
                {"ids": sc_ids},
            )
            logger.info("  source_count +1 applied to %d perfumes", len(sc_ids))

        # 2. rating_count via unnest pair — one query
        if rc_pairs:
            ids = [p[0] for p in rc_pairs]
            vals = [p[1] for p in rc_pairs]
            await session.execute(
                text(
                    "UPDATE perfumes SET rating_count = v.rc"
                    " FROM unnest(CAST(:ids AS int[]), CAST(:vals AS int[])) AS v(pid, rc)"
                    " WHERE perfumes.id = v.pid"
                ),
                {"ids": ids, "vals": vals},
            )
            logger.info("  rating_count updated for %d perfumes", len(rc_pairs))

        # 3. community_overall_rating
        if cor_pairs:
            ids = [p[0] for p in cor_pairs]
            vals = [p[1] for p in cor_pairs]
            await session.execute(
                text(
                    "UPDATE perfumes SET community_overall_rating = v.r"
                    " FROM unnest(CAST(:ids AS int[]), CAST(:vals AS float[])) AS v(pid, r)"
                    " WHERE perfumes.id = v.pid"
                ),
                {"ids": ids, "vals": vals},
            )
            logger.info("  community_overall_rating updated for %d perfumes", len(cor_pairs))

        # 4. community_longevity_label
        if label_pairs:
            ids = [p[0] for p in label_pairs]
            vals = [p[1] for p in label_pairs]
            await session.execute(
                text(
                    "UPDATE perfumes SET community_longevity_label = v.lbl"
                    " FROM unnest(CAST(:ids AS int[]), CAST(:vals AS text[])) AS v(pid, lbl)"
                    " WHERE perfumes.id = v.pid"
                ),
                {"ids": ids, "vals": vals},
            )
            logger.info("  community_longevity_label updated for %d perfumes", len(label_pairs))

        # 5. concentration
        if conc_pairs:
            ids = [p[0] for p in conc_pairs]
            vals = [p[1] for p in conc_pairs]
            await session.execute(
                text(
                    "UPDATE perfumes SET concentration = v.c"
                    " FROM unnest(CAST(:ids AS int[]), CAST(:vals AS text[])) AS v(pid, c)"
                    " WHERE perfumes.id = v.pid"
                ),
                {"ids": ids, "vals": vals},
            )
            logger.info("  concentration updated for %d perfumes", len(conc_pairs))

        # 6. JSON array fields (small subset — individually parameterized)
        if json_updates:
            for u in json_updates:
                pid = u["id"]
                fields = {k: json.dumps(v) for k, v in u.items()
                          if k != "id" and v is not None}
                for field, val in fields.items():
                    await session.execute(
                        text(f"UPDATE perfumes SET {field} = :val::jsonb WHERE id = :pid"),
                        {"val": val, "pid": pid},
                    )
            logger.info("  JSON note pyramids merged for %d perfumes", len(json_updates))

        await session.commit()

    logger.info("Bulk apply complete: %d perfumes updated", len(sc_ids))


# ── Main logic ────────────────────────────────────────────────────────────────

def load_runstate() -> set[str]:
    if RUNSTATE_PATH.exists():
        with open(RUNSTATE_PATH) as f:
            return set(json.load(f))
    return set()


def save_runstate(seen: set[str]) -> None:
    with open(RUNSTATE_PATH, "w") as f:
        json.dump(sorted(seen), f)


async def run_import(csv_path: Path, dry_run: bool, match_threshold: int, save_matches_path: Optional[Path] = None) -> None:
    logger.info("Loading all perfumes from DB…")
    _, exact_index, brand_index, by_id = await load_all_perfumes()
    logger.info(
        "Loaded %d perfumes into index (%d brands)",
        len(exact_index), len(brand_index),
    )

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

            matched = fuzzy_match(pbrand, pname, exact_index, brand_index, by_id, match_threshold)
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

    if save_matches_path:
        with open(save_matches_path, "w") as f:
            json.dump(updates, f)
        logger.info("Matches saved to %s — run with --apply-only to write to DB", save_matches_path)
        return

    await apply_updates(updates, dry_run)

    if not dry_run:
        save_runstate(already_imported)
        logger.info("Runstate saved: %d total Parfumo entries imported", len(already_imported))
    else:
        logger.info("[DRY RUN] Runstate not updated")


async def run_apply_only(matches_path: Path) -> None:
    """Load a saved matches JSON and apply updates to DB (phase 2)."""
    with open(matches_path) as f:
        updates = json.load(f)
    logger.info("Loaded %d updates from %s", len(updates), matches_path)
    await apply_updates(updates, dry_run=False)

    # Rebuild runstate from the match file so re-runs stay idempotent
    seen: set[str] = load_runstate()
    for u in updates:
        pid = u.get("id")
        if pid:
            seen.add(str(pid))
    save_runstate(seen)
    logger.info("Runstate updated: %d entries", len(seen))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Parfumo CSV into perfumes table")
    parser.add_argument("--csv", help="Path to Parfumo CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Parse + match but don't write to DB")
    parser.add_argument("--threshold", type=int, default=90, help="Fuzzy match threshold 0-100 (default 90)")
    parser.add_argument("--save-matches", metavar="FILE",
                        help="Save match list to FILE as JSON (phase 1 only, no DB write)")
    parser.add_argument("--apply-only", metavar="FILE",
                        help="Skip matching; load FILE and apply updates to DB (phase 2)")
    args = parser.parse_args()

    if args.apply_only:
        p = Path(args.apply_only)
        if not p.exists():
            logger.error("Matches file not found: %s", p)
            sys.exit(1)
        asyncio.run(run_apply_only(p))
        return

    if not args.csv:
        parser.error("--csv is required unless --apply-only is used")

    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error("File not found: %s", csv_path)
        sys.exit(1)

    save_matches_path = Path(args.save_matches) if args.save_matches else None
    asyncio.run(run_import(csv_path, args.dry_run, args.threshold, save_matches_path))


if __name__ == "__main__":
    main()
