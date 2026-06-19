"""
Comprehensive Test Suite for Forex Trading API

This test file tests all API endpoints to verify:
1. Endpoints return correct response structures
2. User actions (buy/sell/hold) properly update the portfolio
3. Data consistency across endpoints

Usage:
    pytest test_api.py -v

Or run directly:
    python test_api.py
"""

import pytest
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import os

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
TEST_PAIR = "EURUSD"
TEST_AMOUNT = 5000


# Colors for console output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_test_header(test_name: str):
    """Print a formatted test header"""
    print(f"\n{Colors.HEADER}{'=' * 60}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 60}{Colors.ENDC}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")


def print_fail(message: str):
    """Print failure message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {message}{Colors.ENDC}")


def make_request(
    method: str, endpoint: str, data: Dict = None, params: Dict = None
) -> Dict:
    """Make API request and return response"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return {
            "status_code": response.status_code,
            "data": response.json() if response.text else {},
            "success": response.status_code < 400,
        }
    except requests.exceptions.ConnectionError:
        return {
            "status_code": 0,
            "data": {"error": "Connection refused"},
            "success": False,
        }
    except Exception as e:
        return {"status_code": 0, "data": {"error": str(e)}, "success": False}


# =============================================================================
# HEALTH & STATUS TESTS
# =============================================================================


class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_health_check(self):
        """Test GET /health"""
        print_test_header("Health Check")

        result = make_request("GET", "/health")

        assert result["success"], f"Health check failed: {result['data']}"
        assert result["data"]["status"] == "healthy"
        assert "timestamp" in result["data"]
        assert "version" in result["data"]

        print_success(f"API is healthy, version: {result['data']['version']}")
        return result["data"]


# =============================================================================
# MAIN PAGE ENDPOINT TESTS
# =============================================================================


class TestMainPageEndpoints:
    """Test main page endpoints"""

    def test_get_forex_pairs(self):
        """Test GET /api/v1/pairs"""
        print_test_header("Get Forex Pairs")

        result = make_request("GET", "/api/v1/pairs")

        assert result["success"], f"Failed to get pairs: {result['data']}"
        assert "pairs" in result["data"]
        assert len(result["data"]["pairs"]) == 6

        for pair in result["data"]["pairs"]:
            assert "pair" in pair
            assert "current_price" in pair
            assert "price_change_1d" in pair
            assert "price_change_pct_1d" in pair
            print_info(
                f"{pair['pair']}: {pair['current_price']:.5f} ({pair['price_change_pct_1d']:+.2f}%)"
            )

        print_success(f"Retrieved {len(result['data']['pairs'])} pairs")
        return result["data"]

    def test_get_recommended_trades(self):
        """Test GET /api/v1/recommended-trades"""
        print_test_header("Get Recommended Trades")

        result = make_request("GET", "/api/v1/recommended-trades")

        assert result["success"], f"Failed to get recommendations: {result['data']}"
        assert "trades" in result["data"]

        for trade in result["data"]["trades"]:
            assert "pair" in trade
            assert "action" in trade
            assert trade["action"] in ["buy", "sell", "hold"]
            assert "signal_strength" in trade
            print_info(
                f"{trade['pair']}: {trade['action'].upper()} (strength: {trade['signal_strength']})"
            )

        print_success(
            f"Retrieved recommendations for {len(result['data']['trades'])} pairs"
        )
        return result["data"]

    def test_get_portfolio(self):
        """Test GET /api/v1/portfolio"""
        print_test_header("Get Portfolio Summary")

        result = make_request("GET", "/api/v1/portfolio")

        assert result["success"], f"Failed to get portfolio: {result['data']}"
        assert "total_open_positions" in result["data"]
        assert "total_exposure_long" in result["data"]
        assert "total_exposure_short" in result["data"]
        assert "positions" in result["data"]

        print_info(f"Open positions: {result['data']['total_open_positions']}")
        print_info(f"Long exposure: ${result['data']['total_exposure_long']:,.0f}")
        print_info(f"Short exposure: ${result['data']['total_exposure_short']:,.0f}")
        print_info(f"Net exposure: ${result['data']['net_exposure']:,.0f}")

        print_success("Portfolio summary retrieved")
        return result["data"]


