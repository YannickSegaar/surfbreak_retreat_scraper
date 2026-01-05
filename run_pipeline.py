"""
Complete Lead Enrichment Pipeline
==================================

Runs the full scraping and enrichment pipeline with support for multiple searches
that append to a master leads database.

SUPPORTED SOURCES:
------------------
- retreat.guru (e.g., https://retreat.guru/search?topic=yoga&country=mexico)
- bookretreats.com (e.g., https://bookretreats.com/s/yoga-retreats/mexico)

The source is auto-detected from the URL.

USAGE:
------
# With auto-generated label (NEW! - label is optional):
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=mexico"

# With custom label:
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=mexico" --label "rg-yoga-mexico"

# BookRetreats.com:
uv run python run_pipeline.py --url "https://bookretreats.com/s/yoga-retreats/mexico"

FEATURES:
---------
- Auto-labeling: Labels are automatically generated from URL parameters
- Deduplication: Already-scraped retreats (by event_url) are skipped
- Scrape description: Rich text describing what filters were used

OUTPUT:
-------
- leads_master.csv: Master database with all leads from all searches and sources
- centers_scraped.csv: All scraped retreat centers with addresses, photos, ratings
- guides_scraped.csv: All scraped guide/teacher profiles with bios, photos, ratings
"""

import argparse
import asyncio
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from dotenv import load_dotenv

# Load .env file FIRST before anything else
load_dotenv()

# Master output file
MASTER_FILE = "leads_master.csv"


