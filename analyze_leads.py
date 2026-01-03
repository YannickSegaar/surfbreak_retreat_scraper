"""
Lead Analysis & Prioritization
==============================

Analyzes scraped leads to identify the best prospects for venue rental:
- Traveling facilitators (host at multiple venues)
- Non-venue owners (likely to need rental space)
- High-activity organizers (proven track record)

USAGE:
------
uv run python analyze_leads.py

OUTPUT:
-------
- leads_analyzed.csv: Original data + priority scores and labels
- Console report with insights
"""

import re
from pathlib import Path

import pandas as pd

# Input/output files
INPUT_FILE = "leads_master.csv"
OUTPUT_FILE = "leads_analyzed.csv"


def analyze_leads():
    """Analyze leads and add priority scoring."""

    if not Path(INPUT_FILE).exists():
        print(f"ERROR: {INPUT_FILE} not found!")
        print("Run the scraping pipeline first.")
        return

    df = pd.read_csv(INPUT_FILE)
    print("=" * 70)
    print("LEAD ANALYSIS & PRIORITIZATION")
    print("=" * 70)
    print(f"\nLoaded {len(df)} leads from {INPUT_FILE}")

    # Check if AI enrichment data is available
    has_ai_data = "ai_classification" in df.columns and df["ai_classification"].notna().any()
    if has_ai_data:
        print("✓ AI enrichment data detected - using AI classification for scoring")
    else:
        print("ℹ No AI enrichment data - using heuristic classification only")

    # === ANALYSIS 1: Count retreats per organizer ===
    # Organizers with multiple retreats are more active/established
    agg_dict = {
        "organizer": "first",
        "title": "count",
        "location_city": lambda x: x.nunique(),  # Unique locations
        "source_platform": lambda x: list(x.unique()),  # Which platforms
    }

    # Include AI data if available
    if has_ai_data:
        agg_dict["ai_classification"] = "first"
        agg_dict["ai_confidence"] = "first"

    organizer_counts = df.groupby("unique_id").agg(agg_dict).rename(columns={
        "title": "retreat_count",
        "location_city": "unique_locations",
        "source_platform": "platforms"
    })

    # === ANALYSIS 2: Identify traveling facilitators ===
    # Key insight: If same organizer appears at DIFFERENT locations, they're likely
    # a facilitator who rents venues, not a venue owner
    organizer_counts["is_traveling_facilitator"] = organizer_counts["unique_locations"] > 1

    # === ANALYSIS 3: Cross-platform presence ===
    # Organizers on multiple platforms are more serious/professional
    organizer_counts["platform_count"] = organizer_counts["platforms"].apply(len)
    organizer_counts["is_multi_platform"] = organizer_counts["platform_count"] > 1

    # === ANALYSIS 4: Name-based heuristics ===
    # Venue owners often have location-based names or "center/resort/villa" in name
    venue_keywords = [
        "center", "centre", "resort", "villa", "casa", "hacienda",
        "hotel", "lodge", "camp", "sanctuary", "ashram", "temple",
        "retreat center", "wellness center", "eco", "finca"
    ]

    facilitator_keywords = [
        "yoga with", "wellness by", "retreats by", "journey",
        "school", "academy", "training", "teacher", "coach",
        "healing", "transformation"
    ]

    def classify_by_name(name):
        """Guess if organizer is venue or facilitator based on name."""
        if pd.isna(name):
            return "unknown"
        name_lower = name.lower()

        venue_score = sum(1 for kw in venue_keywords if kw in name_lower)
        facilitator_score = sum(1 for kw in facilitator_keywords if kw in name_lower)

        if venue_score > facilitator_score:
            return "likely_venue"
        elif facilitator_score > venue_score:
            return "likely_facilitator"
        else:
            return "unclear"

    organizer_counts["name_classification"] = organizer_counts["organizer"].apply(classify_by_name)

    # === PRIORITY SCORING ===
    # Higher score = better prospect for venue rental

    def calculate_priority(row):
        score = 50  # Base score

        # Traveling facilitator = HUGE signal (they rent venues!)
        if row["is_traveling_facilitator"]:
            score += 30

        # Multi-platform = professional, serious about business
        if row["is_multi_platform"]:
            score += 10

        # Multiple retreats = active, proven track record
        if row["retreat_count"] >= 3:
            score += 10
        elif row["retreat_count"] >= 2:
            score += 5

        # AI classification (if available) - takes precedence over name heuristics
        if has_ai_data and pd.notna(row.get("ai_classification")):
            ai_class = row["ai_classification"]
            ai_conf = row.get("ai_confidence", 50) or 50

            # Scale AI impact by confidence (0-100)
            confidence_multiplier = ai_conf / 100

            if ai_class == "FACILITATOR":
                score += int(25 * confidence_multiplier)  # Up to +25
            elif ai_class == "VENUE_OWNER":
                score -= int(30 * confidence_multiplier)  # Up to -30
            # UNCLEAR adds no points
        else:
            # Fall back to name classification if no AI data
            if row["name_classification"] == "likely_facilitator":
                score += 15
            elif row["name_classification"] == "likely_venue":
                score -= 20  # Likely a competitor, not a prospect

        return min(100, max(0, score))  # Clamp to 0-100

    organizer_counts["priority_score"] = organizer_counts.apply(calculate_priority, axis=1)

    # === FINAL CLASSIFICATION ===
    def get_lead_type(row):
        # AI classification takes precedence (if available and confident)
        if has_ai_data and pd.notna(row.get("ai_classification")):
            ai_class = row["ai_classification"]
            ai_conf = row.get("ai_confidence", 0) or 0

            # Use AI classification if confidence >= 60%
            if ai_conf >= 60:
                if row["is_traveling_facilitator"]:
                    return "TRAVELING_FACILITATOR"  # Even better signal
                elif ai_class == "FACILITATOR":
                    return "FACILITATOR"
                elif ai_class == "VENUE_OWNER":
                    return "VENUE_OWNER"
                # UNCLEAR falls through to heuristics

        # Fall back to heuristic classification
        if row["is_traveling_facilitator"]:
            return "TRAVELING_FACILITATOR"
        elif row["name_classification"] == "likely_venue":
            return "VENUE_OWNER"
        elif row["name_classification"] == "likely_facilitator":
            return "FACILITATOR"
        else:
            return "UNKNOWN"

    organizer_counts["lead_type"] = organizer_counts.apply(get_lead_type, axis=1)

    # === MERGE BACK TO ORIGINAL DATA ===
    # Add analysis columns to each lead row
    analysis_cols = [
        "retreat_count", "unique_locations", "is_traveling_facilitator",
        "is_multi_platform", "name_classification", "priority_score", "lead_type"
    ]

    for col in analysis_cols:
        df[col] = df["unique_id"].map(organizer_counts[col])

    # Sort by priority score (best leads first)
    df = df.sort_values("priority_score", ascending=False)

    # === SAVE RESULTS ===
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"\nSaved analyzed leads to {OUTPUT_FILE}")

    # === PRINT REPORT ===
    print("\n" + "=" * 70)
    print("ANALYSIS REPORT")
    print("=" * 70)

    total_organizers = len(organizer_counts)
    print(f"\nTotal unique organizers: {total_organizers}")

    # AI classification stats (if available)
    if has_ai_data:
        ai_classified = organizer_counts["ai_classification"].notna().sum()
        ai_facilitators = (organizer_counts["ai_classification"] == "FACILITATOR").sum()
        ai_venue_owners = (organizer_counts["ai_classification"] == "VENUE_OWNER").sum()
        ai_unclear = (organizer_counts["ai_classification"] == "UNCLEAR").sum()
        avg_confidence = organizer_counts["ai_confidence"].mean()

        print(f"\n--- AI Classification Summary ---")
        print(f"  Leads analyzed by AI: {ai_classified}/{total_organizers}")
        print(f"  AI Classifications:")
        print(f"    FACILITATOR:  {ai_facilitators} ({ai_facilitators/total_organizers*100:.1f}%)")
        print(f"    VENUE_OWNER:  {ai_venue_owners} ({ai_venue_owners/total_organizers*100:.1f}%)")
        print(f"    UNCLEAR:      {ai_unclear} ({ai_unclear/total_organizers*100:.1f}%)")
        print(f"  Average AI confidence: {avg_confidence:.1f}%")

    # Lead type breakdown
    print("\n--- Lead Type Breakdown ---")
    type_counts = organizer_counts["lead_type"].value_counts()
    for lead_type, count in type_counts.items():
        pct = count / total_organizers * 100
        print(f"  {lead_type}: {count} ({pct:.1f}%)")

    # Traveling facilitators (your BEST prospects)
    traveling = organizer_counts[organizer_counts["is_traveling_facilitator"]]
    print(f"\n--- TRAVELING FACILITATORS (Best Prospects) ---")
    print(f"Found {len(traveling)} organizers who host at multiple locations!")
    if len(traveling) > 0:
        print("\nTop traveling facilitators:")
        top_traveling = traveling.nlargest(10, "retreat_count")
        for _, row in top_traveling.iterrows():
            print(f"  - {row['organizer']}: {row['retreat_count']} retreats across {row['unique_locations']} locations")

    # Multi-platform organizers
    multi_plat = organizer_counts[organizer_counts["is_multi_platform"]]
    print(f"\n--- MULTI-PLATFORM ORGANIZERS ---")
    print(f"Found {len(multi_plat)} organizers on multiple platforms")

    # Priority score distribution
    print(f"\n--- PRIORITY SCORE DISTRIBUTION ---")
    high_priority = (organizer_counts["priority_score"] >= 70).sum()
    medium_priority = ((organizer_counts["priority_score"] >= 50) & (organizer_counts["priority_score"] < 70)).sum()
    low_priority = (organizer_counts["priority_score"] < 50).sum()

    print(f"  HIGH (70-100):   {high_priority} organizers - Contact first!")
    print(f"  MEDIUM (50-69):  {medium_priority} organizers - Worth reaching out")
    print(f"  LOW (0-49):      {low_priority} organizers - Likely competitors")

    # Top 10 overall
    print(f"\n--- TOP 10 PROSPECTS ---")
    top_10 = organizer_counts.nlargest(10, "priority_score")
    for i, (uid, row) in enumerate(top_10.iterrows(), 1):
        print(f"  {i}. {row['organizer']} (Score: {row['priority_score']})")
        print(f"     - {row['retreat_count']} retreats, {row['unique_locations']} locations")
        print(f"     - Type: {row['lead_type']}")

    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print("""
1. PRIORITIZE: Focus on leads with priority_score >= 70
   These are likely facilitators who rent venues

2. TRAVELING FACILITATORS: Your best prospects!
   They already host at multiple locations = open to new venues

3. AVOID: Leads marked as VENUE_OWNER (priority < 50)
   These are your competitors, not prospects

4. CONTACT STRATEGY:
   - Mention you saw their retreats on [platform]
   - Highlight what makes your venue unique
   - Offer a site visit or virtual tour
   - Be specific about dates/availability

5. NEXT STEPS:
   - Filter leads_analyzed.csv by priority_score >= 70
   - Export high-priority leads to a CRM
   - Personalize outreach based on their retreat style
""")
    print("=" * 70)


if __name__ == "__main__":
    analyze_leads()