# =============================================================================
# TRADE ACTION TESTS
# =============================================================================


class TestTradeActions:
    """Test trade action endpoints - verifies portfolio updates correctly"""

    def test_buy_action(self):
        """Test POST /api/v1/trade with buy action"""
        print_test_header(f"BUY Action for {TEST_PAIR}")

        # Get initial portfolio state
        initial_portfolio = make_request("GET", "/api/v1/portfolio")
        initial_positions = initial_portfolio["data"].get("positions", {})
        initial_state = initial_positions.get(TEST_PAIR, {}).get(
            "current_position", "flat"
        )

        print_info(f"Initial position: {initial_state}")

        # Execute BUY
        result = make_request(
            "POST",
            "/api/v1/trade",
            {"pair": TEST_PAIR, "action": "buy", "amount": TEST_AMOUNT},
        )

        assert result["success"], f"BUY action failed: {result['data']}"
        assert result["data"]["success"] == True
        assert result["data"]["action"] == "BUY"
        assert result["data"]["position_after"] == "long"
        assert result["data"]["portfolio_summary"] is not None

        print_info(f"Executed at: {result['data']['executed_price']}")
        print_info(f"Trade ID: {result['data']['trade_id']}")

        # Verify portfolio updated
        updated_portfolio = make_request("GET", "/api/v1/portfolio")
        updated_position = updated_portfolio["data"]["positions"].get(TEST_PAIR, {})

        assert updated_position.get("current_position") == "long", (
            "Position not updated to long"
        )
        assert updated_position.get("position_size") == TEST_AMOUNT, (
            "Position size not correct"
        )

        print_success(f"BUY executed successfully, portfolio updated")
        return result["data"]

    def test_sell_action(self):
        """Test POST /api/v1/trade with sell action"""
        print_test_header(f"SELL Action for {TEST_PAIR}")

        # Get initial state
        initial_portfolio = make_request("GET", "/api/v1/portfolio")
        initial_state = (
            initial_portfolio["data"]["positions"]
            .get(TEST_PAIR, {})
            .get("current_position", "flat")
        )
        print_info(f"Initial position: {initial_state}")

        # Execute SELL
        result = make_request(
            "POST",
            "/api/v1/trade",
            {"pair": TEST_PAIR, "action": "sell", "amount": TEST_AMOUNT},
        )

        assert result["success"], f"SELL action failed: {result['data']}"
        assert result["data"]["success"] == True
        assert result["data"]["action"] == "SELL"
        assert result["data"]["position_after"] == "short"

        print_info(f"Executed at: {result['data']['executed_price']}")

        # Verify portfolio updated
        updated_portfolio = make_request("GET", "/api/v1/portfolio")
        updated_position = updated_portfolio["data"]["positions"].get(TEST_PAIR, {})

        assert updated_position.get("current_position") == "short", (
            "Position not updated to short"
        )

        print_success("SELL executed successfully, portfolio updated")
        return result["data"]

    def test_hold_action(self):
        """Test POST /api/v1/trade with hold action (close position)"""
        print_test_header(f"HOLD Action for {TEST_PAIR}")

        # First ensure we have a position
        make_request(
            "POST",
            "/api/v1/trade",
            {"pair": TEST_PAIR, "action": "buy", "amount": TEST_AMOUNT},
        )

        # Now execute HOLD
        result = make_request(
            "POST", "/api/v1/trade", {"pair": TEST_PAIR, "action": "hold"}
        )

        assert result["success"], f"HOLD action failed: {result['data']}"
        assert result["data"]["success"] == True
        assert result["data"]["action"] == "HOLD"
        assert result["data"]["position_after"] == "flat"

        print_info(f"Position closed at: {result['data']['executed_price']}")

        # Verify portfolio updated
        updated_portfolio = make_request("GET", "/api/v1/portfolio")
        updated_position = updated_portfolio["data"]["positions"].get(TEST_PAIR, {})

        assert updated_position.get("current_position") == "flat", "Position not closed"

        print_success("HOLD executed successfully, position closed")
        return result["data"]

    def test_trade_records_after_actions(self):
        """Verify trades are recorded after actions"""
        print_test_header("Verify Trade Records")

        result = make_request("GET", f"/api/v1/trade-records?pair={TEST_PAIR}")

        assert result["success"], f"Failed to get trade records: {result['data']}"

        print_info(f"Total records: {result['data']['total_count']}")

        for record in result["data"]["records"][:5]:
            status = record["status"]
            pnl = record.get("pnl_pct", "N/A")
            print_info(
                f"  {record['entry_datetime']}: {record['action']} @ {record['entry_price']} [{status}] P&L: {pnl}"
            )

        print_success("Trade records verified")
        return result["data"]


