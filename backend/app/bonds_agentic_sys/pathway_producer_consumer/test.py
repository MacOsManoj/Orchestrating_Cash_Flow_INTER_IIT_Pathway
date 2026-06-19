"""
MCP Server Test Client - Bond Forecasting System
Tests all 13 tools exposed by the Pathway MCP server
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
        client = Client(MCP_URL)
        async with client:
            print(f"✓ Successfully connected to {MCP_URL}")
            return True
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Is the server running? (python bond_server.py)")
        print(f"  2. Is it listening on {MCP_URL}?")
        print(f"  3. Check server logs for errors")
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

            print(f"\n✓ Found {len(tools)} tools:")
            for i, tool in enumerate(tools, 1):
                print(f"  {i:2d}. {tool.name}")

            expected_tools = [
                "get_latest_yields",
                "get_yield_forecast",
                "get_all_yield_forecasts",
                "get_bond_price",
                "list_bonds",
                "search_bonds",
                "get_bond_info",
                "calculate_bond_ytm",
                "calculate_bond_duration",
                "filter_bonds",
                "compare_bonds",
                "get_yield_curve",
                "recommend_bonds",
            ]

            tool_names = [t.name for t in tools]
            missing = [t for t in expected_tools if t not in tool_names]
            extra = [t for t in tool_names if t not in expected_tools]

            if missing:
                print(f"\nWARNING: Missing expected tools: {missing}")
            if extra:
                print(f"\nWARNING: Extra tools found: {extra}")

            if not missing and not extra:
                print(f"\n✓ All 13 expected tools are registered!")

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

            if isinstance(data, dict) and "yields" in data:
                yields = data["yields"]
                print(f"\n✓ Retrieved yields for {len(yields)} maturities:")
                for maturity, yield_val in yields.items():
                    print(f"  {maturity}: {yield_val}%")
                print(f"\nLast Update: {data.get('last_update', 'N/A')}")
            else:
                print(f"WARNING: Unexpected response format")

            return result
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return None


async def test_yield_forecast():
    """Test 4: Get yield forecast for specific maturity"""
    print("\n" + "=" * 80)
    print("TEST 4: Get Yield Forecasts")
    print("=" * 80)

    test_cases = [
        {"maturity": 1, "days_ahead": 7},
        {"maturity": 5, "days_ahead": 14},
        {"maturity": 10, "days_ahead": 21},
    ]

    for test_case in test_cases:
        print(
            f"\n--- Testing: {test_case['maturity']}Y, {test_case['days_ahead']} days ---"
        )

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="get_yield_forecast", arguments=test_case
                )

                data = extract_json_from_result(result)
                if isinstance(data, dict) and "forecasts" in data:
                    forecasts = data["forecasts"]
                    print(f"  ✓ Received {len(forecasts)} forecast points")
                    if forecasts:
                        # Sort by day number to ensure chronological order
                        sorted_forecasts = sorted(forecasts, key=lambda x: x["day"])
                        print(
                            f"  First: Day {sorted_forecasts[0]['day']}, Date {sorted_forecasts[0]['date']}, Yield {sorted_forecasts[0]['predicted_yield']}%"
                        )
                        print(
                            f"  Last:  Day {sorted_forecasts[-1]['day']}, Date {sorted_forecasts[-1]['date']}, Yield {sorted_forecasts[-1]['predicted_yield']}%"
                        )
                else:
                    print(f"  WARNING: Response: {data}")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


async def test_all_forecasts():
    """Test 5: Get all yield forecasts at once"""
    print("\n" + "=" * 80)
    print("TEST 5: Get All Yield Forecasts")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(
                name="get_all_yield_forecasts", arguments={}
            )

            data = extract_json_from_result(result)

            if isinstance(data, list):
                print(f"\n✓ Received forecasts for {len(data)} maturities")
                for maturity_data in data:
                    mat = maturity_data.get("maturity")
                    forecast_count = len(maturity_data.get("forecasts", []))
                    print(f"  {mat}: {forecast_count} forecast days")
            else:
                print(f"Response: {data}")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_list_bonds():
    """Test 6: List available bonds"""
    print("\n" + "=" * 80)
    print("TEST 6: List Available Bonds")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(name="list_bonds", arguments={})

            data = extract_json_from_result(result)

            if isinstance(data, dict) and "bonds" in data:
                bonds = data["bonds"]
                total = data.get("total_bonds", len(bonds))
                print(f"\n✓ Total bonds available: {total}")

                if bonds:
                    print(f"\nFirst 5 bonds:")
                    for i, bond in enumerate(bonds[:5], 1):
                        print(
                            f"  {i}. Symbol: {bond.get('symbol')}, ISIN: {bond.get('isin')}"
                        )
                        print(f"     Name: {bond.get('name')}")
                        print(
                            f"     Coupon: {bond.get('coupon_rate')}%, Maturity: {bond.get('maturity_date')}"
                        )
            else:
                print(f"Response: {data}")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_search_bonds():
    """Test 7: Search for bonds"""
    print("\n" + "=" * 80)
    print("TEST 7: Search Bonds")
    print("=" * 80)

    search_terms = ["GS", "2028", "GOI"]

    for term in search_terms:
        print(f"\n--- Searching for: '{term}' ---")

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="search_bonds", arguments={"search_term": term}
                )

                data = extract_json_from_result(result)

                if isinstance(data, dict):
                    matches = data.get("matches", 0)
                    print(f"  ✓ Found {matches} matching bonds")

                    bonds = data.get("bonds", [])
                    for bond in bonds[:3]:  # Show first 3
                        print(f"    - {bond.get('symbol')}: {bond.get('name')}")
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Search failed: {e}")


async def test_bond_info():
    """Test 8: Get detailed bond information"""
    print("\n" + "=" * 80)
    print("TEST 8: Get Bond Information")
    print("=" * 80)

    # Test with first available bond
    print("\nFetching a bond to test with...")

    try:
        # First get a bond identifier
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    bond_identifier = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"Testing with bond: {bond_identifier}")

                    result = await client.call_tool(
                        name="get_bond_info",
                        arguments={
                            "bond_identifier": bond_identifier,
                            "days_ahead": 0,  # Get current info
                        },
                    )

                    data = extract_json_from_result(result)
                    print("\nBond Details:")
                    print(json.dumps(data, indent=2))
                else:
                    print("WARNING: No bonds available to test")
            else:
                print("WARNING: Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_bond_pricing():
    """Test 9: Get bond price forecasts"""
    print("\n" + "=" * 80)
    print("TEST 9: Get Bond Price Forecasts")
    print("=" * 80)

    try:
        # First get a bond identifier
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    bond_identifier = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"\nTesting with bond: {bond_identifier}")

                    # Test 1: Price for specific day
                    print(f"\n--- Pricing for day 7 ---")
                    result = await client.call_tool(
                        name="get_bond_price",
                        arguments={"bond_identifier": bond_identifier, "days_ahead": 7},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "estimated_price" in data:
                        print(
                            f"  ✓ Day {data.get('day')}: ${data.get('estimated_price'):.2f}"
                        )
                        print(f"    Date: {data.get('date')}")
                        print(f"    YTM: {data.get('ytm_percent')}%")
                    else:
                        print(f"  Response: {data}")

                    # Test 2: All forecasts
                    print(f"\n--- Getting all price forecasts ---")
                    result = await client.call_tool(
                        name="get_bond_price",
                        arguments={"bond_identifier": bond_identifier, "days_ahead": 0},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "forecasts" in data:
                        forecasts = data["forecasts"]
                        print(f"  ✓ Received {len(forecasts)} price forecasts")
                        print(f"    Starting price: ${data.get('starting_price'):.2f}")
                        print(f"    Ending price: ${data.get('ending_price'):.2f}")
                        print(
                            f"    Change: ${data.get('price_change'):.2f} ({data.get('pct_change'):.2f}%)"
                        )
                    else:
                        print(f"  Response: {data}")
                else:
                    print("WARNING: No bonds available to test")
            else:
                print("WARNING: Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_calculate_ytm():
    """Test 10: Calculate bond YTM"""
    print("\n" + "=" * 80)
    print("TEST 10: Calculate Bond YTM")
    print("=" * 80)

    try:
        # First get a bond identifier
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    bond_identifier = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"\nCalculating YTM for: {bond_identifier}")

                    result = await client.call_tool(
                        name="calculate_bond_ytm",
                        arguments={"bond_identifier": bond_identifier},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "ytm_percent" in data:
                        print(f"\n✓ Bond: {data.get('bond_name')}")
                        print(f"  YTM: {data.get('ytm_percent')}%")
                        print(f"  Valuation Date: {data.get('valuation_date')}")
                    else:
                        print(f"Response: {data}")
                else:
                    print("WARNING: No bonds available to test")
            else:
                print("WARNING: Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_calculate_duration():
    """Test 11: Calculate bond duration and convexity"""
    print("\n" + "=" * 80)
    print("TEST 11: Calculate Bond Duration & Convexity")
    print("=" * 80)

    try:
        # First get a bond identifier
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    bond_identifier = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"\nCalculating duration for: {bond_identifier}")

                    result = await client.call_tool(
                        name="calculate_bond_duration",
                        arguments={"bond_identifier": bond_identifier},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "macaulay_duration" in data:
                        print(f"\n✓ Bond: {data.get('bond_name')}")
                        print(
                            f"  Macaulay Duration: {data.get('macaulay_duration'):.3f} years"
                        )
                        print(
                            f"  Modified Duration: {data.get('modified_duration'):.3f} years"
                        )
                        print(f"  Convexity: {data.get('convexity'):.3f}")
                        print(f"  Estimated Price: ${data.get('estimated_price'):.2f}")
                    else:
                        print(f"Response: {data}")
                else:
                    print("WARNING: No bonds available to test")
            else:
                print("WARNING: Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_filter_bonds():
    """Test 12: Filter bonds by criteria"""
    print("\n" + "=" * 80)
    print("TEST 12: Filter Bonds")
    print("=" * 80)

    test_filters = [
        {
            "min_coupon": 6.0,
            "max_coupon": 8.0,
            "min_years_to_maturity": 5.0,
            "max_years_to_maturity": 15.0,
            "symbol_contains": "",
            "name_contains": "",
        },
        {
            "min_coupon": 0.0,
            "max_coupon": 0.0,
            "min_years_to_maturity": 0.0,
            "max_years_to_maturity": 0.0,
            "symbol_contains": "GS",
            "name_contains": "",
        },
    ]

    for i, filter_criteria in enumerate(test_filters, 1):
        print(f"\n--- Filter Test {i} ---")
        print(f"Criteria: {filter_criteria}")

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="filter_bonds", arguments=filter_criteria
                )

                data = extract_json_from_result(result)

                if isinstance(data, dict):
                    matches = data.get("total_matches", 0)
                    print(f"  ✓ Found {matches} matching bonds")

                    bonds = data.get("bonds", [])
                    for bond in bonds[:3]:  # Show first 3
                        print(f"    - {bond.get('symbol')}: {bond.get('name')}")
                        print(
                            f"      Coupon: {bond.get('coupon_rate')}%, Maturity: {bond.get('maturity_date')}"
                        )
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Filter failed: {e}")


async def test_compare_bonds():
    """Test 13: Compare multiple bonds"""
    print("\n" + "=" * 80)
    print("TEST 13: Compare Multiple Bonds")
    print("=" * 80)

    try:
        # First get some bond identifiers
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if len(bonds) >= 2:
                    # Get first 2-3 bonds
                    bond_ids = [
                        bonds[0].get("symbol") or bonds[0].get("isin"),
                        bonds[1].get("symbol") or bonds[1].get("isin"),
                    ]
                    if len(bonds) >= 3:
                        bond_ids.append(bonds[2].get("symbol") or bonds[2].get("isin"))

                    identifiers_str = ",".join(bond_ids)

                    print(f"\nComparing bonds: {identifiers_str}")

                    result = await client.call_tool(
                        name="compare_bonds",
                        arguments={"bond_identifiers": identifiers_str},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "bonds" in data:
                        compared = data["bonds"]
                        print(f"\n✓ Comparison Date: {data.get('comparison_date')}")
                        print(f"  Bonds Compared: {data.get('bonds_compared')}")

                        print("\nComparison Results:")
                        for bond in compared:
                            print(f"\n  {bond.get('symbol')}: {bond.get('name')}")
                            print(f"    Coupon: {bond.get('coupon_rate')}%")
                            print(f"    YTM: {bond.get('ytm_percent')}%")
                            print(f"    Price: ${bond.get('price'):.2f}")
                            print(f"    Duration: {bond.get('duration'):.3f} years")
                            print(f"    Convexity: {bond.get('convexity'):.3f}")
                    else:
                        print(f"Response: {data}")
                else:
                    print("WARNING: Not enough bonds to compare (need at least 2)")
            else:
                print("WARNING: Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_get_yield_curve():
    """Test 14: Get yield curve for specific date"""
    print("\n" + "=" * 80)
    print("TEST 14: Get Yield Curve")
    print("=" * 80)

    test_days = [1, 7, 14, 21]

    for days in test_days:
        print(f"\n--- Yield Curve for Day {days} ---")

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="get_yield_curve", arguments={"days_ahead": days}
                )

                data = extract_json_from_result(result)

                if isinstance(data, dict) and "yield_curve" in data:
                    curve = data["yield_curve"]
                    print(f"  ✓ Date: {data.get('date')}")
                    print(f"  Yield Curve:")
                    for point in curve:
                        print(f"    {point.get('maturity')}: {point.get('yield')}%")
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


async def test_recommend_bonds():
    """Test 15: Get bond recommendations"""
    print("\n" + "=" * 80)
    print("TEST 15: Recommend Bonds")
    print("=" * 80)

    test_criteria = [
        {
            "target_yield": 6.5,
            "max_risk": "medium",
            "investment_horizon": 10.0,
            "sort_by": "yield",
        },
        {
            "target_yield": 7.0,
            "max_risk": "low",
            "investment_horizon": 5.0,
            "sort_by": "duration",
        },
    ]

    for i, criteria in enumerate(test_criteria, 1):
        print(f"\n--- Recommendation Test {i} ---")
        print(
            f"Criteria: Target Yield={criteria['target_yield']}%, Risk={criteria['max_risk']}, Horizon={criteria['investment_horizon']} years"
        )

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="recommend_bonds", arguments=criteria
                )

                data = extract_json_from_result(result)

                if isinstance(data, dict) and "recommendations" in data:
                    recs = data["recommendations"]
                    print(
                        f"  ✓ Found {data.get('total_recommendations')} recommendations"
                    )
                    print(f"  Recommendation Date: {data.get('recommendation_date')}")

                    print("\n  Top 3 Recommendations:")
                    for j, rec in enumerate(recs[:3], 1):
                        print(f"\n    {j}. {rec.get('symbol')}: {rec.get('name')}")
                        print(f"       YTM: {rec.get('ytm_percent')}%")
                        print(f"       Price: ${rec.get('estimated_price'):.2f}")
                        print(
                            f"       Duration: {rec.get('modified_duration'):.3f} years"
                        )
                        print(
                            f"       Years to Maturity: {rec.get('years_to_maturity'):.2f}"
                        )
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


async def run_all_tests():
    """Run complete test suite"""
    print("\n" + "=" * 80)
    print("BOND FORECASTING MCP SERVER - COMPREHENSIVE TEST SUITE")
    print("Testing All 13 Tools")
    print("=" * 80)

    if not await test_server_connection():
        return

    await test_list_tools()

    print("\n" + "=" * 80)
    print("YIELD ANALYTICS TESTS")
    print("=" * 80)
    await test_get_latest_yields()
    await test_yield_forecast()
    await test_all_forecasts()
    await test_get_yield_curve()

    print("\n" + "=" * 80)
    print("BOND DISCOVERY & INFO TESTS")
    print("=" * 80)
    await test_list_bonds()
    await test_search_bonds()
    await test_bond_info()

    print("\n" + "=" * 80)
    print("BOND VALUATION TESTS")
    print("=" * 80)
    await test_bond_pricing()
    await test_calculate_ytm()
    await test_calculate_duration()

    print("\n" + "=" * 80)
    print("BOND ANALYSIS & COMPARISON TESTS")
    print("=" * 80)
    await test_filter_bonds()
    await test_compare_bonds()
    await test_recommend_bonds()

    print("\n" + "=" * 80)
    print("✓ TEST SUITE COMPLETE")
    print("=" * 80 + "\n")


async def run_quick_tests():
    """Run quick smoke tests"""
    print("\n" + "=" * 80)
    print("QUICK SMOKE TEST - Testing Core Functionality")
    print("=" * 80)

    if not await test_server_connection():
        return

    await test_list_tools()
    await test_get_latest_yields()
    await test_yield_forecast()
    await test_list_bonds()
    await test_bond_pricing()

    print("\n" + "=" * 80)
    print("✓ QUICK TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(run_quick_tests())
    else:
        asyncio.run(run_all_tests())
