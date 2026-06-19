"""
Test script for Portfolio Manager
Tests MongoDB operations, bond updates, and portfolio management
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from agents.portfolio_manager import create_portfolio_manager
from schemas_v2 import Portfolio, Position
from dotenv import load_dotenv

load_dotenv()


def test_portfolio_manager():
    """Test portfolio manager functionality"""
    print("\n" + "=" * 80)
    print("🧪 TESTING PORTFOLIO MANAGER")
    print("=" * 80)

    # Create portfolio manager
    print("\n Creating Portfolio Manager...")
    manager = create_portfolio_manager(use_mongodb=True)

    if not manager.use_mongodb:
        print("  MongoDB not available, using file-based storage")
    else:
        print(" Using MongoDB for portfolio storage")

    # Test 1: Get existing portfolio
    print("\n" + "=" * 80)
    print("TEST 1: Get Portfolio from MongoDB")
    print("=" * 80)

    user_id = "SAMPLE_USER_001"
    portfolio = manager.get_portfolio(user_id)

    if portfolio:
        print(f" Portfolio found for {user_id}")
        print(f"   Portfolio ID: {portfolio.portfolio_id}")
        print(f"   Total Value: ₹{portfolio.total_value:,.2f}")
        print(f"   Cash: ₹{portfolio.cash:,.2f}")
        print(f"   Positions: {len(portfolio.positions)}")
        print(f"   Duration: {portfolio.duration:.2f} years")
        print(f"   YTM: {portfolio.ytm:.2%}")

        # Show first few positions
        if portfolio.positions:
            print(f"\n   First 3 positions:")
            for i, pos in enumerate(portfolio.positions[:3], 1):
                print(f"   {i}. {pos.name} ({pos.isin})")
                print(f"      Quantity: {pos.quantity:,.0f}")
                print(f"      Current Price: ₹{pos.current_price:.2f}")
                print(f"      Market Value: ₹{pos.market_value:,.2f}")
                print(f"      Weight: {pos.weight:.2%}")
    else:
        print(f"  Portfolio not found for {user_id}")
        print("   Creating a test portfolio...")
        # Create a test portfolio
        test_portfolio = Portfolio(
            portfolio_id=user_id,
            name=f"Test Portfolio for {user_id}",
            positions=[
                Position(
                    isin="INE001A01036",
                    name="HDFC Bank 7.50% 2025",
                    quantity=1000000,
                    avg_cost=100.0,
                    current_price=101.5,
                    market_value=1015000.0,
                    weight=0.5,
                    unrealized_pnl=15000.0,
                ),
                Position(
                    isin="INE002A01018",
                    name="NTPC 7.20% 2030",
                    quantity=500000,
                    avg_cost=98.0,
                    current_price=98.5,
                    market_value=492500.0,
                    weight=0.3,
                    unrealized_pnl=2500.0,
                ),
            ],
            total_value=2000000.0,
            cash=500000.0,
            duration=3.5,
            ytm=0.072,
            sector_exposures={"Financial": 0.5, "PSU_Energy": 0.3},
            rating_exposures={"AAA": 0.8},
        )
        manager.save_portfolio(test_portfolio, user_id)
        print(f" Test portfolio created and saved")
        portfolio = test_portfolio

    # Test 2: Update single bond
    print("\n" + "=" * 80)
    print("TEST 2: Update Single Bond in Portfolio")
    print("=" * 80)

    if portfolio and portfolio.positions:
        test_isin = portfolio.positions[0].isin
        old_price = portfolio.positions[0].current_price
        old_quantity = portfolio.positions[0].quantity

        print(f"\n Updating bond: {test_isin}")
        print(f"   Old Price: ₹{old_price:.2f}")
        print(f"   Old Quantity: {old_quantity:,.0f}")

        new_price = old_price + 1.0
        new_quantity = old_quantity + 100000

        success = manager.update_bond_in_portfolio(
            user_id=user_id,
            isin=test_isin,
            updates={"current_price": new_price, "quantity": new_quantity},
        )

        if success:
            print(f" Bond updated successfully")

            # Verify update
            updated_portfolio = manager.get_portfolio(user_id)
            if updated_portfolio:
                updated_pos = next(
                    (p for p in updated_portfolio.positions if p.isin == test_isin),
                    None,
                )
                if updated_pos:
                    print(
                        f"   New Price: ₹{updated_pos.current_price:.2f} (expected: ₹{new_price:.2f})"
                    )
                    print(
                        f"   New Quantity: {updated_pos.quantity:,.0f} (expected: {new_quantity:,.0f})"
                    )
                    print(f"   Market Value: ₹{updated_pos.market_value:,.2f}")
                    print(f"   Unrealized P&L: ₹{updated_pos.unrealized_pnl:,.2f}")

                    if (
                        abs(updated_pos.current_price - new_price) < 0.01
                        and abs(updated_pos.quantity - new_quantity) < 0.01
                    ):
                        print("    Update verified successfully!")
                    else:
                        print("     Update values don't match")
        else:
            print(" Failed to update bond")

    # Test 3: Update multiple bonds
    print("\n" + "=" * 80)
    print("TEST 3: Update Multiple Bonds")
    print("=" * 80)

    if portfolio and len(portfolio.positions) >= 2:
        bond_updates = []
        for i, pos in enumerate(portfolio.positions[:2], 1):
            bond_updates.append(
                {
                    "isin": pos.isin,
                    "current_price": pos.current_price + 0.5,
                    "quantity": pos.quantity + 50000,
                }
            )
            print(f"\n Bond {i}: {pos.isin}")
            print(
                f"   Current Price: ₹{pos.current_price:.2f} → ₹{pos.current_price + 0.5:.2f}"
            )
            print(f"   Quantity: {pos.quantity:,.0f} → {pos.quantity + 50000:,.0f}")

        results = manager.update_multiple_bonds(
            user_id=user_id, bond_updates=bond_updates
        )

        print(f"\n Update Results:")
        for isin, success in results.items():
            status = "" if success else ""
            print(f"   {status} {isin}: {'Success' if success else 'Failed'}")

        # Verify updates
        updated_portfolio = manager.get_portfolio(user_id)
        if updated_portfolio:
            print(f"\n Portfolio metrics recalculated:")
            print(f"   Total Value: ₹{updated_portfolio.total_value:,.2f}")
            print(f"   Number of Positions: {len(updated_portfolio.positions)}")

    # Test 4: Add new bond to portfolio
    print("\n" + "=" * 80)
    print("TEST 4: Add New Bond to Portfolio")
    print("=" * 80)

    new_isin = "INE999A01099"
    new_bond_name = "Test Bond 7.00% 2026"

    print(f"\n Adding new bond: {new_isin} ({new_bond_name})")

    success = manager.update_bond_in_portfolio(
        user_id=user_id,
        isin=new_isin,
        updates={
            "name": new_bond_name,
            "quantity": 750000,
            "current_price": 99.5,
            "avg_cost": 100.0,
        },
    )

    if success:
        print(f" New bond added successfully")

        # Verify addition
        updated_portfolio = manager.get_portfolio(user_id)
        if updated_portfolio:
            new_pos = next(
                (p for p in updated_portfolio.positions if p.isin == new_isin), None
            )
            if new_pos:
                print(f"    Bond found in portfolio:")
                print(f"      Name: {new_pos.name}")
                print(f"      Quantity: {new_pos.quantity:,.0f}")
                print(f"      Price: ₹{new_pos.current_price:.2f}")
                print(f"      Market Value: ₹{new_pos.market_value:,.2f}")
            else:
                print("     Bond not found after addition")
    else:
        print(" Failed to add new bond")

    # Test 5: Remove bond from portfolio
    print("\n" + "=" * 80)
    print("TEST 5: Remove Bond from Portfolio")
    print("=" * 80)

    if portfolio and portfolio.positions:
        bond_to_remove = portfolio.positions[-1].isin
        print(f"\n Removing bond: {bond_to_remove}")

        # Get portfolio before removal
        before_portfolio = manager.get_portfolio(user_id)
        positions_before = len(before_portfolio.positions) if before_portfolio else 0

        success = manager.remove_bond_from_portfolio(
            user_id=user_id, isin=bond_to_remove
        )

        if success:
            print(f" Bond removed successfully")

            # Verify removal
            after_portfolio = manager.get_portfolio(user_id)
            if after_portfolio:
                positions_after = len(after_portfolio.positions)
                removed_pos = next(
                    (p for p in after_portfolio.positions if p.isin == bond_to_remove),
                    None,
                )

                print(f"   Positions before: {positions_before}")
                print(f"   Positions after: {positions_after}")
                print(f"   Total Value: ₹{after_portfolio.total_value:,.2f}")

                if removed_pos is None:
                    print("    Bond successfully removed!")
                else:
                    print("     Bond still found in portfolio")
        else:
            print(" Failed to remove bond")

    # Test 6: Calculate portfolio metrics
    print("\n" + "=" * 80)
    print("TEST 6: Calculate Portfolio Metrics")
    print("=" * 80)

    final_portfolio = manager.get_portfolio(user_id)
    if final_portfolio:
        metrics = manager.calculate_portfolio_metrics(final_portfolio)

        print(f"\n Portfolio Metrics:")
        print(f"   Duration: {metrics.get('duration', 0):.2f} years")
        print(f"   YTM: {metrics.get('ytm', 0):.2%}")
        print(f"   Total Value: ₹{metrics.get('total_value', 0):,.2f}")
        print(f"   Cash: ₹{metrics.get('cash', 0):,.2f}")
        print(f"   Cash %: {metrics.get('cash_pct', 0):.2%}")
        print(f"   Number of Positions: {metrics.get('num_positions', 0)}")

        if metrics.get("sector_exposures"):
            print(f"\n   Sector Exposures:")
            for sector, exposure in metrics["sector_exposures"].items():
                print(f"      {sector}: {exposure:.2%}")

        if metrics.get("rating_exposures"):
            print(f"\n   Rating Exposures:")
            for rating, exposure in metrics["rating_exposures"].items():
                print(f"      {rating}: {exposure:.2%}")

    # Test 7: Validate recommendations
    print("\n" + "=" * 80)
    print("TEST 7: Validate Trade Recommendations")
    print("=" * 80)

    if final_portfolio:
        from schemas_v2 import TradeRecommendation

        # Create some test recommendations
        test_recommendations = [
            TradeRecommendation(
                action="BUY",
                isin="INE001A01036",
                name="HDFC Bank 7.50% 2025",
                quantity=500000,
                target_price=102.0,
                rationale="Test buy recommendation",
                expected_return=0.08,
                risk_score=0.3,
            ),
            TradeRecommendation(
                action="SELL",
                isin=final_portfolio.positions[0].isin
                if final_portfolio.positions
                else "INE001A01036",
                name="Test Sell",
                quantity=100000,
                rationale="Test sell recommendation",
                expected_return=0.05,
                risk_score=0.2,
            ),
        ]

        print(f"\n Validating {len(test_recommendations)} recommendations...")

        valid_recs = manager.validate_recommendations(
            portfolio=final_portfolio,
            recommendations=test_recommendations,
            context={"risk_profile": "moderate"},
        )

        print(f"\n Validation Results:")
        print(f"   Total Recommendations: {len(test_recommendations)}")
        print(f"   Valid Recommendations: {len(valid_recs)}")
        print(f"   Rejected: {len(test_recommendations) - len(valid_recs)}")

        for rec in valid_recs:
            print(f"\n    {rec.action}: {rec.name}")
            print(f"      Quantity: {rec.quantity:,.0f}")
            if rec.target_price:
                print(f"      Target Price: ₹{rec.target_price:.2f}")
            print(f"      Rationale: {rec.rationale[:80]}...")

    print("\n" + "=" * 80)
    print(" PORTFOLIO MANAGER TEST COMPLETE")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    success = test_portfolio_manager()
    sys.exit(0 if success else 1)
