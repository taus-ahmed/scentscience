"""
Fragrantica scraper — single lookup, bulk mode, and note expansion.
For educational / personal use only. Respects rate limits.

Usage:
  python -m scrapers.fragrantica --name "Sauvage" --brand "Dior"
  python -m scrapers.fragrantica --bulk --limit 500
  python -m scrapers.fragrantica --notes --limit 300
"""

import asyncio
import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import argparse
import requests
from bs4 import BeautifulSoup
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type

# ---------------------------------------------------------------------------
# Path setup — allow running as `python -m scrapers.fragrantica` from backend/
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings  # noqa: E402

settings = get_settings()
log = logging.getLogger("fragrantica")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

BASE_URL = "https://www.fragrantica.com"
DATA_DIR = Path(__file__).parent.parent / "data"
NOTES_PATH = DATA_DIR / "notes_chemistry.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}

# Search queries used to collect perfume URLs across the alphabet
_BROWSE_QUERIES = list("abcdefghijklmnopqrstuvwxyz") + ["popular", "new"]

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

@retry(
    wait=wait_fixed(5),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _get(url: str, delay: float | None = None) -> requests.Response:
    time.sleep(delay if delay is not None else settings.fragrantica_scrape_delay)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp


def _jitter(base: float = 2.5) -> float:
    """Random delay between base and base+1.5 seconds."""
    return base + random.uniform(0, 1.5)


# ---------------------------------------------------------------------------
# Single-perfume search (existing behaviour, kept intact)
# ---------------------------------------------------------------------------

def search_perfume(name: str, brand: str | None = None) -> list[dict]:
    query = f"{brand} {name}".strip() if brand else name
    url = f"{BASE_URL}/search/?query={requests.utils.quote(query)}"
    resp = _get(url, delay=settings.fragrantica_scrape_delay)
    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for item in soup.select("div.cell.card.fr-news-box")[:5]:
        a = item.select_one("a[href*='/perfume/']") or item.select_one("a")
        if a and a.get("href"):
            href = a["href"]
            results.append({
                "name": a.get_text(strip=True),
                "url": BASE_URL + href if href.startswith("/") else href,
            })
    return results


# ---------------------------------------------------------------------------
# URL collection for bulk mode
# ---------------------------------------------------------------------------

def _collect_perfume_urls(limit: int) -> list[str]:
    """
    Harvest perfume page URLs from Fragrantica search result pages.
    Iterates search queries (a–z + 'popular') until we have enough.
    Returns a deduplicated list of up to `limit` URLs.
    """
    seen: set[str] = set()
    urls: list[str] = []

    for query in _BROWSE_QUERIES:
        if len(urls) >= limit:
            break

        for page in range(1, 20):           # up to 20 pages per query
            if len(urls) >= limit:
                break

            search_url = (
                f"{BASE_URL}/search/?query={requests.utils.quote(query)}"
                f"&page={page}"
            )
            try:
                resp = _get(search_url, delay=_jitter(1.5))
                soup = BeautifulSoup(resp.text, "lxml")

                cards = soup.select("div.cell.card.fr-news-box")
                if not cards:
                    break  # no more pages for this query

                for card in cards:
                    a = card.select_one("a[href*='/perfume/']") or card.select_one("a")
                    if not a:
                        continue
                    href = a.get("href", "")
                    if not href or "/perfume/" not in href:
                        continue
                    full = BASE_URL + href if href.startswith("/") else href
                    if full not in seen:
                        seen.add(full)
                        urls.append(full)
                        if len(urls) >= limit:
                            break

            except Exception as e:
                log.warning("URL collection failed (query=%s page=%d): %s", query, page, e)
                break

    return urls[:limit]


# ---------------------------------------------------------------------------
# Full perfume page scraper
# ---------------------------------------------------------------------------

def _extract_fragrantica_id(url: str) -> str | None:
    m = re.search(r"-(\d+)\.html", url)
    return m.group(1) if m else None


def _extract_concentration(name: str) -> str:
    name_lower = name.lower()
    if "extrait" in name_lower:
        return "Extrait"
    if "parfum" in name_lower and "eau de" not in name_lower:
        return "Parfum"
    if "eau de parfum" in name_lower or " edp" in name_lower:
        return "EDP"
    if "eau de toilette" in name_lower or " edt" in name_lower:
        return "EDT"
    if "eau de cologne" in name_lower or " edc" in name_lower:
        return "EDC"
    return "EDT"


def _parse_notes_section(soup: BeautifulSoup, header_text: str) -> list[str]:
    """Try several selector strategies to extract notes for a given pyramid tier."""
    notes: list[str] = []

    # Strategy 1: bold header → parent container → links
    header = soup.find("b", string=re.compile(header_text, re.IGNORECASE))
    if header:
        container = header.find_parent()
        if container:
            notes = [a.get_text(strip=True) for a in container.select("a") if a.get_text(strip=True)]
        if notes:
            return notes

    # Strategy 2: span/div with class containing the tier name
    tier_key = header_text.split()[0].lower()  # "top", "middle", "base"
    for el in soup.select(f"[class*='{tier_key}']"):
        links = [a.get_text(strip=True) for a in el.select("a") if a.get_text(strip=True)]
        if links:
            return links

    # Strategy 3: note-img divs near the header
    for section in soup.find_all(["div", "span"], string=re.compile(header_text, re.IGNORECASE)):
        parent = section.find_parent("div")
        if parent:
            notes = [img.get("title", "").strip() for img in parent.select("img[title]")
                     if img.get("title", "").strip()]
            if notes:
                return notes

    return notes


def _parse_accords(soup: BeautifulSoup) -> list[str]:
    accords: list[str] = []
    for sel in [
        "div.accord-box div.accord-name",
        "div[class*='accord'] span",
        "span.accord-name",
    ]:
        found = [el.get_text(strip=True) for el in soup.select(sel) if el.get_text(strip=True)]
        if found:
            accords = found
            break
    return accords[:8]   # cap at 8 main accords


def _parse_gender(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True).lower()
    # Look for vote percentage text that Fragrantica shows
    masc_m = re.search(r"(\d+)%?\s*men", text)
    fem_m = re.search(r"(\d+)%?\s*wom", text)
    if masc_m and fem_m:
        masc_pct = int(masc_m.group(1))
        fem_pct = int(fem_m.group(1))
        if masc_pct > 60:
            return "masculine"
        if fem_pct > 60:
            return "feminine"
        return "unisex"
    for phrase in ["for women and men", "unisex", "for men and women"]:
        if phrase in text:
            return "unisex"
    if "for women" in text:
        return "feminine"
    if "for men" in text:
        return "masculine"
    return "unisex"


def _parse_season_votes(soup: BeautifulSoup) -> dict[str, int]:
    seasons = {"spring": 0, "summer": 0, "fall": 0, "winter": 0}
    text = soup.get_text(" ", strip=True).lower()
    for season in seasons:
        m = re.search(rf"{season}\s*[:\-]?\s*(\d+)", text)
        if m:
            seasons[season] = int(m.group(1))
    # Also look for percentage blocks near season names
    for el in soup.find_all(string=re.compile(r"spring|summer|fall|autumn|winter", re.I)):
        parent = el.find_parent()
        if not parent:
            continue
        for season, alt in [("spring", "spring"), ("summer", "summer"),
                             ("fall", "fall"), ("fall", "autumn"), ("winter", "winter")]:
            if alt in el.lower():
                # Try to grab a sibling number
                sibs = parent.find_all(string=re.compile(r"\d+"))
                for s in sibs:
                    try:
                        seasons[season] = max(seasons[season], int(s.strip()))
                    except ValueError:
                        pass
    return seasons


def _parse_occasion_votes(soup: BeautifulSoup) -> dict[str, int]:
    occasions = {
        "daily": 0, "evening": 0, "sport": 0,
        "office": 0, "night": 0, "beach": 0,
    }
    text = soup.get_text(" ", strip=True).lower()
    aliases = {
        "daily": ["daily", "day"],
        "evening": ["evening"],
        "sport": ["sport", "leisure"],
        "office": ["office", "business"],
        "night": ["night", "night out"],
        "beach": ["beach", "poolside"],
    }
    for key, words in aliases.items():
        for word in words:
            m = re.search(rf"{re.escape(word)}\s*[:\-]?\s*(\d+)", text)
            if m:
                occasions[key] = int(m.group(1))
                break
    return occasions


def _parse_rating(soup: BeautifulSoup, keyword: str, default: float = 3.0) -> float:
    """Extract a community rating (1-5 scale) by searching for keyword near a number."""
    text = soup.get_text(" ", strip=True)
    # Pattern: "Longevity: 7.72" or "longevity 4 out of 5"
    patterns = [
        rf"{keyword}[^\d]{{0,30}}(\d+\.\d+)",
        rf"{keyword}[^\d]{{0,30}}(\d)\s*/\s*5",
        rf"{keyword}[^\d]{{0,30}}(\d)\s+out",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = float(m.group(1))
            # Fragrantica shows /10 internally; convert to /5 if needed
            return round(min(5.0, raw / 2.0 if raw > 5 else raw), 2)
    return default


def scrape_perfume(url: str) -> dict | None:
    """Scrape a single perfume page. Returns None if the page is not a perfume."""
    try:
        resp = _get(url, delay=_jitter())
    except Exception as e:
        log.warning("HTTP error for %s: %s", url, e)
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    name_el = soup.select_one("h1.fn") or soup.select_one("h1[itemprop='name']")
    if not name_el:
        return None

    full_name = name_el.get_text(strip=True)

    # Brand — try several selectors
    brand = ""
    for sel in [
        "span[itemprop='brand'] span[itemprop='name']",
        "p.designer a",
        "a[href*='/designers/']",
        "span[itemprop='name']",
    ]:
        el = soup.select_one(sel)
        if el:
            brand = el.get_text(strip=True)
            break

    # Strip brand + concentration keywords from name to get clean name
    clean_name = full_name
    if brand and clean_name.startswith(brand):
        clean_name = clean_name[len(brand):].strip()

    concentration = _extract_concentration(full_name + " " + soup.get_text(" ")[:500])
    fragrantica_id = _extract_fragrantica_id(url)

    top_notes = _parse_notes_section(soup, "Top notes")
    mid_notes = _parse_notes_section(soup, "Middle notes") or _parse_notes_section(soup, "Heart notes")
    base_notes = _parse_notes_section(soup, "Base notes")
    accords = _parse_accords(soup)
    gender_vote = _parse_gender(soup)
    season_v = _parse_season_votes(soup)
    occ_v = _parse_occasion_votes(soup)
    longevity = _parse_rating(soup, "longevity")
    sillage = _parse_rating(soup, "sillage")
    overall = _parse_rating(soup, "overall") or _parse_rating(soup, "worth")

    return {
        "name": clean_name or full_name,
        "brand": brand,
        "concentration": concentration,
        "fragrantica_id": fragrantica_id,
        "fragrantica_url": url,
        "top_notes": top_notes,
        "middle_notes": mid_notes,
        "base_notes": base_notes,
        "accords": accords,
        "gender_vote": gender_vote,
        "season_spring_votes": season_v["spring"],
        "season_summer_votes": season_v["summer"],
        "season_fall_votes": season_v["fall"],
        "season_winter_votes": season_v["winter"],
        "occasion_daily_votes": occ_v["daily"],
        "occasion_evening_votes": occ_v["evening"],
        "occasion_sport_votes": occ_v["sport"],
        "occasion_office_votes": occ_v["office"],
        "occasion_night_votes": occ_v["night"],
        "occasion_beach_votes": occ_v["beach"],
        "community_longevity_rating": longevity,
        "community_sillage_rating": sillage,
        "community_overall_rating": overall,
    }


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

async def _upsert_perfume(data: dict) -> str:
    """Insert or update a perfume row. Returns 'inserted' or 'updated'."""
    from sqlalchemy import select
    from models.database import AsyncSessionLocal, init_db
    from models.perfume import Perfume

    async with AsyncSessionLocal() as session:
        stmt = None
        existing = None

        if data.get("fragrantica_id"):
            result = await session.execute(
                select(Perfume).where(Perfume.fragrantica_id == data["fragrantica_id"])
            )
            existing = result.scalar_one_or_none()

        if existing is None:
            # Also try name + brand + concentration match
            result = await session.execute(
                select(Perfume).where(
                    Perfume.name == data["name"],
                    Perfume.brand == data["brand"],
                    Perfume.concentration == data["concentration"],
                )
            )
            existing = result.scalar_one_or_none()

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.scraped_at = datetime.now(timezone.utc)
            await session.commit()
            return "updated"
        else:
            perfume = Perfume(**data, scraped_at=datetime.now(timezone.utc))
            session.add(perfume)
            await session.commit()
            return "inserted"


async def _db_count() -> int:
    from sqlalchemy import func, select
    from models.database import AsyncSessionLocal
    from models.perfume import Perfume
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(Perfume))
        return result.scalar_one()


async def _all_db_notes() -> set[str]:
    """Return all note names referenced in perfume pyramids in the DB."""
    from sqlalchemy import select
    from models.database import AsyncSessionLocal
    from models.perfume import Perfume
    names: set[str] = set()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Perfume.top_notes, Perfume.middle_notes, Perfume.base_notes))
        for top, mid, base in result.all():
            for n in (top or []) + (mid or []) + (base or []):
                names.add(n.strip())
    return names