def detect_source(url: str) -> str:
    """
    Auto-detect which platform the URL is from.

    Returns: 'retreat.guru', 'bookretreats.com', or raises ValueError
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if "retreat.guru" in domain:
        return "retreat.guru"
    elif "bookretreats.com" in domain:
        return "bookretreats.com"
    else:
        raise ValueError(
            f"Unknown source: {domain}\n"
            f"Supported sources: retreat.guru, bookretreats.com"
        )


def generate_unique_id(organizer: str) -> str:
    """
    Generate a unique ID using SHA256 hash based on ORGANIZER NAME ONLY.

    This means:
    - Same organizer with multiple retreats = same hash (easy to identify unique organizers)
    - Same organizer on different platforms = same hash (cross-platform duplicate detection!)
    - Different organizers = different hash

    Returns first 12 characters of the hash for readability.
    """
    # Normalize: lowercase and strip whitespace
    normalized = organizer.lower().strip()

    # Create SHA256 hash
    hash_object = hashlib.sha256(normalized.encode('utf-8'))

    # Return first 12 chars (still unique enough, more readable)
    return hash_object.hexdigest()[:12]


def get_existing_event_urls() -> set[str]:
    """
    Load existing event URLs from master CSV for deduplication.

    Returns a set of URLs that have already been scraped.
    """
    if not Path(MASTER_FILE).exists():
        return set()

    try:
        df = pd.read_csv(MASTER_FILE)
        if "event_url" not in df.columns:
            return set()
        return set(df["event_url"].dropna().tolist())
    except (pd.errors.EmptyDataError, Exception):
        return set()


def append_to_master(
    new_leads_file: str,
    source_url: str,
    source_label: str,
    source_platform: str,
    scrape_description: str = ""
) -> int:
    """
    Append new leads to the master file with source tracking.

    Returns the number of new leads added.
    """
    # Read new leads
    new_df = pd.read_csv(new_leads_file)

    if len(new_df) == 0:
        print("No new leads to add.")
        return 0

    # Add metadata columns
    scrape_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_df["source_url"] = source_url
    new_df["source_label"] = source_label
    new_df["source_platform"] = source_platform
    new_df["scrape_date"] = scrape_date
    new_df["scrape_description"] = scrape_description

    # Generate unique IDs (based on organizer name only)
    new_df["unique_id"] = new_df.apply(
        lambda row: generate_unique_id(str(row.get("organizer", ""))),
        axis=1
    )

    # Reorder columns to put unique_id and source info first
    priority_cols = ["unique_id", "source_platform", "source_label", "scrape_date", "organizer", "title"]
    other_cols = [c for c in new_df.columns if c not in priority_cols and c not in ["source_url", "scrape_description"]]
    new_df = new_df[priority_cols + other_cols + ["scrape_description", "source_url"]]

    # Check if master file exists and has data
    master_exists = False
    if Path(MASTER_FILE).exists():
        # Check if file is not empty
        try:
            master_df = pd.read_csv(MASTER_FILE)
            if len(master_df) > 0:
                master_exists = True
        except pd.errors.EmptyDataError:
            # File exists but is empty - treat as new
            print(f"  Note: {MASTER_FILE} was empty, starting fresh")
            master_exists = False

    if master_exists:
        # Count duplicates (same unique_id already exists)
        existing_ids = set(master_df["unique_id"].tolist())
        new_ids = set(new_df["unique_id"].tolist())
        duplicate_count = len(new_ids.intersection(existing_ids))

        if duplicate_count > 0:
            print(f"  Note: {duplicate_count} organizers already exist in master database")
            print(f"        (Same organizer may appear on multiple platforms)")

        # Ensure columns match (add missing columns to master)
        for col in new_df.columns:
            if col not in master_df.columns:
                master_df[col] = ""

        # Ensure columns match (add missing columns to new_df)
        for col in master_df.columns:
            if col not in new_df.columns:
                new_df[col] = ""

        # Reorder new_df to match master_df columns
        new_df = new_df[master_df.columns]

        # Append
        combined_df = pd.concat([master_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        duplicate_count = 0

    # Save master file
    combined_df.to_csv(MASTER_FILE, index=False, encoding="utf-8")

    return len(new_df)


async def run_pipeline(search_url: str, source_label: str = None):
    """Run the complete enrichment pipeline."""

    # Auto-detect source
    try:
        source_platform = detect_source(search_url)
    except ValueError as e:
        print(f"ERROR: {e}")
        return

    # Import URL parser for auto-labeling
    from url_parser import parse_url, generate_label, generate_description

    # Auto-generate label and description if not provided
    url_data = parse_url(search_url)

    if not source_label:
        source_label = generate_label(url_data)
        print(f"Auto-generated label: {source_label}")

    scrape_description = generate_description(url_data)

    print("=" * 70)
    print("SURFBREAK RETREAT LEAD ENRICHMENT PIPELINE")
    print("=" * 70)
    print(f"\nSource:       {source_platform}")
    print(f"Search URL:   {search_url[:80]}...")
    print(f"Source Label: {source_label}")
    print(f"Description:  {scrape_description}")
    print(f"Master File:  {MASTER_FILE}")

    # Get existing URLs for deduplication
    existing_urls = get_existing_event_urls()
    if existing_urls:
        print(f"\n✓ Found {len(existing_urls)} existing retreats (will skip duplicates)")

    # Check for API keys (after loading .env)
    google_api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")

    if google_api_key:
        print(f"✓ Google API key loaded ({len(google_api_key)} chars)")
    else:
        print("⚠ GOOGLE_PLACES_API_KEY not set - Google Places enrichment will be skipped")

    if openai_api_key:
        print(f"✓ OpenAI API key loaded ({len(openai_api_key)} chars)")
    else:
        print("⚠ OPENAI_API_KEY not set - AI enrichment will be skipped")

    # Step 1-2: Scrape based on source
    print("\n" + "=" * 70)
    print(f"STEP 1-2: Scraping {source_platform}")
    print("=" * 70)

    # Collect guide URLs for later scraping
    all_guide_urls = set()

    # Variable to hold centers data for later use
    scraped_centers_data = {}

    if source_platform == "retreat.guru":
        from scraper import RetreatScraper, ENRICH_WITH_CENTER_DATA

        async with RetreatScraper(openai_api_key=openai_api_key) as scraper:
            # Scrape search results with pagination (loads ALL results)
            leads = await scraper.scrape_search_page(search_url, skip_urls=existing_urls, paginate=True)

            if ENRICH_WITH_CENTER_DATA and leads:
                await scraper.enrich_with_center_data(leads)

                # Collect guide URLs from center pages
                for center_url, center_data in scraper.scraped_centers.items():
                    if "guides" in center_data:
                        for guide in center_data["guides"]:
                            if guide.get("profile_url"):
                                all_guide_urls.add(guide["profile_url"])

                # Store centers data for later saving
                scraped_centers_data = dict(scraper.scraped_centers)

            scraper.save_to_csv(leads, "leads_enriched.csv")
            scraper.print_summary()

    elif source_platform == "bookretreats.com":
        from scraper_bookretreats import BookRetreatsScraper

        async with BookRetreatsScraper(openai_api_key=openai_api_key) as scraper:
            leads = await scraper.scrape_search_page(search_url, skip_urls=existing_urls)
            scraper.save_to_csv(leads, "leads_enriched.csv")
            scraper.print_summary()

    # Check if leads_enriched.csv was created
    if not Path("leads_enriched.csv").exists():
        print("No new leads found (all may have been already scraped).")
        return

    # Check if there are any leads
    enriched_df = pd.read_csv("leads_enriched.csv")
    if len(enriched_df) == 0:
        print("No new leads to process.")
        Path("leads_enriched.csv").unlink()
        return

    # Step 2.5: Save Centers Data (NEW!)
    if source_platform == "retreat.guru" and scraped_centers_data:
        print("\n" + "=" * 70)
        print("STEP 2.5a: Saving Centers Data")
        print("=" * 70)

        centers_data = []
        for center_url, center_data in scraped_centers_data.items():
            centers_data.append({
                "center_id": center_data.get("center_id", ""),
                "name": center_data.get("name", ""),
                "address": center_data.get("address", ""),
                "description": center_data.get("description", "")[:500] if center_data.get("description") else "",
                "center_photo_url": center_data.get("center_photo_url", ""),
                "google_maps_url": center_data.get("google_maps_url", ""),
                "center_rating": center_data.get("center_rating", 0.0),
                "center_review_count": center_data.get("center_review_count", 0),
                "center_url": center_url,
                "guide_count": len(center_data.get("guides", [])),
                "guide_ids": ",".join([g.get("teacher_id", "") for g in center_data.get("guides", []) if g.get("teacher_id")]),
            })

        if centers_data:
            centers_df = pd.DataFrame(centers_data)
            centers_df.to_csv("centers_scraped.csv", index=False, encoding="utf-8")
            print(f"✓ Saved {len(centers_data)} centers to centers_scraped.csv")

    # Step 2.5b: Direct Guide Profile Scraping
    if all_guide_urls and source_platform == "retreat.guru":
        print("\n" + "=" * 70)
        print("STEP 2.5b: Direct Guide Profile Scraping")
        print("=" * 70)
        print(f"Found {len(all_guide_urls)} unique guide profiles to scrape")

        from scraper_guides import GuideProfileScraper

        async with GuideProfileScraper() as guide_scraper:
            guides = await guide_scraper.scrape_multiple_guides(list(all_guide_urls))
            guide_scraper.print_summary()

            # Save guides to separate CSV for Airtable import
            if guides:
                guides_data = []
                for g in guides:
                    guides_data.append({
                        # Entity IDs
                        "teacher_id": g.teacher_id,
                        "guide_id": g.guide_id,

                        # Basic info
                        "name": g.name,
                        "credentials": g.credentials,
                        "role": g.role,

                        # Detailed info
                        "bio": g.bio[:500] if g.bio else "",  # Truncate for CSV
                        "photo_url": g.photo_url,
                        "profile_url": g.profile_url,

                        # Ratings
                        "rating": g.rating,
                        "review_count": g.review_count,

                        # Affiliations
                        "affiliated_center": g.affiliated_center,
                        "affiliated_center_url": g.affiliated_center_url,
                        "affiliated_center_id": g.affiliated_center_id,

                        # Stats
                        "upcoming_retreats_count": len(g.upcoming_retreats),
                    })

                guides_df = pd.DataFrame(guides_data)
                guides_df.to_csv("guides_scraped.csv", index=False, encoding="utf-8")
                print(f"✓ Saved {len(guides)} guides to guides_scraped.csv")

    # Step 3: Google Places enrichment (CENTER-BASED - more efficient!)
    # Enrich centers first, then propagate to leads
    if google_api_key:
        print("\n" + "=" * 70)
        print("STEP 3: Google Places API Enrichment (CENTER-BASED)")
        print("=" * 70)
        print("Enriching centers instead of individual leads (saves ~44% API calls)")

        from enrich_centers_google import enrich_centers_with_google, propagate_center_enrichment_to_leads

        # Step 3a: Enrich centers with Google Places data
        centers_enriched = await enrich_centers_with_google(
            input_file="centers_scraped.csv",
            output_file="centers_enriched.csv"
        )

        # Step 3b: Propagate center enrichment to leads
        if centers_enriched:
            propagate_center_enrichment_to_leads(
                centers_file="centers_enriched.csv",
                leads_file="leads_enriched.csv",
                output_file="leads_google_enriched.csv"
            )

            # Update centers_scraped.csv with enrichment data for Airtable import
            if Path("centers_enriched.csv").exists():
                Path("centers_enriched.csv").replace("centers_scraped.csv")
                print("✓ Updated centers_scraped.csv with Google enrichment data")
        else:
            # Fallback: copy leads without Google enrichment
            df = pd.read_csv("leads_enriched.csv")
            df.to_csv("leads_google_enriched.csv", index=False, encoding="utf-8")
            print("⚠ Center enrichment failed, continuing without Google data")
    else:
        print("\n" + "=" * 70)
        print("STEP 3: SKIPPED (no API key)")
        print("=" * 70)
        df = pd.read_csv("leads_enriched.csv")
        df["google_business_name"] = ""
        df["google_address"] = ""
        df["phone"] = ""
        df["website"] = ""
        df["google_maps_url"] = ""
        df["google_rating"] = ""
        df["google_reviews"] = ""
        df["latitude"] = ""
        df["longitude"] = ""
        df["distance_to_surfbreak_miles"] = ""
        df.to_csv("leads_google_enriched.csv", index=False, encoding="utf-8")
        print("Created leads_google_enriched.csv with empty contact columns")

    # Step 4: Website scraping
    print("\n" + "=" * 70)
    print("STEP 4: Website Contact Scraping")
    print("=" * 70)

    from enrich_website import enrich_leads_with_website_data
    await enrich_leads_with_website_data("leads_google_enriched.csv", "leads_batch.csv")

    # Step 5: Append to master file
    print("\n" + "=" * 70)
    print("STEP 5: Appending to Master Database")
    print("=" * 70)

    new_count = append_to_master(
        "leads_batch.csv",
        search_url,
        source_label,
        source_platform,
        scrape_description
    )

    # Clean up intermediate files
    for temp_file in ["leads_enriched.csv", "leads_google_enriched.csv", "leads_batch.csv"]:
        if Path(temp_file).exists():
            Path(temp_file).unlink()

    # Step 6: AI-Powered Lead Analysis
    if openai_api_key:
        print("\n" + "=" * 70)
        print("STEP 6: AI-Powered Lead Analysis")
        print("=" * 70)

        from enrich_ai import enrich_leads_with_ai
        await enrich_leads_with_ai(MASTER_FILE, "leads_ai_enriched.csv")

        # Replace master with AI-enriched version
        if Path("leads_ai_enriched.csv").exists():
            Path("leads_ai_enriched.csv").replace(MASTER_FILE)
            print(f"✓ AI enrichment applied to {MASTER_FILE}")
    else:
        print("\n" + "=" * 70)
        print("STEP 6: AI Analysis SKIPPED (no OPENAI_API_KEY)")
        print("=" * 70)
        print("Add OPENAI_API_KEY to .env for AI-powered lead profiling")

    # Final summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE!")
    print("=" * 70)

    # Count total and duplicates in master
    if Path(MASTER_FILE).exists():
        master_df = pd.read_csv(MASTER_FILE)
        total_leads = len(master_df)
        unique_organizers = master_df["unique_id"].nunique()
        duplicate_count = total_leads - unique_organizers

        # Count by platform
        platform_counts = master_df["source_platform"].value_counts().to_dict()

        print(f"\n  Leads added this run:     {new_count}")
        print(f"  Total leads in master:    {total_leads}")
        print(f"  Unique organizers:        {unique_organizers}")
        print(f"  Duplicate entries:        {duplicate_count}")
        print(f"\n  Leads by platform:")
        for platform, count in platform_counts.items():
            print(f"    - {platform}: {count}")
        print(f"\n→ Open {MASTER_FILE} for the complete leads database!")

    print("=" * 70)


def main():
    """Parse arguments and run pipeline."""
    parser = argparse.ArgumentParser(
        description="Scrape retreat websites and build a lead database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported sources (auto-detected from URL):
  - retreat.guru
  - bookretreats.com

Examples:
  # Auto-generated label (NEW! - label is now optional):
  %(prog)s --url "https://retreat.guru/search?topic=yoga&country=mexico"

  # With custom label:
  %(prog)s --url "https://retreat.guru/search?topic=yoga&country=mexico" --label "rg-yoga-mexico"

  # Complex URL with multiple filters:
  %(prog)s --url "https://retreat.guru/search?topic=yoga&topic=meditation&country=mexico&experiences_type=ayahuasca"

  # BookRetreats.com:
  %(prog)s --url "https://bookretreats.com/search?scopes[type]=Yoga+Retreats&scopes[location]=Mexico"

Features:
  - Auto-labeling: Labels are automatically generated from URL parameters
  - Deduplication: Already-scraped retreats are skipped
  - Enhanced extraction: Retreat descriptions, group sizes, and guides
        """
    )

    parser.add_argument(
        "--url", "-u",
        required=True,
        help="The search URL to scrape (retreat.guru or bookretreats.com)"
    )

    parser.add_argument(
        "--label", "-l",
        required=False,
        default=None,
        help="Optional: A short label for this search. If not provided, one is auto-generated from the URL."
    )

    args = parser.parse_args()

    # Run the pipeline
    asyncio.run(run_pipeline(args.url, args.label))


if __name__ == "__main__":
    main()
