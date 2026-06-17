"""
Import community vote data from ledecanteur/fragrantica-perfumes Kaggle dataset.

Source: data/kaggle_new/perfumes.csv  (131,930 rows, scraped June 2026)
Kaggle: kaggle datasets download ledecanteur/fragrantica-perfumes -f perfumes.csv

What it fills in (gap-fill only — never overwrites existing non-zero values):
  rating_count              ← vote_count         (if DB has 0)
  community_longevity_rating ← longevity_avg     (if DB has default 3.0)
  community_sillage_rating   ← sillage_avg       (if DB has default 3.0)
  community_overall_rating   ← rating_avg        (if DB has default 3.0)
  season_*_votes             ← spring/summer/autumn/winter  (if all 4 are 0)
  top/middle/base_notes      ← notes_top/middle/base        (if top_notes empty)
  accords                    ← accords column    (if empty)
  fragrantica_id             ← id column         (if NULL)
  community_longevity_label  ← derived from longevity histogram (if NULL, ≥20 votes)

Matching strategy:
  1. Exact match on fragrantica_id (Fragrantica numeric id)
  2. Brand-scoped fuzzy name match (rapidfuzz token_sort_ratio ≥ 88)

Run from backend/ directory:
  python scripts/import_fragrantica_votes.py
  python scripts/import_fragrantica_votes.py --dry-run
  python scripts/import_fragrantica_votes.py --csv /path/to/perfumes.csv
  python scripts/import_fragrantica_votes.py --limit 5000   # test run
"""

import sys
import os
import re
import json
import time
import argparse
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import Json as PgJson, execute_values
from rapidfuzz import fuzz
from rapidfuzz import process as rfprocess

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/railway",
)
DEFAULT_CSV = Path(__file__).parent.parent.parent / "data" / "kaggle_new" / "perfumes.csv"

FUZZY_THRESHOLD = 88.0
BATCH_SIZE = 500        # rows per write batch — commit often, keep Railway happy
PROGRESS_EVERY = 5_000
MIN_LONGEVITY_VOTES = 20   # min votes to derive longevity label from histogram

DB_LOAD_CHUNK = 5_000   # rows per paginated keyset SELECT when building in-memory index
DB_CONNECT_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Brand-name normalization
# ---------------------------------------------------------------------------

_PUNC_RE = re.compile(r"[^\w\s]")


def _norm(s: str) -> str:
    return _PUNC_RE.sub("", str(s).lower()).strip()


# Common brand aliases so "Christian Dior" → "dior" etc.
_BRAND_ALIASES: dict[str, str] = {
    "christian dior": "dior",
    "yves saint laurent": "yves saint laurent",  # keep as-is (YSL also common)
    "giorgio armani": "armani",
    "ralph lauren": "ralph lauren",
    "viktor  rolf": "viktor rolf",
    "viktor & rolf": "viktor rolf",
}


def _norm_brand(s: str) -> str:
    n = _norm(s)
    return _BRAND_ALIASES.get(n, n)


# ---------------------------------------------------------------------------
# Load DB into memory
# ---------------------------------------------------------------------------


# Avoid loading JSON columns (top_notes, middle_notes, base_notes, accords) —
# they add ~7ms/row over the wire and push a 5k-chunk from ~8s to >60s.
# Instead, compute boolean flags server-side via text comparison (json is stored
# as raw text in PostgreSQL, so 'col::text = "[]"' is a cheap string check).
_DB_LOAD_COLS = [
    "id", "name", "brand", "fragrantica_id",
    "rating_count",
    "community_longevity_rating",
    "community_sillage_rating",
    "community_overall_rating",
    "season_spring_votes",
    "community_longevity_label",
]
_DB_LOAD_SQL = """
    SELECT
        id, name, brand, fragrantica_id,
        rating_count,
        community_longevity_rating,
        community_sillage_rating,
        community_overall_rating,
        season_spring_votes,
        community_longevity_label,
        (top_notes::text = '[]')  AS top_notes_empty,
        (accords::text = '[]')    AS accords_empty
    FROM perfumes
    WHERE id > %s
    ORDER BY id
    LIMIT %s
"""
_DB_ALL_COLS = _DB_LOAD_COLS + ["top_notes_empty", "accords_empty"]


# Column → PostgreSQL cast for VALUES-based bulk UPDATE
_COL_CAST: dict[str, str] = {
    "rating_count": "int",
    "community_longevity_rating": "float8",
    "community_sillage_rating": "float8",
    "community_overall_rating": "float8",
    "season_spring_votes": "int",
    "season_summer_votes": "int",
    "season_fall_votes": "int",
    "season_winter_votes": "int",
    "top_notes": "json",
    "middle_notes": "json",
    "base_notes": "json",
    "accords": "json",
    "fragrantica_id": "text",
    "community_longevity_label": "text",
}


