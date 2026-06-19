"""
MongoDB Search Config Setup Script
Run this once to seed the config_db.search_config collection with company search queries.

Usage:
    python setup_search_config.py

This creates search queries for each company that combine:
- Company name/aliases
- Risk themes (political, regulatory, economic)
- Negative term filters (to exclude job postings etc.)
"""

import os
from pymongo import MongoClient
from companies import SEARCH_CONFIG

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_CONFIG_DB = os.getenv("MONGODB_CONFIG_DB", "config_db")


def build_company_query(
    company_code: str,
    company_data: dict,
    theme: str,
    theme_query: str,
    negative_terms: str,
) -> str:
    """
    Build a Google News search query for a company + theme combination.

    Example output for TCS + regulatory:
    ("TCS" OR "TCS Ltd" OR "TCS Limited") AND (regulation OR compliance OR ...) -job -jobs -hiring...
    """
    # Build company aliases part: ("TCS" OR "TCS Ltd" OR ...)
    aliases = company_data.get("aliases", [company_code.upper()])
    alias_part = " OR ".join(f'"{alias}"' for alias in aliases)
    company_part = f"({alias_part})"

    # Combine: company AND theme AND negative filters
    query = f"{company_part} AND {theme_query} {negative_terms}"

    return query


def build_all_queries(config: dict) -> dict:
    """
    Build pre-computed search queries for all companies.

    Returns: {
        "companies": {
            "tcs": {
                "aliases": [...],
                "queries": {
                    "political": "...",
                    "regulatory": "...",
                    "economic": "..."
                }
            },
            ...
        }
    }
    """
    negative_terms = config.get("negative_terms", "")
    risk_themes = config.get("risk_themes", {})
    companies = config.get("companies", {})

    result = {"companies": {}}

    for company_code, company_data in companies.items():
        company_queries = {}

        for theme, theme_query in risk_themes.items():
            query = build_company_query(
                company_code, company_data, theme, theme_query, negative_terms
            )
            company_queries[theme] = query

        result["companies"][company_code] = {
            "aliases": company_data.get("aliases", []),
            "queries": company_queries,
        }

    return result


def seed_mongodb():
    """Seed MongoDB with the search configuration"""
    print(f"Connecting to MongoDB at {MONGODB_URI}...")

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    config_db = client[MONGODB_CONFIG_DB]

    # Build all queries
    print("Building search queries for all companies...")
    config_doc = build_all_queries(SEARCH_CONFIG)
    config_doc["_id"] = "search_config_v1"
    config_doc["version"] = "1.0"
    config_doc["description"] = "Pre-built search queries for company news scraping"

    # Upsert the configuration
    config_db.search_config.replace_one(
        {"_id": "search_config_v1"}, config_doc, upsert=True
    )

    # Print summary
    company_count = len(config_doc["companies"])
    theme_count = len(SEARCH_CONFIG.get("risk_themes", {}))
    total_queries = company_count * theme_count

    print(f"\n✅ Successfully seeded MongoDB!")
    print(f"   - Companies: {company_count}")
    print(f"   - Themes per company: {theme_count}")
    print(f"   - Total queries: {total_queries}")
    print(f"\nSample query for 'tcs_financial':")
    if "tcs" in config_doc["companies"]:
        sample = config_doc["companies"]["tcs"]["queries"].get("financial", "N/A")
        print(f"   {sample[:100]}...")

    client.close()


def list_config():
    """List the current config from MongoDB"""
    print(f"Connecting to MongoDB at {MONGODB_URI}...")

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    config_db = client[MONGODB_CONFIG_DB]

    config = config_db.search_config.find_one({"_id": "search_config_v1"})

    if not config:
        print("❌ No search config found. Run: python setup_search_config.py")
        return

    print("\n📋 Current Search Configuration:")
    print(f"   Version: {config.get('version', 'unknown')}")

    companies = config.get("companies", {})
    print(f"   Companies ({len(companies)}):")
    for company_code in sorted(companies.keys()):
        themes = list(companies[company_code].get("queries", {}).keys())
        print(f"      - {company_code}: {themes}")

    client.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_config()
    else:
        seed_mongodb()
