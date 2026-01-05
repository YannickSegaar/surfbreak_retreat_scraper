# Surfbreak Retreat Scraper - Complete Rebuild Specification

## Overview

This document provides complete instructions and prompts for rebuilding the Surfbreak Retreat Scraper from scratch using Claude Code with MCP servers.

---

## PROJECT SPECIFICATION PROMPT

Use this prompt when starting a new Claude Code conversation to rebuild the project:

---

### MASTER PROMPT: Surfbreak Retreat Lead Generation System

```
I need to build a comprehensive retreat lead generation system for Surfbreak PXM, a retreat venue in Puerto Escondido, Mexico. The goal is to identify traveling retreat facilitators (NOT venue owners) who might rent our space.

## BUSINESS CONTEXT

- Surfbreak PXM is a retreat venue that rents to traveling facilitators
- Most listings on retreat platforms are venue owners (competitors) - only ~20% are actual prospects
- We need to scrape retreat listings, enrich with contact data, and use AI to classify leads
- The system must deduplicate across platforms (same organizer on retreat.guru AND bookretreats.com = one lead)

## TECHNICAL REQUIREMENTS

### 1. MCP Servers Required
Set up .mcp.json with:
- Playwright MCP (@anthropic/mcp-playwright) - for browser automation and page analysis
- Airtable MCP (@domdomegg/airtable-mcp-server) - for CRM integration
- n8n MCP (n8n-mcp) - for workflow automation

### 2. Three-Table Output Structure

**Table 1: Retreat Centers (Main CRM - Organizers)**
- center_id: SHA256 hash of organizer name (for deduplication)
- organizer_name, phone, email, website
- Social media: instagram, facebook, linkedin, twitter, youtube, tiktok
- Google data: google_address, google_rating, google_reviews, latitude, longitude
- AI fields: ai_classification (FACILITATOR/VENUE_OWNER/UNCLEAR), ai_confidence, profile_summary
- Sales fields: priority_score, outreach_status, outreach_talking_points
- Links to: Retreat Events (one-to-many)

**Table 2: Retreat Events (Individual Listings)**
- event_id: unique per listing
- title, dates, price, location_city, event_url
- retreat_description, group_size, rating
- source_platform (retreat.guru / bookretreats.com), source_label, scrape_date
- Links to: Retreat Centers (many-to-one), Retreat Guides (many-to-many)

**Table 3: Retreat Guides (Facilitators)**
- guide_id: SHA256 hash of (name + profile_url) for deduplication
- name, role, bio, photo_url, profile_url, credentials
- Links to: Retreat Events (many-to-many)

### 3. Platform-Specific Scrapers

**retreat.guru Requirements:**
- Full JavaScript rendering (Playwright required)
- Search page selectors: article.search-event-tile
- Center pages: [data-cy='center-location'] for address
- Teacher links: a[href*='/teachers/'] for guide profiles
- Group size format: "Up to X in group"

**bookretreats.com Requirements:**
- Multi-page pagination with pageNumber parameter
- JSON-LD structured data extraction (primary method)
- Retreat URL pattern: /r/retreat-slug (exclude /r/s/ filter URLs)
- Organizer URL pattern: /organizers/o/...

### 4. Hierarchical Extraction Order

IMPORTANT: Extract data in this order to build relationships:

1. **First Pass - Retreat Centers**:
   - Extract organizer name, center URL from search results
   - Generate center_id = SHA256(organizer_name.lower())
   - Build unique center list

2. **Second Pass - Retreat Events**:
   - Scrape each event page
   - Link to center via center_id
   - Extract: title, dates, price, location, description, group_size

3. **Third Pass - Retreat Guides**:
   - Use AI extraction on event pages to find guides
   - Generate guide_id = SHA256(name + profile_url)
   - Deduplicate guides across events
   - Link guides to events

### 5. AI Extraction Requirements

**Stage 1: Page Data Extraction (GPT-4o-mini)**
Use Playwright to load each event page, then extract:
```json
{
  "description": "About this retreat (max 500 chars)",
  "group_size": 12,
  "guides": [
    {
      "name": "Guide Name",
      "role": "Lead Instructor",
      "bio": "Biography text",
      "photo_url": "https://...",
      "profile_url": "/teachers/123"
    }
  ]
}
```

Group size regex patterns (for preprocessing):
- r'(?:group|retreat)\s*size[:\s]+(\d+)'
- r'up\s+to\s+(\d+)\s+in\s+group'  # retreat.guru format
- r'(\d+)\s+in\s+group'
- r'capacity[:\s]+(\d+)'

**Stage 2: Deep Website Analysis (GPT-4o-mini)**
Scrape organizer websites (12+ pages: /, /about, /team, /venue, /rooms, /contact)
Classify as:
- FACILITATOR: No venue pages, focuses on retreats they lead
- VENUE_OWNER: Has /venue, /accommodations, /rooms pages
- UNCLEAR: Insufficient data

Output:
```json
{
  "ai_classification": "FACILITATOR|VENUE_OWNER|UNCLEAR",
  "ai_confidence": 85,
  "profile_summary": "2-3 sentence description",
  "outreach_talking_points": ["Point 1", "Point 2", "Point 3"],
  "ai_red_flags": "Concerns",
  "ai_green_flags": "Positive signals"
}
```

### 6. Deduplication Strategy

**Cross-Platform Deduplication:**
- Same organizer on both platforms = SAME center_id
- center_id = SHA256(organizer_name.lower().strip())[:12]
- Before scraping, load existing center_ids to skip duplicates

**Event Deduplication:**
- Skip events whose event_url already exists in database

**Guide Deduplication:**
- guide_id = SHA256(name.lower() + profile_url)[:12]
- Same guide teaching multiple retreats = ONE guide record linked to multiple events

### 7. API Integrations Required

**Google Places API (New):**
- Search by organizer name + location
- Extract: phone, website, address, coordinates, rating, reviews
- Calculate distance to Surfbreak (15.8614° N, 97.0722° W)

**OpenAI API:**
- GPT-4o-mini for HTML extraction (~$0.001/page)
- GPT-4o-mini for website analysis (~$0.005/organizer)

### 8. Priority Scoring

Calculate priority_score (0-100) based on:
- +30 if ai_classification = FACILITATOR
- +20 if has phone number
- +15 if has email
- +10 if has website
- +10 if near Puerto Escondido (<100 miles)
- +5 if has social media
- -20 if ai_classification = VENUE_OWNER

Flag as "TRAVELING_FACILITATOR" (best prospects) if:
- Classification = FACILITATOR with confidence > 70%
- OR multiple retreats at different locations
- OR no /venue pages on website

## WORKFLOW

1. User provides search URL(s) from retreat.guru or bookretreats.com
2. System auto-detects platform from URL
3. System auto-generates label from URL parameters (e.g., rg-yoga-mexico)
4. Use Playwright to analyze page structure
5. Extract all data following hierarchical order
6. Enrich with Google Places + website scraping
7. Run AI classification
8. Calculate priority scores
9. Output to three linked tables (CSV or Airtable)

## OUTPUT FORMAT

Produce three CSV files:
1. retreat_centers.csv - Main CRM table (one row per organizer)
2. retreat_events.csv - Event listings (links to centers via center_id)
3. retreat_guides.csv - Guide profiles (links to events via guide_id)

Or directly import to Airtable three-table structure with linked records.
```

