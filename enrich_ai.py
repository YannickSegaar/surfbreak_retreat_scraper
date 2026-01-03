"""
AI-Powered Lead Enrichment
==========================

Deep-scrapes websites and uses OpenAI GPT-4 to generate intelligent lead analysis:
- Classification (FACILITATOR vs VENUE_OWNER)
- Profile summaries
- Outreach talking points
- Fit reasoning

USAGE:
------
uv run python enrich_ai.py

Or as part of the pipeline:
uv run python run_pipeline.py --url "..." --label "..."

SETUP:
------
Add to .env:
OPENAI_API_KEY=your-api-key-here
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = "leads_master.csv"
OUTPUT_FILE = "leads_ai_enriched.csv"
CACHE_FILE = "ai_enrichment_cache.json"

# Website scraping settings
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.5
MAX_CONTENT_LENGTH = 4000  # Max chars per page to send to AI

# Pages to scrape for deep content analysis
PAGES_TO_SCRAPE = [
    "/",
    "/about",
    "/about-us",
    "/our-story",
    "/team",
    "/founder",
    "/facilitators",
    "/services",
    "/retreats",
    "/offerings",
    "/venue",           # IMPORTANT: existence suggests venue owner
    "/accommodations",  # IMPORTANT: room types = venue owner
    "/rooms",
    "/contact",
]

# OpenAI settings
OPENAI_MODEL = "gpt-4o-mini"  # Cheaper and faster, good quality


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class WebsiteContent:
    """Extracted content from a website."""
    homepage_text: str = ""
    about_text: str = ""
    services_text: str = ""
    has_venue_page: bool = False
    has_accommodations_page: bool = False
    all_text: str = ""
    pages_found: list = field(default_factory=list)


@dataclass
class AIAnalysis:
    """AI-generated lead analysis."""
    classification: str = "UNCLEAR"  # FACILITATOR, VENUE_OWNER, UNCLEAR
    confidence: int = 50
    profile_summary: str = ""
    website_analysis: str = ""
    outreach_talking_points: list = field(default_factory=list)
    fit_reasoning: str = ""
    red_flags: list = field(default_factory=list)
    green_flags: list = field(default_factory=list)


# =============================================================================
# WEBSITE CONTENT EXTRACTOR
# =============================================================================

class WebsiteContentExtractor:
    """Deep scrapes websites to extract relevant content for AI analysis."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )

    async def close(self):
        await self.client.aclose()

    async def extract_content(self, website_url: str) -> WebsiteContent:
        """Extract content from multiple pages of a website."""
        content = WebsiteContent()

        if not website_url:
            return content

        # Normalize URL
        if not website_url.startswith(("http://", "https://")):
            website_url = "https://" + website_url

        base_url = website_url.rstrip("/")

        for path in PAGES_TO_SCRAPE:
            try:
                url = base_url + path if path != "/" else base_url
                response = await self.client.get(url)

                if response.status_code == 200:
                    text = self._extract_text(response.text)
                    content.pages_found.append(path)

                    # Categorize content
                    if path == "/":
                        content.homepage_text = text[:MAX_CONTENT_LENGTH]
                    elif path in ["/about", "/about-us", "/our-story", "/team", "/founder"]:
                        content.about_text += text[:MAX_CONTENT_LENGTH] + "\n"
                    elif path in ["/services", "/retreats", "/offerings"]:
                        content.services_text += text[:MAX_CONTENT_LENGTH] + "\n"
                    elif path in ["/venue", "/accommodations", "/rooms"]:
                        content.has_venue_page = True
                        if path == "/accommodations" or path == "/rooms":
                            content.has_accommodations_page = True

                    # Add to combined text
                    content.all_text += f"\n--- {path} ---\n{text[:MAX_CONTENT_LENGTH]}\n"

                await asyncio.sleep(REQUEST_DELAY)

            except Exception:
                # Silently skip failed pages
                continue

        return content

    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator=" ", strip=True)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)

        return text[:MAX_CONTENT_LENGTH * 2]


# =============================================================================
# AI LEAD ANALYZER
# =============================================================================

