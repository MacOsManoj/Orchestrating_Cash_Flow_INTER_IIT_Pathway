#!/usr/bin/env python3
"""
Test Smart News Scraper Integration
Verifies that the smart news scraper works as a tool
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load .env from project root
load_dotenv(dotenv_path=project_root / ".env")

from tools.news_scraper_tool import NewsScraperTool
from schemas_v2 import ToolType


async def test_smart_news_scraper():
    """Test the smart news scraper integration"""
    print("\n" + "=" * 80)
    print(" TESTING SMART NEWS SCRAPER INTEGRATION")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("NEWSDATA_API_KEY")
    if not api_key:
        print("\n  NEWSDATA_API_KEY not set")
        print("   Tool will use mock data mode")
        print("   To enable: export NEWSDATA_API_KEY='your-key'")
    else:
        print(f"\n NEWSDATA_API_KEY found: {api_key[:10]}...")

    # Initialize tool
    print("\nInitializing NewsScraperTool...")
    tool = NewsScraperTool(cache_dir="files-mock/cache", newsdata_api_key=api_key)
    print(" Tool initialized")

    if not tool.newspaper4k_available:
        print("  Smart scraper not available, will use mock data")

    # Test queries
    test_keywords = [
        ["RBI", "interest", "rate"],
        ["Indian", "bond", "market"],
        ["corporate", "bonds", "yield"],
    ]

    for i, keywords in enumerate(test_keywords, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: Keywords: {', '.join(keywords)}")
        print(f"{'=' * 80}")

        try:
            print(f"\n Scraping news...")
            result = await tool.scrape_news(
                keywords=keywords, max_articles=5, hours_back=24
            )

            print(f"\n Scraping completed")
            print(f"   Success: {result.success}")
            print(f"   Tool Type: {result.tool_type}")
            print(f"   Cached: {result.cached}")

            if result.success:
                articles = result.data
                print(f"   Articles: {len(articles)}")

                # Display first article
                if articles:
                    article = articles[0]
                    print(f"\n   First Article:")
                    print(f"      Title: {article.title[:60]}...")
                    print(f"      Source: {article.source}")
                    print(f"      Sentiment: {article.sentiment_score:+.2f}")
                    print(f"      Relevance: {article.relevance_score:.2f}")
                    print(f"      Entities: {', '.join(article.entities[:5])}")
                    if article.published_at:
                        print(f"      Published: {article.published_at}")
            else:
                print(f"   Error: {result.error}")

        except Exception as e:
            print(f"\n Exception during scraping: {e}")
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("SMART NEWS SCRAPER INTEGRATION TEST COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(test_smart_news_scraper())
