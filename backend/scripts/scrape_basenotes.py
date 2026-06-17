"""
Basenotes.net fragrance data scraper — brand-page approach.

Uses plain requests (no Chrome/browser automation) to navigate brand pages
and collect top/middle/base note pyramids plus rating/vote data.

Run from the backend/ directory:
  python scripts/scrape_basenotes.py --brands "dior,chanel" --limit 5 --dry-run
  python scripts/scrape_basenotes.py --brands "dior" --limit 50
  python scripts/scrape_basenotes.py              # all 30 brands, 50 each

NOTE: Basenotes.net is behind Cloudflare. If the pre-flight check returns 403
this script exits immediately. Options to unblock: pass --cookies from a browser
session, or set BASENOTES_COOKIE env var to a valid session cookie string.
"""

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import psycopg2
import requests
from bs4 import BeautifulSoup
from psycopg2.extras import Json as PgJson
from rapidfuzz import fuzz
from rapidfuzz import process as rfprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/railway",
)
BASE_URL = "https://www.basenotes.net"
DELAY = 1.5        # seconds between requests
FUZZY_THRESHOLD = 85.0

# Top 30 brands: display name → Basenotes URL slug
BRAND_SLUGS: dict[str, str] = {
    "Dior": "dior",
    "Chanel": "chanel",
    "Tom Ford": "tom-ford",
    "Yves Saint Laurent": "yves-saint-laurent",
    "Creed": "creed",
    "Versace": "versace",
    "Prada": "prada",
    "Gucci": "gucci",
    "Armani": "giorgio-armani",
    "Mugler": "thierry-mugler",
    "Lancome": "lancome",
    "Jo Malone": "jo-malone-london",
    "Hermes": "hermes",
    "Givenchy": "givenchy",
    "Burberry": "burberry",
    "Calvin Klein": "calvin-klein",
    "Paco Rabanne": "paco-rabanne",
    "Viktor&Rolf": "viktor-rolf",
    "Maison Francis Kurkdjian": "maison-francis-kurkdjian",
    "Maison Margiela": "maison-margiela",
    "Le Labo": "le-labo",
    "Byredo": "byredo",
    "Diptyque": "diptyque",
    "Penhaligons": "penhaligons",
    "Amouage": "amouage",
    "Serge Lutens": "serge-lutens",
    "Frederic Malle": "frederic-malle",
    "Acqua di Parma": "acqua-di-parma",
    "Parfums de Marly": "parfums-de-marly",
    "Initio": "initio-parfums-prives",
}

# Canonical DB brand names that may differ from display names above
_DB_BRAND_VARIANTS: dict[str, list[str]] = {
    "Dior": ["Dior", "Christian Dior"],
    "Armani": ["Giorgio Armani", "Armani"],
    "Mugler": ["Thierry Mugler", "Mugler"],
    "Jo Malone": ["Jo Malone London", "Jo Malone"],
    "Hermes": ["Hermès", "Hermes"],
    "Lancome": ["Lancôme", "Lancome"],
    "Viktor&Rolf": ["Viktor&Rolf", "Viktor & Rolf"],
    "Penhaligons": ["Penhaligon's", "Penhaligons"],
    "Yves Saint Laurent": ["Yves Saint Laurent", "YSL"],
    "Creed": ["Creed"],
}

_PUNC_RE = re.compile(r"[^\w\s]")


def _norm(s: str) -> str:
    return _PUNC_RE.sub("", str(s).lower()).strip()


# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------

_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
})


