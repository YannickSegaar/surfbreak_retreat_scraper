"""
AI-Assisted Data Extraction
===========================

Uses GPT-4o-mini to extract structured data from retreat pages.
Handles variable page layouts for guides, descriptions, and group sizes.

USAGE:
------
from extract_with_ai import extract_retreat_details

details = await extract_retreat_details(html_content, openai_client)
# Returns:
# {
#   "description": "About this retreat...",
#   "group_size": 8,
#   "guides": [{"name": "...", "role": "...", "bio": "...", ...}]
# }

COST:
-----
~$0.001 per page with GPT-4o-mini
"""

import json
import os
import re

from bs4 import BeautifulSoup
from openai import OpenAI

# =============================================================================
# CONFIGURATION
# =============================================================================

# Model to use for extraction
EXTRACTION_MODEL = "gpt-4o-mini"

# Maximum tokens for input (we truncate HTML to stay under this)
MAX_INPUT_CHARS = 12000

# Maximum tokens for output
MAX_OUTPUT_TOKENS = 1500


# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

EXTRACTION_PROMPT = """You are extracting structured data from a retreat listing page.

Analyze the HTML content and extract:

1. **description**: The main retreat description/about section. Max 500 characters. Look for:
   - "About This Retreat" sections
   - Overview or summary text
   - The main description paragraph

2. **group_size**: Maximum number of participants (as a number). Look for:
   - "Group size", "Retreat size", "Max participants"
   - "Up to X people/participants"
   - Capacity information

3. **guides**: Array of guide/facilitator/instructor information. For each person, extract:
   - **name**: Full name
   - **role**: Their role (Guide, Facilitator, Instructor, Teacher, etc.)
   - **bio**: Their biography/description (max 300 chars)
   - **photo_url**: URL to their photo if present
   - **profile_url**: URL to their profile page if present
   - **credentials**: Any certifications, training, or credentials mentioned

Look for sections titled:
- "Your Guides", "Meet Your Guides"
- "Team", "Our Team"
- "Facilitator", "Facilitators"
- "Teachers", "Instructors"
- "About the Host"

IMPORTANT:
- Only extract information that is actually present on the page
- If a field is not found, use null (for single values) or [] (for arrays)
- Do not make up or infer information
- For photo URLs, include the full URL if available
- For profile URLs, include relative paths if absolute URLs aren't available

Return ONLY valid JSON with this exact structure:
{
  "description": "string or null",
  "group_size": number or null,
  "guides": [
    {
      "name": "string",
      "role": "string",
      "bio": "string or null",
      "photo_url": "string or null",
      "profile_url": "string or null",
      "credentials": "string or null"
    }
  ]
}

HTML Content to analyze:
"""


# =============================================================================
# HTML PREPROCESSING
# =============================================================================

def extract_relevant_sections(html: str, platform: str = "retreat.guru") -> str:
    """
    Extract only relevant HTML sections to reduce tokens.

    Focuses on:
    - Description/about sections
    - Guide/team/facilitator sections
    - Group size information
    """
    soup = BeautifulSoup(html, "lxml")
    sections = []

    # Remove script and style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Platform-specific selectors
    if platform == "retreat.guru":
        # Description selectors for retreat.guru
        desc_selectors = [
            "[class*='event-description']",
            "[class*='about-retreat']",
            "[class*='description']",
            "[class*='overview']",
            "section[class*='about']",
        ]

        # Guide selectors for retreat.guru
        guide_selectors = [
            "[class*='teacher']",
            "[class*='guide']",
            "[class*='facilitator']",
            "section[class*='team']",
            "a[href*='/teachers/']",
        ]

    else:  # bookretreats.com
        # Description selectors for bookretreats
        desc_selectors = [
            "[class*='retreat-description']",
            "[class*='experience']",
            "[class*='overview']",
            "[class*='about']",
            "[class*='summary']",
        ]

        # Guide selectors for bookretreats
        guide_selectors = [
            "[class*='team']",
            "[class*='facilitator']",
            "[class*='teacher']",
            "[class*='instructor']",
            "a[href*='/teacher/']",
        ]

    # Extract description sections
    for selector in desc_selectors:
        for elem in soup.select(selector)[:3]:
            text = str(elem)[:3000]
            if len(text) > 100:  # Only include substantial content
                sections.append(f"<!-- DESCRIPTION SECTION -->\n{text}")

    # Extract guide sections
    for selector in guide_selectors:
        for elem in soup.select(selector)[:5]:
            text = str(elem)[:2500]
            if len(text) > 50:
                sections.append(f"<!-- GUIDE SECTION -->\n{text}")

    # Look for group size with regex patterns
    size_patterns = [
        r'(?:group|retreat)\s*size[:\s]+(\d+)',
        r'(?:up\s+to|maximum|max)[:\s]+(\d+)\s*(?:people|participants|guests)',
        r'up\s+to\s+(\d+)\s+in\s+group',  # "Up to 7 in group" (retreat.guru format)
        r'(\d+)\s+in\s+group',  # "7 in group"
        r'(\d+)\s*(?:people|participants|guests)\s*(?:max|maximum)',
        r'capacity[:\s]+(\d+)',
    ]

    page_text = soup.get_text()
    for pattern in size_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            sections.append(f"<!-- GROUP SIZE -->\nGroup size: {match.group(1)} participants")
            break

    # If we didn't find much, include more general content
    if len("\n".join(sections)) < 1000:
        # Get main content area
        main_content = soup.select_one("main, article, [role='main'], .content, #content")
        if main_content:
            sections.append(f"<!-- MAIN CONTENT -->\n{str(main_content)[:5000]}")

    # Combine and truncate
    combined = "\n\n".join(sections)
    return combined[:MAX_INPUT_CHARS]


