"""
Simple Pipeline Runner
Runs a single query through the complete pipeline
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from schemas_v2 import SystemConfigV2
from orchestrator_v3 import create_orchestrator_v3
from dotenv import load_dotenv

load_dotenv()
from utils.mcp_client import create_mcp_client


async def run_pipeline_demo():
    """Run a demo query through the pipeline"""
    print("\n" + "=" * 80)
    print("BOND PIPELINE - DEMO RUN")
    print("=" * 80)

    # Configuration
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        print("   Please set: export OPENAI_API_KEY='sk-...'")
        return
    config = SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model="gpt-4o-mini",
        llm_temperature=0.0,
        rag_enabled=False,
        cache_enabled=True,
        enable_pathway_forecasts=True,  # ENABLE MCP
        enable_dynamic_model_selection=False,
        enable_guardrails=False,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        guardrails_check_input=True,
        guardrails_check_output=True,
        valuation_weight=0.25,
        return_weight=0.30,
        quality_weight=0.25,
        liquidity_weight=0.20,
        portfolio_db_path=str(project_root / ".cache" / "portfolios"),
        cache_dir=str(project_root / ".cache"),
        vector_db_path=str(project_root / "vector_store"),
    )

    # Check MCP Server
    mcp_client = None
    if config.enable_pathway_forecasts:
        print("\nChecking MCP Bonds Server...")
        try:
            mcp_client = create_mcp_client()
            status = mcp_client.get_model_status()
            bonds_result = mcp_client.list_available_bonds()
            if status.get("status") == "ready":
                print(f"    MCP Server: READY")
                print(f"    Models Trained: {status.get('models_trained', 0)}")
                print(f"    Forecast Days: {status.get('forecast_days', 0)}")
                print(f"    Bonds Available: {status.get('bonds_available', 0)}")
            else:
                print(
                    f"   Warning: MCP Server: {status.get('status', 'unknown').upper()}"
                )
                mcp_client = None
        except Exception as e:
            print(f"   ✗ MCP Server: NOT REACHABLE")
            print(f"   Error: {e}")
            mcp_client = None
    print("\nConfiguration:")
    print(f"   - LLM Model: {config.llm_model}")
    print(f"   - RAG: {'Enabled' if config.rag_enabled else 'Disabled'}")
    print(f"   - Cache: {'Enabled' if config.cache_enabled else 'Disabled'}")
    print(
        f"   - MCP Forecasts: {'Enabled' if config.enable_pathway_forecasts else 'Disabled'}"
    )

    # Initialize orchestrator
    print("\nInitializing Orchestrator...")
    orchestrator = create_orchestrator_v3(config, rag_system=None)

    # Get bonds from MCP if available
    bonds_universe = None
    if mcp_client:
        try:
            result = mcp_client.list_available_bonds()
            all_bonds = result.get("available_bonds", [])

            # Convert to expected format
            bonds_universe = []
            for bond in all_bonds[:50]:  # Limit to 50 bonds
                bonds_universe.append(
                    {
                        "isin": bond.get("isin", ""),
                        "symbol": bond.get("symbol", ""),
                        "name": bond.get("name", ""),
                        "issuer": bond.get("name", "").split()[0]
                        if bond.get("name")
                        else "Unknown",
                        "bond_type": "Government",
                        "sector": "Government",
                        "coupon_rate": bond.get("coupon_rate", 0) / 100.0,
                        "maturity_date": bond.get("maturity_date", ""),
                        "last_traded_price": 100.0,
                        "ytm": bond.get("coupon_rate", 7.0) / 100.0,
                        "rating": "AAA",  # Government bonds are AAA
                        "volume": 1000000,
                        "duration": 5.0,
                        "years_to_maturity": 5.0,
                    }
                )
            print(f"    Loaded {len(bonds_universe)} bonds from MCP")
        except Exception as e:
            print(f"   Warning: Could not load bonds: {e}")

    # Demo query - IMPROVED for Government bonds
    query = "What are the high yielding government bonds maturing in 2028?"
    user_id = "DEMO_USER_001"

    print(f"\nQuery: {query}")
    print(f"User ID: {user_id}")
    if bonds_universe:
        print(f"Bonds Universe: {len(bonds_universe)} bonds")
    print("\n" + "=" * 80)
    print("EXECUTING PIPELINE...")
    print("=" * 80)

    # Run pipeline
    state = await orchestrator.run_async(
        query=query, user_id=user_id, bonds_universe=bonds_universe
    )

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\nProcessing Time: {state.processing_time:.2f}s")
    print(f"Cache Hits: {state.cache_hits}/{state.total_tool_calls}")

    if state.execution_plan:
        print(f"\nExecution Plan:")
        print(
            f"   - Tools Used: {[t.tool_type.value for t in state.execution_plan.tools_needed]}"
        )
        print(
            f"   - Agents Used: {[a.value for a in state.execution_plan.agents_needed]}"
        )
        print(f"   - Reasoning: {state.execution_plan.reasoning[:100]}...")

    if state.classified_query:
        intent = getattr(state.classified_query, "intent", None)
        if hasattr(intent, "value"):
            intent = intent.value
        print(f"\nQuery Classification:")
        print(f"   - Intent: {intent}")

    if state.ml_predictions:
        print(f"\nML Predictions: {len(state.ml_predictions)} bonds")

    if state.bond_analytics:
        print(f"\nBond Analytics: {len(state.bond_analytics)} bonds analyzed")
        for isin, analytics in list(state.bond_analytics.items())[:3]:
            print(
                f"   - {analytics.name}: YTM={analytics.ytm:.2%}, Duration={analytics.duration:.2f}Y"
            )

    if state.bond_scores:
        print(f"\nBond Scores: {len(state.bond_scores)} bonds scored")
        top_score = max(state.bond_scores.values(), key=lambda x: x.total_score)
        print(f"   - Top Score: {top_score.name} (Score: {top_score.total_score:.4f})")
    if state.advisory and state.advisory.recommendations:
        print(f"\nRecommendations: {len(state.advisory.recommendations)}")
        for i, rec in enumerate(state.advisory.recommendations[:5], 1):
            print(f"\n   {i}. {rec.action}: {rec.name}")
            print(f"      Quantity: {rec.quantity:,.0f}")
            if rec.target_price:
                print(f"      Target Price: ₹{rec.target_price:.2f}")
            print(f"      Expected Return: {rec.expected_return:.2%}")
            print(f"      Risk Score: {rec.risk_score:.3f}")
            print(f"      Rationale: {rec.rationale[:100]}...")

        if state.advisory.summary:
            print(f"\nSummary:")
            summary_lines = state.advisory.summary.split("\n")
            for line in summary_lines[:5]:  # First 5 lines
                print(f"   {line}")
            if len(summary_lines) > 5:
                print(f"   ... ({len(summary_lines) - 5} more lines)")
    else:
        print("\nWarning: No recommendations generated")

    if state.explanations:
        print(f"\nExplanations: {len(state.explanations)}")
        for i, exp in enumerate(state.explanations[:2], 1):
            print(f"\n   Explanation {i}:")
            if hasattr(exp, "explanation_text"):
                print(f"   {exp.explanation_text[:150]}...")

    if state.errors:
        print(f"\nErrors ({len(state.errors)}):")
        for error in state.errors[:3]:
            print(f"   - {error}")

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION COMPLETE")
    print("=" * 80 + "\n")

    return state


if __name__ == "__main__":
    asyncio.run(run_pipeline_demo())
