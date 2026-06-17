import psycopg2, os
from pathlib import Path

env_path = Path('E:/scentscience/.env')
db_url = ''
for line in env_path.read_text().splitlines():
    if line.startswith('DATABASE_URL'):
        db_url = line.split('=', 1)[1].strip().strip('"').replace('+asyncpg', '')
        break

print('Connecting to DB...')
conn = psycopg2.connect(db_url)
cur = conn.cursor()
targets = ['Angel', 'L Homme Libre', 'Alien', 'Black Orchid', 'La Nuit Tresor']
for name in targets:
    cur.execute("UPDATE perfumes SET community_longevity_label='Strong' WHERE name ILIKE %s AND (community_longevity_label IS NULL OR community_longevity_label != 'Strong')", (f'%{name}%',))
    print(f'{name}: {cur.rowcount} rows updated')
conn.commit()
cur.close()
conn.close()
print('Done')
