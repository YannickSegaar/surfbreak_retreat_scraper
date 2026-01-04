"""
URL Parser for Retreat Scraping
===============================

Parses search URLs from retreat.guru and bookretreats.com to automatically
generate labels and descriptions for scrape batches.

USAGE:
------
from url_parser import parse_url, generate_label, generate_description

url_data = parse_url("https://retreat.guru/search?topic=yoga&country=mexico")
label = generate_label(url_data)  # "rg-yoga-mexico"
description = generate_description(url_data)  # "Retreats scraped from retreat.guru | Retreat Types: yoga | Locations: mexico"
"""

import re
from urllib.parse import parse_qs, unquote, urlparse


def parse_retreat_guru_url(url: str) -> dict:
    """
    Parse retreat.guru search URL into components.

    Handles parameters:
    - topic: Retreat type (yoga, meditation, wellness, psychedelic, etc.)
    - country: Location country
    - experiences_type: Experience filter (yoga, meditation, ayahuasca, etc.)
    - price_range: Min/max price
    - is_online, is_weekend, is_affordable: Boolean filters

    Example URL:
    https://retreat.guru/search?topic=yoga&topic=meditation&country=mexico&experiences_type=yoga
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    return {
        "platform": "retreat.guru",
        "topics": params.get("topic", []),
        "countries": params.get("country", []),
        "experiences": params.get("experiences_type", []),
        "price_range": params.get("price_range", []),
        "duration_days": params.get("duration_days", []),
        "is_online": "true" in [str(v).lower() for v in params.get("is_online", [])],
        "is_weekend": "true" in [str(v).lower() for v in params.get("is_weekend", [])],
        "is_affordable": "true" in [str(v).lower() for v in params.get("is_affordable", [])],
    }


def parse_bookretreats_url(url: str) -> dict:
    """
    Parse bookretreats.com search URL into components.

    Handles parameters:
    - scopes[type]: Retreat type (e.g., "Yoga Retreats")
    - scopes[location]: Location
    - scopes[category]: Category filter
    - scopes[style]: Style filter
    - facets[popularFilters]: Popular filters like "Women Only"
    - pageNumber: Pagination

    Example URL:
    https://bookretreats.com/search?scopes[type]=Yoga+Retreats&scopes[location]=Mexico&pageNumber=1
    """
    parsed = urlparse(url)
    query = parsed.query

    # bookretreats uses bracket notation which parse_qs doesn't handle well
    # We need to manually parse scopes[type], scopes[location], etc.
    result = {
        "platform": "bookretreats.com",
        "type": "",
        "location": "",
        "category": "",
        "style": "",
        "popular_filters": [],
    }

    # Parse scopes[type]
    type_match = re.search(r'scopes\[type\]=([^&]+)', query)
    if type_match:
        result["type"] = unquote(type_match.group(1).replace("+", " "))

    # Parse scopes[location]
    location_match = re.search(r'scopes\[location\]=([^&]+)', query)
    if location_match:
        result["location"] = unquote(location_match.group(1).replace("+", " "))

    # Parse scopes[category]
    category_match = re.search(r'scopes\[category\]=([^&]+)', query)
    if category_match:
        result["category"] = unquote(category_match.group(1).replace("+", " "))

    # Parse scopes[style]
    style_match = re.search(r'scopes\[style\]=([^&]+)', query)
    if style_match:
        result["style"] = unquote(style_match.group(1).replace("+", " "))

    # Parse facets[popularFilters] (can be multiple)
    filter_matches = re.findall(r'facets\[popularFilters\]\[\d*\]=([^&]+)', query)
    result["popular_filters"] = [unquote(f.replace("+", " ")) for f in filter_matches]

    return result


def parse_url(url: str) -> dict:
    """
    Auto-detect platform and parse URL.

    Returns a dict with platform-specific fields.
    """
    if "retreat.guru" in url:
        return parse_retreat_guru_url(url)
    elif "bookretreats.com" in url:
        return parse_bookretreats_url(url)
    else:
        raise ValueError(f"Unknown platform URL: {url}")


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    # Lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)
    return text


def generate_label(url_data: dict) -> str:
    """
    Generate human-readable label from URL data.

    Format: {platform}-{types}-{locations}-{experiences}

    Examples:
    - "rg-yoga-mexico"
    - "rg-yoga-meditation-mexico-united-states"
    - "br-yoga-mexico"
    """
    parts = []

    # Platform prefix
    if url_data["platform"] == "retreat.guru":
        parts.append("rg")
    else:
        parts.append("br")

    # Topics/types (max 2 for readability)
    if url_data.get("topics"):
        topics = [slugify(t) for t in url_data["topics"][:2]]
        parts.append("-".join(topics))
    elif url_data.get("type"):
        # Remove "Retreats" suffix for cleaner labels
        type_clean = url_data["type"].replace(" Retreats", "").replace(" retreats", "")
        parts.append(slugify(type_clean))

    # Location (max 2 countries for readability)
    if url_data.get("countries"):
        countries = [slugify(c) for c in url_data["countries"][:2]]
        parts.append("-".join(countries))
    elif url_data.get("location"):
        parts.append(slugify(url_data["location"]))

    # Experiences (only if different from topics, max 2)
    if url_data.get("experiences"):
        # Filter out experiences that are already in topics
        topics_set = set(t.lower() for t in url_data.get("topics", []))
        unique_exp = [e for e in url_data["experiences"] if e.lower() not in topics_set]
        if unique_exp:
            exps = [slugify(e) for e in unique_exp[:2]]
            parts.append("-".join(exps))

    # Category/style for bookretreats
    if url_data.get("category"):
        cat_clean = url_data["category"].replace(" Retreats", "").replace(" retreats", "")
        parts.append(slugify(cat_clean))

    return "-".join(parts)


def generate_description(url_data: dict) -> str:
    """
    Generate rich text description of what was scraped.

    This is stored in the CSV and can be displayed in Airtable
    to explain what filters were used for this batch.

    Example output:
    "Retreats scraped from retreat.guru | Retreat Types: yoga, meditation | Experiences: ayahuasca, psilocybin | Locations: Mexico, Costa Rica"
    """
    if url_data["platform"] == "retreat.guru":
        platform_name = "retreat.guru"
    else:
        platform_name = "BookRetreats.com"

    parts = [f"Retreats scraped from {platform_name}"]

    # Retreat types/topics
    if url_data.get("topics"):
        topics_str = ", ".join(url_data["topics"])
        parts.append(f"Retreat Types: {topics_str}")
    elif url_data.get("type"):
        parts.append(f"Type: {url_data['type']}")

    # Category (bookretreats)
    if url_data.get("category"):
        parts.append(f"Category: {url_data['category']}")

    # Style (bookretreats)
    if url_data.get("style"):
        parts.append(f"Style: {url_data['style']}")

    # Experiences
    if url_data.get("experiences"):
        exp_str = ", ".join(url_data["experiences"])
        parts.append(f"Experiences: {exp_str}")

    # Locations
    if url_data.get("countries"):
        countries_str = ", ".join(url_data["countries"])
        parts.append(f"Locations: {countries_str}")
    elif url_data.get("location"):
        parts.append(f"Location: {url_data['location']}")

    # Price range
    if url_data.get("price_range") and len(url_data["price_range"]) >= 2:
        min_price = url_data["price_range"][0]
        max_price = url_data["price_range"][1]
        parts.append(f"Price Range: ${min_price} - ${max_price}")

    # Boolean filters
    filters = []
    if url_data.get("is_online"):
        filters.append("Online")
    if url_data.get("is_weekend"):
        filters.append("Weekend")
    if url_data.get("is_affordable"):
        filters.append("Affordable")
    if url_data.get("popular_filters"):
        filters.extend(url_data["popular_filters"])
    if filters:
        parts.append(f"Filters: {', '.join(filters)}")

    return " | ".join(parts)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test URLs
    test_urls = [
        # Simple retreat.guru
        "https://retreat.guru/search?topic=yoga&country=mexico",

        # Complex retreat.guru with multiple filters
        "https://retreat.guru/search?topic=yoga&topic=meditation&topic=wellness&topic=psychedelic&country=mexico&country=united-states&country=colombia&country=guatemala&country=peru&country=costa-rica&price_range=0&price_range=3000&experiences_type=yoga&experiences_type=meditation&experiences_type=ayahuasca&experiences_type=psilocybin&experiences_type=breathwork",

        # retreat.guru with experiences
        "https://retreat.guru/search?topic=yoga&country=mexico&experiences_type=yoga",

        # Simple bookretreats
        "https://bookretreats.com/search?scopes%5Btype%5D=Yoga+Retreats&scopes%5Blocation%5D=Mexico&pageNumber=1",

        # Complex bookretreats
        "https://bookretreats.com/search?scopes%5Btype%5D=Yoga+Retreats&scopes%5Bcategory%5D=Affordable+Yoga+Retreats&scopes%5Bstyle%5D=General+Yoga&scopes%5Blocation%5D=Mexico&facets%5BpopularFilters%5D%5B0%5D=Women+Only&pageNumber=1",
    ]

    print("=" * 70)
    print("URL PARSER TEST")
    print("=" * 70)

    for url in test_urls:
        print(f"\n{'=' * 70}")
        print(f"URL: {url[:80]}...")
        print("-" * 70)

        try:
            url_data = parse_url(url)
            label = generate_label(url_data)
            description = generate_description(url_data)

            print(f"Platform: {url_data['platform']}")
            print(f"Label: {label}")
            print(f"Description: {description}")
        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 70)
