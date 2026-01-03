"""
Google Places API Enrichment
============================

Enriches leads with contact information from Google Places API:
- Phone number
- Website URL
- Google Maps URL
- Verified business name and address
- Latitude/Longitude coordinates
- Distance to Surfbreak PXM (Puerto Escondido)

SETUP:
1. Get your API key from Google Cloud Console
2. Set it as environment variable: export GOOGLE_PLACES_API_KEY="your-key"
   Or create a .env file with: GOOGLE_PLACES_API_KEY=your-key

PRICING:
- Text Search: ~$32 per 1,000 requests
- For 64 leads ≈ $2-3 total
"""

import asyncio
import os
import re
from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import httpx
import pandas as pd
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get API key from environment variable or .env file
GOOGLE_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

# Input/output files
INPUT_FILE = "leads_enriched.csv"
OUTPUT_FILE = "leads_google_enriched.csv"

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between requests (be respectful)

# Google Places API endpoints
PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# =============================================================================
# SURFBREAK PXM LOCATION (for distance calculations)
# =============================================================================
# Address: Los Laureles, Nogales Tamarindos, Brisas de Zicatela,
#          70934 Puerto Escondido, Oax., Mexico
# TODO: Update with exact coordinates from Google Maps
SURFBREAK_LAT = 15.8427193  # Approximate - update with exact coordinates
SURFBREAK_LNG = -97.04802360000001  # Approximate - update with exact coordinates


# =============================================================================
# HAVERSINE DISTANCE CALCULATION
# =============================================================================

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance in miles between two points using Haversine formula.

    The Haversine formula calculates the great-circle distance between two points
    on a sphere given their longitudes and latitudes.

    Args:
        lat1, lng1: First point coordinates (degrees)
        lat2, lng2: Second point coordinates (degrees)

    Returns:
        Distance in miles
    """
    R = 3959  # Earth's radius in miles (use 6371 for km)

    # Convert to radians
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def calculate_distance_to_surfbreak(lat: float, lng: float) -> float | None:
    """
    Calculate distance in miles from a location to Surfbreak PXM.

    Args:
        lat: Latitude of the location
        lng: Longitude of the location

    Returns:
        Distance in miles, or None if coordinates are invalid
    """
    if not lat or not lng or lat == 0 or lng == 0:
        return None
    return round(haversine_distance(lat, lng, SURFBREAK_LAT, SURFBREAK_LNG), 1)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PlaceResult:
    """Result from Google Places API."""
    found: bool = False
    place_id: str = ""
    business_name: str = ""
    formatted_address: str = ""
    phone_number: str = ""
    website: str = ""
    google_maps_url: str = ""
    rating: float = 0.0
    total_reviews: int = 0
    types: str = ""  # Business categories
    latitude: float = 0.0
    longitude: float = 0.0


# =============================================================================
# GOOGLE PLACES API CLIENT
# =============================================================================

class GooglePlacesClient:
    """Client for Google Places API (New)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30)
        self.stats = {"found": 0, "not_found": 0, "errors": 0}

    async def close(self):
        await self.client.aclose()

    async def search_place(self, query: str, location_bias: str = "Mexico") -> PlaceResult:
        """
        Search for a place using text query.

        Uses the new Places API (v1) which has better results and more fields.
        """
        if not self.api_key:
            print("  ⚠ No API key set!")
            return PlaceResult()

        # Add location context to improve results
        search_query = f"{query}"
        if location_bias and location_bias.lower() not in query.lower():
            search_query = f"{query} {location_bias}"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join([
                "places.id",
                "places.displayName",
                "places.formattedAddress",
                "places.nationalPhoneNumber",
                "places.internationalPhoneNumber",
                "places.websiteUri",
                "places.googleMapsUri",
                "places.rating",
                "places.userRatingCount",
                "places.types",
                "places.location",  # Latitude/Longitude for distance calculations
            ])
        }

        body = {
            "textQuery": search_query,
            "maxResultCount": 1,  # We only need the top result
        }

        try:
            response = await self.client.post(
                PLACES_TEXT_SEARCH_URL,
                headers=headers,
                json=body
            )

            if response.status_code != 200:
                error_text = response.text[:200]
                print(f"  ⚠ API error: {response.status_code} - {error_text}")
                self.stats["errors"] += 1
                return PlaceResult()

            data = response.json()
            places = data.get("places", [])

            if not places:
                self.stats["not_found"] += 1
                return PlaceResult(found=False)

            # Get the first (best) result
            place = places[0]
            self.stats["found"] += 1

            # Extract location coordinates
            location = place.get("location", {})
            latitude = location.get("latitude", 0.0)
            longitude = location.get("longitude", 0.0)

            return PlaceResult(
                found=True,
                place_id=place.get("id", ""),
                business_name=place.get("displayName", {}).get("text", ""),
                formatted_address=place.get("formattedAddress", ""),
                phone_number=place.get("internationalPhoneNumber", "") or place.get("nationalPhoneNumber", ""),
                website=place.get("websiteUri", ""),
                google_maps_url=place.get("googleMapsUri", ""),
                rating=place.get("rating", 0.0),
                total_reviews=place.get("userRatingCount", 0),
                types=", ".join(place.get("types", [])[:3]),  # First 3 types
                latitude=latitude,
                longitude=longitude,
            )

        except Exception as e:
            print(f"  ⚠ Request error: {str(e)[:50]}")
            self.stats["errors"] += 1
            return PlaceResult()


