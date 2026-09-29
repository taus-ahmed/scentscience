"""004 - longevity data cleanup.

Replaces the synthetic default 3.0 for longevity/sillage with NULL for
rows that have no real community signal, so XGBoost treats them as truly
missing rather than spuriously centred.

Governance:
  - Never touches rows that already have a real longevity label.
  - Adds a longevity_data_quality column to record source of each value.
  - Dry-run by default; --write to apply.
  - Safety gate: refuses Railway without V2_ALLOW_REMOTE=yes.

Usage:
    set DATABASE_URL=postgresql://...@localhost/decode_v2
    cd backend
    python scripts/v2/004_longevity.py          # dry-run
    python scripts/v2/004_longevity.py --write  # apply

Decision rationale (from V2 plan):
  - 63,183 rows carry the default 3.0 — these are noise, not signal.
  - 34,055 rows have a real Light/Medium/Strong community label.
  - XGBoost handles NULL natively; missing becomes its own signal.
  - Rating features keep a small weight; the ablation measures how much.
"""

import os
import sys
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
parser.add_argument("--write", action="store_true")
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
        ADD COLUMN IF NOT EXISTS longevity_data_quality varchar(20) DEFAULT NULL;
""")
print("  Added longevity_data_quality column (idempotent).")

# ── Step 2: Audit before ──────────────────────────────────────────────────────

print("\n=== Step 2: Before state ===")

cur.execute("""
    SELECT
        CASE
            WHEN community_longevity_label IS NOT NULL AND community_longevity_label != ''
                THEN 'real_label'
            WHEN rating_count >= 10
                THEN 'has_ratings_no_label'
            WHEN community_longevity_rating = 3.0 AND rating_count < 10
                THEN 'default_3.0_no_ratings'
            ELSE 'other'
        END AS category,
        count(*) AS cnt,
        round(avg(community_longevity_rating)::numeric, 2) AS avg_longevity
    FROM perfumes
    GROUP BY 1
    ORDER BY 2 DESC
""")
rows = cur.fetchall()
total = sum(r["cnt"] for r in rows)
print(f"  Total perfumes: {total:,}\n")
print(f"  {'Category':<35} {'Count':>8}  {'Avg longevity':>14}")
print(f"  {'-'*35} {'-'*8}  {'-'*14}")
for r in rows:
    print(f"  {r['category']:<35} {r['cnt']:>8,}  {r['avg_longevity']:>14}")

# ── Step 3: Identify rows to NULL-ify ─────────────────────────────────────────

print("\n=== Step 3: Identify rows with synthetic defaults ===")

# A row is synthetic if:
#   community_longevity_rating = 3.0  AND
#   community_longevity_label IS NULL  AND
#   rating_count < 10  (fewer than 10 raters — very thin real signal)

cur.execute("""
    SELECT count(*) AS cnt
    FROM perfumes
    WHERE community_longevity_rating = 3.0
      AND (community_longevity_label IS NULL OR community_longevity_label = '')
      AND (rating_count < 10 OR rating_count IS NULL)
""")
synthetic_count = cur.fetchone()["cnt"]
print(f"  Rows with synthetic default longevity 3.0 (no label, <10 raters): {synthetic_count:,}")

cur.execute("""
    SELECT count(*) AS cnt
    FROM perfumes
    WHERE community_sillage_rating = 3.0
      AND (rating_count < 10 OR rating_count IS NULL)
""")
sillage_default_count = cur.fetchone()["cnt"]
print(f"  Rows with synthetic default sillage 3.0 (<10 raters)            : {sillage_default_count:,}")

# ── Step 4: Sample ───────────────────────────────────────────────────────────

print("\n=== Step 4: Sample (10 rows to NULL, 10 to keep) ===")

cur.execute("""
    SELECT name, brand, community_longevity_rating, community_longevity_label, rating_count
    FROM perfumes
    WHERE community_longevity_rating = 3.0
      AND (community_longevity_label IS NULL OR community_longevity_label = '')
      AND (rating_count < 10 OR rating_count IS NULL)
    ORDER BY rating_count DESC NULLS LAST
    LIMIT 10
""")
print("  Synthetic rows (will become NULL):")
for r in cur.fetchall():
    print(f"    {r['name'][:40]:<40} | {r['brand'][:20]:<20} | longevity={r['community_longevity_rating']} | label={r['community_longevity_label']} | ratings={r['rating_count']}")

cur.execute("""
    SELECT name, brand, community_longevity_rating, community_longevity_label, rating_count
    FROM perfumes
    WHERE community_longevity_label IS NOT NULL AND community_longevity_label != ''
    ORDER BY rating_count DESC
    LIMIT 10
""")
print("\n  Real-label rows (untouched):")
for r in cur.fetchall():
    print(f"    {r['name'][:40]:<40} | {r['brand'][:20]:<20} | longevity={r['community_longevity_rating']} | label={r['community_longevity_label']} | ratings={r['rating_count']}")

# ── Step 5: Write ────────────────────────────────────────────────────────────

if args.write:
    print("\n=== Step 5: Writing ===")

    # Tag rows with real labels
    cur.execute("""
        UPDATE perfumes
           SET longevity_data_quality = 'community_label'
         WHERE community_longevity_label IS NOT NULL
           AND community_longevity_label != ''
           AND longevity_data_quality IS NULL
    """)
    tagged_label = cur.rowcount
    print(f"  Tagged 'community_label': {tagged_label:,}")

    # Tag rows with good rating coverage but no explicit label
    cur.execute("""
        UPDATE perfumes
           SET longevity_data_quality = 'rating_based'
         WHERE (community_longevity_label IS NULL OR community_longevity_label = '')
           AND rating_count >= 10
           AND longevity_data_quality IS NULL
    """)
    tagged_rating = cur.rowcount
    print(f"  Tagged 'rating_based'   : {tagged_rating:,}")

    # NULL-ify synthetic defaults
    cur.execute("""
        UPDATE perfumes
           SET community_longevity_rating = NULL,
               community_sillage_rating   = NULL,
               longevity_data_quality     = 'missing'
         WHERE community_longevity_rating = 3.0
           AND (community_longevity_label IS NULL OR community_longevity_label = '')
           AND (rating_count < 10 OR rating_count IS NULL)
    """)
    nullified = cur.rowcount
    print(f"  Set to NULL             : {nullified:,}")

    conn.commit()

    # Report after
    print("\n=== After state ===")
    cur.execute("""
        SELECT longevity_data_quality, count(*), round(avg(community_longevity_rating)::numeric, 2) AS avg
        FROM perfumes
        GROUP BY 1
        ORDER BY 2 DESC
    """)
    for r in cur.fetchall():
        print(f"  {str(r['longevity_data_quality']):<20} {r['count']:>8,}  avg={r['avg']}")

else:
    print("\nDRY-RUN — no writes. Pass --write to apply.")
    conn.rollback()

cur.close()
conn.close()
print("\nDone.")