---

## ENVIRONMENT SETUP

### Required .env File
```
GOOGLE_PLACES_API_KEY=your_google_places_api_key
OPENAI_API_KEY=your_openai_api_key
AIRTABLE_API_KEY=your_airtable_api_key
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_n8n_api_key
```

### Required .mcp.json File
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@anthropic/mcp-playwright"]
    },
    "airtable": {
      "command": "npx",
      "args": ["-y", "@domdomegg/airtable-mcp-server"],
      "env": {
        "AIRTABLE_API_KEY": "${AIRTABLE_API_KEY}"
      }
    },
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "N8N_API_URL": "${N8N_API_URL}",
        "N8N_API_KEY": "${N8N_API_KEY}"
      }
    }
  }
}
```

### Python Dependencies (pyproject.toml)
```toml
[project]
name = "surfbreak-retreat-scraper"
version = "2.0.0"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "pandas>=2.0.0",
    "httpx>=0.25.0",
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
]
```

---

## AIRTABLE TABLE PROMPTS

Use these prompts with Airtable AI to create the three tables:

### Prompt 1: Retreat Centers Table
```
Create a table called "Retreat Centers" for managing retreat organizer leads with these fields:

- center_id (Single line text) - Primary key, SHA256 hash
- organizer_name (Single line text) - Required
- phone (Phone number)
- email (Email)
- website (URL)
- instagram (URL)
- facebook (URL)
- linkedin (URL)
- twitter (URL)
- youtube (URL)
- tiktok (URL)
- google_address (Single line text)
- google_rating (Number, 1 decimal)
- google_reviews (Number)
- latitude (Number, 6 decimals)
- longitude (Number, 6 decimals)
- distance_to_surfbreak_miles (Number, 1 decimal)
- ai_classification (Single select: FACILITATOR, VENUE_OWNER, UNCLEAR)
- ai_confidence (Number, 0-100)
- profile_summary (Long text)
- website_analysis (Long text)
- outreach_talking_points (Long text)
- fit_reasoning (Long text)
- ai_red_flags (Long text)
- ai_green_flags (Long text)
- priority_score (Number, 0-100)
- lead_type (Single select: TRAVELING_FACILITATOR, VENUE_OWNER, UNKNOWN)
- outreach_status (Single select: NEW, CONTACTED, RESPONDED, MEETING_SCHEDULED, NOT_INTERESTED)
- notes (Long text)
- created_date (Created time)
- last_modified (Last modified time)
```

### Prompt 2: Retreat Events Table
```
Create a table called "Retreat Events" for tracking individual retreat listings with these fields:

