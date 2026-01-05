"""
Google Places API Enrichment for Centers
=========================================

Enriches CENTERS (not individual leads) with contact information from Google Places API:
- Phone number
- Website URL
- Google Maps URL (verified)
- Google business name and address
- Google rating and review count
- Latitude/Longitude coordinates
- Distance to Surfbreak PXM (Puerto Escondido)

This is more efficient than enriching per-lead because:
- Multiple events can occur at the same center
- Physical location data (phone, address, coords) belongs to the center, not the event
- Reduces API calls by ~44% (45 centers vs 80 events)

SETUP:
1. Get your API key from Google Cloud Console
2. Set it as environment variable: export GOOGLE_PLACES_API_KEY="your-key"
   Or create a .env file with: GOOGLE_PLACES_API_KEY=your-key
"""

import asyncio
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Import shared components from the original enrichment module
from enrich_google import (
    GOOGLE_API_KEY,
    GooglePlacesClient,
    calculate_distance_to_surfbreak,
    REQUEST_DELAY,
)

# Load .env file if it exists
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Input/output files
CENTERS_INPUT_FILE = "centers_scraped.csv"
CENTERS_OUTPUT_FILE = "centers_enriched.csv"


# =============================================================================
# CENTER ENRICHMENT FUNCTIONS
# =============================================================================

def build_center_search_query(row: pd.Series) -> str:
    """
    Build a search query for Google Places API from center data.

    Uses center name + address for best results.
    """
    name = str(row.get("name", "")).strip()
    address = str(row.get("address", "")).strip()

    # If we have both name and address, combine them
    if name and address:
        # Use just city/country from address if it's very long
        if len(address) > 50:
            # Try to extract city/country (usually last parts)
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 2:
                address = ", ".join(parts[-2:])
        return f"{name}, {address}"
    elif name:
        return name
    elif address:
        return address
    else:
        return ""


async def enrich_centers_with_google(input_file: str = CENTERS_INPUT_FILE, output_file: str = CENTERS_OUTPUT_FILE):
    """
    Read centers CSV and enrich with Google Places data.

    This enriches each unique center once, rather than each event.
    """
    print("=" * 70)
    print("GOOGLE PLACES ENRICHMENT (CENTERS)")
    print("=" * 70)

    if not GOOGLE_API_KEY:
        print("\n⚠ ERROR: No API key found!")
        print("Set your API key:")
        print("  export GOOGLE_PLACES_API_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  GOOGLE_PLACES_API_KEY=your-api-key-here")
        return False

    # Check if input file exists
    if not Path(input_file).exists():
        print(f"\n⚠ ERROR: Centers file not found: {input_file}")
        return False

    # Read input
    df = pd.read_csv(input_file)
    print(f"\nLoaded {len(df)} centers from {input_file}")

    if len(df) == 0:
        print("No centers to enrich.")
        return False

    # Initialize client
    client = GooglePlacesClient(GOOGLE_API_KEY)

    # Add new columns for enrichment data
    enrichment_columns = [
        "google_business_name",
        "google_address",
        "phone",
        "email",  # Placeholder - Google doesn't provide email
        "website",
        "google_maps_url_verified",
        "google_rating",
        "google_reviews",
        "latitude",
        "longitude",
        "distance_to_surfbreak_miles",
    ]

    for col in enrichment_columns:
        if col not in df.columns:
            df[col] = ""

    print(f"\nSearching Google Places API for {len(df)} centers...")
    print("-" * 70)

    for idx, row in df.iterrows():
        center_id = row.get("center_id", f"row_{idx}")
        center_name = row.get("name", "Unknown")

        # Build search query
        query = build_center_search_query(row)

        if not query:
            print(f"[{idx+1}/{len(df)}] {center_name}: No search data available")
            continue

        print(f"[{idx+1}/{len(df)}] {center_name[:40]}...")
        print(f"    Query: {query[:60]}")

        result = await client.search_place(query)

        if result.found:
            print(f"    ✓ Found: {result.business_name}")

            # Update row with enrichment data
            df.at[idx, "google_business_name"] = result.business_name
            df.at[idx, "google_address"] = result.formatted_address
            df.at[idx, "phone"] = result.phone_number
            df.at[idx, "website"] = result.website
            df.at[idx, "google_maps_url_verified"] = result.google_maps_url
            df.at[idx, "google_rating"] = result.rating if result.rating else ""
            df.at[idx, "google_reviews"] = result.total_reviews if result.total_reviews else ""

            # Add coordinates and distance
            if result.latitude and result.longitude:
                df.at[idx, "latitude"] = result.latitude
                df.at[idx, "longitude"] = result.longitude
                distance = calculate_distance_to_surfbreak(result.latitude, result.longitude)
                if distance is not None:
                    df.at[idx, "distance_to_surfbreak_miles"] = distance
                    print(f"    📍 Distance to Surfbreak: {distance} miles")

            if result.phone_number:
                print(f"    📞 Phone: {result.phone_number}")
            if result.website:
                print(f"    🌐 Web: {result.website[:50]}")
        else:
            print(f"    ✗ Not found in Google Places")

        # Rate limiting
        await asyncio.sleep(REQUEST_DELAY)

    await client.close()

    # Save output
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"\nSaved enriched centers to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("CENTER ENRICHMENT SUMMARY")
    print("=" * 70)
    print(f"   Total centers:     {len(df)}")
    print(f"   Places found:      {client.stats['found']}")
    print(f"   Not found:         {client.stats['not_found']}")
    print(f"   Errors:            {client.stats['errors']}")
    print("-" * 70)

    # Count enriched fields
    with_phone = df["phone"].notna() & (df["phone"] != "")
    with_website = df["website"].notna() & (df["website"] != "")
    with_coords = df["latitude"].notna() & (df["latitude"] != "")
    with_distance = df["distance_to_surfbreak_miles"].notna() & (df["distance_to_surfbreak_miles"] != "")

    print(f"   Centers with phone:       {with_phone.sum()}")
    print(f"   Centers with website:     {with_website.sum()}")
    print(f"   Centers with coordinates: {with_coords.sum()}")
    print(f"   Centers with distance:    {with_distance.sum()}")
    print("=" * 70)

    return True


