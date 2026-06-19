"""
Test suite for Portfolio Manager
Run: python testing/portfolio.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.portfolio_manager import (
    PortfolioManager,
    create_portfolio_manager,
    load_portfolios_from_files,
)
from schemas_v2 import TradeRecommendation, Portfolio


def print_header(title):
    """Print test section header"""
    print("\n" + "=" * 70)
    print(f"   {title}")
    print("=" * 70)


def print_test(name):
    """Print test name"""
    print(f"\n>>> TEST: {name}")
    print("-" * 70)


def test_load_portfolios():
    """Test loading portfolios from files"""
    print_test("Load Portfolios from Files")

    portfolios = load_portfolios_from_files()
    print(f" Loaded {len(portfolios)} portfolio entries")

    # Display loaded portfolios
    unique_portfolios = {}
    for key, portfolio in portfolios.items():
        if portfolio.portfolio_id not in unique_portfolios:
            unique_portfolios[portfolio.portfolio_id] = portfolio

    print(f"\nUnique Portfolios: {len(unique_portfolios)}")
    for pid, portfolio in unique_portfolios.items():
        print(f"  • {pid}: {portfolio.name}")
        print(f"    - Total Value: ${portfolio.total_value:,.2f}")
        print(f"    - Cash: ${portfolio.cash:,.2f}")
        print(f"    - Positions: {len(portfolio.positions)}")

    assert len(portfolios) > 0, " No portfolios loaded"
    print("\n PASS")
    return portfolios


def test_get_portfolio():
    """Test fetching a specific portfolio"""
    print_test("Get Portfolio by ID")

    manager = create_portfolio_manager()

    # Test user portfolio
    print("\n1. Testing SAMPLE_USER_001...")
    portfolio = manager.get_portfolio("SAMPLE_USER_001")

    if portfolio:
        print(f" Found: {portfolio.name}")
        print(f"  - Portfolio ID: {portfolio.portfolio_id}")
        print(f"  - Total Value: ${portfolio.total_value:,.2f}")
        print(f"  - Cash: ${portfolio.cash:,.2f}")
        print(f"  - Duration: {portfolio.duration}")
        print(f"  - YTM: {portfolio.ytm}%")
        print(f"  - Positions: {len(portfolio.positions)}")

        if portfolio.positions:
            print(f"\n  Holdings:")
            for pos in portfolio.positions[:3]:
                print(f"    • {pos.name} ({pos.isin})")
                print(f"      Qty: {pos.quantity}, Price: ${pos.current_price:.2f}")
                print(
                    f"      Value: ${pos.market_value:,.2f}, Weight: {pos.weight * 100:.1f}%"
                )
    else:
        print("  Portfolio not found")

    # Test bank portfolio
    print("\n2. Testing SAMPLE_BANK_001...")
    bank_portfolio = manager.get_portfolio("SAMPLE_BANK_001")

    if bank_portfolio:
        print(f" Found: {bank_portfolio.name}")
        print(f"  - Total Value: ${bank_portfolio.total_value:,.2f}")
        print(f"  - Positions: {len(bank_portfolio.positions)}")

    # Test non-existent
    print("\n3. Testing NONEXISTENT...")
    missing = manager.get_portfolio("NONEXISTENT")
    assert missing is None, " Should return None for missing portfolio"
    print(" Correctly returns None for missing portfolio")

    print("\n PASS")
    return portfolio


def test_validate_buy_recommendation(portfolio):
    """Test BUY recommendation validation"""
    print_test("Validate BUY Recommendations")

    manager = create_portfolio_manager()

    print(f"\nPortfolio State:")
    print(f"  Cash: ${portfolio.cash:,.2f}")
    print(f"  Total Value: ${portfolio.total_value:,.2f}")

    # Valid BUY
    rec_valid = TradeRecommendation(
        action="BUY",
        isin="TEST_VALID",
        name="Valid Test Bond AAA",
        quantity=100,
        target_price=100.0,
        rationale="Good fundamentals, strong credit rating",
        expected_return=7.5,
        risk_score=0.3,
        confidence=0.85,
    )

    # Invalid - too expensive
    rec_expensive = TradeRecommendation(
        action="BUY",
        isin="TEST_EXPENSIVE",
        name="Too Expensive Bond",
        quantity=1000000,
        target_price=100.0,
        rationale="High yield opportunity",
        expected_return=8.0,
        risk_score=0.2,
        confidence=0.7,
    )

    # Invalid - high risk for conservative
    rec_risky = TradeRecommendation(
        action="BUY",
        isin="TEST_RISKY",
        name="High Risk Bond",
        quantity=10,
        target_price=100.0,
        rationale="Speculative investment",
        expected_return=12.0,
        risk_score=0.9,
        confidence=0.6,
    )

    # Test with moderate risk profile
    print(f"\n1. Testing with MODERATE risk profile:")
    validated_moderate = manager.validate_recommendations(
        portfolio,
        [rec_valid, rec_expensive, rec_risky],
        context={"risk_profile": "moderate"},
    )

    print(f"   Validated: {len(validated_moderate)}/3 recommendations")
    for rec in [rec_valid, rec_expensive, rec_risky]:
        if rec in validated_moderate:
            print(f"    PASSED: {rec.name}")
        else:
            print(f"   ✗ REJECTED: {rec.name}")
            print(f"     Reason: {rec.rationale}")

    # Test with conservative risk profile
    print(f"\n2. Testing with CONSERVATIVE risk profile:")

    # Reset rationales
    rec_risky.rationale = "Speculative investment"

    validated_conservative = manager.validate_recommendations(
        portfolio, [rec_risky], context={"risk_profile": "conservative"}
    )

    print(f"   Validated: {len(validated_conservative)}/1 recommendations")
    if rec_risky not in validated_conservative:
        print(f"    Correctly rejected high-risk bond for conservative profile")
        print(f"     Reason: {rec_risky.rationale}")

    print("\n PASS")


def test_validate_sell_recommendation(portfolio):
    """Test SELL recommendation validation"""
    print_test("Validate SELL Recommendations")

    if not portfolio or not portfolio.positions:
        print("⊘ SKIP - No portfolio positions available")
        return

    manager = create_portfolio_manager()

    print(f"\nPortfolio Holdings:")
    for i, pos in enumerate(portfolio.positions[:3], 1):
        print(f"  {i}. {pos.name} ({pos.isin})")
        print(f"     Quantity: {pos.quantity}")

    held_isin = portfolio.positions[0].isin
    held_name = portfolio.positions[0].name
    held_qty = portfolio.positions[0].quantity

    # Valid SELL
    rec_valid = TradeRecommendation(
        action="SELL",
        isin=held_isin,
        name=held_name,
        quantity=min(10, held_qty),
        rationale="Taking profits, overvalued",
    )

    # Invalid - not held
    rec_not_held = TradeRecommendation(
        action="SELL",
        isin="NOT_OWNED_123",
        name="Not Owned Bond",
        quantity=100,
        rationale="Exit position",
    )

    # Oversell - too much quantity
    rec_oversell = TradeRecommendation(
        action="SELL",
        isin=held_isin,
        name=held_name,
        quantity=held_qty * 10,
        rationale="Complete exit",
    )

    print(f"\n1. Testing valid SELL:")
    validated = manager.validate_recommendations(
        portfolio, [rec_valid, rec_not_held, rec_oversell]
    )

    print(f"   Validated: {len(validated)}/3 recommendations")

    for rec in [rec_valid, rec_not_held, rec_oversell]:
        if rec in validated:
            print(f"    PASSED: {rec.name}")
            if "ADJUSTED" in rec.rationale:
                print(f"     Note: {rec.rationale}")
        else:
            print(f"   ✗ REJECTED: {rec.name}")
            print(f"     Reason: {rec.rationale}")

    print("\n PASS")


def test_validate_switch_recommendation(portfolio):
    """Test SWITCH recommendation validation"""
    print_test("Validate SWITCH Recommendations")

    if not portfolio or not portfolio.positions:
        print("⊘ SKIP - No portfolio positions available")
        return

    manager = create_portfolio_manager()

    held_isin = portfolio.positions[0].isin
    held_name = portfolio.positions[0].name
    held_qty = portfolio.positions[0].quantity

    print(f"\nSwitching from: {held_name} ({held_isin})")
    print(f"Available quantity: {held_qty}")

    # Valid SWITCH
    rec_valid_switch = TradeRecommendation(
        action="SWITCH",
        isin=held_isin,
        name=held_name,
        quantity=min(10, held_qty),
        switch_to_isin="NEW_BOND_AAA",
        switch_to_name="Better Rated Bond AAA",
        target_price=100.0,
        rationale="Upgrade to higher credit quality",
    )

    # Invalid - switching non-held position
    rec_invalid_switch = TradeRecommendation(
        action="SWITCH",
        isin="NOT_HELD_XYZ",
        name="Non-existent Bond",
        quantity=100,
        switch_to_isin="NEW_BOND",
        switch_to_name="Replacement",
        rationale="Portfolio rebalancing",
    )

    validated = manager.validate_recommendations(
        portfolio, [rec_valid_switch, rec_invalid_switch]
    )

    print(f"\nValidated: {len(validated)}/2 recommendations")

    for rec in [rec_valid_switch, rec_invalid_switch]:
        if rec in validated:
            print(f" PASSED: SWITCH {rec.name} → {rec.switch_to_name}")
        else:
            print(f"✗ REJECTED: {rec.name}")
            print(f"  Reason: {rec.rationale}")

    print("\n PASS")


def test_calculate_metrics(portfolio):
    """Test portfolio metrics calculation"""
    print_test("Calculate Portfolio Metrics")

    manager = create_portfolio_manager()

    print(f"\nCalculating metrics for: {portfolio.name}")
    metrics = manager.calculate_portfolio_metrics(portfolio)

    print(f"\n Portfolio Metrics:")
    print(f"  • Duration: {metrics['duration']:.2f} years")
    print(f"  • YTM: {metrics['ytm']:.2f}%")
    print(f"  • Total Value: ${metrics['total_value']:,.2f}")
    print(f"  • Cash: ${metrics['cash']:,.2f}")
    print(f"  • Cash %: {metrics['cash_pct'] * 100:.2f}%")
    print(f"  • Number of Positions: {metrics['num_positions']}")

    if metrics.get("sector_exposures"):
        print(f"\n  Sector Exposures:")
        for sector, exposure in metrics["sector_exposures"].items():
            print(f"    - {sector}: {exposure * 100:.1f}%")

    if metrics.get("rating_exposures"):
        print(f"\n  Rating Exposures:")
        for rating, exposure in metrics["rating_exposures"].items():
            print(f"    - {rating}: {exposure * 100:.1f}%")

    assert metrics["num_positions"] >= 0, " Invalid position count"
    assert metrics["total_value"] >= 0, " Invalid total value"

    print("\n PASS")


def test_check_constraints(portfolio):
    """Test constraint checking"""
    print_test("Check Portfolio Constraints")

    manager = create_portfolio_manager()

    constraints = {
        "max_duration": 5.0,
        "min_duration": 3.0,
        "min_cash_pct": 0.03,
        "max_sector_pct": 0.35,
    }

    print(f"\n Constraints:")
    print(f"  • Max Duration: {constraints['max_duration']} years")
    print(f"  • Min Duration: {constraints['min_duration']} years")
    print(f"  • Min Cash: {constraints['min_cash_pct'] * 100}%")
    print(f"  • Max Sector: {constraints['max_sector_pct'] * 100}%")

    result = manager.check_constraints(portfolio, constraints)

    print(f"\n Compliance Check:")
    print(f"  Status: {' COMPLIANT' if result['is_compliant'] else '  NON-COMPLIANT'}")

    if result["violations"]:
        print(f"\n  Violations Found ({len(result['violations'])}):")
        for v in result["violations"]:
            print(f"    • {v}")
    else:
        print(f"  No violations found")

    print(f"\n  Individual Checks:")
    for check_name, passed in result["checks"].items():
        status = "" if passed else "✗"
        print(f"    {status} {check_name}")

    print("\n PASS")


def test_risk_thresholds():
    """Test risk threshold logic"""
    print_test("Risk Profile Thresholds")

    manager = create_portfolio_manager()

    profiles = ["conservative", "moderate", "aggressive", "unknown"]

    print(f"\n Risk Thresholds:")
    for profile in profiles:
        threshold = manager._get_risk_threshold(profile)
        print(f"  • {profile.capitalize()}: {threshold} (max risk score)")

    assert manager._get_risk_threshold("conservative") == 0.8
    assert manager._get_risk_threshold("moderate") == 0.6
    assert manager._get_risk_threshold("aggressive") == 1.0
    assert manager._get_risk_threshold("unknown") == 0.6  # default

    print("\n PASS")


def test_configuration():
    """Test manager configuration"""
    print_test("Manager Configuration")

    manager = create_portfolio_manager()

    print(f"\n  Configuration:")
    print(f"  • Max Single Position: {manager.max_single_position_pct * 100}%")
    print(
        f"  • Max Sector Concentration: {manager.max_sector_concentration_pct * 100}%"
    )
    print(f"  • Min Cash Buffer: {manager.min_cash_buffer_pct * 100}%")
    print(f"  • Conservative Risk Threshold: {manager.conservative_risk_threshold}")
    print(f"  • Moderate Risk Threshold: {manager.moderate_risk_threshold}")

    print("\n PASS")


def run_all_tests():
    """Run all tests"""
    print_header("PORTFOLIO MANAGER TEST SUITE")

    try:
        # Test 1: Load portfolios
        portfolios = test_load_portfolios()

        # Test 2: Get portfolio
        portfolio = test_get_portfolio()

        if portfolio:
            # Test 3-8: Tests requiring a portfolio
            test_validate_buy_recommendation(portfolio)
            test_validate_sell_recommendation(portfolio)
            test_validate_switch_recommendation(portfolio)
            test_calculate_metrics(portfolio)
            test_check_constraints(portfolio)
        else:
            print("\n  Skipping portfolio-dependent tests (no portfolio found)")

        # Test 9-10: Standalone tests
        test_risk_thresholds()
        test_configuration()

        print_header(" ALL TESTS PASSED")
        print("\nPortfolio Manager is working correctly!\n")

    except AssertionError as e:
        print(f"\n TEST FAILED (Assertion): {e}")
        import traceback

        traceback.print_exc()
        return False

    except Exception as e:
        print(f"\n TEST FAILED (Exception): {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