# ---------------------------------------------------------------------------
# Bulk scrape orchestrator
# ---------------------------------------------------------------------------

def run_bulk(limit: int) -> None:
    print(f"[bulk] Collecting up to {limit} perfume URLs from Fragrantica…")
    urls = _collect_perfume_urls(limit)
    print(f"[bulk] Collected {len(urls)} unique URLs. Starting scrape…")

    # Ensure DB tables exist
    asyncio.run(_ensure_db())

    scraped = 0
    errors: list[str] = []

    for i, url in enumerate(urls, 1):
        try:
            data = scrape_perfume(url)
            if data and data.get("name") and data.get("brand"):
                action = asyncio.run(_upsert_perfume(data))
                scraped += 1
                if scraped % 10 == 0:
                    print(f"[bulk] Scraped {scraped}/{len(urls)} perfumes… (last: {data['brand']} {data['name']})")
            else:
                errors.append(url)
                log.warning("Skipped (no name/brand): %s", url)
        except Exception as e:
            errors.append(url)
            log.warning("Error scraping %s: %s", url, e)

    total_in_db = asyncio.run(_db_count())
    print(
        f"\n[bulk] Done.\n"
        f"  Total scraped this run : {scraped}\n"
        f"  Total errors           : {len(errors)}\n"
        f"  Total perfumes in DB   : {total_in_db}"
    )
    if errors:
        print(f"  Failed URLs logged to stderr (first 5):")
        for u in errors[:5]:
            print(f"    {u}")


