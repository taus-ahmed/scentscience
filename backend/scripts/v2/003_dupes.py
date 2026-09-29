"""003 - dupes: inspired_by field, perfume_role, similarity scoring.

Idempotent — safe to re-run. Adds two columns, then computes similarity
between clone-house perfumes and their likely originals.

Governance:
  - Never modifies existing rows without a printed diff + approval step.
  - Only adds columns; never drops or alters existing columns.
  - Dry-run mode (default) prints proposals without writing.

Usage:
    set DATABASE_URL=postgresql://...@localhost/decode_v2
    cd backend
    python scripts/v2/003_dupes.py             # dry-run, print proposals
    python scripts/v2/003_dupes.py --write     # apply approved proposals

Safety gate: refuses to run against rlwy.net/railway without V2_ALLOW_REMOTE=yes.
"""

import os
import sys
import re
import json
import argparse
from urllib.parse import urlparse

# ── Safety gate ───────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    sys.exit(1)

host = urlparse(DATABASE_URL).hostname or ""
print(f"\nDATABASE_URL host: {host}\n")

IS_RAILWAY = any(p in host for p in ["rlwy.net", "railway.app", "railway.internal"])
if IS_RAILWAY and os.environ.get("V2_ALLOW_REMOTE", "").lower() != "yes":
    print("REFUSED: pointing at Railway. Set V2_ALLOW_REMOTE=yes to proceed.")
    sys.exit(1)

# ── Args ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--write", action="store_true", help="Apply proposals (default: dry-run)")
args = parser.parse_args()

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: pip install psycopg2-binary")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── Step 1: DDL ───────────────────────────────────────────────────────────────

print("=== Step 1: DDL ===")

