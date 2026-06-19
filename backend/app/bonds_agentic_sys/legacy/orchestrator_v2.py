"""
Orchestrator V2 - Production-Grade Multi-Agent System
Integrates Planner, Tools, RAG, and Conditional Agents
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from schemas_v2 import (
    EnhancedAgentState,
    SystemConfigV2,
    ExecutionPlan,
    ToolType,
    AgentType,
    ToolResult,
    AdvisoryOutput,
    ClassifiedQuery,
    UserPortfolio,
    Portfolio,
    Position,
    RAGQuery,
    BondAnalytics,
)
import os
import json
import time
import traceback
import asyncio


# Import agents
from agents.planner import create_planner_agent
from agents.query_classifier import create_query_classifier
from agents.ml_model import create_ml_agent
from agents.analyst import AnalystAgent
from agents.scoring import ScoringAgent
from agents.advisory import create_advisory_agent
from agents.explainability import create_explainability_agent

# Import tools
from tools.tools_manager import (
    create_news_scraper,
    create_web_search,
    create_crisil_scraper,
    create_portfolio_manager,
    create_yield_forecaster,
    create_bond_pricer,
)
from dotenv import load_dotenv

load_dotenv()

# Import RAG
from rag.rag_system import RAGSystem


class OrchestratorV2:
    """
    Production orchestrator with intelligent planning and conditional execution
    """

    def __init__(self, config: SystemConfigV2, rag_system: Optional[RAGSystem] = None):
        self.config = config
        self.rag = rag_system

        # Initialize agents
        print("Initializing agents...")
        self.planner = create_planner_agent(config.openai_api_key, config.llm_model)
        self.query_classifier = create_query_classifier(
            config.openai_api_key, config.llm_model
        )
        self.ml_agent = create_ml_agent(config)
        self.analyst = AnalystAgent()
        self.scoring = ScoringAgent(
            valuation_weight=config.valuation_weight,
            return_weight=config.return_weight,
            quality_weight=config.quality_weight,
            liquidity_weight=config.liquidity_weight,
        )
        self.advisory = create_advisory_agent(config.openai_api_key, config.llm_model)
        self.explainability = create_explainability_agent(
            config.openai_api_key, config.llm_model
        )

        # Agent execution map
        self.agent_map = {
            AgentType.QUERY_CLASSIFIER: self._run_query_classifier,
            AgentType.ML_MODEL: self._run_ml_model,
            AgentType.ANALYST: self._run_analyst,
            AgentType.SCORING: self._run_scoring,
            AgentType.ADVISORY: self._run_advisory,
            AgentType.EXPLAINABILITY: self._run_explainability,
        }

        # Initialize tools
        print("Initializing tools...")
        self.tools = {
            ToolType.NEWS_SCRAPER: create_news_scraper(),
            ToolType.WEB_SEARCH: create_web_search(config.serpapi_key),
            ToolType.CRISIL_SCRAPER: create_crisil_scraper(),
            ToolType.PORTFOLIO_MANAGER: create_portfolio_manager(
                config.portfolio_db_path
            ),
            ToolType.YIELD_FORECASTER: create_yield_forecaster(),
            ToolType.BOND_PRICER: create_bond_pricer(),
        }

        print(" Orchestrator V2 ready")

    async def run_async(
        self,
        query: str,
        user_id: str,
        bonds_universe: Optional[list] = None,
        user_profile: Optional[Dict] = None,
    ) -> EnhancedAgentState:
        """
        Async execution of complete pipeline

        Args:
            query: User's natural language query
            user_id: User identifier
            bonds_universe: List of bonds to analyze
            user_profile: User preferences

        Returns:
            EnhancedAgentState with all results
        """
        start_time = time.time()

        # Check if query is bond-related
        bond_keywords = [
            "bond",
            "yield",
            "duration",
            "credit",
            "rating",
            "portfolio",
            "invest",
            "buy",
            "sell",
            "hold",
            "isin",
            "maturity",
            "coupon",
            "g-sec",
            "corporate",
            "psu",
            "sovereign",
            "interest rate",
            "spread",
            "liquidity",
            "risk",
            "return",
            "recommendation",
        ]
        query_lower = query.lower()
        is_bond_query = any(keyword in query_lower for keyword in bond_keywords)

        # If not bond-related, return early with appropriate message
        if not is_bond_query:
            state = EnhancedAgentState(
                user_query=query, user_id=user_id, timestamp=datetime.now()
            )
            # Create a simple advisory output with a message
            from schemas_v2 import AdvisoryOutput, TradeRecommendation

            state.advisory = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=f"I'm a bond trading assistant. Your query '{query}' doesn't appear to be related to bonds or fixed income investments. Please ask me about bonds, portfolios, yields, credit ratings, or investment recommendations.",
                timestamp=datetime.now(),
            )
            state.processing_time = time.time() - start_time
            return state

        # Initialize state
        state = EnhancedAgentState(
            user_query=query, user_id=user_id, timestamp=datetime.now()
        )

        try:
            # STEP 1: Create execution plan
            print(f"\n{'=' * 80}")
            print(f"🧠 PLANNER: Analyzing query...")

            has_portfolio = await self._check_portfolio_exists(user_id)
            try:
                plan = self.planner.create_plan(
                    query=query, has_portfolio=has_portfolio
                )
                state.execution_plan = plan
            except Exception as e:
                print(f" Error creating plan: {e}")
                # Create a default plan as fallback
                from schemas_v2 import ToolCall, AgentType, DataSource

                state.execution_plan = ExecutionPlan(
                    plan_id=f"fallback_{hash(query) % 10000}",
                    query=query,
                    intent="custom",
                    tools_needed=[],
                    agents_needed=[
                        AgentType.QUERY_CLASSIFIER,
                        AgentType.ML_MODEL,
                        AgentType.ANALYST,
                        AgentType.SCORING,
                        AgentType.ADVISORY,
                    ],
                    data_sources=[DataSource.NSE],
                    needs_explainability=False,
                    needs_rag=False,
                    needs_portfolio_access=has_portfolio,
                    reasoning="Fallback plan due to planning error",
                )
                plan = state.execution_plan

            print(f" Plan created:")
            print(f"  - Tools: {[t.tool_type.value for t in plan.tools_needed]}")
            print(f"  - Agents: {[a.value for a in plan.agents_needed]}")
            print(f"  - Explainability: {plan.needs_explainability}")
            print(f"  - Reasoning: {plan.reasoning}")

            # STEP 2: Execute tools in parallel
            if plan.tools_needed:
                print(
                    f"\nTOOLS: Executing {len(plan.tools_needed)} tools in parallel..."
                )
                tool_results = await self._execute_tools_parallel(
                    plan, user_id, state, bonds_universe=bonds_universe
                )
                state.tool_results = tool_results
                state.total_tool_calls = len(tool_results)

                # Count cache hits
                state.cache_hits = sum(1 for r in tool_results.values() if r.cached)
                print(
                    f" Tools completed (Cache hits: {state.cache_hits}/{len(tool_results)})"
                )

            # STEP 3: Execute agents sequentially
            print(f"\n AGENTS: Executing pipeline...")

            # Default bonds if not provided
            if bonds_universe is None:
                bonds_universe = self._get_default_bonds()

            # Ensure required agents run even if not in plan
            # Import AgentType here to avoid scope issues
            from schemas_v2 import AgentType as AgentTypeEnum

            required_agents = [
                AgentTypeEnum.QUERY_CLASSIFIER,
                AgentTypeEnum.ML_MODEL,
                AgentTypeEnum.ANALYST,
                AgentTypeEnum.SCORING,
                AgentTypeEnum.ADVISORY,
            ]

            # Combine plan agents with required agents (avoid duplicates)
            agents_to_run = []
            seen = set()
            for agent_type in plan.agents_needed:
                if agent_type not in seen:
                    agents_to_run.append(agent_type)
                    seen.add(agent_type)

            # Add required agents that weren't in the plan
            for agent_type in required_agents:
                if agent_type not in seen:
                    agents_to_run.append(agent_type)
                    seen.add(agent_type)

            for agent_type in agents_to_run:
                if agent_type in self.agent_map:
                    try:
                        await self.agent_map[agent_type](
                            state,
                            bonds_universe=bonds_universe,
                            plan=plan,
                            user_profile=user_profile,
                        )
                    except Exception as e:
                        print(f" Error in agent {agent_type.value}: {e}")
                        import traceback

                        traceback.print_exc()
                        # Continue with other agents even if one fails
                        continue

            print(f" All agents completed")

        except Exception as e:
            print(f" Error: {e}")
            import traceback

            traceback.print_exc()

        # Calculate total time
        state.processing_time = time.time() - start_time

        print(f"\n{'=' * 80}")
        print(f" COMPLETE in {state.processing_time:.2f}s")
        print(f"   Cache hits: {state.cache_hits}/{state.total_tool_calls}")
        print(
            f"   Recommendations: {len(state.advisory.recommendations) if state.advisory else 0}"
        )
        print(f"   Explanations: {len(state.explanations)}")
        print(f"{'=' * 80}\n")

        return state

    async def _run_query_classifier(self, state: EnhancedAgentState, **kwargs):
        print(f"  1⃣ Query Classifier...")
        state.classified_query = self.query_classifier.classify(
            state.user_query, kwargs.get("user_profile")
        )

    async def _run_ml_model(self, state: EnhancedAgentState, **kwargs):
        print(f"  2⃣ ML Model (with your forecasts)...")
        mock_ml_output = "files-mock/analytics/ml_model_output.json"
        if os.path.exists(mock_ml_output):
            # Use ML agent to properly parse and convert to MLPrediction objects
            state.ml_predictions = self.ml_agent.predict_batch(
                bonds=kwargs.get("bonds_universe", []),
                yield_curve=None,
                rbi_policy=None,
                news_items=None,
            )
            print(
                f"     Loaded {len(state.ml_predictions)} ML predictions from mock data."
            )
        else:
            yield_forecast_result = state.tool_results.get(ToolType.YIELD_FORECASTER)
            state.ml_predictions = self.ml_agent.predict_batch(
                bonds=kwargs.get("bonds_universe", []),
                yield_curve=yield_forecast_result.data
                if yield_forecast_result and yield_forecast_result.success
                else None,
                rbi_policy=self._extract_rbi_from_rag(state),
                news_items=[article.dict() for article in state.news_articles],
            )

    async def _run_analyst(self, state: EnhancedAgentState, **kwargs):
        print(f"  3⃣ Analyst...")
        mock_analyst_output = "files-mock/analytics/analyst_output.json"

        # Get yield curve from forecasts or default
        yield_curve = self._get_yield_curve()
        if state.yield_forecasts:
            # Convert YieldCurveForecast to dict
            yield_curve = {
                f.maturity_years: f.predicted_yield
                for f in state.yield_forecasts.forecasts
            }

        # Get bond price forecasts if available
        bond_price_forecasts = state.bond_price_forecasts or {}

        if os.path.exists(mock_analyst_output):
            with open(mock_analyst_output, "r") as f:
                analytics_data = json.load(f)
            # Convert dict to BondAnalytics objects
            state.bond_analytics = {
                k: BondAnalytics(**v) for k, v in analytics_data.items()
            }
            print("     Loaded mock analyst data.")
        else:
            state.bond_analytics = self.analyst.analyze_bonds(
                bonds=kwargs.get("bonds_universe", []),
                ml_predictions=state.ml_predictions,
                credit_data=state.credit_ratings,
                yield_curve=yield_curve,
            )

    async def _run_scoring(self, state: EnhancedAgentState, **kwargs):
        print(f"  4⃣ Scoring...")
        state.bond_scores = self.scoring.score_bonds(state.bond_analytics)

    async def _run_advisory(self, state: EnhancedAgentState, **kwargs):
        print(f"  5⃣ Advisory...")
        # Always use real advisory agent, don't load mock data
        # This ensures recommendations are based on actual query and analytics
        if state.classified_query:
            portfolio_to_pass = None
            if state.portfolio:
                # Convert UserPortfolio to the simpler Portfolio for the agent
                positions = [Position(**p.dict()) for p in state.portfolio.holdings]
                portfolio_to_pass = Portfolio(
                    portfolio_id=state.portfolio.portfolio_id,
                    name=state.portfolio.user_id,
                    positions=positions,
                    total_value=state.portfolio.total_value,
                    cash=state.portfolio.cash,
                )

            state.advisory = self.advisory.generate_advisory(
                classified_query=state.classified_query,
                bond_analytics=state.bond_analytics,
                bond_scores=state.bond_scores,
                portfolio=portfolio_to_pass,
            )

    async def _run_explainability(self, state: EnhancedAgentState, **kwargs):
        print(f"  6⃣ Explainability...")
        plan = kwargs.get("plan")
        if plan and plan.needs_explainability and state.advisory:
            state.explanations = self.explainability.explain_recommendations(
                recommendations=state.advisory.recommendations,
                bond_analytics=state.bond_analytics,
                bond_scores=state.bond_scores,
                ml_predictions=state.ml_predictions,
                rbi_policy=self._extract_rbi_from_rag(state),
                news_items=[article.dict() for article in state.news_articles],
                credit_ratings=state.credit_ratings,
            )

    async def _execute_tools_parallel(
        self,
        plan: ExecutionPlan,
        user_id: str,
        state: EnhancedAgentState,
        bonds_universe: Optional[List[Dict]] = None,
    ) -> Dict[ToolType, ToolResult]:
        """
        Execute all needed tools in parallel
        """
        tasks = []
        tool_types = []

        for tool_call in plan.tools_needed:
            tool_type = tool_call.tool_type
            params = tool_call.parameters

            if tool_type == ToolType.NEWS_SCRAPER:
                # Extract only valid parameters
                keywords = params.get("keywords")
                max_articles = params.get("max_articles", 50)
                hours_back = params.get("hours_back", 24)
                tasks.append(
                    self.tools[tool_type].scrape_news(
                        keywords=keywords,
                        max_articles=max_articles,
                        hours_back=hours_back,
                    )
                )
                tool_types.append(tool_type)

            elif tool_type == ToolType.WEB_SEARCH:
                query = params.get("query") or params.get("search_query", "")
                num_results = params.get("num_results", 10)
                tasks.append(
                    self.tools[tool_type].search(query=query, num_results=num_results)
                )
                tool_types.append(tool_type)

            elif tool_type == ToolType.CRISIL_SCRAPER:
                # Extract only valid parameters for scrape_rating
                company_name = (
                    params.get("company_name")
                    or params.get("company")
                    or params.get("name", "")
                )
                isin = params.get("isin")
                tasks.append(
                    self.tools[tool_type].scrape_rating(
                        company_name=company_name, isin=isin
                    )
                )
                tool_types.append(tool_type)

            elif tool_type == ToolType.PORTFOLIO_MANAGER:
                tasks.append(self.tools[tool_type].get_portfolio(user_id))
                tool_types.append(tool_type)

            elif tool_type == ToolType.RAG_RETRIEVER:
                if self.rag:
                    rag_query = RAGQuery(query_text=params.get("query", plan.query))
                    tasks.append(self.rag.retrieve(rag_query))
                    tool_types.append(tool_type)

            elif tool_type == ToolType.YIELD_FORECASTER:
                maturities = params.get("maturities")
                horizon_days = params.get("horizon_days", 14)
                tasks.append(
                    self.tools[tool_type].forecast_yield_curve(maturities, horizon_days)
                )
                tool_types.append(tool_type)

            elif tool_type == ToolType.BOND_PRICER:
                # Get bonds from params or from bonds_universe parameter
                bonds = params.get("bonds", bonds_universe or [])
                forecast_days = params.get("forecast_days", 30)
                tasks.append(
                    self.tools[tool_type].forecast_bond_prices(bonds, forecast_days)
                )
                tool_types.append(tool_type)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        tool_results: Dict[ToolType, ToolResult] = {}
        for tool_type, result in zip(tool_types, results):
            if isinstance(result, Exception):
                tool_results[tool_type] = ToolResult(
                    tool_type=tool_type, success=False, data=None, error=str(result)
                )
            else:
                # Now, result is guaranteed to be a ToolResult
                tool_results[tool_type] = result

                # Update state with specific data
                if result.success:
                    if tool_type == ToolType.NEWS_SCRAPER:
                        state.news_articles = result.data
                    elif tool_type == ToolType.PORTFOLIO_MANAGER:
                        state.portfolio = result.data
                    elif tool_type == ToolType.RAG_RETRIEVER:
                        state.rag_results = result.data
                    elif tool_type == ToolType.CRISIL_SCRAPER:
                        if result.data and getattr(result.data, "isin", None):
                            state.credit_ratings[result.data.isin] = result.data
                    elif tool_type == ToolType.YIELD_FORECASTER:
                        state.yield_forecasts = result.data
                    elif tool_type == ToolType.BOND_PRICER:
                        state.bond_price_forecasts = result.data

        return tool_results

    async def _check_portfolio_exists(self, user_id: str) -> bool:
        """Check if user has a portfolio"""
        try:
            result = await self.tools[ToolType.PORTFOLIO_MANAGER].get_portfolio(user_id)
            return result.success
        except:
            return False

    def _extract_rbi_from_rag(self, state: EnhancedAgentState) -> Optional[Dict]:
        """Extract RBI policy from RAG results"""
        if not state.rag_results:
            return None

        # Parse RAG chunks for RBI data
        rbi_data = {
            "repo_rate": 6.5,  # Default
            "stance": "neutral",
            "CPI_forecast": 4.5,
            "forward_guidance": "Data dependent",
        }

        # TODO: Parse from RAG chunks

        return rbi_data

    def _get_yield_curve(self) -> Dict[float, float]:
        """Get current yield curve"""
        # Default yield curve (would come from data in production)
        return {
            0.5: 0.060,
            1.0: 0.065,
            2.0: 0.068,
            5.0: 0.072,
            7.0: 0.074,
            10.0: 0.076,
            15.0: 0.078,
        }

    def _get_default_bonds(self) -> list:
        """Get default bond universe for testing"""
        from datetime import datetime, timedelta

        bonds = [
            {
                "isin": "INE001A01036",
                "name": "HDFC Bank 7.50% 2025",
                "issuer": "HDFC Bank",
                "bond_type": "Corporate",
                "sector": "Financial",
                "coupon_rate": 0.075,
                "maturity_date": (datetime.now() + timedelta(days=365)).strftime(
                    "%Y-%m-%d"
                ),
                "last_traded_price": 101.5,
                "ytm": 0.070,
                "rating": "AAA",
                "volume": 5000000,
                "duration": 2.1,
                "years_to_maturity": 1.0,
            },
            {
                "isin": "INE002A01018",
                "name": "NTPC 7.20% 2030",
                "issuer": "NTPC",
                "bond_type": "PSU",
                "sector": "PSU_Energy",
                "coupon_rate": 0.072,
                "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                    "%Y-%m-%d"
                ),
                "last_traded_price": 98.5,
                "ytm": 0.075,
                "rating": "AAA",
                "volume": 3000000,
                "duration": 6.5,
                "years_to_maturity": 5.0,
            },
            {
                "isin": "INE003A01024",
                "name": "G-Sec 7.06% 2028",
                "issuer": "Government of India",
                "bond_type": "G-Sec",
                "sector": "Sovereign",
                "coupon_rate": 0.0706,
                "maturity_date": (datetime.now() + timedelta(days=1095)).strftime(
                    "%Y-%m-%d"
                ),
                "last_traded_price": 100.2,
                "ytm": 0.070,
                "rating": "AAA",
                "volume": 10000000,
                "duration": 4.2,
                "years_to_maturity": 3.0,
            },
            {
                "isin": "INE004A01030",
                "name": "SBI 7.35% 2027",
                "issuer": "State Bank of India",
                "bond_type": "PSU",
                "sector": "PSU_Financial",
                "coupon_rate": 0.0735,
                "maturity_date": (datetime.now() + timedelta(days=730)).strftime(
                    "%Y-%m-%d"
                ),
                "last_traded_price": 99.8,
                "ytm": 0.074,
                "rating": "AAA",
                "volume": 8000000,
                "duration": 3.5,
                "years_to_maturity": 2.0,
            },
            {
                "isin": "INE005A01045",
                "name": "REC 7.80% 2032",
                "issuer": "REC Limited",
                "bond_type": "PSU",
                "sector": "PSU_Infrastructure",
                "coupon_rate": 0.078,
                "maturity_date": (datetime.now() + timedelta(days=2555)).strftime(
                    "%Y-%m-%d"
                ),
                "last_traded_price": 97.2,
                "ytm": 0.082,
                "rating": "AA+",
                "volume": 2500000,
                "duration": 8.2,
                "years_to_maturity": 7.0,
            },
            {
                "isin": "INE006A01050",
                "name": "ICICI Bank 7.25% 2026",
                "issuer": "ICICI Bank",
                "bond_type": "Corporate",
                "sector": "Private_Financial",
                "coupon_rate": 0.0725,
                "maturity_date": (datetime.now() + timedelta(days=548)).strftime(
                    "%Y-%m-%d"
                ),
                "last_traded_price": 100.5,
                "ytm": 0.071,
                "rating": "AAA",
                "volume": 4500000,
                "duration": 2.8,
                "years_to_maturity": 1.5,
            },
        ]

        return bonds


def create_orchestrator_v2(
    config: SystemConfigV2, rag_system: Optional[RAGSystem] = None
) -> OrchestratorV2:
    """Factory function"""
    return OrchestratorV2(config, rag_system)
