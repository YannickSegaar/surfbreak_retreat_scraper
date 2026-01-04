# Surfbreak Lead Generation System - Client Guide

## What This System Does

This system automatically finds retreat facilitators who might want to host their retreats at Surfbreak PXM. It searches popular retreat booking websites, gathers contact information, and uses AI to identify which leads are most likely to become your clients.

**The key insight:** Most retreat listings online are from venue owners (your competitors), not the facilitators who actually rent venues. This system is specifically designed to filter out competitors and surface the ~20-30% of leads who are traveling facilitators - your ideal prospects.

---

## Table of Contents

1. [The Problem We're Solving](#the-problem-were-solving)
2. [How It Works (Step by Step)](#how-it-works-step-by-step)
3. [Understanding Your Leads](#understanding-your-leads)
4. [Using Airtable](#using-airtable)
5. [Managing Duplicate Leads](#managing-duplicate-leads)
6. [Sales Workflow & Lead Tracking](#sales-workflow--lead-tracking)
7. [Recommended Additional Fields](#recommended-additional-fields)
8. [Best Practices for Outreach](#best-practices-for-outreach)

---

## The Problem We're Solving

### The Challenge

When you search retreat websites like retreat.guru or bookretreats.com, you'll find hundreds of retreat listings. But here's the problem:

- **~70% are venue owners** - These are retreat centers that own their property. They're your competitors, not prospects.
- **~30% are traveling facilitators** - These are yoga teachers, wellness coaches, and meditation guides who rent venues to host their retreats. These are your ideal clients.

Manually going through hundreds of listings to figure out who owns a venue versus who rents venues would take days. This system does it automatically.

### The Solution

Our system:
1. Automatically scrapes retreat listings from multiple websites
2. Finds contact information (phone, email, social media)
3. Uses AI to analyze each lead and determine if they're a facilitator or venue owner
4. Calculates how far each lead's current retreats are from Surfbreak
5. Scores and prioritizes leads so you know exactly who to contact first

---

## How It Works (Step by Step)

### Step 1: Finding Retreat Listings

The system visits retreat booking websites and collects information about every retreat listing:
- **Retreat name** - What the retreat is called
- **Organizer name** - Who is running the retreat
- **Location** - Where the retreat takes place
- **Dates and pricing** - When it runs and how much it costs
- **Links** - Direct links to the listings

**Why multiple websites?** By searching both retreat.guru and bookretreats.com, we can:
- Find more leads overall
- Identify organizers who appear on multiple platforms (more established)
- Cross-reference the same organizer across sites

### Step 2: Finding Contact Information

For each organizer found, the system searches Google to find:
- **Phone number** - Direct business phone
- **Website** - Their official website
- **Google Maps listing** - Verified business information
- **GPS coordinates** - For distance calculations

### Step 3: Scraping Websites for More Contacts

The system visits each organizer's website and looks for:
- **Email addresses** - Contact emails, booking emails
- **Social media links** - Instagram, Facebook, LinkedIn, Twitter, YouTube, TikTok

This gives you multiple ways to reach each prospect.

### Step 4: AI Analysis

This is where the magic happens. For each lead, our AI:

**Analyzes their website deeply:**
- Reads their homepage, about page, team page, and services
- Looks for signs they own a venue (room bookings, accommodation details)
- Looks for signs they're a traveling facilitator (teaching at multiple locations)

**Generates a classification:**
- **FACILITATOR** - They rent venues, they're a prospect
- **VENUE_OWNER** - They own their venue, they're a competitor
- **UNCLEAR** - Needs manual review

**Creates a profile summary:**
A 2-3 sentence description of who they are, what they do, and their style.

**Generates outreach talking points:**
Three personalized conversation starters based on their specific retreats and style.

**Explains the fit:**
Why they would or wouldn't be a good fit for Surfbreak.

**Identifies signals:**
- Green flags (positive indicators)
- Red flags (concerns to watch for)

### Step 5: Distance Calculation

The system calculates how far each lead's current retreat location is from Surfbreak PXM in Puerto Escondido. This helps you understand:
- Are they already hosting retreats nearby? (Easy logistics for them)
- Are they far away? (Might need more convincing about the location)

### Step 6: Scoring and Prioritization

Each lead gets a **priority score from 0-100** based on:

| Factor | Impact |
|--------|--------|
| Hosts at multiple different locations | +30 points (strongest signal they rent venues!) |
| AI classified as FACILITATOR | +25 points (scaled by confidence) |
| Appears on multiple platforms | +10 points (more established) |
| Has 3+ retreats listed | +10 points (very active) |
| AI classified as VENUE_OWNER | -30 points (competitor) |

**Score interpretation:**
- **70-100:** Contact immediately - high likelihood they rent venues
- **50-69:** Worth reaching out - decent prospect
- **Below 50:** Likely a competitor - skip unless you have time

### Step 7: Final Classification

Each lead is assigned a **lead type**:

| Type | What it means | Priority |
|------|---------------|----------|
| **TRAVELING_FACILITATOR** | Hosts retreats at 2+ different locations. Best prospects! | Highest |
| **FACILITATOR** | AI confirms they're a facilitator who rents venues | High |
| **UNKNOWN** | Can't determine - worth investigating | Medium |
| **VENUE_OWNER** | Owns their own venue - competitor | Low (skip) |

---

## Understanding Your Leads

### Key Fields Explained

**Identification:**
- `unique_id` - A code that identifies each organizer. Same code = same organizer (even across different platforms)
- `source_platform` - Which website the lead came from (retreat.guru or bookretreats.com)
- `source_label` - Which search batch this came from (e.g., "yoga-mexico")

**Contact Information:**
- `phone` - Business phone number
- `email` - Email address(es) found
- `website` - Their website URL
- `instagram`, `facebook`, etc. - Social media profiles

**AI Analysis:**
- `ai_classification` - FACILITATOR, VENUE_OWNER, or UNCLEAR
- `ai_confidence` - How sure the AI is (0-100%)
- `profile_summary` - Who they are in 2-3 sentences
- `outreach_talking_points` - Ready-to-use conversation starters
- `fit_reasoning` - Why they're a good/bad fit for Surfbreak

**Scoring:**
- `priority_score` - Overall score (0-100), higher = better prospect
- `lead_type` - Final classification
- `retreat_count` - How many retreats they have listed
- `unique_locations` - How many different places they host retreats
- `is_traveling_facilitator` - TRUE if they host at 2+ locations

---

## Using Airtable

### Three-Table Structure (Recommended)

For best results, we recommend a three-table Airtable structure with linked records:

| Table | Purpose | Records |
|-------|---------|---------|
| **Retreat Centers** | Your main CRM - unique organizers/facilitators | One record per organizer |
| **Retreat Events** | Individual retreat listings | All scraped events |
| **Retreat Guides** | Facilitators who lead retreats | Deduplicated guides |

**Benefits:**
- **No duplicate organizers** - Even if someone has 10 retreats, they appear once in Centers
- **Linked records** - Click a center to see all their events and guides
- **Better sales workflow** - Focus on Centers table for outreach
- **Guide tracking** - See which facilitators work with which organizers

### Option 1: Automated Import via n8n (Recommended)

Use the n8n workflow to automatically:
1. Create/update Center records (deduplicated by organizer)
2. Create Event records linked to Centers
3. Create/update Guide records linked to Events

See `AIRTABLE_N8N_SETUP.md` for complete setup instructions and Airtable AI prompts.

### Option 2: Simple Single-Table Import

If you prefer simplicity, import `leads_analyzed.csv` directly:

1. Open Airtable and create a new base
2. Use the Airtable AI assistant with the setup prompt (in DOCUMENTATION.md)
3. Import the `leads_analyzed.csv` file
4. The fields will automatically map to the correct columns

**Pre-configured views:**

1. **All Leads** - Everything, sorted by priority score
2. **High Priority (70+)** - Your best prospects to contact first
3. **Traveling Facilitators** - The absolute best prospects (host at multiple locations)
4. **Facilitators** - All likely facilitators
5. **Venue Owners (Skip)** - Competitors to avoid
6. **Needs Review** - Unclear leads that need manual review
7. **By Platform** - Grouped by source website

---

## Managing Duplicate Leads

### Why There Are Duplicates

You'll see the same organizer appearing multiple times because:

1. **Multiple retreats** - One organizer might have 5 different retreats listed
2. **Multiple platforms** - The same organizer might be on both retreat.guru AND bookretreats.com
3. **Multiple search batches** - If you ran searches for "yoga" and "meditation", the same organizer might appear in both

### How to Identify Duplicates

**Look at the `unique_id` field.** Every row with the same `unique_id` is the same organizer.

For example:
| unique_id | organizer | title | source_platform |
|-----------|-----------|-------|-----------------|
| a1b2c3d4e5f6 | Sarah's Yoga | Beach Yoga Retreat | retreat.guru |
| a1b2c3d4e5f6 | Sarah's Yoga | Mountain Meditation | retreat.guru |
| a1b2c3d4e5f6 | Sarah's Yoga | Bali Transformation | bookretreats.com |

All three rows are the SAME organizer (Sarah's Yoga) - she just has multiple retreats.

### Handling Duplicates in Airtable

**Option 1: Group by unique_id (Recommended for outreach)**

Create a view that groups by `unique_id`. This way you see each organizer once, with all their retreats grouped together.

**Option 2: Use the data for context**

Don't delete duplicates! They give you valuable information:
- How many retreats does this organizer run? (more = more active)
- What types of retreats do they offer? (yoga, meditation, wellness?)
- What locations do they use? (If multiple, they're a traveling facilitator!)

**Option 3: Create a "Unique Organizers" view**

In Airtable, create a view that:
1. Groups by `unique_id`
2. Shows only the first record in each group
3. Displays `retreat_count` to show how many retreats they have

### Important Note on Scoring

The scoring system already accounts for duplicates:
- `retreat_count` tells you how many retreats this organizer has
- `unique_locations` tells you how many different places they host
- `is_traveling_facilitator` is TRUE if they host at 2+ locations

So you get all the benefits of the duplicate data without having to manually analyze it.

---

## Sales Workflow & Lead Tracking

### Recommended Workflow

**Phase 1: Initial Review (Day 1)**
1. Open the "High Priority (70+)" view
2. Quickly scan through leads
3. Mark any obvious non-fits for removal

**Phase 2: Research & Preparation (Day 1-2)**
1. For each high-priority lead, read the `profile_summary`
2. Review the `outreach_talking_points`
3. Check their website and social media
4. Note anything relevant in the Notes field

**Phase 3: Outreach (Ongoing)**
1. Send personalized outreach using the talking points
2. Log your contact in Airtable
3. Update the status as you progress

**Phase 4: Follow-up (Weekly)**
1. Review leads in "Contacted" status
2. Send follow-ups to non-responders
3. Move responding leads through your pipeline

---

## Recommended Additional Fields

Add these fields to Airtable for tracking your sales process:

### Status Tracking

**`outreach_status`** - Single Select
- `Not Started` - Haven't contacted yet
- `Researching` - Gathering more info before contact
- `Ready to Contact` - Prepared, ready to reach out
- `Contacted - Email` - Sent initial email
- `Contacted - DM` - Sent social media message
- `Contacted - Phone` - Called them
- `Follow-up Needed` - No response, need to follow up
- `In Conversation` - They responded, talking
- `Call Scheduled` - Have a call booked
- `Tour Scheduled` - Coming to visit Surfbreak
- `Proposal Sent` - Sent pricing/proposal
- `Negotiating` - Discussing terms
- `Won - Booked` - They booked!
- `Lost - Not Interested` - They declined
- `Lost - Wrong Fit` - Not actually a good fit
- `Lost - No Response` - Never responded after multiple attempts

**`contact_priority`** - Single Select
- `Hot` - Contact today
- `Warm` - Contact this week
- `Cold` - Contact when time permits
- `Do Not Contact` - Skip this lead

**`interest_level`** - Single Select (after contact)
- `Very Interested` - Excited, asking questions
- `Somewhat Interested` - Open but not urgent
- `Maybe Later` - Not now, but possibly future
- `Not Interested` - Declined
- `Unknown` - Haven't determined yet

### Date Tracking

**`first_contact_date`** - Date
When you first reached out

**`last_contact_date`** - Date
Most recent contact attempt

**`next_follow_up_date`** - Date
When to follow up next

**`booked_date`** - Date
If they book, when is the retreat?

### Notes & Communication

**`notes`** - Long Text
General notes about this lead, observations, research findings

**`contact_log`** - Long Text
Log of all contact attempts:
```
2024-01-15: Sent intro email to info@example.com
2024-01-18: No response, sent follow-up
2024-01-22: They replied! Interested in learning more
2024-01-25: Had 20 min call, sending proposal
```

**`objections`** - Long Text
Any concerns or objections they raised

**`what_they_liked`** - Long Text
What aspects of Surfbreak interested them

### Assignment & Organization

**`assigned_to`** - Collaborator
Who is handling this lead (if multiple people on your team)

**`lead_source_detail`** - Single Line Text
Additional notes on where you found them

**`tags`** - Multiple Select
- `Yoga`
- `Meditation`
- `Wellness`
- `Teacher Training`
- `Corporate`
- `Women's Retreat`
- `Couples`
- `High-End`
- `Budget-Friendly`
- `Large Groups`
- `Small Groups`
- `Repeat Potential`

### Financial Tracking

**`estimated_group_size`** - Number
How many attendees they typically have

**`estimated_retreat_length`** - Number
How many days their retreats typically run

**`estimated_value`** - Currency
Potential revenue from this booking

**`quoted_price`** - Currency
What you quoted them

---

## Best Practices for Outreach

### Personalization is Key

Don't send generic emails! Use the AI-generated data:

**Bad approach:**
> "Hi, I run a retreat venue and wondered if you'd be interested in hosting here."

**Good approach (using the talking points):**
> "Hi Sarah, I saw your Ocean Flow retreat in Tulum and loved your focus on connecting surf culture with yoga practice. I run Surfbreak PXM in Puerto Escondido - we have a similar ocean-focused philosophy and I think your retreats would be a perfect fit for our space. Would you be open to a quick call to see if there's potential for your 2025 calendar?"

### What to Reference

Use information from these fields:
- `profile_summary` - Understand who they are
- `outreach_talking_points` - Specific conversation starters
- `title` - Reference their specific retreats
- `location_city` - Their current locations
- `retreat_count` - How active they are

### Contact Methods (in order of effectiveness)

1. **Email** - If you have their email, start here
2. **Instagram DM** - Many facilitators are active here
3. **Facebook Message** - For those more active on Facebook
4. **Phone Call** - Can be effective for established centers
5. **LinkedIn** - For more corporate/professional facilitators

### Follow-up Cadence

1. **Day 1:** Initial outreach
2. **Day 4:** First follow-up if no response
3. **Day 10:** Second follow-up with different angle
4. **Day 21:** Final follow-up
5. **After that:** Move to "No Response" and try again in 3 months

### Red Flags to Watch For

Before reaching out, check:
- If `ai_classification` is "VENUE_OWNER" - they probably own a venue
- If `ai_red_flags` has concerns - read them first
- If `priority_score` is below 50 - probably not a good prospect

### Green Flags to Prioritize

Focus on leads with:
- `is_traveling_facilitator` = TRUE (they definitely rent venues)
- `priority_score` above 70
- Multiple `unique_locations` (host at different places)
- Strong `ai_green_flags`

---

## Quick Reference

### Views to Use Daily

| View | Use Case |
|------|----------|
| High Priority (70+) | Start your day here - best prospects |
| Traveling Facilitators | Your absolute best leads |
| Needs Review | When you have time for manual research |

### Fields to Check Before Outreach

1. `profile_summary` - Who are they?
2. `outreach_talking_points` - What to say?
3. `fit_reasoning` - Why are they a good fit?
4. `ai_red_flags` - Any concerns?

### Status Flow

```
Not Started
    ↓
Researching → Ready to Contact
                    ↓
              Contacted (Email/DM/Phone)
                    ↓
         ┌─────────┴─────────┐
    No Response          In Conversation
         ↓                    ↓
    Follow-up Needed    Call Scheduled
         ↓                    ↓
    Lost - No Response   Tour Scheduled
                              ↓
                        Proposal Sent
                              ↓
                         Negotiating
                              ↓
                    ┌────────┴────────┐
               Won - Booked      Lost - Not Interested
```

---

## Summary

This system gives you:

1. **Qualified leads** - Not just any retreat organizer, but specifically those who rent venues
2. **Contact information** - Phone, email, social media, website
3. **AI-powered insights** - Understanding of who each lead is and how to approach them
4. **Prioritization** - Know exactly who to contact first
5. **Personalization** - Ready-to-use talking points for each lead

Your job is to:
1. Review the high-priority leads
2. Use the AI-generated talking points to personalize outreach
3. Track your progress in Airtable
4. Follow up consistently
5. Convert conversations into bookings!

---

*This guide was created for Surfbreak PXM's lead generation system. For technical documentation, see DOCUMENTATION.md.*
