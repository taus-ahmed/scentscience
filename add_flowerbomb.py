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

cur.execute("SELECT COUNT(*) FROM perfumes WHERE name ILIKE '%Flowerbomb%' AND brand ILIKE '%Viktor%'")
if cur.fetchone()[0] > 0:
    print('Flowerbomb already exists, skipping')
else:
    cur.execute('''
        INSERT INTO perfumes (name, brand, concentration, top_notes, middle_notes, base_notes,
            accords, community_longevity_label, source_count, gender_vote)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ''', (
        'Flowerbomb', 'Viktor&Rolf', 'EDP',
        'Tea, Bergamot, Osmanthus',
        'Orchid, Freesia, Rose, Jasmine',
        'Patchouli, Musk',
        'floral, sweet, powdery, warm spicy',
        'Strong', 4, 'feminine'
    ))
    print(f'Flowerbomb inserted: {cur.rowcount} row')

conn.commit()
cur.close()
conn.close()
print('Done')
