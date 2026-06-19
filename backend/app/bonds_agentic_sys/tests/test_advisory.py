"""
Tests for the Advisory Agent
"""

import sys
import os
import unittest
from unittest.mock import MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.advisory import AdvisoryAgent
from schemas_v2 import (
    ClassifiedQuery,
    BondAnalytics,
    BondScore,
    Portfolio,
    TradeRecommendation,
    AdvisoryOutput,
    Signal,
    QueryType,
    Intent,
    Constraint,
    ConstraintType,
    Rating,
    Sector,
)


class TestAdvisoryAgent(unittest.TestCase):
    """Test suite for the AdvisoryAgent."""

    def setUp(self):
        """Set up the test environment."""
        # Mock the language model
        self.mock_llm = MagicMock()
        self.advisory_agent = AdvisoryAgent(llm=self.mock_llm)

    def test_advisory_agent_creation(self):
        """Test if the AdvisoryAgent is created successfully."""
        self.assertIsNotNone(self.advisory_agent)
        print(" AdvisoryAgent created successfully")

    def test_generate_advisory_buy_recommendation(self):
        """Test the advisory generation for a simple BUY recommendation."""

        query_text = "Recommend some good bonds to buy"
        isin = "INE020B08339"

        # Mock the LLM response
        mock_response = AdvisoryOutput(
            query=query_text,
            recommendations=[
                TradeRecommendation(
                    action="BUY",
                    isin=isin,
                    name="RELIANCE INDUSTRIES",
                    quantity=100000,
                    target_price=101.5,
                    stop_loss=99.0,
                    rationale="Strong credit profile and attractive yield.",
                    expected_return=0.05,
                    risk_score=0.1,
                    confidence=0.9,
                )
            ],
            summary="Recommend buying RELIANCE INDUSTRIES due to strong fundamentals.",
            portfolio_changes={},
        )
        self.mock_llm.invoke.return_value = MagicMock(
            content=mock_response.model_dump_json()
        )

        # Inputs
        classified_query = ClassifiedQuery(
            query=query_text,
            query_type=QueryType.ADVISORY,
            intent=Intent.INCREASE_YIELD,
            constraints=[
                Constraint(constraint_type=ConstraintType.RATING, value="AAA")
            ],
            reasoning="User wants to buy high-quality bonds for yield.",
        )

        bond_analytics = {
            isin: BondAnalytics(
                isin=isin,
                name="RELIANCE",
                current_price=101,
                fair_value=103,
                valuation_gap=-0.02,
                duration=5,
                modified_duration=4.8,
                convexity=0.2,
                rate_sensitivity=0.048,
                credit_risk_score=0.1,
                current_yield=6.9,
                ytm=6.8,
                expected_return=0.07,
                liquidity_score=0.9,
                credit_rating=Rating.AAA,
                sector=Sector.PRIVATE_CORPORATE,
                ml_signal=Signal.BUY,
                ml_confidence=0.85,
            )
        }

        bond_scores = {
            isin: BondScore(
                isin=isin,
                name="RELIANCE",
                valuation_score=0.9,
                return_score=0.8,
                quality_score=0.95,
                liquidity_score=0.85,
                total_score=0.875,
                rank=1,
            )
        }

        # Generate advisory
        advisory_output = self.advisory_agent.generate_advisory(
            classified_query=classified_query,
            bond_analytics=bond_analytics,
            bond_scores=bond_scores,
            portfolio=None,
        )

        self.assertIsInstance(advisory_output, AdvisoryOutput)
        self.assertEqual(len(advisory_output.recommendations), 1)
        self.assertEqual(advisory_output.recommendations[0].action, "BUY")
        self.assertEqual(advisory_output.recommendations[0].isin, "INE020B08339")
        print(" Generated BUY recommendation successfully")


if __name__ == "__main__":
    # Set dummy API key for tests if not present
    if "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = "test_key"
    unittest.main()
