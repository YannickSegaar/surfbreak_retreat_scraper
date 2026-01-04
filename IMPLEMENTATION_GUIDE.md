# Surfbreak Lead Generation - Implementation Guide

This guide covers setting up Airtable with a three-table structure for managing retreat leads, organizers, and guides.

---

## Table of Contents

1. [Three-Table Structure Overview](#three-table-structure-overview)
2. [Table 1: Retreats](#table-1-retreats)
3. [Table 2: Leads (Organizers)](#table-2-leads-organizers)
4. [Table 3: Guides](#table-3-guides)
5. [Quick Airtable Setup](#quick-airtable-setup)
6. [CSV Import Instructions](#csv-import-instructions)
7. [n8n Automation Setup](#n8n-automation-setup)

---

## Three-Table Structure Overview

The scraper outputs a flat CSV file, but for effective CRM usage, we recommend a three-table structure in Airtable:

```
+-------------------+       +-------------------+       +-------------------+
|     RETREATS      |       |       LEADS       |       |      GUIDES       |
+-------------------+       +-------------------+       +-------------------+
| retreat_id (PK)   |       | unique_id (PK)    |       | guide_id (PK)     |
| title             |       | organizer         |       | name              |
| dates             |       | phone             |       | role              |
| price             |       | email             |       | bio               |
| location_city     |       | website           |       | photo_url         |
| event_url         |       | instagram, etc.   |       | profile_url       |
| group_size        |       | ai_classification |       | credentials       |
| retreat_desc      |       | priority_score    |       +-------------------+
|                   |       | lead_type         |               |
| Lead (FK) ------->|       |<----------------- |               |
| Guides (FK) ------|-------|-------------------|-------------->|
+-------------------+       +-------------------+

```

**Benefits:**
- **One lead record per organizer** (even if they have 10 retreats)
- **Guide deduplication** (same guide across multiple retreats)
- **Better sales workflow** (focus on leads, not retreats)
- **Cleaner reporting** (count unique organizers, not retreat listings)

---

## Table 1: Retreats

Individual retreat listings from the scraped platforms.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `retreat_id` | Auto Number | Primary key |
| `title` | Single line text | Retreat name |
| `dates` | Single line text | Event dates |
| `price` | Single line text | Pricing |
| `location_city` | Single line text | City, Country |
| `event_url` | URL | Link to listing |
| `center_url` | URL | Link to organizer profile |
| `detailed_address` | Long text | Full address |
| `rating` | Single line text | Platform rating |
| `source_platform` | Single select | retreat.guru / bookretreats.com |
| `source_label` | Single line text | Scrape batch label |
| `scrape_description` | Long text | What filters were used |
| `scrape_date` | Date with time | When scraped |
| `retreat_description` | Long text | About this retreat (AI-extracted) |
| `group_size` | Number | Max participants |
| **Lead** | Link to Leads | → Links to organizer |
| **Guides** | Link to Guides | → Links to facilitators |

---

## Table 2: Leads (Organizers)

One record per unique organizer. This is your primary sales table.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `unique_id` | Single line text | SHA256 hash (12 chars) - PRIMARY IDENTIFIER |
| `organizer` | Single line text | Business/facilitator name |
| `phone` | Phone | Contact phone |
| `email` | Email | Primary email |
| `website` | URL | Main website |
| `instagram` | URL | Instagram profile |
| `facebook` | URL | Facebook page |
| `linkedin` | URL | LinkedIn profile |
| `twitter` | URL | Twitter/X profile |
| `youtube` | URL | YouTube channel |
| `tiktok` | URL | TikTok profile |

**Google Places Data:**
| Field | Type | Description |
|-------|------|-------------|
| `google_business_name` | Single line text | Verified name |
| `google_address` | Single line text | Verified address |
| `google_rating` | Number (decimal) | Google rating (0-5) |
| `google_reviews` | Number (integer) | Review count |
| `google_maps_url` | URL | Maps link |
| `latitude` | Number | GPS latitude |
| `longitude` | Number | GPS longitude |

**AI Analysis:**
| Field | Type | Description |
|-------|------|-------------|
| `ai_classification` | Single select | FACILITATOR / VENUE_OWNER / UNCLEAR |
| `ai_confidence` | Number (0-100) | Confidence level |
| `profile_summary` | Long text | Who they are (2-3 sentences) |
| `website_analysis` | Long text | Key website insights |
| `outreach_talking_points` | Long text | Conversation starters |
| `fit_reasoning` | Long text | Why good/bad fit |
| `ai_red_flags` | Long text | Concerns |
| `ai_green_flags` | Long text | Positive signals |

**Scoring:**
| Field | Type | Description |
|-------|------|-------------|
| `priority_score` | Number (0-100) | Overall priority |
| `lead_type` | Single select | TRAVELING_FACILITATOR / FACILITATOR / VENUE_OWNER / UNKNOWN |
| `retreat_count` | Number | Total retreats |
| `unique_locations` | Number | Different venues |
| `is_traveling_facilitator` | Checkbox | Hosts at 2+ locations |
| `is_multi_platform` | Checkbox | On multiple sites |

**Linked Records:**
| Field | Type | Description |
|-------|------|-------------|
| **Retreats** | Link to Retreats | All retreats by this organizer |

---

## Table 3: Guides

Individual guides/facilitators who lead retreats. Same guide may appear across multiple retreats.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `guide_id` | Single line text | SHA256 hash - PRIMARY IDENTIFIER |
| `name` | Single line text | Guide's full name |
| `role` | Single select | Guide / Facilitator / Instructor / Teacher / Host |
| `bio` | Long text | Biography (300 chars) |
| `photo_url` | URL | Profile photo |
| `profile_url` | URL | Link to profile page |
| `credentials` | Long text | Certifications, training |
| **Retreats** | Link to Retreats | All retreats they lead |

---

## Quick Airtable Setup

Copy and paste this prompt into Airtable's AI assistant to create all three tables:

```
Create three linked tables for a retreat lead generation system:

=== TABLE 1: Retreats ===
Create a table called "Retreats" with these fields:
1. retreat_id - Auto number
2. title - Single line text
3. dates - Single line text
4. price - Single line text
5. location_city - Single line text
6. event_url - URL
7. center_url - URL
8. detailed_address - Long text
9. rating - Single line text
10. source_platform - Single select (retreat.guru, bookretreats.com)
11. source_label - Single line text
12. scrape_description - Long text
13. scrape_date - Date with time
14. retreat_description - Long text
15. group_size - Number (integer)
16. Lead - Link to another record (will link to Leads table)
17. Guides - Link to another record (will link to Guides table, allow multiple)

=== TABLE 2: Leads ===
Create a table called "Leads" with these fields:
1. unique_id - Single line text (primary identifier)
2. organizer - Single line text (primary display field)
3. phone - Phone
4. email - Email
5. website - URL
6. instagram - URL
7. facebook - URL
8. linkedin - URL
9. twitter - URL
10. youtube - URL
11. tiktok - URL
12. google_business_name - Single line text
13. google_address - Single line text
14. google_rating - Number (decimal)
15. google_reviews - Number (integer)
16. google_maps_url - URL
17. latitude - Number (decimal, 6 places)
18. longitude - Number (decimal, 6 places)
19. ai_classification - Single select (FACILITATOR, VENUE_OWNER, UNCLEAR)
20. ai_confidence - Number (integer, 0-100)
21. profile_summary - Long text
22. website_analysis - Long text
23. outreach_talking_points - Long text
24. fit_reasoning - Long text
25. ai_red_flags - Long text
26. ai_green_flags - Long text
27. priority_score - Number (integer, 0-100)
28. lead_type - Single select (TRAVELING_FACILITATOR, FACILITATOR, VENUE_OWNER, UNKNOWN)
29. retreat_count - Number (integer)
30. unique_locations - Number (integer)
31. is_traveling_facilitator - Checkbox
32. is_multi_platform - Checkbox
33. Retreats - Link to Retreats table (reverse of Lead field)

=== TABLE 3: Guides ===
Create a table called "Guides" with these fields:
1. guide_id - Single line text (primary identifier)
2. name - Single line text (primary display field)
3. role - Single select (Guide, Facilitator, Instructor, Teacher, Host, Founder)
4. bio - Long text
5. photo_url - URL
6. profile_url - URL
7. credentials - Long text
8. Retreats - Link to Retreats table (reverse of Guides field)

=== VIEWS ===
Create these views in the Leads table:
1. "All Leads" - Grid view sorted by priority_score descending
2. "High Priority (70+)" - Filtered to priority_score >= 70
3. "Traveling Facilitators" - Filtered to is_traveling_facilitator = true
4. "Facilitators" - Filtered to lead_type = FACILITATOR or TRAVELING_FACILITATOR
5. "Venue Owners (Skip)" - Filtered to lead_type = VENUE_OWNER
6. "Needs Review" - Filtered to ai_classification = UNCLEAR
```

---

## CSV Import Instructions

The scraper outputs a flat CSV (`leads_master.csv` or `leads_analyzed.csv`). To use the three-table structure, you'll need to split this data.

### Option 1: Simple Import (Single Table)

If you don't need the three-table structure, import directly:

1. Open Airtable and create a new base
2. Import `leads_analyzed.csv`
3. Use the Airtable setup prompt from DOCUMENTATION.md

### Option 2: Manual Split

1. **Create Leads table first** - One row per unique `unique_id`
2. **Create Retreats table** - All rows from CSV
3. **Create Guides table** - Parse `guides_json` column, one row per unique `guide_id`
4. **Link records** - Match by `unique_id` (Leads) and `guide_id` (Guides)

### Option 3: n8n Automation (Recommended)

Use n8n to automatically split and link records. See next section.

---

## n8n Automation Setup

Use n8n to automate the CSV → Airtable three-table import.

### Workflow Overview

```
CSV File → Parse JSON → Split Data → Create/Update Airtable Records
                ↓
        +-----------------+
        |   For each row  |
        +-----------------+
                ↓
    +------------------------+
    | 1. Upsert Lead record  |
    |    (by unique_id)      |
    +------------------------+
                ↓
    +------------------------+
    | 2. Create Retreat      |
    |    (link to Lead)      |
    +------------------------+
                ↓
    +------------------------+
    | 3. Parse guides_json   |
    |    For each guide:     |
    |    - Upsert Guide      |
    |    - Link to Retreat   |
    +------------------------+
```

### Key n8n Nodes

1. **Read CSV File** - Load `leads_analyzed.csv`
2. **Set Node** - Transform data for Airtable
3. **Airtable Node (Leads)** - Upsert by `unique_id`
4. **Airtable Node (Retreats)** - Create and link to Lead
5. **Function Node** - Parse `guides_json`
6. **Airtable Node (Guides)** - Upsert by `guide_id`
7. **Airtable Node (Update Retreat)** - Add Guide links

### Sample n8n Expression for Parsing Guides

```javascript
// In a Function node after creating the Retreat
const retreat = $input.first().json;
const guidesJson = retreat.guides_json;

if (!guidesJson) {
  return [];
}

try {
  const guides = JSON.parse(guidesJson);
  return guides.map(guide => ({
    json: {
      guide_id: guide.guide_id,
      name: guide.name,
      role: guide.role,
      bio: guide.bio,
      photo_url: guide.photo_url,
      profile_url: guide.profile_url,
      credentials: guide.credentials,
      retreat_id: retreat.retreat_id  // For linking
    }
  }));
} catch (e) {
  return [];
}
```

### Airtable Upsert Configuration

For the Leads table, configure the Airtable node to:
- **Operation:** Update/Append
- **Match Field:** `unique_id`
- This ensures same organizer = same record (no duplicates)

For the Guides table:
- **Operation:** Update/Append
- **Match Field:** `guide_id`
- This ensures same guide = same record across retreats

---

## Summary

1. **Flat CSV** - What the scraper outputs
2. **Three-Table Structure** - Recommended for Airtable
3. **Linking Strategy**:
   - Retreats → Leads: by `unique_id`
   - Retreats → Guides: by `guide_id` (from `guides_json`)
4. **Automation** - Use n8n to handle the split and linking

For the simple approach, just import the CSV directly using the prompt in DOCUMENTATION.md.
