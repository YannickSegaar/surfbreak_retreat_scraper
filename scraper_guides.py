"""
Guide Profile Scraper
=====================

Scrapes individual guide/teacher profile pages from retreat.guru.
This provides MORE RELIABLE data than extracting from event pages because:
1. Full biography text (not truncated)
2. All credentials listed
3. Photo URL
4. Affiliated center information
5. List of upcoming retreats

URL Pattern: https://retreat.guru/teachers/{center_id}-{teacher_id}/{name-slug}

USAGE:
------
from scraper_guides import GuideProfileScraper, GuideProfile

async with GuideProfileScraper() as scraper:
    guide = await scraper.scrape_guide_page("https://retreat.guru/teachers/156-93/shane-christopher-perkins")
    print(guide.name, guide.credentials, guide.bio[:100])
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://retreat.guru"
PAGE_DELAY = 1.0  # seconds between pages
REQUEST_TIMEOUT = 30  # seconds


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GuideProfile:
    """Represents a guide/teacher profile scraped from their dedicated page."""

    # Core identification
    teacher_id: str = ""               # From URL: /teachers/{id}/ (e.g., "156-93")
    guide_id: str = ""                 # SHA256(name:profile_path)[:12]
    profile_url: str = ""              # Full URL to profile page

    # Basic info
    name: str = ""                     # Full name (without credentials)
    credentials: str = ""              # E-RYT 500, YACEP, etc.
    role: str = "Guide"                # Default role

    # Detailed info
    bio: str = ""                      # Full biography text
    photo_url: str = ""                # Profile photo URL

    # Ratings and reviews
    rating: float = 0.0                # Guide rating (if available)
    review_count: int = 0              # Number of reviews

    # Affiliations
    affiliated_center: str = ""        # Center name
    affiliated_center_url: str = ""    # Center page URL
    affiliated_center_id: str = ""     # Center ID from URL

    # Upcoming retreats this guide is leading
    upcoming_retreats: list = field(default_factory=list)  # [{title, dates, url}]


@dataclass
class GuideScraperStats:
    """Track guide scraping statistics."""
    total_guides: int = 0
    scraped: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_teacher_id(url: str) -> str:
    """
    Extract teacher ID from /teachers/{id}/ URL pattern.

    Example:
        URL: https://retreat.guru/teachers/156-93/shane-perkins
        Returns: "156-93"
    """
    if not url:
        return ""
    match = re.search(r'/teachers/([^/]+)/', url)
    return match.group(1) if match else ""


def extract_center_id(url: str) -> str:
    """
    Extract center ID from /centers/{id}/ URL pattern.

    Example:
        URL: https://retreat.guru/centers/156/fitflow-yoga-tulum
        Returns: "156"
    """
    if not url:
        return ""
    match = re.search(r'/centers/([^/]+)/', url)
    return match.group(1) if match else ""


def generate_guide_id(name: str, profile_url: str = "") -> str:
    """
    Generate unique ID for a guide based on name and profile URL.

    This allows deduplication of guides across retreats and centers.
    """
    # Normalize name
    name_normalized = name.lower().strip()

    # Include profile URL path for uniqueness
    if profile_url:
        if "/teachers/" in profile_url:
            path = profile_url.split("/teachers/")[-1]
        elif "/teacher/" in profile_url:
            path = profile_url.split("/teacher/")[-1]
        else:
            path = profile_url
        key = f"{name_normalized}:{path}"
    else:
        key = name_normalized

    # Create hash
    hash_obj = hashlib.sha256(key.encode("utf-8"))
    return hash_obj.hexdigest()[:12]


def parse_name_and_credentials(full_text: str) -> tuple[str, str]:
    """
    Parse a name string that may include credentials.

    Examples:
    - "Shane-Christopher Perkins, E-RYT 500, YACEP®" -> ("Shane-Christopher Perkins", "E-RYT 500, YACEP®")
    - "Sarah Jones" -> ("Sarah Jones", "")
    """
    # Common credential patterns
    credential_patterns = [
        r',?\s*(E-RYT\s*\d+)',
        r',?\s*(RYT\s*\d+)',
        r',?\s*(YACEP®?)',
        r',?\s*(CYT)',
        r',?\s*(PhD)',
        r',?\s*(MA|MS|MBA)',
        r',?\s*(LMT)',
        r',?\s*(Reiki\s+Master)',
    ]

    credentials = []
    name = full_text.strip()

    for pattern in credential_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            credentials.append(match.group(1).strip())
            name = name[:match.start()] + name[match.end():]

    # Clean up name
    name = re.sub(r',\s*$', '', name.strip())
    name = re.sub(r'\s+', ' ', name)

    return name.strip(), ", ".join(credentials)


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class GuideProfileScraper:
    """Scrapes individual guide profile pages from retreat.guru."""

    def __init__(self):
        self.browser = None
        self.page = None
        self.stats = GuideScraperStats()
        self.scraped_guides: dict[str, GuideProfile] = {}  # Cache by profile URL

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_guide_page(self, url: str) -> GuideProfile | None:
        """
        Scrape a single guide profile page.

        Args:
            url: Full URL to the guide's profile page (e.g., /teachers/156-93/name-slug)

        Returns:
            GuideProfile object or None if scraping failed
        """
        # Check cache
        if url in self.scraped_guides:
            return self.scraped_guides[url]

        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)

            html = await self.page.content()
            guide = self._parse_guide_page(html, url)

            if guide:
                self.scraped_guides[url] = guide
                self.stats.scraped += 1

            return guide

        except Exception as e:
            error_msg = f"Error scraping {url}: {str(e)[:50]}"
            print(f"  {error_msg}")
            self.stats.errors += 1
            self.stats.error_messages.append(error_msg)
            return None

    def _parse_guide_page(self, html: str, url: str) -> GuideProfile | None:
        """Parse guide profile HTML and extract data."""
        soup = BeautifulSoup(html, "lxml")

        guide = GuideProfile()
        guide.profile_url = url
        guide.teacher_id = extract_teacher_id(url)

        # Name and credentials from H1
        h1 = soup.select_one("h1")
        if h1:
            full_name = h1.get_text(strip=True)
            guide.name, guide.credentials = parse_name_and_credentials(full_name)
        else:
            # Try to extract from URL slug as fallback
            if "/teachers/" in url:
                slug = url.split("/teachers/")[-1].split("/")[-1]
                guide.name = slug.replace("-", " ").title()

        if not guide.name:
            return None  # Can't proceed without a name

        # Generate guide ID (hash-based)
        guide.guide_id = generate_guide_id(guide.name, url)

        # Bio from "About the Teacher" section
        # Try multiple selectors for bio content
        bio_selectors = [
            "section:has(h2:contains('About the Teacher'))",
            "[class*='about']",
            "[class*='bio']",
            "[class*='description']",
            "article p",
        ]

        for selector in bio_selectors:
            try:
                bio_elem = soup.select_one(selector)
                if bio_elem:
                    bio_text = bio_elem.get_text(strip=True)
                    # Filter out very short or nav-like content
                    if len(bio_text) > 100:
                        guide.bio = bio_text[:2000]  # Cap at 2000 chars
                        break
            except Exception:
                continue

        # If no bio found, try paragraphs after "About" header
        if not guide.bio:
            about_headers = soup.find_all(["h2", "h3"], string=re.compile(r"about", re.I))
            for header in about_headers:
                next_p = header.find_next("p")
                if next_p:
                    text = next_p.get_text(strip=True)
                    if len(text) > 50:
                        guide.bio = text[:2000]
                        break

        # Profile photo - ENHANCED with more selectors and srcset support
        photo_selectors = [
            # data-cy attributes (most reliable if present)
            "img[data-cy='teacher-avatar']",
            "img[data-cy='teacher-photo']",
            "img[data-cy='profile-photo']",
            "img[data-cy='teacher-image']",

            # Class-based selectors
            "img.teacher-avatar",
            "img.profile-avatar",
            "img[class*='avatar']",
            "img[class*='profile-image']",
            "img[class*='teacher-photo']",
            "img[class*='teacher-image']",

            # Structural (within known containers)
            ".teacher-profile img",
            ".profile-header img",
            "[class*='teacher'] img[class*='avatar']",
            "[class*='profile'] img",
            "header img",

            # More general selectors (last resort)
            "article img:first-of-type",
            "main img:first-of-type",
            "img[alt*='teacher' i]",
            "img[alt*='instructor' i]",
            "img[alt*='guide' i]",
        ]

        for selector in photo_selectors:
            try:
                img = soup.select_one(selector)
                if img:
                    # Check for src or srcset (handle responsive images)
                    src = img.get("src") or ""
                    srcset = img.get("srcset", "")

                    # If srcset exists, extract the first/largest URL
                    if srcset and not src:
                        # srcset format: "url1 1x, url2 2x" or "url1 480w, url2 800w"
                        first_src = srcset.split(",")[0].strip().split()[0]
                        src = first_src

                    if src:
                        # Skip tiny icons, logos, placeholders
                        skip_patterns = ["icon", "logo", "svg", "placeholder", "default", "avatar-default", "1x1", "loading"]
                        if not any(x in src.lower() for x in skip_patterns):
                            # Clean up URL (remove query params for cleaner URL)
                            clean_src = src.split("?")[0]
                            guide.photo_url = urljoin(BASE_URL, clean_src)
                            break
            except Exception:
                continue

        # Rating and review count for guide
        rating_selectors = [
            "[data-cy='teacher-rating']",
            "[class*='rating']",
            "[class*='stars']",
            "[class*='review-score']",
        ]

        for selector in rating_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    # Parse rating like "4.8" or "4.8/5"
                    rating_match = re.search(r'(\d+\.?\d*)', text)
                    if rating_match:
                        guide.rating = float(rating_match.group(1))
                        break
            except Exception:
                continue

        # Review count
        page_text = soup.get_text()
        review_patterns = [
            r'(\d+)\s*reviews?',
            r'(\d+)\s*ratings?',
            r'\((\d+)\s*reviews?\)',
        ]

        for pattern in review_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                try:
                    guide.review_count = int(match.group(1))
                    break
                except ValueError:
                    pass

        # Affiliated center
        center_link = soup.select_one("a[href*='/centers/']")
        if center_link:
            guide.affiliated_center = center_link.get_text(strip=True)
            center_href = center_link.get("href", "")
            guide.affiliated_center_url = urljoin(BASE_URL, center_href)
            guide.affiliated_center_id = extract_center_id(guide.affiliated_center_url)

        # Upcoming retreats
        retreat_tiles = soup.select(".event-tile, [class*='retreat'], [class*='event']")[:10]
        for tile in retreat_tiles:
            title_elem = tile.select_one("h2, h3, h4, [class*='title']")
            link_elem = tile.select_one("a[href*='/events/']")
            date_elem = tile.select_one("[class*='date']")

            if title_elem and link_elem:
                retreat = {
                    "title": title_elem.get_text(strip=True),
                    "url": urljoin(BASE_URL, link_elem.get("href", "")),
                    "dates": date_elem.get_text(strip=True) if date_elem else ""
                }
                guide.upcoming_retreats.append(retreat)

        return guide

    async def scrape_multiple_guides(
        self,
        guide_urls: list[str],
        skip_urls: set[str] = None
    ) -> list[GuideProfile]:
        """
        Scrape multiple guide profile pages.

        Args:
            guide_urls: List of guide profile URLs to scrape
            skip_urls: Set of URLs to skip (already scraped)

        Returns:
            List of GuideProfile objects
        """
        skip_urls = skip_urls or set()
        guides = []

        # Deduplicate and filter
        unique_urls = []
        seen = set()
        for url in guide_urls:
            if url not in seen and url not in skip_urls:
                seen.add(url)
                unique_urls.append(url)

        self.stats.total_guides = len(unique_urls)
        self.stats.skipped = len(guide_urls) - len(unique_urls)

        print(f"\nScraping {len(unique_urls)} guide profiles...")
        if self.stats.skipped > 0:
            print(f"  (Skipping {self.stats.skipped} already-scraped or duplicate URLs)")

        for i, url in enumerate(unique_urls):
            print(f"  [{i+1}/{len(unique_urls)}] {url[:60]}...")

            guide = await self.scrape_guide_page(url)
            if guide:
                guides.append(guide)
                print(f"    -> {guide.name} ({guide.credentials or 'no credentials'})")

            # Rate limiting
            await asyncio.sleep(PAGE_DELAY)

        return guides

    def get_all_guides(self) -> list[GuideProfile]:
        """Return all scraped guides from cache."""
        return list(self.scraped_guides.values())

    def print_summary(self) -> None:
        """Print scraping summary."""
        print("\n" + "=" * 60)
        print("GUIDE SCRAPING SUMMARY")
        print("=" * 60)
        print(f"   Total guide URLs:     {self.stats.total_guides}")
        print(f"   Successfully scraped: {self.stats.scraped}")
        print(f"   Skipped (duplicates): {self.stats.skipped}")
        print(f"   Errors:               {self.stats.errors}")
        print("=" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Test the guide profile scraper."""
    print("=" * 60)
    print("GUIDE PROFILE SCRAPER TEST")
    print("=" * 60)

    test_urls = [
        "https://retreat.guru/teachers/156-93/shane-christopher-perkins-e-ryt-500-yacep",
        "https://retreat.guru/teachers/156-495/mercy-ananda",
    ]

    async with GuideProfileScraper() as scraper:
        guides = await scraper.scrape_multiple_guides(test_urls)

        print("\n" + "-" * 60)
        print("RESULTS:")
        print("-" * 60)

        for guide in guides:
            print(f"\nGuide: {guide.name}")
            print(f"  ID: {guide.guide_id}")
            print(f"  Credentials: {guide.credentials or 'None'}")
            print(f"  Bio: {guide.bio[:100]}..." if guide.bio else "  Bio: None")
            print(f"  Photo: {guide.photo_url[:50]}..." if guide.photo_url else "  Photo: None")
            print(f"  Center: {guide.affiliated_center or 'None'}")
            print(f"  Upcoming retreats: {len(guide.upcoming_retreats)}")

        scraper.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
