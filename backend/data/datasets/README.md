# FragDB v5.6 - Fragrance Databases (Fragrantica core + Parfumo bundle preview)

This is a **FREE SAMPLE** of the FragDB bundle:
- **Fragrantica** (132,858 perfumes, 23 languages) — primary; 10-row CSV samples at root
- **Parfumo** (219,963 perfumes, English-only) — also in bundle; 10-row CSV samples in `parfumo/`
- **Cross-database connection layer** — 80,968 F↔P matched pairs + schema equivalence; structural samples in `cross/`

Perfect for building recommendation systems, market analysis, multilingual fragrance apps, and cross-database research. Full datasets + cross-walk: [fragdb.net](https://fragdb.net).

## What's New in v5.6

- **Fragrantica updated** from v5.5 → v5.6: 132,124 → **132,858** fragrances (+734), +46 brands, +17 perfumers, +17 notes
- **Notes multilingual 100% coverage** (was 99.8%) — 6 previously incomplete notes now have all 22 language translations
- **Photo URL stability** — Fragrantica cache-buster query params stripped, eliminating phantom diffs across releases
- **F schema unchanged** — existing scripts work without modification (column counts 30/54/42/55/27/25 identical)
- **Free sample files unchanged** from v5.5

## Snapshot Freshness

- **Fragrantica**: refreshed 2026-06-10 (v5.6)
- **Parfumo**: 1.1 (last data prep 2026-05-26)
- **Cross-walk last refreshed**: 2026-05-26 (Phase 2B Fellegi-Sunter, quarterly rerun cadence; ~99% precision)

## What's Included

### Fragrantica (primary, at root)

| File | Records | Fields | Description |
|------|---------|--------|-------------|
| `fragrances.csv` | 10 | 30 | Iconic fragrances (v5.6) |
| `brands.csv` | 9 (referenced) | 54 | Brand profiles + 22 lang translations |
| `perfumers.csv` | 15 (referenced) | 42 | Perfumer profiles + 22 lang + 9 name translit |
| `notes.csv` | 86 (referenced) | 55 | Fragrance notes + 22 lang translations |
| `accords.csv` | 32 (referenced) | 27 | Accords + 22 lang translations |
| `translations.csv` | 34 | 25 | Gender & voting vocabulary (full, 23 languages) |
| `comments_sample.parquet` | 25 | 8 | User reviews preview (parquet, schema unchanged) |
| `news_sample.parquet` | 20 | 16 | Editorial articles preview (parquet) |
| `news_comments_sample.parquet` | 20 | 9 | News comments preview (parquet) |
| `SPEC.md` | — | — | Parquet schema documentation |

### Parfumo (in bundle)

| File | Records | Fields | Description |
|------|---------|--------|-------------|
| `parfumo/perfumes.csv` | 10 | 34 | Master catalog (10 fully-populated rows) |
| `parfumo/brands.csv` | 6 | 12 | Brand catalog |
| `parfumo/perfumers.csv` | 11 | 11 | Perfumer catalog |
| `parfumo/notes.csv` | 60 | 11 | Notes catalog |
| `parfumo/notes_categories.csv` | 79 | 6 | Hierarchical taxonomy (P-only) |
| `parfumo/accords.csv` | 18 | 4 | Accord catalog |

### Cross-database Connection Layer

| File | Records | Description |
|------|---------|-------------|
| `cross/matched_pairs_sample.csv` | 30 | First 30 of 80,968 F↔P perfume pairs |
| `cross/brand_matches_sample.csv` | 30 | First 30 of 6,522 brand pairs |
| `cross/field_equivalence_map.csv` | 206 | Full schema-level F↔P column equivalence |
| `cross/*_overlap.json` | — | 5 aggregate overlap stats |
| `cross/README.md` | — | Methodology + join recipes |

## Companion Parquet Datasets — User Reviews, News, and Community Comments

FragDB ships with **three Apache Parquet datasets** containing **4.9 million rows** of user-generated content and editorial coverage — the largest publicly-organized corpus of fragrance reviews and perfumery journalism. Use them for NLP, sentiment analysis, recommendation systems, market research, or training language models on fragrance-specific text.

**SEO Keywords:** fragrance reviews dataset · perfume reviews corpus · multilingual NLP dataset · fragrance sentiment analysis · perfumery news archive · fragrance recommendation system · scent reviews 23 languages · perfume community comments · fragrance knowledge graph · perfume market research data

### `comments.parquet` — 4.6 Million User Reviews in 23 Languages

The world's largest collection of structured fragrance reviews. Every entry includes the perfume ID (joinable with `fragrances.csv`), author username, posting date, full review text, avatar URL, and language code.

- **4,643,851 user reviews** spanning every major perfume on Fragrantica
- **23 languages** — English (1.69M reviews), Russian, Portuguese, Spanish, Korean, Turkish, Japanese, Polish, Italian, Hungarian, Serbian, Swedish, German, Hebrew, Ukrainian, French, Arabic, Greek, Czech, Chinese, Romanian, Mongolian, Dutch
- **Coverage:** 70.6% of all fragrances in the database have at least one review (93,305 of 132,160 PIDs)
- **Deterministic global primary key** — stable comment IDs survive re-scrapes
- **Zero duplicate rows**, **zero foreign key orphans** against `fragrances.csv.pid`
- **Independent UGC per language** — each language is genuine localized content, not machine translation
- **8 fields:** `pid`, `lang`, `comment_id`, `author`, `date`, `text`, `avatar_url`, `gradient_class`
- **PyArrow large_string format** — combined corpus exceeds 32-bit string offset limit

**Use cases:** sentiment analysis · review classification · recommendation systems · perfume similarity from text · language detection benchmark · multilingual NLP training corpus · fragrance market research · author network analysis · trend detection by language

### `news.parquet` — 24,440 Editorial Articles (2008–2026)

Two decades of professional fragrance journalism from Fragrantica's editorial team. Every article includes title, author, full text (plain + HTML), category, related perfumes/brands/perfumers, publication date, and main image. Foreign keys to fragrances, brands, and perfumers make this a powerful resource for content-based recommendation and knowledge graph construction.

- **24,440 editorial articles** from 2008 to 2026 — the complete public archive
- **30+ categories** — top: New Fragrances (34.9%), Fragrance Reviews (22.8%), Niche Perfumery (10.4%), Designer Brands, Interviews, History, Industry News, Niche Houses, and more
- **Bilingual storage** — `text` (plain) for NLP / search, `text_html` (preserved markup) for rich display
- **Linked entities** — `related_pids[]`, `related_brands[]`, `related_perfumers[]` as JSON arrays
- **0% orphans** over 119,662 PID references — clean foreign keys
- **Modern + archived** — 63.1% archived legacy articles, 36.9% modern fully-dated articles
- **16 fields:** `nid`, `title`, `category`, `author`, `url`, `is_archived`, `date_unix`, `description`, `text`, `text_html`, `main_image`, `article_images`, `related_pids`, `related_brands`, `related_perfumers`, `comments_count`

**Use cases:** content recommendation · article search engine · perfume knowledge graph · trend analysis · author influence study · category classification · entity linking · timeline analysis · industry research · niche perfumery research · fragrance journalism corpus

### `news_comments.parquet` — 263,798 Threaded Community Comments

Community discussions attached to editorial articles, with threading support for replies. Joinable with `news.parquet` via `nid`.

- **263,798 threaded comments** across **21,820 articles** (89.3% of news articles have at least one comment)
- **4.9% reply rate** — threaded conversations with reply detection (`is_reply` flag)
- **100% populated timestamps** — `date_unix` parsed for every comment
- **9 fields:** `nid`, `comment_id`, `is_reply`, `author`, `date`, `date_unix`, `text`, `avatar_url`, `gradient`
- **Zero foreign key orphans** against `news.parquet.nid`

**Use cases:** community engagement analysis · threaded discussion mining · reply network construction · comment sentiment · author activity profiles · temporal analysis of community responses

### Tier Availability

The parquet datasets ship with **all paid tiers except the $200 Core**:

| Tier | CSV Core | Parquet Datasets |
|------|----------|------------------|
| **$200 One-Time Core** | ✅ | ❌ |
| **$400 One-Time Full Database** | ✅ | ✅ |
| **Annual Subscription** | ✅ | ✅ (always latest) |
| **Lifetime Access** | ✅ | ✅ (always latest) |

See https://fragdb.net/#pricing for complete tier comparison.

### Free Parquet Samples (in this dataset)

This Kaggle dataset includes **free parquet preview samples**:

- `comments_sample.parquet` — 25 user reviews (8 fields)
- `news_sample.parquet` — 20 editorial articles (16 fields)
- `news_comments_sample.parquet` — 20 threaded news comments (9 fields)
- `SPEC.md` — full field-by-field schema documentation (Apache Parquet)

### Quick Start — Reading Parquet Datasets

```python
import pyarrow.parquet as pq
import pandas as pd
import json

# Read user review samples
reviews = pq.read_table('comments_sample.parquet').to_pandas()
print(reviews.head())
print(f"Languages: {reviews['lang'].nunique()}")

# Join with CSV fragrance metadata
fragrances = pd.read_csv('fragrances.csv', sep='|')
reviews_with_frag = reviews.merge(fragrances, on='pid', how='left')

# Read news article samples
news = pq.read_table('news_sample.parquet').to_pandas()
news['related_pids_list'] = news['related_pids'].apply(json.loads)
print(news[['nid', 'title', 'category', 'date_unix']].head())

# Read news comment samples and join with articles
news_comments = pq.read_table('news_comments_sample.parquet').to_pandas()
discussion = news_comments.merge(news[['nid', 'title']], on='nid')
print(discussion[['nid', 'title', 'author', 'text']].head())
```

Full schema, field types, and audit statistics are documented in `SPEC.md`.

## Full Database Statistics

| | Sample | Full Database |
|---|--------|---------------|
| F Fragrances | 10 | **132,858** |
| F Brands | 9 (referenced) | **7,927** |
| F Perfumers | 15 (referenced) | **3,005** |
| F Notes | 86 (referenced) | **2,550** |
| F Accords | 32 (referenced) | **92** |
| F Translations | 34 | **34** |
| F Languages | 23 | **23** |
| **F Total Records** | ~186 | **146,432** |
| P Perfumes (in bundle) | 10 | **219,963** |
| P Brands | 6 | 14,277 |
| P Perfumers | 11 | 2,472 |
| P Notes | 60 | 12,082 |
| P Categories (hierarchical, P-only) | 79 | 677 |
| Cross-walk F↔P perfume pairs | 30 | **80,968** |
| Cross-walk brand pairs | 30 | 6,522 |

### From v5.4 (unchanged in v5.5)
- **23 languages**: EN + de, es, fr, cs, it, ru, pl, pt, el, zh, ja, nl, sr, ro, ar, uk, mn, ko, tr, sv, he, hu
- **translations.csv**: vocabulary file — gender values and voting labels translated
- **Compact notes pyramid**: `note_id,opacity,weight` (name/icon via notes.csv JOIN)
- Each note name variant (Rose, Damask Rose) has its own ID with translations
- **Translation IDs** in gender and voting fields for multilingual support

## How Translations Work

Gender and voting fields in `fragrances.csv` contain **translation IDs** instead of text:
- `gender`: `gender_for_women` (was `for women`)
- `appreciation`: `like_love:15500:59` (was `love:15500:59`)

Look up any ID in `translations.csv` to get text in any of 23 languages.

Reference files have extra columns: `country_ru`, `note_name_ja`, `name_de`, etc.

## Quick Start

```python
import pandas as pd

fragrances = pd.read_csv('fragrances.csv', sep='|')
brands = pd.read_csv('brands.csv', sep='|')
notes = pd.read_csv('notes.csv', sep='|')
translations = pd.read_csv('translations.csv', sep='|')

# Join and translate
fragrances['brand_id'] = fragrances['brand'].str.split(';').str[1]
df = fragrances.merge(brands, left_on='brand_id', right_on='id', suffixes=('', '_brand'))
trans = translations.set_index('id')
df['gender_ru'] = df['gender'].map(lambda x: trans.loc[x, 'ru'] if x in trans.index else x)

print(df[['name', 'name_brand', 'country_ja', 'gender_ru']])
```

## File Format

- **Format**: CSV (pipe `|` delimited)
- **Encoding**: UTF-8
- **Quote Character**: `"` (double quote)

## Use Cases

### CSV Core (all tiers)
- **E-commerce** — Enrich product listings with detailed fragrance data, notes, accords
- **Mobile Apps** — Build fragrance collection managers, scent discovery apps, perfume catalog apps
- **Data Analysis** — Analyze fragrance industry trends by brand, country, perfumer, year
- **Recommendations** — Content-based or collaborative filtering systems using accord/note vectors
- **Content Creation** — Power blogs, videos, fragrance reviews with accurate data
- **Multilingual UIs** — Localized perfume catalogs in 23 languages out of the box
- **Knowledge Graphs** — Brand → Perfumer → Fragrance → Notes → Accords graph construction
- **Market Research** — Country-of-origin analysis, parent company portfolios, perfumer productivity stats

### Parquet Datasets ($400+ tiers)
- **NLP & Sentiment Analysis** — Train models on 4.6M multilingual fragrance reviews
- **Recommender Systems** — Hybrid models combining CSV structure with review text similarity
- **Language Models** — Domain-specific corpus for fragrance/perfumery LLM fine-tuning
- **Review Classification** — Identify positive/negative reviews, fake review detection
- **Trend Detection** — News article timeline analysis, emerging fragrance trends
- **Author Networks** — Identify influential reviewers, perfumery journalists, community leaders
- **Content-Based Discovery** — "Articles about this perfume" — JOIN news.related_pids with fragrances.pid
- **Community Analytics** — Reply networks, engagement metrics on editorial content
- **Cross-Language Studies** — Compare review sentiment across 23 languages for the same fragrance
- **Search Engines** — Full-text search across reviews, articles, and structured metadata
- **Entity Resolution** — Match journalist's `related_brands[]` mentions with `brands.csv` IDs
- **Knowledge Extraction** — Mine 24K editorial articles for perfume facts, launch dates, perfumer interviews

## Get the Full Database

This sample demonstrates the data quality and structure. The full database with **144,280 records** in **23 languages**, plus **4.9 million parquet records** (reviews, news, comments) is available at:

### [fragdb.net](https://fragdb.net)

## License

This sample is provided under **CC-BY-NC-4.0** (Attribution-NonCommercial).

## Links

- **Full Database**: [fragdb.net](https://fragdb.net)
- **GitHub**: [github.com/FragDB/fragrance-database](https://github.com/FragDB/fragrance-database)
- **Hugging Face**: [huggingface.co/datasets/FragDBnet/fragrance-database](https://huggingface.co/datasets/FragDBnet/fragrance-database)
- **Documentation**: [Data Dictionary](https://github.com/FragDB/fragrance-database/blob/main/DATA_DICTIONARY.md)

---

*Last updated: May 2026 (v5.4)*