def clean_extracted_html(html: str) -> str:
    """
    Clean HTML for better AI processing.
    Remove excessive whitespace and common noise.
    """
    # Remove excessive newlines
    html = re.sub(r'\n\s*\n', '\n', html)
    # Remove excessive spaces
    html = re.sub(r' +', ' ', html)
    # Remove common noise patterns
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    return html.strip()


# =============================================================================
# AI EXTRACTION
# =============================================================================

def extract_retreat_details_sync(html: str, client: OpenAI, platform: str = "retreat.guru") -> dict:
    """
    Use GPT-4o-mini to extract retreat details from HTML.

    Args:
        html: Full HTML content of the retreat page
        client: OpenAI client instance
        platform: "retreat.guru" or "bookretreats.com"

    Returns:
        Dict with description, group_size, and guides
    """
    # Extract and clean relevant sections
    relevant_html = extract_relevant_sections(html, platform)
    relevant_html = clean_extracted_html(relevant_html)

    if not relevant_html or len(relevant_html) < 100:
        return {"description": None, "group_size": None, "guides": []}

    try:
        response = client.chat.completions.create(
            model=EXTRACTION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured data from HTML. Return only valid JSON, no markdown."
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + relevant_html
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0
        )

        result = json.loads(response.choices[0].message.content)

        # Validate and clean result
        return {
            "description": result.get("description") or None,
            "group_size": result.get("group_size") if isinstance(result.get("group_size"), int) else None,
            "guides": result.get("guides") or []
        }

    except json.JSONDecodeError as e:
        print(f"    AI returned invalid JSON: {e}")
        return {"description": None, "group_size": None, "guides": []}
    except Exception as e:
        print(f"    AI extraction error: {e}")
        return {"description": None, "group_size": None, "guides": []}


async def extract_retreat_details(html: str, client: OpenAI, platform: str = "retreat.guru") -> dict:
    """
    Async wrapper for extract_retreat_details_sync.

    For use in async scrapers.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        extract_retreat_details_sync,
        html,
        client,
        platform
    )


# =============================================================================
# GUIDE ID GENERATION
# =============================================================================

def generate_guide_id(name: str, profile_url: str = "") -> str:
    """
    Generate unique ID for a guide based on name and profile URL.

    This allows deduplication of guides across retreats.
    """
    import hashlib

    # Normalize name
    name_normalized = name.lower().strip()

    # Include profile URL if available (more unique)
    if profile_url:
        # Extract the path part for consistency
        if "/teachers/" in profile_url:
            path = profile_url.split("/teachers/")[-1]
        elif "/teacher/" in profile_url:
            path = profile_url.split("/teacher/")[-1]
        else:
            path = profile_url

        key = f"{name_normalized}:{path}"
    else:
        key = name_normalized

    # Create hash
    hash_obj = hashlib.sha256(key.encode("utf-8"))
    return hash_obj.hexdigest()[:12]


def enrich_guides_with_ids(guides: list[dict]) -> list[dict]:
    """
    Add guide_id to each guide in the list.
    """
    for guide in guides:
        guide["guide_id"] = generate_guide_id(
            guide.get("name", ""),
            guide.get("profile_url", "")
        )
    return guides


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test with sample HTML
    sample_html = """
    <html>
    <body>
        <section class="event-description">
            <h2>About This Retreat</h2>
            <p>Join us for a transformative 5-day yoga and meditation retreat in beautiful Puerto Escondido.
            Experience daily yoga classes, meditation sessions, and connection with nature.</p>
        </section>

        <section class="retreat-size">
            <h3>Group Size</h3>
            <p>Up to 12 participants</p>
        </section>

        <section class="teachers">
            <h2>Your Guides</h2>
            <div class="teacher">
                <img src="https://example.com/sarah.jpg" />
                <h3><a href="/teachers/123/sarah-jones">Sarah Jones</a></h3>
                <p class="role">Lead Yoga Instructor</p>
                <p class="bio">Sarah has been teaching yoga for 15 years. She holds certifications in Vinyasa and Hatha yoga.</p>
            </div>
            <div class="teacher">
                <img src="https://example.com/mike.jpg" />
                <h3><a href="/teachers/456/mike-chen">Mike Chen</a></h3>
                <p class="role">Meditation Guide</p>
                <p class="bio">Mike is a certified meditation teacher with 10 years of practice.</p>
            </div>
        </section>
    </body>
    </html>
    """

    print("=" * 70)
    print("AI EXTRACTION TEST")
    print("=" * 70)

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("\nNo OPENAI_API_KEY found. Set it to test AI extraction.")
        print("\nTesting HTML preprocessing only...")
        print("-" * 70)

        relevant = extract_relevant_sections(sample_html, "retreat.guru")
        print(f"Extracted {len(relevant)} characters of relevant HTML")
        print(relevant[:500])
    else:
        print("\nTesting with OpenAI API...")
        print("-" * 70)

        client = OpenAI(api_key=api_key)
        result = extract_retreat_details_sync(sample_html, client, "retreat.guru")

        print(f"Description: {result['description']}")
        print(f"Group Size: {result['group_size']}")
        print(f"Guides: {len(result['guides'])}")
        for guide in result['guides']:
            print(f"  - {guide.get('name')}: {guide.get('role')}")

    print("\n" + "=" * 70)