- event_id (Single line text) - Primary key
- title (Single line text) - Required
- dates (Single line text)
- price (Single line text)
- location_city (Single line text)
- detailed_address (Long text)
- event_url (URL)
- retreat_description (Long text)
- group_size (Number)
- rating (Single line text)
- source_platform (Single select: retreat.guru, bookretreats.com)
- source_label (Single line text)
- scrape_date (Date)
- Center (Link to Retreat Centers table)
- Guides (Link to Retreat Guides table)
```

### Prompt 3: Retreat Guides Table
```
Create a table called "Retreat Guides" for tracking facilitators/instructors with these fields:

- guide_id (Single line text) - Primary key, SHA256 hash for deduplication
- name (Single line text) - Required
- role (Single select: Guide, Facilitator, Instructor, Teacher, Host, Lead)
- bio (Long text)
- photo_url (URL)
- profile_url (URL)
- credentials (Long text)
- Events (Link to Retreat Events table)
```

---

## KEY DIFFERENCES: retreat.guru vs bookretreats.com

| Aspect | retreat.guru | bookretreats.com |
|--------|--------------|------------------|
| **JS Rendering** | Required (heavy JS) | Light (mostly static) |
| **Pagination** | Single page scroll | pageNumber parameter |
| **Data Source** | HTML parsing | JSON-LD structured data |
| **Center Pages** | Separate URL to scrape | Organizer link in listing |
| **Group Size** | "Up to X in group" | Varies, often in JSON-LD |
| **Guide Links** | /teachers/ID/slug | /teacher/ID or in listing |
| **Address** | [data-cy='center-location'] | JSON-LD location object |
| **Coordinates** | Rarely available | Often in JSON-LD geo field |

---

## CRITICAL: PLATFORM-SPECIFIC EXTRACTION LOCATIONS

This section tells the AI agent **exactly where** to find each piece of data on each platform, and **what to avoid**.

### retreat.guru Page Structure

```
URL Pattern: https://retreat.guru/events/{id}-{num}/{slug}

