"""
Website Scraper for Contact Information
========================================

Scrapes websites found via Google Places API to extract:
- Email addresses
- Social media links (Instagram, Facebook, LinkedIn, Twitter/X, YouTube, TikTok)

This script reads leads that have a 'website' column and extracts contact info.
"""

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
import pandas as pd
from bs4 import BeautifulSoup


# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = "leads_google_enriched.csv"
OUTPUT_FILE = "leads_final.csv"

# Request settings
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.5  # seconds between requests

# Pages to check for contact info (in order of priority)
CONTACT_PAGE_PATHS = [
    "/contact",
    "/contact-us",
    "/contacto",
    "/about",
    "/about-us",
    "/connect",
    "/get-in-touch",
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ContactInfo:
    """Contact information extracted from a website."""
    emails: list[str] = field(default_factory=list)
    instagram: str = ""
    facebook: str = ""
    linkedin: str = ""
    twitter: str = ""
    youtube: str = ""
    tiktok: str = ""


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_emails(html: str, soup: BeautifulSoup) -> list[str]:
    """Extract email addresses from HTML content."""
    emails = set()

    # Pattern for email addresses
    email_pattern = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Search in raw HTML
    found = email_pattern.findall(html)
    for email in found:
        email_lower = email.lower()
        # Filter out common false positives
        if not any(skip in email_lower for skip in [
            'example.com', 'domain.com', 'email.com', 'your',
            'noreply', 'no-reply', 'donotreply',
            '.png', '.jpg', '.gif', '.svg', '.webp',
            'sentry.io', 'cloudfront', 'wixpress',
        ]):
            emails.add(email_lower)

    # Also check mailto links
    for link in soup.select('a[href^="mailto:"]'):
        href = link.get('href', '')
        email = href.replace('mailto:', '').split('?')[0].strip()
        if email and '@' in email:
            emails.add(email.lower())

    return list(emails)[:3]  # Return up to 3 emails


def extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    """Extract social media links from page."""
    social = {
        'instagram': '',
        'facebook': '',
        'linkedin': '',
        'twitter': '',
        'youtube': '',
        'tiktok': '',
    }

    # Patterns to match social media URLs
    patterns = {
        'instagram': [r'instagram\.com/([^/?]+)', r'instagr\.am/([^/?]+)'],
        'facebook': [r'facebook\.com/([^/?]+)', r'fb\.com/([^/?]+)'],
        'linkedin': [r'linkedin\.com/(?:company|in)/([^/?]+)'],
        'twitter': [r'twitter\.com/([^/?]+)', r'x\.com/([^/?]+)'],
        'youtube': [r'youtube\.com/(?:c/|channel/|user/|@)?([^/?]+)'],
        'tiktok': [r'tiktok\.com/@?([^/?]+)'],
    }

    # Find all links
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()

        for platform, regexes in patterns.items():
            if social[platform]:  # Already found
                continue

            for regex in regexes:
                match = re.search(regex, href)
                if match:
                    # Store the full URL
                    social[platform] = href if href.startswith('http') else f"https:{href}" if href.startswith('//') else href
                    break

    return social


# =============================================================================
# WEBSITE SCRAPER
# =============================================================================

class WebsiteScraper:
    """Scrapes websites for contact information."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.stats = {"scraped": 0, "errors": 0}

    async def close(self):
        await self.client.aclose()

    async def fetch_page(self, url: str) -> tuple[str, BeautifulSoup] | None:
        """Fetch a page and return HTML and BeautifulSoup object."""
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'lxml')
                return html, soup
        except Exception as e:
            pass
        return None

    async def scrape_website(self, website_url: str) -> ContactInfo:
        """
        Scrape a website for contact information.

        Checks homepage and common contact pages.
        """
        if not website_url:
            return ContactInfo()

        # Normalize URL
        if not website_url.startswith('http'):
            website_url = f"https://{website_url}"

        contact = ContactInfo()
        all_emails = set()
        pages_checked = 0

        # Parse base URL
        parsed = urlparse(website_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Pages to check
        pages_to_check = [website_url]  # Start with homepage
        for path in CONTACT_PAGE_PATHS:
            pages_to_check.append(urljoin(base_url, path))

        for page_url in pages_to_check:
            result = await self.fetch_page(page_url)
            if not result:
                continue

            html, soup = result
            pages_checked += 1

            # Extract emails
            emails = extract_emails(html, soup)
            all_emails.update(emails)

            # Extract social links (only need to do this once from homepage or footer)
            if not contact.instagram:
                social = extract_social_links(soup, base_url)
                contact.instagram = social['instagram']
                contact.facebook = social['facebook']
                contact.linkedin = social['linkedin']
                contact.twitter = social['twitter']
                contact.youtube = social['youtube']
                contact.tiktok = social['tiktok']

            # If we found emails and social, we can stop
            if all_emails and contact.instagram:
                break

            # Small delay between pages on same site
            await asyncio.sleep(0.2)

        contact.emails = list(all_emails)[:3]
        self.stats["scraped"] += 1

        return contact


# =============================================================================
# MAIN ENRICHMENT FUNCTION
# =============================================================================

async def enrich_leads_with_website_data(input_file: str, output_file: str):
    """
    Read leads with websites and enrich with contact info.
    """
    print("=" * 70)
    print("WEBSITE CONTACT ENRICHMENT")
    print("=" * 70)

    # Read input
    df = pd.read_csv(input_file)
    print(f"\nLoaded {len(df)} leads from {input_file}")

    # Count leads with websites
    has_website = df["website"].notna() & (df["website"] != "")
    websites_to_scrape = df[has_website]["website"].unique()
    print(f"Unique websites to scrape: {len(websites_to_scrape)}")

    if len(websites_to_scrape) == 0:
        print("\n⚠ No websites found to scrape!")
        print("Continuing with empty contact columns...")

        # Add empty contact columns and save
        df["email"] = ""
        df["instagram"] = ""
        df["facebook"] = ""
        df["linkedin"] = ""
        df["twitter"] = ""
        df["youtube"] = ""
        df["tiktok"] = ""
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"\nSaved to {output_file} (no contact enrichment)")
        return

    # Initialize scraper
    scraper = WebsiteScraper()

    # Cache for results
    results_cache: dict[str, ContactInfo] = {}

    print(f"\nScraping websites for contact info...")
    print("-" * 70)

    for i, website in enumerate(websites_to_scrape):
        if not website or pd.isna(website):
            continue

        print(f"[{i+1}/{len(websites_to_scrape)}] Scraping: {website[:50]}...")

        try:
            contact = await scraper.scrape_website(website)
            results_cache[website] = contact

            found_items = []
            if contact.emails:
                found_items.append(f"emails: {contact.emails}")
            if contact.instagram:
                found_items.append("IG")
            if contact.facebook:
                found_items.append("FB")
            if contact.linkedin:
                found_items.append("LI")
            if contact.twitter:
                found_items.append("TW")

            if found_items:
                print(f"  ✓ Found: {', '.join(found_items)}")
            else:
                print(f"  ✗ No contact info found")

        except Exception as e:
            print(f"  ⚠ Error: {str(e)[:50]}")
            scraper.stats["errors"] += 1
            results_cache[website] = ContactInfo()

        # Rate limiting
        await asyncio.sleep(REQUEST_DELAY)

    await scraper.close()

    # Apply results to dataframe
    print("\n" + "-" * 70)
    print("Applying results to leads...")

    # Add new columns
    df["email"] = ""
    df["instagram"] = ""
    df["facebook"] = ""
    df["linkedin"] = ""
    df["twitter"] = ""
    df["youtube"] = ""
    df["tiktok"] = ""

    for idx, row in df.iterrows():
        website = row.get("website", "")
        if website and website in results_cache:
            contact = results_cache[website]
            df.at[idx, "email"] = "; ".join(contact.emails) if contact.emails else ""
            df.at[idx, "instagram"] = contact.instagram
            df.at[idx, "facebook"] = contact.facebook
            df.at[idx, "linkedin"] = contact.linkedin
            df.at[idx, "twitter"] = contact.twitter
            df.at[idx, "youtube"] = contact.youtube
            df.at[idx, "tiktok"] = contact.tiktok

    # Reorder columns for better readability
    priority_cols = [
        "organizer", "title", "location_city", "detailed_address",
        "phone", "email", "website",
        "instagram", "facebook", "linkedin", "twitter",
        "dates", "price", "rating",
        "event_url", "center_url", "google_maps_url",
    ]

    # Keep priority columns that exist, then add remaining columns
    existing_priority = [c for c in priority_cols if c in df.columns]
    remaining = [c for c in df.columns if c not in priority_cols]
    df = df[existing_priority + remaining]

    # Save output
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"\nSaved final enriched data to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("ENRICHMENT SUMMARY")
    print("=" * 70)
    print(f"   Websites scraped: {scraper.stats['scraped']}")
    print(f"   Errors:           {scraper.stats['errors']}")
    print("-" * 70)

    # Count enriched fields
    with_email = df["email"].notna() & (df["email"] != "")
    with_instagram = df["instagram"].notna() & (df["instagram"] != "")
    with_facebook = df["facebook"].notna() & (df["facebook"] != "")
    with_linkedin = df["linkedin"].notna() & (df["linkedin"] != "")

    print(f"   Leads with email:     {with_email.sum()}")
    print(f"   Leads with Instagram: {with_instagram.sum()}")
    print(f"   Leads with Facebook:  {with_facebook.sum()}")
    print(f"   Leads with LinkedIn:  {with_linkedin.sum()}")
    print("=" * 70)

    print("\n✓ ENRICHMENT COMPLETE!")
    print(f"  Final output: {output_file}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    asyncio.run(enrich_leads_with_website_data(INPUT_FILE, OUTPUT_FILE))
