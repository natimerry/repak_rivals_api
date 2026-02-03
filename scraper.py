import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://marvelrivals.fandom.com/wiki"
HEROES_URL = f"{BASE}/Heroes"

CACHE_DIR = Path("cache")
CACHE_TTL_SECONDS = 2 * 60 * 60  # 2 hours


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://marvelrivals.fandom.com/",
}

@dataclass
class Hero:
    name: str
    url: str
    id: Optional[str]


@dataclass
class HeroSkin:
    base_hero: Hero
    name: str
    url: str
    id: Optional[str]


def get_soup(url: str) -> BeautifulSoup:
    
    r = requests.get(
        url,
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


class Cache:
    """Simple file-based cache with TTL"""

    def __init__(self, cache_dir: Path = CACHE_DIR, ttl: int = CACHE_TTL_SECONDS):
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.cache_dir.mkdir(exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Convert cache key to safe filename"""
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[dict]:
        """Get cached data if valid, else None"""
        path = self._get_path(key)

        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if cache is still valid
            age = time.time() - data.get("timestamp", 0)
            if age >= self.ttl:
                return None

            return data.get("payload")
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, payload: dict) -> None:
        """Save data to cache"""
        path = self._get_path(key)
        data = {"timestamp": time.time(), "payload": payload}

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# Global cache instance
cache = Cache()


def fetch_heroes() -> List[Hero]:
    soup = get_soup(HEROES_URL)
    heroes: List[Hero] = []

    for a in soup.select(".herocard-link a"):
        name = a.get_text(strip=True)
        href = urljoin(BASE, a["href"])
        heroes.append(Hero(name=name, url=href, id=None))

    return heroes


def get_heroes() -> List[Hero]:
    """Get heroes with caching"""
    cached = cache.get("heroes")
    if cached:
        return [Hero(**item) for item in cached]

    heroes = fetch_heroes()
    cache.set("heroes", [asdict(h) for h in heroes])
    return heroes


def extract_skin_id(soup) -> Optional[str]:
    """Extract skin ID from the character table"""
    # Look for tables with character info
    tables = soup.select(
        "table.char-table-chronology, table.char-table-epic, table.char-table-legendary, table.char-table-rare"
    )

    for table in tables:
        # Find all rows in the table
        rows = table.select("tr")

        for row in rows:
            # Look for a <th> containing "ID NO."
            th_elements = row.select("th")
            for th in th_elements:
                th_text = th.get_text(strip=True)
                if "ID NO." in th_text or "ID_NO." in th_text or th_text == "ID NO.":
                    # Found the ID row - now get the td in the same row
                    td_elements = row.select("td")
                    for td in td_elements:
                        text = td.get_text(strip=True)
                        # Make sure it's a valid ID (7-8 digits typically)
                        if text.isdigit() and len(text) >= 6:
                            return str(text)

    return None


def fetch_hero_skins(hero: Hero) -> List[HeroSkin]:
    """Fetch skins for a hero (no caching here)"""
    soup = get_soup(hero.url)
    skins: List[HeroSkin] = []

    # Find all tab content sections (both Catalog and Recolor tabs)
    tab_contents = soup.select(".wds-tab__content")

    for tab_content in tab_contents:
        anchors = tab_content.select(".charcat-wrapper a[href^='/wiki/']")

        for a in anchors:
            name = a.get("title", "").strip()

            href = a.get("href", "")
            if not name or not href:
                continue

            href = urljoin(BASE, href)

            # Follow the href to get the skin id
            try:
                skin_soup = get_soup(href)
                skin_id = extract_skin_id(skin_soup)
            except Exception as e:
                print(f"Error fetching skin page for {name}: {e}")
                skin_id = None

            if f"(battlepass)" in name.lower() or "Twitch" in name:
                continue

            if skin_id is None:
                continue

            if f"({hero.name})" in name:
                name = name.replace(f"({hero.name})", "").strip()

            skins.append(
                HeroSkin(
                    base_hero=hero,
                    name=name,
                    url=href,
                    id=skin_id,
                )
            )

    skins.append(
        HeroSkin(
            base_hero=hero,
            name=f"{hero.name} (Default)",
            url=hero.url,
            id=f"{skins[0].id[:4]}001",
        )
    )

    hero.id = hero.id or f"{skins[0].id[:4]}001"

    return skins


def get_hero_skins(hero: Hero) -> List[HeroSkin]:
    """Get skins for a hero with caching"""
    cache_key = f"skins_{hero.name}"
    cached = cache.get(cache_key)
    if cached:
        # Reconstruct HeroSkin objects from cached data
        return [
            HeroSkin(
                base_hero=hero,
                name=item["skin_name"],
                url=item["url"],
                id=item["skinid"],
            )
            for item in cached
        ]
    skins = fetch_hero_skins(hero)
    # Cache the skins (without the full hero object to avoid circular refs)
    cache.set(
        cache_key,
        [
            {
                "name": skin.base_hero.name,
                "id": skin.base_hero.id,
                "url": skin.url,
                "skinid": skin.id,
                "skin_name": skin.name,
            }
            for skin in skins
        ],
    )
    return skins


if __name__ == "__main__":
    heroes = get_heroes()
    print(f"Found {len(heroes)} heroes")

    for hero in heroes:
        print(f"\n{hero.name}:")
        skins = get_hero_skins(hero)
        for skin in skins:
            print(f"  - {skin.name} (ID: {skin.id})")
