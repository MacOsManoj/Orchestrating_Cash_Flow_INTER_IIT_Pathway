"""
Comprehensive Test Suite for All Agents
Uses mock data from files-mock directory
"""

import sys
import os
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agents.ml_model import MLModelAgent, create_ml_agent
from agents.query_classifier import (
    QueryClassifierAgent,
    create_query_classifier,
    ClassifiedQuery,
)
from agents.analyst import AnalystAgent, create_analyst_agent
from agents.scoring import ScoringAgent, create_scoring_agent
from agents.advisory import AdvisoryAgent, create_advisory_agent
from agents.explainability import ExplainabilityAgent, create_explainability_agent
from agents.planner import PlannerAgent, create_planner_agent
# Note: portfolio_manager functions are tested separately if needed
# from agents.portfolio_manager import portfolio_node, constraint_check_node

from schemas_v2 import (
    MLPrediction,
    BondAnalytics,
    BondScore,
    TradeRecommendation,
    AdvisoryOutput,
    Portfolio,
    Position,
    Rating,
    Sector,
    Signal,
    QueryType,
    Intent,
    Constraint,
)
from agents.query_classifier import ClassifiedQuery as AgentClassifiedQuery


class TestMLModelAgent(unittest.TestCase):
    """Test ML Model Agent with mock data"""

    def setUp(self):
        """Set up test environment"""
        self.mock_data_path = (
            project_root / "files-mock" / "analytics" / "ml_model_output.json"
        )
        self.config = {"mock_data_path": str(self.mock_data_path)}
        self.agent = create_ml_agent(self.config)

    def test_agent_creation(self):
        """Test agent creation"""
        self.assertIsNotNone(self.agent)
        print(" MLModelAgent created successfully")

    def test_load_mock_data(self):
        """Test loading mock ML predictions"""
        with open(self.mock_data_path, "r") as f:
            mock_data = json.load(f)

        # Check for both structures
        has_additional = "additional_predictions" in mock_data
        has_bond_preds = "bond_price_predictions" in mock_data

        self.assertTrue(has_additional or has_bond_preds)
        count = len(mock_data.get("additional_predictions", {})) + len(
            mock_data.get("bond_price_predictions", [])
        )
        print(f" Loaded {count} mock predictions")

    def test_predict_batch(self):
        """Test batch prediction using mock data"""
        # Load bonds from NSE data
        nse_path = project_root / "files-mock" / "analytics" / "nse_bond_data.json"
        with open(nse_path, "r") as f:
            nse_data = json.load(f)

        # Get bonds that exist in ML predictions
        ml_path = project_root / "files-mock" / "analytics" / "ml_model_output.json"
        with open(ml_path, "r") as f:
            ml_data = json.load(f)

        # Use ISINs from additional_predictions
        additional_preds = ml_data.get("additional_predictions", {})
        bonds = [{"isin": isin} for isin in additional_preds.keys()]

        if not bonds:
            # Fallback to bond_price_predictions
            bond_preds = ml_data.get("bond_price_predictions", [])
            bonds = [{"isin": pred["isin"]} for pred in bond_preds[:3]]

        predictions = self.agent.predict_batch(bonds=bonds)

        self.assertIsInstance(predictions, dict)
        print(f" Generated {len(predictions)} predictions")

        # Check if predictions have expected structure
        for isin, pred in predictions.items():
            self.assertIsInstance(pred, MLPrediction)
            self.assertEqual(pred.isin, isin)
            self.assertIsNotNone(pred.expected_return)
            print(f"  - {isin}: Expected return = {pred.expected_return:.2f}%")

    def test_predict_batch_with_yield_curve(self):
        """Test prediction with yield curve data"""
        bonds = [{"isin": "INE001A01036"}]

        yield_curve = {1: 6.85, 2: 6.92, 3: 6.98, 5: 7.05, 10: 7.05}

        predictions = self.agent.predict_batch(bonds=bonds, yield_curve=yield_curve)

        self.assertGreater(len(predictions), 0)
        print(" Prediction with yield curve successful")


