"""
Tests for the Planner Agent
"""

import sys
import unittest
import os
import json
from unittest.mock import MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.planner import PlannerAgent
from schemas_v2 import ExecutionPlan, ToolType, AgentType


class TestPlannerAgent(unittest.TestCase):
    """Test suite for the PlannerAgent."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_llm = MagicMock()

        # Create a dummy config file
        self.config_path = "test_planner_config.json"
        self.config_data = {
            "tools": [
                {"name": "news_scraper", "description": "Fetches financial news."},
                {
                    "name": "portfolio_manager",
                    "description": "Accesses user portfolio.",
                },
            ],
            "agents": [
                {"name": "query_classifier", "description": "Classifies the query."},
                {"name": "advisory", "description": "Generates recommendations."},
            ],
        }
        with open(self.config_path, "w") as f:
            json.dump(self.config_data, f)

        self.agent = PlannerAgent(llm=self.mock_llm, config_path=self.config_path)

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

    def test_agent_creation_and_config_loading(self):
        """Test if the agent is created and loads config correctly."""
        self.assertIsNotNone(self.agent)
        self.assertIn("news_scraper", [t["name"] for t in self.agent.config["tools"]])
        print(" PlannerAgent created and config loaded successfully")

    def test_create_plan_simple_query(self):
        """Test plan creation for a simple advisory query."""

        # Mock LLM response
        mock_plan_json = {
            "tools_needed": [],
            "agents_needed": ["query_classifier", "advisory"],
            "needs_explainability": False,
            "reasoning": "Simple advisory query requires classification and recommendation.",
        }
        self.mock_llm.invoke.return_value = MagicMock(
            content=json.dumps(mock_plan_json)
        )

        # Create plan
        plan = self.agent.create_plan(query="Recommend some bonds")

        self.assertIsInstance(plan, ExecutionPlan)
        self.assertIn(AgentType.ADVISORY, plan.agents_needed)
        self.assertFalse(plan.needs_explainability)
        self.assertEqual(len(plan.tools_needed), 0)
        print(" Simple plan created successfully")

    def test_create_plan_with_explainability(self):
        """Test plan creation when user asks for explanation."""

        mock_plan_json = {
            "tools_needed": [],
            "agents_needed": ["query_classifier", "advisory", "explainability"],
            "needs_explainability": True,
            "reasoning": "User asked 'why', so explainability is needed.",
        }
        self.mock_llm.invoke.return_value = MagicMock(
            content=json.dumps(mock_plan_json)
        )

        plan = self.agent.create_plan(query="Why should I buy this bond?")

        self.assertTrue(plan.needs_explainability)
        self.assertIn(AgentType.EXPLAINABILITY, plan.agents_needed)
        print(" Plan with explainability created successfully")

    def test_create_plan_with_portfolio_context(self):
        """Test plan creation for a query involving a user's portfolio."""

        mock_plan_json = {
            "tools_needed": [{"tool_type": "portfolio_manager", "parameters": {}}],
            "agents_needed": ["query_classifier", "advisory"],
            "needs_explainability": False,
            "reasoning": "Query mentions 'my portfolio'.",
        }
        self.mock_llm.invoke.return_value = MagicMock(
            content=json.dumps(mock_plan_json)
        )

        plan = self.agent.create_plan(query="Analyze my portfolio", has_portfolio=True)

        self.assertEqual(len(plan.tools_needed), 1)
        self.assertEqual(plan.tools_needed[0].tool_type, ToolType.PORTFOLIO_MANAGER)
        print(" Plan with portfolio context created successfully")

    def test_create_plan_with_mock_data(self):
        """Test plan creation using mock data for a complex query."""

        # Mock LLM response
        mock_plan_json = {
            "tools_needed": [
                {"tool_type": "portfolio_manager", "parameters": {}},
                {
                    "tool_type": "news_scraper",
                    "parameters": {"keywords": ["bonds", "interest rates"]},
                },
            ],
            "agents_needed": ["query_classifier", "analyst", "scoring", "advisory"],
            "needs_explainability": False,
            "reasoning": "Complex query involving portfolio analysis and market news.",
        }
        self.mock_llm.invoke.return_value = MagicMock(
            content=json.dumps(mock_plan_json)
        )

        # Create plan
        plan = self.agent.create_plan(
            query="Analyze my portfolio and give me some recommendations based on the latest news.",
            has_portfolio=True,
        )

        self.assertIsInstance(plan, ExecutionPlan)
        self.assertIn(AgentType.ANALYST, plan.agents_needed)
        self.assertIn(
            ToolType.PORTFOLIO_MANAGER, [t.tool_type for t in plan.tools_needed]
        )
        self.assertIn(ToolType.NEWS_SCRAPER, [t.tool_type for t in plan.tools_needed])
        self.assertFalse(plan.needs_explainability)
        print(" Complex plan with mock data created successfully")


if __name__ == "__main__":
    unittest.main()