class AILeadAnalyzer:
    """Uses OpenAI GPT-4 to analyze leads and generate insights."""

    SYSTEM_PROMPT = """You are a lead qualification expert for Surfbreak Mexico Retreats, a premium retreat venue in Mexico looking to attract facilitators who want to rent their space for hosting retreats.

Your task is to analyze retreat organizer data and determine:
1. Is this a FACILITATOR (someone who leads retreats and rents venues) or a VENUE_OWNER (owns their own retreat property - these are competitors)?
2. Are they a good fit to potentially rent our venue?
3. What specific things should we mention when reaching out to them?

KEY SIGNALS OF A FACILITATOR (good prospect - they rent venues):
- Hosts retreats at MULTIPLE DIFFERENT locations/venues
- Personal brand focused on teaching (yoga teacher, wellness coach, meditation guide)
- Website focuses on their teachings, philosophy, programs - NOT accommodations
- No mention of owning property or a specific venue
- Often based in US/Canada/Europe but hosts retreats internationally
- Language like "we partner with beautiful venues" or "held at [various locations]"

KEY SIGNALS OF A VENUE_OWNER (competitor - skip these):
- Owns a specific property or retreat center
- Website has room bookings, accommodation details, room types
- Has a /venue, /accommodations, or /rooms page with booking info
- Name includes location-specific words like "casa", "villa", "resort", "center", "hacienda"
- Single fixed location for all their retreats
- Language like "our center", "our property", "stay with us"

Be specific in your analysis. Reference actual details from their website/data."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def analyze_lead(self, lead_data: dict, website_content: WebsiteContent) -> AIAnalysis:
        """Analyze a lead using GPT-4."""

        # Build the analysis prompt
        prompt = self._build_prompt(lead_data, website_content)

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            # Parse the JSON response
            result = json.loads(response.choices[0].message.content)
            return self._parse_response(result)

        except Exception as e:
            print(f"    ⚠ AI analysis error: {str(e)[:50]}")
            return AIAnalysis()

    def _build_prompt(self, lead_data: dict, website_content: WebsiteContent) -> str:
        """Build the analysis prompt with all available data."""

        # Gather retreat info
        retreats_info = f"""
Retreats listed: {lead_data.get('retreat_count', 1)}
Unique locations: {lead_data.get('unique_locations', 1)}
Retreat titles: {lead_data.get('titles', 'N/A')}
Locations: {lead_data.get('locations', 'N/A')}
"""

        # Website signals
        website_signals = ""
        if website_content.has_venue_page:
            website_signals += "⚠ HAS /venue PAGE (venue owner signal)\n"
        if website_content.has_accommodations_page:
            website_signals += "⚠ HAS /accommodations or /rooms PAGE (strong venue owner signal)\n"
        if website_content.pages_found:
            website_signals += f"Pages found: {', '.join(website_content.pages_found)}\n"

        prompt = f"""Analyze this retreat organizer for Surfbreak Mexico Retreats (we want FACILITATORS who rent venues, NOT venue owners who are competitors).

ORGANIZER DATA:
- Name: {lead_data.get('organizer', 'Unknown')}
- Platform: {lead_data.get('source_platform', 'N/A')}
{retreats_info}
- Google Business Name: {lead_data.get('google_business_name', 'N/A')}
- Google Rating: {lead_data.get('google_rating', 'N/A')} ({lead_data.get('google_reviews', 'N/A')} reviews)
- Location: {lead_data.get('location_city', 'N/A')}

WEBSITE SIGNALS:
{website_signals}

WEBSITE CONTENT (extracted text):
{website_content.all_text[:6000] if website_content.all_text else 'No website content available'}

---

