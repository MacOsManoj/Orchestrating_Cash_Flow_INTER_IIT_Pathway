"""
Script to load mock portfolio data from JSON files into MongoDB
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.portfolio_manager import (
    load_portfolios_from_files,
    create_portfolio_manager,
)
from utils.mongodb_client import get_mongodb_client
from dotenv import load_dotenv

load_dotenv()


def load_mock_portfolios_to_mongodb(
    portfolios_dir: str = "files-mock/portfolios", clear_existing: bool = False
) -> int:
    """
    Load mock portfolios from JSON files into MongoDB

    Args:
        portfolios_dir: Directory containing portfolio JSON files
        clear_existing: Whether to clear existing portfolios before loading

    Returns:
        Number of portfolios loaded
    """
    # Get MongoDB client
    client = get_mongodb_client()

    if not client.is_connected():
        print(" Error: MongoDB is not connected!")
        print("Please ensure MongoDB is running and MONGODB_URI is set in .env")
        return 0

    collection = client.portfolios_collection

    if collection is None:
        print(" Error: Could not access portfolios collection")
        return 0

    # Clear existing portfolios if requested
    if clear_existing:
        result = collection.delete_many({})
        print(f"🗑  Cleared {result.deleted_count} existing portfolios")

    # Load portfolios from files
    print(f"Loading portfolios from {portfolios_dir}...")
    portfolios = load_portfolios_from_files(portfolios_dir)

    if not portfolios:
        print("  No portfolios found in files")
        return 0

    # Create portfolio manager
    portfolio_manager = create_portfolio_manager(use_mongodb=True)

    # Save each portfolio to MongoDB
    loaded_count = 0
    for user_id, portfolio in portfolios.items():
        try:
            success = portfolio_manager.save_portfolio(portfolio, user_id)
            if success:
                loaded_count += 1
                print(f" Loaded portfolio for {user_id} ({portfolio.portfolio_id})")
            else:
                print(f"  Failed to load portfolio for {user_id}")
        except Exception as e:
            print(f" Error loading portfolio for {user_id}: {e}")

    # Verify loaded portfolios
    total_in_db = collection.count_documents({})
    print(f"\n Successfully loaded {loaded_count} portfolios")
    print(f" Total portfolios in MongoDB: {total_in_db}")

    # List all portfolios
    print("\n Portfolios in database:")
    for doc in collection.find({}):
        portfolio_id = doc.get("portfolio_id", "N/A")
        user_id = doc.get("user_id", doc.get("bank_id", "N/A"))
        name = doc.get("name", "N/A")
        total_value = doc.get("total_value", 0)
        print(f"  - {user_id} ({portfolio_id}): {name} - ₹{total_value:,.2f}")

    return loaded_count


def create_additional_mock_portfolios() -> Dict[str, Any]:
    """
    Create additional mock portfolios for testing
    Returns a dict of portfolio data
    """
    from datetime import datetime, timedelta

    additional_portfolios = {
        "SAMPLE_USER_002": {
            "user_id": "SAMPLE_USER_002",
            "portfolio_id": "PF_002",
            "holdings": [
                {
                    "isin": "INE001A01036",
                    "bond_name": "HDFC Bank 7.50% 2025",
                    "quantity": 200,
                    "avg_cost": 101.0,
                    "current_price": 101.5,
                    "market_value": 20300,
                    "unrealized_pnl": 100,
                    "weight": 0.20,
                    "duration": 2.1,
                    "ytm": 7.0,
                    "sector": "Private_Financial",
                    "rating": "AAA",
                },
                {
                    "isin": "INE003A01024",
                    "bond_name": "G-Sec 7.06% 2028",
                    "quantity": 500,
                    "avg_cost": 100.0,
                    "current_price": 100.2,
                    "market_value": 50100,
                    "unrealized_pnl": 100,
                    "weight": 0.50,
                    "duration": 4.2,
                    "ytm": 7.0,
                    "sector": "Sovereign",
                    "rating": "AAA",
                },
                {
                    "isin": "INE002A01018",
                    "bond_name": "NTPC 7.20% 2030",
                    "quantity": 150,
                    "avg_cost": 98.0,
                    "current_price": 98.5,
                    "market_value": 14775,
                    "unrealized_pnl": 75,
                    "weight": 0.15,
                    "duration": 6.5,
                    "ytm": 7.5,
                    "sector": "PSU_Energy",
                    "rating": "AAA",
                },
            ],
            "total_value": 85175,
            "cash": 15000,
            "portfolio_duration": 4.0,
            "portfolio_ytm": 7.1,
            "sector_exposures": {
                "Sovereign": 0.5,
                "Private_Financial": 0.20,
                "PSU_Energy": 0.15,
            },
            "rating_exposures": {"AAA": 1.0},
            "last_updated": datetime.now().isoformat(),
        },
        "SAMPLE_USER_003": {
            "user_id": "SAMPLE_USER_003",
            "portfolio_id": "PF_003",
            "holdings": [
                {
                    "isin": "INE003A01024",
                    "bond_name": "G-Sec 7.06% 2028",
                    "quantity": 2000,
                    "avg_cost": 100.0,
                    "current_price": 100.2,
                    "market_value": 200400,
                    "unrealized_pnl": 400,
                    "weight": 0.80,
                    "duration": 4.2,
                    "ytm": 7.0,
                    "sector": "Sovereign",
                    "rating": "AAA",
                },
                {
                    "isin": "INE001A01036",
                    "bond_name": "HDFC Bank 7.50% 2025",
                    "quantity": 100,
                    "avg_cost": 101.0,
                    "current_price": 101.5,
                    "market_value": 10150,
                    "unrealized_pnl": 50,
                    "weight": 0.04,
                    "duration": 2.1,
                    "ytm": 7.0,
                    "sector": "Private_Financial",
                    "rating": "AAA",
                },
            ],
            "total_value": 250550,
            "cash": 50000,
            "portfolio_duration": 3.8,
            "portfolio_ytm": 7.0,
            "sector_exposures": {"Sovereign": 0.80, "Private_Financial": 0.04},
            "rating_exposures": {"AAA": 1.0},
            "last_updated": datetime.now().isoformat(),
        },
    }

    return additional_portfolios


def load_additional_mock_portfolios() -> int:
    """Load additional mock portfolios created programmatically"""
    from agents.portfolio_manager import _parse_user_portfolio, create_portfolio_manager

    portfolio_manager = create_portfolio_manager(use_mongodb=True)
    additional = create_additional_mock_portfolios()

    loaded = 0
    for user_id, data in additional.items():
        try:
            portfolio = _parse_user_portfolio(data)
            if portfolio_manager.save_portfolio(portfolio, user_id):
                loaded += 1
                print(f" Loaded additional portfolio for {user_id}")
        except Exception as e:
            print(f" Error loading additional portfolio for {user_id}: {e}")

    return loaded


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load mock portfolios into MongoDB")
    parser.add_argument(
        "--portfolios-dir",
        type=str,
        default="files-mock/portfolios",
        help="Directory containing portfolio JSON files",
    )
    parser.add_argument(
        "--clear", action="store_true", help="Clear existing portfolios before loading"
    )
    parser.add_argument(
        "--additional", action="store_true", help="Also load additional mock portfolios"
    )

    args = parser.parse_args()

    print(" Starting portfolio data load to MongoDB...\n")

    # Load from files
    count = load_mock_portfolios_to_mongodb(
        portfolios_dir=args.portfolios_dir, clear_existing=args.clear
    )

    # Load additional mock portfolios if requested
    if args.additional:
        print("\n Loading additional mock portfolios...")
        additional_count = load_additional_mock_portfolios()
        print(f" Loaded {additional_count} additional portfolios")

    print("\n✨ Done!")
