"""
Test script for portfolio updates from natural language queries
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from orchestrator_v3 import create_orchestrator_v3
from schemas_v2 import SystemConfigV2


async def test_portfolio_updates():
    """Test portfolio update functionality"""
    print("=" * 80)
    print("TESTING PORTFOLIO UPDATES FROM NATURAL LANGUAGE QUERIES")
    print("=" * 80)

    # Create config
    config = SystemConfigV2(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model="gpt-4o-mini",
        llm_temperature=0.0,
        rag_enabled=False,
        cache_enabled=True,
        enable_pathway_forecasts=False,
        enable_dynamic_model_selection=False,
        enable_guardrails=False,
        valuation_weight=0.25,
        return_weight=0.30,
        quality_weight=0.25,
        liquidity_weight=0.20,
        portfolio_db_path="files-mock/portfolios",
        cache_dir="files-mock/cache",
        vector_db_path="vector_store",
    )

    # Create orchestrator
    orchestrator = create_orchestrator_v3(config)

    # Test user ID
    user_id = "SAMPLE_USER_001"

    # Test queries
    test_queries = [
        # Add bond
        "add 1000 units of HDFC Bank 7.50% 2025 bond at price 101.5",
        # Update bond
        "update quantity of INE001A01036 to 1500000",
        # Remove bond
        "remove HDFC Bank bond from my portfolio",
    ]

    print(f"\nTesting with user: {user_id}\n")

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: {query}")
        print(f"{'=' * 80}\n")

        try:
            result = await orchestrator.run_async(
                query=query, user_id=user_id, thread_id=f"test_thread_{i}"
            )

            print(f"\n Query processed")
            print(
                f"  Summary: {result.advisory.summary[:200] if result.advisory else 'None'}..."
            )

            if result.portfolio:
                print(
                    f"  Portfolio positions: {len(result.portfolio.holdings) if hasattr(result.portfolio, 'holdings') else 'N/A'}"
                )
                print(
                    f"  Total value: ₹{result.portfolio.total_value:,.2f}"
                    if hasattr(result.portfolio, "total_value")
                    else ""
                )

        except Exception as e:
            print(f" Error: {e}")
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("TESTING COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(test_portfolio_updates())
