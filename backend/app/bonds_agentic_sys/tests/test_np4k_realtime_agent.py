#!/usr/bin/env python3
"""
Test script for Newspaper4K tool integration with Real-Time Info Agent
Tests both direct tool usage and agent integration
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

# Import the Newspaper4K tool
from tools.np4kvesion import search_news_newspaper

# Import real-time info agent
from agents.realtime_info_agent import create_realtime_info_agent

# Import tools for direct testing
from tools.tools_manager import create_web_search, create_news_scraper
from schemas_v2 import ToolResult, ToolType


def print_section(title: str, char: str = "="):
    """Print a formatted section header"""
    print(f"\n{char * 60}")
    print(f"{title:^60}")
    print(f"{char * 60}\n")


def print_article(article: dict, index: int):
    """Print a single article in a formatted way"""
    print(f"\n{'─' * 60}")
    print(f"Article #{index + 1}")
    print(f"{'─' * 60}")
    print(f"Source: {article.get('source', 'Unknown')}")
    print(f"URL: {article.get('url', 'N/A')}")
    print(f"Date: {article.get('date', 'N/A')}")
    print(f"Word Count: {article.get('word_count', 0)}")

    content = article.get("content", "")
    if content:
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"\nContent Preview:\n{preview}")


async def test_newspaper4k_direct():
    """Test the Newspaper4K tool directly with a single query"""
    print_section("TEST 1: DIRECT NEWSPAPER4K TOOL TEST", "=")

    query = "RBI interest rate India"
    print(f" Testing query: '{query}'")
    print(f"{'─' * 60}\n")

    try:
        start_time = datetime.now()
        result = await search_news_newspaper(query, target_count=5)
        elapsed = (datetime.now() - start_time).total_seconds()

        if result:
            print(f" Success! Time: {result.get('time', elapsed):.2f}s")
            print(f"  Articles found: {result.get('count', 0)}")
            print(f"  Total time: {elapsed:.2f}s")

            articles = result.get("articles", [])
            if articles:
                print(f"\n📰 Articles ({len(articles)}):")
                for idx, article in enumerate(articles):
                    print_article(article, idx)
            else:
                print("    No articles returned")
        else:
            print(" No result returned")

    except Exception as e:
        print(f" Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)


async def test_realtime_agent_fetch_news():
    """Test the real-time info agent's fetch_news_direct method"""
    print_section("TEST 2: REAL-TIME INFO AGENT - FETCH NEWS DIRECT", "=")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(" OPENAI_API_KEY not set. Skipping agent test.")
        return

    try:
        # Create real-time info agent
        print("Initializing Real-Time Info Agent...")
        agent = create_realtime_info_agent(api_key=api_key, model="gpt-4o-mini")
        print(" Agent initialized")

        test_queries = ["RBI monetary policy", "bond yields India"]

        for query in test_queries:
            print(f"\n Testing query: '{query}'")
            print(f"{'─' * 60}")

            try:
                start_time = datetime.now()
                articles = await agent.fetch_news_direct(query, target_count=3)
                elapsed = (datetime.now() - start_time).total_seconds()

                if articles:
                    print(f" Success! Time: {elapsed:.2f}s")
                    print(f"  Articles found: {len(articles)}")

                    print(f"\n📰 Articles:")
                    for idx, article in enumerate(articles):
                        print(f"\n{'─' * 60}")
                        print(f"Article #{idx + 1}")
                        print(f"{'─' * 60}")
                        print(f"Title: {article.get('title', 'N/A')}")
                        print(f"Source: {article.get('source', 'Unknown')}")
                        print(f"URL: {article.get('url', 'N/A')}")
                        print(f"Published: {article.get('published_at', 'N/A')}")
                        print(f"Sentiment: {article.get('sentiment_score', 0.0):.2f}")
                        print(f"Relevance: {article.get('relevance_score', 0.0):.2f}")

                        summary = article.get("summary", "")
                        if summary:
                            preview = (
                                summary[:200] + "..." if len(summary) > 200 else summary
                            )
                            print(f"\nSummary:\n{preview}")
                else:
                    print("  No articles returned")

            except Exception as e:
                print(f" Error: {e}")
                import traceback

                traceback.print_exc()

            print("\n" + "=" * 60)

    except Exception as e:
        print(f" Error initializing agent: {e}")
        import traceback

        traceback.print_exc()


def print_tool_result(tool_result: ToolResult, tool_name: str):
    """Print raw tool result in detail"""
    print(f"\n{'─' * 60}")
    print(f"RAW {tool_name} RESULT:")
    print(f"{'─' * 60}")
    print(f"Success: {tool_result.success}")
    print(f"Cached: {tool_result.cached}")
    print(f"Execution Time: {tool_result.execution_time:.2f}s")
    if tool_result.error:
        print(f"Error: {tool_result.error}")

    if tool_result.success and tool_result.data:
        print(f"\nData Type: {type(tool_result.data)}")
        print(
            f"Data Length: {len(tool_result.data) if hasattr(tool_result.data, '__len__') else 'N/A'}"
        )

        if isinstance(tool_result.data, list):
            print(f"\nItems ({len(tool_result.data)}):")
            for idx, item in enumerate(tool_result.data[:3], 1):  # Show first 3
                print(f"\n  Item #{idx}:")
                if isinstance(item, dict):
                    for key, value in list(item.items())[:5]:  # Show first 5 keys
                        if isinstance(value, str) and len(value) > 100:
                            print(f"    {key}: {value[:100]}...")
                        else:
                            print(f"    {key}: {value}")
                else:
                    print(f"    {item}")
            if len(tool_result.data) > 3:
                print(f"  ... and {len(tool_result.data) - 3} more items")
        elif isinstance(tool_result.data, dict):
            print(f"\nKeys: {list(tool_result.data.keys())}")
            for key, value in list(tool_result.data.items())[:5]:  # Show first 5 items
                if isinstance(value, str) and len(value) > 200:
                    print(f"  {key}: {value[:200]}...")
                elif isinstance(value, list):
                    print(f"  {key}: [{len(value)} items]")
                else:
                    print(f"  {key}: {value}")
    print(f"{'─' * 60}\n")


