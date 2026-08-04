"""
Scrape verified concentration (EDT/EDP/Extrait/etc.) from Fragrantica perfume
pages and write to perfume_enrichment_v2. Designed to run as a Railway
background job (long-lived, resumable, tiered).

Only rows where perfumes.fragrantica_url is a real fragrantica.com URL are
scraped. NOTE: ~42,830 rows have a fragrantica_url that actually points to
parfumo.com (leftover from the Parfumo import writing into the wrong column)
-- those are excluded here since Fragrantica-specific selectors won't apply.

Checkpointing: any perfume_id already in perfume_enrichment_v2 with a
non-NULL concentration_source is considered done and is skipped. A restart
(new Railway deploy, crash, manual re-run) resumes exactly where it left off.

"Not found" (no concentration mentioned in the page prose) is a terminal,
checkpointed result: concentration_source='not_found' is written so the row
is never retried.

403s are NOT checkpointed: nothing is written to the DB, so a blocked row
is retried on the next run. A 403 triggers a 15s extra cooldown before
continuing to the next perfume.

Tiering (--tier 1|2) lets you prioritize high-value perfumes (top brands /
top rating_count) before grinding through the long tail.

Writes ONLY to perfume_enrichment_v2. Only ever SELECTs from perfumes and
perfume_brand_v2 (for the tier filter).

Usage:
  python backend/scripts/scrape_concentration_v2.py --tier 1
  python backend/scripts/scrape_concentration_v2.py --tier 2
  python backend/scripts/scrape_concentration_v2.py --tier 1 --limit 10   # sample run
"""
import argparse
import os
import random
import re
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Railway injects DATABASE_URL (internal, private-network host) into the job
# environment automatically. The public proxy URL is kept as a fallback for
# local/manual runs and can be overridden by setting DATABASE_URL yourself.
PUBLIC_DB_URL = "postgresql://postgres:qEKyVfuGveaaePXgdeJchyDIIKRjQUkc@tramway.proxy.rlwy.net:19043/railway"
DB_URL = os.environ.get("DATABASE_URL", PUBLIC_DB_URL)

DELAY_MIN = 5.0
DELAY_MAX = 8.0
FORBIDDEN_COOLDOWN = 15.0
COMMIT_EVERY = 50
LOG_EVERY = 50
REQUEST_TIMEOUT = 20
TOP_RATING_COUNT_LIMIT = 5000

TIER1_BRANDS = [
    "Armaf", "Al Haramain", "Swiss Arabian", "Rasasi", "Lattafa", "Dior",
    "Chanel", "Tom Ford", "Yves Saint Laurent", "Guerlain", "Giorgio Armani",
    "Versace", "Paco Rabanne", "Hugo Boss", "Calvin Klein", "Dolce Gabbana",
    "Burberry", "Givenchy", "Lancome", "Hermès", "Creed",
    "Maison Francis Kurkdjian", "Jo Malone London", "Parfums De Marly",
    "Xerjoff",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# Longest/most-specific phrases first so "Eau de Parfum" doesn't get
# swallowed by a bare "Parfum" match.
_CONCENTRATION_PATTERNS = [
    (re.compile(r"extrait\s+de\s+parfum", re.I), "Extrait"),
    (re.compile(r"\bextrait\b", re.I), "Extrait"),
    (re.compile(r"eau\s+de\s+parfum", re.I), "EDP"),
    (re.compile(r"eau\s+de\s+toilette", re.I), "EDT"),
    (re.compile(r"eau\s+de\s+cologne", re.I), "EDC"),
    (re.compile(r"\bparfum\b", re.I), "Parfum"),
]


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.fragrantica.com",
    }


class Forbidden(Exception):
    pass


