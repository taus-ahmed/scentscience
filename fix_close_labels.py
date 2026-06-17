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

targets = [
    ('Bleu De Chanel', 'Chanel'),
    ('No 5', 'Chanel'),
    ('Black Opium', 'Yves Saint Laurent'),
    ('Hypnotic Poison', 'Dior'),
    ('Lost Cherry', 'Tom Ford'),
    ('La Nuit Tresor', 'Lancome'),
    ('Black Orchid', 'Tom Ford'),
    ('La Vie Est Belle', 'Lancome'),
    ('Eros Flame', 'Versace'),
    ('L Homme Libre', 'Yves Saint Laurent'),
    ('Angel', 'Mugler'),
    ('Alien', 'Mugler'),
    ('Flowerbomb', 'Viktor'),
]

for name, brand in targets:
    cur.execute(
        "UPDATE perfumes SET community_longevity_label='Strong' WHERE name ILIKE %s AND brand ILIKE %s AND (community_longevity_label IS NULL OR community_longevity_label != 'Strong')",
        (f'%{name}%', f'%{brand}%')
    )
    print(f'{name} ({brand}): {cur.rowcount} rows updated')

conn.commit()
cur.close()
conn.close()
print('Done')