# =============================================================================
# ENRICHMENT FUNCTIONS
# =============================================================================

async def enrich_leads_with_google(input_file: str, output_file: str):
    """
    Read leads CSV and enrich with Google Places data.
    """
    print("=" * 70)
    print("GOOGLE PLACES ENRICHMENT")
    print("=" * 70)

    if not GOOGLE_API_KEY:
        print("\n⚠ ERROR: No API key found!")
        print("Set your API key:")
        print("  export GOOGLE_PLACES_API_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  GOOGLE_PLACES_API_KEY=your-api-key-here")
        return

    # Read input
    df = pd.read_csv(input_file)
    print(f"\nLoaded {len(df)} leads from {input_file}")

    # Get unique search queries (avoid duplicate API calls)
    unique_queries = df["search_query"].dropna().unique()
    print(f"Unique search queries: {len(unique_queries)}")

    # Initialize client
    client = GooglePlacesClient(GOOGLE_API_KEY)

    # Cache for results (to avoid duplicate lookups)
    results_cache: dict[str, PlaceResult] = {}

    print(f"\nSearching Google Places API...")
    print("-" * 70)

    for i, query in enumerate(unique_queries):
        if not query or pd.isna(query):
            continue

        print(f"[{i+1}/{len(unique_queries)}] Searching: {query[:60]}...")

        result = await client.search_place(query)
        results_cache[query] = result

        if result.found:
            print(f"  ✓ Found: {result.business_name}")
            if result.phone_number:
                print(f"    Phone: {result.phone_number}")
            if result.website:
                print(f"    Web: {result.website[:50]}")
        else:
            print(f"  ✗ Not found")

        # Rate limiting
        await asyncio.sleep(REQUEST_DELAY)

    await client.close()

    # Apply results to dataframe
    print("\n" + "-" * 70)
    print("Applying results to leads...")

    # Add new columns
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

    for idx, row in df.iterrows():
        query = row.get("search_query", "")
        if query and query in results_cache:
            result = results_cache[query]
            if result.found:
                df.at[idx, "google_business_name"] = result.business_name
                df.at[idx, "google_address"] = result.formatted_address
                df.at[idx, "phone"] = result.phone_number
                df.at[idx, "website"] = result.website
                df.at[idx, "google_maps_url"] = result.google_maps_url
                df.at[idx, "google_rating"] = result.rating if result.rating else ""
                df.at[idx, "google_reviews"] = result.total_reviews if result.total_reviews else ""
                # Add coordinates and distance
                if result.latitude and result.longitude:
                    df.at[idx, "latitude"] = result.latitude
                    df.at[idx, "longitude"] = result.longitude
                    distance = calculate_distance_to_surfbreak(result.latitude, result.longitude)
                    if distance is not None:
                        df.at[idx, "distance_to_surfbreak_miles"] = distance

    # Save output
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"\nSaved enriched data to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("ENRICHMENT SUMMARY")
    print("=" * 70)
    print(f"   Places found:     {client.stats['found']}")
    print(f"   Not found:        {client.stats['not_found']}")
    print(f"   Errors:           {client.stats['errors']}")
    print("-" * 70)

    # Count enriched fields
    with_phone = df["phone"].notna() & (df["phone"] != "")
    with_website = df["website"].notna() & (df["website"] != "")
    with_coords = df["latitude"].notna() & (df["latitude"] != "")
    with_distance = df["distance_to_surfbreak_miles"].notna() & (df["distance_to_surfbreak_miles"] != "")

    print(f"   Leads with phone:      {with_phone.sum()}")
    print(f"   Leads with website:    {with_website.sum()}")
    print(f"   Leads with coordinates: {with_coords.sum()}")
    print(f"   Leads with distance:   {with_distance.sum()}")
    print("=" * 70)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    asyncio.run(enrich_leads_with_google(INPUT_FILE, OUTPUT_FILE))
