# Surfbreak PXM Lead Generation System
## Client Guide

---

## What We Built For You

This system is a comprehensive lead generation engine specifically designed for Surfbreak PXM. We've built a sophisticated data pipeline that:

- **Scrapes** retreat listings from the two largest retreat booking platforms
- **Extracts** organizer and facilitator information from multiple sources
- **Enriches** leads with verified contact data from Google Maps
- **Analyzes** each prospect using AI to determine fit
- **Prioritizes** leads so you know exactly who to contact first

The result: **A ready-to-use Airtable database** with hundreds of qualified leads, complete with contact information, AI-generated talking points, and prioritization scores.

---

## Table of Contents

1. [The Data Collection Process](#the-data-collection-process)
2. [The Challenge We Solved](#the-challenge-we-solved)
3. [Important Notes & Disclaimers](#important-notes--disclaimers)
4. [Your Airtable Database](#your-airtable-database)
5. [How to Use This for Sales](#how-to-use-this-for-sales)
6. [Getting Started Checklist](#getting-started-checklist)

---

## The Data Collection Process

Here's how we gathered and enriched your leads, step by step:

### Step 1: Search URL Configuration

We configured searches on both major retreat booking platforms:

| Platform | What We Searched |
|----------|------------------|
| **retreat.guru** | Yoga, meditation, wellness, and psychedelic retreats in Mexico, Costa Rica, Guatemala, Peru, Colombia, and United States |
| **BookRetreats.com** | Similar retreat types across the same geographic areas |

These searches were designed to capture facilitators who might be interested in hosting at Surfbreak PXM in Puerto Escondido.

### Step 2: Retreat Event Extraction

From each search, we extracted all retreat listings including:
- Retreat title and description
- Date ranges and pricing
- Location and venue information
- Direct links to the listing pages
- Ratings and reviews

### Step 3: Center/Organizer Pages

For each retreat event, we navigated to the organizer's profile page to extract:
- Organization/center name
- Full address and location details
- Profile descriptions
- Existing Google Maps links

### Step 4: Guide/Facilitator Extraction

We identified individual teachers and facilitators from retreat pages:
- Guide names and roles
- Bios and credentials
- Profile photos
- Ratings and review counts

### Step 5: Google Maps Enrichment

We searched Google Places API for each center to obtain verified contact information:

| Data Point | Description |
|------------|-------------|
| Phone Number | Business phone from Google |
| Website URL | Official website |
| Google Maps Link | Verified location |
| GPS Coordinates | For distance calculations |
| Rating & Reviews | Google business ratings |
| Distance to Surfbreak | Calculated in miles from Puerto Escondido |

### Step 6: Website Scraping

For centers with websites, we scraped their sites to find:
- Email addresses (contact forms, mailto links)
- Social media profiles (Instagram, Facebook, LinkedIn, Twitter, YouTube, TikTok)
- Additional contact information

### Step 7: AI Analysis

This is where the real magic happens. For each center, our AI system:

**Analyzed their online presence** by reading their website content, retreat descriptions, and profile information.

**Classified the lead** into one of three categories:
- **FACILITATOR** - They rent venues to host retreats (your prospects)
- **VENUE_OWNER** - They own their own venue (your competitors)
- **UNCLEAR** - Needs manual review

**Generated a profile summary** - A 2-3 sentence description of who they are and what they do.

**Created outreach talking points** - Three personalized conversation starters specific to each lead.

**Identified fit reasoning** - Why they would or wouldn't be a good match for Surfbreak.

**Flagged signals** - Green flags (positive indicators) and red flags (concerns).

---

## The Challenge We Solved

### The Problem with Retreat Listings

When you search retreat websites, you'll find hundreds of listings. But here's the challenge:

| Lead Type | Percentage | What They Are |
|-----------|------------|---------------|
| Venue Owners | ~70% | Centers that own their property - your **competitors** |
| Facilitators | ~30% | Teachers who rent venues - your **prospects** |

Manually sorting through hundreds of listings to determine who owns a venue versus who rents venues would take days of research.

### Our Solution

The AI classification system automatically identifies which leads are most likely to rent your venue:

1. **TRAVELING_FACILITATOR** - Hosts retreats at multiple different locations. These are your **best prospects** - they definitely rent venues!

2. **FACILITATOR** - AI analysis indicates they rent venues rather than own them. **Great prospects**.

3. **VENUE_OWNER** - Owns their own property. Still potentially useful as:
   - Networking contacts
   - Referral sources (they may know facilitators)
   - Future partnerships

4. **UNCLEAR** - Worth a quick manual review

### Priority Scoring

Each lead receives a score from 0-100 based on multiple factors:

| Factor | Points |
|--------|--------|
| Hosts at multiple locations | +30 |
| AI classified as FACILITATOR | +25 |
| Appears on multiple platforms | +10 |
| Has 3+ retreats listed | +10 |
| AI classified as VENUE_OWNER | -30 |

**What the scores mean:**
- **70-100**: Contact immediately - excellent prospects
- **50-69**: Worth reaching out - good potential
- **Below 50**: Likely competitors - lower priority

---

## Important Notes & Disclaimers

### Google Maps Matching

The Google Places API searches for businesses by name and location. In some cases:
- The exact business may not be found
- A similarly-named business might be returned
- Contact information may be for a different entity

**Recommendation:** Always verify contact information before reaching out, especially for high-priority leads.

### Web Scraping Limitations

Website scraping extracts data based on each site's structure at the time of scraping:
- If websites have been redesigned, some data may be missing
- Social media links and emails depend on where sites display them
- Not all websites publicly display contact information

**Recommendation:** For high-priority leads with missing contact info, a quick manual search can often fill in gaps.

### AI Classification Accuracy

The AI classification system is highly accurate but not perfect:
- Some venue owners may be misclassified as facilitators
- Some facilitators may appear as unclear
- Always check the `ai_confidence` score - higher is better

**Recommendation:** For leads with confidence below 70%, consider a quick manual review before investing significant outreach time.

### Data Freshness

This data was scraped at a specific point in time:
- Retreat dates and pricing may change
- Contact information may become outdated
- New retreats may have been added since scraping

**Recommendation:** When contacting leads, verify current information from their profiles.

---

## Your Airtable Database

### Table Overview

Your database contains three interconnected tables:

| Table | Purpose | What It Contains |
|-------|---------|------------------|
| **Centers** | Your main leads table | Organizations and facilitators who run retreats |
| **Events** | Individual retreat listings | All retreat events we scraped |
| **Guides** | Teachers/facilitators | Individual people who lead retreats |

### How the Tables Connect

```
                    ┌─────────────────┐
                    │     EVENTS      │
                    │  (478 records)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              │              ▼
    ┌─────────────────┐      │    ┌─────────────────┐
    │     CENTERS     │◄─────┘    │     GUIDES      │
    │  (265 records)  │           │  (492 records)  │
    └─────────────────┘           └─────────────────┘
```

**Relationships:**
- Each **Event** links to one **Center** (the organization running it)
- Each **Event** links to one or more **Guides** (the facilitators leading it)
- **Guides** link back to **Centers** they're affiliated with

**Why this matters:** You can click on any Center and see all their events and guides. You can click on any Guide and see all the retreats they lead.

---

### Centers Table - Field Reference

This is your **primary leads table**. Focus here for outreach.

#### Basic Information

| Field | Type | Description |
|-------|------|-------------|
| `center_id` | Text | Unique identifier for this center |
| `name` | Text | Organization/center name |
| `address` | Long Text | Full address |
| `description` | Long Text | Center's description from their profile |
| `center_url` | URL | Link to their profile on the source platform |

#### Google Maps Data (Enriched)

| Field | Type | Description |
|-------|------|-------------|
| `google_business_name` | Text | Verified business name from Google |
| `google_address` | Text | Verified address from Google |
| `google_maps_url` | URL | Direct link to Google Maps listing |
| `google_rating` | Number | Google rating (1-5 stars) |
| `google_reviews` | Number | Number of Google reviews |
| `latitude` | Number | GPS latitude coordinate |
| `longitude` | Number | GPS longitude coordinate |
| `distance_to_surfbreak_miles` | Number | Distance from Puerto Escondido |

#### Contact Information

| Field | Type | Description |
|-------|------|-------------|
| `phone` | Phone | Business phone number |
| `email` | Email | Email address |
| `website` | URL | Official website |
| `instagram` | URL | Instagram profile |
| `facebook` | URL | Facebook page |
| `linkedin` | URL | LinkedIn profile |
| `twitter` | URL | Twitter/X profile |
| `youtube` | URL | YouTube channel |
| `tiktok` | URL | TikTok profile |

#### AI Analysis

| Field | Type | Description |
|-------|------|-------------|
| `ai_classification` | Select | FACILITATOR, VENUE_OWNER, or UNCLEAR |
| `ai_confidence` | Number | Confidence score (0-100) |
| `profile_summary` | Long Text | 2-3 sentence summary of who they are |
| `website_analysis` | Long Text | Analysis of their website content |
| `outreach_talking_points` | Long Text | Ready-to-use conversation starters |
| `fit_reasoning` | Long Text | Why they're a good/bad fit for Surfbreak |
| `ai_red_flags` | Long Text | Concerns to watch for |
| `ai_green_flags` | Long Text | Positive indicators |

#### Sales Tracking (CRM Fields)

| Field | Type | Description |
|-------|------|-------------|
| `contact_status` | Select | Not Contacted, Email Sent, Responded, etc. |
| `is_good_prospect` | Checkbox | Mark as good prospect |
| `is_disqualified` | Checkbox | Mark as disqualified |
| `priority_level` | Select | High, Medium, Low |
| `last_contact_date` | Date | When you last reached out |
| `next_follow_up_date` | Date | When to follow up |
| `outreach_notes` | Long Text | Your notes on this lead |
| `contact_person` | Text | Specific person to contact |
| `contact_person_email` | Email | Their email |
| `contact_person_phone` | Phone | Their phone |

#### Linked Records

| Field | Type | Description |
|-------|------|-------------|
| `retreat_events3` | Linked | Events run by this center |
| `retreat_guides3` | Linked | Guides affiliated with this center |
| `event_count` | Count | Number of events |
| `guide_count` | Count | Number of guides |

---

### Events Table - Field Reference

Individual retreat listings. Use this to understand what types of retreats each center offers.

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | Text | Unique identifier |
| `title` | Text | Retreat title |
| `dates` | Text | Date range |
| `price` | Text | Pricing information |
| `event_url` | URL | Link to the retreat listing |
| `event_rating` | Number | Rating (1-5 stars) |
| `event_review_count` | Number | Number of reviews |
| `retreat_description` | Long Text | Full retreat description |
| `group_size` | Number | Maximum group size |
| `location_city` | Text | City/location |
| `source_platform` | Select | retreat.guru or bookretreats.com |
| `source_label` | Text | Search batch label |
| `scrape_date` | Date | When this was scraped |
| `Center3` | Linked | Link to Center record |
| `Guides3` | Linked | Links to Guide records |

---

### Guides Table - Field Reference

Individual teachers and facilitators. Useful for identifying key people at each organization.

| Field | Type | Description |
|-------|------|-------------|
| `teacher_id` | Text | Platform-specific ID |
| `guide_id` | Text | Unique identifier |
| `name` | Text | Guide's name |
| `credentials` | Text | Certifications and qualifications |
| `role` | Text | Role (Lead Teacher, Co-Facilitator, etc.) |
| `bio` | Long Text | Biography |
| `photo_url` | URL | Profile photo |
| `profile_url` | URL | Link to their profile |
| `rating` | Number | Rating (1-5) |
| `review_count` | Number | Number of reviews |
| `upcoming_retreats_count` | Number | Active retreats |
| `url_slug` | Text | URL identifier for linking |
| `retreat_events3` | Linked | Events they lead |
| `retreat_centers3` | Linked | Centers they're affiliated with |

---

## How to Use This for Sales

### Recommended Workflow

#### Phase 1: High-Priority Outreach (Week 1)

1. **Filter Centers table** by `ai_classification` = FACILITATOR
2. **Sort by** any priority indicators you prefer
3. **Review each lead:**
   - Read the `profile_summary` - Who are they?
   - Check `outreach_talking_points` - What to say?
   - Review `fit_reasoning` - Why are they a good fit?
   - Note any `ai_red_flags` - Any concerns?

4. **Personalize your outreach** using the AI-generated talking points
5. **Update `contact_status`** after each contact attempt

#### Phase 2: Broader Outreach (Week 2-3)

1. Move to leads with `ai_classification` = UNCLEAR
2. Do a quick manual review of their website
3. Reclassify as needed and proceed with outreach

#### Phase 3: Networking (Ongoing)

Even VENUE_OWNER leads can be valuable:
- They may know facilitators looking for new venues
- They could be referral partners
- Industry networking opportunities

### Using the AI-Generated Content

**The `profile_summary` tells you:**
- What type of retreats they run
- Their style and approach
- Their target audience

**The `outreach_talking_points` give you:**
- Three ready-to-use conversation starters
- Specific references to their work
- Angles for approaching them

**Example outreach (using the talking points):**

> "Hi [Name], I came across your [Retreat Name] retreat and was impressed by your focus on [specific element from their profile]. I run Surfbreak PXM in Puerto Escondido - we're a surf and wellness venue that regularly hosts traveling facilitators. Given your experience with [another specific element], I think your retreats could be a great fit for our space. Would you be open to a quick call to explore possibilities for 2025?"

### Tracking Your Progress

Update these fields as you work:

| When | Update |
|------|--------|
| Before outreach | Review the lead, set `priority_level` |
| After first contact | Set `contact_status` to "Email Sent" etc. |
| After response | Update `contact_status`, add to `outreach_notes` |
| Schedule follow-up | Set `next_follow_up_date` |
| Lead closes | Update `contact_status` to Won/Lost |

---

## Getting Started Checklist

### Day 1: Orientation

- [ ] Open your Airtable base
- [ ] Familiarize yourself with the three tables (Centers, Events, Guides)
- [ ] Explore the linked records - click through to see how they connect
- [ ] Set up views (see AIRTABLE_VIEWS_SETUP.md for instructions)

### Day 2: Review High-Priority Leads

- [ ] Filter Centers by `ai_classification` = FACILITATOR
- [ ] Review the top 20 leads
- [ ] Read their `profile_summary` and `outreach_talking_points`
- [ ] Mark any obvious non-fits

### Day 3: Begin Outreach

- [ ] Select your first 5 leads
- [ ] Personalize outreach using the AI talking points
- [ ] Send initial contact (email, DM, or call)
- [ ] Update `contact_status` for each

### Ongoing

- [ ] Check `next_follow_up_date` daily for follow-ups due
- [ ] Update status as conversations progress
- [ ] Add notes to `outreach_notes` after each interaction
- [ ] Celebrate when you close your first booking!

---

## Quick Reference

### Best Prospects to Contact First

| What to Look For | Why |
|------------------|-----|
| `ai_classification` = FACILITATOR | AI identified them as venue renters |
| Multiple linked Events | Active organizers with ongoing business |
| Multiple linked Guides | Larger operations with teams |
| `distance_to_surfbreak_miles` < 1000 | Already active in Mexico region |
| `google_rating` > 4.0 | Well-reviewed, quality operations |

### Red Flags to Watch

| Warning Sign | What It Means |
|--------------|---------------|
| `ai_classification` = VENUE_OWNER | They probably own a venue |
| `ai_confidence` < 50 | Classification uncertain |
| Check `ai_red_flags` | Specific concerns identified |
| No contact information | May be difficult to reach |

### Fields to Always Check Before Outreach

1. `profile_summary` - Who are they?
2. `outreach_talking_points` - What to say?
3. `fit_reasoning` - Why are they a fit?
4. `ai_red_flags` - Any concerns?
5. `ai_green_flags` - Positive indicators?

---

## Support & Next Steps

### Additional Resources

- **AIRTABLE_VIEWS_SETUP.md** - Instructions for creating useful Airtable views
- **DOCUMENTATION.md** - Technical documentation for the system

### Running New Searches

If you want to expand your lead database with new searches:
1. Configure new search URLs in the scraper
2. Run the data pipeline
3. Import new data via the n8n workflow

### Questions?

Contact your system administrator for technical support or questions about the data pipeline.

---

*This guide was created for Surfbreak PXM's Lead Generation System.*