def _open_conn() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DB_URL, connect_timeout=DB_CONNECT_TIMEOUT)
    conn.cursor().execute("SET statement_timeout = 0")  # disable session timeout
    conn.commit()
    return conn


def load_db() -> tuple[dict, dict, dict]:
    """Return (db_by_id, frag_id_index, brand_index).

    Uses paginated 10k-row queries so no single connection stays open long
    enough to hit the Railway proxy idle timeout.
    """
    frag_id_index: dict[str, int] = {}
    brand_index: dict[str, list] = {}
    db_by_id: dict[int, dict] = {}

    last_id = 0
    n_chunks = 0
    while True:
        conn = _open_conn()
        cur = conn.cursor()
        cur.execute(_DB_LOAD_SQL, (last_id, DB_LOAD_CHUNK))
        rows = cur.fetchall()
        conn.close()
        n_chunks += 1

        if not rows:
            break

        for row in rows:
            d = dict(zip(_DB_ALL_COLS, row))
            db_id = d["id"]
            db_by_id[db_id] = d

            if d["fragrantica_id"]:
                frag_id_index[str(d["fragrantica_id"])] = db_id

            bn = _norm_brand(d["brand"])
            brand_index.setdefault(bn, []).append((_norm(d["name"]), db_id))

        last_id = rows[-1][0]  # id is always first column
        if n_chunks % 5 == 0:
            print(f"  ... {len(db_by_id):,} loaded (last_id={last_id})")
        if len(rows) < DB_LOAD_CHUNK:
            break

    return db_by_id, frag_id_index, brand_index


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def find_match(
    name: str,
    brand: str,
    frag_id_str: str,
    frag_id_index: dict,
    brand_index: dict,
) -> int | None:
    # 1. Exact fragrantica ID match
    if frag_id_str in frag_id_index:
        return frag_id_index[frag_id_str]

    # 2. Brand-scoped fuzzy name match
    bn = _norm_brand(brand)
    candidates = brand_index.get(bn, [])
    if not candidates:
        return None

    names = [c[0] for c in candidates]
    result = rfprocess.extractOne(
        _norm(name), names, scorer=fuzz.token_sort_ratio
    )
    if result and result[1] >= FUZZY_THRESHOLD:
        return candidates[result[2]][1]

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_notes(s) -> list[str]:
    """Parse pipe-separated note string → title-cased list."""
    if s is None or (isinstance(s, float) and s != s):
        return []
    return [n.strip().title() for n in str(s).split("|") if n.strip()]


def _parse_accords(s) -> list[str]:
    """Parse 'name:strength|name:strength' → list of names (no strengths)."""
    if s is None or (isinstance(s, float) and s != s):
        return []
    return [a.split(":")[0].strip() for a in str(s).split("|") if a.strip()]


def _longevity_label(b1: int, b2: int, b3: int, b4: int, b5: int) -> str | None:
    """Derive Strong/Medium/Light from Fragrantica longevity histogram."""
    total = b1 + b2 + b3 + b4 + b5
    if total < MIN_LONGEVITY_VOTES:
        return None
    strong_frac = (b4 + b5) / total
    light_frac = (b1 + b2) / total
    if strong_frac >= 0.50:
        return "Strong"
    if light_frac >= 0.55:
        return "Light"
    return "Medium"