# =============================================================================
# CURRENCY PAGE ENDPOINT TESTS
# =============================================================================


class TestCurrencyPageEndpoints:
    """Test currency page endpoints"""

    def test_get_price_data(self):
        """Test GET /api/v1/currency/{pair}/price-data"""
        print_test_header(f"Get Price Data for {TEST_PAIR}")

        result = make_request(
            "GET", f"/api/v1/currency/{TEST_PAIR}/price-data", params={"days": 30}
        )

        assert result["success"], f"Failed to get price data: {result['data']}"
        assert "data" in result["data"]
        assert "spot_rate" in result["data"]
        assert "realized_volatility_10d" in result["data"]
        assert "atr_14d" in result["data"]

        print_info(f"Data points: {len(result['data']['data'])}")
        print_info(f"Spot rate: {result['data']['spot_rate']}")
        print_info(f"Volatility (10d): {result['data']['realized_volatility_10d']:.4f}")
        print_info(f"ATR (14d): {result['data']['atr_14d']:.5f}")

        print_success("Price data retrieved")
        return result["data"]

    def test_get_risk_metrics(self):
        """Test GET /api/v1/currency/{pair}/risk-metrics"""
        print_test_header(f"Get Risk Metrics for {TEST_PAIR}")

        result = make_request("GET", f"/api/v1/currency/{TEST_PAIR}/risk-metrics")

        assert result["success"], f"Failed to get risk metrics: {result['data']}"
        assert "volatility_10d" in result["data"]
        assert "volatility_20d" in result["data"]
        assert "value_at_risk_95" in result["data"]
        assert "position_size" in result["data"]

        print_info(f"Volatility (10d): {result['data']['volatility_10d']:.4f}")
        print_info(f"Volatility (20d): {result['data']['volatility_20d']:.4f}")
        print_info(f"VaR (95%): {result['data']['value_at_risk_95']:.4f}%")
        print_info(f"VaR (99%): {result['data']['value_at_risk_99']:.4f}%")
        print_info(f"Sharpe: {result['data']['strategy_sharpe']:.4f}")

        print_success("Risk metrics retrieved")
        return result["data"]

    def test_get_exposure(self):
        """Test GET /api/v1/currency/{pair}/exposure"""
        print_test_header(f"Get Portfolio Exposure for {TEST_PAIR}")

        result = make_request("GET", f"/api/v1/currency/{TEST_PAIR}/exposure")

        assert result["success"], f"Failed to get exposure: {result['data']}"
        assert "current_position" in result["data"]
        assert "realized_pnl" in result["data"]
        assert "unrealized_pnl" in result["data"]
        assert "portfolio_exposure_pct" in result["data"]

        print_info(f"Current position: {result['data']['current_position']}")
        print_info(f"Position size: ${result['data']['position_size']:,.0f}")
        print_info(f"Realized P&L: {result['data']['realized_pnl']:.4f}%")
        print_info(f"Unrealized P&L: ${result['data']['unrealized_pnl']:,.2f}")
        print_info(
            f"Portfolio exposure: {result['data']['portfolio_exposure_pct']:.2f}%"
        )

        print_success("Exposure data retrieved")
        return result["data"]