Analyze this lead and respond with a JSON object containing:
{{
  "classification": "FACILITATOR" or "VENUE_OWNER" or "UNCLEAR",
  "confidence": 0-100 (how confident are you in this classification),
  "profile_summary": "2-3 sentences describing who they are and what they do",
  "website_analysis": "Key insights from their website that informed your classification",
  "outreach_talking_points": [
    "Specific conversation starter referencing their work",
    "Something that shows you researched them",
    "A relevant value proposition for them"
  ],
  "fit_reasoning": "Why they are or aren't a good fit for our venue rental",
  "red_flags": ["Any concerns or reasons to deprioritize this lead"],
  "green_flags": ["Strong positive signals that make them a good prospect"]
}}"""

        return prompt

    def _parse_response(self, result: dict) -> AIAnalysis:
        """Parse the AI response into an AIAnalysis object."""
        return AIAnalysis(
            classification=result.get("classification", "UNCLEAR"),
            confidence=result.get("confidence", 50),
            profile_summary=result.get("profile_summary", ""),
            website_analysis=result.get("website_analysis", ""),
            outreach_talking_points=result.get("outreach_talking_points", []),
            fit_reasoning=result.get("fit_reasoning", ""),
            red_flags=result.get("red_flags", []),
            green_flags=result.get("green_flags", [])
        )


# =============================================================================
# CACHING
# =============================================================================

class AICache:
    """Caches AI analysis results to avoid re-processing."""

    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.ttl_days = 30

    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def get(self, unique_id: str) -> Optional[AIAnalysis]:
        """Get cached analysis if exists and not expired."""
        if unique_id in self.cache:
            entry = self.cache[unique_id]
            cached_date = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_date < timedelta(days=self.ttl_days):
                return AIAnalysis(**entry.get("analysis", {}))
        return None

    def set(self, unique_id: str, analysis: AIAnalysis):
        """Cache an analysis result."""
        self.cache[unique_id] = {
            "cached_at": datetime.now().isoformat(),
            "analysis": {
                "classification": analysis.classification,
                "confidence": analysis.confidence,
                "profile_summary": analysis.profile_summary,
                "website_analysis": analysis.website_analysis,
                "outreach_talking_points": analysis.outreach_talking_points,
                "fit_reasoning": analysis.fit_reasoning,
                "red_flags": analysis.red_flags,
                "green_flags": analysis.green_flags
            }
        }
        self._save_cache()


# =============================================================================
# MAIN ENRICHMENT FUNCTION
# =============================================================================

async def enrich_leads_with_ai(input_file: str = INPUT_FILE, output_file: str = OUTPUT_FILE):
    """Main function to enrich leads with AI analysis."""

    print("=" * 70)
    print("AI-POWERED LEAD ENRICHMENT")
    print("=" * 70)

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("\n⚠ ERROR: OPENAI_API_KEY not set in .env file!")
        print("Add this line to your .env file:")
        print("OPENAI_API_KEY=your-api-key-here")
        return

    print(f"\n✓ OpenAI API key loaded")
    print(f"Model: {OPENAI_MODEL}")

    # Load leads
    if not Path(input_file).exists():
        print(f"\n⚠ ERROR: {input_file} not found!")
        return

    df = pd.read_csv(input_file)
    print(f"\nLoaded {len(df)} leads from {input_file}")

    # Get unique organizers (group by unique_id)
    unique_organizers = df.groupby("unique_id").agg({
        "organizer": "first",
        "title": lambda x: " | ".join(str(t) for t in x.head(3) if pd.notna(t)),  # First 3 retreat titles
        "location_city": lambda x: " | ".join(str(loc) for loc in x.dropna().unique()),
        "website": "first",
        "source_platform": lambda x: ", ".join(str(p) for p in x.dropna().unique()),
        "google_business_name": "first",
        "google_rating": "first",
        "google_reviews": "first",
    }).reset_index()

    # Add counts
    retreat_counts = df.groupby("unique_id").size().reset_index(name="retreat_count")
    location_counts = df.groupby("unique_id")["location_city"].nunique().reset_index(name="unique_locations")
    unique_organizers = unique_organizers.merge(retreat_counts, on="unique_id")
    unique_organizers = unique_organizers.merge(location_counts, on="unique_id")

    print(f"Unique organizers to analyze: {len(unique_organizers)}")

    # Initialize components
    extractor = WebsiteContentExtractor()
    analyzer = AILeadAnalyzer(api_key)
    cache = AICache()

    # Track results
    results = {}
    stats = {"cached": 0, "analyzed": 0, "no_website": 0, "errors": 0}

    print(f"\nAnalyzing leads...")
    print("-" * 70)

    for idx, row in unique_organizers.iterrows():
        unique_id = row["unique_id"]
        organizer = row["organizer"]
        website = row.get("website", "")

        print(f"[{idx + 1}/{len(unique_organizers)}] {organizer[:40]}...", end=" ")

        # Check cache first
        cached = cache.get(unique_id)
        if cached:
            results[unique_id] = cached
            stats["cached"] += 1
            print(f"(cached: {cached.classification})")
            continue

        # Skip if no website
        if not website or pd.isna(website):
            results[unique_id] = AIAnalysis(
                classification="UNCLEAR",
                confidence=30,
                profile_summary="No website available for analysis.",
                fit_reasoning="Cannot determine fit without website data."
            )
            stats["no_website"] += 1
            print("(no website)")
            continue

        # Extract website content
        try:
            content = await extractor.extract_content(website)

            # Prepare lead data for AI
            lead_data = {
                "organizer": organizer,
                "titles": row.get("title", ""),
                "locations": row.get("location_city", ""),
                "retreat_count": row.get("retreat_count", 1),
                "unique_locations": row.get("unique_locations", 1),
                "source_platform": row.get("source_platform", ""),
                "google_business_name": row.get("google_business_name", ""),
                "google_rating": row.get("google_rating", ""),
                "google_reviews": row.get("google_reviews", ""),
                "location_city": row.get("location_city", ""),
            }

            # Analyze with AI
            analysis = analyzer.analyze_lead(lead_data, content)
            results[unique_id] = analysis
            cache.set(unique_id, analysis)
            stats["analyzed"] += 1
            print(f"→ {analysis.classification} ({analysis.confidence}%)")

        except Exception as e:
            print(f"⚠ Error: {str(e)[:30]}")
            results[unique_id] = AIAnalysis()
            stats["errors"] += 1

        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)

    await extractor.close()

    # Apply results to original dataframe
    print("\n" + "-" * 70)
    print("Applying AI analysis to leads...")

    # Add new columns
    df["ai_classification"] = ""
    df["ai_confidence"] = 0
    df["profile_summary"] = ""
    df["website_analysis"] = ""
    df["outreach_talking_points"] = ""
    df["fit_reasoning"] = ""
    df["ai_red_flags"] = ""
    df["ai_green_flags"] = ""

    for idx, row in df.iterrows():
        unique_id = row["unique_id"]
        if unique_id in results:
            analysis = results[unique_id]
            df.at[idx, "ai_classification"] = analysis.classification
            df.at[idx, "ai_confidence"] = analysis.confidence
            df.at[idx, "profile_summary"] = analysis.profile_summary
            df.at[idx, "website_analysis"] = analysis.website_analysis
            df.at[idx, "outreach_talking_points"] = " | ".join(analysis.outreach_talking_points)
            df.at[idx, "fit_reasoning"] = analysis.fit_reasoning
            df.at[idx, "ai_red_flags"] = " | ".join(analysis.red_flags)
            df.at[idx, "ai_green_flags"] = " | ".join(analysis.green_flags)

    # Save enriched data
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"\nSaved enriched data to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("AI ENRICHMENT SUMMARY")
    print("=" * 70)
    print(f"   Analyzed (new):     {stats['analyzed']}")
    print(f"   From cache:         {stats['cached']}")
    print(f"   No website:         {stats['no_website']}")
    print(f"   Errors:             {stats['errors']}")
    print("-" * 70)

    # Classification breakdown
    classifications = df["ai_classification"].value_counts()
    print("\nClassification breakdown:")
    for cls, count in classifications.items():
        pct = count / len(df) * 100
        print(f"   {cls}: {count} ({pct:.1f}%)")

    print("=" * 70)


# =============================================================================
# STANDALONE EXECUTION
# =============================================================================

if __name__ == "__main__":
    asyncio.run(enrich_leads_with_ai())
