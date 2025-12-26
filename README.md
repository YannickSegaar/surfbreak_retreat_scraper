# Surfbreak Retreat Scraper

Scrapes retreat listings from multiple platforms and enriches them with contact information to build a lead generation database.

## Supported Platforms

- **retreat.guru** - Global retreat marketplace
- **bookretreats.com** - Retreat booking platform

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1-2: Scrape retreat platform                                  │
│  - scraper.py (retreat.guru)                                        │
│  - scraper_bookretreats.py (bookretreats.com)                       │
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
│  Output: leads_batch.csv                                            │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 5: Append to Master Database                                  │
│  Adds unique_id, source tracking, deduplication                     │
│  Output: leads_master.csv                                           │
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

Create a `.env` file:
```
GOOGLE_PLACES_API_KEY=your-api-key-here
```

Or export directly:
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

The source platform is **auto-detected** from the URL:

```bash
# Scrape retreat.guru
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=mexico" --label "rg-yoga-mexico"

# Scrape bookretreats.com
uv run python run_pipeline.py --url "https://bookretreats.com/s/yoga-retreats/mexico" --label "br-yoga-mexico"
```

### More examples

```bash
# Retreat.guru - different searches
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=meditation&country=costa-rica" --label "rg-meditation-cr"
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=wellness&country=indonesia" --label "rg-wellness-bali"

# BookRetreats - different searches
uv run python run_pipeline.py --url "https://bookretreats.com/s/meditation-retreats/bali" --label "br-meditation-bali"
uv run python run_pipeline.py --url "https://bookretreats.com/s/wellness-retreats/costa-rica" --label "br-wellness-cr"
```

### Run individual scrapers (standalone)

```bash
# Retreat.guru only
uv run python scraper.py

# BookRetreats only
uv run python scraper_bookretreats.py

# Google Places enrichment
uv run python enrich_google.py

# Website contact scraping
uv run python enrich_website.py
```

## Output: leads_master.csv

All leads are appended to a single master file with these fields:

| Field | Description |
|-------|-------------|
| **unique_id** | SHA256 hash of organizer name (same across platforms!) |
| **source_platform** | "retreat.guru" or "bookretreats.com" |
| **source_label** | Your custom label for this search |
| **scrape_date** | When this lead was scraped |
| organizer | Retreat center/venue name |
| title | Retreat event title |
| location_city | City, State, Country |
| detailed_address | Full street address |
| phone | Phone number (from Google) |
| email | Email addresses (from website) |
| website | Website URL |
| instagram | Instagram profile URL |
| facebook | Facebook page URL |
| linkedin | LinkedIn page URL |
| twitter | Twitter/X profile URL |
| youtube | YouTube channel URL |
| tiktok | TikTok profile URL |
| dates | Event dates |
| price | Starting price |
| rating | Rating on platform |
| event_url | Link to retreat page |
| center_url | Link to organizer profile |
| google_maps_url | Link to Google Maps |
| source_url | The search URL used |

## Cross-Platform Duplicate Detection

The `unique_id` is based on the **organizer name only**, which means:

- Same organizer with multiple retreats → same hash
- Same organizer on different platforms → same hash
- You can easily identify organizers that appear on both retreat.guru AND bookretreats.com

Example: If "Casa Violeta" is on both platforms, they'll have the same `unique_id`, making it easy to:
1. Avoid contacting the same organizer twice
2. Compare their listings across platforms
3. Identify which organizers have broader reach

## Cost Estimate

- Google Places API: ~$32 per 1,000 requests
- For 100 leads with 60 unique organizers: ~$2-3

## Files

| File | Description |
|------|-------------|
| `run_pipeline.py` | Main entry point - runs full pipeline with CLI args |
| `scraper.py` | retreat.guru scraper |
| `scraper_bookretreats.py` | bookretreats.com scraper |
| `enrich_google.py` | Google Places API enrichment |
| `enrich_website.py` | Website scraping for email/social |
| `DOCUMENTATION.md` | Detailed technical documentation |