cur.execute("""
    ALTER TABLE perfumes
        ADD COLUMN IF NOT EXISTS perfume_role    varchar(10)  DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS inspired_by_id  integer      DEFAULT NULL
            REFERENCES perfumes(id) ON DELETE SET NULL;
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_perfumes_inspired_by_id ON perfumes (inspired_by_id) WHERE inspired_by_id IS NOT NULL")
print("  columns: perfume_role, inspired_by_id — added (idempotent)")

# ── Step 2: Load data ─────────────────────────────────────────────────────────

print("\n=== Step 2: Load perfumes for similarity ===")

cur.execute("""
    SELECT id, name, brand, brand_canonical,
           accords, top_notes, middle_notes, base_notes,
           community_overall_rating, rating_count,
           perfume_role, inspired_by_id
    FROM perfumes
    WHERE rating_count >= 5
    ORDER BY rating_count DESC
""")
rows = cur.fetchall()
print(f"  Loaded {len(rows):,} perfumes with >=5 ratings.")

# Index by id for fast lookup
by_id = {r["id"]: r for r in rows}

# ── Step 3: Similarity function ───────────────────────────────────────────────

def _notes_set(row):
    """All notes as a lowercase set."""
    out = set()
    for col in ("top_notes", "middle_notes", "base_notes"):
        val = row.get(col) or []
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                val = []
        out.update(n.lower().strip() for n in val if n)
    return out

def _accords_set(row):
    val = row.get("accords") or []
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:
            val = []
    return {a.lower().strip() for a in val if a}

def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)

def similarity(p1, p2) -> float:
    """Combined similarity: 60% notes, 40% accords."""
    n1, n2 = _notes_set(p1), _notes_set(p2)
    a1, a2 = _accords_set(p1), _accords_set(p2)
    note_sim = jaccard(n1, n2) if (n1 or n2) else 0.0
    accord_sim = jaccard(a1, a2) if (a1 or a2) else 0.0
    return 0.6 * note_sim + 0.4 * accord_sim

# ── Step 4: Known clone houses ────────────────────────────────────────────────

# Brands known to produce clones / inspired-by perfumes.
# Key = canonical brand name (from 001_brand_aliases), value = label for reporting.
CLONE_HOUSES = {
    "Afnan":           "budget Arabic clone house",
    "Armaf":           "Pakistani clone house",
    "Lattafa":         "Dubai clone house",
    "Al Haramain":     "Arabic clone house",
    "Fragrance World": "clone house",
    "Ard Al Zaafaran": "clone house",
    "Ahmed Al Maghribi": "clone house",
    "Paris Corner":    "clone house",
    "Milestone":       "clone house",
}

def _canonical_brand(row):
    return row.get("brand_canonical") or row.get("brand") or ""

# Separate clone-house perfumes from potential originals
clone_candidates = [r for r in rows if _canonical_brand(r) in CLONE_HOUSES]
original_candidates = [r for r in rows if _canonical_brand(r) not in CLONE_HOUSES and r["rating_count"] >= 20]

print(f"  Clone-house perfumes with >=5 ratings : {len(clone_candidates):,}")
print(f"  Potential originals with >=20 ratings : {len(original_candidates):,}")

# ── Step 5: Match each clone to its best original ─────────────────────────────

print("\n=== Step 3: Compute clone→original matches (top 50 by rating) ===")

# Only process the top 50 clone candidates (by rating_count) to keep this fast.
top_clones = sorted(clone_candidates, key=lambda r: -(r["rating_count"] or 0))[:50]

proposals = []  # {clone_id, clone_name, clone_brand, original_id, original_name, original_brand, score}

for clone in top_clones:
    best_score = 0.0
    best_original = None

    # Skip if notes/accords are empty — can't compute similarity
    if not _notes_set(clone) and not _accords_set(clone):
        continue

    for orig in original_candidates:
        sc = similarity(clone, orig)
        if sc > best_score:
            best_score = sc
            best_original = orig

    if best_original and best_score >= 0.30:
        proposals.append({
            "clone_id":       clone["id"],
            "clone_name":     clone["name"],
            "clone_brand":    _canonical_brand(clone),
            "original_id":    best_original["id"],
            "original_name":  best_original["name"],
            "original_brand": _canonical_brand(best_original),
            "score":          round(best_score, 3),
            "clone_ratings":  clone["rating_count"],
            "orig_ratings":   best_original["rating_count"],
        })

proposals.sort(key=lambda x: -x["score"])

# ── Step 6: Print proposals ───────────────────────────────────────────────────

print(f"\n{'Clone':<35} {'Brand':<18} → {'Original':<35} {'Brand':<18} {'Score':>6} {'Ratings':>8}")
print("-" * 125)
for p in proposals[:30]:
    print(
        f"{p['clone_name'][:34]:<35} {p['clone_brand'][:17]:<18} → "
        f"{p['original_name'][:34]:<35} {p['original_brand'][:17]:<18} "
        f"{p['score']:>6.3f}  {p['clone_ratings']:>4}/{p['orig_ratings']:<4}"
    )

if len(proposals) > 30:
    print(f"  … and {len(proposals) - 30} more")

print(f"\nTotal proposals: {len(proposals)}")

# ── Step 7: Write (if --write) ────────────────────────────────────────────────

if args.write:
    print("\n=== Step 4: Writing proposals ===")
    written = 0
    for p in proposals:
        cur.execute("""
            UPDATE perfumes
               SET perfume_role = 'clone',
                   inspired_by_id = %s
             WHERE id = %s
               AND (perfume_role IS NULL OR perfume_role = 'clone')
        """, (p["original_id"], p["clone_id"]))
        written += cur.rowcount

        # Mark originals that now have at least one clone
        cur.execute("""
            UPDATE perfumes
               SET perfume_role = 'original'
             WHERE id = %s
               AND (perfume_role IS NULL OR perfume_role = 'original')
        """, (p["original_id"],))

    conn.commit()
    print(f"  Written {written} clone links.")

    # Report
    cur.execute("SELECT perfume_role, count(*) FROM perfumes GROUP BY perfume_role ORDER BY 2 DESC")
    print("\n  perfume_role distribution:")
    for row in cur.fetchall():
        print(f"    {row['perfume_role'] or 'NULL':<12}  {row['count']:>8,}")
else:
    print("\nDRY-RUN — no writes made. Pass --write to apply.")
    conn.rollback()

cur.close()
conn.close()
print("\nDone.")
