# Airtable + n8n Integration Guide

This guide covers setting up a three-table Airtable structure with automated data import via n8n.

---

## Table of Contents

1. [Three-Table Architecture](#three-table-architecture)
2. [Airtable Setup Prompts](#airtable-setup-prompts)
3. [n8n Workflow Implementation](#n8n-workflow-implementation)
4. [Field Mappings](#field-mappings)

---

## Three-Table Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THREE-TABLE AIRTABLE STRUCTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   RETREAT EVENTS    │     │   RETREAT CENTERS   │     │   RETREAT GUIDES    │
│  (Individual Listings)│    │    (Organizers)     │     │   (Facilitators)    │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ event_id (PK)       │     │ center_id (PK)      │     │ guide_id (PK)       │
│ title               │     │ organizer_name      │     │ name                │
│ dates               │     │ phone               │     │ role                │
│ price               │     │ email               │     │ bio                 │
│ location_city       │     │ website             │     │ photo_url           │
│ event_url           │     │ social_media        │     │ profile_url         │
│ retreat_description │     │ ai_classification   │     │ credentials         │
│ group_size          │     │ priority_score      │     │                     │
│ source_platform     │     │ lead_type           │     │                     │
│ scrape_date         │     │ outreach_status     │     │                     │
│                     │     │                     │     │                     │
│ Center ─────────────┼────►│◄────────────────────┼─────┤ Events              │
│ Guides ─────────────┼─────┼─────────────────────┼────►│◄── Events           │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
         │                           │                           │
         │  One event belongs        │  One center has          │  One guide leads
         │  to ONE center            │  MANY events             │  MANY events
         │                           │                           │
         │  One event has            │  One center has          │  One guide works
         │  MANY guides              │  MANY guides             │  with MANY centers
         └───────────────────────────┴───────────────────────────┘

RELATIONSHIPS:
- Events → Centers: Many-to-One (each event belongs to one organizer)
- Events → Guides: Many-to-Many (events have multiple guides, guides lead multiple events)
- Centers → Guides: Many-to-Many (derived through events)
```

### Why Three Tables?

| Benefit | Description |
|---------|-------------|
| **No duplicate organizers** | One record per organizer, even if they have 10 retreats |
| **Guide deduplication** | Same guide across multiple retreats = one record |
| **Better sales workflow** | Focus on Centers (leads), not individual events |
| **Cleaner reporting** | Count unique organizers, not retreat listings |
| **Linked records** | Click a center to see all their events and guides |

---

## Airtable Setup Prompts

### Prompt 1: Retreat Events Table

Copy and paste this into Airtable's AI assistant:

```
Create a table called "Retreat Events" for tracking individual retreat listings scraped from booking platforms.

TABLE DESCRIPTION:
Individual retreat listings scraped from retreat.guru and bookretreats.com. Each row represents a single retreat event. Multiple events may belong to the same organizer (linked via the Center field). This table stores event-specific details like dates, pricing, and descriptions.

FIELDS TO CREATE:

1. event_id (Single line text) - Primary identifier, auto-generated hash
2. title (Single line text) - Name of the retreat event
3. dates (Single line text) - When the retreat runs
4. price (Single line text) - Pricing information
5. location_city (Single line text) - City and country where held
6. detailed_address (Long text) - Full street address if available
7. event_url (URL) - Direct link to the retreat listing
8. center_url (URL) - Link to the organizer's profile page
9. retreat_description (Long text) - About this specific retreat (AI-extracted)
10. group_size (Number, integer) - Maximum number of participants
11. rating (Single line text) - Platform rating and reviews
12. source_platform (Single select) - Options: retreat.guru, bookretreats.com
13. source_label (Single line text) - Scrape batch identifier (e.g., "rg-yoga-mexico")
14. scrape_description (Long text) - Description of search filters used
15. scrape_date (Date with time) - When this event was scraped
16. source_url (URL) - The search URL used to find this event
17. Center (Link to another record) - Links to "Retreat Centers" table
18. Guides (Link to another record) - Links to "Retreat Guides" table, allow multiple selections

VIEWS TO CREATE:
1. "All Events" - Grid view showing all events
2. "By Center" - Grouped by the linked Center field
3. "By Platform" - Grouped by source_platform
4. "Recent Scrapes" - Sorted by scrape_date descending
```

---

### Prompt 2: Retreat Centers Table

Copy and paste this into Airtable's AI assistant:

```
Create a table called "Retreat Centers" for tracking unique retreat organizers/facilitators as sales leads.

TABLE DESCRIPTION:
Unique retreat organizers and facilitators - your primary sales leads. Each row represents one organizer, regardless of how many retreats they have listed. This is your main CRM table for tracking outreach and managing the sales pipeline. Includes AI-generated classifications, contact information, and priority scores.

FIELDS TO CREATE:

IDENTIFICATION:
1. center_id (Single line text) - Primary identifier (unique_id from CSV)
2. organizer_name (Single line text) - Business or facilitator name (PRIMARY DISPLAY FIELD)

CONTACT INFORMATION:
3. phone (Phone) - Business phone number
4. email (Email) - Primary contact email
5. website (URL) - Main website
6. instagram (URL) - Instagram profile
7. facebook (URL) - Facebook page
8. linkedin (URL) - LinkedIn profile
9. twitter (URL) - Twitter/X profile
10. youtube (URL) - YouTube channel
11. tiktok (URL) - TikTok profile

GOOGLE PLACES DATA:
12. google_business_name (Single line text) - Verified business name from Google
13. google_address (Single line text) - Verified address from Google
14. google_rating (Number, decimal, 1 decimal place) - Google rating (0-5)
15. google_reviews (Number, integer) - Number of Google reviews
16. google_maps_url (URL) - Link to Google Maps listing
17. latitude (Number, decimal, 6 decimal places) - GPS latitude
18. longitude (Number, decimal, 6 decimal places) - GPS longitude
19. distance_to_surfbreak_miles (Number, decimal, 1 decimal place) - Distance from Surfbreak PXM

AI ANALYSIS:
20. ai_classification (Single select) - Options: FACILITATOR, VENUE_OWNER, UNCLEAR
21. ai_confidence (Number, integer) - AI confidence level 0-100
22. profile_summary (Long text) - 2-3 sentence description of who they are
23. website_analysis (Long text) - Key insights from their website
24. outreach_talking_points (Long text) - 3 personalized conversation starters
25. fit_reasoning (Long text) - Why they're a good/bad fit for Surfbreak
26. ai_red_flags (Long text) - Concerns or warning signs
27. ai_green_flags (Long text) - Positive indicators

SCORING & CLASSIFICATION:
28. priority_score (Number, integer) - Overall priority 0-100 (higher = better prospect)
29. lead_type (Single select) - Options: TRAVELING_FACILITATOR, FACILITATOR, VENUE_OWNER, UNKNOWN
30. retreat_count (Number, integer) - Total retreats by this organizer
31. unique_locations (Number, integer) - Number of different venues used
32. is_traveling_facilitator (Checkbox) - TRUE if hosts at 2+ locations
33. is_multi_platform (Checkbox) - TRUE if on multiple booking sites

SALES TRACKING:
34. outreach_status (Single select) - Options: Not Started, Researching, Ready to Contact, Contacted - Email, Contacted - DM, Contacted - Phone, Follow-up Needed, In Conversation, Call Scheduled, Tour Scheduled, Proposal Sent, Negotiating, Won - Booked, Lost - Not Interested, Lost - Wrong Fit, Lost - No Response
35. contact_priority (Single select) - Options: Hot, Warm, Cold, Do Not Contact
36. first_contact_date (Date) - When first outreach was made
37. last_contact_date (Date) - Most recent contact
38. next_follow_up_date (Date) - When to follow up
39. notes (Long text) - General notes about this lead
40. contact_log (Long text) - Log of all contact attempts

LINKED RECORDS:
41. Events (Link to "Retreat Events" table) - All events by this organizer

VIEWS TO CREATE:
1. "All Centers" - Grid sorted by priority_score descending
2. "High Priority (70+)" - Filter: priority_score >= 70
3. "Traveling Facilitators" - Filter: is_traveling_facilitator = TRUE
4. "Facilitators Only" - Filter: lead_type = FACILITATOR OR lead_type = TRAVELING_FACILITATOR
5. "Venue Owners (Skip)" - Filter: lead_type = VENUE_OWNER
6. "Needs Review" - Filter: ai_classification = UNCLEAR
7. "To Contact Today" - Filter: outreach_status = Ready to Contact
8. "Awaiting Response" - Filter: outreach_status = Follow-up Needed
9. "In Pipeline" - Filter: outreach_status contains "Conversation" OR "Scheduled" OR "Proposal" OR "Negotiating"
```

---

### Prompt 3: Retreat Guides Table

Copy and paste this into Airtable's AI assistant:

```
Create a table called "Retreat Guides" for tracking individual facilitators and instructors who lead retreats.

TABLE DESCRIPTION:
Individual guides, facilitators, and instructors who lead retreat events. The same guide may appear across multiple retreats and multiple organizers. This table enables tracking of specific teachers and understanding team compositions. Guide data is extracted via AI from retreat pages.

FIELDS TO CREATE:

1. guide_id (Single line text) - Primary identifier (SHA256 hash)
2. name (Single line text) - Guide's full name (PRIMARY DISPLAY FIELD)
3. role (Single select) - Options: Guide, Facilitator, Instructor, Teacher, Host, Founder, Co-Founder, Lead Teacher, Assistant Teacher, Guest Teacher
4. bio (Long text) - Biography and background (up to 500 characters)
5. photo_url (URL) - Link to their profile photo
6. profile_url (URL) - Link to their profile page on the platform
7. credentials (Long text) - Certifications, training, qualifications
8. Events (Link to "Retreat Events" table) - All events they lead, allow multiple selections

VIEWS TO CREATE:
1. "All Guides" - Grid view showing all guides sorted alphabetically
2. "By Role" - Grouped by role field
3. "Most Active" - Sorted by count of linked Events (descending)
```

---

## n8n Workflow Implementation

### Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         n8n WORKFLOW: CSV TO AIRTABLE                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────────────┐
│  1. TRIGGER  │───►│  2. READ CSV │───►│  3. PROCESS EACH ROW                 │
│  Manual/     │    │  leads_      │    │                                      │
│  Schedule    │    │  analyzed.csv│    │  ┌─────────────────────────────────┐ │
└──────────────┘    └──────────────┘    │  │ 3a. Upsert Center Record        │ │
                                        │  │     (by center_id = unique_id)  │ │
                                        │  │     → Returns Airtable record ID│ │
                                        │  └─────────────┬───────────────────┘ │
                                        │                │                     │
                                        │  ┌─────────────▼───────────────────┐ │
                                        │  │ 3b. Create Event Record         │ │
                                        │  │     (link to Center)            │ │
                                        │  │     → Returns Airtable record ID│ │
                                        │  └─────────────┬───────────────────┘ │
                                        │                │                     │
                                        │  ┌─────────────▼───────────────────┐ │
                                        │  │ 3c. Parse guides_json           │ │
                                        │  │     For each guide:             │ │
                                        │  │     - Upsert Guide (by guide_id)│ │
                                        │  │     - Link to Event             │ │
                                        │  └─────────────────────────────────┘ │
                                        └──────────────────────────────────────┘
```

### Complete n8n Workflow JSON

Import this JSON into n8n to create the workflow:

```json
{
  "name": "Surfbreak CSV to Airtable",
  "nodes": [
    {
      "parameters": {},
      "id": "trigger",
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [240, 300]
    },
    {
      "parameters": {
        "filePath": "/path/to/leads_analyzed.csv",
        "options": {}
      },
      "id": "read_csv",
      "name": "Read CSV",
      "type": "n8n-nodes-base.readBinaryFiles",
      "typeVersion": 1,
      "position": [460, 300]
    },
    {
      "parameters": {
        "operation": "toJson",
        "options": {}
      },
      "id": "parse_csv",
      "name": "Parse CSV",
      "type": "n8n-nodes-base.spreadsheetFile",
      "typeVersion": 1,
      "position": [680, 300]
    },
    {
      "parameters": {
        "jsCode": "// Process each row and prepare for Airtable\nconst items = $input.all();\nconst output = [];\n\nfor (const item of items) {\n  const row = item.json;\n  \n  // Parse guides_json if it exists\n  let guides = [];\n  if (row.guides_json && row.guides_json !== '') {\n    try {\n      guides = JSON.parse(row.guides_json);\n    } catch (e) {\n      guides = [];\n    }\n  }\n  \n  output.push({\n    json: {\n      // Center data (for upsert)\n      center_id: row.unique_id || '',\n      organizer_name: row.organizer || '',\n      phone: row.phone || '',\n      email: row.email || '',\n      website: row.website || '',\n      instagram: row.instagram || '',\n      facebook: row.facebook || '',\n      linkedin: row.linkedin || '',\n      twitter: row.twitter || '',\n      youtube: row.youtube || '',\n      tiktok: row.tiktok || '',\n      google_business_name: row.google_business_name || '',\n      google_address: row.google_address || '',\n      google_rating: parseFloat(row.google_rating) || null,\n      google_reviews: parseInt(row.google_reviews) || null,\n      google_maps_url: row.google_maps_url || '',\n      latitude: parseFloat(row.latitude) || null,\n      longitude: parseFloat(row.longitude) || null,\n      distance_to_surfbreak_miles: parseFloat(row.distance_to_surfbreak_miles) || null,\n      ai_classification: row.ai_classification || '',\n      ai_confidence: parseInt(row.ai_confidence) || null,\n      profile_summary: row.profile_summary || '',\n      website_analysis: row.website_analysis || '',\n      outreach_talking_points: row.outreach_talking_points || '',\n      fit_reasoning: row.fit_reasoning || '',\n      ai_red_flags: row.ai_red_flags || '',\n      ai_green_flags: row.ai_green_flags || '',\n      priority_score: parseInt(row.priority_score) || 0,\n      lead_type: row.lead_type || '',\n      retreat_count: parseInt(row.retreat_count) || 0,\n      unique_locations: parseInt(row.unique_locations) || 0,\n      is_traveling_facilitator: row.is_traveling_facilitator === 'True' || row.is_traveling_facilitator === true,\n      is_multi_platform: row.is_multi_platform === 'True' || row.is_multi_platform === true,\n      \n      // Event data\n      event_id: `${row.unique_id}-${row.event_url ? row.event_url.slice(-20) : Date.now()}`,\n      title: row.title || '',\n      dates: row.dates || '',\n      price: row.price || '',\n      location_city: row.location_city || '',\n      detailed_address: row.detailed_address || '',\n      event_url: row.event_url || '',\n      center_url: row.center_url || '',\n      retreat_description: row.retreat_description || '',\n      group_size: parseInt(row.group_size) || null,\n      rating: row.rating || '',\n      source_platform: row.source_platform || '',\n      source_label: row.source_label || '',\n      scrape_description: row.scrape_description || '',\n      scrape_date: row.scrape_date || '',\n      source_url: row.source_url || '',\n      \n      // Guides array\n      guides: guides\n    }\n  });\n}\n\nreturn output;"
      },
      "id": "process_data",
      "name": "Process Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [900, 300]
    },
    {
      "parameters": {
        "operation": "upsert",
        "base": "YOUR_AIRTABLE_BASE_ID",
        "table": "Retreat Centers",
        "columns": {
          "mappingMode": "defineBelow",
          "value": {
            "center_id": "={{ $json.center_id }}",
            "organizer_name": "={{ $json.organizer_name }}",
            "phone": "={{ $json.phone }}",
            "email": "={{ $json.email }}",
            "website": "={{ $json.website }}",
            "instagram": "={{ $json.instagram }}",
            "facebook": "={{ $json.facebook }}",
            "linkedin": "={{ $json.linkedin }}",
            "twitter": "={{ $json.twitter }}",
            "youtube": "={{ $json.youtube }}",
            "tiktok": "={{ $json.tiktok }}",
            "google_business_name": "={{ $json.google_business_name }}",
            "google_address": "={{ $json.google_address }}",
            "google_rating": "={{ $json.google_rating }}",
            "google_reviews": "={{ $json.google_reviews }}",
            "google_maps_url": "={{ $json.google_maps_url }}",
            "latitude": "={{ $json.latitude }}",
            "longitude": "={{ $json.longitude }}",
            "distance_to_surfbreak_miles": "={{ $json.distance_to_surfbreak_miles }}",
            "ai_classification": "={{ $json.ai_classification }}",
            "ai_confidence": "={{ $json.ai_confidence }}",
            "profile_summary": "={{ $json.profile_summary }}",
            "website_analysis": "={{ $json.website_analysis }}",
            "outreach_talking_points": "={{ $json.outreach_talking_points }}",
            "fit_reasoning": "={{ $json.fit_reasoning }}",
            "ai_red_flags": "={{ $json.ai_red_flags }}",
            "ai_green_flags": "={{ $json.ai_green_flags }}",
            "priority_score": "={{ $json.priority_score }}",
            "lead_type": "={{ $json.lead_type }}",
            "retreat_count": "={{ $json.retreat_count }}",
            "unique_locations": "={{ $json.unique_locations }}",
            "is_traveling_facilitator": "={{ $json.is_traveling_facilitator }}",
            "is_multi_platform": "={{ $json.is_multi_platform }}"
          }
        },
        "options": {
          "upsert": true,
          "upsertFields": ["center_id"]
        }
      },
      "id": "upsert_center",
      "name": "Upsert Center",
      "type": "n8n-nodes-base.airtable",
      "typeVersion": 2,
      "position": [1120, 300],
      "credentials": {
        "airtableTokenApi": {
          "id": "YOUR_CREDENTIAL_ID",
          "name": "Airtable API Token"
        }
      }
    },
    {
      "parameters": {
        "operation": "create",
        "base": "YOUR_AIRTABLE_BASE_ID",
        "table": "Retreat Events",
        "columns": {
          "mappingMode": "defineBelow",
          "value": {
            "event_id": "={{ $json.event_id }}",
            "title": "={{ $json.title }}",
            "dates": "={{ $json.dates }}",
            "price": "={{ $json.price }}",
            "location_city": "={{ $json.location_city }}",
            "detailed_address": "={{ $json.detailed_address }}",
            "event_url": "={{ $json.event_url }}",
            "center_url": "={{ $json.center_url }}",
            "retreat_description": "={{ $json.retreat_description }}",
            "group_size": "={{ $json.group_size }}",
            "rating": "={{ $json.rating }}",
            "source_platform": "={{ $json.source_platform }}",
            "source_label": "={{ $json.source_label }}",
            "scrape_description": "={{ $json.scrape_description }}",
            "scrape_date": "={{ $json.scrape_date }}",
            "source_url": "={{ $json.source_url }}",
            "Center": "={{ [$node['Upsert Center'].json.id] }}"
          }
        }
      },
      "id": "create_event",
      "name": "Create Event",
      "type": "n8n-nodes-base.airtable",
      "typeVersion": 2,
      "position": [1340, 300],
      "credentials": {
        "airtableTokenApi": {
          "id": "YOUR_CREDENTIAL_ID",
          "name": "Airtable API Token"
        }
      }
    },
    {
      "parameters": {
        "jsCode": "// Split guides into individual items for processing\nconst items = $input.all();\nconst output = [];\n\nfor (const item of items) {\n  const guides = item.json.guides || [];\n  const eventId = item.json.event_id;\n  const eventRecordId = $node['Create Event'].json.id; // Airtable record ID\n  \n  for (const guide of guides) {\n    output.push({\n      json: {\n        guide_id: guide.guide_id || '',\n        name: guide.name || '',\n        role: guide.role || 'Guide',\n        bio: guide.bio || '',\n        photo_url: guide.photo_url || '',\n        profile_url: guide.profile_url || '',\n        credentials: guide.credentials || '',\n        event_record_id: eventRecordId\n      }\n    });\n  }\n}\n\n// If no guides, return empty to skip\nif (output.length === 0) {\n  return [{ json: { skip: true } }];\n}\n\nreturn output;"
      },
      "id": "split_guides",
      "name": "Split Guides",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1560, 300]
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.skip }}",
              "value2": true,
              "operation": "notEqual"
            }
          ]
        }
      },
      "id": "filter_empty",
      "name": "Filter Empty",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [1780, 300]
    },
    {
      "parameters": {
        "operation": "upsert",
        "base": "YOUR_AIRTABLE_BASE_ID",
        "table": "Retreat Guides",
        "columns": {
          "mappingMode": "defineBelow",
          "value": {
            "guide_id": "={{ $json.guide_id }}",
            "name": "={{ $json.name }}",
            "role": "={{ $json.role }}",
            "bio": "={{ $json.bio }}",
            "photo_url": "={{ $json.photo_url }}",
            "profile_url": "={{ $json.profile_url }}",
            "credentials": "={{ $json.credentials }}",
            "Events": "={{ [$json.event_record_id] }}"
          }
        },
        "options": {
          "upsert": true,
          "upsertFields": ["guide_id"]
        }
      },
      "id": "upsert_guide",
      "name": "Upsert Guide",
      "type": "n8n-nodes-base.airtable",
      "typeVersion": 2,
      "position": [2000, 200],
      "credentials": {
        "airtableTokenApi": {
          "id": "YOUR_CREDENTIAL_ID",
          "name": "Airtable API Token"
        }
      }
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [[{"node": "Read CSV", "type": "main", "index": 0}]]
    },
    "Read CSV": {
      "main": [[{"node": "Parse CSV", "type": "main", "index": 0}]]
    },
    "Parse CSV": {
      "main": [[{"node": "Process Data", "type": "main", "index": 0}]]
    },
    "Process Data": {
      "main": [[{"node": "Upsert Center", "type": "main", "index": 0}]]
    },
    "Upsert Center": {
      "main": [[{"node": "Create Event", "type": "main", "index": 0}]]
    },
    "Create Event": {
      "main": [[{"node": "Split Guides", "type": "main", "index": 0}]]
    },
    "Split Guides": {
      "main": [[{"node": "Filter Empty", "type": "main", "index": 0}]]
    },
    "Filter Empty": {
      "main": [
        [{"node": "Upsert Guide", "type": "main", "index": 0}],
        []
      ]
    }
  }
}
```

### n8n Setup Instructions

1. **Create a new workflow** in n8n
2. **Import the JSON** above (or build manually following the structure)
3. **Configure credentials:**
   - Add your Airtable API token
   - Update `YOUR_AIRTABLE_BASE_ID` with your base ID
   - Update `YOUR_CREDENTIAL_ID` with your credential ID
4. **Update the CSV path** in the "Read CSV" node
5. **Test with a small batch** first (maybe 5-10 rows)
6. **Run the full import** once tested

### Key n8n Node Configurations

#### Upsert Center Node
- **Operation:** Upsert (Update if exists, Insert if new)
- **Match Field:** `center_id`
- This ensures the same organizer isn't duplicated

#### Create Event Node
- **Operation:** Create
- **Link to Center:** Uses the Airtable record ID from the previous upsert
- Events are always created (no deduplication needed)

#### Upsert Guide Node
- **Operation:** Upsert
- **Match Field:** `guide_id`
- **Link to Event:** Adds the Event record ID to the Events field
- Same guide across retreats = one record with multiple linked events

---

## Field Mappings

### CSV to Retreat Centers

| CSV Column | Airtable Field |
|------------|----------------|
| `unique_id` | `center_id` |
| `organizer` | `organizer_name` |
| `phone` | `phone` |
| `email` | `email` |
| `website` | `website` |
| `instagram` | `instagram` |
| `facebook` | `facebook` |
| `linkedin` | `linkedin` |
| `twitter` | `twitter` |
| `youtube` | `youtube` |
| `tiktok` | `tiktok` |
| `google_business_name` | `google_business_name` |
| `google_address` | `google_address` |
| `google_rating` | `google_rating` |
| `google_reviews` | `google_reviews` |
| `google_maps_url` | `google_maps_url` |
| `latitude` | `latitude` |
| `longitude` | `longitude` |
| `distance_to_surfbreak_miles` | `distance_to_surfbreak_miles` |
| `ai_classification` | `ai_classification` |
| `ai_confidence` | `ai_confidence` |
| `profile_summary` | `profile_summary` |
| `website_analysis` | `website_analysis` |
| `outreach_talking_points` | `outreach_talking_points` |
| `fit_reasoning` | `fit_reasoning` |
| `ai_red_flags` | `ai_red_flags` |
| `ai_green_flags` | `ai_green_flags` |
| `priority_score` | `priority_score` |
| `lead_type` | `lead_type` |
| `retreat_count` | `retreat_count` |
| `unique_locations` | `unique_locations` |
| `is_traveling_facilitator` | `is_traveling_facilitator` |
| `is_multi_platform` | `is_multi_platform` |

### CSV to Retreat Events

| CSV Column | Airtable Field |
|------------|----------------|
| (generated) | `event_id` |
| `title` | `title` |
| `dates` | `dates` |
| `price` | `price` |
| `location_city` | `location_city` |
| `detailed_address` | `detailed_address` |
| `event_url` | `event_url` |
| `center_url` | `center_url` |
| `retreat_description` | `retreat_description` |
| `group_size` | `group_size` |
| `rating` | `rating` |
| `source_platform` | `source_platform` |
| `source_label` | `source_label` |
| `scrape_description` | `scrape_description` |
| `scrape_date` | `scrape_date` |
| `source_url` | `source_url` |
| (from upsert) | `Center` (linked record) |

### guides_json to Retreat Guides

| JSON Field | Airtable Field |
|------------|----------------|
| `guide_id` | `guide_id` |
| `name` | `name` |
| `role` | `role` |
| `bio` | `bio` |
| `photo_url` | `photo_url` |
| `profile_url` | `profile_url` |
| `credentials` | `credentials` |
| (from create) | `Events` (linked record) |

---

## Alternative: Airtable Native CSV Import

If you prefer not to use n8n, you can do a simpler single-table import:

1. Import `leads_analyzed.csv` directly into Airtable
2. Use the single-table setup prompt from `IMPLEMENTATION_GUIDE.md`
3. Manually create linked tables later if needed

The n8n workflow is recommended for:
- Automatic three-table structure
- Proper record linking
- Guide deduplication
- Repeatable imports for new scrapes
