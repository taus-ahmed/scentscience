import psycopg2
from pathlib import Path

env_path = Path('E:/scentscience/.env')
db_url = ''
for line in env_path.read_text().splitlines():
    if line.startswith('DATABASE_URL'):
        db_url = line.split('=', 1)[1].strip().strip('"').replace('+asyncpg', '')
        break

conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Fix Cedrat Boise concentration + label
cur.execute("UPDATE perfumes SET concentration='EDP', community_longevity_label='Strong' WHERE name ILIKE '%Cedrat Boise%' AND brand ILIKE '%Mancera%'")
print(f'Cedrat Boise: {cur.rowcount} rows')

# Fix Boss Bottled Intense
cur.execute("UPDATE perfumes SET concentration='EDP', community_longevity_label='Strong' WHERE name ILIKE '%Bottled Intense%' AND brand ILIKE '%Boss%'")
print(f'Boss Bottled Intense: {cur.rowcount} rows')

conn.commit()
cur.close()
conn.close()
print('Done')
