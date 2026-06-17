# Dump schema — `perfumes.jsonl.zst`

One JSON object per line, zstd-compressed. The whole corpus, every perfume, unfiltered.

```sh
zstd -dc perfumes.jsonl.zst | jq        # browse
zstd -dc perfumes.jsonl.zst | wc -l     # count
```

This dump is the complete corpus. `perfumes.db` is a trimmed SQLite **showcase** built from a subset of it — vote-filtered, with the similar-perfume carousels capped and a few fields dropped — so use this dump if you want everything. Run `.schema` on the db for its shape.

## A record

```jsonc
{
  "id": 9828,
  "slug": "Creed/Aventus",
  "url": "https://www.fragrantica.com/perfume/Creed/Aventus-9828.html",
  "name": "Aventus", "brand": "Creed", "year": 2010,
  "collection": "Aventus", "gender": "male",
  "description": "Aventus by Creed is …",
  "picture":   "https://fimgs.net/mdimg/perfume/375x500.9828.jpg",
  "thumbnail": "https://fimgs.net/mdimg/perfume/m.9828.jpg",

  "perfumers": [ { "name": "Erwin Creed", "slug": "Erwin_Creed", "image_id": 865 } ],
  "accords":   [ { "name": "fruity", "strength": 100 } ],            // strength 0..100
  "notes": {
    "tiered": { "top": [ { "name": "Bergamot", "slug": "Bergamot", "image_id": 75 } ],
                "middle": [ … ], "base": [ … ] },
    "flat":   []                                                     // tiered XOR flat — never both
  },

  "rating":      { "average": 4.32, "histogram": [ { "bucket": 1, "count": 587 }, … ] },  // 1..5
  "longevity":   { "average": 3.37, "histogram": [ … ] },                                 // 1..5
  "sillage":     { "average": 2.31, "histogram": [ … ] },                                 // 1..4
  "price_value": { "average": 1.69, "histogram": [ … ] },                                 // 1..5

  "relation":         { "have": 42714, "had": 9963, "want": 28417 },        // collection counts
  "community_gender": { "female": 168, "female_leaning": 46, "unisex": 916,
                        "male_leaning": 2884, "male": 8743 },               // vote counts
  "seasons":          { "winter": 5660, "spring": 12424, "summer": 12708, "autumn": 9453 },
  "daypart":          { "day": 12660, "night": 8707 },
  "people":           26895,                                                // total raters

  "ai_summary": {
    "pros": [ { "text": "…", "up_votes": 1400, "down_votes": 66 } ],        // agree/disagree
    "cons": [ … ]
  },
  "similar": {
    "reminds_me_of": [ { "id": 34696, "slug": "…", "up_votes": 5900, "down_votes": 886 } ],
    "also_liked":    [ { "id": 51037, "slug": "…" } ]                  // no votes — algorithmic
  },

  "popularity": { "magnitude": 119527, "compound_magnitude": 34075,
                  "recent_magnitude": 31087, "last_comment_at": 1778195462 },
  "meta": { "scraped_at": 1779692833 }
}
```

## Field notes

| Field | Meaning |
|---|---|
| `id`, `slug` | Fragrantica's numeric id and URL slug. `url`/`picture`/`thumbnail` are shipped for convenience but are pure functions of `id`+`slug` — rebuild them as `https://www.fragrantica.com/perfume/{slug}-{id}.html`, `https://fimgs.net/mdimg/perfume/375x500.{id}.jpg`, `https://fimgs.net/mdimg/perfume/m.{id}.jpg`. (`perfumes.db` omits all three for that reason.) |
| `year`, `collection` | `null` when unknown / not part of a line. |
| `gender` | Fragrantica's official label (`male` / `female` / `unisex`); see `community_gender` for the crowd's view. |
| `perfumers[].image_id`, `notes[].image_id` | Fragrantica image id for the portrait / note icon (`null` when none). |
| `accords[].strength` | Accord prominence, 0–100. |
| `*.average` | Mean of the matching histogram. |
| `*.histogram` | `[{bucket, count}]`, low→high. Buckets are **rating** 1..5 (1 worst), **longevity** 1..5 (1 weak), **sillage** 1..4 (1 intimate), **price_value** 1..5 (1 overpriced, 5 great value). |
| `relation` | How many users *have* / *had* / *want* it. |
| `community_gender`, `seasons`, `daypart` | Community **vote counts** per category (not booleans). |
| `people` | Total users who voted on the aggregates above. |
| `ai_summary.pros/cons` | Fragrantica's AI-summarised opinions; `up_votes`/`down_votes` = users who agreed/disagreed. |
| `similar.reminds_me_of` | "Smells like" carousel; votes answer "does it smell like this perfume?". Counts ≥1000 are approximate (the page abbreviates them). |
| `similar.also_liked` | Algorithmic carousel; `id` + `slug` only, no votes. |
| `popularity.magnitude` | Fragrantica's engagement score (`≈ 1.47 × (have+had+want)`); backs the "most popular" sort. `*_at` fields are unix seconds. |
| `meta.scraped_at` | Unix seconds when this perfume's **page** was captured — the freshness stamp for the vote aggregates. (`rating.average` may come from a slightly older index, so treat it as "page captured at", not a stamp on every value.) |

## Conventions

- Missing scalar → `null`; missing list → `[]`; missing dict → `{}`. Lists and dicts are never `null`.
- The vote aggregates (`longevity`, `sillage`, `price_value`, `relation`, `community_gender`, `seasons`, `daypart`, `people`) come from one encrypted blob and go `null` **together** when it's absent. `rating.average` survives (index fallback); `rating.histogram` becomes `[]`.
