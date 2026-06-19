"""
Comprehensive Integration Test
Verifies all agents work together in the orchestrator
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from schemas_v2 import SystemConfigV2
from orchestrator_v2 import create_orchestrator_v2
from dotenv import load_dotenv

load_dotenv()


async def test_full_integration():
    """Test complete pipeline integration"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE INTEGRATION TEST")
    print("=" * 80)

    # Setup
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    config = SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model="gpt-4o-mini",
        llm_temperature=0.0,
        rag_enabled=False,
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

    print("\n1. Initializing Orchestrator...")
    try:
        orchestrator = create_orchestrator_v2(config, rag_system=None)
        print("    Orchestrator initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test queries
    test_cases = [
        {
            "name": "Simple Query",
            "query": "Find high yield AAA bonds",
            "user_id": "TEST_USER_001",
            "expected_agents": [
                "query_classifier",
                "ml_model",
                "analyst",
                "scoring",
                "advisory",
            ],
        },
        {
            "name": "Portfolio Query",
            "query": "Analyze my portfolio",
            "user_id": "SAMPLE_BANK_001",
            "expected_agents": [
                "query_classifier",
                "ml_model",
                "analyst",
                "scoring",
                "advisory",
            ],
        },
        {
            "name": "Explanation Query",
            "query": "Why should I buy HDFC bonds? Explain.",
            "user_id": "TEST_USER_002",
            "expected_agents": [
                "query_classifier",
                "ml_model",
                "analyst",
                "scoring",
                "advisory",
                "explainability",
            ],
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   Query: {test_case['query']}")

        try:
            state = await orchestrator.run_async(
                query=test_case["query"], user_id=test_case["user_id"]
            )

            # Verify state
            assert state is not None, "State should not be None"
            assert state.user_query == test_case["query"], "User query should match"

            # Verify execution plan
            assert state.execution_plan is not None, "Execution plan should exist"
            print(f"    Execution plan created")

            # Verify agents executed
            agents_executed = []
            if state.classified_query:
                agents_executed.append("query_classifier")
            if state.ml_predictions:
                agents_executed.append("ml_model")
            if state.bond_analytics:
                agents_executed.append("analyst")
            if state.bond_scores:
                agents_executed.append("scoring")
            if state.advisory:
                agents_executed.append("advisory")
            if state.explanations:
                agents_executed.append("explainability")

            print(f"    Agents executed: {agents_executed}")

            # Verify data flow
            issues = []

            if not state.classified_query:
                issues.append("Query classifier did not produce output")

            if not state.ml_predictions:
                issues.append("ML model did not produce predictions")
            elif not isinstance(state.ml_predictions, dict):
                issues.append(
                    f"ML predictions should be dict, got {type(state.ml_predictions)}"
                )

            if not state.bond_analytics:
                issues.append("Analyst did not produce analytics")
            elif not isinstance(state.bond_analytics, dict):
                issues.append(
                    f"Bond analytics should be dict, got {type(state.bond_analytics)}"
                )

            if not state.bond_scores:
                issues.append("Scoring did not produce scores")
            elif not isinstance(state.bond_scores, dict):
                issues.append(
                    f"Bond scores should be dict, got {type(state.bond_scores)}"
                )

            if not state.advisory:
                issues.append("Advisory did not produce recommendations")
            elif not state.advisory.recommendations:
                issues.append("Advisory produced no recommendations")

            if issues:
                print(f"    Issues found:")
                for issue in issues:
                    print(f"      - {issue}")
            else:
                print(f"    All data flows verified")

            # Verify recommendations
            if state.advisory and state.advisory.recommendations:
                print(
                    f"    Generated {len(state.advisory.recommendations)} recommendations"
                )
                for rec in state.advisory.recommendations[:2]:
                    print(f"      • {rec.action}: {rec.name}")
            else:
                print(f"    No recommendations generated")

            results.append(
                {
                    "name": test_case["name"],
                    "success": len(issues) == 0,
                    "issues": issues,
                    "recommendations": len(state.advisory.recommendations)
                    if state.advisory
                    else 0,
                    "time": state.processing_time,
                }
            )

        except Exception as e:
            print(f"   ✗ Test failed: {e}")
            import traceback

            traceback.print_exc()
            results.append(
                {
                    "name": test_case["name"],
                    "success": False,
                    "issues": [str(e)],
                    "recommendations": 0,
                    "time": 0,
                }
            )

    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    total_recommendations = sum(r["recommendations"] for r in results)
    total_time = sum(r["time"] for r in results)

    print(f"\nTests: {passed_tests}/{total_tests} passed")
    print(f"Total Recommendations: {total_recommendations}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Average Time: {total_time / total_tests:.2f}s per query")

    print(f"\nDetailed Results:")
    for result in results:
        status = "" if result["success"] else "✗"
        print(
            f"  {status} {result['name']}: {result['recommendations']} recs, {result['time']:.2f}s"
        )
        if result["issues"]:
            for issue in result["issues"]:
                print(f"      - {issue}")

    print("\n" + "=" * 80)
    if passed_tests == total_tests:
        print(" ALL INTEGRATION TESTS PASSED")
    else:
        print(f"  {total_tests - passed_tests} TEST(S) FAILED")
    print("=" * 80)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = asyncio.run(test_full_integration())
    sys.exit(0 if success else 1)