PAGE LAYOUT (top to bottom):
┌─────────────────────────────────────────────────────────────┐
│ HEADER: Breadcrumb navigation (Health & Wellness > Location)│
├─────────────────────────────────────────────────────────────┤
│ HERO SECTION: Photo gallery (5+ images)                     │
├─────────────────────────────────────────────────────────────┤
│ TITLE SECTION:                                              │
│   - H1: Retreat title                                       │
│   - Location icon + "City, State, Country"                  │
│   - People icon + "Up to X in group"  ← GROUP SIZE HERE    │
│   - Calendar icon + "Date range"                            │
├─────────────────────────────────────────────────────────────┤
│ SIDEBAR (right): Booking widget                             │
│   - "SELECT YOUR OPTIONS"                                   │
│   - Available Dates                                         │
│   - Room types with prices                                  │
│   - "START MY BOOKING" button                               │
├─────────────────────────────────────────────────────────────┤
│ MAIN CONTENT (left):                                        │
│                                                             │
│   "Retreat Highlights" section ← DESCRIPTION STARTS HERE   │
│   - Bullet points of retreat features                       │
│                                                             │
│   "About This Retreat" section ← PRIMARY DESCRIPTION       │
│   - Main description paragraphs                             │
│   - This is the REAL description, NOT reviews               │
│                                                             │
│   "What's Included" section                                 │
│   - Accommodation, meals, activities                        │
│                                                             │
│   "Your Guides" section ← GUIDES/FACILITATORS HERE         │
│   - Guide cards with:                                       │
│     - Photo                                                 │
│     - Name (linked to /teachers/{id}/{slug})               │
│     - Role/title                                            │
│     - Bio text                                              │
│                                                             │
│   ⚠️ "Reviews" section ← AVOID THIS - CUSTOMER REVIEWS     │
│   - Star ratings                                            │
│   - Customer names                                          │
│   - Review text (NOT retreat description!)                  │
│                                                             │
│   "Location" section                                        │
│   - Map embed                                               │
│   - Address details                                         │
│                                                             │
│   "About [Center Name]" section                             │
│   - Center description (NOT retreat description)            │
│   - Link to center page                                     │
└─────────────────────────────────────────────────────────────┘
```

**retreat.guru CSS Selectors:**
| Data | Selector | Notes |
|------|----------|-------|
| Title | `h1` | First h1 on page |
| Group Size | Text containing "in group" near people icon | Pattern: "Up to X in group" |
| Description | `.retreat-highlights`, `[class*='about-retreat']` | AVOID `.reviews` section |
| Guides | `a[href*='/teachers/']` parent containers | Each guide links to /teachers/ |
| Guide Photo | `img` inside guide container | |
| Guide Name | `a[href*='/teachers/']` text | |
| Guide Bio | Text content after guide name | |
| Reviews (AVOID) | `[class*='review']`, `[class*='testimonial']` | DO NOT extract as description |
| Center Link | `a[href*='/centers/']` | Links to organizer page |

**retreat.guru AVOID List:**
- ❌ Customer reviews (contain star ratings, customer names)
- ❌ "About [Center Name]" section (that's the venue, not the retreat)
- ❌ Booking widget content (prices, room types)
- ❌ Similar retreats section at bottom
- ❌ Footer content

---

### bookretreats.com Page Structure

```
URL Pattern: https://bookretreats.com/r/{slug}-{id}

