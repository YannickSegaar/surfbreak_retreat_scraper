"""
BookRetreats.com Scraper
========================

Scrapes retreat listings from bookretreats.com to build a lead generation database.

KEY INSIGHT: BookRetreats embeds JSON-LD structured data on each page, making extraction
much more reliable than parsing HTML elements.

PHASE 1: Scrape search results for retreat URLs
PHASE 2: Scrape each retreat page for detailed info from JSON-LD data

OUTPUT FORMAT: Same as retreat.guru scraper for unified pipeline processing
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://bookretreats.com"

# Delays (be respectful to the server)
PAGE_DELAY = 1.5  # seconds between pages
REQUEST_TIMEOUT = 30  # seconds

# Output file
OUTPUT_FILE = "leads_enriched.csv"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RetreatLead:
    """Represents a single retreat listing with enriched data."""
    # Core fields (same as retreat.guru for unified processing)
    title: str = ""
    organizer: str = ""           # Host/organization name
    location_city: str = ""       # City, State, Country
    dates: str = ""
    price: str = ""
    rating: str = ""
    event_url: str = ""
    center_url: str = ""          # URL to organizer profile

    # Enriched data
    detailed_address: str = ""    # Full address if available
    center_description: str = ""  # About the retreat/host

    # For Google Maps lookup
    search_query: str = ""        # Pre-formatted search query

    # BookRetreats-specific (bonus data from JSON-LD)
    host_email: str = ""          # Sometimes available in JSON-LD
    latitude: str = ""
    longitude: str = ""


@dataclass
class ScraperStats:
    """Track scraping statistics."""
    total_events: int = 0
    unique_organizers: int = 0
    retreats_scraped: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class BookRetreatsScraper:
    """Scrapes retreat listings from bookretreats.com."""

    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
        self.stats = ScraperStats()
        self.leads: list[RetreatLead] = []

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

    async def scrape_search_page(self, url: str) -> list[RetreatLead]:
        """
        Navigate to search results and extract all retreat URLs,
        then scrape each retreat page for details.
        """
        print(f"Navigating to: {url}")

        # Load the search page
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  ⚠ Initial load warning: {str(e)[:50]}")

        # Wait for content to render
        print("  Waiting for content to render...")
        await self.page.wait_for_timeout(5000)

        # Scroll to load more content (bookretreats may use lazy loading)
        await self._scroll_to_load_all()

        html = await self.page.content()
        retreat_urls = self._extract_retreat_urls(html)

        print(f"  Found {len(retreat_urls)} retreat URLs")

        if not retreat_urls:
            print("  ⚠ No retreats found! The page structure may have changed.")
            return []

        # Scrape each retreat page
        leads = []
        for i, retreat_url in enumerate(retreat_urls):
            print(f"  [{i+1}/{len(retreat_urls)}] Scraping: {retreat_url}")

            try:
                lead = await self._scrape_retreat_page(retreat_url)
                if lead and lead.title:
                    leads.append(lead)
                    self.stats.retreats_scraped += 1
            except Exception as e:
                error_msg = f"Error scraping {retreat_url}: {str(e)[:50]}"
                print(f"    ⚠ {error_msg}")
                self.stats.errors += 1
                self.stats.error_messages.append(error_msg)

            # Be respectful
            await asyncio.sleep(PAGE_DELAY)

        self.stats.total_events = len(leads)

        # Count unique organizers
        unique_orgs = set(lead.organizer for lead in leads if lead.organizer)
        self.stats.unique_organizers = len(unique_orgs)

        print(f"  Successfully scraped {len(leads)} retreats")
        print(f"  Unique organizers: {self.stats.unique_organizers}")

        return leads

    async def _scroll_to_load_all(self):
        """Scroll down to trigger lazy loading of all retreats."""
        print("  Scrolling to load all content...")

        last_height = await self.page.evaluate("document.body.scrollHeight")

        for _ in range(10):  # Max 10 scroll attempts
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(1500)

            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _extract_retreat_urls(self, html: str) -> list[str]:
        """Extract all retreat detail page URLs from search results."""
        soup = BeautifulSoup(html, "lxml")
        urls = set()

        # Find all links to retreat pages (pattern: /r/retreat-slug)
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/r/") and not href.startswith("/r/s/"):
                # Skip search/filter URLs, only get actual retreats
                full_url = urljoin(BASE_URL, href)
                urls.add(full_url)

        return list(urls)

    async def _scrape_retreat_page(self, url: str) -> RetreatLead:
        """Scrape a single retreat page for detailed info using JSON-LD data."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
        except Exception:
            await self.page.goto(url, wait_until="commit", timeout=20000)
            await self.page.wait_for_timeout(3000)

        html = await self.page.content()
        soup = BeautifulSoup(html, "lxml")

        lead = RetreatLead()
        lead.event_url = url

        # Extract JSON-LD structured data (primary source)
        json_ld_data = self._extract_json_ld(soup)

        if json_ld_data:
            lead = self._parse_json_ld(json_ld_data, lead)

        # Fallback: extract from HTML if JSON-LD missing key fields
        if not lead.title:
            h1 = soup.select_one("h1")
            if h1:
                lead.title = h1.get_text(strip=True)

        # Try to find organizer profile URL
        org_link = soup.select_one("a[href*='/organizers/']")
        if org_link:
            lead.center_url = urljoin(BASE_URL, org_link.get("href", ""))

        # Build search query for Google Maps
        if lead.organizer and lead.detailed_address:
            lead.search_query = f"{lead.organizer} {lead.detailed_address}"
        elif lead.organizer and lead.location_city:
            lead.search_query = f"{lead.organizer} {lead.location_city}"

        return lead

    def _extract_json_ld(self, soup: BeautifulSoup) -> dict | None:
        """Extract JSON-LD structured data from page."""
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle @graph structure
                if isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") in ["Product", "Event", "TouristTrip", "LodgingBusiness"]:
                            return item
                    # Return first item if no specific type found
                    if data["@graph"]:
                        return data["@graph"][0]

                # Direct object
                if isinstance(data, dict) and data.get("@type"):
                    return data

                # List of objects
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type"):
                            return item

            except (json.JSONDecodeError, TypeError):
                continue

        return None

    def _parse_json_ld(self, data: dict, lead: RetreatLead) -> RetreatLead:
        """Parse JSON-LD data into RetreatLead fields."""

        # Title
        lead.title = data.get("name", "") or data.get("headline", "")

        # Organizer/Host
        organizer = data.get("organizer") or data.get("provider") or data.get("brand") or {}
        if isinstance(organizer, dict):
            lead.organizer = organizer.get("name", "")
            # Sometimes email is here
            if organizer.get("email"):
                lead.host_email = organizer.get("email", "")
        elif isinstance(organizer, str):
            lead.organizer = organizer

        # Also check for "seller" or "offers.seller"
        if not lead.organizer:
            offers = data.get("offers", {})
            if isinstance(offers, dict):
                seller = offers.get("seller", {})
                if isinstance(seller, dict):
                    lead.organizer = seller.get("name", "")

        # Location
        location = data.get("location") or data.get("contentLocation") or {}
        if isinstance(location, dict):
            address = location.get("address", {})
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                    address.get("addressCountry", "")
                ]
                lead.location_city = ", ".join(p for p in parts if p)
                lead.detailed_address = address.get("streetAddress", "") or lead.location_city
            elif isinstance(address, str):
                lead.location_city = address
                lead.detailed_address = address

            # Coordinates
            geo = location.get("geo", {})
            if isinstance(geo, dict):
                lead.latitude = str(geo.get("latitude", ""))
                lead.longitude = str(geo.get("longitude", ""))

        # Price
        offers = data.get("offers", {})
        if isinstance(offers, dict):
            price = offers.get("price", "")
            currency = offers.get("priceCurrency", "USD")
            if price:
                lead.price = f"{currency} {price}"
        elif isinstance(offers, list) and offers:
            first_offer = offers[0]
            price = first_offer.get("price", "")
            currency = first_offer.get("priceCurrency", "USD")
            if price:
                lead.price = f"{currency} {price}"

        # Rating
        rating = data.get("aggregateRating", {})
        if isinstance(rating, dict):
            rating_val = rating.get("ratingValue", "")
            review_count = rating.get("reviewCount", "")
            if rating_val:
                lead.rating = f"{rating_val}"
                if review_count:
                    lead.rating += f" ({review_count} reviews)"

        # Dates (if available)
        start_date = data.get("startDate", "")
        end_date = data.get("endDate", "")
        if start_date and end_date:
            lead.dates = f"{start_date} - {end_date}"
        elif start_date:
            lead.dates = start_date

        # Description
        desc = data.get("description", "")
        if desc:
            lead.center_description = desc[:500]  # First 500 chars

        return lead

    def save_to_csv(self, leads: list[RetreatLead], filename: str = OUTPUT_FILE) -> None:
        """Save retreat data to CSV (same format as retreat.guru)."""
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
                # Bonus fields from BookRetreats (will be empty for retreat.guru)
                "host_email_scraped": lead.host_email,
                "latitude": lead.latitude,
                "longitude": lead.longitude,
            })

        df = pd.DataFrame(data)

        # Sort by organizer to group retreats from same host
        df = df.sort_values("organizer")

        df.to_csv(filename, index=False, encoding="utf-8")
        print(f"\nSaved {len(leads)} leads to {filename}")

    def print_summary(self) -> None:
        """Print scraping summary."""
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY (BookRetreats)")
        print("=" * 60)
        print(f"   Total retreats:       {self.stats.total_events}")
        print(f"   Unique organizers:    {self.stats.unique_organizers}")
        print(f"   Successfully scraped: {self.stats.retreats_scraped}")
        print(f"   Errors:               {self.stats.errors}")
        print("-" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for the scraper."""
    test_url = "https://bookretreats.com/s/yoga-retreats/mexico"

    print("=" * 60)
    print("BOOKRETREATS.COM SCRAPER")
    print("=" * 60)
    print(f"Target URL: {test_url}")
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 60 + "\n")

    async with BookRetreatsScraper() as scraper:
        leads = await scraper.scrape_search_page(test_url)
        scraper.save_to_csv(leads)
        scraper.print_summary()
        return leads


if __name__ == "__main__":
    asyncio.run(main())
