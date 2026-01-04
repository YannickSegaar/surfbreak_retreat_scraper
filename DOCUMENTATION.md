# Surfbreak Retreat Scraper - Complete Technical Documentation

## Executive Summary

This project is a **lead generation pipeline** specifically designed for Surfbreak PXM, a retreat venue in Puerto Escondido, Mexico. The system scrapes retreat listings from multiple platforms, enriches them with contact information, **uses AI to analyze and classify leads**, and calculates distances to your venue - delivering sales-ready lead profiles with personalized outreach recommendations.

### The Business Problem

Surfbreak wants to find retreat facilitators who might host their retreats at their venue. The challenge:
- Most retreat listings are from **venue owners** (competitors)
- The ideal prospects are **traveling facilitators** who rent spaces
- Contact information is not publicly available on retreat platforms
- Need to identify and prioritize the ~20% of leads that are actual prospects
- Sales team needs context and talking points for personalized outreach

### The Solution

A 7-step automated pipeline that:
1. Scrapes retreat listings from multiple platforms (with **auto-labeling** and **pagination**)
2. **Skips already-scraped retreats** (deduplication by event URL)
3. **AI-extracts enhanced data** (retreat descriptions, group sizes, guide profiles)
4. Enriches with Google Places data (phone, website, coordinates)
5. Scrapes websites for email and social media
6. Appends to a master database with cross-platform deduplication
7. **AI-powered lead analysis** (classification, profiles, outreach talking points)
8. **Calculates distance** to Surfbreak PXM using Haversine formula
9. Outputs prioritized, sales-ready lead list

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Features](#key-features)
3. [Supported Platforms](#supported-platforms)
4. [Complete Pipeline Flow](#complete-pipeline-flow)
5. [AI-Powered Lead Analysis](#ai-powered-lead-analysis)
6. [Distance Calculations](#distance-calculations)
7. [Lead Prioritization System](#lead-prioritization-system)
8. [Scripts & Components](#scripts--components)
9. [Input & Output Specifications](#input--output-specifications)
10. [Usage Guide](#usage-guide)
11. [Cost Analysis](#cost-analysis)
12. [Technical Implementation](#technical-implementation)

---

## Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                    SURFBREAK RETREAT LEAD GENERATION PIPELINE                      |
|                                                                                    |
|   "Find retreat facilitators who want to rent our venue, not venue owners"         |
+-----------------------------------------------------------------------------------+

                              +---------------------+
                              |   DATA SOURCES      |
                              +---------------------+
                              |  - retreat.guru     |
                              |  - bookretreats.com |
                              |  - (extensible)     |
                              +---------+-----------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              SCRAPING LAYER                                        |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  +---------------------+         +---------------------+                           |
|  |   scraper.py        |         | scraper_bookretreats|                           |
|  |   (retreat.guru)    |         |       .py           |                           |
|  |                     |         |                     |                           |
|  |  - Playwright       |         |  - Playwright       |                           |
|  |  - BeautifulSoup    |         |  - BeautifulSoup    |                           |
|  |  - JS-rendered      |         |  - HTML parsing     |                           |
|  +---------+-----------+         +---------+-----------+                           |
|            |                               |                                       |
|            +---------------+---------------+                                       |
|                            v                                                       |
|                   leads_enriched.csv                                               |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              ENRICHMENT LAYER                                      |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  +---------------------------------+    +---------------------------------+        |
|  |      enrich_google.py           |    |      enrich_website.py          |        |
|  |                                 |    |                                 |        |
|  |  Google Places API (New)        |--->|  Website Contact Scraping       |        |
|  |  - Phone numbers                |    |  - Email addresses              |        |
|  |  - Website URLs                 |    |  - Instagram, Facebook          |        |
|  |  - Google Maps links            |    |  - LinkedIn, Twitter            |        |
|  |  - Latitude/Longitude           |    |  - YouTube, TikTok              |        |
|  |  - Distance to Surfbreak        |    |                                 |        |
|  +---------------------------------+    +---------------------------------+        |
|                                                                                    |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              MASTER DATABASE                                       |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  leads_master.csv                                                                  |
|  +-- unique_id (SHA256 hash of organizer name)                                    |
|  +-- source_platform (retreat.guru / bookretreats.com)                            |
|  +-- source_label (user-defined batch label)                                      |
|  +-- All scraped fields...                                                        |
|  +-- All enriched fields...                                                       |
|  +-- latitude, longitude, distance_to_surfbreak_miles                             |
|                                                                                    |
|  KEY FEATURE: Same organizer on different platforms = SAME unique_id              |
|               Enables cross-platform duplicate detection!                          |
|                                                                                    |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              AI ENRICHMENT LAYER                                   |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  enrich_ai.py                                                                      |
|  +-- Website Deep Scraping (12+ pages per site)                                   |
|  |   - Homepage, About, Team, Services, Contact                                   |
|  |   - /venue, /accommodations (venue owner signals)                              |
|  |                                                                                 |
|  +-- OpenAI GPT-4o-mini Analysis                                                  |
|      - ai_classification: FACILITATOR / VENUE_OWNER / UNCLEAR                     |
|      - ai_confidence: 0-100 confidence score                                      |
|      - profile_summary: 2-3 sentence description                                  |
|      - website_analysis: Key insights from website                                |
|      - outreach_talking_points: 3 personalized conversation starters              |
|      - fit_reasoning: Why good/bad fit for Surfbreak                              |
|      - ai_red_flags: Concerns to watch for                                        |
|      - ai_green_flags: Positive signals                                           |
|                                                                                    |
|  30-day caching to avoid re-processing same organizers                            |
|                                                                                    |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              ANALYSIS LAYER                                        |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  analyze_leads.py                                                                  |
|  +-- Identifies TRAVELING FACILITATORS (host at multiple venues)                  |
|  +-- Detects VENUE OWNERS (competitors to avoid)                                  |
|  +-- Uses AI classification in scoring (+25 FACILITATOR, -30 VENUE_OWNER)         |
|  +-- Calculates PRIORITY SCORE (0-100)                                            |
|  +-- Outputs leads_analyzed.csv with recommendations                              |
|                                                                                    |
|  PRIORITY SCORING:                                                                 |
|  +--------------------------------------------------------------------+           |
|  |  +30 points: Traveling facilitator (multiple locations)            |           |
|  |  +25 points: AI classified as FACILITATOR (scaled by confidence)   |           |
|  |  +10 points: Multi-platform presence (on both sites)               |           |
|  |  +10 points: High activity (3+ retreats)                           |           |
|  |  -30 points: AI classified as VENUE_OWNER (scaled by confidence)   |           |
|  +--------------------------------------------------------------------+           |
|                                                                                    |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
                              +---------------------+
                              |  leads_analyzed.csv |
                              |                     |
                              |  READY FOR OUTREACH |
                              |  Sorted by priority |
                              |  With AI profiles   |
                              |  & talking points   |
                              +---------------------+
```

---

## Key Features

### Auto-Labeling from URL

**No more manual labels!** The system automatically generates labels and descriptions from URL parameters.

```bash
# Before: Required manual --label
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=mexico" --label "rg-yoga-mexico"

# After: Auto-generates label from URL
uv run python run_pipeline.py --url "https://retreat.guru/search?topic=yoga&country=mexico"
# Generates: label="rg-yoga-mexico", description="Retreats scraped from retreat.guru | Retreat Types: yoga | Locations: mexico"
```

**Complex URL handling:**
```
URL: https://retreat.guru/search?topic=yoga&topic=meditation&country=mexico&experiences_type=ayahuasca
Label: rg-yoga-meditation-mexico-ayahuasca
Description: Retreats scraped from retreat.guru | Retreat Types: yoga, meditation | Experiences: ayahuasca | Locations: mexico
```

**Implementation:** `url_parser.py`

### Deduplication (Skip Already-Scraped)

When running a new scrape, the pipeline automatically skips retreats that already exist in `leads_master.csv`.

**How it works:**
1. Load existing `event_url` values from master CSV
2. During scraping, compare each retreat URL against existing URLs
3. Skip if already scraped, continue if new
4. Report how many were skipped

**Output:**
```
✓ Found 127 existing retreats (will skip duplicates)
  Page 1: Found 50 retreats, skipping 23 already-scraped
  Page 2: Found 50 retreats, skipping 15 already-scraped
  Total new retreats to scrape: 62
```

### Enhanced Data Extraction (AI-Powered)

For each retreat page, the system now extracts additional data using GPT-4o-mini:

| Field | Description | Example |
|-------|-------------|---------|
| `retreat_description` | About this retreat (500 chars) | "Join us for a transformative 7-day yoga and meditation retreat in beautiful Tulum..." |
| `group_size` | Maximum participants | `12` |
| `guides_json` | JSON array of guide profiles | `[{"name": "Sarah Jones", "role": "Lead Instructor", "bio": "...", "guide_id": "abc123"}]` |

**Guide Profile Structure:**
```json
{
  "name": "Sarah Jones",
  "role": "Lead Yoga Instructor",
  "bio": "Sarah has been teaching yoga for 15 years...",
  "photo_url": "https://example.com/sarah.jpg",
  "profile_url": "/teachers/123/sarah-jones",
  "credentials": "RYT-500, E-RYT 200",
  "guide_id": "a1b2c3d4e5f6"
}
```

**Implementation:** `extract_with_ai.py`

**Cost:** ~$0.001 per retreat page (GPT-4o-mini)

### Pagination for BookRetreats

The BookRetreats scraper now supports full pagination:

- Automatically iterates through all search result pages
- Uses `pageNumber` parameter to navigate
- Stops when no more retreats found or page limit (20) reached
- Combines results from all pages before processing

**Output:**
```
Starting paginated scrape: https://bookretreats.com/s/yoga-retreats/mexico

  Page 1: Found 50 new retreat URLs
  Page 2: Found 50 new retreat URLs
  Page 3: Found 50 new retreat URLs
  Page 4: Found 32 new retreat URLs
  Page 5: No more retreats found

  Total unique retreat URLs to scrape: 182
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
- Two-phase scraping: search results -> center detail pages

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
- JSON-LD data with latitude/longitude

**Technical approach:**
- HTML parsing with fallback patterns
- Organizer extraction from profile links
- Location extracted from page elements or title

**Data available:**
- Retreat title, organizer name
- Location (often from title: "...in Tulum, Mexico")
- Price, rating
- Organizer profile URL
- Latitude/Longitude (from JSON-LD)

---

## Complete Pipeline Flow

### Step-by-Step Process

```
STEP 1: USER INITIATES SCRAPE
----------------------------------------------------------------------
Command:
  uv run python run_pipeline.py \
    --url "https://retreat.guru/search?topic=yoga&country=mexico" \
    --label "rg-yoga-mexico"

What happens:
  - Pipeline detects source platform from URL
  - Loads API keys from .env file (GOOGLE_PLACES_API_KEY, OPENAI_API_KEY)
  - Initializes headless browser (Chromium)


STEP 2: SCRAPE SEARCH RESULTS
----------------------------------------------------------------------
For retreat.guru:
  - Navigate to search URL
  - Wait for JavaScript to render (5 seconds)
  - Extract all retreat "tiles" using CSS selectors
  - Parse: title, organizer, location, dates, price, rating, URLs

For bookretreats.com:
  - Navigate to search URL
  - Scroll to load all content (handles lazy loading)
  - Extract retreat URLs from page
  - Visit each retreat page individually
  - Parse organizer from profile links

Output: List of RetreatLead objects


STEP 3: ENRICH WITH CENTER DATA (retreat.guru only)
----------------------------------------------------------------------
  - Collect unique center URLs from Step 2
  - Visit each center page
  - Extract detailed street address
  - Cache results (same center may have multiple retreats)

Purpose: Search results only show "Tulum, Mexico" but center pages
         have full addresses like "Carretera Tulum-Boca Paila Km 7.5"


STEP 4: GOOGLE PLACES API ENRICHMENT
----------------------------------------------------------------------
API: Google Places API (New) - Text Search

For each unique organizer:
  - Build search query: "{organizer} {address}"
  - Send API request to places.googleapis.com
  - Extract: phone, website, Google Maps URL, rating
  - Extract: latitude, longitude coordinates
  - Calculate: distance to Surfbreak PXM (Haversine formula)

Example request:
  POST https://places.googleapis.com/v1/places:searchText
  Body: {"textQuery": "Yandara Yoga Institute Todos Santos Mexico"}

Cost: ~$0.032 per request ($32 per 1,000)


STEP 5: WEBSITE CONTACT SCRAPING
----------------------------------------------------------------------
For each website found in Step 4:
  - Fetch homepage
  - Fetch common contact pages (/contact, /about, /contacto, etc.)
  - Extract emails using regex + mailto: links
  - Extract social media links (Instagram, Facebook, LinkedIn, etc.)

Filtering applied:
  - Skip noreply@, example.com, image files
  - Deduplicate social links
  - Limit to 3 emails per lead


STEP 6: APPEND TO MASTER DATABASE
----------------------------------------------------------------------
  - Generate unique_id: SHA256(organizer_name.lower())
  - Add metadata: source_platform, source_label, scrape_date
  - Append to leads_master.csv
  - Report duplicate detection (same organizer across sources)

Key insight: unique_id is based on organizer name ONLY, so:
  - "Casa Violeta" on retreat.guru -> hash abc123
  - "Casa Violeta" on bookretreats  -> hash abc123 (SAME!)
  This enables cross-platform deduplication.


STEP 7: AI-POWERED LEAD ANALYSIS (if OPENAI_API_KEY set)
----------------------------------------------------------------------
For each unique organizer:
  - Deep scrape their website (12+ pages)
  - Extract content from about, services, team, venue pages
  - Send to OpenAI GPT-4o-mini for analysis
  - Generate:
    - Classification (FACILITATOR / VENUE_OWNER / UNCLEAR)
    - Confidence score (0-100)
    - Profile summary (2-3 sentences)
    - Website analysis insights
    - 3 outreach talking points
    - Fit reasoning
    - Red/green flags

Caching: Results cached for 30 days to avoid re-processing


STEP 8: ANALYZE AND PRIORITIZE (run separately)
----------------------------------------------------------------------
Command: uv run python analyze_leads.py

Analysis performed:
  - Count retreats per organizer
  - Count unique locations per organizer
  - Count platforms per organizer
  - Use AI classification in scoring
  - Classify by name patterns (fallback)

Output:
  - priority_score (0-100)
  - lead_type (TRAVELING_FACILITATOR, FACILITATOR, VENUE_OWNER, UNKNOWN)
  - Sorted leads_analyzed.csv
```

---

## AI-Powered Lead Analysis

### Overview

The AI enrichment system (`enrich_ai.py`) provides deep analysis of each lead to help your sales team:
- **Understand who they are** with profile summaries
- **Know what to say** with personalized talking points
- **Prioritize effectively** with confidence-scored classification

### Website Deep Scraping

For each lead with a website, the system scrapes **12+ pages**:

```python
PAGES_TO_SCRAPE = [
    "/",              # Homepage
    "/about",         # About page
    "/about-us",
    "/our-story",
    "/team",          # Team info
    "/founder",
    "/services",      # What they offer
    "/retreats",
    "/offerings",
    "/venue",         # IMPORTANT: If exists, likely venue owner
    "/accommodations",# IMPORTANT: Room types = venue owner
    "/rooms",
    "/contact",
]
```

**Key Signal Detection:**
- `/venue` or `/accommodations` pages = strong venue owner indicator
- Personal brand focus (teachings, retreats) = facilitator indicator

### AI Classification Logic

The system uses GPT-4o-mini with specialized prompts to analyze:

**FACILITATOR Signals (Good Prospects):**
- Hosts at multiple different locations
- Personal brand (yoga teacher, wellness coach)
- No venue ownership mentions on website
- Website focuses on teachings, not accommodations
- Travel-focused language

**VENUE_OWNER Signals (Competitors - Skip):**
- Owns a specific property
- Website has room bookings, accommodation details
- Name includes "casa", "villa", "resort", "center"
- Fixed location focus
- /venue or /accommodations pages exist

### AI-Generated Fields

| Field | Description | Example |
|-------|-------------|---------|
| `ai_classification` | Primary classification | FACILITATOR |
| `ai_confidence` | Confidence level (0-100) | 92 |
| `profile_summary` | Who they are (2-3 sentences) | "Sarah Chen is a yoga teacher based in San Diego who leads vinyasa retreats across Mexico and Costa Rica. She has hosted at 4 different venues." |
| `website_analysis` | Key website insights | "Personal brand site focused on teacher trainings. No venue ownership signals. Mentions 'seeking ocean-view venues for 2025'." |
| `outreach_talking_points` | 3 conversation starters | "Reference her Ocean Flow retreat program; Ask about her 2025 retreat calendar; Offer a virtual tour of our ocean-view studios" |
| `fit_reasoning` | Why good/bad fit | "Excellent fit: traveling facilitator, seeks Mexico venues, hosts 3-4 retreats/year, focuses on vinyasa which aligns with our yoga shala." |
| `ai_red_flags` | Concerns | "None identified" |
| `ai_green_flags` | Positive signals | "Traveling facilitator; Seeks ocean venues; Active social presence; Premium retreat pricing" |

### Caching Strategy

- **Cache file:** `ai_enrichment_cache.json`
- **Cache key:** `unique_id` (organizer hash)
- **TTL:** 30 days
- **Benefit:** Re-running pipeline on same organizers uses cached results (no API cost)

---

## Distance Calculations

### Haversine Formula

The system calculates the great-circle distance from each retreat location to Surfbreak PXM using the Haversine formula:

```python
def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance in miles between two points."""
    R = 3959  # Earth's radius in miles

    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c
```

### Surfbreak PXM Reference Point

**Address:** Los Laureles, Nogales Tamarindos, Brisas de Zicatela, 70934 Puerto Escondido, Oax., Mexico

**Coordinates:** Configured in `enrich_google.py` as `SURFBREAK_LAT` and `SURFBREAK_LNG`

### Using Distance Data

The `distance_to_surfbreak_miles` field helps prioritize:
- **< 100 miles:** Very close, easy logistics
- **100-500 miles:** Regional, may drive
- **500-1000 miles:** Domestic Mexico, flights available
- **> 1000 miles:** International, require flights

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

    # AI CLASSIFICATION (if available)
    if has_ai_data:
        confidence_multiplier = ai_confidence / 100
        if ai_classification == "FACILITATOR":
            score += 25 * confidence_multiplier  # Up to +25
        elif ai_classification == "VENUE_OWNER":
            score -= 30 * confidence_multiplier  # Up to -30
    else:
        # Fallback to name-based heuristics
        if name_suggests_facilitator:
            score += 15
        elif name_suggests_venue:
            score -= 20

    # MULTI-PLATFORM: On both retreat.guru AND bookretreats
    if organizer.on_multiple_platforms:
        score += 10

    # HIGH ACTIVITY: 3+ retreats listed
    if organizer.retreat_count >= 3:
        score += 10
    elif organizer.retreat_count >= 2:
        score += 5

    return clamp(score, 0, 100)
```

### Lead Type Classification

| Type | Description | Priority | Action |
|------|-------------|----------|--------|
| **TRAVELING_FACILITATOR** | Hosts at 2+ different locations | Highest (80-100) | Contact immediately |
| **FACILITATOR** | AI confirms facilitator or name suggests | High (65-80) | Strong prospect |
| **UNKNOWN** | Can't determine from data | Medium (50-65) | Worth investigating |
| **VENUE_OWNER** | AI confirms or name suggests venue | Low (30-49) | Skip - competitor |

---

## Scripts & Components

### File Structure

```
surfbreak_retreat_scraper/
+-- .env                        # API keys (GOOGLE_PLACES_API_KEY, OPENAI_API_KEY)
+-- .gitignore                  # Excludes .env, CSVs, __pycache__
+-- pyproject.toml              # Dependencies (playwright, pandas, httpx, openai, etc.)
+-- uv.lock                     # Locked versions
|
+-- run_pipeline.py             # Main orchestrator (CLI interface)
+-- scraper.py                  # retreat.guru scraper
+-- scraper_bookretreats.py     # bookretreats.com scraper (with pagination)
+-- url_parser.py               # NEW: URL parsing & auto-label generation
+-- extract_with_ai.py          # NEW: AI extraction for descriptions/guides
+-- enrich_google.py            # Google Places API + distance calculations
+-- enrich_website.py           # Website contact scraping
+-- enrich_ai.py                # AI-powered lead analysis (OpenAI)
+-- analyze_leads.py            # Lead prioritization & scoring
|
+-- ai_enrichment_cache.json    # AI analysis cache (30-day TTL)
+-- leads_master.csv            # Master database (all scrapes appended)
+-- leads_analyzed.csv          # Prioritized output
|
+-- README.md                   # Quick start guide
+-- DOCUMENTATION.md            # This file
+-- CLIENT_GUIDE.md             # Non-technical client guide
```

### Script Details

#### `run_pipeline.py` - Main Orchestrator

**Purpose:** Single command to run the entire pipeline

**Features:**
- Auto-detects platform from URL
- **Auto-generates labels and descriptions** from URL parameters (--label is now optional)
- **Deduplicates** by skipping already-scraped event URLs
- Handles missing API keys gracefully
- Runs AI enrichment if OPENAI_API_KEY is set
- Cleans up intermediate files
- Reports statistics on completion

**Usage:**
```bash
# With auto-generated label (NEW! - label is optional)
uv run python run_pipeline.py \
  --url "https://retreat.guru/search?topic=yoga&country=mexico"

# With custom label (optional override)
uv run python run_pipeline.py \
  --url "https://retreat.guru/search?topic=yoga&country=mexico" \
  --label "custom-label"

# Complex URL with multiple filters
uv run python run_pipeline.py \
  --url "https://retreat.guru/search?topic=yoga&topic=meditation&country=mexico&experiences_type=ayahuasca"
```

#### `url_parser.py` - URL Parsing & Auto-Labeling

**Purpose:** Parse search URLs and generate labels/descriptions automatically

**Features:**
- Parses retreat.guru URL parameters (topic, country, experiences_type, etc.)
- Parses bookretreats.com URL parameters (scopes[type], scopes[location], etc.)
- Generates human-readable labels: `rg-yoga-mexico`, `br-meditation-costa-rica`
- Generates rich descriptions: `"Retreats scraped from retreat.guru | Retreat Types: yoga | Locations: mexico"`

**Usage:**
```python
from url_parser import parse_url, generate_label, generate_description

url_data = parse_url("https://retreat.guru/search?topic=yoga&country=mexico")
label = generate_label(url_data)  # "rg-yoga-mexico"
description = generate_description(url_data)  # "Retreats scraped from..."
```

#### `extract_with_ai.py` - AI-Powered Data Extraction

**Purpose:** Extract structured data from retreat pages using GPT-4o-mini

**Features:**
- Extracts retreat descriptions (500 chars max)
- Extracts group size (max participants)
- Extracts guide/facilitator profiles (name, role, bio, photo, credentials)
- HTML preprocessing to reduce token usage
- Platform-specific selectors for retreat.guru and bookretreats.com
- Guide ID generation for cross-retreat deduplication

**Usage:**
```python
from extract_with_ai import extract_retreat_details, enrich_guides_with_ids

details = await extract_retreat_details(html, openai_client, "retreat.guru")
# Returns:
# {
#   "description": "About this retreat...",
#   "group_size": 12,
#   "guides": [{"name": "...", "role": "...", "bio": "..."}]
# }

guides = enrich_guides_with_ids(details["guides"])
# Adds guide_id to each guide for deduplication
```

**Cost:** ~$0.001 per page with GPT-4o-mini

#### `enrich_ai.py` - AI-Powered Lead Analysis

**Purpose:** Deep analysis of leads using OpenAI GPT-4o-mini

**Key components:**
- `WebsiteContentExtractor` - Scrapes 12+ pages per website
- `AILeadAnalyzer` - Sends data to OpenAI, parses responses
- `AICache` - 30-day caching to avoid re-processing

**Usage:**
```bash
# Run AI enrichment on existing leads
uv run python -c "
import asyncio
from enrich_ai import enrich_leads_with_ai
asyncio.run(enrich_leads_with_ai('leads_master.csv', 'leads_master.csv'))
"
```

#### `enrich_google.py` - Google Places API + Distance

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
places.location  # For lat/lng and distance calculations
```

**Distance calculation:**
- Uses Haversine formula
- Reference point: Surfbreak PXM (Puerto Escondido)
- Output: `distance_to_surfbreak_miles`

#### `analyze_leads.py` - Lead Prioritization

**Input:** leads_master.csv
**Output:** leads_analyzed.csv

**Analysis performed:**
1. Group by unique_id (organizer)
2. Count retreats per organizer
3. Count unique locations per organizer
4. Detect multi-platform presence
5. Use AI classification (if available)
6. Classify by name patterns (fallback)
7. Calculate priority score
8. Assign lead type

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

All leads from all scrapes, with **43+ columns**:

**Identification & Source (7 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `unique_id` | SHA256 hash of organizer name (12 chars) | `a1b2c3d4e5f6` |
| `source_platform` | Which site it came from | `retreat.guru` |
| `source_label` | Auto-generated or custom batch label | `rg-yoga-mexico` |
| `scrape_date` | When scraped | `2024-12-26 17:43:22` |
| `scrape_description` | Rich text describing filters used | `Retreats scraped from retreat.guru \| Retreat Types: yoga \| Locations: mexico` |
| `source_url` | Search URL used | `https://retreat.guru/search?...` |
| `search_query` | Query sent to Google Places | `Yandara Yoga Todos Santos Mexico` |

**Organizer & Retreat Info (8 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `organizer` | Center/facilitator name | `Yandara Yoga Institute` |
| `title` | Retreat name | `28-day 300hr YTT` |
| `location_city` | Location | `Todos Santos, Mexico` |
| `detailed_address` | Full address | `Carretera 19, KM 74...` |
| `dates` | Event dates | `March 29 - April 26, 2026` |
| `price` | Price | `$4,000.00` |
| `rating` | Platform rating | `5 (1 review)` |
| `event_url` | Link to listing | `https://retreat.guru/events/...` |
| `center_url` | Link to organizer | `https://retreat.guru/centers/...` |

**Contact Info - Direct (7 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `phone` | Phone number | `+52 612 123 4567` |
| `email` | Email(s) found | `info@yandara.com` |
| `website` | Website URL | `https://yandara.com` |
| `instagram` | Instagram URL | `https://instagram.com/yandarayoga` |
| `facebook` | Facebook URL | `https://facebook.com/yandarayoga` |
| `linkedin` | LinkedIn URL | (if found) |
| `twitter` | Twitter URL | (if found) |
| `youtube` | YouTube URL | (if found) |
| `tiktok` | TikTok URL | (if found) |
| `host_email_scraped` | Email scraped from website | `contact@yandara.com` |

**Google Places Data (6 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `google_business_name` | Verified name | `Yandara Yoga Institute` |
| `google_address` | Verified address | `Todos Santos, BCS, Mexico` |
| `google_rating` | Google rating | `4.8` |
| `google_reviews` | Review count | `127` |
| `google_maps_url` | Google Maps link | `https://maps.google.com/?cid=...` |

**Location Data (2 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `latitude` | GPS latitude | `23.4567` |
| `longitude` | GPS longitude | `-110.2345` |

**Enhanced Retreat Data (3 columns - from AI extraction):**
| Column | Description | Example |
|--------|-------------|---------|
| `retreat_description` | About this retreat (500 chars max) | `"Join us for a transformative 7-day yoga retreat..."` |
| `group_size` | Maximum participants | `12` |
| `guides_json` | JSON array of guide profiles | `[{"name": "Sarah", "role": "Instructor", "guide_id": "abc123"}]` |

**AI Enrichment (8 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `ai_classification` | AI classification | `FACILITATOR` / `VENUE_OWNER` / `UNCLEAR` |
| `ai_confidence` | Confidence (0-100) | `92` |
| `profile_summary` | Who they are (2-3 sentences) | `"Sarah Chen is a yoga teacher based in SD..."` |
| `website_analysis` | Key website insights | `"Personal brand site, no venue ownership..."` |
| `outreach_talking_points` | 3 conversation starters (pipe-separated) | `"Reference Ocean Flow | Ask about 2025 | Offer tour"` |
| `fit_reasoning` | Why good/bad fit for Surfbreak | `"Excellent fit: traveling facilitator..."` |
| `ai_red_flags` | Concerns to watch | `"None identified"` |
| `ai_green_flags` | Positive signals | `"Traveling facilitator; Active social..."` |

#### `leads_analyzed.csv` - Prioritized Output

All 40 columns from master, **plus 7 analysis columns (47 total)**:

**Analysis & Scoring (7 columns):**
| Column | Description | Example |
|--------|-------------|---------|
| `priority_score` | 0-100 priority score | `85` |
| `lead_type` | Final classification | `TRAVELING_FACILITATOR` / `FACILITATOR` / `VENUE_OWNER` / `UNKNOWN` |
| `retreat_count` | Total retreats by organizer | `7` |
| `unique_locations` | Different venue locations | `3` |
| `is_traveling_facilitator` | Hosts at multiple locations | `True` / `False` |
| `is_multi_platform` | On both retreat.guru and bookretreats | `True` / `False` |
| `name_classification` | Heuristic name analysis | `likely_facilitator` / `likely_venue` / `unclear` |

---

## Airtable Integration

### Importing to Airtable

The `leads_analyzed.csv` file can be imported directly into Airtable. Use the prompt below with Airtable's AI assistant to set up the table structure before importing.

### Airtable Setup Prompt

Copy and paste this entire prompt into Airtable's AI assistant to create the table:

```
Create a table called "Surfbreak Leads" for tracking retreat facilitator prospects. This is a sales lead database for a retreat venue in Puerto Escondido, Mexico.

Create the following fields in this exact order:

=== IDENTIFICATION & SOURCE ===
1. unique_id - Single line text - Primary identifier (SHA256 hash of organizer name, 12 characters). Used to identify same organizer across platforms.
2. source_platform - Single select with options: "retreat.guru", "bookretreats.com" - Which website the lead was scraped from.
3. source_label - Single line text - User-defined batch label for this scrape run (e.g., "rg-yoga-mexico").
4. scrape_date - Date with time - When this lead was scraped.
5. source_url - URL - The search URL that was scraped.
6. search_query - Single line text - The query sent to Google Places API to find contact info.

=== ORGANIZER & RETREAT INFO ===
7. organizer - Single line text - Name of the retreat organizer, yoga teacher, or wellness center. This is the primary name field.
8. title - Single line text - Name of the specific retreat being offered.
9. location_city - Single line text - City and country where the retreat takes place.
10. detailed_address - Long text - Full street address of the retreat location.
11. dates - Single line text - When the retreat takes place.
12. price - Single line text - Price of the retreat.
13. rating - Single line text - Rating on the source platform.
14. event_url - URL - Direct link to the retreat listing page.
15. center_url - URL - Link to the organizer's profile page on the source platform.

=== CONTACT INFORMATION ===
16. phone - Phone number - Phone number from Google Places API.
17. email - Email - Primary email address found.
18. website - URL - Organizer's main website.
19. instagram - URL - Instagram profile link.
20. facebook - URL - Facebook page link.
21. linkedin - URL - LinkedIn profile link.
22. twitter - URL - Twitter/X profile link.
23. youtube - URL - YouTube channel link.
24. tiktok - URL - TikTok profile link.
25. host_email_scraped - Email - Additional email scraped from their website.

=== GOOGLE PLACES DATA ===
26. google_business_name - Single line text - Verified business name from Google.
27. google_address - Single line text - Verified address from Google.
28. google_rating - Number (decimal, 1 decimal place) - Google Maps rating (0-5 scale).
29. google_reviews - Number (integer) - Number of Google reviews.
30. google_maps_url - URL - Direct link to Google Maps listing.

=== LOCATION DATA ===
31. latitude - Number (decimal, 6 decimal places) - GPS latitude coordinate.
32. longitude - Number (decimal, 6 decimal places) - GPS longitude coordinate.

=== AI ANALYSIS ===
33. ai_classification - Single select with options: "FACILITATOR", "VENUE_OWNER", "UNCLEAR" - AI-determined classification. FACILITATOR = good prospect (rents venues). VENUE_OWNER = competitor (owns their venue). UNCLEAR = needs manual review.
34. ai_confidence - Number (integer, 0-100) - AI confidence level in the classification. Higher = more certain.
35. profile_summary - Long text - AI-generated 2-3 sentence description of who this organizer is and what they do.
36. website_analysis - Long text - AI-generated insights from analyzing their website content.
37. outreach_talking_points - Long text - AI-generated personalized conversation starters for sales outreach. Contains 3 talking points separated by " | ".
38. fit_reasoning - Long text - AI explanation of why this lead is or isn't a good fit for Surfbreak venue.
39. ai_red_flags - Long text - AI-identified concerns or warning signs about this lead.
40. ai_green_flags - Long text - AI-identified positive signals about this lead.

=== ANALYSIS & SCORING ===
41. priority_score - Number (integer, 0-100) - Overall priority score. Higher = better prospect. 70+ = contact immediately, 50-69 = worth reaching out, <50 = likely competitor.
42. lead_type - Single select with options: "TRAVELING_FACILITATOR", "FACILITATOR", "VENUE_OWNER", "UNKNOWN" - Final lead classification. TRAVELING_FACILITATOR is the best prospect type.
43. retreat_count - Number (integer) - How many retreats this organizer has listed.
44. unique_locations - Number (integer) - How many different locations this organizer hosts retreats at. More locations = traveling facilitator.
45. is_traveling_facilitator - Checkbox - True if organizer hosts at 2+ different locations.
46. is_multi_platform - Checkbox - True if organizer appears on both retreat.guru AND bookretreats.com.
47. name_classification - Single select with options: "likely_facilitator", "likely_venue", "unclear" - Heuristic classification based on organizer name patterns.

=== VIEWS TO CREATE ===

Create these views:
1. "All Leads" - Grid view showing all records, sorted by priority_score descending.
2. "High Priority (70+)" - Grid view filtered to priority_score >= 70, sorted by priority_score descending. These are the best prospects to contact first.
3. "Traveling Facilitators" - Grid view filtered to is_traveling_facilitator = true. These are the BEST prospects - they already rent venues.
4. "Facilitators" - Grid view filtered to lead_type = "FACILITATOR" or lead_type = "TRAVELING_FACILITATOR".
5. "Venue Owners (Skip)" - Grid view filtered to lead_type = "VENUE_OWNER". These are competitors, not prospects.
6. "Needs Review" - Grid view filtered to ai_classification = "UNCLEAR" or lead_type = "UNKNOWN".
7. "By Platform" - Grid view grouped by source_platform.

=== FIELD GROUPING (Optional) ===
Group fields into sections:
- "Identification" - unique_id through search_query
- "Organizer Info" - organizer through center_url
- "Contact" - phone through host_email_scraped
- "Google Data" - google_business_name through google_maps_url
- "Location" - latitude, longitude
- "AI Analysis" - ai_classification through ai_green_flags
- "Scoring" - priority_score through name_classification
```

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

# 4. Set up API keys
cat > .env << EOF
GOOGLE_PLACES_API_KEY=your-google-key-here
OPENAI_API_KEY=your-openai-key-here
EOF
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

### Running AI Enrichment Separately

```bash
# If you skipped AI during pipeline, run it separately
uv run python -c "
import asyncio
from enrich_ai import enrich_leads_with_ai
asyncio.run(enrich_leads_with_ai('leads_master.csv', 'leads_master.csv'))
"

# Then re-run analysis to use AI data in scoring
uv run python analyze_leads.py
```

### Recommended Workflow

1. **Scrape multiple sources** - More data = better analysis
2. **Scrape multiple countries** - Identifies traveling facilitators
3. **Run analysis** - Prioritizes leads
4. **Filter by priority_score >= 70** - Focus on best prospects
5. **Use AI talking points** - Personalize outreach
6. **Export high-priority leads to CRM** - Begin outreach

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

### OpenAI API Costs (GPT-4o-mini)

**AI Lead Analysis (`enrich_ai.py`):**
| Metric | Value |
|--------|-------|
| Input tokens per lead | ~1,500 |
| Output tokens per lead | ~400 |
| Cost per lead | ~$0.002-0.003 |
| **100 leads** | **~$0.25** |
| **1,000 leads** | **~$2.50** |

**Note:** Cached results (30-day TTL) are free on re-runs.

**AI Retreat Extraction (`extract_with_ai.py`):**
| Metric | Value |
|--------|-------|
| Input tokens per page | ~800 |
| Output tokens per page | ~200 |
| Cost per page | ~$0.001 |
| **100 retreat pages** | **~$0.10** |
| **1,000 retreat pages** | **~$1.00** |

**Total OpenAI Cost per 100 leads:** ~$0.35

### Time Costs

| Step | Duration (100 leads) |
|------|---------------------|
| Scraping + AI extraction | 10-15 minutes |
| Google enrichment | 1-2 minutes |
| Website scraping | 3-5 minutes |
| AI lead analysis | 5-10 minutes |
| Lead analysis | < 1 second |
| **Total** | ~20-30 minutes |

---

## Technical Implementation

### Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Browser automation | Playwright | Handles JavaScript-rendered pages |
| HTML parsing | BeautifulSoup + lxml | Fast, Pythonic |
| HTTP client | httpx | Async support, modern API |
| Data handling | pandas | Easy CSV operations |
| AI analysis | OpenAI GPT-4o-mini | Cost-effective, high quality |
| Package management | uv | Fast, reliable |
| Config | python-dotenv | Secure API key management |

### Error Handling

- **Page timeouts:** Retry with fallback wait strategies
- **Missing elements:** Return empty strings, continue
- **API errors:** Log and skip, don't crash
- **Empty files:** Handle gracefully, create output anyway
- **AI failures:** Fall back to heuristic classification

### Caching Strategy

**Google API and center scraping (in-memory):**
```python
# Same center appears in multiple retreats
self.scraped_centers: dict[str, dict] = {}

# Same organizer in multiple retreats
results_cache: dict[str, PlaceResult] = {}
```

**AI enrichment (persistent, 30-day TTL):**
```python
# Stored in ai_enrichment_cache.json
{
    "unique_id": {
        "timestamp": "2024-12-26T17:43:22",
        "data": { ... AI analysis results ... }
    }
}
```

Benefits:
- Reduces API costs
- Speeds up re-runs
- Prevents duplicate requests

---

## Appendix: Sample Analysis Output

```
======================================================================
LEAD ANALYSIS & PRIORITIZATION
======================================================================

Loaded 265 leads from leads_master.csv
AI enrichment data detected - using AI classification for scoring

--- AI Classification Summary ---
  Leads analyzed by AI: 126/126
  AI Classifications:
    FACILITATOR:  48 (38.1%)
    VENUE_OWNER:  62 (49.2%)
    UNCLEAR:      16 (12.7%)
  Average AI confidence: 78.5%

--- Lead Type Breakdown ---
  VENUE_OWNER: 62 (49.2%)
  FACILITATOR: 44 (34.9%)
  UNKNOWN: 16 (12.7%)
  TRAVELING_FACILITATOR: 4 (3.2%)

--- TRAVELING FACILITATORS (Best Prospects) ---
Found 4 organizers who host at multiple locations!

Top traveling facilitators:
  - Harmony Holistic Life: 13 retreats across 2 locations
  - Jojo: 9 retreats across 2 locations
  - Fitflowyoga: 7 retreats across 2 locations
  - Healing Retreat In The jungle: 2 retreats across 2 locations

--- MULTI-PLATFORM ORGANIZERS ---
Found 35 organizers on multiple platforms

--- PRIORITY SCORE DISTRIBUTION ---
  HIGH (70-100):   52 organizers - Contact first!
  MEDIUM (50-69):  54 organizers - Worth reaching out
  LOW (0-49):      20 organizers - Likely competitors

--- TOP 10 PROSPECTS ---
  1. Jojo (Score: 100)
     - 9 retreats, 2 locations
     - Type: TRAVELING_FACILITATOR
  2. Harmony Holistic Life (Score: 100)
     - 13 retreats, 2 locations
     - Type: TRAVELING_FACILITATOR
  3. Fitflowyoga (Score: 100)
     - 7 retreats, 2 locations
     - Type: TRAVELING_FACILITATOR
  4. Healing Retreat In The jungle (Score: 100)
     - 2 retreats, 2 locations
     - Type: TRAVELING_FACILITATOR
  5. Yoga with Elisha (Score: 85)
     - 2 retreats, 1 location
     - Type: FACILITATOR (AI: 92% confidence)
  ...

======================================================================
RECOMMENDATIONS
======================================================================

1. PRIORITIZE: Focus on leads with priority_score >= 70
   These are likely facilitators who rent venues

2. TRAVELING FACILITATORS: Your best prospects!
   They already host at multiple locations = open to new venues

3. USE AI TALKING POINTS: Check outreach_talking_points column
   Personalized conversation starters for each lead

4. AVOID: Leads marked as VENUE_OWNER (priority < 50)
   These are your competitors, not prospects

5. CONTACT STRATEGY:
   - Mention you saw their retreats on [platform]
   - Reference their specific programs (from profile_summary)
   - Highlight what makes your venue unique
   - Offer a site visit or virtual tour
   - Be specific about dates/availability

6. NEXT STEPS:
   - Filter leads_analyzed.csv by priority_score >= 70
   - Export high-priority leads to a CRM
   - Use profile_summary and outreach_talking_points for personalization

======================================================================
```
