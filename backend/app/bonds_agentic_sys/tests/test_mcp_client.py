"""
MCP Server Test Client
Tests all tools exposed by the Pathway MCP server
"""

import asyncio
import json
from fastmcp import Client

# MCP Server Configuration
MCP_URL = "http://localhost:8123/mcp/"


async def test_server_connection():
    """Test 1: Check if server is reachable"""
    print("\n" + "=" * 80)
    print("TEST 1: Server Connection")
    print("=" * 80)

    try:
        # Note: Client connection in fastmcp is usually managed per call or via context
        # We will test a simple tool list to verify connection
        client = Client(MCP_URL)
        async with client:
            print(f" Successfully connected to {MCP_URL}")
            return True
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Is the server running? (python mcp_bonds.py)")
        print(f"  2. Is it listening on {MCP_URL}?")
        return False


async def test_list_tools():
    """Test 2: List all available tools"""
    print("\n" + "=" * 80)
    print("TEST 2: List Available Tools")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            tools = await client.list_tools()

            print(f"\n Found {len(tools)} tools:")
            for i, tool in enumerate(tools, 1):
                print(f"\n  {i}. {tool.name}")

            expected_tools = [
                "get_latest_yields",
                "calculate_yield_curve_slope",
                "get_yield_forecast",
                "estimate_bond_price",
                "get_model_status",
                "list_available_bonds",
            ]

            tool_names = [t.name for t in tools]
            missing = [t for t in expected_tools if t not in tool_names]

            if missing:
                print(f"\n Missing expected tools: {missing}")
            else:
                print(f"\n All expected tools are registered!")

            return tools
    except Exception as e:
        print(f"✗ Failed to list tools: {e}")
        return None


def extract_json_from_result(result):
    """Helper to extract JSON from MCP content list"""
    if hasattr(result, "content"):
        for item in result.content:
            if hasattr(item, "text"):
                try:
                    return json.loads(item.text)
                except:
                    # If text is not pure JSON, just return raw
                    return item.text
    return result


async def test_get_latest_yields():
    """Test 3: Get latest yield values"""
    print("\n" + "=" * 80)
    print("TEST 3: Get Latest Yields")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(name="get_latest_yields", arguments={})

            data = extract_json_from_result(result)
            print("\nResponse:")
            print(json.dumps(data, indent=2))
            return result
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return None


async def test_yield_curve_slope():
    """Test 4: Calculate yield curve slope"""
    print("\n" + "=" * 80)
    print("TEST 4: Calculate Yield Curve Slope (10Y-2Y)")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(
                name="calculate_yield_curve_slope", arguments={}
            )

            data = extract_json_from_result(result)
            print("\nResponse:")
            print(json.dumps(data, indent=2))

            if isinstance(data, dict) and "slope_10y_2y" in data:
                print(f"\nInterpretation: {data.get('interpretation', 'N/A')}")

            return result
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return None


async def test_yield_forecast():
    """Test 5: Get yield forecast"""
    print("\n" + "=" * 80)
    print("TEST 5: Get Yield Forecast")
    print("=" * 80)

    test_cases = [{"maturity": 10, "days_ahead": 7}, {"maturity": 2, "days_ahead": 14}]

    for test_case in test_cases:
        print(
            f"\n--- Testing: {test_case['maturity']}Y, {test_case['days_ahead']} days ahead ---"
        )

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="get_yield_forecast", arguments=test_case
                )

                data = extract_json_from_result(result)
                if isinstance(data, dict) and "forecasts" in data:
                    print(f"   Received {len(data['forecasts'])} forecast points")
                    print(f"  First: {data['forecasts'][0]}")
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"✗ Test failed: {e}")


async def test_bond_pricing():
    """Test 6: Estimate bond prices"""
    print("\n" + "=" * 80)
    print("TEST 6: Estimate Bond Prices")
    print("=" * 80)

    # 1. Get Bonds
    bond_name = "GS 2028 (High Coupon)"
    try:
        client = Client(MCP_URL)
        async with client:
            res = await client.call_tool("list_available_bonds", arguments={})
            data = extract_json_from_result(res)
            if isinstance(data, dict) and "available_bonds" in data:
                print(f" Found {len(data['available_bonds'])} bonds")
                bond_name = data["available_bonds"][0]["name"]
    except Exception as e:
        print(f"Error listing bonds: {e}")

    # 2. Price Bond
    print(f"\nPricing '{bond_name}' for 7 days ahead...")
    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(
                name="estimate_bond_price",
                arguments={"bond_name": bond_name, "days_ahead": 7},
            )
            data = extract_json_from_result(result)
            print("Response:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error pricing bond: {e}")


async def test_model_status():
    """Test 7: Get model training status"""
    print("\n" + "=" * 80)
    print("TEST 7: Get Model Status")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(name="get_model_status", arguments={})
            data = extract_json_from_result(result)
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"✗ Test failed: {e}")


async def run_all_tests():
    """Run complete test suite"""
    print("\n" + "=" * 80)
    print("PATHWAY MCP SERVER TEST SUITE")
    print("=" * 80)

    if not await test_server_connection():
        return

    await test_list_tools()
    await test_get_latest_yields()
    await test_yield_curve_slope()
    await test_yield_forecast()
    await test_bond_pricing()
    await test_model_status()

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