def _get(url: str) -> Optional[requests.Response]:
    try:
        r = _session.get(url, timeout=20, allow_redirects=True)
        if r.status_code == 403:
            log.error("403 Cloudflare block on %s — plaintext requests are blocked.", url)
            log.error("Set BASENOTES_COOKIE env var or use --cookies <file> to unblock.")
            sys.exit(1)
        if r.status_code == 404:
            log.debug("404: %s", url)
            return None
        if r.status_code != 200:
            log.warning("HTTP %d for %s", r.status_code, url)
            return None
        return r
    except requests.RequestException as e:
        log.warning("Request failed for %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Brand page — collect fragrance URLs
# ---------------------------------------------------------------------------

# Basenotes has used several URL structures over the years; try all:
_BRAND_PAGE_TEMPLATES = [
    "/brands/{slug}/",
    "/house/{slug}/",
    "/fragranceDirectory/brands/{slug}/index.html",
    "/perfumes/{slug}/",
]

_FRAG_LINK_RE = re.compile(
    r"/(?:fragrances?|perfumes?)/[a-z0-9\-]+/[a-z0-9\-]+",
    re.IGNORECASE,
)


def _extract_frag_links(html: str) -> list[str]:
    """Pull distinct /fragrances/{brand}/{name}/ hrefs from raw HTML."""
    seen: set[str] = set()
    links: list[str] = []
    for m in re.finditer(r'href=["\']([^"\']*)["\']', html):
        href = m.group(1)
        if _FRAG_LINK_RE.search(href):
            full = urljoin(BASE_URL, href).split("?")[0].rstrip("/") + "/"
            # Exclude brand-level links (exactly 3 path segments after domain)
            path_parts = [p for p in full.replace(BASE_URL, "").split("/") if p]
            if len(path_parts) >= 3 and full not in seen:
                seen.add(full)
                links.append(full)
    return links


def get_brand_perfume_urls(brand_slug: str) -> list[str]:
    """
    Try several Basenotes brand page URL patterns and collect fragrance URLs.
    Handles simple pagination (page=2, page=3, ...) up to 10 pages.
    """
    for template in _BRAND_PAGE_TEMPLATES:
        url = BASE_URL + template.format(slug=brand_slug)
        log.debug("Trying brand URL: %s", url)
        r = _get(url)
        if r is None:
            continue

        links = _extract_frag_links(r.text)
        if not links:
            continue

        log.info("  Brand page %s → %d fragrance links (page 1)", url, len(links))

        # Paginate
        page = 2
        while page <= 10:
            time.sleep(DELAY)
            page_url = url + f"?page={page}" if "?" not in url else url + f"&page={page}"
            pr = _get(page_url)
            if pr is None:
                break
            new_links = _extract_frag_links(pr.text)
            fresh = [l for l in new_links if l not in set(links)]
            if not fresh:
                break
            links.extend(fresh)
            log.info("  Page %d → +%d links (total %d)", page, len(fresh), len(links))
            page += 1

        return links

    log.warning("No fragrance URLs found for brand slug '%s'", brand_slug)
    return []


# ---------------------------------------------------------------------------
# Fragrance page — parse notes + rating
# ---------------------------------------------------------------------------

def parse_note_pyramid(soup: BeautifulSoup) -> Optional[dict[str, list[str]]]:
    """
    Extract top/middle/base notes from a Basenotes fragrance page.

    Supports both the current structure (<ul class="fragrancenotes">) and
    older dt/dd table structures seen on archived pages.
    """
    result: dict[str, list[str]] = {"top": [], "middle": [], "base": []}

    # --- Primary: <ul class="fragrancenotes"> (current site) ---
    ul = soup.find("ul", class_="fragrancenotes")
    if ul:
        label_map = {
            "head": "top", "top": "top", "top notes": "top",
            "heart": "middle", "middle": "middle", "middle notes": "middle",
            "base": "base", "base notes": "base",
        }
        for li in ul.find_all("li", recursive=False):
            hdr = li.find(["h3", "h4", "strong", "b"])
            if not hdr:
                continue
            key = label_map.get(hdr.get_text().strip().rstrip(":").lower())
            if not key:
                continue
            inner = li.find("ul")
            if inner:
                inner_li = inner.find("li")
                if inner_li:
                    raw = inner_li.get_text()
                    result[key] = [n.strip().title() for n in raw.split(",") if n.strip()]
        if any(result.values()):
            return result

    # --- Fallback: <dt> / <dd> structure or plain divs ---
    label_map = {
        "top notes": "top", "head notes": "top",
        "heart notes": "middle", "middle notes": "middle",
        "base notes": "base",
    }
    for dt in soup.find_all("dt"):
        label = dt.get_text().strip().lower().rstrip(":")
        key = label_map.get(label)
        if not key:
            continue
        dd = dt.find_next_sibling("dd")
        if dd:
            raw = dd.get_text()
            result[key] = [n.strip().title() for n in re.split(r"[,;]", raw) if n.strip()]

    if any(result.values()):
        return result

    return None


def parse_rating(soup: BeautifulSoup) -> tuple[Optional[float], Optional[int]]:
    """
    Extract vote count and optional numeric average from a Basenotes page.

    Basenotes shows: "123 Positive (65%)" / "45 Neutral" / "12 Negative"
    Sum of all three is the total vote/review count.
    The numeric average (0-5 scale) comes from structured data or score elements.
    """
    html = str(soup)

    # Vote count
    vote_matches = re.findall(r"(\d[\d,]*)\s+(?:Positive|Neutral|Negative)", html)
    vote_count: Optional[int] = None
    if vote_matches:
        vote_count = sum(int(v.replace(",", "")) for v in vote_matches)

    # Numeric rating
    rating: Optional[float] = None

    # JSON-LD structured data (most reliable)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            rv = data.get("aggregateRating", {}).get("ratingValue")
            if rv is not None:
                val = float(rv)
                best = float(data.get("aggregateRating", {}).get("bestRating", 5))
                rating = round(val / best * 5, 2)
                break
        except Exception:
            pass

    # itemprop fallback
    if rating is None:
        el = soup.find(attrs={"itemprop": "ratingValue"})
        if el:
            m = re.search(r"(\d+(?:\.\d+)?)", el.get_text())
            if m:
                val = float(m.group(1))
                rating = round(val / 2, 2) if val > 5 else val

    return rating, vote_count


def fetch_fragrance(url: str) -> tuple[Optional[dict], Optional[float], Optional[int]]:
    """Fetch fragrance page; return (notes_dict, rating, vote_count)."""
    r = _get(url)
    if r is None:
        return None, None, None
    soup = BeautifulSoup(r.text, "html.parser")
    notes = parse_note_pyramid(soup)
    rating, vote_count = parse_rating(soup)
    return notes, rating, vote_count


def name_from_url(url: str) -> str:
    """Derive a human-readable fragrance name from its Basenotes URL slug."""
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").title()


# ---------------------------------------------------------------------------
# DB helpers (synchronous psycopg2)
# ---------------------------------------------------------------------------

def _open_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(DB_URL, connect_timeout=30)


def load_db_for_brands(display_names: list[str]) -> dict:
    """
    Load perfumes for the target brands from the DB.

    Returns:
      brand_index: {norm_brand: [(norm_name, id), ...]}
      needs_map:   {id: (top_notes_empty, rating_count_zero)}
    """
    # Build the full set of DB brand name variants to query
    db_brand_names: list[str] = []
    for dn in display_names:
        variants = _DB_BRAND_VARIANTS.get(dn, [dn])
        db_brand_names.extend(variants)
    db_brand_names = list(set(db_brand_names))

    log.info("Querying DB for brands: %s", db_brand_names)
    conn = _open_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, brand,
               (top_notes IS NULL OR top_notes::text = '[]') AS top_empty,
               (rating_count IS NULL OR rating_count = 0)   AS rc_zero
        FROM perfumes
        WHERE brand = ANY(%s)
    """, [db_brand_names])
    rows = cur.fetchall()
    conn.close()

    brand_index: dict[str, list[tuple[str, int]]] = {}
    needs_map: dict[int, tuple[bool, bool]] = {}

    for pid, name, brand, top_empty, rc_zero in rows:
        nb = _norm(brand)
        brand_index.setdefault(nb, []).append((_norm(name), pid))
        needs_map[pid] = (bool(top_empty), bool(rc_zero))

    total = sum(len(v) for v in brand_index.values())
    log.info("Loaded %d perfumes across %d brand buckets from DB", total, len(brand_index))
    return brand_index, needs_map


def find_db_match(frag_name: str, display_brand: str, brand_index: dict) -> Optional[int]:
    """Fuzzy-match a scraped fragrance name to a DB id (≥85% token_sort_ratio)."""
    # Try each known DB variant of this brand
    variants = _DB_BRAND_VARIANTS.get(display_brand, [display_brand])
    for variant in variants:
        bucket = brand_index.get(_norm(variant), [])
        if not bucket:
            continue
        candidate_names = [c[0] for c in bucket]
        result = rfprocess.extractOne(
            _norm(frag_name), candidate_names, scorer=fuzz.token_sort_ratio
        )
        if result and result[1] >= FUZZY_THRESHOLD:
            return bucket[result[2]][1]
    return None


def write_to_db(
    pid: int,
    notes: Optional[dict[str, list[str]]],
    vote_count: Optional[int],
) -> None:
    """Gap-fill: write notes and/or rating_count to DB for one perfume."""
    updates: dict = {}
    if notes:
        updates["top_notes"] = PgJson(notes["top"])
        updates["middle_notes"] = PgJson(notes["middle"])
        updates["base_notes"] = PgJson(notes["base"])
    if vote_count and vote_count > 0:
        updates["rating_count"] = vote_count

    if not updates:
        return

    cols = list(updates.keys())
    set_clause = ", ".join(f"{c} = %s" for c in cols)
    params = [updates[c] for c in cols] + [pid]

    conn = _open_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE perfumes SET {set_clause} WHERE id = %s", params)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Per-brand scrape loop
# ---------------------------------------------------------------------------

def scrape_brand(
    display_name: str,
    brand_slug: str,
    brand_index: dict,
    needs_map: dict,
    limit: int,
    dry_run: bool,
) -> dict[str, int]:
    stats = {
        "fetched": 0, "matched": 0, "no_match": 0, "skipped": 0,
        "updated_notes": 0, "updated_rating": 0, "no_pyramid": 0, "errors": 0,
    }

    log.info("=" * 60)
    log.info("Brand: %s  (slug: %s)", display_name, brand_slug)

    urls = get_brand_perfume_urls(brand_slug)
    if not urls:
        log.warning("  No fragrance URLs found — check slug or site structure")
        return stats

    log.info("  %d fragrance URLs found; processing up to %d", len(urls), limit)

    for i, url in enumerate(urls[:limit]):
        frag_name = name_from_url(url)
        log.info("[%d/%d] %s", i + 1, min(limit, len(urls)), frag_name)
        log.debug("       URL: %s", url)

        pid = find_db_match(frag_name, display_name, brand_index)
        if pid is None:
            log.info("  → No DB match (fuzzy threshold %.0f%%)", FUZZY_THRESHOLD)
            stats["no_match"] += 1
            time.sleep(DELAY)
            stats["fetched"] += 1
            continue

        needs_notes, needs_rating = needs_map.get(pid, (False, False))
        if not needs_notes and not needs_rating:
            log.info("  → DB id=%d already complete, skipping fetch", pid)
            stats["skipped"] += 1
            continue

        stats["matched"] += 1
        time.sleep(DELAY)

        try:
            notes, rating, vote_count = fetch_fragrance(url)
            stats["fetched"] += 1
        except SystemExit:
            raise
        except Exception as e:
            log.warning("  → Fetch error: %s", e)
            stats["errors"] += 1
            continue

        if notes:
            log.info(
                "  → top=%s | mid=%s | base=%s | votes=%s",
                notes["top"][:3], notes["middle"][:3], notes["base"][:3], vote_count,
            )
        else:
            log.info("  → No note pyramid | votes=%s", vote_count)
            stats["no_pyramid"] += 1

        write_notes = notes if needs_notes else None
        write_votes = vote_count if needs_rating else None

        if dry_run:
            if write_notes:
                stats["updated_notes"] += 1
            if write_votes:
                stats["updated_rating"] += 1
            log.info("  → [DRY RUN] Would update id=%d", pid)
        else:
            try:
                write_to_db(pid, write_notes, write_votes)
                if write_notes:
                    stats["updated_notes"] += 1
                if write_votes:
                    stats["updated_rating"] += 1
                log.info("  → DB updated (id=%d)", pid)
            except Exception as e:
                log.warning("  → DB write error: %s", e)
                stats["errors"] += 1

    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Basenotes.net note pyramids via brand pages (plain requests)."
    )
    parser.add_argument(
        "--brands",
        default="",
        help=(
            'Comma-separated brand names to scrape (case-insensitive). '
            'E.g. "dior,chanel". Default: all 30 brands.'
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max fragrance pages per brand (default 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and match but do not write to DB",
    )
    parser.add_argument(
        "--cookies",
        default="",
        help=(
            "Path to a Netscape-format cookie file, or a raw Cookie header string. "
            "Use this to pass Cloudflare when logged in via a browser."
        ),
    )
    args = parser.parse_args()

    # Inject cookies if provided
    cookie_env = os.environ.get("BASENOTES_COOKIE", "")
    cookie_src = args.cookies or cookie_env
    if cookie_src:
        if Path(cookie_src).exists():
            # Netscape cookie file (e.g. exported by EditThisCookie)
            try:
                import http.cookiejar
                jar = http.cookiejar.MozillaCookieJar(cookie_src)
                jar.load(ignore_discard=True, ignore_expires=True)
                _session.cookies.update(jar)
                log.info("Loaded cookies from file: %s", cookie_src)
            except Exception as e:
                log.warning("Could not load cookie file: %s", e)
        else:
            # Raw "name=value; name2=value2" string
            for part in cookie_src.split(";"):
                part = part.strip()
                if "=" in part:
                    k, _, v = part.partition("=")
                    _session.cookies.set(k.strip(), v.strip(), domain="www.basenotes.net")
            log.info("Loaded %d cookies from string", len(cookie_src.split(";")))

    # Resolve brand list
    if args.brands:
        requested = [b.strip().lower() for b in args.brands.split(",")]
        brand_items: list[tuple[str, str]] = []
        for name, slug in BRAND_SLUGS.items():
            if (
                name.lower() in requested
                or slug in requested
                or any(r in name.lower() for r in requested)
            ):
                brand_items.append((name, slug))
        if not brand_items:
            log.error(
                "No matching brands found for %s. Available: %s",
                args.brands, list(BRAND_SLUGS.keys()),
            )
            sys.exit(1)
    else:
        brand_items = list(BRAND_SLUGS.items())

    log.info("Brands to scrape (%d): %s", len(brand_items), [b[0] for b in brand_items])
    log.info("Limit per brand: %d | Dry run: %s", args.limit, args.dry_run)

    # Pre-flight connectivity check
    log.info("Pre-flight: testing %s ...", BASE_URL)
    try:
        r = _session.get(BASE_URL + "/fragrances/", timeout=10)
        if r.status_code == 403:
            log.error(
                "403 Cloudflare block — plaintext requests are blocked by Basenotes.net."
            )
            log.error(
                "To unblock: export cookies from a logged-in browser session and pass "
                "them with --cookies <file> or BASENOTES_COOKIE env var."
            )
            sys.exit(1)
        log.info("Pre-flight OK (status %d)", r.status_code)
    except requests.RequestException as e:
        log.error("Pre-flight failed: %s", e)
        sys.exit(1)

    # Load DB
    display_names = [name for name, _ in brand_items]
    brand_index, needs_map = load_db_for_brands(display_names)

    # Scrape
    totals: dict[str, int] = {}
    for display_name, brand_slug in brand_items:
        stats = scrape_brand(
            display_name, brand_slug, brand_index, needs_map, args.limit, args.dry_run
        )
        for k, v in stats.items():
            totals[k] = totals.get(k, 0) + v

    log.info("=" * 60)
    log.info("DONE%s", " (DRY RUN — nothing written)" if args.dry_run else "")
    log.info("=" * 60)
    for k, v in totals.items():
        log.info("  %-22s %d", k, v)


if __name__ == "__main__":
    main()
