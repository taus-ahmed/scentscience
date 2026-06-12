# %% [markdown]
# # FragDB v5.3: Multilingual Data Exploration Guide
#
# This notebook explores the FragDB v5.3 fragrance database sample with **23 language translations**.
#
# **Dataset contains 6 relational CSV files:**
# - `fragrances.csv` - 10 fragrances, 30 fields
# - `brands.csv` - 10 brands, 54 fields (22 lang translations)
# - `perfumers.csv` - 10 perfumers, 39 fields (22 lang translations)
# - `notes.csv` - 10 notes, 55 fields (22 lang translations)
# - `accords.csv` - 10 accords, 27 fields (22 lang translations)
# - `translations.csv` - 34 vocabulary entries, 25 fields (23 languages)
#
# **Full database:** 130,086 fragrances, 7,776 brands, 2,960 perfumers, 2,517 notes, 92 accords at [fragdb.net](https://fragdb.net)

# %% [markdown]
# ## 1. Setup & Data Loading

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from collections import Counter

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 100)

# %%
# Load all 6 files (v5.3)
fragrances = pd.read_csv('/kaggle/input/fragdb-fragrance-database/fragrances.csv', sep='|')
brands = pd.read_csv('/kaggle/input/fragdb-fragrance-database/brands.csv', sep='|')
perfumers = pd.read_csv('/kaggle/input/fragdb-fragrance-database/perfumers.csv', sep='|')
notes = pd.read_csv('/kaggle/input/fragdb-fragrance-database/notes.csv', sep='|')
accords = pd.read_csv('/kaggle/input/fragdb-fragrance-database/accords.csv', sep='|')
translations = pd.read_csv('/kaggle/input/fragdb-fragrance-database/translations.csv', sep='|')

print("Data loaded successfully!")
for name, df in [('Fragrances', fragrances), ('Brands', brands), ('Perfumers', perfumers),
                  ('Notes', notes), ('Accords', accords), ('Translations', translations)]:
    print(f"  {name}: {df.shape[0]} rows x {df.shape[1]} columns")

# %% [markdown]
# ## 2. Translations — The Key to Multilingual Data

# %%
print("TRANSLATIONS.CSV — Vocabulary for gender & voting labels")
print("=" * 60)
print(f"Entries: {len(translations)}, Languages: {len(translations.columns) - 3} + EN")
print()
print(translations[['id', 'section', 'en', 'ru', 'ja', 'de']].to_string())

# %%
# Build translation lookup
trans = translations.set_index('id')

# Translate a gender value
example_gender = fragrances['gender'].iloc[0]
print(f"Gender ID: {example_gender}")
print(f"  English: {trans.loc[example_gender, 'en']}")
print(f"  Russian: {trans.loc[example_gender, 'ru']}")
print(f"  Japanese: {trans.loc[example_gender, 'ja']}")
print(f"  Arabic: {trans.loc[example_gender, 'ar']}")

# %% [markdown]
# ## 3. Fragrances — Main Database

# %%
print("FRAGRANCES.CSV — Column Overview (30 fields)")
print("=" * 60)
for i, col in enumerate(fragrances.columns, 1):
    non_null = fragrances[col].notna().sum()
    print(f"{i:2}. {col:<20} | {non_null}/{len(fragrances)} non-null")

# %%
# Gender with translations
print("\nGender Distribution (with Russian translation):")
for gender_id in fragrances['gender'].unique():
    count = (fragrances['gender'] == gender_id).sum()
    en = trans.loc[gender_id, 'en']
    ru = trans.loc[gender_id, 'ru']
    print(f"  {gender_id}: {en} / {ru} — {count} fragrances")

# %%
# Parse voting field with translations
def parse_votes_translated(value, lang='en'):
    if pd.isna(value) or not value:
        return {}
    result = {}
    for entry in str(value).split(';'):
        parts = entry.split(':')
        if len(parts) == 3:
            tid, votes, pct = parts
            label = trans.loc[tid, lang] if tid in trans.index else tid
            result[label] = {'votes': int(votes), 'pct': float(pct)}
    return result

# Example: appreciation in multiple languages
print("\nAppreciation for first fragrance:")
sample = fragrances.iloc[0]
print(f"  Raw: {str(sample['appreciation'])[:80]}...")
for lang in ['en', 'ru', 'ja', 'de']:
    parsed = parse_votes_translated(sample['appreciation'], lang)
    labels = ', '.join(f"{k}: {v['pct']}%" for k, v in parsed.items())
    print(f"  {lang}: {labels}")

# %% [markdown]
# ## 4. Notes Pyramid — Compact Format

