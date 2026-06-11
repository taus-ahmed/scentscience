"""
Fragrantica scraper — fetch perfume note data.
Respects rate limits. For educational / personal use only.
Run: python scrapers/fragrantica.py --name "Sauvage" --brand "Dior"
"""
import time
import re
import json
import argparse
import requests
from bs4 import BeautifulSoup
from tenacity import retry, wait_fixed, stop_after_attempt
from config import get_settings

settings = get_settings()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_URL = "https://www.fragrantica.com"


@retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
def _get(url: str) -> requests.Response:
    time.sleep(settings.fragrantica_scrape_delay)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp


def search_perfume(name: str, brand: str | None = None) -> list[dict]:
    query = f"{brand} {name}".strip() if brand else name
    url = f"{BASE_URL}/search/?query={requests.utils.quote(query)}"
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for item in soup.select("div.cell.card.fr-news-box")[:5]:
        a = item.select_one("a")
        if a:
            results.append({
                "name": a.get_text(strip=True),
                "url": BASE_URL + a["href"] if a["href"].startswith("/") else a["href"],
            })
    return results


def scrape_perfume(url: str) -> dict | None:
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    def extract_notes(section_text: str) -> list[str]:
        section = soup.find("b", string=re.compile(section_text, re.IGNORECASE))
        if not section:
            return []
        parent = section.find_parent()
        if not parent:
            return []
        return [a.get_text(strip=True) for a in parent.select("a") if a.get_text(strip=True)]

    name_el = soup.select_one("h1.fn")
    brand_el = soup.select_one("span[itemprop='name']")
    if not name_el:
        return None

    return {
        "name": name_el.get_text(strip=True),
        "brand": brand_el.get_text(strip=True) if brand_el else "",
        "fragrantica_url": url,
        "top_notes": extract_notes("top notes"),
        "middle_notes": extract_notes("middle notes"),
        "base_notes": extract_notes("base notes"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--brand", default=None)
    args = parser.parse_args()

    results = search_perfume(args.name, args.brand)
    if not results:
        print("No results found.")
    else:
        data = scrape_perfume(results[0]["url"])
        print(json.dumps(data, indent=2))
