#!/usr/bin/env python3
"""Quick test of news scraper tool"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.tools_manager import create_news_scraper


async def test():
    tool = create_news_scraper()
    print(f" Tool created, Newspaper4K scraper available: {tool.newspaper4k_available}")

    result = await tool.scrape_news(keywords=["RBI", "interest"], max_articles=2)
    print(f" Tool works: {result.success}, Articles: {len(result.data)}")
    if result.data:
        print(f"  First article: {result.data[0].title[:50]}...")


if __name__ == "__main__":
    asyncio.run(test())
