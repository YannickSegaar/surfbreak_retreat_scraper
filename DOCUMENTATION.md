# Surfbreak Retreat Scraper - Technical Documentation

## Overview

This project is a **lead generation pipeline** that scrapes retreat listings from [retreat.guru](https://retreat.guru) and enriches them with contact information from multiple sources. The goal is to help retreat venue owners find and contact retreat organizers who might be interested in using their location.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Pipeline Stages](#pipeline-stages)
3. [Data Flow](#data-flow)
4. [Scripts & Components](#scripts--components)
5. [APIs Used](#apis-used)
6. [Input & Output](#input--output)
7. [Configuration](#configuration)
8. [Technical Implementation Details](#technical-implementation-details)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RETREAT LEAD GENERATION PIPELINE                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   STEP 1        │     │   STEP 2        │     │   STEP 3        │     │   STEP 4        │
│                 │     │                 │     │                 │     │                 │
│  Scrape Search  │────▶│  Scrape Center  │────▶│  Google Places  │────▶│  Scrape Website │
│  Results Page   │     │  Detail Pages   │     │  API Lookup     │     │  Contact Info   │
│                 │     │                 │     │                 │     │                 │
│  (Playwright)   │     │  (Playwright)   │     │  (REST API)     │     │  (httpx + BS4)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │                       │
        ▼                       ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    OUTPUT FILES                                          │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────┤
│                     │  leads_enriched.csv │leads_google_enriched│   leads_final.csv     │
│                     │                     │        .csv         │                       │
│  Basic retreat info │  + Street addresses │  + Phone numbers    │  + Email addresses    │
│  from search page   │  from center pages  │  + Website URLs     │  + Social media links │
│                     │                     │  + Google Maps URLs │                       │
└─────────────────────┴─────────────────────┴─────────────────────┴───────────────────────┘
```

---

## Pipeline Stages

### Stage 1: Scrape Search Results (`scraper.py`)

**Purpose:** Extract basic retreat listing information from retreat.guru search results.

**How it works:**
1. Uses **Playwright** (headless Chromium browser) to load the search page
2. The page is JavaScript-rendered, so we need a real browser to execute JS
3. Waits for the DOM content to load and JS to render
4. Extracts retreat "tiles" using BeautifulSoup with CSS selectors

**Data extracted:**
- Retreat title
- Organizer/center name
- City, Country location
- Event dates
- Price
- Rating & reviews
- Event page URL
- Center page URL

**Why Playwright?**
- retreat.guru is a JavaScript Single Page Application (SPA)
- Standard HTTP requests return empty/partial HTML
- Need a real browser to execute JavaScript and render content

---

### Stage 2: Scrape Center Pages (`scraper.py`)

**Purpose:** Get detailed street addresses from each retreat center's dedicated page.

**How it works:**
1. Collects unique center URLs from Stage 1
2. Visits each center page with Playwright
3. Extracts the detailed address from `[data-cy='center-location']` element
4. Caches results to avoid duplicate requests for same center

**Data extracted:**
- Full street address (e.g., "Calle Conejos, Brisas de Zicatela, 70934 Puerto Escondido, Oaxaca, Mexico")
- Center description (if available)

**Why this matters:**
- Search results only show "City, Country"
- Detailed addresses enable accurate Google Maps/Places lookups

---

### Stage 3: Google Places API Enrichment (`enrich_google.py`)

**Purpose:** Find phone numbers and websites via Google's business database.

**How it works:**
1. Reads the `search_query` column (format: "Business Name + Address")
2. Sends text search requests to Google Places API (New)
3. Extracts business information from matched results
4. Caches results to avoid duplicate API calls for same business

**API Used:** Google Places API (New) - Text Search endpoint

**Request format:**
```
POST https://places.googleapis.com/v1/places:searchText
Headers:
  X-Goog-Api-Key: <your-api-key>
  X-Goog-FieldMask: places.displayName,places.formattedAddress,...

Body:
  {
    "textQuery": "Barbarenas Calle Conejos, Puerto Escondido, Mexico",
    "maxResultCount": 1
  }
```

**Data extracted:**
- Phone number (international format)
- Website URL
- Google Maps URL
- Google rating & review count
- Verified business name and address

**Cost:** ~$32 per 1,000 requests (approximately $1-2 for 64 leads)

---

### Stage 4: Website Scraping (`enrich_website.py`)

**Purpose:** Extract email addresses and social media links from business websites.

**How it works:**
1. Reads websites found in Stage 3
2. For each website, scrapes:
   - Homepage
   - Common contact pages (/contact, /about, /contact-us, etc.)
3. Extracts data using regex patterns and link analysis
4. Uses httpx (async HTTP client) - no browser needed for most sites

**Pages checked per website:**
```python
CONTACT_PAGE_PATHS = [
    "/contact",
    "/contact-us",
    "/contacto",
    "/about",
    "/about-us",
    "/connect",
    "/get-in-touch",
]
```

**Data extracted:**

| Data Type | Method |
|-----------|--------|
| Email | Regex pattern matching + `mailto:` links |
| Instagram | Links containing `instagram.com/` |
| Facebook | Links containing `facebook.com/` |
| LinkedIn | Links containing `linkedin.com/company/` or `/in/` |
| Twitter/X | Links containing `twitter.com/` or `x.com/` |
| YouTube | Links containing `youtube.com/` |
| TikTok | Links containing `tiktok.com/` |

**Email extraction regex:**
```python
r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
```

**Filtering:** Excludes false positives like:
- `noreply@`, `no-reply@`
- Image files (`.png@`, `.jpg@`)
- Common placeholder domains

---

## Data Flow

```
INPUT: retreat.guru search URL
  │
  │  Example: https://retreat.guru/search?topic=yoga&country=mexico
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Search Page Scraping                                │
│                                                             │
│ CSS Selectors used:                                         │
│ • article.search-event-tile     (retreat card container)    │
│ • h2                            (title)                     │
│ • a[href*='/centers/']          (center link)               │
│ • .search-event-tile__location  (location info)             │
│ • .search-event-tile__dates     (dates)                     │
│ • .search-event-tile__price     (price)                     │
│ • .search-event-tile__reviews   (rating)                    │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Center Page Scraping                                │
│                                                             │
│ For each unique center URL:                                 │
│ • https://retreat.guru/centers/156-1/yandara-yoga-institute │
│                                                             │
│ CSS Selectors used:                                         │
│ • [data-cy='center-location']   (full street address)       │
│ • .center-description           (about text)                │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Google Places API                                   │
│                                                             │
│ Search query format:                                        │
│ "{organizer} {detailed_address}"                            │
│                                                             │
│ Example:                                                    │
│ "Yandara Yoga Institute Carretera 19, KM 74, Todos Santos"  │
│                                                             │
│ Fields requested from API:                                  │
│ • displayName, formattedAddress                             │
│ • internationalPhoneNumber, nationalPhoneNumber             │
│ • websiteUri, googleMapsUri                                 │
│ • rating, userRatingCount, types                            │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Website Scraping                                    │
│                                                             │
│ For each website URL found:                                 │
│ 1. Fetch homepage                                           │
│ 2. Fetch /contact, /about, etc.                             │
│ 3. Parse HTML for:                                          │
│    • mailto: links → Email                                  │
│    • Social media URLs → Instagram, Facebook, etc.          │
│    • Email patterns in text                                 │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
OUTPUT: leads_final.csv (complete enriched database)
```

---

## Scripts & Components

### File Structure

```
surfbreak_retreat_scraper/
├── .env                    # API keys (not in git)
├── .gitignore
├── pyproject.toml          # Project dependencies
├── uv.lock                 # Locked dependency versions
│
├── run_pipeline.py         # Main entry point - runs all steps
├── scraper.py              # Steps 1-2: retreat.guru scraping
├── enrich_google.py        # Step 3: Google Places API
├── enrich_website.py       # Step 4: Website scraping
│
├── leads_enriched.csv      # Output after Steps 1-2
├── leads_google_enriched.csv # Output after Step 3
└── leads_final.csv         # Final output after Step 4
```

### Script Descriptions

#### `run_pipeline.py`
- **Purpose:** Orchestrates the entire pipeline
- **Dependencies:** All other scripts
- **Features:**
  - Loads `.env` file for API keys
  - Runs steps sequentially
  - Handles missing API key gracefully (skips Google step)
  - Creates intermediate files between steps

#### `scraper.py`
- **Purpose:** Scrapes retreat.guru
- **Key Classes:**
  - `RetreatLead` - Data class for a single lead
  - `RetreatScraper` - Main scraper with Playwright browser
  - `ScraperStats` - Tracks success/error counts
- **Browser:** Headless Chromium via Playwright

#### `enrich_google.py`
- **Purpose:** Google Places API integration
- **Key Classes:**
  - `PlaceResult` - Data class for API response
  - `GooglePlacesClient` - Async API client
- **HTTP Client:** httpx (async)

#### `enrich_website.py`
- **Purpose:** Scrapes websites for contact info
- **Key Classes:**
  - `ContactInfo` - Data class for extracted contacts
  - `WebsiteScraper` - Async website scraper
- **HTTP Client:** httpx (async)
- **Parser:** BeautifulSoup with lxml

---

## APIs Used

### 1. Google Places API (New)

**Endpoint:** `https://places.googleapis.com/v1/places:searchText`

**Authentication:** API key in header (`X-Goog-Api-Key`)

**Required setup:**
1. Google Cloud Console account
2. Enable "Places API" and "Places API (New)"
3. Create API key
4. Enable billing (free tier: $200/month)

**Pricing (as of 2024):**
| Operation | Cost per 1,000 |
|-----------|----------------|
| Text Search | $32.00 |
| Place Details | $17.00 |

**Rate limits:**
- Default: 100 requests/second
- Can be increased in Cloud Console

### 2. retreat.guru (Web Scraping)

**No official API** - data extracted via web scraping

**Pages scraped:**
- Search results: `https://retreat.guru/search?topic=yoga&country=mexico`
- Center pages: `https://retreat.guru/centers/{id}/`

**Rate limiting implemented:**
- 1 second delay between center page requests
- Respectful scraping to avoid overloading servers

---

## Input & Output

### Input

**Primary input:** retreat.guru search URL

```
https://retreat.guru/search?topic=yoga&experiences_type=yoga&country=mexico
```

**URL Parameters:**
| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| `topic` | Type of retreat | yoga, meditation, wellness, detox |
| `experiences_type` | Experience category | yoga, meditation, fitness |
| `country` | Country filter | mexico, usa, costa-rica |

### Output Files

#### `leads_enriched.csv` (After Steps 1-2)

| Column | Description | Example |
|--------|-------------|---------|
| organizer | Center/venue name | Yandara Yoga Institute |
| title | Retreat event name | 28 day 300-hour Advanced YTT |
| location_city | City, Country | Todos Santos, Mexico |
| detailed_address | Full street address | Carretera 19, KM 74, Todos Santos, Baja Calif. Mexico |
| dates | Event dates | March 29 - April 26, 2026 |
| price | Starting price | $4,000.00 |
| rating | Rating on retreat.guru | 5 (1 review) |
| event_url | Link to event page | https://retreat.guru/events/156-1514/... |
| center_url | Link to center page | https://retreat.guru/centers/156-1/ |
| search_query | Pre-formatted for Google | Yandara Yoga Institute Carretera 19, KM 74... |

#### `leads_google_enriched.csv` (After Step 3)

All columns from above, plus:

| Column | Description | Example |
|--------|-------------|---------|
| google_business_name | Verified business name | Yandara Yoga Institute |
| google_address | Verified address | Carretera a Todos Santos 19, La Paz, Mexico |
| phone | Phone number | +52 612 123 4567 |
| website | Website URL | https://www.yandara.com |
| google_maps_url | Google Maps link | https://maps.google.com/?cid=... |
| google_rating | Google rating | 4.8 |
| google_reviews | Number of reviews | 127 |

#### `leads_final.csv` (After Step 4)

All columns from above, plus:

| Column | Description | Example |
|--------|-------------|---------|
| email | Email address(es) | info@yandara.com; contact@yandara.com |
| instagram | Instagram URL | https://instagram.com/yandarayoga |
| facebook | Facebook URL | https://facebook.com/yandarayoga |
| linkedin | LinkedIn URL | https://linkedin.com/company/yandara |
| twitter | Twitter/X URL | https://twitter.com/yandarayoga |
| youtube | YouTube URL | https://youtube.com/c/yandarayoga |
| tiktok | TikTok URL | https://tiktok.com/@yandarayoga |

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_PLACES_API_KEY=your-api-key-here
```

### Configurable Settings in `scraper.py`

```python
# Search URL - modify to change search parameters
SEARCH_URL = "https://retreat.guru/search?topic=yoga&experiences_type=yoga&country=mexico"

# Delays between requests (seconds)
PAGE_DELAY = 1.0

# Request timeout (milliseconds)
REQUEST_TIMEOUT = 30

# Whether to scrape center pages for detailed addresses
ENRICH_WITH_CENTER_DATA = True
```

### Configurable Settings in `enrich_google.py`

```python
# Rate limiting
REQUEST_DELAY = 0.5  # seconds between API calls
```

### Configurable Settings in `enrich_website.py`

```python
# Request settings
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.5

# Pages to check for contact info
CONTACT_PAGE_PATHS = [
    "/contact",
    "/contact-us",
    "/contacto",
    "/about",
    # ... add more as needed
]
```

---

## Technical Implementation Details

### Why These Technologies?

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **Playwright** | Browser automation | Handles JavaScript-rendered pages that `requests` cannot |
| **BeautifulSoup** | HTML parsing | Fast, Pythonic, well-documented |
| **lxml** | HTML parser backend | Faster than html.parser |
| **httpx** | HTTP requests | Async support, modern API, similar to requests |
| **pandas** | Data handling | Easy CSV read/write, data manipulation |
| **python-dotenv** | Environment config | Secure API key management |

### Async Architecture

The scraper uses Python's `asyncio` for concurrent operations:

```python
async with RetreatScraper() as scraper:
    leads = await scraper.scrape_search_page(url)
    await scraper.enrich_with_center_data(leads)
```

Benefits:
- Non-blocking I/O during page loads
- Efficient handling of multiple HTTP requests
- Better resource utilization

### Error Handling Strategy

1. **Page timeouts:** Retry with different wait strategies
2. **Missing elements:** Return empty strings, don't crash
3. **API errors:** Log and continue with next item
4. **Network failures:** Catch exceptions, track in stats

### Caching

Both Google API and center page scraping use in-memory caching:

```python
self.scraped_centers: dict[str, dict] = {}  # URL → data mapping
```

This prevents:
- Duplicate API calls (saves money)
- Redundant page loads (saves time)
- Same center appearing in multiple retreats

---

## Usage Examples

### Run Full Pipeline

```bash
cd surfbreak_retreat_scraper
uv run python run_pipeline.py
```

### Run Individual Steps

```bash
# Step 1-2 only (no API key needed)
uv run python scraper.py

# Step 3 only (requires API key)
uv run python enrich_google.py

# Step 4 only (requires Step 3 output)
uv run python enrich_website.py
```

### Change Search Parameters

Edit `SEARCH_URL` in `scraper.py`:

```python
# Meditation retreats in Costa Rica
SEARCH_URL = "https://retreat.guru/search?topic=meditation&country=costa-rica"

# Wellness retreats in USA
SEARCH_URL = "https://retreat.guru/search?topic=wellness&country=usa"
```

---

## Limitations & Known Issues

### What retreat.guru Does NOT Expose

- Email addresses
- Phone numbers
- External website links
- Social media accounts

This is why we need the Google Places API and website scraping steps.

### Potential Issues

1. **Timeouts:** retreat.guru can be slow; script includes retry logic
2. **Rate limiting:** Be respectful; delays are built in
3. **Data accuracy:** Google Places may return wrong business for ambiguous queries
4. **Website changes:** CSS selectors may break if retreat.guru updates their site

### Cost Considerations

- **retreat.guru scraping:** Free
- **Google Places API:** ~$1-3 per batch of 50-100 leads
- **Website scraping:** Free

---

## Future Improvements

Potential enhancements:
1. Add more search result pages (pagination)
2. Implement proxy rotation for large-scale scraping
3. Add data validation and deduplication
4. Export to CRM formats (HubSpot, Salesforce)
5. Schedule automated runs with cron/Airflow
