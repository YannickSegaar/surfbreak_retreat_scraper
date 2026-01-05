"""
Surfbreak Retreat Scraper
=========================

Scrapes retreat listings from retreat.guru to build a lead generation database.

PHASE 1: Scrape search results for basic info + center URLs
PHASE 2: Scrape center pages for detailed address info
PHASE 3: (Optional) AI extraction for descriptions, group sizes, and guides

PAGE STRUCTURE ANALYSIS:
------------------------
Search Page:
- Main tile container: article.search-event-tile
- Title: h2 inside .search-event-tile__content
- Center URL: a[href*='/centers/'] - format: /centers/{center_id}-{num}/{slug}
- Location: .search-event-tile__location (city, country)
- Dates: .search-event-tile__dates
- Price: .search-event-tile__price
- Reviews: .search-event-tile__reviews

Center Page:
- Center name: h1
- Detailed address: [data-cy='center-location']
- Description: .center-description (if exists)

Event Page (for AI extraction):
- About This Retreat section
- Your Guides section
- Group size information
"""

import asyncio
import json
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from openai import OpenAI
from playwright.async_api import async_playwright


# =============================================================================
# ENTITY ID EXTRACTION FUNCTIONS
# =============================================================================

def extract_event_id(url: str) -> str:
    """
    Extract event ID from /events/{id}/ URL pattern.

    Example:
        URL: https://retreat.guru/events/156-1449/fitflow-yoga
        Returns: "156-1449"
    """
    if not url:
        return ""
    match = re.search(r'/events/([^/]+)/', url)
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


# =============================================================================
# CONFIGURATION
# =============================================================================

SEARCH_URL = "https://retreat.guru/search?topic=yoga&country=mexico"
BASE_URL = "https://retreat.guru"

# Delays (be respectful to the server)
PAGE_DELAY = 1.0  # seconds between pages
REQUEST_TIMEOUT = 30  # seconds

# Output file
OUTPUT_FILE = "leads_enriched.csv"

# Whether to scrape center pages for detailed addresses (slower but more data)
ENRICH_WITH_CENTER_DATA = True

# Whether to use AI extraction for enhanced data (requires OPENAI_API_KEY)
USE_AI_EXTRACTION = True


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RetreatLead:
    """Represents a single retreat listing with enriched data."""

    # Entity IDs (for deduplication and linking)
    event_id: str = ""            # From URL: /events/{id}/
    center_id: str = ""           # From URL: /centers/{id}/

    # From search page
    title: str = ""
    organizer: str = ""           # Center/venue name
    location_city: str = ""       # City, Country (from search)
    dates: str = ""
    price: str = ""
    event_url: str = ""
    center_url: str = ""          # URL to center page

    # Ratings and reviews
    event_rating: float = 0.0
    event_review_count: int = 0
    center_rating: float = 0.0
    center_review_count: int = 0

    # From center page (enriched data)
    detailed_address: str = ""    # Full street address
    center_description: str = ""  # About the center
    center_photo_url: str = ""    # Center profile picture/avatar
    google_maps_url: str = ""     # Direct Google Maps URL

    # For Google Maps lookup (legacy)
    search_query: str = ""        # Pre-formatted search query

    # Enhanced data (from AI extraction)
    retreat_description: str = ""  # About this retreat
    group_size: int | None = None  # Max participants
    guides_json: str = ""          # JSON array of guide info
    guide_ids: list = field(default_factory=list)  # List of guide IDs for linking