# %%
# v5 pyramid format: level(note_id,opacity,weight;...)
print("NOTES PYRAMID — v5 Format")
print("=" * 60)
sample_pyramid = fragrances.iloc[0]['notes_pyramid']
print(f"Raw: {str(sample_pyramid)[:120]}...")

# Parse pyramid and join with notes.csv
notes_map = notes.set_index('id')
levels = re.findall(r'(\w+)\(([^)]+)\)', str(sample_pyramid))
for level_name, notes_str in levels:
    print(f"\n  {level_name.upper()}:")
    for note_entry in notes_str.split(';')[:5]:
        parts = note_entry.split(',')
        if len(parts) == 3:
            note_id, opacity, weight = parts
            if note_id in notes_map.index:
                row = notes_map.loc[note_id]
                en_name = row['name']
                ru_name = row.get('note_name_ru', '')
                ja_name = row.get('note_name_ja', '')
                print(f"    {note_id}: {en_name} / {ru_name} / {ja_name} (opacity={opacity}, weight={weight})")

# %% [markdown]
# ## 5. Brands — Multilingual

# %%
print("BRANDS — Country translations")
print("=" * 60)
print(brands[['id', 'name', 'country', 'country_ru', 'country_ja', 'country_ar']].to_string())

# %%
print("\nBRANDS — Main Activity translations")
print(brands[['name', 'main_activity', 'main_activity_ru', 'main_activity_ja']]].to_string())

# %% [markdown]
# ## 6. Accords — With Colors and Translations

# %%
print("ACCORDS — Multilingual names")
print("=" * 60)
print(accords[['id', 'name', 'name_ru', 'name_ja', 'name_de', 'bar_color', 'fragrance_count']].to_string())

# %%
# Visualize accords with actual colors
fig, ax = plt.subplots(figsize=(12, 6))
accords_sorted = accords.sort_values('fragrance_count', ascending=True)
bars = ax.barh(accords_sorted['name'], accords_sorted['fragrance_count'],
               color=accords_sorted['bar_color'].tolist(), edgecolor='black')
ax.set_xlabel('Number of Fragrances')
ax.set_title('Accords by Fragrance Count (with display colors)')
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 7. Perfumers — Status Translations

# %%
print("PERFUMERS — Status translations")
print("=" * 60)
print(perfumers[['id', 'name', 'status', 'status_ru', 'perfumes_count']].to_string())

# Check name transliterations
print("\nName transliterations (ru, uk, ja):")
for _, row in perfumers.iterrows():
    ru = row.get('perfumer_name_ru', '')
    if pd.notna(ru) and ru:
        print(f"  {row['name']} → ru: {ru}")

# %% [markdown]
# ## 8. Joining Tables

# %%
# Join fragrances with brands
fragrances['brand_id'] = fragrances['brand'].str.split(';').str[1]
df = fragrances.merge(brands, left_on='brand_id', right_on='id', suffixes=('', '_brand'))

# Add translated gender
df['gender_ru'] = df['gender'].map(lambda x: trans.loc[x, 'ru'] if x in trans.index else x)

print("Joined fragrances + brands (with Russian translations):")
print(df[['name', 'name_brand', 'country_ru', 'gender_ru']].to_string(index=False))

# %% [markdown]
# ## 9. Summary

# %%
print("=" * 60)
print("FRAGDB v5.3 DATASET SUMMARY")
print("=" * 60)
print(f"""
SAMPLE DATASET (6 files, 23 languages):
  - Fragrances: {len(fragrances)} records, {len(fragrances.columns)} fields
  - Brands: {len(brands)} records, {len(brands.columns)} fields
  - Perfumers: {len(perfumers)} records, {len(perfumers.columns)} fields
  - Notes: {len(notes)} records, {len(notes.columns)} fields
  - Accords: {len(accords)} records, {len(accords.columns)} fields
  - Translations: {len(translations)} records, {len(translations.columns)} fields

FULL DATABASE (fragdb.net):
  - 130,086 fragrances
  - 7,776 brands
  - 2,960 perfumers
  - 2,517 notes
  - 92 accords
  - 34 translations
  - 23 languages
  - Total: 143,465 records
""")

# %% [markdown]
# ## Links
#
# - **Full Database**: [fragdb.net](https://fragdb.net)
# - **GitHub**: [github.com/FragDB/fragrance-database](https://github.com/FragDB/fragrance-database)
# - **Hugging Face**: [huggingface.co/datasets/FragDBnet/fragrance-database](https://huggingface.co/datasets/FragDBnet/fragrance-database)
# - **Documentation**: [Data Dictionary](https://github.com/FragDB/fragrance-database/blob/main/DATA_DICTIONARY.md)
