#!/usr/bin/env python3
"""
Test script for Web Search Tool
Tests the web search functionality specifically
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

from tools.web_search_tool import WebSearchTool
from schemas_v2 import ToolType


async def test_web_search_tool():
    """Test the web search tool"""
    print("\n" + "=" * 80)
    print(" TESTING WEB SEARCH TOOL")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("\n  SERPAPI_KEY not set")
        print("   Web search will fail, but we'll test error handling")
        print("   To enable: export SERPAPI_KEY='your-key'")
        print("   Or create a .env file with: SERPAPI_KEY=your-key")
    else:
        print(f"\n SERPAPI_KEY found: {api_key[:10]}...")

    # Initialize tool
    print("\nInitializing WebSearchTool...")
    tool = WebSearchTool(api_key=api_key)
    print(" Tool initialized")

    # Test queries
    test_queries = [
        "Indian bond market outlook 2024",
        "RBI interest rate policy",
        "corporate bonds yield forecast",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: {query}")
        print(f"{'=' * 80}")

        try:
            print(f"\n Performing web search...")
            result = await tool.search(query=query, num_results=5)

            print(f"\n Search completed")
            print(f"   Success: {result.success}")
            print(f"   Tool Type: {result.tool_type}")

            if result.success:
                print(f"   Results: {len(result.data)} items")

                # Display results
                for j, item in enumerate(result.data[:3], 1):
                    print(f"\n   Result {j}:")
                    print(f"      Title: {item.get('title', 'N/A')[:80]}...")
                    print(f"      URL: {item.get('url', 'N/A')[:60]}...")
                    print(f"      Snippet: {item.get('snippet', 'N/A')[:100]}...")
                    if item.get("source"):
                        print(f"      Source: {item.get('source')}")
            else:
                print(f"   Error: {result.error}")
                if "not configured" in result.error.lower():
                    print("     This is expected if SERPAPI_KEY is not set")
                elif "not installed" in result.error.lower():
                    print("     Install with: pip install google-search-results")
                else:
                    print(f"     Unexpected error")

        except Exception as e:
            print(f"\n Exception during search: {e}")
            import traceback

            traceback.print_exc()

    # Test edge cases
    print(f"\n{'=' * 80}")
    print("TESTING EDGE CASES")
    print(f"{'=' * 80}")

    # Test empty query
    print("\n Test: Empty query")
    result = await tool.search(query="", num_results=5)
    print(f"   Success: {result.success} (should be False)")
    print(f"   Error: {result.error}")

    # Test invalid num_results
    print("\n Test: Invalid num_results (should clamp)")
    result = await tool.search(query="test", num_results=200)  # Should clamp to 100
    print(f"   Success: {result.success}")
    if result.success:
        print(f"   Results: {len(result.data)} items (should be <= 100)")

    print(f"\n{'=' * 80}")
    print("WEB SEARCH TOOL TEST COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(test_web_search_tool())