@dataclass
class ScraperStats:
    """Track scraping statistics."""
    total_events: int = 0
    unique_centers: int = 0
    centers_scraped: int = 0
    events_scraped: int = 0
    skipped_events: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class RetreatScraper:
    """Scrapes retreat listings from retreat.guru."""

    def __init__(self, openai_api_key: str = None):
        self.browser = None
        self.page = None
        self.httpx_client = None
        self.stats = ScraperStats()
        self.leads: list[RetreatLead] = []
        self.scraped_centers: dict[str, dict] = {}  # Cache center data

        # AI client for enhanced extraction
        self.ai_client = None
        if openai_api_key and USE_AI_EXTRACTION:
            self.ai_client = OpenAI(api_key=openai_api_key)

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        self.httpx_client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.httpx_client:
            await self.httpx_client.aclose()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_search_page(self, url: str, skip_urls: set[str] = None, paginate: bool = True) -> list[RetreatLead]:
        """
        Navigate to search results and extract all retreat listings.

        Args:
            url: Search URL to scrape
            skip_urls: Set of event URLs to skip (already scraped)
            paginate: If True, scroll to load ALL results (default). If False, only first page.
        """
        print(f"Navigating to: {url}")

        # Load the page with domcontentloaded (faster than networkidle)
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  Initial load warning: {str(e)[:50]}")
            # Continue anyway - page might have partially loaded

        # Wait for content to render (the page uses JavaScript)
        print("  Waiting for content to render...")
        await self.page.wait_for_timeout(5000)  # Give JS time to render

        # Check if we have content
        content = await self.page.content()
        if "search-event-tile" not in content:
            # Try waiting a bit more
            print("  Content not ready, waiting longer...")
            await self.page.wait_for_timeout(5000)
            content = await self.page.content()

        if "search-event-tile" not in content:
            raise Exception("Page loaded but no retreat listings found")

        # If pagination enabled, scroll to load ALL results
        if paginate:
            await self._scroll_to_load_all()

        html = await self.page.content()
        leads = self._extract_leads_from_search(html)

        print(f"  Found {len(leads)} retreat listings")

        # Filter out already-scraped URLs
        if skip_urls:
            original_count = len(leads)
            leads = [lead for lead in leads if lead.event_url not in skip_urls]
            skipped = original_count - len(leads)
            if skipped > 0:
                print(f"  Skipping {skipped} already-scraped retreats")
                self.stats.skipped_events = skipped

        self.stats.total_events = len(leads)

        # Count unique centers
        unique_centers = set(lead.center_url for lead in leads if lead.center_url)
        self.stats.unique_centers = len(unique_centers)
        print(f"  New retreats to scrape: {len(leads)}")
        print(f"  Unique centers: {self.stats.unique_centers}")

        return leads

    async def _scroll_to_load_all(self) -> None:
        """
        Scroll the page to load all results (for infinite scroll/lazy loading).

        Retreat Guru uses lazy loading - scrolling triggers loading of more results.
        This method scrolls until no new results appear.
        """
        print("  Scrolling to load all results...")

        MAX_SCROLL_ATTEMPTS = 50  # Safety limit
        SCROLL_PAUSE = 2.0  # Seconds to wait after each scroll

        previous_count = 0

        for attempt in range(MAX_SCROLL_ATTEMPTS):
            # Scroll to bottom
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(int(SCROLL_PAUSE * 1000))

            # Count current results
            current_count = await self.page.evaluate(
                "document.querySelectorAll('article.search-event-tile').length"
            )

            if current_count == previous_count:
                # No new results loaded - we've reached the end
                print(f"  Loaded all {current_count} results (stopped scrolling)")
                break

            previous_count = current_count
            if (attempt + 1) % 5 == 0:  # Progress update every 5 scrolls
                print(f"    ... loaded {current_count} results so far")

        else:
            # Hit the safety limit
            print(f"  Warning: Hit scroll limit at {previous_count} results")

    def _extract_leads_from_search(self, html: str) -> list[RetreatLead]:
        """Parse search results HTML to extract retreat data."""
        soup = BeautifulSoup(html, "lxml")
        leads = []

        tiles = soup.select("article.search-event-tile")

        for tile in tiles:
            lead = RetreatLead()

            # Title
            title_elem = tile.select_one("h2")
            if title_elem:
                lead.title = title_elem.get_text(strip=True)

            # Event URL and extract event_id
            content_link = tile.select_one("a.search-event-tile__content")
            if content_link:
                href = content_link.get("href", "")
                lead.event_url = urljoin(BASE_URL, href)
                lead.event_id = extract_event_id(lead.event_url)

            # Location and center info
            location_elem = tile.select_one(".search-event-tile__location")
            if location_elem:
                # Get center link and name
                center_link = location_elem.select_one("a[href*='/centers/']")
                if center_link:
                    lead.organizer = center_link.get_text(strip=True)
                    lead.center_url = urljoin(BASE_URL, center_link.get("href", ""))
                    lead.center_id = extract_center_id(lead.center_url)

                # Get city, country
                location_spans = location_elem.select("span")
                for span in location_spans:
                    text = span.get_text(strip=True)
                    if "," in text and not text.startswith("http"):
                        lead.location_city = text
                        break
                    elif "Mexico" in text:
                        lead.location_city = text

            # Dates
            dates_elem = tile.select_one(".search-event-tile__dates a")
            if dates_elem:
                lead.dates = dates_elem.get_text(strip=True)

            # Price
            price_elem = tile.select_one(".search-event-tile__price")
            if price_elem:
                lead.price = price_elem.get_text(strip=True).replace("From", "").strip()

            # Rating and review count from search tile
            reviews_elem = tile.select_one(".search-event-tile__reviews")
            if reviews_elem:
                reviews_text = reviews_elem.get_text(strip=True)
                # Parse rating like "4.8 (42 reviews)" or just "4.8"
                rating_match = re.search(r'(\d+\.?\d*)', reviews_text)
                if rating_match:
                    try:
                        lead.event_rating = float(rating_match.group(1))
                    except ValueError:
                        pass
                # Parse review count
                count_match = re.search(r'\((\d+)', reviews_text)
                if count_match:
                    try:
                        lead.event_review_count = int(count_match.group(1))
                    except ValueError:
                        pass

            if lead.title and lead.event_url:
                leads.append(lead)

        return leads

    async def enrich_with_center_data(self, leads: list[RetreatLead]) -> None:
        """
        Scrape center pages to get detailed addresses.
        Uses caching to avoid scraping the same center twice.
        """
        unique_centers = set(lead.center_url for lead in leads if lead.center_url)
        print(f"\nEnriching data from {len(unique_centers)} unique center pages...")

        for i, center_url in enumerate(unique_centers):
            if not center_url:
                continue

            # Check cache
            if center_url in self.scraped_centers:
                print(f"  [{i+1}/{len(unique_centers)}] Using cached: {center_url}")
                continue

            print(f"  [{i+1}/{len(unique_centers)}] Scraping: {center_url}")

            try:
                center_data = await self._scrape_center_page(center_url)
                self.scraped_centers[center_url] = center_data
                self.stats.centers_scraped += 1
            except Exception as e:
                error_msg = f"Error scraping {center_url}: {str(e)[:50]}"
                print(f"    {error_msg}")
                self.stats.errors += 1
                self.stats.error_messages.append(error_msg)
                self.scraped_centers[center_url] = {}

            # Be respectful
            await asyncio.sleep(PAGE_DELAY)

        # Apply cached data to leads
        for lead in leads:
            if lead.center_url and lead.center_url in self.scraped_centers:
                center_data = self.scraped_centers[lead.center_url]
                lead.detailed_address = center_data.get("address", "")
                lead.center_description = center_data.get("description", "")

                # New fields from enhanced center scraping
                lead.center_photo_url = center_data.get("center_photo_url", "")
                lead.google_maps_url = center_data.get("google_maps_url", "")
                lead.center_rating = center_data.get("center_rating", 0.0)
                lead.center_review_count = center_data.get("center_review_count", 0)

                # Collect guide IDs for linking
                guides = center_data.get("guides", [])
                lead.guide_ids = [g.get("teacher_id", "") for g in guides if g.get("teacher_id")]

                # Create Google Maps search query (legacy fallback)
                if lead.organizer and lead.detailed_address:
                    lead.search_query = f"{lead.organizer} {lead.detailed_address}"
                elif lead.organizer and lead.location_city:
                    lead.search_query = f"{lead.organizer} {lead.location_city}"

        # Optional: AI extraction for event pages
        if self.ai_client:
            await self._enrich_with_ai(leads)

    async def _scrape_center_page(self, url: str) -> dict:
        """
        Scrape a single center page for detailed info.

        Extracts:
        - Detailed address
        - Center description
        - Center profile picture/avatar
        - Google Maps URL
        - Rating and review count
        - ALL guide profile URLs (for later direct scraping)
        """
        # Try with domcontentloaded first (faster), fall back to shorter timeout
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
        except Exception:
            # If that fails, try one more time with even shorter timeout
            await self.page.goto(url, wait_until="commit", timeout=20000)
            await self.page.wait_for_timeout(3000)

        html = await self.page.content()
        soup = BeautifulSoup(html, "lxml")

        data = {
            "center_id": extract_center_id(url),
            "center_photo_url": "",
            "google_maps_url": "",
            "center_rating": 0.0,
            "center_review_count": 0,
        }

        # Get detailed address
        location_elem = soup.select_one("[data-cy='center-location']")
        if location_elem:
            data["address"] = location_elem.get_text(strip=True)

        # Get description (first 500 chars)
        desc_selectors = [".center-description", "[class*='about']", "article p"]
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if len(text) > 50:
                    data["description"] = text[:500]
                    break

        # Center profile picture/avatar
        avatar_selectors = [
            "img[data-cy='center-avatar']",
            "img[data-cy='center-logo']",
            "img[data-cy='center-image']",
            ".center-profile img",
            ".center-header img",
            "header img[class*='avatar']",
            "header img[class*='logo']",
            "[class*='center'] img[class*='avatar']",
            "[class*='center'] img[class*='logo']",
            "img[class*='center-avatar']",
            "img[class*='center-logo']",
            # More general selectors (last resort)
            ".hero img",
            "header img",
        ]

        for selector in avatar_selectors:
            try:
                img = soup.select_one(selector)
                if img:
                    # Check for src or srcset
                    src = img.get("src") or ""
                    srcset = img.get("srcset", "")
                    if srcset and not src:
                        src = srcset.split()[0].split(",")[0]

                    if src and not any(x in src.lower() for x in ["icon", "placeholder", "default", "avatar-default", "1x1"]):
                        data["center_photo_url"] = urljoin(BASE_URL, src.split("?")[0])
                        break
            except Exception:
                continue

        # Google Maps URL extraction
        maps_selectors = [
            "a[href*='google.com/maps']",
            "a[href*='maps.google.com']",
            "a[href*='goo.gl/maps']",
            "[data-cy='google-maps-link']",
            "a[class*='map-link']",
            "a[class*='maps']",
        ]

        for selector in maps_selectors:
            try:
                link = soup.select_one(selector)
                if link and link.get("href"):
                    data["google_maps_url"] = link.get("href", "")
                    break
            except Exception:
                continue

        # Fallback: construct Google Maps URL from address
        if not data.get("google_maps_url") and data.get("address"):
            encoded_addr = urllib.parse.quote(data["address"])
            data["google_maps_url"] = f"https://www.google.com/maps/search/{encoded_addr}"

        # Rating and review count for center
        rating_selectors = [
            "[data-cy='center-rating']",
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
                        data["center_rating"] = float(rating_match.group(1))
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
                    data["center_review_count"] = int(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract ALL guide profile URLs from the center page
        guide_links = soup.select("a[href*='/teachers/']")
        guides = []
        seen_urls = set()

        for link in guide_links:
            href = link.get("href", "")
            if href and href not in seen_urls:
                seen_urls.add(href)
                profile_url = urljoin(BASE_URL, href)
                name = link.get_text(strip=True)
                if name and len(name) > 1:  # Skip empty or single-char names
                    guides.append({
                        "name": name,
                        "profile_url": profile_url,
                        "teacher_id": extract_teacher_id(profile_url),
                    })

        data["guides"] = guides
        if guides:
            print(f"    Found {len(guides)} guides on center page")

        return data

    async def _enrich_with_ai(self, leads: list[RetreatLead]) -> None:
        """
        Use AI to extract enhanced data from event pages.

        Extracts:
        - Retreat description
        - Group size
        - Guide information
        """
        from extract_with_ai import extract_retreat_details

        print(f"\nAI-enriching {len(leads)} event pages...")

        for i, lead in enumerate(leads):
            if not lead.event_url:
                continue

            print(f"  [{i+1}/{len(leads)}] AI extraction: {lead.event_url[:60]}...")

            try:
                # Navigate to event page
                await self.page.goto(lead.event_url, wait_until="domcontentloaded", timeout=30000)
                await self.page.wait_for_timeout(2000)

                html = await self.page.content()

                # Extract with AI
                details = await extract_retreat_details(html, self.ai_client, "retreat.guru")

                # Apply results
                if details.get("description"):
                    lead.retreat_description = details["description"]
                if details.get("group_size"):
                    lead.group_size = details["group_size"]
                if details.get("guides"):
                    # Add guide IDs
                    from extract_with_ai import enrich_guides_with_ids
                    guides = enrich_guides_with_ids(details["guides"])
                    lead.guides_json = json.dumps(guides)

                self.stats.events_scraped += 1

            except Exception as e:
                error_msg = f"AI extraction failed for {lead.event_url}: {str(e)[:50]}"
                print(f"    {error_msg}")
                self.stats.errors += 1

            # Be respectful
            await asyncio.sleep(PAGE_DELAY)

    def save_to_csv(self, leads: list[RetreatLead], filename: str = OUTPUT_FILE) -> None:
        """Save retreat data to CSV."""
        if not leads:
            print("No leads to save!")
            return

        data = []
        for lead in leads:
            row = {
                # Entity IDs (for deduplication and linking)
                "event_id": lead.event_id,
                "center_id": lead.center_id,

                # Basic info
                "organizer": lead.organizer,
                "title": lead.title,
                "location_city": lead.location_city,
                "detailed_address": lead.detailed_address,
                "dates": lead.dates,
                "price": lead.price,

                # Ratings and reviews
                "event_rating": lead.event_rating,
                "event_review_count": lead.event_review_count,
                "center_rating": lead.center_rating,
                "center_review_count": lead.center_review_count,

                # Center info
                "center_photo_url": lead.center_photo_url,
                "google_maps_url": lead.google_maps_url,

                # URLs
                "event_url": lead.event_url,
                "center_url": lead.center_url,
                "search_query": lead.search_query,

                # Guide IDs for linking
                "guide_ids": ",".join(lead.guide_ids) if lead.guide_ids else "",
            }

            # Add enhanced fields if available
            if lead.retreat_description:
                row["retreat_description"] = lead.retreat_description
            if lead.group_size:
                row["group_size"] = lead.group_size
            if lead.guides_json:
                row["guides_json"] = lead.guides_json

            data.append(row)

        df = pd.DataFrame(data)

        # Sort by organizer to group retreats from same center
        df = df.sort_values("organizer")

        df.to_csv(filename, index=False, encoding="utf-8")
        print(f"\nSaved {len(leads)} leads to {filename}")

    def print_summary(self) -> None:
        """Print scraping summary."""
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY")
        print("=" * 60)
        print(f"   Total new retreats:   {self.stats.total_events}")
        print(f"   Skipped (duplicates): {self.stats.skipped_events}")
        print(f"   Unique centers:       {self.stats.unique_centers}")
        print(f"   Centers scraped:      {self.stats.centers_scraped}")
        if self.ai_client:
            print(f"   Events AI-enriched:   {self.stats.events_scraped}")
        print(f"   Errors:               {self.stats.errors}")
        print("-" * 60)
        print("\nNEXT STEPS:")
        print("   1. Open leads_enriched.csv")
        print("   2. Use 'search_query' column to find businesses on Google Maps")
        print("   3. Extract website, phone, email from Google Business listings")
        print("=" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for the scraper."""
    print("=" * 60)
    print("SURFBREAK RETREAT SCRAPER - ENRICHED")
    print("=" * 60)
    print(f"Target URL: {SEARCH_URL}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Enrich with center data: {ENRICH_WITH_CENTER_DATA}")
    print(f"AI extraction: {USE_AI_EXTRACTION}")
    print("=" * 60 + "\n")

    # Get OpenAI key if available
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    async with RetreatScraper(openai_api_key=openai_key) as scraper:
        # Phase 1: Scrape search results
        leads = await scraper.scrape_search_page(SEARCH_URL)

        # Phase 2: Enrich with center page data
        if ENRICH_WITH_CENTER_DATA and leads:
            await scraper.enrich_with_center_data(leads)

        # Save results
        scraper.save_to_csv(leads)

        # Print summary
        scraper.print_summary()

        return leads


if __name__ == "__main__":
    asyncio.run(main())