PAGE LAYOUT (top to bottom):
┌─────────────────────────────────────────────────────────────┐
│ HEADER: Navigation + Search bar                             │
├─────────────────────────────────────────────────────────────┤
│ HERO SECTION: Large photo + gallery thumbnails              │
├─────────────────────────────────────────────────────────────┤
│ TITLE BAR:                                                  │
│   - H1: Retreat title (often includes "X Day" + location)  │
│   - Star rating + review count                              │
│   - Location text                                           │
├─────────────────────────────────────────────────────────────┤
│ SIDEBAR (right): Booking/pricing panel                      │
│   - Price display                                           │
│   - Date selector                                           │
│   - "Check Availability" button                             │
├─────────────────────────────────────────────────────────────┤
│ TAB NAVIGATION: Overview | Itinerary | Accommodation | etc  │
├─────────────────────────────────────────────────────────────┤
│ MAIN CONTENT (varies by tab):                               │
│                                                             │
│   "Overview" tab ← PRIMARY DESCRIPTION HERE                │
│   - Main retreat description                                │
│   - "Highlights" bullet points                              │
│   - "What's included" list                                  │
│                                                             │
│   "Skill Level" or "Experience" info                        │
│   - Beginner/Intermediate/Advanced                          │
│                                                             │
│   "Group Size" indicator ← GROUP SIZE HERE                 │
│   - "Maximum X participants" or similar                     │
│                                                             │
│   "Meet Your Instructors/Hosts" ← GUIDES HERE              │
│   - Facilitator cards with:                                 │
│     - Photo                                                 │
│     - Name                                                  │
│     - Title/role                                            │
│     - Bio                                                   │
│                                                             │
│   "Organizer" section                                       │
│   - Link to organizer profile (/organizers/o/{slug})       │
│   - Organizer name                                          │
│                                                             │
│   ⚠️ "Reviews" section ← AVOID THIS - CUSTOMER REVIEWS     │
│   - "X Reviews" heading                                     │
│   - Individual review cards                                 │
│   - Reviewer names, dates, star ratings                     │
│                                                             │
│   "Location" section                                        │
│   - Map                                                     │
│   - Address                                                 │
└─────────────────────────────────────────────────────────────┘

ALSO CHECK: JSON-LD structured data in <script type="application/ld+json">
- Contains: name, description, offers.price, location, aggregateRating
- This is the MOST RELIABLE source for bookretreats.com
```

**bookretreats.com CSS Selectors:**
| Data | Selector | Notes |
|------|----------|-------|
| Title | `h1` | First h1, often includes location |
| Description | `[class*='overview']`, `[class*='description']` | Primary content section |
| Group Size | Text containing "participants", "group size" | Various formats |
| Guides | `[class*='instructor']`, `[class*='host']`, `[class*='facilitator']` | Look for team sections |
| Organizer | `a[href*='/organizers/']` | Link to organizer profile |
| JSON-LD | `script[type='application/ld+json']` | **Best data source** |
| Reviews (AVOID) | `[class*='review']`, sections with star icons + customer names | |

**bookretreats.com AVOID List:**
- ❌ Customer reviews (look for "Reviews" heading, star ratings, dates)
- ❌ "Similar Retreats" or "You might also like" sections
- ❌ Accommodation details (that's venue info, not retreat description)
- ❌ Footer content
- ❌ Sidebar booking widgets

---

## AI EXTRACTION PROMPT TEMPLATE (Improved)

Use this improved prompt that tells the AI exactly what to look for and avoid:

```
You are extracting structured data from a {PLATFORM} retreat listing page.

## PLATFORM: {PLATFORM}

{IF retreat.guru}
### WHERE TO FIND DATA:
- **DESCRIPTION**: Look in "Retreat Highlights" or "About This Retreat" sections
  - These appear BEFORE the reviews section
  - Usually contains bullet points or paragraphs about the retreat experience

- **GROUP SIZE**: Look for "Up to X in group" text near the title
  - Appears with a people/group icon
  - Format is always "Up to [NUMBER] in group"

- **GUIDES**: Look in "Your Guides" or "Meet Your Guides" section
  - Each guide has a link to /teachers/{id}/{slug}
  - Extract: name, role, bio, photo URL, profile URL

### WHAT TO AVOID (DO NOT EXTRACT):
- ❌ REVIEWS SECTION: Contains customer testimonials with:
  - Star ratings (★★★★★)
  - Customer names like "Sarah M." or "John D."
  - Dates like "Reviewed on January 2024"
  - Text starting with "I loved..." or "This retreat was..."

- ❌ "About [Center Name]" section - this describes the VENUE, not the retreat
- ❌ Booking widget content (prices, room options)
- ❌ "Similar Retreats" recommendations
{ENDIF}

{IF bookretreats.com}
### WHERE TO FIND DATA:
- **DESCRIPTION**: Look in "Overview" tab content
  - The main description paragraphs at top of content area
  - "Highlights" bullet points
  - PREFER JSON-LD data if available (most reliable)

- **GROUP SIZE**: Look for:
  - "Maximum X participants"
  - "Group size: X"
  - "Up to X guests"

