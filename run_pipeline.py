"""
Complete Lead Enrichment Pipeline
==================================

Runs the full scraping and enrichment pipeline with support for multiple searches
that append to a master leads database.

USAGE:
------
# Basic usage with URL and label:
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=mexico" --label "yoga-mexico"

# Examples for different searches:
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=meditation&country=costa-rica" --label "meditation-costa-rica"
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=wellness&country=indonesia" --label "wellness-bali"
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=usa" --label "yoga-usa"

# All leads are appended to leads_master.csv with:
# - unique_id: SHA256 hash based on organizer + title (identifies duplicates)
# - source_label: Your custom label for this search
# - source_url: The full search URL
# - scrape_date: When this lead was scraped

SETUP:
------
Create a .env file with your Google API key:
GOOGLE_PLACES_API_KEY=your-api-key-here

OUTPUT:
-------
- leads_master.csv: Master database with all leads from all searches
"""

import argparse
import asyncio
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load .env file FIRST before anything else
load_dotenv()

# Master output file
MASTER_FILE = "leads_master.csv"


def generate_unique_id(organizer: str) -> str:
    """
    Generate a unique ID using SHA256 hash based on ORGANIZER NAME ONLY.

    This means:
    - Same organizer with multiple retreats = same hash (easy to identify unique organizers)
    - Different organizers = different hash

    Returns first 12 characters of the hash for readability.
    """
    # Normalize: lowercase and strip whitespace
    normalized = organizer.lower().strip()

    # Create SHA256 hash
    hash_object = hashlib.sha256(normalized.encode('utf-8'))

    # Return first 12 chars (still unique enough, more readable)
    return hash_object.hexdigest()[:12]


def append_to_master(new_leads_file: str, source_url: str, source_label: str) -> int:
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
    new_df["scrape_date"] = scrape_date

    # Generate unique IDs (based on organizer name only)
    new_df["unique_id"] = new_df.apply(
        lambda row: generate_unique_id(str(row.get("organizer", ""))),
        axis=1
    )

    # Reorder columns to put unique_id and source info first
    priority_cols = ["unique_id", "source_label", "scrape_date", "organizer", "title"]
    other_cols = [c for c in new_df.columns if c not in priority_cols and c != "source_url"]
    new_df = new_df[priority_cols + other_cols + ["source_url"]]

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
            print(f"  Note: {duplicate_count} leads have same unique_id as existing records")
            print(f"        (These are the same retreats from different searches)")

        # Append (keeping duplicates as requested)
        combined_df = pd.concat([master_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        duplicate_count = 0

    # Save master file
    combined_df.to_csv(MASTER_FILE, index=False, encoding="utf-8")

    return len(new_df)


async def run_pipeline(search_url: str, source_label: str):
    """Run the complete enrichment pipeline."""
    print("=" * 70)
    print("SURFBREAK RETREAT LEAD ENRICHMENT PIPELINE")
    print("=" * 70)
    print(f"\nSearch URL:   {search_url}")
    print(f"Source Label: {source_label}")
    print(f"Master File:  {MASTER_FILE}")

    # Check for API key (after loading .env)
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if api_key:
        print(f"\n✓ Google API key loaded ({len(api_key)} chars)")
    else:
        print("\n⚠ WARNING: GOOGLE_PLACES_API_KEY not set!")
        print("Google Places enrichment will be skipped.")

    # Step 1-2: Scrape retreat.guru
    print("\n" + "=" * 70)
    print("STEP 1-2: Scraping retreat.guru")
    print("=" * 70)

    from scraper import RetreatScraper, ENRICH_WITH_CENTER_DATA

    async with RetreatScraper() as scraper:
        # Scrape with the provided URL
        leads = await scraper.scrape_search_page(search_url)

        # Enrich with center data
        if ENRICH_WITH_CENTER_DATA and leads:
            await scraper.enrich_with_center_data(leads)

        # Save to temporary file
        scraper.save_to_csv(leads, "leads_enriched.csv")
        scraper.print_summary()

    # Check if leads_enriched.csv was created
    if not Path("leads_enriched.csv").exists():
        print("ERROR: leads_enriched.csv not created!")
        return

    # Step 3: Google Places enrichment
    if api_key:
        print("\n" + "=" * 70)
        print("STEP 3: Google Places API Enrichment")
        print("=" * 70)

        from enrich_google import enrich_leads_with_google
        await enrich_leads_with_google("leads_enriched.csv", "leads_google_enriched.csv")
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

    new_count = append_to_master("leads_batch.csv", search_url, source_label)

    # Clean up intermediate files
    for temp_file in ["leads_enriched.csv", "leads_google_enriched.csv", "leads_batch.csv"]:
        if Path(temp_file).exists():
            Path(temp_file).unlink()

    # Final summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE!")
    print("=" * 70)

    # Count total and duplicates in master
    if Path(MASTER_FILE).exists():
        master_df = pd.read_csv(MASTER_FILE)
        total_leads = len(master_df)
        unique_leads = master_df["unique_id"].nunique()
        duplicate_count = total_leads - unique_leads

        print(f"\n  Leads added this run:     {new_count}")
        print(f"  Total leads in master:    {total_leads}")
        print(f"  Unique retreats:          {unique_leads}")
        print(f"  Duplicate entries:        {duplicate_count}")
        print(f"\n→ Open {MASTER_FILE} for the complete leads database!")

    print("=" * 70)


def main():
    """Parse arguments and run pipeline."""
    parser = argparse.ArgumentParser(
        description="Scrape retreat.guru and build a lead database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://retreat.guru/search?topic=yoga&country=mexico" --label "yoga-mexico"
  %(prog)s --url "https://retreat.guru/search?topic=meditation&country=costa-rica" --label "meditation-cr"
  %(prog)s --url "https://retreat.guru/search?topic=wellness&country=indonesia" --label "wellness-bali"
        """
    )

    parser.add_argument(
        "--url", "-u",
        required=True,
        help="The retreat.guru search URL to scrape"
    )

    parser.add_argument(
        "--label", "-l",
        required=True,
        help="A short label for this search (e.g., 'yoga-mexico', 'meditation-bali')"
    )

    args = parser.parse_args()

    # Run the pipeline
    asyncio.run(run_pipeline(args.url, args.label))


if __name__ == "__main__":
    main()
