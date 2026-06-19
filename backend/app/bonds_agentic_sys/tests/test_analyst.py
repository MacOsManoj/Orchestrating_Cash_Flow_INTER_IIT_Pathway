"""
Tests for the Analyst Agent
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.analyst import AnalystAgent
from schemas_v2 import (
    BondData,
    BondAnalytics,
    MLPrediction,
    CreditRiskData,
    YieldCurve,
    Rating,
    Sector,
    BondType,
    Signal,
)


class TestAnalystAgent(unittest.TestCase):
    """Test suite for the AnalystAgent."""

    def setUp(self):
        """Set up the test environment."""
        self.analyst_agent = AnalystAgent()

    def test_analyst_agent_creation(self):
        """Test if the AnalystAgent is created successfully."""
        self.assertIsNotNone(self.analyst_agent)
        print(" AnalystAgent created successfully")

    def test_analyze_single_bond(self):
        """Test the analysis of a single bond."""

        # Sample data
        bond_data = BondData(
            isin="INE020B08339",
            name="RELIANCE INDUSTRIES",
            issuer="RELIANCE INDUSTRIES",
            coupon_rate=7.0,
            maturity_date=datetime(2030, 12, 31),
            face_value=100.0,
            last_traded_price=101.0,
            bond_type=BondType.CORPORATE,
            sector=Sector.PRIVATE_CORPORATE,
        )

        ml_prediction = MLPrediction(
            isin="INE020B08339",
            predicted_price=102.5,
            expected_return=0.068,
            confidence=0.85,
        )

        credit_data = CreditRiskData(
            isin="INE020B08339", rating=Rating.AAA, rating_outlook="Stable"
        )

        yield_curve = YieldCurve(
            date=datetime.now(), rates={1: 7.0, 2: 7.1, 3: 7.2, 5: 7.3, 10: 7.5}
        )

        # Analyze the bond
        analytics = self.analyst_agent._analyze_single_bond(
            bond=bond_data,
            ml_prediction=ml_prediction,
            credit_data=credit_data,
            yield_curve=yield_curve,
            risk_free_rate=7.0,
        )

        self.assertIsInstance(analytics, BondAnalytics)
        self.assertEqual(analytics.isin, "INE020B08339")
        self.assertGreater(analytics.ytm, 0)
        self.assertGreater(analytics.duration, 0)
        self.assertIsNotNone(analytics.credit_risk_score)
        print(" Single bond analysis successful")

    def test_analyze_bonds_batch(self):
        """Test the analysis of a batch of bonds."""

        bonds = [
            BondData(
                isin="INE001A07QF2",
                name="HDFC BANK",
                issuer="HDFC BANK",
                coupon_rate=7.5,
                maturity_date=datetime(2028, 5, 20),
            ),
            BondData(
                isin="INE020B08339",
                name="RELIANCE",
                issuer="RELIANCE",
                coupon_rate=7.0,
                maturity_date=datetime(2030, 12, 31),
            ),
        ]

        ml_predictions = {
            "INE001A07QF2": MLPrediction(
                isin="INE001A07QF2",
                predicted_price=101,
                expected_return=0.072,
                confidence=0.8,
            ),
            "INE020B08339": MLPrediction(
                isin="INE020B08339",
                predicted_price=102.5,
                expected_return=0.068,
                confidence=0.85,
            ),
        }

        credit_data = {
            "INE001A07QF2": CreditRiskData(
                isin="INE001A07QF2", rating=Rating.AAA, rating_outlook="Stable"
            ),
            "INE020B08339": CreditRiskData(
                isin="INE020B08339", rating=Rating.AAA, rating_outlook="Stable"
            ),
        }

        yield_curve = YieldCurve(
            date=datetime.now(), rates={1: 7.0, 3: 7.2, 5: 7.3, 10: 7.5}
        )

        analytics_map = self.analyst_agent.analyze_bonds(
            bonds=bonds,
            ml_predictions=ml_predictions,
            credit_data=credit_data,
            yield_curve=yield_curve,
        )

        self.assertEqual(len(analytics_map), 2)
        self.assertIn("INE001A07QF2", analytics_map)
        self.assertIn("INE020B08339", analytics_map)
        self.assertIsInstance(analytics_map["INE001A07QF2"], BondAnalytics)
        print(" Batch bond analysis successful")

    def test_analyze_bonds_with_mock_data(self):
        """Test the analysis of a batch of bonds using mock data files."""

        # Load mock data from files
        with open("files-mock/analytics/analyst_output.json") as f:
            mock_analytics_data = json.load(f)

        with open("files-mock/analytics/ml_model_output.json") as f:
            mock_ml_predictions = json.load(f)

        with open("files-mock/companies/HDFC_BANK/crisil_rating.json") as f:
            mock_credit_data = {"INE001A07QF2": json.load(f)}

        bonds = [
            BondData(
                isin="INE001A07QF2",
                name="HDFC BANK",
                issuer="HDFC BANK",
                coupon_rate=7.5,
                maturity_date=datetime(2028, 5, 20),
            ),
        ]

        yield_curve = YieldCurve(
            date=datetime.now(), rates={1: 7.0, 3: 7.2, 5: 7.3, 10: 7.5}
        )

        # Analyze bonds
        analytics_map = self.analyst_agent.analyze_bonds(
            bonds=bonds,
            ml_predictions=mock_ml_predictions,
            credit_data=mock_credit_data,
            yield_curve=yield_curve,
        )

        self.assertIn("INE001A07QF2", analytics_map)
        self.assertIsInstance(analytics_map["INE001A07QF2"], BondAnalytics)

        # Compare with mock output
        expected_analytics = BondAnalytics(**mock_analytics_data["INE001A07QF2"])
        actual_analytics = analytics_map["INE001A07QF2"]

        self.assertAlmostEqual(
            expected_analytics.fair_value, actual_analytics.fair_value, places=1
        )
        self.assertAlmostEqual(
            expected_analytics.duration, actual_analytics.duration, places=1
        )
        self.assertEqual(
            expected_analytics.credit_rating, actual_analytics.credit_rating
        )

        print(" Batch bond analysis with mock data successful")


if __name__ == "__main__":
    unittest.main()