- **GUIDES**: Look in "Meet Your Instructors" or "Your Hosts" section
  - Cards with photo, name, title, bio

- **JSON-LD DATA**: Check <script type="application/ld+json"> for structured data
  - This is the MOST RELIABLE source

### WHAT TO AVOID (DO NOT EXTRACT):
- ❌ REVIEWS SECTION: Contains customer feedback with:
  - "X Reviews" heading
  - Star ratings
  - Reviewer names and profile photos
  - Review dates
  - Text that sounds like personal experiences

- ❌ "Similar Retreats" or recommendations
- ❌ Accommodation/room descriptions (that's venue info)
- ❌ "About the Location" - geographical info, not retreat description
{ENDIF}

## HOW TO IDENTIFY REVIEWS VS DESCRIPTIONS:

REVIEWS typically have:
- Star ratings (★ symbols or 5-point scale)
- Personal pronouns: "I", "we", "my experience"
- Past tense: "was", "loved", "enjoyed", "had"
- Customer names: First name + Last initial, or full names
- Dates: "January 2024", "2 months ago"
- Phrases: "I would recommend", "My favorite part was"

DESCRIPTIONS typically have:
- Third person or imperative: "Join us", "Experience", "This retreat offers"
- Present/future tense: "includes", "will learn", "offers"
- No personal names (except facilitator names)
- No star ratings
- Structured information about the retreat itself

## EXTRACTION OUTPUT:
Return ONLY valid JSON:
{
  "description": "string (max 500 chars) or null - from About/Overview section ONLY",
  "group_size": number or null,
  "guides": [
    {
      "name": "Full Name",
      "role": "Their title/role",
      "bio": "Their bio (max 300 chars) or null",
      "photo_url": "URL or null",
      "profile_url": "URL or null",
      "credentials": "Certifications or null"
    }
  ]
}

HTML Content to analyze:
```

---

## HIERARCHICAL SCRAPING ORDER (Detailed)

**Step 1: Search Results Page**
```
FOR EACH platform:
  1. Load search URL with Playwright
  2. Wait for JavaScript rendering (retreat.guru needs longer)
  3. Extract list of:
     - Event URLs
     - Organizer names (preliminary)
     - Center/Organizer URLs
  4. Generate center_id for each unique organizer
  5. Check against existing center_ids for deduplication
```

**Step 2: Center/Organizer Pages (First)**
```
FOR EACH unique center_id:
  1. Navigate to center URL:
     - retreat.guru: /centers/{id}/{slug}
     - bookretreats: /organizers/o/{slug}
  2. Extract CENTER-level data:
     - Full organizer name
     - Contact info if visible
     - Center description (NOT retreat description)
     - Address (retreat.guru: [data-cy='center-location'])
  3. Save to retreat_centers table
```

**Step 3: Event Pages (Second)**
```
FOR EACH event URL:
  1. Navigate to event page
  2. Identify platform from URL
  3. Extract event data using platform-specific selectors:

     retreat.guru:
     - Title: h1
     - Group size: regex "Up to (\d+) in group"
     - Description: .retreat-highlights, [class*='about-retreat']
     - Dates: calendar section
     - Price: booking widget

     bookretreats.com:
     - FIRST: Check JSON-LD <script type="application/ld+json">
     - Title: h1 or JSON-LD name
     - Description: JSON-LD description or [class*='overview']
     - Group size: text search for "participants", "group size"
     - Price: JSON-LD offers.price or sidebar

  4. Link to center via center_id
  5. Save to retreat_events table
```

**Step 4: AI Extraction for Guides (Third)**
```
FOR EACH event (with AI enabled):
  1. Pass preprocessed HTML to GPT-4o-mini
  2. Use platform-specific prompt (see above)
  3. Extract guides array
  4. Generate guide_id for each guide
  5. Check for existing guide_id (deduplication)
  6. Save new guides to retreat_guides table
  7. Create event-guide links
```

---

## TESTING CHECKLIST

After building, test with these URLs:

**retreat.guru:**
- Search: https://retreat.guru/search?topic=yoga&country=mexico
- Event: https://retreat.guru/events/10839-45/5-day-somatic-healing-retreat-for-women-return-to-the-body
- Verify: Group size = 7 extracted correctly

**bookretreats.com:**
- Search: https://bookretreats.com/s/yoga-retreats/mexico
- Event: https://bookretreats.com/r/7-day-holistic-healing-retreat-in-paradise-yelapa-mexico-18174
- Verify: JSON-LD data extracted, pagination works

**Deduplication Test:**
- Run same search twice → should skip already-scraped events
- Same organizer on both platforms → same center_id

**AI Extraction Test:**
- Verify guides extracted with guide_id
- Verify descriptions captured
- Verify group sizes captured

### CRITICAL: Review vs Description Test

**How to verify you're NOT extracting reviews as descriptions:**

1. Check the extracted description for these RED FLAGS:
   - ❌ Contains "I" or "we" (personal pronouns)
   - ❌ Contains star ratings or "★"
   - ❌ Contains dates like "January 2024" or "last month"
   - ❌ Contains phrases like "I loved", "I would recommend", "My experience"
   - ❌ Contains names like "Sarah M." or "- John D."
   - ❌ Past tense focus: "was amazing", "enjoyed", "had a great time"

2. A CORRECT description should have:
   - ✅ Third person or imperative voice: "This retreat offers...", "Join us for..."
   - ✅ Present/future tense: "includes", "features", "you will experience"
   - ✅ Structured info about the retreat itself
   - ✅ No customer names (only facilitator names are OK)

**Test Script to Validate:**
```python
import re

def validate_description_not_review(description: str) -> dict:
    """Check if extracted description might actually be a review."""
    red_flags = []

    # Personal pronouns (review indicator)
    if re.search(r'\b(I|we|my|our)\b', description, re.IGNORECASE):
        red_flags.append("Contains personal pronouns (I/we/my)")

    # Past tense review phrases
    review_phrases = [
        r'\bI loved\b', r'\bI enjoyed\b', r'\bI would recommend\b',
        r'\bwas amazing\b', r'\bwas wonderful\b', r'\bhad a great\b',
        r'\bmy experience\b', r'\bmy favorite\b'
    ]
    for phrase in review_phrases:
        if re.search(phrase, description, re.IGNORECASE):
            red_flags.append(f"Contains review phrase: {phrase}")

    # Star ratings
    if '★' in description or re.search(r'\d/5|\d out of 5', description):
        red_flags.append("Contains star rating")

    # Review dates
    if re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', description):
        red_flags.append("Contains review date")

    # Customer name patterns (First L. or - Name)
    if re.search(r'- [A-Z][a-z]+ [A-Z]\.', description):
        red_flags.append("Contains customer name pattern")

    return {
        "is_likely_review": len(red_flags) > 0,
        "red_flags": red_flags,
        "confidence": "HIGH" if len(red_flags) >= 2 else "MEDIUM" if len(red_flags) == 1 else "LOW"
    }
```

---

## COST ESTIMATES

| Component | Cost per 100 leads |
|-----------|-------------------|
| Google Places API | ~$2-3 |
| OpenAI (page extraction) | ~$0.10 |
| OpenAI (website analysis) | ~$0.50 |
| **Total** | **~$3-4 per 100 leads** |

---

## FILES TO CREATE

1. **run_pipeline.py** - Main orchestrator with CLI args
2. **scraper_retreat_guru.py** - retreat.guru specific scraper
3. **scraper_bookretreats.py** - bookretreats.com specific scraper
4. **extract_with_ai.py** - GPT-4o-mini page extraction
5. **enrich_google.py** - Google Places API integration
6. **enrich_website.py** - Website scraping for contacts
7. **enrich_ai.py** - Deep website analysis + classification
8. **url_parser.py** - Auto-labeling from URLs
9. **analyze_leads.py** - Priority scoring + traveling facilitator detection
10. **models.py** - Data classes for RetreatCenter, RetreatEvent, RetreatGuide

---

This specification provides everything needed to rebuild the system from scratch with proper MCP integration, three-table structure, and hierarchical extraction.