def propagate_center_enrichment_to_leads(
    centers_file: str = CENTERS_OUTPUT_FILE,
    leads_file: str = "leads_enriched.csv",
    output_file: str = "leads_google_enriched.csv"
):
    """
    Copy center enrichment data to leads that reference those centers.

    This joins center enrichment data to leads based on center_id.
    """
    print("\n" + "=" * 70)
    print("PROPAGATING CENTER ENRICHMENT TO LEADS")
    print("=" * 70)

    # Check files exist
    if not Path(centers_file).exists():
        print(f"⚠ Centers file not found: {centers_file}")
        return False

    if not Path(leads_file).exists():
        print(f"⚠ Leads file not found: {leads_file}")
        return False

    # Load data
    centers_df = pd.read_csv(centers_file)
    leads_df = pd.read_csv(leads_file)

    print(f"Loaded {len(centers_df)} centers and {len(leads_df)} leads")

    # Define which columns to copy from centers to leads
    enrichment_columns = [
        "google_business_name",
        "google_address",
        "phone",
        "website",
        "google_maps_url_verified",
        "google_rating",
        "google_reviews",
        "latitude",
        "longitude",
        "distance_to_surfbreak_miles",
    ]

    # Create lookup dict from centers
    center_enrichment = {}
    for _, row in centers_df.iterrows():
        center_id = row.get("center_id", "")
        if center_id:
            center_enrichment[str(center_id)] = {
                col: row.get(col, "") for col in enrichment_columns if col in centers_df.columns
            }

    print(f"Built enrichment lookup for {len(center_enrichment)} centers")

    # Add columns to leads if not present
    for col in enrichment_columns:
        if col not in leads_df.columns:
            leads_df[col] = ""

    # Apply enrichment to leads
    enriched_count = 0
    for idx, row in leads_df.iterrows():
        center_id = str(row.get("center_id", ""))
        if center_id and center_id in center_enrichment:
            enrichment = center_enrichment[center_id]
            for col, value in enrichment.items():
                if value and str(value).strip():
                    leads_df.at[idx, col] = value
            enriched_count += 1

    print(f"Applied center enrichment to {enriched_count} leads")

    # Save output
    leads_df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"Saved enriched leads to {output_file}")

    return True


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    async def main():
        # Enrich centers
        success = await enrich_centers_with_google()

        if success:
            # Propagate to leads
            propagate_center_enrichment_to_leads()

    asyncio.run(main())