def fetch_concentration(url: str) -> str | None:
    """Fetch a Fragrantica page and return the mapped concentration, or None
    if no concentration is mentioned in the page prose ("not found").
    Raises Forbidden on HTTP 403.
    """
    resp = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT)
    if resp.status_code == 403:
        raise Forbidden(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    haystack_parts: list[str] = []

    desc_div = soup.select_one('div[itemprop="description"]')
    if desc_div:
        haystack_parts.append(desc_div.get_text(" ", strip=True))

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        haystack_parts.append(meta_desc["content"])

    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        haystack_parts.append(og_desc["content"])

    title_tag = soup.find("title")
    if title_tag:
        haystack_parts.append(title_tag.get_text())

    breadcrumb = soup.select_one("nav[aria-label='breadcrumb'], ol.breadcrumb, div.breadcrumbs")
    if breadcrumb:
        haystack_parts.append(breadcrumb.get_text(" ", strip=True))

    haystack = " ".join(haystack_parts)

    for pattern, label in _CONCENTRATION_PATTERNS:
        if pattern.search(haystack):
            return label

    return None


def get_conn():
    return psycopg2.connect(DB_URL)


def fetch_targets(conn, tier: int, limit: int | None):
    cur = conn.cursor()

    if tier == 1:
        query = """
            SELECT p.id, p.brand, p.name, p.fragrantica_url
            FROM perfumes p
            LEFT JOIN perfume_enrichment_v2 e
                ON e.perfume_id = p.id AND e.concentration_source IS NOT NULL
            LEFT JOIN perfume_brand_v2 b
                ON b.perfume_id = p.id
            WHERE p.fragrantica_url ILIKE %s
              AND e.perfume_id IS NULL
              AND (
                    b.brand_normalized = ANY(%s)
                    OR p.id IN (
                        SELECT id FROM perfumes
                        WHERE fragrantica_url ILIKE %s
                        ORDER BY rating_count DESC NULLS LAST
                        LIMIT %s
                    )
              )
            ORDER BY p.id
        """
        params = ["%fragrantica.com%", TIER1_BRANDS, "%fragrantica.com%", TOP_RATING_COUNT_LIMIT]
    else:
        query = """
            SELECT p.id, p.brand, p.name, p.fragrantica_url
            FROM perfumes p
            LEFT JOIN perfume_enrichment_v2 e
                ON e.perfume_id = p.id AND e.concentration_source IS NOT NULL
            WHERE p.fragrantica_url ILIKE %s
              AND e.perfume_id IS NULL
            ORDER BY p.id
        """
        params = ["%fragrantica.com%"]

    if limit:
        query += " LIMIT %s"
        params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def count_tier1(conn) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT count(*)
        FROM perfumes p
        LEFT JOIN perfume_brand_v2 b ON b.perfume_id = p.id
        WHERE p.fragrantica_url ILIKE %s
          AND (
                b.brand_normalized = ANY(%s)
                OR p.id IN (
                    SELECT id FROM perfumes
                    WHERE fragrantica_url ILIKE %s
                    ORDER BY rating_count DESC NULLS LAST
                    LIMIT %s
                )
          )
        """,
        ["%fragrantica.com%", TIER1_BRANDS, "%fragrantica.com%", TOP_RATING_COUNT_LIMIT],
    )
    n = cur.fetchone()[0]
    cur.close()
    return n


def upsert_batch(conn, batch: list[tuple]) -> None:
    if not batch:
        return
    cur = conn.cursor()
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO perfume_enrichment_v2
            (perfume_id, concentration_verified, concentration_source, concentration_fetched_at)
        VALUES %s
        ON CONFLICT (perfume_id) DO UPDATE SET
            concentration_verified = EXCLUDED.concentration_verified,
            concentration_source = EXCLUDED.concentration_source,
            concentration_fetched_at = EXCLUDED.concentration_fetched_at
        """,
        batch,
    )
    conn.commit()
    cur.close()


def run(tier: int, limit: int | None):
    conn = get_conn()
    targets = fetch_targets(conn, tier, limit)
    total = len(targets)
    print(f"Targets to scrape (tier={tier}): {total}\n")

    batch: list[tuple] = []
    verified = 0
    not_found = 0
    forbidden = 0

    for i, (perfume_id, brand, name, url) in enumerate(targets, 1):
        fetched_at = datetime.now(timezone.utc)

        try:
            concentration = fetch_concentration(url)
        except Forbidden:
            forbidden += 1
            print(f"  [{i}/{total}] id={perfume_id} brand={brand} name={name} -> 403 BLOCKED (will retry next run)")
            time.sleep(FORBIDDEN_COOLDOWN)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue
        except requests.RequestException as e:
            print(f"  [{i}/{total}] id={perfume_id} brand={brand} name={name} -> fetch error: {e} (will retry next run)")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        if concentration is None:
            not_found += 1
            batch.append((perfume_id, None, "not_found", fetched_at))
            print(f"  [{i}/{total}] id={perfume_id} brand={brand} name={name} -> not_found")
        else:
            verified += 1
            batch.append((perfume_id, concentration, "fragrantica_scrape", fetched_at))
            print(f"  [{i}/{total}] id={perfume_id} brand={brand} name={name} -> {concentration}")

        if len(batch) >= COMMIT_EVERY:
            upsert_batch(conn, batch)
            batch = []

        if i % LOG_EVERY == 0:
            print(
                f"[{i}/{total} tier={tier}] id={perfume_id} brand={brand} → "
                f"{concentration if concentration else 'not_found'} "
                f"({'fragrantica_scrape' if concentration else 'not_found'}) "
                f"| 403s={forbidden} not_found={not_found} verified={verified}"
            )

        if i < total:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    upsert_batch(conn, batch)

    print(
        f"\nDone. tier={tier} total={total} verified={verified} "
        f"not_found={not_found} 403_blocked={forbidden}"
    )
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tiered Fragrantica concentration scraper -> perfume_enrichment_v2")
    parser.add_argument("--tier", type=int, choices=[1, 2], required=True, help="1 = priority brands/top rating_count, 2 = everything remaining")
    parser.add_argument("--limit", type=int, default=None, help="Max perfumes to process this run (omit for full tier)")
    args = parser.parse_args()
    run(args.tier, args.limit)
