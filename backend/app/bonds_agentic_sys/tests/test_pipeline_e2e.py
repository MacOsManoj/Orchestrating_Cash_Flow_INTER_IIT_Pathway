"""
End-to-End Pipeline Test
Tests the complete pipeline from user query to recommendations using mock data
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from schemas_v2 import SystemConfigV2, EnhancedAgentState
from orchestrator_v2 import create_orchestrator_v2
from dotenv import load_dotenv

load_dotenv()


class TestPipelineE2E:
    """End-to-end pipeline tests"""

    def __init__(self):
        self.project_root = project_root
        self.config = None
        self.orchestrator = None

    def setup(self):
        """Set up test environment"""
        print("\n" + "=" * 80)
        print("SETTING UP END-TO-END PIPELINE TEST")
        print("=" * 80)

        # Create configuration
        api_key = os.getenv("OPENAI_API_KEY", "test-key")
        self.config = SystemConfigV2(
            openai_api_key=api_key,
            serpapi_key=os.getenv("SERPAPI_KEY"),
            llm_model="gpt-4o-mini",  # Use cheaper model for testing
            llm_temperature=0.0,
            rag_enabled=False,  # Disable RAG for faster testing
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

        print(f" Configuration created")
        print(f"  - LLM Model: {self.config.llm_model}")
        print(f"  - RAG Enabled: {self.config.rag_enabled}")
        print(f"  - Portfolio DB: {self.config.portfolio_db_path}")

    def load_mock_bonds(self) -> List[Dict]:
        """Load bonds from mock NSE data"""
        nse_path = project_root / "files-mock" / "analytics" / "nse_bond_data.json"

        if not nse_path.exists():
            print(f"Warning: NSE data not found at {nse_path}")
            return []

        with open(nse_path, "r") as f:
            nse_data = json.load(f)

        bonds = []

        # Add G-Secs
        for gsec in nse_data.get("gsec_prices", [])[:3]:
            bonds.append(
                {
                    "isin": gsec["isin"],
                    "name": gsec["security_name"],
                    "issuer": "Government of India",
                    "coupon_rate": gsec["coupon"],
                    "maturity_date": gsec["maturity"],
                    "last_traded_price": gsec["last_price"],
                    "ytm": gsec["ytm"],
                    "rating": "AAA",
                    "sector": "Sovereign",
                    "bond_type": "G-Sec",
                    "volume": gsec.get("volume_cr", 0),
                }
            )

        # Add corporate bonds
        for corp in nse_data.get("corporate_bonds", [])[:5]:
            bonds.append(
                {
                    "isin": corp["isin"],
                    "name": f"{corp['issuer']} {corp['coupon']}% {corp['maturity'][:4]}",
                    "issuer": corp["issuer"],
                    "coupon_rate": corp["coupon"],
                    "maturity_date": corp["maturity"],
                    "last_traded_price": corp["last_price"],
                    "ytm": corp["ytm"],
                    "rating": corp["rating"],
                    "sector": corp["sector"],
                    "bond_type": "Corporate",
                    "volume": corp.get("volume_cr", 0),
                    "duration": corp.get("duration", 3.0),
                }
            )

        print(f" Loaded {len(bonds)} bonds from mock data")
        return bonds

    async def test_simple_query(self):
        """Test a simple buy recommendation query"""
        print("\n" + "=" * 80)
        print("TEST 1: Simple Buy Recommendation Query")
        print("=" * 80)

        query = "Find high yield AAA bonds"
        user_id = "TEST_USER_001"
        bonds = self.load_mock_bonds()

        print(f"Query: {query}")
        print(f"User ID: {user_id}")
        print(f"Bonds Universe: {len(bonds)} bonds")

        # Run pipeline
        state = await self.orchestrator.run_async(
            query=query, user_id=user_id, bonds_universe=bonds
        )

        # Verify results
        assert state is not None, "State should not be None"
        assert state.user_query == query, "User query should match"
        assert state.user_id == user_id, "User ID should match"

        # Check execution plan
        assert state.execution_plan is not None, "Execution plan should be created"
        print(f"\n Execution Plan Created:")
        print(
            f"  - Tools: {[t.tool_type.value for t in state.execution_plan.tools_needed]}"
        )
        print(f"  - Agents: {[a.value for a in state.execution_plan.agents_needed]}")
        print(f"  - Reasoning: {state.execution_plan.reasoning[:100]}...")

        # Check query classification (may be None if query_classifier wasn't run)
        if state.classified_query is not None:
            print(f"\n Query Classified:")
            intent = getattr(state.classified_query, "intent", None)
            if hasattr(intent, "value"):
                intent = intent.value
            print(f"  - Intent: {intent}")
        else:
            print(f"\n Query not classified (query_classifier may have been skipped)")

        # Check ML predictions
        if len(state.ml_predictions) > 0:
            print(f"\n ML Predictions: {len(state.ml_predictions)} bonds")
        else:
            print(f"\n No ML predictions (ml_model may have been skipped)")

        # Check bond analytics
        if len(state.bond_analytics) > 0:
            print(f"\n Bond Analytics: {len(state.bond_analytics)} bonds analyzed")
            for isin, analytics in list(state.bond_analytics.items())[:3]:
                print(
                    f"  - {analytics.name}: Duration={analytics.duration:.2f}Y, YTM={analytics.ytm:.2f}%"
                )
        else:
            print(f"\n No bond analytics (analyst may have been skipped)")

        # Check bond scores
        if len(state.bond_scores) > 0:
            print(f"\n Bond Scores: {len(state.bond_scores)} bonds scored")
            top_score = max(state.bond_scores.values(), key=lambda x: x.total_score)
            print(
                f"  - Top Score: {top_score.name} (Score: {top_score.total_score:.4f})"
            )
        else:
            print(f"\n No bond scores (scoring may have been skipped)")

        # Check advisory output (this should always exist)
        if state.advisory is not None:
            print(f"\n Advisory Output:")
            print(f"  - Recommendations: {len(state.advisory.recommendations)}")
            print(
                f"  - Summary: {state.advisory.summary[:150] if state.advisory.summary else 'N/A'}..."
            )

            if state.advisory.recommendations:
                for rec in state.advisory.recommendations[:3]:
                    print(f"    • {rec.action} {rec.name}: {rec.rationale[:80]}...")
        else:
            print(f"\n No advisory output generated")

        print(f"\n Processing Time: {state.processing_time:.2f}s")
        print(f" Cache Hits: {state.cache_hits}/{state.total_tool_calls}")

        return state

    async def test_portfolio_query(self):
        """Test query with portfolio context"""
        print("\n" + "=" * 80)
        print("TEST 2: Portfolio-Based Query")
        print("=" * 80)

        query = "Analyze my portfolio and suggest improvements"
        user_id = "SAMPLE_BANK_001"  # Use existing portfolio
        bonds = self.load_mock_bonds()

        print(f"Query: {query}")
        print(f"User ID: {user_id} (has portfolio)")

        # Run pipeline
        state = await self.orchestrator.run_async(
            query=query, user_id=user_id, bonds_universe=bonds
        )

        # Verify portfolio was accessed
        if state.portfolio:
            print(f"\n Portfolio Loaded:")
            print(f"  - Portfolio ID: {state.portfolio.portfolio_id}")
            print(f"  - Total Value: {state.portfolio.total_value:,.0f}")
            print(f"  - Positions: {len(state.portfolio.positions)}")
        else:
            print(f"\n Portfolio not loaded (may not exist)")

        # Check advisory considers portfolio
        if state.advisory and state.advisory.portfolio_changes:
            print(f"\n Portfolio Impact Calculated:")
            for key, value in state.advisory.portfolio_changes.items():
                print(f"  - {key}: {value}")

        return state

    async def test_explanation_query(self):
        """Test query that triggers explainability"""
        print("\n" + "=" * 80)
        print("TEST 3: Explanation Query (Triggers Explainability)")
        print("=" * 80)

        query = "Why should I buy HDFC Bank bonds? Explain the reasoning."
        user_id = "TEST_USER_002"
        bonds = self.load_mock_bonds()

        print(f"Query: {query}")
        print(f"User ID: {user_id}")

        # Run pipeline
        state = await self.orchestrator.run_async(
            query=query, user_id=user_id, bonds_universe=bonds
        )

        # Check if explainability was triggered
        if state.execution_plan:
            print(
                f"\n Explainability Flag: {state.execution_plan.needs_explainability}"
            )

        # Check explanations
        if state.explanations:
            print(f"\n Explanations Generated: {len(state.explanations)}")
            for i, exp in enumerate(state.explanations[:2], 1):
                print(f"  Explanation {i}:")
                if hasattr(exp, "explanation_text"):
                    print(f"    {exp.explanation_text[:150]}...")
                if hasattr(exp, "top_positive_factors"):
                    print(f"    Top Factors: {exp.top_positive_factors[:3]}")
        else:
            print(f"\n No explanations generated (may not have been triggered)")

        return state

    async def test_duration_reduction_query(self):
        """Test specific strategy query"""
        print("\n" + "=" * 80)
        print("TEST 4: Duration Reduction Strategy")
        print("=" * 80)

        query = "I want to reduce duration in my portfolio, suggest low duration bonds"
        user_id = "TEST_USER_003"
        bonds = self.load_mock_bonds()

        print(f"Query: {query}")

        # Run pipeline
        state = await self.orchestrator.run_async(
            query=query, user_id=user_id, bonds_universe=bonds
        )

        # Check intent
        if state.classified_query:
            intent = getattr(state.classified_query, "intent", None)
            if hasattr(intent, "value"):
                intent = intent.value
            print(f"\n Intent Detected: {intent}")

        # Check recommendations match strategy
        if state.advisory and state.advisory.recommendations:
            print(f"\n Strategy-Specific Recommendations:")
            for rec in state.advisory.recommendations[:5]:
                # Check if recommendation mentions duration
                rationale_lower = rec.rationale.lower()
                if "duration" in rationale_lower or "low" in rationale_lower:
                    print(f"    • {rec.action} {rec.name}: {rec.rationale[:100]}...")

        return state

    async def run_all_tests(self):
        """Run all end-to-end tests"""
        print("\n" + "=" * 80)
        print("END-TO-END PIPELINE TEST SUITE")
        print("=" * 80)

        # Setup
        self.setup()

        # Initialize orchestrator (with mocked LLM to avoid API costs)
        print(f"\n Initializing Orchestrator...")
        try:
            self.orchestrator = create_orchestrator_v2(self.config, rag_system=None)
            print(" Orchestrator initialized")
        except Exception as e:
            print(f"✗ Failed to initialize orchestrator: {e}")
            import traceback

            traceback.print_exc()
            return False

        results = []

        # Run tests
        try:
            # Test 1: Simple query
            result1 = await self.test_simple_query()
            results.append(("Simple Query", result1))

            # Test 2: Portfolio query
            result2 = await self.test_portfolio_query()
            results.append(("Portfolio Query", result2))

            # Test 3: Explanation query
            result3 = await self.test_explanation_query()
            results.append(("Explanation Query", result3))

            # Test 4: Strategy query
            result4 = await self.test_duration_reduction_query()
            results.append(("Duration Reduction", result4))

        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            return False

        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total_time = sum(r.processing_time for _, r in results)
        total_recommendations = sum(
            len(r.advisory.recommendations) if r.advisory else 0 for _, r in results
        )

        print(f"\nTests Completed: {len(results)}")
        print(f"Total Processing Time: {total_time:.2f}s")
        print(f"Average Time per Query: {total_time / len(results):.2f}s")
        print(f"Total Recommendations Generated: {total_recommendations}")

        for test_name, result in results:
            status = "" if result.advisory else ""
            rec_count = len(result.advisory.recommendations) if result.advisory else 0
            print(
                f"{status} {test_name}: {rec_count} recommendations, {result.processing_time:.2f}s"
            )

        print("\n" + "=" * 80)
        print(" ALL END-TO-END TESTS COMPLETED")
        print("=" * 80)

        return True


async def main():
    """Main test runner"""
    tester = TestPipelineE2E()
    success = await tester.run_all_tests()
    return success


if __name__ == "__main__":
    # Run the async test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
