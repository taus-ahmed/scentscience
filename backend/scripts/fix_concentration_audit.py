"""
Data quality audit and fix for perfume concentration fields and longevity labels.

Steps:
  1. Audit — print distribution and mismatch counts
  2. Fix concentration — name-based inference (safe: name explicitly says EDP/EDT)
  3. Fix longevity labels — add Strong for known powerhouse houses/keywords
  4. Report — before/after summary
"""

import psycopg2
from pathlib import Path


def get_conn():
    env_path = Path(__file__).parent.parent.parent / '.env'
    db_url = ''
    for line in env_path.read_text().splitlines():
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=', 1)[1].strip().strip('"').replace('+asyncpg', '')
            break
    if not db_url:
        raise RuntimeError('.env has no DATABASE_URL')
    return psycopg2.connect(db_url)


def section(title):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print('='*60)


def run():
    conn = get_conn()
    cur = conn.cursor()

    # ------------------------------------------------------------------ #
    # STEP 1 — AUDIT
    # ------------------------------------------------------------------ #
    section('STEP 1: PRE-FIX AUDIT')

    cur.execute(
        'SELECT concentration, COUNT(*) FROM perfumes GROUP BY concentration ORDER BY COUNT(*) DESC'
    )
    rows = cur.fetchall()
    print('\nConcentration distribution (before):')
    for conc, cnt in rows:
        print(f'  {str(conc):20s}  {cnt:>8,}')

    cur.execute("""
        SELECT COUNT(*) FROM perfumes
        WHERE concentration = 'EDT'
          AND (name ILIKE '%Eau de Parfum%' OR name ILIKE '% EDP %' OR name ILIKE '% EDP')
          AND name NOT ILIKE '%Eau de Toilette%'
          AND name NOT ILIKE '%Eau de Parfum et de Toilette%'
    """)
    edt_to_edp_count = cur.fetchone()[0]
    print(f'\nEDT->EDP mismatches (name says Eau de Parfum/EDP): {edt_to_edp_count:,}')

    cur.execute("""
        SELECT id, name, brand, concentration FROM perfumes
        WHERE concentration = 'EDT'
          AND (name ILIKE '%Eau de Parfum%' OR name ILIKE '% EDP %' OR name ILIKE '% EDP')
          AND name NOT ILIKE '%Eau de Toilette%'
          AND name NOT ILIKE '%Eau de Parfum et de Toilette%'
        LIMIT 20
    """)
    samples = cur.fetchall()
    print('\nSample EDT->EDP mismatches (up to 20):')
    for pid, name, brand, conc in samples:
        print(f'  [{pid}] {brand} - {name} (stored: {conc})')

    cur.execute("""
        SELECT COUNT(*) FROM perfumes
        WHERE concentration = 'EDP'
          AND (name ILIKE '%Eau de Toilette%' OR name ILIKE '% EDT %' OR name ILIKE '% EDT')
          AND name NOT ILIKE '%Eau de Parfum%'
    """)
    edp_to_edt_count = cur.fetchone()[0]
    print(f'\nEDP->EDT mismatches (name says Eau de Toilette/EDT): {edp_to_edt_count:,}')

    cur.execute("""
        SELECT COUNT(*) FROM perfumes
        WHERE (concentration IS NULL OR concentration = '')
          AND (name ILIKE '%Eau de Parfum%' OR name ILIKE '%Eau de Toilette%'
               OR name ILIKE '% EDP%' OR name ILIKE '% EDT%'
               OR name ILIKE '%Extrait%' OR name ILIKE '%Parfum%')
    """)
    null_fixable = cur.fetchone()[0]
    print(f'NULL/empty concentration with name hint:          {null_fixable:,}')

    # ------------------------------------------------------------------ #
    # STEP 2 — FIX CONCENTRATIONS
    # ------------------------------------------------------------------ #
    section('STEP 2: FIX CONCENTRATIONS')

    # EDT → EDP
    cur.execute("""
        UPDATE perfumes SET concentration = 'EDP'
        WHERE concentration = 'EDT'
          AND (name ILIKE '%Eau de Parfum%' OR name ILIKE '% EDP %' OR name ILIKE '% EDP')
          AND name NOT ILIKE '%Eau de Toilette%'
          AND name NOT ILIKE '%Eau de Parfum et de Toilette%'
    """)
    edt_to_edp_fixed = cur.rowcount
    print(f'EDT -> EDP fixes applied: {edt_to_edp_fixed:,}')

    # EDP → EDT
    cur.execute("""
        UPDATE perfumes SET concentration = 'EDT'
        WHERE concentration = 'EDP'
          AND (name ILIKE '%Eau de Toilette%' OR name ILIKE '% EDT %' OR name ILIKE '% EDT')
          AND name NOT ILIKE '%Eau de Parfum%'
    """)
    edp_to_edt_fixed = cur.rowcount
    print(f'EDP -> EDT fixes applied: {edp_to_edt_fixed:,}')

    # NULL → EDP (name says Eau de Parfum)
    cur.execute("""
        UPDATE perfumes SET concentration = 'EDP'
        WHERE (concentration IS NULL OR concentration = '')
          AND (name ILIKE '%Eau de Parfum%' OR name ILIKE '% EDP %' OR name ILIKE '% EDP')
          AND name NOT ILIKE '%Eau de Toilette%'
    """)
    null_to_edp = cur.rowcount
    print(f'NULL -> EDP fixes applied:  {null_to_edp:,}')

    # NULL → EDT (name says Eau de Toilette)
    cur.execute("""
        UPDATE perfumes SET concentration = 'EDT'
        WHERE (concentration IS NULL OR concentration = '')
          AND (name ILIKE '%Eau de Toilette%' OR name ILIKE '% EDT %' OR name ILIKE '% EDT')
          AND name NOT ILIKE '%Eau de Parfum%'
    """)
    null_to_edt = cur.rowcount
    print(f'NULL -> EDT fixes applied:  {null_to_edt:,}')

    # NULL → Extrait (name says Extrait)
    cur.execute("""
        UPDATE perfumes SET concentration = 'Extrait'
        WHERE (concentration IS NULL OR concentration = '')
          AND (name ILIKE '%Extrait de Parfum%' OR name ILIKE '% Extrait%')
    """)
    null_to_extrait = cur.rowcount
    print(f'NULL -> Extrait fixes:      {null_to_extrait:,}')

    # EDT → Extrait (name explicitly says Extrait)
    cur.execute("""
        UPDATE perfumes SET concentration = 'Extrait'
        WHERE concentration = 'EDT'
          AND (name ILIKE '%Extrait de Parfum%' OR name ILIKE '% Extrait%')
          AND name NOT ILIKE '%Eau de Toilette%'
    """)
    edt_to_extrait = cur.rowcount
    print(f'EDT -> Extrait fixes:       {edt_to_extrait:,}')

    # EDP → Extrait (name explicitly says Extrait)
    cur.execute("""
        UPDATE perfumes SET concentration = 'Extrait'
        WHERE concentration = 'EDP'
          AND (name ILIKE '%Extrait de Parfum%' OR name ILIKE '% Extrait%')
          AND name NOT ILIKE '%Eau de Parfum%'
    """)
    edp_to_extrait = cur.rowcount
    print(f'EDP -> Extrait fixes:       {edp_to_extrait:,}')

    total_conc_fixed = (
        edt_to_edp_fixed + edp_to_edt_fixed
        + null_to_edp + null_to_edt + null_to_extrait
        + edt_to_extrait + edp_to_extrait
    )
    print(f'\nTotal concentration rows updated: {total_conc_fixed:,}')

    # ------------------------------------------------------------------ #
    # STEP 3 — FIX LONGEVITY LABELS (known powerhouse houses/keywords)
    # ------------------------------------------------------------------ #
    section('STEP 3: FIX STRONG LONGEVITY LABELS')

    # Count existing Strong labels before
    cur.execute("SELECT COUNT(*) FROM perfumes WHERE community_longevity_label = 'Strong'")
    strong_before = cur.fetchone()[0]
    print(f'Strong labels before: {strong_before:,}')

    cur.execute("""
        UPDATE perfumes SET community_longevity_label = 'Strong'
        WHERE community_longevity_label IS NULL
          AND (
              brand ILIKE '%Mancera%'
           OR brand ILIKE '%Xerjoff%'
           OR brand ILIKE '%Roja%'
           OR brand ILIKE '%Amouage%'
           OR brand ILIKE '%Initio%'
           OR brand ILIKE '%Maison Francis Kurkdjian%'
           OR brand ILIKE '%Parfums de Marly%'
           OR brand ILIKE '%Orto Parisi%'
           OR brand ILIKE '%Nishane%'
           OR brand ILIKE '%Roja Parfums%'
           OR brand ILIKE '%Kilian%'
           OR brand ILIKE '%By Kilian%'
           OR name  ILIKE '%Baccarat Rouge%'
           OR name  ILIKE '%Oud Wood%'
           OR name  ILIKE '%Cedrat Boise%'
           OR name  ILIKE '%Black Orchid%'
           OR name  ILIKE '%Coco Noir%'
           OR name  ILIKE '%Angel%'
           OR name  ILIKE '% Intense%'
           OR name  ILIKE '% Absolu%'
           OR name  ILIKE '%Extrait de Parfum%'
           OR name  ILIKE '%Extrait%'
          )
    """)
    strong_added = cur.rowcount
    print(f'Strong labels added:  {strong_added:,}')

    cur.execute("SELECT COUNT(*) FROM perfumes WHERE community_longevity_label = 'Strong'")
    strong_after = cur.fetchone()[0]
    print(f'Strong labels after:  {strong_after:,}')

    # ------------------------------------------------------------------ #
    # STEP 4 — POST-FIX REPORT
    # ------------------------------------------------------------------ #
    section('STEP 4: POST-FIX REPORT')

    cur.execute(
        'SELECT concentration, COUNT(*) FROM perfumes GROUP BY concentration ORDER BY COUNT(*) DESC'
    )
    rows = cur.fetchall()
    print('\nConcentration distribution (after):')
    for conc, cnt in rows:
        print(f'  {str(conc):20s}  {cnt:>8,}')

    cur.execute(
        'SELECT community_longevity_label, COUNT(*) FROM perfumes '
        'GROUP BY community_longevity_label ORDER BY COUNT(*) DESC'
    )
    rows = cur.fetchall()
    print('\nLongevity label distribution (after):')
    for label, cnt in rows:
        print(f'  {str(label):20s}  {cnt:>8,}')

    print('\n--- SUMMARY ---')
    print(f'  EDT -> EDP:          {edt_to_edp_fixed:>6,}')
    print(f'  EDP -> EDT:          {edp_to_edt_fixed:>6,}')
    print(f'  NULL -> EDP:         {null_to_edp:>6,}')
    print(f'  NULL -> EDT:         {null_to_edt:>6,}')
    print(f'  NULL -> Extrait:     {null_to_extrait:>6,}')
    print(f'  EDT  -> Extrait:     {edt_to_extrait:>6,}')
    print(f'  EDP  -> Extrait:     {edp_to_extrait:>6,}')
    print(f'  TOTAL conc fixes:   {total_conc_fixed:>6,}')
    print(f'  Strong added:       {strong_added:>6,}')
    print(f'  Strong total after: {strong_after:>6,}')

    conn.commit()
    print('\nAll changes committed.')
    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
