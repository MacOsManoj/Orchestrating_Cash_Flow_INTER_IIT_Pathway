#!/usr/bin/env python3
"""
Comprehensive API Endpoint Tester for Forex Trading API

This script tests all endpoints defined in api.py.
Run the API server first: python api.py --port 8000

Usage:
    python test_all_endpoints.py
    python test_all_endpoints.py --base-url http://localhost:8001
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Test data
TEST_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "EURINR", "GBPINR", "JPYINR"]
TEST_PAIR = "EURUSD"
TEST_AMOUNT = 5000

# =============================================================================
# COLORS FOR OUTPUT
# =============================================================================


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}{Colors.ENDC}")


def print_section(text: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}--- {text} ---{Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_fail(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.BLUE}  → {text}{Colors.ENDC}")


# =============================================================================
# HTTP REQUEST HELPER
# =============================================================================


def make_request(
    method: str,
    endpoint: str,
    data: Dict = None,
    params: Dict = None,
    stream: bool = False,
) -> Tuple[bool, int, Any]:
    """
    Make HTTP request and return (success, status_code, response_data)
    """
    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=TIMEOUT, stream=stream)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=TIMEOUT)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, timeout=TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=TIMEOUT)
        else:
            return False, 0, {"error": f"Unsupported method: {method}"}

        if stream:
            return response.status_code < 400, response.status_code, response

        try:
            data = response.json()
        except:
            data = {"raw": response.text}

        return response.status_code < 400, response.status_code, data

    except requests.exceptions.ConnectionError:
        return False, 0, {"error": "Connection refused - is the API running?"}
    except requests.exceptions.Timeout:
        return False, 0, {"error": "Request timed out"}
    except Exception as e:
        return False, 0, {"error": str(e)}


# =============================================================================
# TEST FUNCTIONS
# =============================================================================


def test_endpoint(
    name: str,
    method: str,
    endpoint: str,
    data: Dict = None,
    params: Dict = None,
    expected_fields: List[str] = None,
    show_response: bool = True,
) -> bool:
    """Test a single endpoint"""
    print(f"\n  Testing: {Colors.BOLD}{method} {endpoint}{Colors.ENDC}")

    success, status_code, response = make_request(method, endpoint, data, params)

    if not success:
        print_fail(f"Failed with status {status_code}")
        if isinstance(response, dict) and "error" in response:
            print_info(f"Error: {response['error']}")
        elif isinstance(response, dict) and "detail" in response:
            print_info(f"Detail: {response['detail']}")
        return False

    print_success(f"Status: {status_code}")

    # Check expected fields
    if expected_fields and isinstance(response, dict):
        missing = [f for f in expected_fields if f not in response]
        if missing:
            print_warning(f"Missing fields: {missing}")
        else:
            print_info(f"All expected fields present: {expected_fields}")

    # Show response summary
    if show_response and isinstance(response, dict):
        # Show first few keys/values
        for key in list(response.keys())[:5]:
            value = response[key]
            if isinstance(value, list):
                print_info(f"{key}: [{len(value)} items]")
            elif isinstance(value, dict):
                print_info(f"{key}: {{...}}")
            elif isinstance(value, str) and len(value) > 50:
                print_info(f"{key}: {value[:50]}...")
            else:
                print_info(f"{key}: {value}")

    return True


# =============================================================================
# TEST CATEGORIES
# =============================================================================


def test_health_endpoints() -> List[Tuple[str, bool]]:
    """Test health and status endpoints"""
    print_section("HEALTH & STATUS ENDPOINTS")
    results = []

    # GET /health
    results.append(
        (
            "GET /health",
            test_endpoint(
                "Health Check",
                "GET",
                "/health",
                expected_fields=["status", "timestamp", "version"],
            ),
        )
    )

    # GET /status
    results.append(
        (
            "GET /status",
            test_endpoint(
                "Pipeline Status",
                "GET",
                "/status",
                expected_fields=[
                    "status",
                    "models_trained",
                    "current_signals",
                    "positions",
                ],
            ),
        )
    )

    return results


def test_main_page_endpoints() -> List[Tuple[str, bool]]:
    """Test main page endpoints"""
    print_section("MAIN PAGE ENDPOINTS")
    results = []

    # GET /api/v1/pairs
    results.append(
        (
            "GET /api/v1/pairs",
            test_endpoint(
                "Get Forex Pairs",
                "GET",
                "/api/v1/pairs",
                expected_fields=["pairs", "timestamp"],
            ),
        )
    )

    # GET /api/v1/recommended-trades
    results.append(
        (
            "GET /api/v1/recommended-trades",
            test_endpoint(
                "Get Recommended Trades",
                "GET",
                "/api/v1/recommended-trades",
                expected_fields=["trades", "timestamp"],
            ),
        )
    )

    # GET /api/v1/portfolio
    results.append(
        (
            "GET /api/v1/portfolio",
            test_endpoint(
                "Get Portfolio Summary",
                "GET",
                "/api/v1/portfolio",
                expected_fields=[
                    "total_open_positions",
                    "total_exposure_long",
                    "total_exposure_short",
                    "positions",
                ],
            ),
        )
    )

    # POST /api/v1/portfolio/refresh
    results.append(
        (
            "POST /api/v1/portfolio/refresh",
            test_endpoint(
                "Refresh Portfolio",
                "POST",
                "/api/v1/portfolio/refresh",
                expected_fields=["success", "message"],
            ),
        )
    )

    return results


def test_trade_action_endpoints() -> List[Tuple[str, bool]]:
    """Test trade action endpoints"""
    print_section("TRADE ACTION ENDPOINTS")
    results = []

    # POST /api/v1/trade - BUY
    results.append(
        (
            "POST /api/v1/trade (BUY)",
            test_endpoint(
                "Execute BUY Trade",
                "POST",
                "/api/v1/trade",
                data={"pair": TEST_PAIR, "action": "buy", "amount": TEST_AMOUNT},
                expected_fields=[
                    "success",
                    "pair",
                    "action",
                    "executed_price",
                    "position_after",
                ],
            ),
        )
    )

    # POST /api/v1/trade - SELL
    results.append(
        (
            "POST /api/v1/trade (SELL)",
            test_endpoint(
                "Execute SELL Trade",
                "POST",
                "/api/v1/trade",
                data={"pair": TEST_PAIR, "action": "sell", "amount": TEST_AMOUNT},
                expected_fields=[
                    "success",
                    "pair",
                    "action",
                    "executed_price",
                    "position_after",
                ],
            ),
        )
    )

    # POST /api/v1/trade - HOLD
    results.append(
        (
            "POST /api/v1/trade (HOLD)",
            test_endpoint(
                "Execute HOLD Trade",
                "POST",
                "/api/v1/trade",
                data={"pair": TEST_PAIR, "action": "hold"},
                expected_fields=["success", "pair", "action", "position_after"],
            ),
        )
    )

    # POST /api/v1/positions/update - open_long
    results.append(
        (
            "POST /api/v1/positions/update (open_long)",
            test_endpoint(
                "Update Position - Open Long",
                "POST",
                "/api/v1/positions/update",
                data={"pair": "GBPUSD", "action": "open_long", "size": 10000},
                expected_fields=["success", "pair", "action", "message"],
            ),
        )
    )

    # POST /api/v1/positions/update - close
    results.append(
        (
            "POST /api/v1/positions/update (close)",
            test_endpoint(
                "Update Position - Close",
                "POST",
                "/api/v1/positions/update",
                data={"pair": "GBPUSD", "action": "close"},
                expected_fields=["success", "pair", "action", "message"],
            ),
        )
    )

    return results


def test_currency_page_endpoints() -> List[Tuple[str, bool]]:
    """Test currency page endpoints"""
    print_section("CURRENCY PAGE ENDPOINTS")
    results = []

    for pair in [TEST_PAIR, "USDJPY"]:
        # GET /api/v1/currency/{pair}/price-data
        results.append(
            (
                f"GET /api/v1/currency/{pair}/price-data",
                test_endpoint(
                    f"Get Price Data for {pair}",
                    "GET",
                    f"/api/v1/currency/{pair}/price-data",
                    params={"days": 30},
                    expected_fields=[
                        "pair",
                        "data",
                        "spot_rate",
                        "realized_volatility_10d",
                        "atr_14d",
                    ],
                ),
            )
        )

        # GET /api/v1/currency/{pair}/risk-metrics
        results.append(
            (
                f"GET /api/v1/currency/{pair}/risk-metrics",
                test_endpoint(
                    f"Get Risk Metrics for {pair}",
                    "GET",
                    f"/api/v1/currency/{pair}/risk-metrics",
                    expected_fields=[
                        "pair",
                        "volatility_10d",
                        "volatility_20d",
                        "value_at_risk_95",
                        "strategy_sharpe",
                    ],
                ),
            )
        )

        # GET /api/v1/currency/{pair}/exposure
        results.append(
            (
                f"GET /api/v1/currency/{pair}/exposure",
                test_endpoint(
                    f"Get Exposure for {pair}",
                    "GET",
                    f"/api/v1/currency/{pair}/exposure",
                    expected_fields=[
                        "pair",
                        "current_position",
                        "realized_pnl",
                        "unrealized_pnl",
                        "portfolio_exposure_pct",
                    ],
                ),
            )
        )

    return results


def test_profit_endpoints() -> List[Tuple[str, bool]]:
    """Test profit tracking endpoints"""
    print_section("PROFIT ENDPOINTS")
    results = []

    # GET /api/v1/profits
    results.append(
        (
            "GET /api/v1/profits",
            test_endpoint(
                "Get All Profits",
                "GET",
                "/api/v1/profits",
                expected_fields=[
                    "pairs",
                    "total_portfolio_profit_pct",
                    "best_performing_pair",
                    "worst_performing_pair",
                ],
            ),
        )
    )

    # GET /api/v1/profits/{pair}
    results.append(
        (
            f"GET /api/v1/profits/{TEST_PAIR}",
            test_endpoint(
                f"Get Profit for {TEST_PAIR}",
                "GET",
                f"/api/v1/profits/{TEST_PAIR}",
                expected_fields=[
                    "pair",
                    "total_profit_pct",
                    "total_trades",
                    "win_rate",
                    "profit_history",
                ],
            ),
        )
    )

    # GET /api/v1/profits/{pair}/chart-data
    results.append(
        (
            f"GET /api/v1/profits/{TEST_PAIR}/chart-data",
            test_endpoint(
                f"Get Profit Chart Data for {TEST_PAIR}",
                "GET",
                f"/api/v1/profits/{TEST_PAIR}/chart-data",
                expected_fields=[
                    "pair",
                    "data_points",
                    "starting_capital",
                    "final_capital",
                    "total_return_pct",
                ],
            ),
        )
    )

    return results


def test_analysis_endpoints() -> List[Tuple[str, bool]]:
    """Test analysis endpoints"""
    print_section("ANALYSIS ENDPOINTS")
    results = []

    # GET /api/v1/correlation-matrix
    results.append(
        (
            "GET /api/v1/correlation-matrix",
            test_endpoint(
                "Get Correlation Matrix",
                "GET",
                "/api/v1/correlation-matrix",
                params={"days": 60},
                expected_fields=["pairs", "matrix", "period_days"],
            ),
        )
    )

    # GET /api/v1/trade-records
    results.append(
        (
            "GET /api/v1/trade-records",
            test_endpoint(
                "Get Trade Records",
                "GET",
                "/api/v1/trade-records",
                params={"limit": 20},
                expected_fields=["records", "total_count"],
            ),
        )
    )

    # GET /api/v1/trade-records with pair filter
    results.append(
        (
            f"GET /api/v1/trade-records?pair={TEST_PAIR}",
            test_endpoint(
                f"Get Trade Records for {TEST_PAIR}",
                "GET",
                "/api/v1/trade-records",
                params={"pair": TEST_PAIR, "limit": 10},
                expected_fields=["records", "total_count"],
            ),
        )
    )

    return results


def test_agent_endpoints() -> List[Tuple[str, bool]]:
    """Test agent endpoints"""
    print_section("AGENT ENDPOINTS")
    results = []

    # POST /api/v1/agent/query
    results.append(
        (
            "POST /api/v1/agent/query",
            test_endpoint(
                "Query Agent",
                "POST",
                "/api/v1/agent/query",
                data={"query": "What is the current market regime for EURUSD?"},
                expected_fields=["response", "tools_called", "processing_time_ms"],
            ),
        )
    )

    # GET /api/v1/agent/query/stream - streaming endpoint
    print(f"\n  Testing: {Colors.BOLD}GET /api/v1/agent/query/stream{Colors.ENDC}")
    success, status_code, response = make_request(
        "GET", "/api/v1/agent/query/stream", params={"query": "Hello"}, stream=True
    )
    if success:
        print_success(f"Status: {status_code} (streaming endpoint)")
        results.append(("GET /api/v1/agent/query/stream", True))
    else:
        print_fail(f"Failed with status {status_code}")
        results.append(("GET /api/v1/agent/query/stream", False))

    return results


def test_pipeline_endpoints() -> List[Tuple[str, bool]]:
    """Test pipeline endpoints"""
    print_section("PIPELINE ENDPOINTS")
    results = []

    # GET /api/v1/pipeline/signals
    results.append(
        (
            "GET /api/v1/pipeline/signals",
            test_endpoint(
                "Get Pipeline Signals",
                "GET",
                "/api/v1/pipeline/signals",
                expected_fields=["signals", "timestamp"],
            ),
        )
    )

    # GET /api/v1/pipeline/allocations
    results.append(
        (
            "GET /api/v1/pipeline/allocations",
            test_endpoint(
                "Get Pipeline Allocations",
                "GET",
                "/api/v1/pipeline/allocations",
                expected_fields=["allocations", "timestamp"],
            ),
        )
    )

    # POST /api/v1/pipeline/run - this runs in background
    results.append(
        (
            "POST /api/v1/pipeline/run",
            test_endpoint(
                "Run Pipeline (Background)",
                "POST",
                "/api/v1/pipeline/run",
                data={"force_retrain": False, "update_data": False},
                expected_fields=["status", "message"],
            ),
        )
    )

    return results


def test_legacy_endpoints() -> List[Tuple[str, bool]]:
    """Test legacy endpoints"""
    print_section("LEGACY ENDPOINTS")
    results = []

    # GET /positions
    results.append(
        (
            "GET /positions",
            test_endpoint("Get All Positions (Legacy)", "GET", "/positions"),
        )
    )

    # GET /positions/{pair}
    results.append(
        (
            f"GET /positions/{TEST_PAIR}",
            test_endpoint(
                f"Get Position for {TEST_PAIR} (Legacy)",
                "GET",
                f"/positions/{TEST_PAIR}",
                expected_fields=["pair", "position"],
            ),
        )
    )

    # GET /trades
    results.append(
        ("GET /trades", test_endpoint("Get All Trades (Legacy)", "GET", "/trades"))
    )

    # GET /trades/{pair}
    results.append(
        (
            f"GET /trades/{TEST_PAIR}",
            test_endpoint(
                f"Get Trades for {TEST_PAIR} (Legacy)",
                "GET",
                f"/trades/{TEST_PAIR}",
                expected_fields=["pair", "trades"],
            ),
        )
    )

    # GET /analysis/regime/{pair}
    results.append(
        (
            f"GET /analysis/regime/{TEST_PAIR}",
            test_endpoint(
                f"Get Regime Analysis for {TEST_PAIR}",
                "GET",
                f"/analysis/regime/{TEST_PAIR}",
                expected_fields=["pair", "analysis"],
            ),
        )
    )

    # GET /analysis/news/{pair}
    results.append(
        (
            f"GET /analysis/news/{TEST_PAIR}",
            test_endpoint(
                f"Get News Analysis for {TEST_PAIR}",
                "GET",
                f"/analysis/news/{TEST_PAIR}",
                expected_fields=["pair", "analysis"],
            ),
        )
    )

    return results


def test_news_endpoints() -> List[Tuple[str, bool]]:
    """Test news headline sentiment endpoints"""
    print_section("NEWS HEADLINE ENDPOINTS")
    results = []

    # GET /news/headlines
    results.append(
        (
            "GET /news/headlines",
            test_endpoint(
                "Get All Headlines Sentiment",
                "GET",
                "/news/headlines",
                expected_fields=["pairs", "market_sentiment", "market_sentiment_score"],
            ),
        )
    )

    # GET /news/headlines with specific pairs
    results.append(
        (
            "GET /news/headlines?pairs=EURUSD,GBPUSD",
            test_endpoint(
                "Get Headlines for Specific Pairs",
                "GET",
                "/news/headlines",
                params={"pairs": "EURUSD,GBPUSD"},
                expected_fields=["pairs", "market_sentiment"],
            ),
        )
    )

    # GET /news/headlines/{pair}
    results.append(
        (
            f"GET /news/headlines/{TEST_PAIR}",
            test_endpoint(
                f"Get Headlines for {TEST_PAIR}",
                "GET",
                f"/news/headlines/{TEST_PAIR}",
                expected_fields=[
                    "pair",
                    "overall_sentiment",
                    "sentiment_score",
                    "headlines",
                ],
            ),
        )
    )

    return results


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================


def run_all_tests():
    """Run all endpoint tests"""
    print_header("FOREX TRADING API - ENDPOINT TEST SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    # Check if API is running
    print_section("CHECKING API CONNECTION")
    success, status_code, data = make_request("GET", "/health")

    if not success:
        print_fail("API is not running!")
        print_info(f"Error: {data.get('error', 'Unknown error')}")
        print_info(f"Please start the API first: python api.py --port 8000")
        return

    print_success(f"API is healthy (version: {data.get('version', 'unknown')})")

    # Run all test categories
    all_results = []

    all_results.extend(test_health_endpoints())
    all_results.extend(test_main_page_endpoints())
    all_results.extend(test_trade_action_endpoints())
    all_results.extend(test_currency_page_endpoints())
    all_results.extend(test_profit_endpoints())
    all_results.extend(test_analysis_endpoints())
    all_results.extend(test_agent_endpoints())
    all_results.extend(test_pipeline_endpoints())
    all_results.extend(test_legacy_endpoints())
    all_results.extend(test_news_endpoints())

    # Print summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, success in all_results if success)
    failed = sum(1 for _, success in all_results if not success)
    total = len(all_results)

    print(f"\nTotal Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {failed}{Colors.ENDC}")
    print(f"Success Rate: {(passed / total) * 100:.1f}%")

    if failed > 0:
        print(f"\n{Colors.RED}Failed Endpoints:{Colors.ENDC}")
        for endpoint, success in all_results:
            if not success:
                print(f"  - {endpoint}")

    print()
    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ {failed} TEST(S) FAILED{Colors.ENDC}")

    return passed, failed


# =============================================================================
# QUICK TEST MODE
# =============================================================================


def quick_test():
    """Quick test of essential endpoints only"""
    print_header("QUICK TEST - ESSENTIAL ENDPOINTS")
    print(f"Base URL: {BASE_URL}")

    essential_endpoints = [
        ("Health", "GET", "/health"),
        ("Forex Pairs", "GET", "/api/v1/pairs"),
        ("Portfolio", "GET", "/api/v1/portfolio"),
        ("Recommended Trades", "GET", "/api/v1/recommended-trades"),
        ("Price Data", "GET", f"/api/v1/currency/{TEST_PAIR}/price-data"),
        ("Risk Metrics", "GET", f"/api/v1/currency/{TEST_PAIR}/risk-metrics"),
        ("All Profits", "GET", "/api/v1/profits"),
        ("Correlation Matrix", "GET", "/api/v1/correlation-matrix"),
        ("Trade Records", "GET", "/api/v1/trade-records"),
    ]

    results = []
    for name, method, endpoint in essential_endpoints:
        success, status, data = make_request(method, endpoint)
        status_str = (
            f"{Colors.GREEN}✓{Colors.ENDC}"
            if success
            else f"{Colors.RED}✗{Colors.ENDC}"
        )
        print(f"  {status_str} {name}: {method} {endpoint} [{status}]")
        results.append(success)

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} essential endpoints working")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Forex Trading API Endpoints")
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL for the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test of essential endpoints only",
    )

    args = parser.parse_args()
    BASE_URL = args.base_url

    if args.quick:
        quick_test()
    else:
        passed, failed = run_all_tests()
        sys.exit(0 if failed == 0 else 1)
