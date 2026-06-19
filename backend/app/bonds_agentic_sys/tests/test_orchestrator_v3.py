#!/usr/bin/env python3
"""
Quick test script for Orchestrator V3
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load .env from project root
load_dotenv(dotenv_path=project_root / ".env")

from schemas_v2 import SystemConfigV2
from orchestrator_v3 import create_orchestrator_v3


async def test_orchestrator():
    """Test the orchestrator with a simple query"""
    print("\n" + "=" * 80)
    print(" TESTING ORCHESTRATOR V3")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(" Error: OPENAI_API_KEY not set")
        print("   Please set: export OPENAI_API_KEY='sk-...'")
        print("   Or create a .env file with: OPENAI_API_KEY=sk-...")
        return

    # Configuration
    config = SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model="gpt-4o-mini",
        llm_temperature=0.0,
        rag_enabled=False,  # Disable for faster test
        cache_enabled=True,
        enable_pathway_forecasts=False,
        valuation_weight=0.25,
        return_weight=0.30,
        quality_weight=0.25,
        liquidity_weight=0.20,
        portfolio_db_path=str(project_root / "files-mock" / "portfolios"),
        cache_dir=str(project_root / "files-mock" / "cache"),
        vector_db_path=str(project_root / "vector_store"),
    )

    print("\n Configuration:")
    print(f"   - LLM Model: {config.llm_model}")
    print(f"   - RAG: {'Enabled' if config.rag_enabled else 'Disabled'}")
    print(f"   - Cache: {'Enabled' if config.cache_enabled else 'Disabled'}")

    # Initialize orchestrator
    print("\n Initializing Orchestrator V3...")
    try:
        orchestrator = create_orchestrator_v3(config, rag_system=None)
        print(" Orchestrator initialized successfully!")
    except Exception as e:
        print(f" Failed to initialize: {e}")
        import traceback

        traceback.print_exc()
        return

    # Test queries
    test_queries = [
        "Find high yield AAA bonds with good liquidity",
        "Recommend bonds to reduce portfolio duration",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: {query}")
        print(f"{'=' * 80}")

        try:
            result = await orchestrator.run_async(query=query, user_id="test_user")

            # Display results
            print(f"\n Query completed!")
            print(f"   Processing time: {result.processing_time:.2f}s")
            print(f"   Cache hits: {result.cache_hits}/{result.total_tool_calls}")

            if result.execution_plan:
                print(f"\n Execution Plan:")
                print(
                    f"   Tools: {[t.tool_type.value for t in result.execution_plan.tools_needed]}"
                )
                print(
                    f"   Agents: {[a.value for a in result.execution_plan.agents_needed]}"
                )
                print(f"   Reasoning: {result.execution_plan.reasoning[:200]}...")

            if result.advisory:
                print(f"\n Recommendations: {len(result.advisory.recommendations)}")
                for j, rec in enumerate(result.advisory.recommendations[:3], 1):
                    print(f"   {j}. {rec.action}: {rec.name}")
                    print(f"      Expected Return: {rec.expected_return:.2%}")
                    print(f"      Confidence: {rec.confidence:.2%}")

                if result.advisory.summary:
                    print(f"\n Summary:")
                    print(f"   {result.advisory.summary[:300]}...")

            if result.bond_analytics:
                print(f"\n Analytics: {len(result.bond_analytics)} bonds analyzed")

            if result.bond_scores:
                print(f" Scores: {len(result.bond_scores)} bonds scored")

            if result.explanations:
                print(f" Explanations: {len(result.explanations)} generated")

        except Exception as e:
            print(f" Error processing query: {e}")
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print(" All tests completed!")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