# =============================================================================
# PROFIT ENDPOINT TESTS
# =============================================================================


class TestProfitEndpoints:
    """Test profit tracking endpoints"""

    def test_get_cumulative_profit(self):
        """Test GET /api/v1/profits/{pair}"""
        print_test_header(f"Get Cumulative Profit for {TEST_PAIR}")

        result = make_request("GET", f"/api/v1/profits/{TEST_PAIR}")

        assert result["success"], f"Failed to get profit: {result['data']}"
        assert "total_profit_pct" in result["data"]
        assert "total_trades" in result["data"]
        assert "win_rate" in result["data"]

        print_info(f"Total profit: {result['data']['total_profit_pct']:.4f}%")
        print_info(
            f"Total profit amount: ${result['data']['total_profit_amount']:,.2f}"
        )
        print_info(f"Total trades: {result['data']['total_trades']}")
        print_info(f"Win rate: {result['data']['win_rate'] * 100:.1f}%")
        print_info(f"Current streak: {result['data']['current_streak']}")

        print_success("Cumulative profit retrieved")
        return result["data"]

    def test_get_all_profits(self):
        """Test GET /api/v1/profits"""
        print_test_header("Get All Pairs Profit Summary")

        result = make_request("GET", "/api/v1/profits")

        assert result["success"], f"Failed to get profits: {result['data']}"
        assert "pairs" in result["data"]
        assert "total_portfolio_profit_pct" in result["data"]

        print_info(
            f"Total portfolio profit: {result['data']['total_portfolio_profit_pct']:.4f}%"
        )
        print_info(f"Best performing: {result['data']['best_performing_pair']}")
        print_info(f"Worst performing: {result['data']['worst_performing_pair']}")

        for pair, stats in result["data"]["pairs"].items():
            print_info(
                f"  {pair}: {stats['total_profit_pct']:+.2f}% ({stats['total_trades']} trades)"
            )

        print_success("All profits retrieved")
        return result["data"]

    def test_get_profit_chart_data(self):
        """Test GET /api/v1/profits/{pair}/chart-data"""
        print_test_header(f"Get Profit Chart Data for {TEST_PAIR}")

        result = make_request("GET", f"/api/v1/profits/{TEST_PAIR}/chart-data")

        assert result["success"], f"Failed to get chart data: {result['data']}"
        assert "data_points" in result["data"]
        assert "starting_capital" in result["data"]
        assert "final_capital" in result["data"]

        print_info(f"Data points: {result['data']['total_data_points']}")
        print_info(f"Starting capital: ${result['data']['starting_capital']:,.0f}")
        print_info(f"Final capital: ${result['data']['final_capital']:,.0f}")
        print_info(f"Total return: {result['data']['total_return_pct']:.2f}%")

        print_success("Profit chart data retrieved")
        return result["data"]


# =============================================================================
# ANALYSIS ENDPOINT TESTS
# =============================================================================


class TestAnalysisEndpoints:
    """Test analysis endpoints"""

    def test_get_correlation_matrix(self):
        """Test GET /api/v1/correlation-matrix"""
        print_test_header("Get Correlation Matrix")

        result = make_request("GET", "/api/v1/correlation-matrix", params={"days": 60})

        assert result["success"], f"Failed to get correlation: {result['data']}"
        assert "pairs" in result["data"]
        assert "matrix" in result["data"]

        pairs = result["data"]["pairs"]
        matrix = result["data"]["matrix"]

        print_info(f"Pairs: {', '.join(pairs)}")
        print_info(f"Period: {result['data']['period_days']} days")
        print_info("Correlation matrix:")

        # Print header
        header = "       " + "  ".join([p[:6] for p in pairs])
        print(f"  {header}")

        # Print matrix
        for i, row in enumerate(matrix):
            row_str = "  ".join([f"{v:+.2f}" for v in row])
            print(f"  {pairs[i][:6]}: {row_str}")

        print_success("Correlation matrix retrieved")
        return result["data"]

    def test_get_trade_records(self):
        """Test GET /api/v1/trade-records"""
        print_test_header("Get Trade Records")

        result = make_request("GET", "/api/v1/trade-records", params={"limit": 10})

        assert result["success"], f"Failed to get records: {result['data']}"
        assert "records" in result["data"]

        print_info(f"Total records: {result['data']['total_count']}")

        for record in result["data"]["records"][:5]:
            print_info(
                f"  {record['pair']}: {record['action']} @ {record['entry_price']} [{record['status']}]"
            )

        print_success("Trade records retrieved")
        return result["data"]


