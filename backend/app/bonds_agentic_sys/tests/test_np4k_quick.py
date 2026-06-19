#!/usr/bin/env python3
"""
Quick test script for Newspaper4K tool
Simple test to verify the tool works
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from tools.np4kvesion import search_news_newspaper


async def test():
    """Quick test of Newspaper4K tool"""
    print(" Testing Newspaper4K tool...")
    print("=" * 60)

    query = "RBI interest rate India"
    print(f"Query: {query}")
    print(f"{'─' * 60}\n")

    try:
        result = await search_news_newspaper(query, target_count=3)

        if result:
            print(f" Success!")
            print(f"  Time: {result.get('time', 0):.2f}s")
            print(f"  Articles: {result.get('count', 0)}")

            articles = result.get("articles", [])
            if articles:
                print(f"\n📰 Articles found:")
                for idx, article in enumerate(articles, 1):
                    print(f"\n  Article #{idx}:")
                    print(f"    Source: {article.get('source', 'Unknown')}")
                    print(f"    URL: {article.get('url', 'N/A')}")
                    print(f"    Word Count: {article.get('word_count', 0)}")
                    content = article.get("content", "")
                    if content:
                        preview = (
                            content[:150] + "..." if len(content) > 150 else content
                        )
                        print(f"    Preview: {preview}")
            else:
                print("    No articles returned")
        else:
            print(" No result returned")

    except Exception as e:
        print(f" Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
