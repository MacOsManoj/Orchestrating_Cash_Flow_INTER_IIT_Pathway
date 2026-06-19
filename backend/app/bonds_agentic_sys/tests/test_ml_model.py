"""
Tests for the ML Model Agent
"""

import sys
import unittest
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.ml_model import MLModelAgent
from schemas_v2 import MLPrediction, BondData


class TestMLModelAgent(unittest.TestCase):
    """Test suite for the MLModelAgent."""

    def setUp(self):
        """Set up the test environment."""
        self.config = {}  # Mock config
        self.agent = MLModelAgent(config=self.config)

        # Create a dummy mock data file
        self.mock_data_dir = "files-mock/analytics"
        os.makedirs(self.mock_data_dir, exist_ok=True)
        self.mock_data_path = os.path.join(self.mock_data_dir, "ml_model_output.json")

        self.mock_predictions = {
            "INE020B08339": {
                "isin": "INE020B08339",
                "expected_return": 0.075,
                "predicted_price": 102.0,
                "confidence": 0.9,
            },
            "INE001A07QF2": {
                "isin": "INE001A07QF2",
                "expected_return": 0.065,
                "predicted_price": 101.0,
                "confidence": 0.85,
            },
        }

        with open(self.mock_data_path, "w") as f:
            json.dump(self.mock_predictions, f)

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.mock_data_path):
            os.remove(self.mock_data_path)

    def test_agent_creation(self):
        """Test if the agent is created successfully."""
        self.assertIsNotNone(self.agent)
        print(" MLModelAgent created successfully")

    def test_predict_batch_with_mock_data(self):
        """Test batch prediction using mock data."""

        bonds_to_predict = [{"isin": "INE020B08339"}, {"isin": "INE001A07QF2"}]

        predictions = self.agent.predict_batch(bonds=bonds_to_predict)

        self.assertIsInstance(predictions, dict)
        self.assertEqual(len(predictions), 2)
        self.assertIn("INE020B08339", predictions)
        self.assertIsInstance(predictions["INE020B08339"], MLPrediction)
        self.assertEqual(predictions["INE020B08339"].expected_return, 0.075)
        print(" Batch prediction successful")

    def test_predict_batch_filters_unrequested_bonds(self):
        """Test that the agent only returns predictions for requested bonds."""

        bonds_to_predict = [
            {"isin": "INE020B08339"}  # Only request one bond
        ]

        predictions = self.agent.predict_batch(bonds=bonds_to_predict)

        self.assertEqual(len(predictions), 1)
        self.assertIn("INE020B08339", predictions)
        self.assertNotIn("INE001A07QF2", predictions)
        print(" Prediction filtering successful")


if __name__ == "__main__":
    unittest.main()
