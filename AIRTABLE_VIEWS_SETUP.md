# Airtable Views Setup Guide

This guide walks you through creating useful views in your Airtable database to help organize and filter your leads effectively.

---

## What Are Views?

Views are different ways to look at the same data. Each view can have its own:
- **Filters** - Show only records matching certain criteria
- **Sorting** - Order records by specific fields
- **Grouping** - Group records by a field value
- **Hidden fields** - Hide columns you don't need for that view

Your underlying data stays the same - views just change how you see it.

---

## How to Create a View

1. Open your table in Airtable
2. Look at the left sidebar - you'll see "Grid view" (the default)
3. Click the **"+ Add view"** button (or the dropdown arrow next to the current view name)
4. Select **"Grid"** as the view type
5. Name your view
6. Configure filters, sorting, and hidden fields as described below

---

## Centers Table Views

These views help you organize your main leads table.

### View 1: All Centers (Default)

**Purpose:** See all centers at a glance

**Setup:**
1. Keep this as your default Grid view
2. Sort by: `name` (A to Z)

---

### View 2: High Priority - Facilitators

**Purpose:** Your best prospects - centers classified as facilitators

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `High Priority - Facilitators`
3. Click **Filter** in the toolbar
4. Add filter: `ai_classification` **is** `FACILITATOR`
5. Click **Sort** → Add sort: `ai_confidence` (High to Low)

---

### View 3: Ready to Contact

**Purpose:** Facilitators you haven't contacted yet

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Ready to Contact`
3. Click **Filter** → Add filter group:
   - `ai_classification` **is** `FACILITATOR`
   - **AND** `contact_status` **is** `Not Contacted`
4. Sort by: `google_rating` (High to Low)

---

### View 4: By Classification

**Purpose:** See all leads grouped by their AI classification

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `By Classification`
3. Click **Group** in the toolbar
4. Group by: `ai_classification`
5. Within each group, sort by: `name` (A to Z)

---

### View 5: Needs Follow-up

**Purpose:** Leads that need follow-up action

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Needs Follow-up`
3. Click **Filter** → Add filter:
   - `contact_status` **is** `No Response`
   - **OR** `next_follow_up_date` **is on or before** `Today`
4. Sort by: `next_follow_up_date` (Earliest first)

---

### View 6: Contact Pipeline

**Purpose:** Track leads through your sales process

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Contact Pipeline`
3. Click **Group** → Group by: `contact_status`
4. Sort within groups by: `name` (A to Z)

**Tip:** You can also create a Kanban view for this:
1. Click **+ Add view** → Kanban
2. Name it: `Pipeline Kanban`
3. Set the field for stacks: `contact_status`

---

### View 7: Nearby Centers

**Purpose:** Centers closest to Puerto Escondido

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Nearby Centers`
3. Click **Filter**:
   - `distance_to_surfbreak_miles` **is not empty**
4. Sort by: `distance_to_surfbreak_miles` (Low to High)

---

### View 8: Venue Owners (Reference)

**Purpose:** Keep track of venue owners for networking

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Venue Owners (Reference)`
3. Click **Filter**:
   - `ai_classification` **is** `VENUE_OWNER`
4. Sort by: `name` (A to Z)

---

### View 9: Unclear - Needs Review

**Purpose:** Leads that need manual classification

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Unclear - Needs Review`
3. Click **Filter**:
   - `ai_classification` **is** `UNCLEAR`
4. Sort by: `ai_confidence` (Low to High)

---

## Events Table Views

These views help you explore individual retreat listings.

### View 1: All Events (Default)

**Purpose:** See all events

**Setup:**
1. Keep as default Grid view
2. Sort by: `title` (A to Z)

---

### View 2: By Platform

**Purpose:** See which events came from which source

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `By Platform`
3. Click **Group** → Group by: `source_platform`
4. Sort within groups by: `title` (A to Z)

---

### View 3: Events with Descriptions

**Purpose:** Events that have detailed descriptions (useful for research)

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `With Descriptions`
3. Click **Filter**:
   - `retreat_description` **is not empty**
4. Sort by: `title` (A to Z)

---

### View 4: Top Rated Events

**Purpose:** Highest-rated retreats

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Top Rated`
3. Click **Filter**:
   - `event_rating` **is not empty**
4. Sort by: `event_rating` (High to Low)

---

### View 5: By Location

**Purpose:** See events grouped by city/location

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `By Location`
3. Click **Group** → Group by: `location_city`
4. Sort within groups by: `title` (A to Z)

---

## Guides Table Views

These views help you explore individual facilitators and teachers.

### View 1: All Guides (Default)

**Purpose:** See all guides

**Setup:**
1. Keep as default Grid view
2. Sort by: `name` (A to Z)

---

### View 2: Guides with Bios

**Purpose:** Guides who have biography information

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `With Bios`
3. Click **Filter**:
   - `bio` **is not empty**
4. Sort by: `name` (A to Z)

---

### View 3: Top Rated Guides

**Purpose:** Highest-rated facilitators

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Top Rated`
3. Click **Filter**:
   - `rating` **is not empty**
4. Sort by: `rating` (High to Low)

---

### View 4: Most Active Guides

**Purpose:** Guides with the most upcoming retreats

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `Most Active`
3. Click **Filter**:
   - `upcoming_retreats_count` **is greater than** `0`
4. Sort by: `upcoming_retreats_count` (High to Low)

---

### View 5: With Credentials

**Purpose:** Guides who have listed certifications

**Setup:**
1. Click **+ Add view** → Grid
2. Name it: `With Credentials`
3. Click **Filter**:
   - `credentials` **is not empty**
4. Sort by: `name` (A to Z)

---

## Recommended View Order

For daily use, arrange your Centers table views in this order:

1. **High Priority - Facilitators** - Start here each day
2. **Ready to Contact** - Your to-do list for outreach
3. **Needs Follow-up** - Check for pending follow-ups
4. **Contact Pipeline** - Track progress through stages
5. **Unclear - Needs Review** - When you have time for research
6. **By Classification** - Overview of all leads
7. **Nearby Centers** - Location-based filtering
8. **Venue Owners (Reference)** - For networking purposes
9. **All Centers** - Full database access

---

## Pro Tips

### Saving Filter Conditions

When you set filters on a view, they're automatically saved to that view. You can:
- Switch between views to apply different filters instantly
- Modify filters temporarily without affecting the saved view

### Using Field Hiding

For focused work, hide fields you don't need:
1. Click **Hide fields** in the toolbar
2. Toggle off fields you don't need for this view
3. Common fields to hide in daily views:
   - Technical IDs (`center_id`, `event_id`)
   - Linked record fields (unless needed)
   - Less-used contact methods

### Creating Personal Views

If multiple people use this base:
1. Create views with your name prefix: `[Your Name] - My Prospects`
2. This keeps everyone's work organized

### Using Conditional Coloring

Make important data stand out:
1. Right-click on any cell → **Conditional coloring**
2. Set colors based on values (e.g., red for VENUE_OWNER, green for FACILITATOR)

---

## Quick Reference: Filter Operators

| Operator | Use For |
|----------|---------|
| **is** | Exact match (for select fields) |
| **is not** | Exclude specific value |
| **is empty** | Find blank fields |
| **is not empty** | Find filled fields |
| **contains** | Partial text match |
| **is on or before** | Date comparisons |
| **is greater than** | Number comparisons |

---

## Need Help?

Airtable has excellent built-in documentation:
- Click the **?** icon in the bottom-right corner
- Search for "views" or "filters" for detailed guides
- Their support team is also very responsive

---

*This guide was created for the Surfbreak PXM Lead Generation System.*
