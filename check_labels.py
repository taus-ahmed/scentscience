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
checks = [
    ('Bleu De Chanel','Chanel'),
    ('No 5','Chanel'),
    ('Black Opium','Saint Laurent'),
    ('Hypnotic Poison','Dior'),
    ('Lost Cherry','Tom Ford'),
    ('La Vie Est Belle','Lancome'),
]
for name, brand in checks:
    cur.execute('SELECT name, brand, community_longevity_label FROM perfumes WHERE name ILIKE %s AND brand ILIKE %s LIMIT 1', (f'%{name}%', f'%{brand}%'))
    row = cur.fetchone()
    print(row if row else f'NOT FOUND: {name}')
cur.close()
conn.close()
