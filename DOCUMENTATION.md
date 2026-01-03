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
1. Scrapes retreat listings from multiple platforms
2. Enriches with Google Places data (phone, website, coordinates)
3. Scrapes websites for email and social media
4. Appends to a master database with deduplication
5. **AI-powered lead analysis** (classification, profiles, outreach talking points)
6. **Calculates distance** to Surfbreak PXM using Haversine formula
7. Outputs prioritized, sales-ready lead list

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Supported Platforms](#supported-platforms)
3. [Complete Pipeline Flow](#complete-pipeline-flow)
4. [AI-Powered Lead Analysis](#ai-powered-lead-analysis)
5. [Distance Calculations](#distance-calculations)
6. [Lead Prioritization System](#lead-prioritization-system)
7. [Scripts & Components](#scripts--components)
8. [Input & Output Specifications](#input--output-specifications)
9. [Usage Guide](#usage-guide)
10. [Cost Analysis](#cost-analysis)
11. [Technical Implementation](#technical-implementation)

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
+-- scraper_bookretreats.py     # bookretreats.com scraper
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
```

### Script Details

#### `run_pipeline.py` - Main Orchestrator

**Purpose:** Single command to run the entire pipeline

**Features:**
- Auto-detects platform from URL
- CLI arguments for URL and label
- Handles missing API keys gracefully
- Runs AI enrichment if OPENAI_API_KEY is set
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
| **latitude** | GPS latitude | 23.4567 |
| **longitude** | GPS longitude | -110.2345 |
| **distance_to_surfbreak_miles** | Distance to Surfbreak PXM | 234.5 |
| source_url | Search URL used | https://retreat.guru/search?... |
| **ai_classification** | AI classification | FACILITATOR |
| **ai_confidence** | AI confidence (0-100) | 92 |
| **profile_summary** | AI-generated profile | "Sarah Chen is a yoga teacher..." |
| **website_analysis** | AI website insights | "Personal brand site, no venue..." |
| **outreach_talking_points** | AI talking points | "Reference her Ocean Flow retreat..." |
| **fit_reasoning** | AI fit analysis | "Excellent fit: traveling facilitator..." |
| **ai_red_flags** | AI concerns | "None identified" |
| **ai_green_flags** | AI positive signals | "Traveling facilitator; Active social..." |

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

| Metric | Value |
|--------|-------|
| Input tokens per lead | ~1,500 |
| Output tokens per lead | ~400 |
| Cost per lead | ~$0.002-0.003 |
| **100 leads** | **~$0.25** |
| **1,000 leads** | **~$2.50** |

**Note:** Cached results (30-day TTL) are free on re-runs.

### Time Costs

| Step | Duration (100 leads) |
|------|---------------------|
| Scraping | 5-10 minutes |
| Google enrichment | 1-2 minutes |
| Website scraping | 3-5 minutes |
| AI enrichment | 5-10 minutes |
| Analysis | < 1 second |
| **Total** | ~15-25 minutes |

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
