"""
BookRetreats.com Scraper
========================

Scrapes retreat listings from bookretreats.com to build a lead generation database.

KEY INSIGHT: BookRetreats embeds JSON-LD structured data on each page, making extraction
much more reliable than parsing HTML elements.

PHASE 1: Scrape search results for retreat URLs (with pagination)
PHASE 2: Scrape each retreat page for detailed info from JSON-LD data
PHASE 3: (Optional) AI extraction for descriptions, group sizes, and guides

OUTPUT FORMAT: Same as retreat.guru scraper for unified pipeline processing
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import pandas as pd
from bs4 import BeautifulSoup
from openai import OpenAI
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

# Whether to use AI extraction for enhanced data (requires OPENAI_API_KEY)
USE_AI_EXTRACTION = True

# Maximum pages to scrape (safety limit)
MAX_PAGES = 20


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

    # Enhanced data (from AI extraction)
    retreat_description: str = ""  # About this retreat
    group_size: int | None = None  # Max participants
    guides_json: str = ""          # JSON array of guide info


@dataclass
class ScraperStats:
    """Track scraping statistics."""
    total_events: int = 0
    unique_organizers: int = 0
    retreats_scraped: int = 0
    skipped_events: int = 0
    pages_scraped: int = 0
    events_ai_enriched: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class BookRetreatsScraper:
    """Scrapes retreat listings from bookretreats.com."""

    def __init__(self, openai_api_key: str = None):
        self.browser = None
        self.page = None
        self.playwright = None
        self.stats = ScraperStats()
        self.leads: list[RetreatLead] = []

        # AI client for enhanced extraction
        self.ai_client = None
        if openai_api_key and USE_AI_EXTRACTION:
            self.ai_client = OpenAI(api_key=openai_api_key)

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

    async def scrape_search_page(self, url: str, skip_urls: set[str] = None) -> list[RetreatLead]:
        """
        Navigate to search results and extract all retreat URLs with pagination,
        then scrape each retreat page for details.

        Args:
            url: Search URL to scrape
            skip_urls: Set of event URLs to skip (already scraped)
        """
        all_leads = []
        all_retreat_urls = []
        page_num = 1

        print(f"Starting paginated scrape: {url}")

        # Phase 1: Collect all retreat URLs from all pages
        while page_num <= MAX_PAGES:
            page_url = self._add_page_param(url, page_num)
            print(f"\n  Page {page_num}: {page_url[:80]}...")

            try:
                await self.page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"    Initial load warning: {str(e)[:50]}")

            # Wait for content to render
            await self.page.wait_for_timeout(3000)

            # Scroll to load lazy content on this page
            await self._scroll_to_load_all()

            html = await self.page.content()
            retreat_urls = self._extract_retreat_urls(html)

            if not retreat_urls:
                print(f"    No more retreats found on page {page_num}")
                break

            # Filter out already-scraped URLs
            new_urls = retreat_urls
            if skip_urls:
                new_urls = [u for u in retreat_urls if u not in skip_urls]
                skipped = len(retreat_urls) - len(new_urls)
                if skipped > 0:
                    print(f"    Found {len(retreat_urls)} retreats, skipping {skipped} already-scraped")
                    self.stats.skipped_events += skipped
                else:
                    print(f"    Found {len(retreat_urls)} new retreat URLs")
            else:
                print(f"    Found {len(retreat_urls)} retreat URLs")

            # Add to master list (avoiding duplicates within this session)
            for u in new_urls:
                if u not in all_retreat_urls:
                    all_retreat_urls.append(u)

            self.stats.pages_scraped += 1
            page_num += 1

            # Small delay between pages
            await asyncio.sleep(PAGE_DELAY)

        print(f"\n  Total unique retreat URLs to scrape: {len(all_retreat_urls)}")

        if not all_retreat_urls:
            print("  No retreats found to scrape!")
            return []

        # Phase 2: Scrape each retreat page
        for i, retreat_url in enumerate(all_retreat_urls):
            print(f"  [{i+1}/{len(all_retreat_urls)}] Scraping: {retreat_url[:60]}...")

            try:
                lead = await self._scrape_retreat_page(retreat_url)
                if lead and lead.title:
                    all_leads.append(lead)
                    self.stats.retreats_scraped += 1
            except Exception as e:
                error_msg = f"Error scraping {retreat_url}: {str(e)[:50]}"
                print(f"    {error_msg}")
                self.stats.errors += 1
                self.stats.error_messages.append(error_msg)

            # Be respectful
            await asyncio.sleep(PAGE_DELAY)

        self.stats.total_events = len(all_leads)

        # Count unique organizers
        unique_orgs = set(lead.organizer for lead in all_leads if lead.organizer)
        self.stats.unique_organizers = len(unique_orgs)

        print(f"\n  Successfully scraped {len(all_leads)} retreats")
        print(f"  Unique organizers: {self.stats.unique_organizers}")

        return all_leads

    def _add_page_param(self, url: str, page_num: int) -> str:
        """Add or update pageNumber parameter in URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Update pageNumber
        params['pageNumber'] = [str(page_num)]

        # Rebuild URL
        new_query = urlencode(params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

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
        """Scrape a single retreat page for detailed info from HTML."""
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

        # === TITLE ===
        h1 = soup.select_one("h1")
        if h1:
            lead.title = h1.get_text(strip=True)

        # === ORGANIZER NAME AND URL ===
        # The organizer link is the anchor tag with href="/organizers/o/..."
        org_link = soup.select_one("a[href*='/organizers/o/']")
        if org_link:
            lead.organizer = org_link.get_text(strip=True)
            lead.center_url = urljoin(BASE_URL, org_link.get("href", ""))

        # === LOCATION ===
        # Look for location text patterns in the page
        # Usually appears near the title or in a location section
        location_patterns = [
            soup.select_one("[class*='location']"),
            soup.select_one("[class*='Location']"),
            soup.select_one("[data-testid*='location']"),
        ]
        for loc_elem in location_patterns:
            if loc_elem:
                lead.location_city = loc_elem.get_text(strip=True)
                break

        # Fallback: extract location from title (often includes "in Location, Country")
        if not lead.location_city and lead.title:
            if " in " in lead.title:
                # e.g., "5 Day Retreat in Tulum, Mexico" -> "Tulum, Mexico"
                location_part = lead.title.split(" in ")[-1]
                if "," in location_part:
                    lead.location_city = location_part

        # === PRICE ===
        # Look for price elements (usually contains "US$" or "$")
        price_elem = soup.find(string=re.compile(r'US?\$[\d,]+'))
        if price_elem:
            # Extract just the price portion
            price_match = re.search(r'US?\$[\d,]+', price_elem)
            if price_match:
                lead.price = price_match.group(0)

        # === RATING ===
        # Look for rating stars or review count
        rating_elem = soup.select_one("[class*='rating']")
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            # Extract numeric rating
            rating_match = re.search(r'(\d+\.?\d*)\s*(?:/\s*5)?', rating_text)
            if rating_match:
                lead.rating = rating_match.group(1)

        # Also look for review count
        review_elem = soup.find(string=re.compile(r'\d+\s*reviews?'))
        if review_elem:
            review_match = re.search(r'(\d+)\s*reviews?', review_elem)
            if review_match:
                if lead.rating:
                    lead.rating += f" ({review_match.group(1)} reviews)"
                else:
                    lead.rating = f"({review_match.group(1)} reviews)"

        # === DETAILED ADDRESS ===
        # Look for address-like content
        address_selectors = [
            "[class*='address']",
            "[class*='Address']",
            "[itemprop='address']",
        ]
        for selector in address_selectors:
            addr_elem = soup.select_one(selector)
            if addr_elem:
                lead.detailed_address = addr_elem.get_text(strip=True)
                break

        # If no specific address, use location_city as detailed_address
        if not lead.detailed_address and lead.location_city:
            lead.detailed_address = lead.location_city

        # === BUILD SEARCH QUERY ===
        if lead.organizer and lead.detailed_address:
            lead.search_query = f"{lead.organizer} {lead.detailed_address}"
        elif lead.organizer and lead.location_city:
            lead.search_query = f"{lead.organizer} {lead.location_city}"

        # === AI EXTRACTION (if available) ===
        if self.ai_client:
            try:
                await self._enrich_lead_with_ai(lead, html)
            except Exception as e:
                print(f"    AI extraction warning: {str(e)[:50]}")

        return lead

    async def _enrich_lead_with_ai(self, lead: RetreatLead, html: str) -> None:
        """
        Use AI to extract enhanced data from retreat page HTML.

        Extracts:
        - Retreat description
        - Group size
        - Guide information
        """
        from extract_with_ai import extract_retreat_details, enrich_guides_with_ids

        try:
            details = await extract_retreat_details(html, self.ai_client, "bookretreats.com")

            # Apply results
            if details.get("description"):
                lead.retreat_description = details["description"]
            if details.get("group_size"):
                lead.group_size = details["group_size"]
            if details.get("guides"):
                # Add guide IDs for deduplication
                guides = enrich_guides_with_ids(details["guides"])
                lead.guides_json = json.dumps(guides)

            self.stats.events_ai_enriched += 1

        except Exception as e:
            print(f"    AI extraction failed: {str(e)[:50]}")

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
            row = {
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
            }

            # Add enhanced fields if available (from AI extraction)
            if lead.retreat_description:
                row["retreat_description"] = lead.retreat_description
            if lead.group_size:
                row["group_size"] = lead.group_size
            if lead.guides_json:
                row["guides_json"] = lead.guides_json

            data.append(row)

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
        print(f"   Pages scraped:        {self.stats.pages_scraped}")
        print(f"   Total new retreats:   {self.stats.total_events}")
        print(f"   Skipped (duplicates): {self.stats.skipped_events}")
        print(f"   Unique organizers:    {self.stats.unique_organizers}")
        print(f"   Successfully scraped: {self.stats.retreats_scraped}")
        if self.ai_client:
            print(f"   Events AI-enriched:   {self.stats.events_ai_enriched}")
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
    test_url = "https://bookretreats.com/s/yoga-retreats/mexico"

    print("=" * 60)
    print("BOOKRETREATS.COM SCRAPER")
    print("=" * 60)
    print(f"Target URL: {test_url}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"AI extraction: {USE_AI_EXTRACTION}")
    print("=" * 60 + "\n")

    # Get OpenAI key if available
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    async with BookRetreatsScraper(openai_api_key=openai_key) as scraper:
        leads = await scraper.scrape_search_page(test_url)
        scraper.save_to_csv(leads)
        scraper.print_summary()
        return leads


if __name__ == "__main__":
    asyncio.run(main())
