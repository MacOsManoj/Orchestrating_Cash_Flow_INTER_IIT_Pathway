"""
Simple script to test MongoDB connection and portfolio operations
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.mongodb_client import get_mongodb_client
from agents.portfolio_manager import create_portfolio_manager
from dotenv import load_dotenv

load_dotenv()


def test_mongodb_connection():
    """Test MongoDB connection"""
    print(" Testing MongoDB connection...")

    client = get_mongodb_client()

    if client.is_connected():
        print(" MongoDB connection successful!")

        # Test collection access
        collection = client.portfolios_collection
        if collection is not None:
            count = collection.count_documents({})
            print(f" Found {count} portfolios in database")
            return True
        else:
            print("  Could not access portfolios collection")
            return False
    else:
        print(" MongoDB connection failed!")
        print("   Please check:")
        print("   1. MongoDB is running")
        print("   2. MONGODB_URI is set in .env")
        print("   3. Connection string is correct")
        return False


def test_portfolio_manager():
    """Test PortfolioManager with MongoDB"""
    print("\n Testing PortfolioManager...")

    manager = create_portfolio_manager(use_mongodb=True)

    if manager.use_mongodb:
        print(" PortfolioManager is using MongoDB")
    else:
        print("  PortfolioManager is using file-based storage (MongoDB not available)")

    # Try to get a portfolio
    portfolio = manager.get_portfolio("SAMPLE_USER_001")

    if portfolio:
        print(f" Successfully retrieved portfolio: {portfolio.portfolio_id}")
        print(f"   Total value: ₹{portfolio.total_value:,.2f}")
        print(f"   Positions: {len(portfolio.positions)}")
        return True
    else:
        print("  No portfolio found for SAMPLE_USER_001")
        print("   Run: python scripts/load_portfolios_to_mongodb.py")
        return False


if __name__ == "__main__":
    print(" MongoDB Portfolio Manager Test\n")

    # Test connection
    connection_ok = test_mongodb_connection()

    if connection_ok:
        # Test portfolio manager
        test_portfolio_manager()

    print("\n✨ Test complete!")
