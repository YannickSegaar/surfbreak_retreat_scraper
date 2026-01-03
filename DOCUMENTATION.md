# Surfbreak Retreat Scraper - Complete Technical Documentation

## Executive Summary

This project is a **lead generation pipeline** specifically designed for Surfbreak, a retreat venue in Mexico seeking to attract retreat facilitators. The system scrapes retreat listings from multiple platforms, enriches them with contact information, and **intelligently prioritizes leads** to identify the best prospects - retreat organizers who are likely to want to rent venue space rather than venue owners who are competitors.

### The Business Problem

Surfbreak wants to find retreat facilitators who might host their retreats at their venue. The challenge:
- Most retreat listings are from **venue owners** (competitors)
- The ideal prospects are **traveling facilitators** who rent spaces
- Contact information is not publicly available on retreat platforms
- Need to identify and prioritize the ~20% of leads that are actual prospects

### The Solution

A 6-step automated pipeline that:
1. Scrapes retreat listings from multiple platforms
2. Enriches with Google Places data (phone, website)
3. Scrapes websites for email and social media
4. Appends to a master database with deduplication
5. **Analyzes and scores leads** to identify best prospects
6. Outputs prioritized lead list ready for outreach

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Supported Platforms](#supported-platforms)
3. [Complete Pipeline Flow](#complete-pipeline-flow)
4. [Data Collection Strategy](#data-collection-strategy)
5. [Lead Prioritization System](#lead-prioritization-system)
6. [Scripts & Components](#scripts--components)
7. [Input & Output Specifications](#input--output-specifications)
8. [Usage Guide](#usage-guide)
9. [Cost Analysis](#cost-analysis)
10. [Technical Implementation](#technical-implementation)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    SURFBREAK RETREAT LEAD GENERATION PIPELINE                        │
│                                                                                      │
│   "Find retreat facilitators who want to rent our venue, not venue owners"           │
└─────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────┐
                              │   DATA SOURCES      │
                              ├─────────────────────┤
                              │  • retreat.guru     │
                              │  • bookretreats.com │
                              │  • (extensible)     │
                              └──────────┬──────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SCRAPING LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────┐         ┌─────────────────────┐                            │
│  │   scraper.py        │         │ scraper_bookretreats│                            │
│  │   (retreat.guru)    │         │       .py           │                            │
│  │                     │         │                     │                            │
│  │  • Playwright       │         │  • Playwright       │                            │
│  │  • BeautifulSoup    │         │  • BeautifulSoup    │                            │
│  │  • JS-rendered      │         │  • HTML parsing     │                            │
│  └──────────┬──────────┘         └──────────┬──────────┘                            │
│             │                               │                                        │
│             └───────────────┬───────────────┘                                        │
│                             ▼                                                        │
│                   leads_enriched.csv                                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ENRICHMENT LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐         │
│  │      enrich_google.py           │    │      enrich_website.py          │         │
│  │                                 │    │                                 │         │
│  │  Google Places API (New)        │───▶│  Website Contact Scraping       │         │
│  │  • Phone numbers                │    │  • Email addresses              │         │
│  │  • Website URLs                 │    │  • Instagram, Facebook          │         │
│  │  • Google Maps links            │    │  • LinkedIn, Twitter            │         │
│  │  • Business verification        │    │  • YouTube, TikTok              │         │
│  └─────────────────────────────────┘    └─────────────────────────────────┘         │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MASTER DATABASE                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  leads_master.csv                                                                    │
│  ├── unique_id (SHA256 hash of organizer name)                                      │
│  ├── source_platform (retreat.guru / bookretreats.com)                              │
│  ├── source_label (user-defined batch label)                                        │
│  ├── All scraped fields...                                                          │
│  └── All enriched fields...                                                         │
│                                                                                      │
│  KEY FEATURE: Same organizer on different platforms = SAME unique_id                │
│               Enables cross-platform duplicate detection!                            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ANALYSIS LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  analyze_leads.py                                                                    │
│  ├── Identifies TRAVELING FACILITATORS (host at multiple venues)                    │
│  ├── Detects VENUE OWNERS (competitors to avoid)                                    │
│  ├── Calculates PRIORITY SCORE (0-100)                                              │
│  └── Outputs leads_analyzed.csv with recommendations                                │
│                                                                                      │
│  PRIORITY SCORING:                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐             │
│  │  +30 points: Traveling facilitator (multiple locations)            │             │
│  │  +15 points: Name suggests facilitator ("Yoga with...", etc.)      │             │
│  │  +10 points: Multi-platform presence (on both sites)               │             │
│  │  +10 points: High activity (3+ retreats)                           │             │
│  │  -20 points: Name suggests venue ("Resort", "Villa", "Center")     │             │
│  └────────────────────────────────────────────────────────────────────┘             │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  leads_analyzed.csv │
                              │                     │
                              │  READY FOR OUTREACH │
                              │  Sorted by priority │
                              └─────────────────────┘
```

---

## Supported Platforms

### 1. retreat.guru

**URL Pattern:** `https://retreat.guru/search?topic=yoga&country=mexico`

**Why this platform?**
- Largest retreat marketplace globally
- High-quality listings with verified organizers
- Detailed center pages with addresses

**Technical approach:**
- JavaScript-rendered (requires Playwright browser)
- CSS selectors for data extraction
- Two-phase scraping: search results → center detail pages

**Data available:**
- Retreat title, organizer name
- Location (city, country, street address)
- Dates, price, rating
- Event and center URLs

### 2. bookretreats.com

**URL Pattern:** `https://bookretreats.com/s/yoga-retreats/mexico`

**Why this platform?**
- Large selection of retreats
- Different organizer base than retreat.guru
- Good for cross-platform duplicate detection

**Technical approach:**
- HTML parsing with fallback patterns
- Organizer extraction from profile links
- Location extracted from page elements or title

**Data available:**
- Retreat title, organizer name
- Location (often from title: "...in Tulum, Mexico")
- Price, rating
- Organizer profile URL

---

## Complete Pipeline Flow

### Step-by-Step Process

```
STEP 1: USER INITIATES SCRAPE
──────────────────────────────────────────────────────────────────────────
Command:
  uv run python run_pipeline.py \
    --url "https://retreat.guru/search?topic=yoga&country=mexico" \
    --label "rg-yoga-mexico"

What happens:
  • Pipeline detects source platform from URL
  • Loads Google API key from .env file
  • Initializes headless browser (Chromium)


STEP 2: SCRAPE SEARCH RESULTS
──────────────────────────────────────────────────────────────────────────
For retreat.guru:
  • Navigate to search URL
  • Wait for JavaScript to render (5 seconds)
  • Extract all retreat "tiles" using CSS selectors
  • Parse: title, organizer, location, dates, price, rating, URLs

For bookretreats.com:
  • Navigate to search URL
  • Scroll to load all content (handles lazy loading)
  • Extract retreat URLs from page
  • Visit each retreat page individually
  • Parse organizer from profile links

Output: List of RetreatLead objects


STEP 3: ENRICH WITH CENTER DATA (retreat.guru only)
──────────────────────────────────────────────────────────────────────────
  • Collect unique center URLs from Step 2
  • Visit each center page
  • Extract detailed street address
  • Cache results (same center may have multiple retreats)

Purpose: Search results only show "Tulum, Mexico" but center pages
         have full addresses like "Carretera Tulum-Boca Paila Km 7.5"


STEP 4: GOOGLE PLACES API ENRICHMENT
──────────────────────────────────────────────────────────────────────────
API: Google Places API (New) - Text Search

For each unique organizer:
  • Build search query: "{organizer} {address}"
  • Send API request to places.googleapis.com
  • Extract: phone, website, Google Maps URL, rating

Example request:
  POST https://places.googleapis.com/v1/places:searchText
  Body: {"textQuery": "Yandara Yoga Institute Todos Santos Mexico"}

Cost: ~$0.032 per request ($32 per 1,000)


STEP 5: WEBSITE CONTACT SCRAPING
──────────────────────────────────────────────────────────────────────────
For each website found in Step 4:
  • Fetch homepage
  • Fetch common contact pages (/contact, /about, /contacto, etc.)
  • Extract emails using regex + mailto: links
  • Extract social media links (Instagram, Facebook, LinkedIn, etc.)

Filtering applied:
  • Skip noreply@, example.com, image files
  • Deduplicate social links
  • Limit to 3 emails per lead


STEP 6: APPEND TO MASTER DATABASE
──────────────────────────────────────────────────────────────────────────
  • Generate unique_id: SHA256(organizer_name.lower())
  • Add metadata: source_platform, source_label, scrape_date
  • Append to leads_master.csv
  • Report duplicate detection (same organizer across sources)

Key insight: unique_id is based on organizer name ONLY, so:
  • "Casa Violeta" on retreat.guru → hash abc123
  • "Casa Violeta" on bookretreats  → hash abc123 (SAME!)
  This enables cross-platform deduplication.


STEP 7: ANALYZE AND PRIORITIZE (run separately)
──────────────────────────────────────────────────────────────────────────
Command: uv run python analyze_leads.py

Analysis performed:
  • Count retreats per organizer
  • Count unique locations per organizer
  • Count platforms per organizer
  • Classify by name patterns

Output:
  • priority_score (0-100)
  • lead_type (TRAVELING_FACILITATOR, FACILITATOR, VENUE_OWNER, UNKNOWN)
  • Sorted leads_analyzed.csv
```

---

## Data Collection Strategy

### Why This Multi-Source Approach?

Retreat platforms like retreat.guru do **NOT** expose:
- Email addresses
- Phone numbers
- External website URLs
- Social media accounts

This is intentional - they want users to book through their platform.

**Our strategy bypasses this by:**

1. **Scraping what IS available:** organizer names, locations, retreat details
2. **Using Google Places API:** Search for the business to find phone/website
3. **Scraping the website:** Extract email and social media from their own site

### Data Quality Considerations

| Source | Reliability | Notes |
|--------|-------------|-------|
| Organizer name | High | Directly from listing |
| Location | Medium | May be city-only; center pages have full address |
| Phone | Medium | Google may return wrong business for ambiguous names |
| Website | Medium | Google match required |
| Email | High | Extracted directly from their website |
| Social media | High | Extracted directly from their website |

---

## Lead Prioritization System

### The Core Problem

**~70-80% of scraped leads are VENUE OWNERS** - these are Surfbreak's competitors, not prospects.

The ideal leads are **TRAVELING FACILITATORS** - yoga teachers, wellness coaches, meditation guides who:
- Lead retreats but don't own a venue
- Currently rent spaces from others
- Host retreats at multiple different locations

### Priority Scoring Algorithm

```python
def calculate_priority(organizer):
    score = 50  # Base score

    # TRAVELING FACILITATOR: They host at multiple locations
    # This is the STRONGEST signal - they rent venues!
    if organizer.hosts_at_multiple_locations:
        score += 30

    # MULTI-PLATFORM: On both retreat.guru AND bookretreats
    # Indicates professional operation, serious about business
    if organizer.on_multiple_platforms:
        score += 10

    # HIGH ACTIVITY: 3+ retreats listed
    # Proven track record, active in the market
    if organizer.retreat_count >= 3:
        score += 10
    elif organizer.retreat_count >= 2:
        score += 5

    # NAME SUGGESTS FACILITATOR
    # "Yoga with Sarah", "Transformational Journeys", etc.
    if name_suggests_facilitator(organizer.name):
        score += 15

    # NAME SUGGESTS VENUE OWNER (COMPETITOR)
    # "Casa...", "Resort...", "Villa...", "Center..."
    if name_suggests_venue(organizer.name):
        score -= 20

    return clamp(score, 0, 100)
```

### Lead Type Classification

| Type | Description | Priority | Action |
|------|-------------|----------|--------|
| **TRAVELING_FACILITATOR** | Hosts at 2+ different locations | Highest (80-100) | Contact immediately |
| **FACILITATOR** | Name suggests facilitator, not venue | High (65-80) | Strong prospect |
| **UNKNOWN** | Can't determine from data | Medium (50-65) | Worth investigating |
| **VENUE_OWNER** | Name suggests they own a venue | Low (30-49) | Skip - competitor |

### Keyword Detection

**Venue owner signals:**
- center, centre, resort, villa, casa, hacienda
- hotel, lodge, camp, sanctuary, ashram, temple
- retreat center, wellness center, eco, finca

**Facilitator signals:**
- yoga with, wellness by, retreats by
- school, academy, training, teacher, coach
- healing, transformation, journey

---

## Scripts & Components

### File Structure

```
surfbreak_retreat_scraper/
├── .env                        # API keys (GOOGLE_PLACES_API_KEY)
├── .gitignore                  # Excludes .env, CSVs, __pycache__
├── pyproject.toml              # Dependencies (playwright, pandas, httpx, etc.)
├── uv.lock                     # Locked versions
│
├── run_pipeline.py             # Main orchestrator (CLI interface)
├── scraper.py                  # retreat.guru scraper
├── scraper_bookretreats.py     # bookretreats.com scraper
├── enrich_google.py            # Google Places API enrichment
├── enrich_website.py           # Website contact scraping
├── analyze_leads.py            # Lead prioritization & scoring
│
├── leads_master.csv            # Master database (all scrapes appended)
├── leads_analyzed.csv          # Prioritized output
│
├── README.md                   # Quick start guide
└── DOCUMENTATION.md            # This file
```

### Script Details

#### `run_pipeline.py` - Main Orchestrator

**Purpose:** Single command to run the entire pipeline

**Features:**
- Auto-detects platform from URL
- CLI arguments for URL and label
- Handles missing API key gracefully
- Cleans up intermediate files
- Reports statistics on completion

**Usage:**
```bash
# retreat.guru
uv run python run_pipeline.py \
  --url "https://retreat.guru/search?topic=yoga&country=mexico" \
  --label "rg-yoga-mexico"

# bookretreats.com
uv run python run_pipeline.py \
  --url "https://bookretreats.com/s/yoga-retreats/mexico" \
  --label "br-yoga-mexico"
```

#### `scraper.py` - retreat.guru Scraper

**Key classes:**
- `RetreatLead` - Data class for a single lead
- `RetreatScraper` - Playwright-based scraper
- `ScraperStats` - Tracks success/error metrics

**CSS Selectors used:**
```python
article.search-event-tile      # Retreat card container
h2                             # Title
a[href*='/centers/']           # Center link
.search-event-tile__location   # Location
.search-event-tile__dates      # Dates
.search-event-tile__price      # Price
[data-cy='center-location']    # Detailed address (center page)
```

#### `scraper_bookretreats.py` - bookretreats.com Scraper

**Key differences from retreat.guru:**
- Visits each retreat page individually (no center pages)
- Extracts organizer from profile links: `a[href*='/organizers/o/']`
- Falls back to parsing location from title

#### `enrich_google.py` - Google Places API

**API endpoint:** `https://places.googleapis.com/v1/places:searchText`

**Fields requested:**
```
places.displayName
places.formattedAddress
places.internationalPhoneNumber
places.nationalPhoneNumber
places.websiteUri
places.googleMapsUri
places.rating
places.userRatingCount
```

#### `enrich_website.py` - Website Scraper

**Pages checked per website:**
```python
CONTACT_PAGE_PATHS = [
    "/contact", "/contact-us", "/contacto",
    "/about", "/about-us", "/connect", "/get-in-touch"
]
```

**Data extraction patterns:**
- Emails: Regex + mailto: links
- Social: Link href matching (instagram.com, facebook.com, etc.)

#### `analyze_leads.py` - Lead Prioritization

**Input:** leads_master.csv
**Output:** leads_analyzed.csv

**Analysis performed:**
1. Group by unique_id (organizer)
2. Count retreats per organizer
3. Count unique locations per organizer
4. Detect multi-platform presence
5. Classify by name patterns
6. Calculate priority score
7. Assign lead type

---

## Input & Output Specifications

### Pipeline Input

**Primary input:** Platform search URL + label

```bash
--url "https://retreat.guru/search?topic=yoga&country=mexico"
--label "rg-yoga-mexico"
```

**Supported URL patterns:**

| Platform | Pattern |
|----------|---------|
| retreat.guru | `https://retreat.guru/search?topic={topic}&country={country}` |
| bookretreats.com | `https://bookretreats.com/s/{type}-retreats/{location}` |

### Output Files

#### `leads_master.csv` - Master Database

All leads from all scrapes, with columns:

| Column | Description | Example |
|--------|-------------|---------|
| **unique_id** | SHA256 hash of organizer name | `a1b2c3d4e5f6` |
| **source_platform** | Which site it came from | `retreat.guru` |
| **source_label** | User-defined batch label | `rg-yoga-mexico` |
| **scrape_date** | When scraped | `2024-12-26 17:43:22` |
| organizer | Center/facilitator name | Yandara Yoga Institute |
| title | Retreat name | 28-day 300hr YTT |
| location_city | Location | Todos Santos, Mexico |
| detailed_address | Full address | Carretera 19, KM 74... |
| dates | Event dates | March 29 - April 26, 2026 |
| price | Price | $4,000.00 |
| rating | Platform rating | 5 (1 review) |
| phone | Phone number | +52 612 123 4567 |
| website | Website URL | https://yandara.com |
| email | Email(s) | info@yandara.com |
| instagram | Instagram URL | https://instagram.com/yandarayoga |
| facebook | Facebook URL | https://facebook.com/yandarayoga |
| linkedin | LinkedIn URL | (if found) |
| twitter | Twitter URL | (if found) |
| youtube | YouTube URL | (if found) |
| tiktok | TikTok URL | (if found) |
| event_url | Link to listing | https://retreat.guru/events/... |
| center_url | Link to organizer | https://retreat.guru/centers/... |
| google_maps_url | Google Maps link | https://maps.google.com/?cid=... |
| source_url | Search URL used | https://retreat.guru/search?... |

#### `leads_analyzed.csv` - Prioritized Output

All columns from master, plus:

| Column | Description | Example |
|--------|-------------|---------|
| **priority_score** | 0-100 score | `85` |
| **lead_type** | Classification | `TRAVELING_FACILITATOR` |
| retreat_count | Total retreats | `7` |
| unique_locations | Different venues | `3` |
| is_traveling_facilitator | Boolean | `True` |
| is_multi_platform | Boolean | `True` |
| name_classification | Name analysis | `likely_facilitator` |

---

## Usage Guide

### Initial Setup

```bash
# 1. Navigate to project
cd surfbreak_retreat_scraper

# 2. Install dependencies
uv sync

# 3. Install browser
uv run playwright install chromium

# 4. Set up API key
echo "GOOGLE_PLACES_API_KEY=your-key-here" > .env
```

### Running Scrapes

```bash
# Scrape retreat.guru - yoga in Mexico
uv run python run_pipeline.py \
  --url "https://retreat.guru/search?topic=yoga&country=mexico" \
  --label "rg-yoga-mexico"

# Scrape bookretreats.com - yoga in Mexico
uv run python run_pipeline.py \
  --url "https://bookretreats.com/s/yoga-retreats/mexico" \
  --label "br-yoga-mexico"

# Scrape more countries for cross-reference
uv run python run_pipeline.py \
  --url "https://retreat.guru/search?topic=yoga&country=costa-rica" \
  --label "rg-yoga-costa-rica"
```

### Analyzing Results

```bash
# Run analysis after scraping
uv run python analyze_leads.py
```

### Recommended Workflow

1. **Scrape multiple sources** - More data = better analysis
2. **Scrape multiple countries** - Identifies traveling facilitators
3. **Run analysis** - Prioritizes leads
4. **Filter by priority_score >= 70** - Focus on best prospects
5. **Export high-priority leads to CRM** - Begin outreach

---

## Cost Analysis

### Google Places API Costs

| Operation | Cost per 1,000 |
|-----------|----------------|
| Text Search | $32.00 |

**Typical batch:**
- 100 leads scraped
- ~60 unique organizers
- ~60 API calls
- Cost: ~$2.00

**Free tier:** $200/month credit from Google Cloud

### Time Costs

| Step | Duration (100 leads) |
|------|---------------------|
| Scraping | 5-10 minutes |
| Google enrichment | 1-2 minutes |
| Website scraping | 3-5 minutes |
| Analysis | < 1 second |
| **Total** | ~10-15 minutes |

---

## Technical Implementation

### Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Browser automation | Playwright | Handles JavaScript-rendered pages |
| HTML parsing | BeautifulSoup + lxml | Fast, Pythonic |
| HTTP client | httpx | Async support, modern API |
| Data handling | pandas | Easy CSV operations |
| Package management | uv | Fast, reliable |
| Config | python-dotenv | Secure API key management |

### Error Handling

- **Page timeouts:** Retry with fallback wait strategies
- **Missing elements:** Return empty strings, continue
- **API errors:** Log and skip, don't crash
- **Empty files:** Handle gracefully, create output anyway

### Caching Strategy

Both Google API and center scraping use in-memory caches:

```python
# Same center appears in multiple retreats
self.scraped_centers: dict[str, dict] = {}

# Same organizer in multiple retreats
results_cache: dict[str, PlaceResult] = {}
```

Benefits:
- Reduces API costs
- Speeds up scraping
- Prevents duplicate requests

---

## Appendix: Sample Analysis Output

```
======================================================================
LEAD ANALYSIS & PRIORITIZATION
======================================================================

Loaded 159 leads from leads_master.csv

--- Lead Type Breakdown ---
  UNKNOWN: 66 (75.0%)
  VENUE_OWNER: 12 (13.6%)
  FACILITATOR: 7 (8.0%)
  TRAVELING_FACILITATOR: 3 (3.4%)

--- TRAVELING FACILITATORS (Best Prospects) ---
Found 3 organizers who host at multiple locations!

Top traveling facilitators:
  - Harmony Holistic Life: 7 retreats across 2 locations
  - Jojo: 3 retreats across 2 locations
  - Healing Retreat In The jungle: 2 retreats across 2 locations

--- PRIORITY SCORE DISTRIBUTION ---
  HIGH (70-100):   9 organizers - Contact first!
  MEDIUM (50-69):  67 organizers - Worth reaching out
  LOW (0-49):      12 organizers - Likely competitors

--- TOP 10 PROSPECTS ---
  1. Healing Retreat In The jungle (Score: 100)
  2. Harmony Holistic Life (Score: 100)
  3. Jojo (Score: 90)
  4. Yoga with Elisha (Score: 80)
  5. Yandara Yoga Institute (Score: 70)
  ...
======================================================================
```