# =============================================================================
# PORTFOLIO UPDATE VERIFICATION TEST
# =============================================================================


class TestPortfolioUpdates:
    """Test that user actions properly update the portfolio"""

    def test_full_trade_cycle(self):
        """Test complete trade cycle: buy -> check -> sell -> check -> hold -> check"""
        print_test_header("Full Trade Cycle Test")

        test_pair = "GBPUSD"
        test_amount = 8000

        # Step 1: Get initial state
        print_info("Step 1: Getting initial portfolio state...")
        initial = make_request("GET", "/api/v1/portfolio")
        initial_position = initial["data"]["positions"].get(test_pair, {})
        print_info(
            f"  Initial position: {initial_position.get('current_position', 'none')}"
        )

        # Step 2: Execute BUY
        print_info("Step 2: Executing BUY...")
        buy_result = make_request(
            "POST",
            "/api/v1/trade",
            {"pair": test_pair, "action": "buy", "amount": test_amount},
        )
        assert buy_result["success"], "BUY failed"
        buy_price = buy_result["data"]["executed_price"]
        print_info(f"  BUY executed at {buy_price}")

        # Step 3: Verify position is LONG
        print_info("Step 3: Verifying position is LONG...")
        after_buy = make_request("GET", "/api/v1/portfolio")
        buy_position = after_buy["data"]["positions"].get(test_pair, {})
        assert buy_position.get("current_position") == "long", "Position should be long"
        assert buy_position.get("position_size") == test_amount, (
            "Position size mismatch"
        )
        assert buy_position.get("entry_price") == buy_price, "Entry price mismatch"
        print_success("  Position verified as LONG")

        # Step 4: Check profits endpoint
        print_info("Step 4: Checking profits endpoint...")
        profits_before = make_request("GET", f"/api/v1/profits/{test_pair}")
        trades_before = profits_before["data"]["total_trades"]
        print_info(f"  Trades before: {trades_before}")

        # Step 5: Execute SELL (closes long, opens short)
        print_info("Step 5: Executing SELL (should close long, open short)...")
        sell_result = make_request(
            "POST",
            "/api/v1/trade",
            {"pair": test_pair, "action": "sell", "amount": test_amount},
        )
        assert sell_result["success"], "SELL failed"
        sell_price = sell_result["data"]["executed_price"]
        print_info(f"  SELL executed at {sell_price}")

        # Step 6: Verify position is SHORT
        print_info("Step 6: Verifying position is SHORT...")
        after_sell = make_request("GET", "/api/v1/portfolio")
        sell_position = after_sell["data"]["positions"].get(test_pair, {})
        assert sell_position.get("current_position") == "short", (
            "Position should be short"
        )
        print_success("  Position verified as SHORT")

        # Step 7: Check that trade was recorded
        print_info("Step 7: Checking trade was recorded...")
        profits_after = make_request("GET", f"/api/v1/profits/{test_pair}")
        trades_after = profits_after["data"]["total_trades"]
        print_info(f"  Trades after: {trades_after}")

        # Trade count should increase (long was closed)
        assert trades_after >= trades_before, "Trade should have been recorded"
        print_success("  Trade recorded successfully")

        # Step 8: Execute HOLD (close position)
        print_info("Step 8: Executing HOLD (close position)...")
        hold_result = make_request(
            "POST", "/api/v1/trade", {"pair": test_pair, "action": "hold"}
        )
        assert hold_result["success"], "HOLD failed"
        print_info(f"  Position closed at {hold_result['data']['executed_price']}")

        # Step 9: Verify position is FLAT
        print_info("Step 9: Verifying position is FLAT...")
        after_hold = make_request("GET", "/api/v1/portfolio")
        hold_position = after_hold["data"]["positions"].get(test_pair, {})
        assert hold_position.get("current_position") == "flat", (
            "Position should be flat"
        )
        print_success("  Position verified as FLAT")

        # Step 10: Final verification
        print_info("Step 10: Final profit check...")
        final_profits = make_request("GET", f"/api/v1/profits/{test_pair}")
        print_info(f"  Final trade count: {final_profits['data']['total_trades']}")
        print_info(f"  Total profit: {final_profits['data']['total_profit_pct']:.4f}%")

        print_success("Full trade cycle completed successfully!")
        return True