async def test_realtime_agent_full_flow():
    """Test the full real-time info agent flow with raw tool responses"""
    print_section(
        "TEST 3: REAL-TIME INFO AGENT - FULL FLOW WITH RAW TOOL RESPONSES", "="
    )

    api_key = os.getenv("OPENAI_API_KEY")
    serpapi_key = os.getenv("SERPAPI_KEY")

    if not api_key:
        print(" OPENAI_API_KEY not set. Skipping full flow test.")
        return

    try:
        # Create real-time info agent
        print("Initializing Real-Time Info Agent...")
        agent = create_realtime_info_agent(api_key=api_key, model="gpt-4o-mini")
        print(" Agent initialized")

        # Initialize tools
        print("\nInitializing Tools...")
        web_search_tool = create_web_search(api_key=serpapi_key)
        news_scraper_tool = create_news_scraper()
        print(" Tools initialized")

        test_query = "What is the current RBI interest rate policy?"
        test_intent = "analytics"

        print(f"\n Test Query: '{test_query}'")
        print(f"   Intent: {test_intent}")
        print(f"{'─' * 60}")

        # Step 1: Check if real-time info is needed
        print("\n Step 1: Checking if real-time info is needed...")
        decision = await agent.should_gather_realtime_info(test_query, test_intent)
        print(f"   Needs real-time info: {decision.get('needs_realtime_info', False)}")
        print(f"   Reasoning: {decision.get('reasoning', 'N/A')}")
        print(f"   Priority: {decision.get('priority', 'N/A')}")

        if not decision.get("needs_realtime_info", False):
            print("     Real-time info not needed, skipping...")
            return

        # Step 2: Generate search queries
        print("\n Step 2: Generating search queries...")
        search_queries = await agent.generate_search_queries(test_query, test_intent)
        web_search_query = search_queries.get("web_search_query", test_query)
        news_keywords = search_queries.get("news_keywords", [test_query])
        print(f"   Web Search Query: {web_search_query}")
        print(f"   News Keywords: {news_keywords}")

        # Step 3: Execute tools in parallel and get RAW responses
        print("\n Step 3: Executing tools in parallel...")
        print("   (This will show RAW tool responses before agent processing)")

        web_search_task = web_search_tool.search(query=web_search_query, num_results=5)

        news_task = news_scraper_tool.scrape_news(
            keywords=news_keywords, max_articles=5, hours_back=24
        )

        # Execute in parallel
        web_search_result, news_result = await asyncio.gather(
            web_search_task, news_task, return_exceptions=True
        )

        # Handle exceptions
        if isinstance(web_search_result, Exception):
            print(f" Web search error: {web_search_result}")
            web_search_result = None
        else:
            print(" Web search completed")

        if isinstance(news_result, Exception):
            print(f" News scraping error: {news_result}")
            news_result = None
        else:
            print(" News scraping completed")

        # Step 4: Print RAW tool responses
        print("\n" + "=" * 60)
        print("RAW TOOL RESPONSES (Before Agent Processing):")
        print("=" * 60)

        if web_search_result:
            print_tool_result(web_search_result, "WEB SEARCH")
        else:
            print("\n  No web search result available")

        if news_result:
            print_tool_result(news_result, "NEWS SCRAPER")
        else:
            print("\n  No news scraper result available")

        # Step 5: Process real-time info with raw tool results
        print("\n" + "=" * 60)
        print("AGENT PROCESSING:")
        print("=" * 60)
        print("\n Step 4: Processing real-time info with agent...")

        formatted_context = await agent.process_realtime_info(
            query=test_query,
            intent=test_intent,
            web_search_result=web_search_result,
            news_result=news_result,
            use_direct_news=False,  # Use tool results, not direct news
        )

        # Step 6: Print agent response
        print("\n" + "=" * 60)
        print("AGENT RESPONSE:")
        print("=" * 60)

        if formatted_context:
            print(f"\n{formatted_context}\n")
        else:
            print("\n  No formatted context generated")

        print("=" * 60)

    except Exception as e:
        print(f" Error: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run all tests"""
    print_section("NEWSPAPER4K TOOL & REAL-TIME INFO AGENT TEST SUITE", "=")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Direct Newspaper4K tool test (alone)
    await test_newspaper4k_direct()

    # Test 2: Real-time info agent with raw tool responses
    await test_realtime_agent_full_flow()

    print_section("ALL TESTS COMPLETED", "=")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
