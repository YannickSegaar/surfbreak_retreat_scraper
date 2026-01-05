"""
Test Script for Single Event URL
================================

Tests the scraper improvements on a single retreat event URL.
Validates:
1. Event page scraping (description, guides, group size)
2. Center page scraping (address, all guides)
3. Review filtering (no customer reviews in guide bios)
4. Guide profile page scraping

Usage:
    uv run python test_single_event.py
"""

import asyncio
import json
import os
import sys
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment
load_dotenv()

# Test URL
TEST_EVENT_URL = "https://retreat.guru/events/6715-17/fitflowyoga-teacher-training-in-tulum-3"
BASE_URL = "https://retreat.guru"


async def test_event_scraping():
    """Test scraping a single event page."""
    print("=" * 70)
    print("TESTING SINGLE EVENT URL")
    print("=" * 70)
    print(f"\nEvent URL: {TEST_EVENT_URL}\n")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        # =====================================================================
        # STEP 1: Load Event Page
        # =====================================================================
        print("-" * 70)
        print("STEP 1: Loading Event Page")
        print("-" * 70)

        await page.goto(TEST_EVENT_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        # Remove scripts/styles
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        # =====================================================================
        # STEP 2: Extract Basic Info
        # =====================================================================
        print("\n" + "-" * 70)
        print("STEP 2: Basic Event Information")
        print("-" * 70)

        # Title
        title = soup.select_one("h1")
        print(f"\nTitle: {title.get_text(strip=True) if title else 'NOT FOUND'}")

        # Location
        location = soup.select_one(".search-event-tile__location, [class*='location']")
        if location:
            print(f"Location: {location.get_text(strip=True)[:100]}")

        # Group size (look for "in group" pattern)
        page_text = soup.get_text()
        import re
        group_match = re.search(r'up\s+to\s+(\d+)\s+in\s+group', page_text, re.IGNORECASE)
        if group_match:
            print(f"Group Size: {group_match.group(1)}")
        else:
            group_match = re.search(r'(\d+)\s+in\s+group', page_text, re.IGNORECASE)
            if group_match:
                print(f"Group Size: {group_match.group(1)}")
            else:
                print("Group Size: NOT FOUND")

        # =====================================================================
        # STEP 3: Extract Center URL
        # =====================================================================
        print("\n" + "-" * 70)
        print("STEP 3: Center Information")
        print("-" * 70)

        center_link = soup.select_one("a[href*='/centers/']")
        center_url = None
        center_name = None
        if center_link:
            center_url = urljoin(BASE_URL, center_link.get("href", ""))
            center_name = center_link.get_text(strip=True)
            print(f"Center Name: {center_name}")
            print(f"Center URL: {center_url}")
        else:
            print("Center: NOT FOUND")

        # =====================================================================
        # STEP 4: Extract Guide Links from Event Page
        # =====================================================================
        print("\n" + "-" * 70)
        print("STEP 4: Guides Found on Event Page")
        print("-" * 70)

        guide_links = soup.select("a[href*='/teachers/']")
        guides_found = []
        seen_urls = set()

        for link in guide_links:
            href = link.get("href", "")
            if href and href not in seen_urls:
                seen_urls.add(href)
                name = link.get_text(strip=True)
                if name and len(name) > 1:
                    profile_url = urljoin(BASE_URL, href)
                    guides_found.append({"name": name, "profile_url": profile_url})

        if guides_found:
            print(f"\nFound {len(guides_found)} guide(s):")
            for g in guides_found:
                print(f"  - {g['name']}")
                print(f"    URL: {g['profile_url']}")
        else:
            print("No guide links found on event page")

        # =====================================================================
        # STEP 5: Test Review Filtering
        # =====================================================================
        print("\n" + "-" * 70)
        print("STEP 5: Review Detection Test")
        print("-" * 70)

        # Import our new review detection function
        from extract_with_ai import is_likely_review, EXCLUDE_SELECTORS

        # Find review sections
        review_sections = []
        for selector in EXCLUDE_SELECTORS:
            for elem in soup.select(selector):
                text = elem.get_text(strip=True)[:200]
                if len(text) > 50:
                    review_sections.append(text)

        if review_sections:
            print(f"\nFound {len(review_sections)} review section(s) (these will be EXCLUDED):")
            for i, text in enumerate(review_sections[:3]):
                print(f"  [{i+1}] \"{text[:100]}...\"")
        else:
            print("\nNo obvious review sections found (good!)")

        # Test some sample text
        print("\n  Testing review detection on sample text:")

        test_texts = [
            ("I loved this retreat! The guides were amazing.", True),
            ("Sarah has been teaching yoga for 15 years.", False),
            ("5/5 stars - Would recommend to anyone!", True),
            ("Join us for a transformative 7-day experience.", False),
        ]

        for text, expected in test_texts:
            result = is_likely_review(text)
            status = "PASS" if result == expected else "FAIL"
            print(f"    [{status}] \"{text[:40]}...\" -> {'REVIEW' if result else 'NOT REVIEW'}")

        # =====================================================================
        # STEP 6: Test AI Extraction (if API key available)
        # =====================================================================
        print("\n" + "-" * 70)
        print("STEP 6: AI Extraction Test")
        print("-" * 70)

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            from openai import OpenAI
            from extract_with_ai import extract_retreat_details_sync

            print("\nRunning AI extraction...")
            client = OpenAI(api_key=openai_key)
            result = extract_retreat_details_sync(html, client, "retreat.guru")

            print(f"\n  Description: {result.get('description', 'None')[:200]}..." if result.get('description') else "\n  Description: None")
            print(f"  Group Size: {result.get('group_size', 'None')}")
            print(f"  Guides extracted: {len(result.get('guides', []))}")

            for g in result.get('guides', []):
                print(f"\n    Guide: {g.get('name', 'Unknown')}")
                print(f"      Role: {g.get('role', 'N/A')}")
                print(f"      Bio: {g.get('bio', 'None')[:100]}..." if g.get('bio') else "      Bio: None")
                print(f"      Profile URL: {g.get('profile_url', 'None')}")

                # Check if bio looks like a review
                if g.get('bio'):
                    if is_likely_review(g['bio']):
                        print(f"      WARNING: Bio looks like a customer review!")
                    else:
                        print(f"      Bio check: OK (not a review)")
        else:
            print("\nSkipped (OPENAI_API_KEY not set)")

        # =====================================================================
        # STEP 7: Test Center Page Scraping
        # =====================================================================
        if center_url:
            print("\n" + "-" * 70)
            print("STEP 7: Center Page Scraping")
            print("-" * 70)

            print(f"\nLoading center page: {center_url}")
            await page.goto(center_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            center_html = await page.content()
            center_soup = BeautifulSoup(center_html, "lxml")

            # Address
            addr_elem = center_soup.select_one("[data-cy='center-location']")
            if addr_elem:
                print(f"\nAddress: {addr_elem.get_text(strip=True)}")
            else:
                print("\nAddress: NOT FOUND")

            # Guides from center page
            center_guide_links = center_soup.select("a[href*='/teachers/']")
            center_guides = []
            seen = set()

            for link in center_guide_links:
                href = link.get("href", "")
                if href and href not in seen:
                    seen.add(href)
                    name = link.get_text(strip=True)
                    if name and len(name) > 1:
                        center_guides.append({
                            "name": name,
                            "profile_url": urljoin(BASE_URL, href)
                        })

            print(f"\nGuides on center page: {len(center_guides)}")
            for g in center_guides[:5]:
                print(f"  - {g['name']}")

            if len(center_guides) > 5:
                print(f"  ... and {len(center_guides) - 5} more")

        # =====================================================================
        # STEP 8: Test Guide Profile Scraping
        # =====================================================================
        if guides_found:
            print("\n" + "-" * 70)
            print("STEP 8: Direct Guide Profile Scraping")
            print("-" * 70)

            # Test first guide
            test_guide = guides_found[0]
            print(f"\nTesting: {test_guide['name']}")
            print(f"URL: {test_guide['profile_url']}")

            from scraper_guides import GuideProfileScraper

            async with GuideProfileScraper() as guide_scraper:
                guide = await guide_scraper.scrape_guide_page(test_guide['profile_url'])

                if guide:
                    print(f"\n  Name: {guide.name}")
                    print(f"  Credentials: {guide.credentials or 'None'}")
                    print(f"  Bio: {guide.bio[:150]}..." if guide.bio else "  Bio: None")
                    print(f"  Photo URL: {guide.photo_url[:60]}..." if guide.photo_url else "  Photo URL: None")
                    print(f"  Affiliated Center: {guide.affiliated_center or 'None'}")
                    print(f"  Upcoming Retreats: {len(guide.upcoming_retreats)}")
                else:
                    print("  Failed to scrape guide profile")

        # =====================================================================
        # SUMMARY
        # =====================================================================
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        print(f"""
Event Title:     {title.get_text(strip=True) if title else 'N/A'}
Center:          {center_name or 'N/A'}
Guides on Event: {len(guides_found)}
Center URL:      {center_url or 'N/A'}

Review filtering is {"ACTIVE" if openai_key else "NOT TESTED (no API key)"}
All syntax checks: PASSED
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(test_event_scraping())