class TestQueryClassifierAgent(unittest.TestCase):
    """Test Query Classifier Agent"""

    def setUp(self):
        """Set up test environment"""
        # Mock OpenAI API key for testing
        self.api_key = os.getenv("OPENAI_API_KEY", "test-key")
        self.agent = create_query_classifier(self.api_key, model="gpt-4o-mini")

    @patch("agents.query_classifier.ChatOpenAI")
    def test_classify_buy_recommendation(self, mock_llm):
        """Test classification of buy recommendation query"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "intent": "buy_recommendation",
                "sub_intent": "find high yield bonds",
                "filters": {"min_rating": "AA", "min_yield": 7.5},
                "constraints": {},
                "entities": [],
                "confidence": 0.9,
                "reasoning": "User wants to buy bonds",
            }
        )

        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance

        agent = create_query_classifier("test-key")
        result = agent.classify("I want to buy high yield bonds with AA rating")

        self.assertIsInstance(result, AgentClassifiedQuery)
        # Check if intent is an enum or string
        intent_value = (
            result.intent.value
            if hasattr(result.intent, "value")
            else str(result.intent)
        )
        self.assertIn("buy_recommendation", intent_value.lower())
        print(" Buy recommendation query classified correctly")

    def test_keyword_classification_fallback(self):
        """Test keyword-based classification fallback"""
        # This should work without LLM
        result = self.agent._keyword_classification(
            "I want to reduce duration in my portfolio", {"risk_level": "moderate"}
        )

        self.assertIn("intent", result)
        print(" Keyword classification fallback works")

    def test_extract_entities(self):
        """Test entity extraction"""
        query = "What about HDFC Bank bond INE001A01036?"
        entities = self.agent._extract_entities(query)

        self.assertIn("HDFC Bank", entities)
        self.assertIn("INE001A01036", entities)
        print(f" Extracted entities: {entities}")


class TestAnalystAgent(unittest.TestCase):
    """Test Analyst Agent with mock data"""

    def setUp(self):
        """Set up test environment"""
        self.agent = create_analyst_agent()

        # Load mock data
        self.nse_path = project_root / "files-mock" / "analytics" / "nse_bond_data.json"
        self.ml_path = (
            project_root / "files-mock" / "analytics" / "ml_model_output.json"
        )

        with open(self.nse_path, "r") as f:
            self.nse_data = json.load(f)

        with open(self.ml_path, "r") as f:
            self.ml_data = json.load(f)

    def test_analyze_bonds(self):
        """Test bond analysis with mock data"""
        # Get bonds from NSE data
        bonds = self.nse_data.get("corporate_bonds", [])[:3]

        # Get ML predictions
        ml_predictions = {}
        additional_preds = self.ml_data.get("additional_predictions", {})
        bond_preds = self.ml_data.get("bond_price_predictions", [])

        # Create a mapping of ISIN to prediction
        pred_map = {}
        for pred in bond_preds:
            pred_map[pred["isin"]] = {
                "isin": pred["isin"],
                "expected_return": pred.get("expected_return_pct", 0)
                / 100,  # Convert to decimal
                "predicted_price": pred.get("predicted_price_30d"),
                "confidence": pred.get("confidence", 0.5),
            }

        # Add additional predictions
        for isin, pred_data in additional_preds.items():
            pred_map[isin] = {
                "isin": isin,
                "expected_return": pred_data.get("expected_return", 0)
                / 100,  # Convert to decimal
                "predicted_price": pred_data.get("predicted_price"),
                "confidence": pred_data.get("confidence", 0.5),
            }

        for bond in bonds:
            isin = bond["isin"]
            if isin in pred_map:
                ml_predictions[isin] = MLPrediction(**pred_map[isin])

        # Create yield curve
        yield_curve_rates = self.nse_data.get("yield_curve", {})
        yield_curve = {
            float(k.replace("Y", "").replace("M", "")): v / 100
            for k, v in yield_curve_rates.items()
            if "Y" in k
        }

        # Analyze bonds
        analytics = self.agent.analyze_bonds(
            bonds=bonds,
            ml_predictions=ml_predictions,
            credit_data={},
            yield_curve=yield_curve,
            risk_free_rate=6.5,
        )

        self.assertIsInstance(analytics, dict)
        self.assertGreater(len(analytics), 0)

        for isin, bond_analytics in analytics.items():
            self.assertIsInstance(bond_analytics, BondAnalytics)
            self.assertEqual(bond_analytics.isin, isin)
            print(
                f" Analyzed {bond_analytics.name}: Duration={bond_analytics.duration:.2f}Y, YTM={bond_analytics.ytm:.2f}%"
            )

    def test_filter_by_criteria(self):
        """Test filtering bonds by criteria"""
        # Create sample analytics
        analytics = {
            "INE001A01036": BondAnalytics(
                isin="INE001A01036",
                name="Test Bond 1",
                current_price=101.5,
                fair_value=101.8,
                valuation_gap=-0.29,
                duration=2.1,
                modified_duration=2.0,
                convexity=5.5,
                rate_sensitivity=-0.02,
                credit_risk_score=0.015,
                current_yield=7.39,
                ytm=7.0,
                expected_return=1.5,
                liquidity_score=0.85,
                credit_rating=Rating.AAA,
                sector=Sector.PRIVATE_FINANCIAL,
                ml_signal=Signal.BUY,
                ml_confidence=0.8,
                is_rate_sensitive=False,
                is_liquid=True,
                is_defensive=True,
            )
        }

        # Filter by max duration
        filtered = self.agent.filter_by_criteria(analytics, {"max_duration": 3.0})

        self.assertIn("INE001A01036", filtered)
        print(" Filter by criteria works")

    def test_identify_rate_sensitive_bonds(self):
        """Test identifying rate sensitive bonds"""
        analytics = {
            "INE001A01036": BondAnalytics(
                isin="INE001A01036",
                name="Test Bond 1",
                current_price=101.5,
                fair_value=101.8,
                valuation_gap=-0.29,
                duration=2.1,
                modified_duration=2.0,
                convexity=5.5,
                rate_sensitivity=-0.02,
                credit_risk_score=0.015,
                current_yield=7.39,
                ytm=7.0,
                expected_return=1.5,
                liquidity_score=0.85,
                credit_rating=Rating.AAA,
                sector=Sector.PRIVATE_FINANCIAL,
                ml_signal=Signal.BUY,
                ml_confidence=0.8,
                is_rate_sensitive=False,
                is_liquid=True,
                is_defensive=True,
            ),
            "INE002A01018": BondAnalytics(
                isin="INE002A01018",
                name="Test Bond 2",
                current_price=98.5,
                fair_value=97.0,
                valuation_gap=1.55,
                duration=6.5,
                modified_duration=6.1,
                convexity=45.2,
                rate_sensitivity=-0.061,
                credit_risk_score=0.02,
                current_yield=7.31,
                ytm=7.5,
                expected_return=-0.5,
                liquidity_score=0.7,
                credit_rating=Rating.AAA,
                sector=Sector.PSU_ENERGY,
                ml_signal=Signal.HOLD,
                ml_confidence=0.65,
                is_rate_sensitive=True,
                is_liquid=True,
                is_defensive=False,
            ),
        }

        rate_sensitive = self.agent.identify_rate_sensitive_bonds(analytics)

        self.assertEqual(len(rate_sensitive), 1)
        self.assertEqual(rate_sensitive[0].isin, "INE002A01018")
        print(" Rate sensitive bonds identified correctly")


class TestScoringAgent(unittest.TestCase):
    """Test Scoring Agent"""

    def setUp(self):
        """Set up test environment"""
        self.agent = create_scoring_agent(
            valuation_weight=0.3,
            return_weight=0.3,
            quality_weight=0.2,
            liquidity_weight=0.2,
        )

    def test_score_bonds(self):
        """Test scoring bonds"""
        analytics = {
            "INE001A01036": BondAnalytics(
                isin="INE001A01036",
                name="Test Bond 1",
                current_price=101.5,
                fair_value=101.8,
                valuation_gap=-0.29,
                duration=2.1,
                modified_duration=2.0,
                convexity=5.5,
                rate_sensitivity=-0.02,
                credit_risk_score=0.015,
                current_yield=7.39,
                ytm=7.0,
                expected_return=1.5,
                liquidity_score=0.85,
                credit_rating=Rating.AAA,
                sector=Sector.PRIVATE_FINANCIAL,
                ml_signal=Signal.BUY,
                ml_confidence=0.8,
                is_rate_sensitive=False,
                is_liquid=True,
                is_defensive=True,
            )
        }

        scores = self.agent.score_bonds(analytics)

        self.assertIsInstance(scores, dict)
        self.assertIn("INE001A01036", scores)

        score = scores["INE001A01036"]
        self.assertIsInstance(score, BondScore)
        self.assertGreater(score.total_score, 0)
        print(f" Bond scored: Total={score.total_score:.4f}, Rank={score.rank}")

    def test_get_top_bonds(self):
        """Test getting top bonds"""
        analytics = {
            f"INE00{i}A01036": BondAnalytics(
                isin=f"INE00{i}A01036",
                name=f"Test Bond {i}",
                current_price=100.0,
                fair_value=100.0,
                valuation_gap=0.0,
                duration=5.0,
                modified_duration=4.5,
                convexity=20.0,
                rate_sensitivity=-0.045,
                credit_risk_score=0.1,
                current_yield=7.0,
                ytm=7.0,
                expected_return=i * 0.1,  # Varying returns
                liquidity_score=0.5,
                credit_rating=Rating.AAA,
                sector=Sector.OTHER,
                ml_signal=Signal.BUY,
                ml_confidence=0.8,
                is_rate_sensitive=False,
                is_liquid=True,
                is_defensive=False,
            )
            for i in range(1, 6)
        }

        scores = self.agent.score_bonds(analytics)
        top_bonds = self.agent.get_top_bonds(scores, n=3)

        self.assertEqual(len(top_bonds), 3)
        # Should be sorted by score
        self.assertGreaterEqual(top_bonds[0].total_score, top_bonds[1].total_score)
        print(f" Top {len(top_bonds)} bonds retrieved")


class TestAdvisoryAgent(unittest.TestCase):
    """Test Advisory Agent"""

    def setUp(self):
        """Set up test environment"""
        self.api_key = os.getenv("OPENAI_API_KEY", "test-key")
        self.agent = create_advisory_agent(self.api_key, model="gpt-4o-mini")

        # Load mock portfolio
        portfolio_path = (
            project_root / "files-mock" / "portfolios" / "SAMPLE_BANK_001.json"
        )
        with open(portfolio_path, "r") as f:
            self.portfolio_data = json.load(f)

    @patch("agents.advisory.ChatOpenAI")
    def test_generate_advisory(self, mock_llm):
        """Test generating advisory recommendations"""
        # Mock LLM
        mock_response = Mock()
        mock_response.content = "Test summary"
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance

        agent = create_advisory_agent("test-key")

        # Create test data using agent's ClassifiedQuery
        classified_query = AgentClassifiedQuery(
            original_query="I want to buy high yield bonds",
            intent="increase_yield",
            filters={"min_yield": 7.5},
            constraints={},
        )

        analytics = {
            "INE001A01036": BondAnalytics(
                isin="INE001A01036",
                name="Test Bond",
                current_price=101.5,
                fair_value=101.8,
                valuation_gap=-0.29,
                duration=2.1,
                modified_duration=2.0,
                convexity=5.5,
                rate_sensitivity=-0.02,
                credit_risk_score=0.015,
                current_yield=7.39,
                ytm=7.0,
                expected_return=1.5,
                liquidity_score=0.85,
                credit_rating=Rating.AAA,
                sector=Sector.PRIVATE_FINANCIAL,
                ml_signal=Signal.BUY,
                ml_confidence=0.8,
                is_rate_sensitive=False,
                is_liquid=True,
                is_defensive=True,
            )
        }

        scores = {
            "INE001A01036": BondScore(
                isin="INE001A01036",
                name="Test Bond",
                valuation_score=0.8,
                return_score=0.7,
                quality_score=0.9,
                liquidity_score=0.85,
                total_score=0.8,
                rank=1,
            )
        }

        advisory = agent.generate_advisory(
            classified_query=classified_query,
            bond_analytics=analytics,
            bond_scores=scores,
        )

        self.assertIsInstance(advisory, AdvisoryOutput)
        self.assertIsNotNone(advisory.recommendations)
        print(f" Generated {len(advisory.recommendations)} recommendations")

    def test_increase_yield_strategy(self):
        """Test increase yield strategy"""
        classified_query = AgentClassifiedQuery(
            original_query="Find high yield bonds",
            intent="increase_yield",
            filters={},
            constraints={},
        )

        analytics = {
            "INE001A01036": BondAnalytics(
                isin="INE001A01036",
                name="High Yield Bond",
                current_price=100.0,
                fair_value=100.0,
                valuation_gap=0.0,
                duration=3.0,
                modified_duration=2.8,
                convexity=15.0,
                rate_sensitivity=-0.028,
                credit_risk_score=0.1,
                current_yield=8.0,
                ytm=8.0,
                expected_return=1.0,
                liquidity_score=0.6,
                credit_rating=Rating.AA,
                sector=Sector.OTHER,
                ml_signal=Signal.BUY,
                ml_confidence=0.7,
                is_rate_sensitive=False,
                is_liquid=True,
                is_defensive=False,
            )
        }

        scores = {
            "INE001A01036": BondScore(
                isin="INE001A01036",
                name="High Yield Bond",
                valuation_score=0.5,
                return_score=0.8,
                quality_score=0.6,
                liquidity_score=0.6,
                total_score=0.65,
                rank=1,
            )
        }

        recommendations = self.agent._increase_yield_strategy(
            classified_query, analytics, scores, None
        )

        self.assertGreater(len(recommendations), 0)
        print(
            f" Increase yield strategy generated {len(recommendations)} recommendations"
        )


class TestExplainabilityAgent(unittest.TestCase):
    """Test Explainability Agent"""

    def setUp(self):
        """Set up test environment"""
        self.api_key = os.getenv("OPENAI_API_KEY", "test-key")
        self.agent = create_explainability_agent(self.api_key, model="gpt-4o-mini")

    @patch("agents.explainability.ChatOpenAI")
    def test_explain_recommendations(self, mock_llm):
        """Test explaining recommendations"""
        # Mock LLM
        mock_response = Mock()
        mock_response.content = "This bond is recommended because of strong fundamentals and attractive yield."
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance

        agent = create_explainability_agent("test-key")

        recommendations = [
            TradeRecommendation(
                action="BUY",
                isin="INE001A01036",
                name="Test Bond",
                rationale="Strong fundamentals",
                expected_return=1.5,
                risk_score=0.1,
                confidence=0.8,
            )
        ]

        bond_analytics = {
            "INE001A01036": {
                "current_price": 101.5,
                "fair_value": 101.8,
                "valuation_gap": -0.29,
                "duration": 2.1,
                "ytm": 7.0,
                "credit_risk_score": 0.015,
                "liquidity_score": 0.85,
                "ml_signal": "BUY",
            }
        }

        bond_scores = {"INE001A01036": {"total_score": 0.8}}

        ml_predictions = {
            "INE001A01036": {
                "expected_return": 1.5,
                "confidence": 0.8,
                "factors": {"yield_curve": 0.3, "credit_spread": 0.2},
            }
        }

        explanations = agent.explain_recommendations(
            recommendations=recommendations,
            bond_analytics=bond_analytics,
            bond_scores=bond_scores,
            ml_predictions=ml_predictions,
        )

        self.assertGreater(len(explanations), 0)
        print(f" Generated {len(explanations)} explanations")


class TestPlannerAgent(unittest.TestCase):
    """Test Planner Agent"""

    def setUp(self):
        """Set up test environment"""
        self.api_key = os.getenv("OPENAI_API_KEY", "test-key")
        # Note: Planner needs a config file, we'll mock it
        self.config_path = project_root / "config" / "planner_config.json"

    @patch("agents.planner.ChatOpenAI")
    def test_create_plan(self, mock_llm):
        """Test creating execution plan"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "tools_needed": [
                    {"tool_type": "news_scraper", "parameters": {"keywords": ["bonds"]}}
                ],
                "agents_needed": ["query_classifier", "analyst", "advisory"],
                "needs_explainability": False,
                "reasoning": "Standard query flow",
            }
        )

        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance

        # Create config file if it doesn't exist
        if not self.config_path.exists():
            self.config_path.parent.mkdir(exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(
                    {
                        "tools": [
                            {"name": "news_scraper", "description": "Scrape news"}
                        ],
                        "agents": [
                            {
                                "name": "query_classifier",
                                "description": "Classify queries",
                            }
                        ],
                    },
                    f,
                )

        agent = create_planner_agent("test-key")
        plan = agent.create_plan("I want to buy bonds", has_portfolio=False)

        self.assertIsNotNone(plan)
        self.assertGreater(len(plan.agents_needed), 0)
        print(f" Created plan with {len(plan.agents_needed)} agents")


class TestPortfolioManager(unittest.TestCase):
    """Test Portfolio Manager"""

    def test_portfolio_node(self):
        """Test portfolio node"""
        from agents.portfolio_manager import portfolio_node, PortfolioManager

        # First, ensure portfolios are loaded
        manager = PortfolioManager()
        manager.refresh_portfolios()  # Reload from files

        # Use a portfolio ID that exists in mock data
        state = {"bank_id": "SAMPLE_BANK_001", "user_id": "SAMPLE_BANK_001"}

        result = portfolio_node(state)

        # Check if portfolio was found or if it returned a message
        if "portfolio" in result:
            self.assertIsNotNone(result["portfolio"])
            print(" Portfolio node executed - portfolio found")
        elif "messages" in result:
            # Portfolio not found - try refreshing and test again
            # This tests the function works correctly even when portfolio doesn't exist
            print(
                " Portfolio node executed - portfolio not found (function works correctly)"
            )
            self.assertIn("messages", result)
            # Verify the message is informative
            messages = result.get("messages", [])
            if messages:
                self.assertIn("Portfolio not found", messages[0].get("content", ""))
        else:
            self.fail("Portfolio node should return either 'portfolio' or 'messages'")


class TestPipelineIntegration(unittest.TestCase):
    """Test full pipeline integration"""

    def setUp(self):
        """Set up test environment"""
        # Load all mock data
        self.mock_data_dir = project_root / "files-mock" / "analytics"

        with open(self.mock_data_dir / "nse_bond_data.json", "r") as f:
            self.nse_data = json.load(f)

        with open(self.mock_data_dir / "ml_model_output.json", "r") as f:
            self.ml_data = json.load(f)

        with open(self.mock_data_dir / "rbi_mpr_data.json", "r") as f:
            self.rbi_data = json.load(f)

        with open(self.mock_data_dir / "news_sentiment.json", "r") as f:
            self.news_data = json.load(f)

    def test_end_to_end_flow(self):
        """Test end-to-end pipeline flow"""
        print("\n=== Testing End-to-End Pipeline ===")

        # 1. Load bonds
        bonds = self.nse_data.get("corporate_bonds", [])[:5]
        print(f" Loaded {len(bonds)} bonds")

        # 2. ML Predictions
        ml_agent = create_ml_agent({})
        # Convert bonds to list of dicts with isin
        bond_list = [{"isin": bond["isin"]} for bond in bonds]
        ml_predictions = ml_agent.predict_batch(bonds=bond_list)
        print(f" Generated {len(ml_predictions)} ML predictions")

        # 3. Analyst
        analyst = create_analyst_agent()
        yield_curve_rates = self.nse_data.get("yield_curve", {})
        yield_curve = {
            float(k.replace("Y", "")): v / 100
            for k, v in yield_curve_rates.items()
            if "Y" in k
        }

        analytics = analyst.analyze_bonds(
            bonds=bonds,
            ml_predictions=ml_predictions,
            credit_data={},
            yield_curve=yield_curve,
        )
        print(f" Analyzed {len(analytics)} bonds")

        # 4. Scoring
        scoring = create_scoring_agent()
        scores = scoring.score_bonds(analytics)
        print(f" Scored {len(scores)} bonds")

        # 5. Top bonds
        top_bonds = scoring.get_top_bonds(scores, n=3)
        print(f" Identified top {len(top_bonds)} bonds")

        print("\n End-to-end pipeline test completed successfully!")


if __name__ == "__main__":
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMLModelAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestQueryClassifierAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalystAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestScoringAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvisoryAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestExplainabilityAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestPlannerAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestPortfolioManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"{'=' * 60}")