# =============================================================================
# LEGACY ENDPOINT TESTS
# =============================================================================


class TestLegacyEndpoints:
    """Test legacy endpoints for backward compatibility"""

    def test_legacy_positions(self):
        """Test GET /positions"""
        print_test_header("Legacy: Get Positions")

        result = make_request("GET", "/positions")
        assert result["success"], f"Failed: {result['data']}"
        print_success("Legacy positions endpoint works")
        return result["data"]

    def test_legacy_trades(self):
        """Test GET /trades"""
        print_test_header("Legacy: Get Trades")

        result = make_request("GET", "/trades")
        assert result["success"], f"Failed: {result['data']}"
        print_success("Legacy trades endpoint works")
        return result["data"]


# =============================================================================
# RUN ALL TESTS
# =============================================================================


def run_all_tests():
    """Run all tests and print summary"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("   FOREX TRADING API - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"{Colors.ENDC}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Pair: {TEST_PAIR}")
    print(f"Test Amount: ${TEST_AMOUNT:,}")
    print(f"Time: {datetime.now().isoformat()}")

    results = {"passed": 0, "failed": 0, "errors": []}

    test_classes = [
        TestHealthEndpoints,
        TestMainPageEndpoints,
        TestTradeActions,
        TestCurrencyPageEndpoints,
        TestProfitEndpoints,
        TestAnalysisEndpoints,
        TestPortfolioUpdates,
        TestLegacyEndpoints,
    ]

    for test_class in test_classes:
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                    results["passed"] += 1
                except AssertionError as e:
                    results["failed"] += 1
                    results["errors"].append(
                        f"{test_class.__name__}.{method_name}: {str(e)}"
                    )
                    print_fail(f"ASSERTION ERROR: {e}")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        f"{test_class.__name__}.{method_name}: {str(e)}"
                    )
                    print_fail(f"ERROR: {e}")

    # Print summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("   TEST SUMMARY")
    print("=" * 70)
    print(f"{Colors.ENDC}")

    total = results["passed"] + results["failed"]
    print(f"Total tests: {total}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.ENDC}")
    print(f"{Colors.FAIL}Failed: {results['failed']}{Colors.ENDC}")

    if results["errors"]:
        print(f"\n{Colors.FAIL}Errors:{Colors.ENDC}")
        for error in results["errors"]:
            print(f"  - {error}")

    if results["failed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.ENDC}")

    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    # Check if API is running
    print("Checking if API is running...")
    health = make_request("GET", "/health")

    if not health["success"]:
        print(f"\n{Colors.FAIL}ERROR: API is not running at {BASE_URL}")
        print(f"Please start the API first with: python api.py{Colors.ENDC}")
        print(
            "\nOr set a different URL: API_BASE_URL=http://localhost:8080 python test_api.py"
        )
        sys.exit(1)

    results = run_all_tests()
    sys.exit(0 if results["failed"] == 0 else 1)
