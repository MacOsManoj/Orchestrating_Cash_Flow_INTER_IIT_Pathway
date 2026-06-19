"""
Test MCP Server for Financial News Tool
Run this to test if the tool works properly
"""

import asyncio
import json
from datetime import datetime
from news_tool import create_tool, TOOL_SCHEMA, BATCH_TOOL_SCHEMA


# Simple mock MCP server for testing
class TestMCPServer:
    def __init__(self, api_key: str):
        self.news_tool = create_tool(api_key)
        self.tools = {
            "search_financial_news": TOOL_SCHEMA,
            "get_latest_news_batch": BATCH_TOOL_SCHEMA,
        }

    def list_tools(self):
        """List available tools"""
        print("\n" + "=" * 70)
        print("AVAILABLE TOOLS")
        print("=" * 70)
        for name, schema in self.tools.items():
            print(f"\n[{name}]")
            print(f"  Description: {schema['description']}")
            print(f"  Parameters: {json.dumps(schema['parameters'], indent=4)}")
        print("\n" + "=" * 70)

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a tool with arguments"""
        print(f"\n{'=' * 70}")
        print(f"CALLING TOOL: {tool_name}")
        print(f"{'=' * 70}")
        print(f"Arguments: {json.dumps(arguments, indent=2)}")
        print()

        start_time = datetime.now()

        try:
            if tool_name == "search_financial_news":
                result = self.news_tool.search_news(
                    query=arguments.get("query"),
                    max_articles=arguments.get("max_articles", 5),
                    verbose=arguments.get("verbose", False),
                )

            elif tool_name == "get_latest_news_batch":
                result = self.news_tool.get_latest_news(
                    stocks=arguments.get("stocks"),
                    max_articles_per_stock=arguments.get("max_articles_per_stock", 3),
                )

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

            elapsed = (datetime.now() - start_time).total_seconds()

            print(f"\n{'=' * 70}")
            print(f"RESULT (completed in {elapsed:.1f}s)")
            print(f"{'=' * 70}")
            print(json.dumps(result, indent=2, default=str))
            print("\n" + "=" * 70)

            return result

        except Exception as e:
            print(f"\n[ERROR] {str(e)}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}


async def run_tests(api_key: str):
    """Run test scenarios"""
    server = TestMCPServer(api_key)

    print("\n" + "#" * 70)
    print("# FINANCIAL NEWS TOOL - TEST SERVER")
    print("#" * 70)

    # Show available tools
    server.list_tools()

    # Test 1: Single stock search
    print("\n\n" + "#" * 70)
    print("# TEST 1: Search Single Stock")
    print("#" * 70)

    await server.call_tool(
        tool_name="search_financial_news",
        arguments={"query": "Reliance Industries", "max_articles": 3, "verbose": True},
    )

    # Test 2: Niche stock (Britannia)
    print("\n\n" + "#" * 70)
    print("# TEST 2: Search Niche Stock (Tests Fallback)")
    print("#" * 70)

    await server.call_tool(
        tool_name="search_financial_news",
        arguments={"query": "Britannia", "max_articles": 2, "verbose": True},
    )

    # Test 3: Batch search
    print("\n\n" + "#" * 70)
    print("# TEST 3: Batch Search Multiple Stocks")
    print("#" * 70)

    await server.call_tool(
        tool_name="get_latest_news_batch",
        arguments={"stocks": ["Reliance", "HDFC Bank"], "max_articles_per_stock": 2},
    )

    print("\n\n" + "#" * 70)
    print("# ALL TESTS COMPLETED")
    print("#" * 70)


def main():
    """Main entry point"""
    # Your API key
    API_KEY = "pub_4794bcd33ee04c3bb0289ce6cf08febd"

    print("\nStarting test server...")
    print(f"API Key: {API_KEY[:20]}...")

    # Run async tests
    asyncio.run(run_tests(API_KEY))


if __name__ == "__main__":
    main()
