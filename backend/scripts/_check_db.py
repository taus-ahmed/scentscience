import psycopg2, os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv("../.env")
conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM perfumes WHERE community_longevity_rating != 3.0")
print("Non-default longevity_rating:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM perfumes WHERE season_spring_votes > 0")
print("Has season votes:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM perfumes WHERE community_longevity_label IS NOT NULL")
print("Has longevity label:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM perfumes WHERE fragrantica_id IS NOT NULL")
print("Has fragrantica_id:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM perfumes WHERE community_sillage_rating != 3.0")
print("Non-default sillage_rating:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM perfumes WHERE community_overall_rating != 3.0")
print("Non-default overall_rating:", cur.fetchone()[0])

cur.execute("""
    SELECT name, brand, community_longevity_rating, season_spring_votes,
           community_longevity_label, community_sillage_rating, fragrantica_id
    FROM perfumes WHERE name = 'Aventus' AND brand = 'Creed'
""")
row = cur.fetchone()
if row:
    print(f"Aventus: long={row[2]:.2f} sil={row[5]:.2f} seas={row[3]} label={row[4]} frag_id={row[6]}")

cur.execute("""
    SELECT name, brand, community_longevity_rating, season_spring_votes,
           community_longevity_label, fragrantica_id
    FROM perfumes WHERE name = 'Sauvage' AND brand = 'Dior'
""")
row = cur.fetchone()
if row:
    print(f"Sauvage: long={row[2]:.2f} seas={row[3]} label={row[4]} frag_id={row[5]}")

conn.close()
