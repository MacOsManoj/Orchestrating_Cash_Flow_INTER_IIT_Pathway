"""
Tests for the Explainability Agent
"""

import sys
import unittest
from unittest.mock import MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.explainability import ExplainabilityAgent, Explanation
from schemas_v2 import (
    TradeRecommendation,
    BondAnalytics,
    BondScore,
    MLPrediction,
    Signal,
    Rating,
    Sector,
)


class TestExplainabilityAgent(unittest.TestCase):
    """Test suite for the ExplainabilityAgent."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_llm = MagicMock()
        self.explainability_agent = ExplainabilityAgent(llm=self.mock_llm)

    def test_agent_creation(self):
        """Test if the agent is created successfully."""
        self.assertIsNotNone(self.explainability_agent)
        print(" ExplainabilityAgent created successfully")

    def test_explain_recommendations(self):
        """Test the explanation of recommendations."""

        # Mock LLM response
        mock_explanation_text = "This is a great bond because..."
        self.mock_llm.invoke.return_value = MagicMock(content=mock_explanation_text)

        # Sample data
        isin = "INE020B08339"
        recommendations = [
            TradeRecommendation(
                action="BUY",
                isin=isin,
                name="RELIANCE INDUSTRIES",
                rationale="Strong fundamentals",
                expected_return=0.07,
                risk_score=0.1,
                confidence=0.85,
            )
        ]

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
                total_score=0.88,
                rank=1,
                valuation_score=0.9,
                return_score=0.85,
                quality_score=0.9,
                liquidity_score=0.8,
            )
        }

        ml_predictions = {
            isin: MLPrediction(isin=isin, expected_return=0.07, confidence=0.85)
        }

        # Generate explanations
        explanations = self.explainability_agent.explain_recommendations(
            recommendations=recommendations,
            bond_analytics=bond_analytics,
            bond_scores=bond_scores,
            ml_predictions=ml_predictions,
        )

        self.assertIsInstance(explanations, list)
        self.assertEqual(len(explanations), 1)
        self.assertIsInstance(explanations[0], Explanation)
        self.assertIn("great bond", explanations[0].explanation_text)
        print(" Recommendations explained successfully")


if __name__ == "__main__":
    unittest.main()
