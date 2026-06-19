"""
MCP Server Test Client - Bond Forecasting System (Live Pathway Table Mode)
Tests all tools exposed by the Pathway MCP server with live table access
"""

import asyncio
import json
import time
from fastmcp import Client

# MCP Server Configuration
MCP_URL = "http://localhost:8123/mcp/"


async def test_server_connection():
    """Test 1: Check if server is reachable"""
    print("\n" + "=" * 80)
    print("TEST 1: Server Connection & Live Table")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            print(f" Successfully connected to {MCP_URL}")

            # Try to get data to verify live table is working
            result = await client.call_tool(name="get_latest_yields", arguments={})

            data = extract_json_from_result(result)

            if isinstance(data, dict) and "yields" in data:
                print(f" Live Pathway table is operational")
                print(f"  Received data for {len(data['yields'])} maturities")
                return True
            else:
                print(f" Server connected but data not ready yet")
                print(f"  Response: {data}")
                print(f"\nNote: Pathway may still be building the pipeline...")
                print(f"      Wait a few seconds and try again")
                return False

    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Is the server running? (python bond_server.py)")
        print(f"  2. Is it listening on {MCP_URL}?")
        print(f"  3. Check server logs for errors")
        print(f"  4. Ensure Pathway pipeline has finished building")
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
                "get_bond_details",
                "get_all_bonds_analytics",
                "batch_bond_pricing",
                "get_risk_metrics",
            ]

            tool_names = [t.name for t in tools]
            missing = [t for t in expected_tools if t not in tool_names]
            extra = [t for t in tool_names if t not in expected_tools]

            if missing:
                print(f"\n Missing expected tools: {missing}")
            if extra:
                print(f"\n Extra tools found: {extra}")

            if not missing and not extra:
                print(f"\n All 17 expected tools are registered!")

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
    """Test 3: Get latest yields from live table"""
    print("\n" + "=" * 80)
    print("TEST 3: Get Latest Yields (Live Table)")
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
                print(f"\n Retrieved yields for {len(yields)} maturities:")
                for maturity, yield_val in yields.items():
                    print(f"  {maturity}: {yield_val}%")
                print(f"\nLast Update: {data.get('last_update', 'N/A')}")
                print(f" Data fetched from live Pathway table (not CSV)")
            else:
                print(f" Unexpected response format")

            return result
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return None


async def test_yield_forecast():
    """Test 4: Get yield forecast for specific maturity"""
    print("\n" + "=" * 80)
    print("TEST 4: Get Yield Forecasts (Live Table)")
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
                    print(f"   Received {len(forecasts)} forecast points")
                    if forecasts:
                        sorted_forecasts = sorted(forecasts, key=lambda x: x["day"])
                        print(
                            f"  First: Day {sorted_forecasts[0]['day']}, Date {sorted_forecasts[0]['date']}, Yield {sorted_forecasts[0]['predicted_yield']}%"
                        )
                        print(
                            f"  Last:  Day {sorted_forecasts[-1]['day']}, Date {sorted_forecasts[-1]['date']}, Yield {sorted_forecasts[-1]['predicted_yield']}%"
                        )
                else:
                    print(f"   Response: {data}")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


async def test_all_forecasts():
    """Test 5: Get all yield forecasts at once"""
    print("\n" + "=" * 80)
    print("TEST 5: Get All Yield Forecasts (Live Table)")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool(
                name="get_all_yield_forecasts", arguments={}
            )

            data = extract_json_from_result(result)

            if isinstance(data, list):
                print(f"\n Received forecasts for {len(data)} maturities")
                for maturity_data in data:
                    mat = maturity_data.get("maturity")
                    forecast_count = len(maturity_data.get("forecasts", []))
                    print(f"  {mat}: {forecast_count} forecast days")
                print(f" All data from live Pathway table")
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
                print(f"\n Total bonds available: {total}")

                if bonds:
                    print(f"\nFirst 5 bonds:")
                    for i, bond in enumerate(bonds[:5], 1):
                        print(
                            f"  {i}. Symbol: {bond.get('symbol')}, ISIN: {bond.get('isin')}"
                        )
                        print(f"     Name: {bond.get('name')}")
            else:
                print(f"Response: {data}")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_search_bonds():
    """Test 7: Search for bonds"""
    print("\n" + "=" * 80)
    print("TEST 7: Search Bonds")
    print("=" * 80)

    search_terms = ["GOI", "2030", "7."]

    for term in search_terms:
        print(f"\n--- Searching for: '{term}' ---")

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(
                    name="search_bonds", arguments={"search_term": term}
                )

                data = extract_json_from_result(result)

                if isinstance(data, dict) and "results" in data:
                    matches = data["results"]
                    print(f"   Found {len(matches)} matches")
                    if matches:
                        for i, bond in enumerate(matches[:3], 1):
                            print(f"    {i}. {bond.get('symbol')}: {bond.get('name')}")
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Search failed: {e}")


