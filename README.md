# Surfbreak Retreat Scraper

Scrapes retreat listings from retreat.guru and enriches them with contact information to build a lead generation database.

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1-2: scraper.py                                               │
│  Scrape retreat.guru → Extract center addresses                     │
│  Output: leads_enriched.csv                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 3: enrich_google.py                                           │
│  Google Places API → Phone, Website, Google Maps URL                │
│  Output: leads_google_enriched.csv                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 4: enrich_website.py                                          │
│  Scrape websites → Email, Instagram, Facebook, LinkedIn, etc.       │
│  Output: leads_final.csv                                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install dependencies

```bash
cd surfbreak_retreat_scraper
uv sync
uv run playwright install chromium
```

### 2. Set your Google Places API key

```bash
export GOOGLE_PLACES_API_KEY="your-api-key-here"
```

To get an API key:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project
3. Enable "Places API" and "Places API (New)"
4. Create an API key in Credentials

## Usage

### Run the full pipeline

```bash
uv run python run_pipeline.py
```

### Or run individual steps

```bash
# Step 1-2: Scrape retreat.guru
uv run python scraper.py

# Step 3: Enrich with Google Places
uv run python enrich_google.py

# Step 4: Scrape websites for contacts
uv run python enrich_website.py
```

## Output Fields

The final `leads_final.csv` contains:

| Field | Description |
|-------|-------------|
| organizer | Retreat center/venue name |
| title | Retreat event title |
| location_city | City, Country |
| detailed_address | Full street address |
| phone | Phone number (from Google) |
| email | Email addresses (from website) |
| website | Website URL |
| instagram | Instagram profile URL |
| facebook | Facebook page URL |
| linkedin | LinkedIn page URL |
| twitter | Twitter/X profile URL |
| dates | Event dates |
| price | Starting price |
| rating | Rating on retreat.guru |
| event_url | Link to retreat.guru event page |
| center_url | Link to retreat.guru center page |
| google_maps_url | Link to Google Maps |

## Configuration

Edit the `SEARCH_URL` in `scraper.py` to change the search parameters:

```python
SEARCH_URL = "https://retreat.guru/search?topic=yoga&experiences_type=yoga&country=mexico"
```

You can modify:
- `topic` - Type of retreat (yoga, meditation, wellness, etc.)
- `country` - Country to search in
- Add other filters from retreat.guru's URL parameters

## Cost Estimate

- Google Places API: ~$32 per 1,000 requests
- For 64 leads with 44 unique centers: ~$1.50

## Files

- `scraper.py` - Scrapes retreat.guru search results and center pages
- `enrich_google.py` - Looks up businesses via Google Places API
- `enrich_website.py` - Scrapes websites for email and social media
- `run_pipeline.py` - Runs the complete pipeline