async def _ensure_db() -> None:
    from models.database import init_db
    await init_db()


# ---------------------------------------------------------------------------
# Notes expansion
# ---------------------------------------------------------------------------

# Family defaults: what properties to assign to an auto-estimated note
_FAMILY_DEFAULTS: dict[str, dict] = {
    "citrus":    {"volatility": 9, "heat_performance": 4, "cold_performance": 5, "humidity_performance": 5, "dry_performance": 7, "skin_bonding": 3, "dry_skin_boost": 3, "oily_skin_boost": 3, "projection_strength": 6, "longevity_class": 1},
    "floral":    {"volatility": 6, "heat_performance": 6, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 6, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 6, "longevity_class": 3},
    "woody":     {"volatility": 3, "heat_performance": 7, "cold_performance": 7, "humidity_performance": 6, "dry_performance": 8, "skin_bonding": 8, "dry_skin_boost": 8, "oily_skin_boost": 7, "projection_strength": 6, "longevity_class": 4},
    "earthy":    {"volatility": 2, "heat_performance": 7, "cold_performance": 7, "humidity_performance": 6, "dry_performance": 8, "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 7, "projection_strength": 6, "longevity_class": 5},
    "oriental":  {"volatility": 2, "heat_performance": 8, "cold_performance": 7, "humidity_performance": 7, "dry_performance": 8, "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 8, "projection_strength": 8, "longevity_class": 5},
    "gourmand":  {"volatility": 3, "heat_performance": 7, "cold_performance": 8, "humidity_performance": 6, "dry_performance": 7, "skin_bonding": 8, "dry_skin_boost": 9, "oily_skin_boost": 7, "projection_strength": 7, "longevity_class": 4},
    "chypre":    {"volatility": 3, "heat_performance": 6, "cold_performance": 8, "humidity_performance": 6, "dry_performance": 7, "skin_bonding": 8, "dry_skin_boost": 8, "oily_skin_boost": 7, "projection_strength": 7, "longevity_class": 5},
    "fougere":   {"volatility": 5, "heat_performance": 6, "cold_performance": 7, "humidity_performance": 6, "dry_performance": 7, "skin_bonding": 6, "dry_skin_boost": 7, "oily_skin_boost": 6, "projection_strength": 7, "longevity_class": 3},
    "aquatic":   {"volatility": 8, "heat_performance": 6, "cold_performance": 4, "humidity_performance": 8, "dry_performance": 5, "skin_bonding": 3, "dry_skin_boost": 4, "oily_skin_boost": 3, "projection_strength": 6, "longevity_class": 2},
    "spicy":     {"volatility": 6, "heat_performance": 7, "cold_performance": 7, "humidity_performance": 5, "dry_performance": 7, "skin_bonding": 6, "dry_skin_boost": 6, "oily_skin_boost": 5, "projection_strength": 7, "longevity_class": 3},
    "green":     {"volatility": 7, "heat_performance": 5, "cold_performance": 6, "humidity_performance": 6, "dry_performance": 6, "skin_bonding": 4, "dry_skin_boost": 5, "oily_skin_boost": 4, "projection_strength": 6, "longevity_class": 2},
    "powdery":   {"volatility": 4, "heat_performance": 5, "cold_performance": 7, "humidity_performance": 5, "dry_performance": 7, "skin_bonding": 7, "dry_skin_boost": 8, "oily_skin_boost": 5, "projection_strength": 5, "longevity_class": 4},
    "smoky":     {"volatility": 3, "heat_performance": 6, "cold_performance": 8, "humidity_performance": 5, "dry_performance": 8, "skin_bonding": 8, "dry_skin_boost": 8, "oily_skin_boost": 7, "projection_strength": 7, "longevity_class": 4},
    "resinous":  {"volatility": 2, "heat_performance": 8, "cold_performance": 7, "humidity_performance": 7, "dry_performance": 8, "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 7, "projection_strength": 7, "longevity_class": 5},
    "musky":     {"volatility": 3, "heat_performance": 7, "cold_performance": 6, "humidity_performance": 7, "dry_performance": 7, "skin_bonding": 8, "dry_skin_boost": 8, "oily_skin_boost": 7, "projection_strength": 6, "longevity_class": 4},
    "animalic":  {"volatility": 2, "heat_performance": 8, "cold_performance": 7, "humidity_performance": 8, "dry_performance": 8, "skin_bonding": 10, "dry_skin_boost": 9, "oily_skin_boost": 9, "projection_strength": 8, "longevity_class": 5},
    "fresh":     {"volatility": 8, "heat_performance": 5, "cold_performance": 5, "humidity_performance": 6, "dry_performance": 7, "skin_bonding": 4, "dry_skin_boost": 4, "oily_skin_boost": 4, "projection_strength": 6, "longevity_class": 2},
}

_FAMILY_KEYWORDS: dict[str, list[str]] = {
    "citrus":   ["lemon", "lime", "orange", "bergamot", "grapefruit", "mandarin", "yuzu", "citron", "neroli", "tangerine", "clementine", "pomelo", "blood orange", "bitter orange"],
    "floral":   ["rose", "jasmine", "violet", "iris", "lavender", "lilac", "peony", "magnolia", "lily", "orchid", "tuberose", "mimosa", "ylang", "narcissus", "carnation", "hyacinth", "freesia", "gardenia", "geranium", "heliotrope", "cherry blossom", "elderflower"],
    "woody":    ["cedar", "sandalwood", "oud", "vetiver", "guaiac", "cashmere wood", "birch", "rosewood", "teak", "agarwood", "ebony", "driftwood", "mahogany"],
    "earthy":   ["patchouli", "moss", "earth", "soil", "mushroom", "truffle", "oakmoss", "labdanum", "cistus", "bark"],
    "oriental": ["amber", "incense", "myrrh", "benzoin", "saffron", "oud", "balsam", "coumarin", "tonka"],
    "gourmand": ["vanilla", "chocolate", "caramel", "coffee", "almond", "praline", "honey", "sugar", "cream", "milk", "coconut", "hazelnut", "marzipan", "butterscotch", "waffle", "pastry"],
    "spicy":    ["pepper", "cardamom", "ginger", "cinnamon", "clove", "nutmeg", "cumin", "anise", "star anise", "bay", "saffron", "chili", "pink pepper", "black pepper", "white pepper"],
    "aquatic":  ["marine", "sea", "ocean", "water", "calone", "salt", "aquatic", "ozonic", "watery"],
    "musky":    ["musk", "ambroxan", "ambergris", "galaxolide", "iso e", "hedione", "civettone"],
    "animalic": ["civet", "castoreum", "ambergris", "musk", "leather", "fur"],
    "smoky":    ["smoke", "leather", "tar", "tobacco", "burnt", "birch tar", "fire", "gunpowder", "ash"],
    "resinous": ["frankincense", "labdanum", "cistus", "elemi", "benzoin", "myrrh", "balsam", "styrax", "resin", "galbanum"],
    "green":    ["grass", "leaf", "fern", "bamboo", "tea", "herb", "vetiver", "basil", "sage", "mint", "rosemary", "thyme", "eucalyptus", "pine", "fig leaf", "violet leaf", "tomato leaf"],
    "powdery":  ["iris", "violet", "orris", "talc", "cosmetic", "aldehyde"],
    "fresh":    ["mint", "ozonic", "clean", "air", "breeze", "rain", "dew"],
    "fougere":  ["fougere", "coumarin", "oakmoss", "lavender", "geranium"],
    "chypre":   ["chypre", "oakmoss", "labdanum", "bergamot", "cistus"],
}


def _classify_family(note_name: str) -> str:
    """Classify a note into an olfactory family from its name."""
    name_lower = note_name.lower()
    scores: dict[str, int] = {}
    for family, keywords in _FAMILY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in name_lower)
        if score:
            scores[family] = score
    if scores:
        return max(scores, key=scores.__getitem__)
    # Last-resort heuristics
    if any(c in name_lower for c in ["wood", "tree", "bark"]):
        return "woody"
    if any(c in name_lower for c in ["flower", "blossom", "petal"]):
        return "floral"
    if any(c in name_lower for c in ["fruit", "berry", "apple", "pear", "peach", "plum"]):
        return "fresh"
    return "fresh"   # safest generic default


def _build_note_entry(note_name: str) -> dict:
    family = _classify_family(note_name)
    props = dict(_FAMILY_DEFAULTS.get(family, _FAMILY_DEFAULTS["fresh"]))
    return {"name": note_name, "family": family, **props}


def run_notes_expansion(limit: int) -> None:
    """Collect new notes from DB perfumes and append to notes_chemistry.json."""
    if not NOTES_PATH.exists():
        print(f"[notes] notes_chemistry.json not found at {NOTES_PATH}")
        return

    with open(NOTES_PATH) as f:
        existing: list[dict] = json.load(f)

    existing_names_lower = {n["name"].lower() for n in existing}
    print(f"[notes] Existing notes: {len(existing)}")

    # Collect note names from DB
    try:
        db_note_names: set[str] = asyncio.run(_all_db_notes())
        print(f"[notes] Unique notes found in DB perfume pyramids: {len(db_note_names)}")
    except Exception as e:
        log.warning("Could not query DB (is it running?): %s — falling back to seed JSON only.", e)
        # Fall back to seed perfumes JSON
        seed_path = DATA_DIR / "seed_perfumes.json"
        db_note_names = set()
        if seed_path.exists():
            with open(seed_path) as f:
                for p in json.load(f):
                    for tier in ("top_notes", "middle_notes", "base_notes"):
                        db_note_names.update(p.get(tier, []))

    new_notes: list[dict] = []
    count = 0
    for name in sorted(db_note_names):
        if count >= limit:
            break
        if name.lower() not in existing_names_lower:
            entry = _build_note_entry(name)
            new_notes.append(entry)
            existing_names_lower.add(name.lower())
            count += 1

    if new_notes:
        updated = existing + new_notes
        with open(NOTES_PATH, "w") as f:
            json.dump(updated, f, indent=2)
        print(f"[notes] Added {len(new_notes)} new notes. Total now: {len(updated)}")
        for n in new_notes[:10]:
            print(f"  + {n['name']} ({n['family']})")
        if len(new_notes) > 10:
            print(f"  … and {len(new_notes) - 10} more")
    else:
        print("[notes] No new notes to add — notes_chemistry.json is up to date.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fragrantica scraper for ScentScience",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m scrapers.fragrantica --name \"Sauvage\" --brand \"Dior\"\n"
            "  python -m scrapers.fragrantica --bulk --limit 500\n"
            "  python -m scrapers.fragrantica --notes --limit 300\n"
        ),
    )
    parser.add_argument("--name", help="Perfume name for single lookup")
    parser.add_argument("--brand", default=None, help="Brand name (optional, for single lookup)")
    parser.add_argument("--bulk", action="store_true", help="Enable bulk scraping mode")
    parser.add_argument("--notes", action="store_true", help="Expand notes_chemistry.json with new notes")
    parser.add_argument("--limit", type=int, default=100, help="Max perfumes (bulk) or notes (notes) to process")
    args = parser.parse_args()

    if args.bulk:
        run_bulk(args.limit)
    elif args.notes:
        run_notes_expansion(args.limit)
    elif args.name:
        results = search_perfume(args.name, args.brand)
        if not results:
            print("No results found.")
        else:
            data = scrape_perfume(results[0]["url"])
            print(json.dumps(data, indent=2))
    else:
        parser.print_help()