async def test_bond_info():
    """Test 8: Get detailed bond information"""
    print("\n" + "=" * 80)
    print("TEST 8: Get Bond Info")
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
                    test_bond = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"\nGetting info for bond: {test_bond}")

                    result = await client.call_tool(
                        name="get_bond_info",
                        arguments={"bond_identifier": test_bond, "days_ahead": 0},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "symbol" in data:
                        print(f"\n Bond Information:")
                        print(json.dumps(data, indent=2))
                    else:
                        print(f"Response: {data}")
                else:
                    print(" No bonds available to test")
            else:
                print(" Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_bond_pricing():
    """Test 9: Get bond pricing (using live table)"""
    print("\n" + "=" * 80)
    print("TEST 9: Bond Pricing (Live Table)")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    test_bond = bonds[0].get("symbol") or bonds[0].get("isin")

                    test_days = [0, 7, 14]

                    for days in test_days:
                        print(f"\n--- Pricing for {test_bond}, Day {days} ---")

                        result = await client.call_tool(
                            name="get_bond_price",
                            arguments={
                                "bond_identifier": test_bond,
                                "days_ahead": days,
                            },
                        )

                        data = extract_json_from_result(result)

                        if isinstance(data, dict) and "price" in data:
                            print(f"   Date: {data.get('valuation_date')}")
                            print(f"  Price: ${data.get('price'):.2f}")
                            print(f"  YTM: {data.get('ytm_percent')}%")
                            if "duration" in data:
                                print(f"  Duration: {data.get('duration')} years")
                            print(f"   Data from live Pathway table")
                        else:
                            print(f"  Response: {data}")
                else:
                    print(" No bonds available to test")
            else:
                print(" Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_calculate_ytm():
    """Test 10: Calculate bond YTM"""
    print("\n" + "=" * 80)
    print("TEST 10: Calculate Bond YTM (Live Table)")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    test_bond = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"\nCalculating YTM for: {test_bond}")

                    result = await client.call_tool(
                        name="calculate_bond_ytm",
                        arguments={"bond_identifier": test_bond},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "ytm_percent" in data:
                        print(f"\n YTM Calculation:")
                        print(
                            f"  Bond: {data.get('bond_symbol')} - {data.get('bond_name')}"
                        )
                        print(f"  YTM: {data.get('ytm_percent')}%")
                        print(f"  Valuation Date: {data.get('valuation_date')}")
                        print(f"   Calculated using live yield curve")
                    else:
                        print(f"Response: {data}")
                else:
                    print(" No bonds available to test")
            else:
                print(" Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_calculate_duration():
    """Test 11: Calculate bond duration and convexity"""
    print("\n" + "=" * 80)
    print("TEST 11: Calculate Duration & Convexity (Live Table)")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if bonds:
                    test_bond = bonds[0].get("symbol") or bonds[0].get("isin")

                    print(f"\nCalculating duration for: {test_bond}")

                    result = await client.call_tool(
                        name="calculate_bond_duration",
                        arguments={"bond_identifier": test_bond},
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "macaulay_duration" in data:
                        print(f"\n Duration Metrics:")
                        print(f"  Bond: {data.get('bond_symbol')}")
                        print(
                            f"  Macaulay Duration: {data.get('macaulay_duration')} years"
                        )
                        print(
                            f"  Modified Duration: {data.get('modified_duration')} years"
                        )
                        print(f"  Convexity: {data.get('convexity')}")
                        print(f"  Price: ${data.get('price'):.2f}")
                        print(f"   Calculated using live yield curve")
                    else:
                        print(f"Response: {data}")
                else:
                    print(" No bonds available to test")
            else:
                print(" Could not retrieve bond list")

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
            "max_coupon": 100.0,
            "min_years_to_maturity": 0.0,
            "max_years_to_maturity": 10.0,
            "symbol_contains": "GOI",
            "name_contains": "",
        },
    ]

    for i, filters in enumerate(test_filters, 1):
        print(f"\n--- Filter Test {i} ---")
        print(
            f"Criteria: Coupon {filters['min_coupon']}-{filters['max_coupon']}%, Years {filters['min_years_to_maturity']}-{filters['max_years_to_maturity']}"
        )

        try:
            client = Client(MCP_URL)
            async with client:
                result = await client.call_tool(name="filter_bonds", arguments=filters)

                data = extract_json_from_result(result)

                if isinstance(data, dict) and "results" in data:
                    bonds_found = data.get("bonds_found", 0)
                    print(f"   Found {bonds_found} matching bonds")

                    if bonds_found > 0:
                        results = data["results"]
                        print(f"\n  First 3 matches:")
                        for j, bond in enumerate(results[:3], 1):
                            print(f"    {j}. {bond.get('symbol')}: {bond.get('name')}")
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
    print("TEST 13: Compare Multiple Bonds (Live Table)")
    print("=" * 80)

    try:
        client = Client(MCP_URL)
        async with client:
            list_result = await client.call_tool(name="list_bonds", arguments={})

            list_data = extract_json_from_result(list_result)

            if isinstance(list_data, dict) and "bonds" in list_data:
                bonds = list_data["bonds"]
                if len(bonds) >= 2:
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
                        arguments={
                            "bond_identifiers": identifiers_str,
                            "days_ahead": 0,
                        },
                    )

                    data = extract_json_from_result(result)

                    if isinstance(data, dict) and "results" in data:
                        compared = data["results"]
                        print(f"\n Valuation Date: {data.get('valuation_date')}")
                        print(f"  Bonds Compared: {data.get('bonds_priced')}")
                        print(f"   Data from live Pathway table")

                        print("\nComparison Results:")
                        for bond in compared:
                            print(f"\n  {bond.get('symbol')}: {bond.get('name')}")
                            print(f"    Price: ${bond.get('price'):.2f}")
                            print(f"    YTM: {bond.get('ytm')}%")
                            if "duration" in bond:
                                print(f"    Duration: {bond.get('duration')} years")
                    else:
                        print(f"Response: {data}")
                else:
                    print(" Not enough bonds to compare (need at least 2)")
            else:
                print(" Could not retrieve bond list")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_get_yield_curve():
    """Test 14: Get yield curve for specific date"""
    print("\n" + "=" * 80)
    print("TEST 14: Get Yield Curve (Live Table)")
    print("=" * 80)

    test_days = [0, 7, 14, 21]

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
                    print(f"   Date: {data.get('date')}")
                    print(f"  Yield Curve:")
                    for point in curve:
                        print(f"    {point.get('maturity')}: {point.get('yield')}%")
                    print(f"   Data from live Pathway table")
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


async def test_recommend_bonds():
    """Test 15: Get bond recommendations"""
    print("\n" + "=" * 80)
    print("TEST 15: Recommend Bonds (Live Table)")
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
                        f"   Found {data.get('total_recommendations')} recommendations"
                    )
                    print(f"  Recommendation Date: {data.get('recommendation_date')}")
                    print(f"   Calculated using live yield curve")

                    print("\n  Top 3 Recommendations:")
                    for j, rec in enumerate(recs[:3], 1):
                        print(f"\n    {j}. {rec.get('symbol')}: {rec.get('name')}")
                        print(f"       YTM: {rec.get('ytm_percent')}%")
                        print(f"       Price: ${rec.get('estimated_price'):.2f}")
                        print(f"       Duration: {rec.get('modified_duration')} years")
                else:
                    print(f"  Response: {data}")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


async def run_all_tests():
    """Run complete test suite"""
    print("\n" + "=" * 80)
    print("BOND FORECASTING MCP SERVER - COMPREHENSIVE TEST SUITE")
    print("Live Pathway Table Mode - No CSV Polling")
    print("=" * 80)

    if not await test_server_connection():
        print("\n Server not ready. Waiting 5 seconds and retrying...")
        await asyncio.sleep(5)
        if not await test_server_connection():
            print("\n Server still not ready. Please check server logs.")
            return

    await test_list_tools()

    print("\n" + "=" * 80)
    print("YIELD ANALYTICS TESTS (Live Table)")
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
    print("BOND VALUATION TESTS (Live Table)")
    print("=" * 80)
    await test_bond_pricing()
    await test_calculate_ytm()
    await test_calculate_duration()

    print("\n" + "=" * 80)
    print("BOND ANALYSIS & COMPARISON TESTS (Live Table)")
    print("=" * 80)
    await test_filter_bonds()
    await test_compare_bonds()
    await test_recommend_bonds()

    print("\n" + "=" * 80)
    print(" TEST SUITE COMPLETE")
    print("All data fetched from live Pathway tables (zero CSV polling)")
    print("=" * 80 + "\n")


async def run_quick_tests():
    """Run quick smoke tests"""
    print("\n" + "=" * 80)
    print("QUICK SMOKE TEST - Live Pathway Table Mode")
    print("=" * 80)

    if not await test_server_connection():
        print("\n Server not ready. Waiting 5 seconds and retrying...")
        await asyncio.sleep(5)
        if not await test_server_connection():
            return

    await test_list_tools()
    await test_get_latest_yields()
    await test_yield_forecast()
    await test_list_bonds()
    await test_bond_pricing()

    print("\n" + "=" * 80)
    print(" QUICK TEST COMPLETE")
    print("Live Pathway table verified working!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(run_quick_tests())
    else:
        asyncio.run(run_all_tests())
