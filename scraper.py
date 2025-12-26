"""
Surfbreak Retreat Scraper
=========================

Scrapes retreat listings from retreat.guru to build a lead generation database.

PHASE 1: Scrape search results for basic info + center URLs
PHASE 2: Scrape center pages for detailed address info

PAGE STRUCTURE ANALYSIS (from Playwright MCP):
----------------------------------------------
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

CONTACT INFO STRATEGY:
---------------------
retreat.guru does NOT expose email, phone, website, or social media.
We extract detailed addresses so you can search Google Maps/Google Business
to find the organizer's actual contact information.
"""

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


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


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RetreatLead:
    """Represents a single retreat listing with enriched data."""
    # From search page
    title: str = ""
    organizer: str = ""           # Center/venue name
    location_city: str = ""       # City, Country (from search)
    dates: str = ""
    price: str = ""
    rating: str = ""
    event_url: str = ""
    center_url: str = ""          # URL to center page

    # From center page (enriched data)
    detailed_address: str = ""    # Full street address
    center_description: str = ""  # About the center

    # For Google Maps lookup
    search_query: str = ""        # Pre-formatted search query


@dataclass
class ScraperStats:
    """Track scraping statistics."""
    total_events: int = 0
    unique_centers: int = 0
    centers_scraped: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class RetreatScraper:
    """Scrapes retreat listings from retreat.guru."""

    def __init__(self):
        self.browser = None
        self.page = None
        self.httpx_client = None
        self.stats = ScraperStats()
        self.leads: list[RetreatLead] = []
        self.scraped_centers: dict[str, dict] = {}  # Cache center data

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

    async def scrape_search_page(self, url: str) -> list[RetreatLead]:
        """
        Navigate to search results and extract all retreat listings.
        """
        print(f"Navigating to: {url}")

        # Load the page with domcontentloaded (faster than networkidle)
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  ⚠ Initial load warning: {str(e)[:50]}")
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

        html = await self.page.content()
        leads = self._extract_leads_from_search(html)

        print(f"  Found {len(leads)} retreat listings")
        self.stats.total_events = len(leads)

        # Count unique centers
        unique_centers = set(lead.center_url for lead in leads if lead.center_url)
        self.stats.unique_centers = len(unique_centers)
        print(f"  Unique centers: {self.stats.unique_centers}")

        return leads

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

            # Event URL
            content_link = tile.select_one("a.search-event-tile__content")
            if content_link:
                href = content_link.get("href", "")
                lead.event_url = urljoin(BASE_URL, href)

            # Location and center info
            location_elem = tile.select_one(".search-event-tile__location")
            if location_elem:
                # Get center link and name
                center_link = location_elem.select_one("a[href*='/centers/']")
                if center_link:
                    lead.organizer = center_link.get_text(strip=True)
                    lead.center_url = urljoin(BASE_URL, center_link.get("href", ""))

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

            # Rating
            reviews_elem = tile.select_one(".search-event-tile__reviews")
            if reviews_elem:
                lead.rating = reviews_elem.get_text(strip=True)

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
                print(f"    ⚠ {error_msg}")
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

                # Create Google Maps search query
                if lead.organizer and lead.detailed_address:
                    lead.search_query = f"{lead.organizer} {lead.detailed_address}"
                elif lead.organizer and lead.location_city:
                    lead.search_query = f"{lead.organizer} {lead.location_city}"

    async def _scrape_center_page(self, url: str) -> dict:
        """Scrape a single center page for detailed info."""
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

        data = {}

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

        return data

    def save_to_csv(self, leads: list[RetreatLead], filename: str = OUTPUT_FILE) -> None:
        """Save retreat data to CSV."""
        if not leads:
            print("No leads to save!")
            return

        data = []
        for lead in leads:
            data.append({
                "organizer": lead.organizer,
                "title": lead.title,
                "location_city": lead.location_city,
                "detailed_address": lead.detailed_address,
                "dates": lead.dates,
                "price": lead.price,
                "rating": lead.rating,
                "event_url": lead.event_url,
                "center_url": lead.center_url,
                "search_query": lead.search_query,
            })

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
        print(f"   Total retreats:       {self.stats.total_events}")
        print(f"   Unique centers:       {self.stats.unique_centers}")
        print(f"   Centers scraped:      {self.stats.centers_scraped}")
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
    print("=" * 60 + "\n")

    async with RetreatScraper() as scraper:
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