def _int(val, default: int = 0) -> int:
    if val is None or (isinstance(val, float) and val != val):
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _float(val) -> float | None:
    if val is None or (isinstance(val, float) and val != val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# DB flush
# ---------------------------------------------------------------------------



def _flush(cur, updates: list[tuple[int, dict]]) -> None:
    """Bulk UPDATE using a single VALUES-based statement per column-group.

    All rows sharing the same set of columns are sent in one:
        UPDATE perfumes AS p SET col = t.v_col ...
        FROM (VALUES %s) AS t(id, v_col, ...)
        WHERE p.id = t.id
    No per-row round-trips; safe for remote DB with high latency.
    """
    by_cols: dict[frozenset, list] = {}
    for db_id, upd in updates:
        key = frozenset(upd.keys())
        by_cols.setdefault(key, []).append((db_id, upd))

    for col_set, rows in by_cols.items():
        cols = sorted(col_set)
        alias_list = ", ".join(f"v_{c}" for c in cols)
        set_clause = ", ".join(f"{c} = t.v_{c}" for c in cols)
        # First placeholder = DB id (int); rest = each column value with its cast
        type_template = "(%s::int" + "".join(
            f", %s::{_COL_CAST.get(c, 'text')}" for c in cols
        ) + ")"
        sql = (
            f"UPDATE perfumes AS p SET {set_clause} "
            f"FROM (VALUES %s) AS t(id, {alias_list}) "
            f"WHERE p.id = t.id"
        )
        data = [(db_id,) + tuple(upd[c] for c in cols) for db_id, upd in rows]
        execute_values(cur, sql, data, template=type_template, page_size=50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Match and count updates but do not write to DB")
    parser.add_argument("--csv", default=str(DEFAULT_CSV),
                        help="Path to perfumes.csv from ledecanteur dataset")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only N rows (for testing)")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"ERROR: CSV not found at {args.csv}")
        print("Download it with:")
        print("  kaggle datasets download ledecanteur/fragrantica-perfumes "
              "-f perfumes.csv -p data/kaggle_new --unzip")
        sys.exit(1)

    print("Loading DB perfumes into memory (paginated 10k chunks)...")
    t0 = time.time()
    db_by_id, frag_id_index, brand_index = load_db()
    elapsed = time.time() - t0
    print(f"  {len(db_by_id):,} perfumes loaded in {elapsed:.1f}s")
    print(f"  {len(frag_id_index):,} have fragrantica_id | "
          f"{len(brand_index):,} distinct brands indexed")

    print(f"\nReading CSV: {args.csv}")
    if args.limit:
        print(f"  (limiting to first {args.limit:,} rows)")
    if args.dry_run:
        print("  DRY RUN — no writes")

    # Counters
    n_rows = 0
    n_id_match = 0
    n_fuzzy_match = 0
    n_unmatched = 0
    upd_counts = {
        "rating_count": 0,
        "longevity": 0,
        "sillage": 0,
        "overall_rating": 0,
        "season_votes": 0,
        "notes": 0,
        "accords": 0,
        "fragrantica_id": 0,
        "longevity_label": 0,
    }

    # -----------------------------------------------------------------------
    # Phase 1: Process CSV → collect all updates in memory (no DB writes yet)
    # -----------------------------------------------------------------------
    all_updates: list[tuple[int, dict]] = []
    t_start = time.time()

    for chunk in pd.read_csv(args.csv, chunksize=5000, low_memory=False):
        for _, row in chunk.iterrows():
            n_rows += 1
            if args.limit and n_rows > args.limit:
                break

            frag_id_str = str(int(row["id"])) if not pd.isna(row["id"]) else ""

            id_match = frag_id_str in frag_id_index
            db_id = find_match(
                str(row["name"]),
                str(row["brand"]),
                frag_id_str,
                frag_id_index,
                brand_index,
            )

            if db_id is None:
                n_unmatched += 1
            elif id_match:
                n_id_match += 1
            else:
                n_fuzzy_match += 1

            if db_id is None:
                if n_rows % PROGRESS_EVERY == 0:
                    _log_progress(n_rows, n_id_match, n_fuzzy_match, n_unmatched,
                                  upd_counts, t_start)
                continue

            db_row = db_by_id[db_id]
            upd: dict = {}

            # --- rating_count ---
            vc = _int(row.get("vote_count"))
            if db_row["rating_count"] == 0 and vc > 0:
                upd["rating_count"] = vc
                upd_counts["rating_count"] += 1

            # --- community_longevity_rating ---
            long_b = [_int(row.get(f"longevity_b{i}")) for i in range(1, 6)]
            long_total = sum(long_b)
            long_avg = _float(row.get("longevity_avg"))
            if (db_row["community_longevity_rating"] == 3.0
                    and long_total >= 5
                    and long_avg is not None):
                upd["community_longevity_rating"] = long_avg
                upd_counts["longevity"] += 1

            # --- community_sillage_rating ---
            sil_b = [_int(row.get(f"sillage_b{i}")) for i in range(1, 5)]
            sil_total = sum(sil_b)
            sil_avg = _float(row.get("sillage_avg"))
            if (db_row["community_sillage_rating"] == 3.0
                    and sil_total >= 5
                    and sil_avg is not None):
                upd["community_sillage_rating"] = sil_avg
                upd_counts["sillage"] += 1

            # --- community_overall_rating ---
            rat_avg = _float(row.get("rating_avg"))
            if (db_row["community_overall_rating"] == 3.0
                    and vc > 0
                    and rat_avg is not None):
                upd["community_overall_rating"] = rat_avg
                upd_counts["overall_rating"] += 1

            # --- season votes (all 4 if currently all 0) ---
            if db_row["season_spring_votes"] == 0:
                sp = _int(row.get("spring"))
                su = _int(row.get("summer"))
                fa = _int(row.get("autumn"))
                wi = _int(row.get("winter"))
                if sp + su + fa + wi > 0:
                    upd["season_spring_votes"] = sp
                    upd["season_summer_votes"] = su
                    upd["season_fall_votes"] = fa
                    upd["season_winter_votes"] = wi
                    upd_counts["season_votes"] += 1

            # --- note pyramids (if top_notes empty) ---
            if db_row["top_notes_empty"]:
                top = _parse_notes(row.get("notes_top"))
                mid = _parse_notes(row.get("notes_middle"))
                base = _parse_notes(row.get("notes_base"))
                flat = _parse_notes(row.get("notes_flat"))
                effective_mid = mid if (top or mid or base) else flat
                if top or effective_mid or base:
                    upd["top_notes"] = PgJson(top)
                    upd["middle_notes"] = PgJson(effective_mid)
                    upd["base_notes"] = PgJson(base)
                    upd_counts["notes"] += 1

            # --- accords (if currently empty) ---
            if db_row["accords_empty"]:
                acc = _parse_accords(row.get("accords"))
                if acc:
                    upd["accords"] = PgJson(acc)
                    upd_counts["accords"] += 1

            # --- fragrantica_id (if not set) ---
            if not db_row["fragrantica_id"] and frag_id_str:
                upd["fragrantica_id"] = frag_id_str
                upd_counts["fragrantica_id"] += 1

            # --- community_longevity_label (derive from histogram if NULL) ---
            if db_row["community_longevity_label"] is None and long_total >= MIN_LONGEVITY_VOTES:
                label = _longevity_label(*long_b)
                if label:
                    upd["community_longevity_label"] = label
                    upd_counts["longevity_label"] += 1

            if upd:
                all_updates.append((db_id, upd))

            if n_rows % PROGRESS_EVERY == 0:
                _log_progress(n_rows, n_id_match, n_fuzzy_match, n_unmatched,
                              upd_counts, t_start)

        if args.limit and n_rows >= args.limit:
            break

    csv_elapsed = time.time() - t_start
    print(f"\nCSV done in {csv_elapsed:.0f}s — {len(all_updates):,} updates queued")

    # -----------------------------------------------------------------------
    # Phase 2: Write all updates through a single persistent connection
    # Each BATCH_SIZE rows commits once; on connection drop, reconnect and retry.
    # -----------------------------------------------------------------------
    if all_updates and not args.dry_run:
        print(f"Writing {len(all_updates):,} updates in {BATCH_SIZE}-row batches...")
        write_conn = _open_conn()
        write_cur = write_conn.cursor()
        written = 0

        for i in range(0, len(all_updates), BATCH_SIZE):
            batch = all_updates[i: i + BATCH_SIZE]
            for attempt in range(3):
                try:
                    _flush(write_cur, batch)
                    write_conn.commit()
                    # Ping to keep connection alive between batches
                    write_cur.execute("SELECT 1")
                    break
                except psycopg2.Error as exc:
                    if attempt >= 2:
                        raise
                    print(f"  [WARN] Reconnecting ({exc})...")
                    try:
                        write_conn.close()
                    except Exception:
                        pass
                    write_conn = _open_conn()
                    write_cur = write_conn.cursor()

            written += len(batch)
            if (i // BATCH_SIZE) % 20 == 0 or written == len(all_updates):
                print(f"  Wrote {written:,}/{len(all_updates):,} updates "
                      f"({100*written/len(all_updates):.0f}%)")

        write_conn.close()
        print("  Write phase complete.")

    total_elapsed = time.time() - t_start

    print(f"\n{'='*60}")
    print(f"DONE in {total_elapsed:.0f}s")
    print(f"{'='*60}")
    print(f"CSV rows processed:  {n_rows:,}")
    print(f"  ID-matched:        {n_id_match:,}")
    print(f"  Fuzzy-matched:     {n_fuzzy_match:,}")
    print(f"  Unmatched:         {n_unmatched:,}  "
          f"({100*n_unmatched/max(n_rows,1):.1f}%)")
    print(f"\nUpdates applied{' (dry-run, not written)' if args.dry_run else ''}:")
    for k, v in upd_counts.items():
        print(f"  {k:<28} {v:>7,}")


def _log_progress(
    n_rows: int,
    n_id: int,
    n_fuzz: int,
    n_un: int,
    counts: dict,
    t0: float,
) -> None:
    elapsed = time.time() - t0
    rate = n_rows / elapsed if elapsed > 0 else 0
    print(
        f"[{n_rows:>7,}] id={n_id:,} fuzz={n_fuzz:,} miss={n_un:,} "
        f"| rc={counts['rating_count']:,} long={counts['longevity']:,} "
        f"seas={counts['season_votes']:,} notes={counts['notes']:,} "
        f"| {rate:.0f} rows/s"
    )


if __name__ == "__main__":
    main()
