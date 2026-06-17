import psycopg2, time, os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv("../.env")
url = os.environ["DATABASE_URL"]

sql_keyset = """
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

def test_chunk(label, last_id):
    t = time.time()
    conn = psycopg2.connect(url, connect_timeout=30)
    cur = conn.cursor()
    cur.execute(sql_keyset, (last_id, 5000))
    rows = cur.fetchall()
    conn.close()
    elapsed = time.time() - t
    print(f"{label}: {len(rows)} rows in {elapsed:.2f}s  ({len(rows)/elapsed:.0f} rows/s)")
    return rows[-1][0] if rows else last_id

last_id = 0
last_id = test_chunk("Chunk 1 (id > 0)", last_id)
last_id = test_chunk(f"Chunk 2 (id > {last_id})", last_id)
last_id = test_chunk(f"Chunk 3 (id > {last_id})", last_id)

# Jump to middle
last_id = test_chunk("Chunk ~10 (id > 50000)", 50000)
last_id = test_chunk(f"Chunk ~20 (id > 100000)", 100000)
