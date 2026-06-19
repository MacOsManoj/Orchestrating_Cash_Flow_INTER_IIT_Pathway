"""
Orchestrator V3 - LangGraph-Based Intelligent Multi-Agent System
Uses LangGraph StateGraph for intelligent routing and conditional execution
"""
from typing import Dict, Any, Optional, List, TypedDict, Annotated
from datetime import datetime
import asyncio
import time
import operator
from utils.mcp_client import (
    create_mcp_client,
    MCPBondsClient,
    check_mcp_connection_sync,
)
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

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
    QueryType,
    Intent,
    NonBondRouting,
)
import os
import json
import traceback
from bond_maturity_filter import MATURITY_FILTER, MaturityFilter
# Import agents
from agents.planner import create_planner_agent
from agents.query_classifier import create_query_classifier
from agents.ml_model import create_ml_agent
from agents.analyst import AnalystAgent
from agents.scoring import ScoringAgent
from agents.advisory import create_advisory_agent
from agents.explainability import create_explainability_agent
from agents.response_agent import create_response_agent
from agents.realtime_info_agent import create_realtime_info_agent
from agents.portfolio_update_parser import create_portfolio_update_parser

# Import tools
from tools.tools_manager import (
    create_news_scraper,
    create_web_search,
    create_crisil_scraper,
    create_portfolio_manager,
)
from dotenv import load_dotenv

load_dotenv()

# Import RAG
from rag.rag_system import RAGSystem

# Import model selector
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
try:
    from utils.context_manager import ContextManager, create_context_manager
except ImportError:
    # Fallback if context_manager not available
    ContextManager = None

    def create_context_manager():
        return None


try:
    from utils.model_selector import (
        ModelSelector,
        AgentType as ModelSelectorAgentType,
        create_model_selector,
    )
except ImportError:
    # Fallback
    ModelSelector = None
    ModelSelectorAgentType = None
    create_model_selector = None

# SessionManager removed - using LangGraph message history instead

# Import guardrails
from tools.guardrails import GuardrailsChecker, create_guardrails_checker, SafetyLevel

# Import agent logger
from utils.agent_logger import AgentLogger

# Import utilities
from utils.logger import setup_logger, get_logger
from utils.state_helpers import StateHelper
from utils.bond_cache import get_bond_cache

# Setup logger
logger = setup_logger(__name__)


def _parse_mcp_result(result):
    """Parse MCP JSON result"""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(
                f"Failed to parse MCP result as JSON: {e}, returning as string"
            )
            return result
    return result


class GraphState(TypedDict):
    """State for LangGraph execution"""
    # Core
    user_query: str
    user_id: str
    user_profile: Optional[Dict[str, Any]]
    bonds_universe: Optional[List[Dict]]
    messages: Annotated[
        List[BaseMessage], add_messages
    ]  # LangGraph conversation history

    # State tracking
    current_step: str
    execution_path: List[str]
    errors: List[str]
    # Query classification
    classified_query: Optional[ClassifiedQuery]
    needs_portfolio: bool
    needs_rag: bool
    needs_explainability: bool

    # Planning
    execution_plan: Optional[ExecutionPlan]

    # Tool results
    tool_results: Dict[ToolType, ToolResult]
    tool_execution_order: List[ToolType]

    # Data
    news_articles: List[Any]
    credit_ratings: Dict[str, Any]
    portfolio: Optional[UserPortfolio]
    yield_forecasts: Optional[Any]
    bond_price_forecasts: Dict[str, Any]
    rag_results: Optional[Any]
    web_search_results: Optional[
        str
    ]  # Formatted real-time market intelligence (web search + news processed by real-time info agent)

    # Agent outputs
    ml_predictions: Dict[str, Any]
    bond_analytics: Dict[str, BondAnalytics]
    bond_scores: Dict[str, Any]
    advisory: Optional[AdvisoryOutput]
    explanations: List[Any]
    # Metadata
    start_time: float
    processing_time: float
    cache_hits: int
    total_tool_calls: int
    timestamp: datetime


class OrchestratorV3:
    """
    Intelligent orchestrator using LangGraph for dynamic routing
    """
    def __init__(
        self,
        config: SystemConfigV2,
        rag_system: Optional[RAGSystem] = None,
        mcp_client: Optional[MCPBondsClient] = None,
        model_selector: Optional[ModelSelector] = None,
    ):
        self.config = config
        self.rag = rag_system
        # Store LangGraph messages for conversation history (thread_id -> messages)
        # This uses LangGraph's message system via BaseMessage objects
        self._message_store: Dict[str, List[BaseMessage]] = {}
        # Context manager
        try:
            self.context_manager = create_context_manager()
        except Exception as e:
            self.context_manager = None
            logger.warning(f"ContextManager not available: {e}")

        # Model selector
        self.model_selector = model_selector or (
            create_model_selector(config) if create_model_selector else None
        )

        # Initialize MCP client and verify connection
        self.mcp_client = create_mcp_client()
        self.mcp_connected = False
        # Check MCP server connection
        logger.info("Checking MCP server connection...")
        try:
            is_connected, mcp_message = check_mcp_connection_sync()
            self.mcp_connected = is_connected
            if is_connected:
                logger.info(mcp_message)
            else:
                logger.warning(mcp_message)
                logger.warning("⚠️  Bond predictions will not work without MCP server!")
                logger.warning(
                    "   Start the MCP server with: cd pathway_producer_consumer && python bond_server.py"
                )
        except Exception as e:
            logger.warning(f"Could not verify MCP connection: {e}")
            logger.warning(
                "   Bond predictions may not work. Ensure bond_server.py is running."
            )

        # Initialize bond data cache (24h TTL - data changes once per day)
        self.bond_cache = get_bond_cache()
        logger.info("Success:  Bond data cache initialized (24h TTL)")

        # Initialize guardrails checker
        self.guardrails = create_guardrails_checker(
            api_key=config.groq_api_key, enabled=config.enable_guardrails
        )
        if config.enable_guardrails:
            logger.info("Success:  Guardrails enabled")
        else:
            logger.info("Info:  Guardrails disabled")

        # Success:  Initialize agents WITH mcp_client (after MCP is ready)
        logger.info("Initializing agents...")
        base_model = config.llm_model

        self.planner = create_planner_agent(config.openai_api_key, base_model)
        self.query_classifier = create_query_classifier(
            config.openai_api_key, base_model
        )

        # Success:  KEY FIX: Pass self.mcp_client (not None)
        logger.debug(
            f"Creating ML agent with MCP client: {self.mcp_client is not None}"
        )
        self.ml_agent = create_ml_agent(config, mcp_client=self.mcp_client)

        self.analyst = AnalystAgent()
        self.scoring = ScoringAgent(
            valuation_weight=config.valuation_weight,
            return_weight=config.return_weight,
            quality_weight=config.quality_weight,
            liquidity_weight=config.liquidity_weight,
        )
        # Create web search tool once to share
        web_search_tool = create_web_search(config.serpapi_key)

        self.advisory = create_advisory_agent(
            config.openai_api_key,
            base_model,
            web_search_tool=web_search_tool,  # Pass web search tool
        )
        self.explainability = create_explainability_agent(
            config.openai_api_key, base_model
        )
        self.response_agent = create_response_agent(
            config.openai_api_key,
            base_model,
            advisory_agent=self.advisory,
            web_search_tool=web_search_tool,  # Pass in case response agent needs to create advisory
        )

        # Initialize real-time info agent
        self.realtime_info_agent = create_realtime_info_agent(
            api_key=config.openai_api_key, model=base_model
        )

        # General LLM for non-bond queries
        self.general_llm = ChatOpenAI(
            model=base_model, temperature=0.7, api_key=config.openai_api_key
        )

        # Initialize non-bond tools
        try:
            self.web_search = (
                create_web_search(config.serpapi_key)
                if hasattr(config, "serpapi_key") and config.serpapi_key
                else None
            )
            self.news_scraper = create_news_scraper()
            self.crisil_scraper = create_crisil_scraper()
            self.portfolio_manager = create_portfolio_manager()
            logger.debug(f"  Web search available: {self.web_search is not None}")
            logger.debug(f"  News scraper available: {self.news_scraper is not None}")
            logger.debug(
                f"  CRISIL scraper available: {self.crisil_scraper is not None}"
            )
            logger.debug(
                f"  Portfolio manager available: {self.portfolio_manager is not None}"
            )
        except Exception as e:
            logger.warning(f"  Warning:  Non-bond tools initialization error: {e}")
            self.web_search = None
            self.news_scraper = None
            self.crisil_scraper = None
            self.portfolio_manager = None
        # Create tools dictionary for easy access by ToolType
        self.tools = {
            ToolType.WEB_SEARCH: self.web_search,
            ToolType.NEWS_SCRAPER: self.news_scraper,
            ToolType.CRISIL_SCRAPER: self.crisil_scraper,
            ToolType.PORTFOLIO_MANAGER: self.portfolio_manager,
        }

        # Initialize portfolio update parser
        self.portfolio_update_parser = create_portfolio_update_parser(
            llm=ChatOpenAI(
                model=base_model, temperature=0.0, api_key=config.openai_api_key
            )
        )

        # Store agent LLM instances for dynamic model switching
        self._agent_llms = {}
        self.general_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a helpful AI assistant. Answer the user's question in a clear, concise, and helpful manner.
    If you don't know something, say so. Be friendly and professional.""",
                ),
                ("user", "{query}"),
            ]
        )

        # Build LangGraph
        self.graph = self._build_graph()

        logger.info("Success:  Orchestrator V3 ready")

    def _normalize_tool_name(self, tool_call: Any) -> str:
        """
        Normalize tool name from various formats (enum, string, etc.)

        Args:
            tool_call: ToolCall object with tool_type attribute

        Returns:
            Normalized tool name string
        """
        if hasattr(tool_call, "tool_type"):
            tool_type = tool_call.tool_type
        else:
            tool_type = tool_call

        # Handle enum with .value
        if hasattr(tool_type, "value"):
            tool_name = tool_type.value
        elif isinstance(tool_type, str):
            tool_name = tool_type
        else:
            # If it's an enum without .value, try to get the name
            tool_name = str(tool_type)
            # If it looks like "ToolType.BOND_PRICER", extract just "BOND_PRICER" and convert to lowercase
            if "." in tool_name:
                tool_name = tool_name.split(".")[-1].lower()

        # Normalize: strip whitespace, lowercase for comparison
        return (
            tool_name.strip().lower()
            if isinstance(tool_name, str)
            else str(tool_name).lower()
        )

    def _get_state_value(
        self, state: GraphState, key: str, default: Any = None, required: bool = False
    ) -> Any:
        """
        Safely get a value from state with optional validation

        Args:
            state: GraphState dictionary
            key: Key to retrieve
            default: Default value if key not found
            required: If True, log warning if key is missing
        Returns:
            Value from state or default
        """
        return StateHelper.get(state, key, default, required)

    def _clean_bond_name(self, name: str, symbol: str = "", isin: str = "") -> str:
        """Clean up redundant bond names - removes duplicate symbols/ISINs"""
        import re

        if not name:
            return symbol or isin or "Unknown Bond"

        cleaned = name

        # Remove duplicate symbols
        if symbol and symbol in cleaned:
            cleaned = re.sub(rf"\b{re.escape(symbol)}\b", "", cleaned)

        # Remove duplicate ISINs
        if isin and isin in cleaned:
            cleaned = re.sub(rf"\b{re.escape(isin)}\b", "", cleaned)

        # Remove redundant numbers at the beginning (like "31280 GOVERNMENT OF INDIA")
        cleaned = re.sub(r"^\d+\s+", "", cleaned)

        # Clean up multiple spaces
        cleaned = " ".join(cleaned.split())

        # If we removed everything, use the original
        if not cleaned.strip():
            return name

        return cleaned.strip()

    def _transform_bond_price_forecast(
        self, raw_data: Any, bond_id: str
    ) -> Dict[str, Any]:
        """
        Transform MCP bond price data to match BondPriceForecast schema

        Args:
            raw_data: Raw data from MCP server (dict, list, or other)
            bond_id: Bond identifier (ISIN)

        Returns:
            Dict matching BondPriceForecast schema
        """
        from datetime import datetime
        # DEBUG: Print what we receive
        print(f"\nDEBUG  DEBUG _transform_bond_price_forecast:")
        print(f"   bond_id: {bond_id}")
        print(f"   raw_data type: {type(raw_data)}")
        if isinstance(raw_data, dict):
            print(f"   raw_data keys: {list(raw_data.keys())}")
            print(f"   raw_data values: {raw_data}")

        # Handle different data types
        if isinstance(raw_data, dict):
            # Check if it already matches schema
            if all(k in raw_data for k in ["isin", "forecast_date", "predicted_price"]):
                return raw_data  # Already in correct format

            # Get raw bond name and clean it
            raw_bond_name = (
                raw_data.get("bond_name") or raw_data.get("name") or f"Bond {bond_id}"
            )
            symbol = raw_data.get("symbol") or raw_data.get("bond_symbol") or bond_id
            cleaned_name = self._clean_bond_name(raw_bond_name, symbol, bond_id)

            # CRITICAL: Handle ACTUAL MCP response format
            # When days_ahead=0, MCP returns: {starting_price, ending_price, forecasts: [...]}
            # When days_ahead>0, MCP returns: {day, date, estimated_price, ytm_percent, ...}

            # Extract prices based on actual keys
            if "starting_price" in raw_data:
                # days_ahead=0 format - has trajectory
                current_price = raw_data.get("starting_price")
                predicted_price = raw_data.get("ending_price")

                # Success:  CRITICAL FIX: Get LTP from top-level field (NOT from forecasts!)
                # forecasts[0]['price'] is a PREDICTED price, not the actual LTP from CSV
                ltp = raw_data.get("last_traded_price")

                # Get YTM from first forecast if available
                forecasts = raw_data.get("forecasts", [])
                if forecasts and len(forecasts) > 0:
                    first_forecast = forecasts[0]
                    ytm = first_forecast.get("ytm_percent")
                else:
                    ytm = None

                # Fallback if no LTP provided
                if not ltp:
                    ltp = current_price

                # Calculate expected return
                if current_price and predicted_price and current_price > 0:
                    expected_return = (predicted_price - current_price) / current_price
                else:
                    expected_return = 0.0

            elif "estimated_price" in raw_data:
                # days_ahead>0 format - single day estimate
                predicted_price = raw_data.get("estimated_price")
                current_price = raw_data.get("current_price")
                ltp = raw_data.get("last_traded_price", current_price)
                ytm = raw_data.get("ytm_percent")
                expected_return = 0.0

            else:
                # Fallback to old keys (just in case)
                current_price = raw_data.get("current_price")
                ltp = raw_data.get("last_traded_price")
                predicted_price = raw_data.get("price") or raw_data.get(
                    "predicted_price"
                )
                ytm = raw_data.get("ytm") or raw_data.get("ytm_percent")
                expected_return = raw_data.get("expected_return", 0.0)

            # DEBUG
            print(f"   Success:  EXTRACTED:")
            print(f"      ltp: {ltp}")
            print(f"      current_price: {current_price}")
            print(f"      predicted_price: {predicted_price}")
            print(f"      ytm: {ytm}")
            print(f"      expected_return: {expected_return}")

            # Transform with CLEANED name and CORRECT values
            transformed = {
                "isin": raw_data.get("bond_symbol") or raw_data.get("isin") or bond_id,
                "symbol": symbol,
                "bond_name": cleaned_name,
                "predicted_price": float(predicted_price) if predicted_price else 0.0,
                "current_price": float(current_price) if current_price else None,
                "last_traded_price": float(ltp) if ltp else None,
                "ytm": float(ytm) if ytm else None,
                "expected_return": float(expected_return) if expected_return else 0.0,
                "yield_component": float(raw_data.get("yield_component", 0.0)),
            }

            # Handle date field (multiple possible keys)
            date_field = (
                raw_data.get("date")
                or raw_data.get("forecast_date")
                or raw_data.get("valuation_date")
            )

            if date_field:
                if isinstance(date_field, str):
                    try:
                        transformed["forecast_date"] = datetime.fromisoformat(
                            date_field
                        )
                    except:
                        transformed["forecast_date"] = datetime.now()
                elif isinstance(date_field, datetime):
                    transformed["forecast_date"] = date_field
                else:
                    transformed["forecast_date"] = datetime.now()
            else:
                transformed["forecast_date"] = datetime.now()

            return transformed

        elif isinstance(raw_data, list) and len(raw_data) > 0:
            return self._transform_bond_price_forecast(raw_data[0], bond_id)

        # Default fallback
        return {
            "isin": bond_id,
            "bond_name": f"Bond {bond_id}",
            "forecast_date": datetime.now(),
            "predicted_price": 0.0,
            "current_price": None,
            "expected_return": 0.0,
            "yield_component": 0.0,
        }

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph"""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("validate_query", self._validate_query)
        workflow.add_node("classify_query", self._classify_query)
        # Note: gather_realtime_info and plan_execution are only used internally by plan_and_realtime_parallel
        # They are not standalone nodes in the graph to avoid duplication
        workflow.add_node(
            "plan_and_realtime_parallel", self._plan_and_realtime_parallel
        )
        workflow.add_node("handle_news_only", self._handle_news_only)
        workflow.add_node("handle_non_bond_query", self._handle_non_bond_query)
        workflow.add_node("handle_portfolio_update", self._handle_portfolio_update)
        workflow.add_node("execute_tools", self._execute_tools)
        workflow.add_node("run_ml_model", self._run_ml_model)
        workflow.add_node("run_analyst", self._run_analyst)
        workflow.add_node("run_scoring", self._run_scoring)
        workflow.add_node("run_response", self._run_response)
        workflow.add_node("run_explainability", self._run_explainability)
        workflow.add_node("finalize", self._finalize)

        # Define edges
        workflow.set_entry_point("validate_query")

        # Validation -> Classification (conditional)
        workflow.add_conditional_edges(
            "validate_query",
            self._should_continue_after_validation,
            {"continue": "classify_query", "skip": "finalize"},
        )

        # Classification -> Route based on query type
        workflow.add_conditional_edges(
            "classify_query",
            self._route_after_classification,
            {
                "bond_query": "plan_and_realtime_parallel",
                "news_only": "handle_news_only",
                "non_bond_query": "handle_non_bond_query",
                "portfolio_update": "handle_portfolio_update",
            },
        )

        # Parallel planning and real-time info -> Tool execution
        workflow.add_edge("plan_and_realtime_parallel", "execute_tools")

        # News-only handler -> Finalize (bypasses full pipeline)
        workflow.add_edge("handle_news_only", "finalize")

        # Non-bond query handler -> Finalize
        workflow.add_edge("handle_non_bond_query", "finalize")

        # Portfolio update handler -> Finalize
        workflow.add_edge("handle_portfolio_update", "finalize")

        # Tools -> ML Model (conditional)
        workflow.add_conditional_edges(
            "execute_tools",
            self._should_run_ml,
            {
                "yes": "run_ml_model",
                "no": "run_response",  # Success:  Skip directly to response
            },
        )

        # ML -> Analyst (conditional)
        workflow.add_conditional_edges(
            "run_ml_model",
            self._should_run_analyst,  # Success:  New conditional
            {"yes": "run_analyst", "no": "run_response"},
        )

        # Analyst -> Scoring (conditional)
        workflow.add_conditional_edges(
            "run_analyst",
            self._should_run_scoring,  # Success:  New conditional
            {"yes": "run_scoring", "no": "run_response"},
        )

        # Scoring -> Response
        workflow.add_edge("run_scoring", "run_response")

        # Response -> Explainability (conditional)
        workflow.add_conditional_edges(
            "run_response",
            self._should_explain,
            {"yes": "run_explainability", "no": "finalize"},
        )

        # Explainability -> Finalize
        workflow.add_edge("run_explainability", "finalize")

        # Finalize -> END
        workflow.add_edge("finalize", END)

        # Compile without checkpointing (we'll manage messages manually)
        # This avoids serialization issues with Pydantic models
        return workflow.compile()

    def _should_continue_after_validation(self, state: GraphState) -> str:
        """Conditional: Should we continue after validation?"""
        if state.get("current_step") == "validation_failed":
            return "skip"
        return "continue"
    def _validate_query(self, state: GraphState) -> GraphState:
        """Validate query and check guardrails"""
        logger.info("DEBUG  VALIDATING QUERY...")
        state["current_step"] = "validated"

        # Check guardrails if enabled (check config dynamically at runtime)
        if (
            self.config.enable_guardrails
            and self.config.guardrails_check_input
            and self.guardrails
        ):
            query = self._get_state_value(state, "user_query", "")
            # Guardrails checker respects its enabled flag, which we set based on config
            if self.guardrails.enabled != self.config.enable_guardrails:
                self.guardrails.enabled = self.config.enable_guardrails
            guard_result = self.guardrails.check_input(query)
            if not guard_result.is_safe:
                logger.warning(f"Warning:   Guardrails: Input flagged as unsafe")
                logger.warning(f"   Reason: {guard_result.reason}")
                logger.warning(f"   Categories: {guard_result.categories}")
                state["current_step"] = "validation_failed"
                StateHelper.ensure_list(state, "errors").append(
                    f"Input safety check failed: {guard_result.reason}"
                )
                # Create safe response
                from schemas_v2 import AdvisoryOutput

                state["advisory"] = AdvisoryOutput(
                    query=query,
                    recommendations=[],
                    summary="I cannot process this request as it may violate safety guidelines. Please rephrase your query to be about bonds, trading, or financial analysis.",
                    timestamp=datetime.now(),
                )
                return state

        logger.info(" Query validated (routing will be determined by classifier)")
        return state

    async def _classify_query(self, state: GraphState) -> GraphState:
        """Classify user query"""
        AgentLogger.print_agent_header("Query Classifier", "CLASSIFYING")
        state["current_step"] = "classify_query"
        try:
            # Get conversation history from LangGraph messages
            messages = state.get("messages", [])
            conversation_history = self._messages_to_dict(messages)

            # Use context manager to extract relevant context if available
            if self.context_manager:
                context = self.context_manager.extract_relevant_context(
                    conversation_history, state["user_query"], agent_type="classifier"
                )

            classified_query = self.query_classifier.classify(
                state["user_query"],
                state.get("user_profile"),
                conversation_history=conversation_history
                if conversation_history
                else None,
            )

            # Success:  FIX: Convert Pydantic model to dict
            if hasattr(classified_query, "model_dump"):
                state["classified_query"] = classified_query.model_dump()
            elif hasattr(classified_query, "dict"):
                state["classified_query"] = classified_query.dict()
            else:
                state["classified_query"] = classified_query

            # Extract values for flags
            if isinstance(state["classified_query"], dict):
                state["needs_portfolio"] = state["classified_query"].get(
                    "needs_portfolio", False
                )
                state["needs_rag"] = state["classified_query"].get("needs_rag", False)
                state["needs_explainability"] = state["classified_query"].get(
                    "needs_explainability", False
                )
            else:
                state["needs_portfolio"] = getattr(
                    classified_query, "needs_portfolio", False
                )
                state["needs_rag"] = getattr(classified_query, "needs_rag", False)
                state["needs_explainability"] = getattr(
                    classified_query, "needs_explainability", False
                )

            # Get classification details for logging
            query_type = getattr(classified_query, "query_type", None)
            if query_type and hasattr(query_type, "value"):
                query_type = query_type.value
            intent = getattr(classified_query, "intent", None)
            if intent and hasattr(intent, "value"):
                intent = intent.value

            # Log classification results using AgentLogger
            AgentLogger.print_agent_output(
                "Query Classifier",
                {
                    "Intent": intent,
                    "Query Type": query_type,
                    "Needs Portfolio": state["needs_portfolio"],
                    "Needs Explainability": state["needs_explainability"],
                    "Needs RAG": state["needs_rag"],
                    "Confidence": getattr(classified_query, "confidence", 0.8),
                },
                "Classification Result",
            )
            AgentLogger.print_success(
                f"Query classified as: {intent}", "Query Classifier"
            )

        except Exception as e:
            AgentLogger.print_error(f"Classification error: {e}", "Query Classifier")
            state["errors"].append(f"Classification failed: {str(e)}")
            state["classified_query"] = {
                "query": state["user_query"],
                "query_type": "CUSTOM",
                "intent": "CUSTOM",
            }

        state["execution_path"].append("classify_query")
        return state

    def _is_news_only_query(self, state: GraphState) -> bool:
        """
        Check if query is a pure news query that can bypass the full pipeline.
        ONLY returns True if "news" is explicitly mentioned in the user query.
        """
        query = state.get("user_query", "").lower()
        # CRITICAL: Only treat as news-only if "news" is explicitly mentioned
        # This prevents data queries (yields, bond info, etc.) from being misrouted
        if "news" not in query:
            return False

        # If "news" is mentioned, check if it's asking for news specifically
        # (not asking for data with news as context)
        news_keywords = [
            "news about",
            "news on",
            "news regarding",
            "news update",
            "latest news",
            "recent news",
            "current news",
            "today's news",
            "breaking news",
            "what news",
            "tell me news",
            "show me news",
            "give me news",
            "any news",
            "news regarding",
        ]

        # Check if query explicitly asks for news
        is_news_query = any(keyword in query for keyword in news_keywords)

        # If "news" is mentioned but it's a data query asking for data (not news about data)
        # Route through pipeline to use MCP tools
        data_query_patterns = [
            "yield",
            "yields",
            "g-sec",
            "gsec",
            "government bond",
            "bond price",
            "bond info",
            "bond details",
            "ytm",
            "coupon",
            "maturity",
            "duration",
            "isin",
            "bond symbol",
            "government securities",
            "show me",
            "what are",
            "current",
            "latest",
            "real-time",
        ]

        has_data_keyword = any(kw in query for kw in data_query_patterns)

        # If it has data keywords AND doesn't explicitly say "news about [data]"
        # Then it's asking for data, not news - route through pipeline
        if has_data_keyword:
            # Check if it explicitly says "news about [data]" or similar
            news_about_data = any(
                phrase in query
                for phrase in ["news about", "news on", "news regarding"]
            )
            if not news_about_data:
                # It mentions "news" but is asking for data itself - route through pipeline
                return False

        # Only return True if "news" is explicitly mentioned AND it's asking for news
        return is_news_query

    def _route_after_classification(self, state: GraphState) -> str:
        """Conditional: Route based on query type"""
        query = state.get("user_query", "").lower()

        # Check if it's a portfolio update query (command, not question)
        # Portfolio update queries are ACTION commands, not questions about recommendations
        portfolio_update_action_keywords = [
            "add",
            "update",
            "change",
            "modify",
            "remove",
            "delete",
            "set quantity",
            "set price",
            "buy",
            "purchase",
            "sell all",
            "adjust",
            "edit portfolio",
            "update portfolio",
            "change bond",
        ]

        # Question words that indicate it's NOT a portfolio update command
        question_keywords = [
            "what",
            "which",
            "how",
            "when",
            "where",
            "why",
            "can i",
            "should i",
            "recommend",
            "suggest",
            "best",
            "good",
            "better",
            "top",
            "worst",
        ]

        # Check if it's a question (not a command)
        is_question = any(qw in query for qw in question_keywords)

        # Check if it's a portfolio update command (action keyword + portfolio context)
        has_action_keyword = any(kw in query for kw in portfolio_update_action_keywords)
        has_portfolio_context = any(
            ctx in query
            for ctx in [
                "bond",
                "position",
                "holding",
                "isin",
                "portfolio",
                "my portfolio",
            ]
        )

        # Only route to portfolio_update if:
        # 1. It has an action keyword (add, update, remove, etc.)
        # 2. It has portfolio context
        # 3. It's NOT a question (questions should go to advisory/recommendations)
        is_portfolio_update = (
            has_action_keyword and has_portfolio_context and not is_question
        )

        if is_portfolio_update:
            return "portfolio_update"

        classified = state.get("classified_query")
        if classified:
            # Check if it's bond-related
            is_bond_related = getattr(classified, "is_bond_related", True)
            if not is_bond_related:
                return "non_bond_query"

            # Check if it's a news-only query (bypass full pipeline)
            if self._is_news_only_query(state):
                return "news_only"

        return "bond_query"

    async def _plan_and_realtime_parallel(self, state: GraphState) -> GraphState:
        """
        Run planning and real-time info gathering in parallel
        Both operations are independent and can run simultaneously
        Real-time info output goes directly to advisory/response agent via state["web_search_results"]
        """
        state["current_step"] = "planning_and_realtime_parallel"
        state["execution_path"].append("plan_and_realtime_parallel")

        AgentLogger.print_agent_header(
            "Parallel Execution", "PLANNING + REAL-TIME INFO"
        )

        # Run planning and real-time info gathering in parallel
        # _plan_execution is synchronous, _gather_realtime_info is async
        # Run planning in executor thread and real-time info as async task
        try:
            import concurrent.futures

            # Create a flag to prevent execution_path duplication
            # When called from parallel, don't append to execution_path in sub-functions
            state["_internal_call"] = True

            # Run planning in thread pool (since it's synchronous)
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                planning_future = executor.submit(self._plan_execution, state)
                realtime_task = asyncio.create_task(self._gather_realtime_info(state))

                # Wait for both to complete
                planning_result = await loop.run_in_executor(
                    None, planning_future.result
                )
                await realtime_task

                # Update state with planning results
                if "execution_plan" in planning_result:
                    state["execution_plan"] = planning_result["execution_plan"]
                if "errors" in planning_result:
                    state["errors"].extend(planning_result.get("errors", []))

            # Check for exceptions in realtime task
            if realtime_task.exception():
                state["errors"].append(
                    f"Real-time info error: {str(realtime_task.exception())}"
                )
                if "web_search_results" not in state:
                    state["web_search_results"] = None

            # Remove internal call flag
            state.pop("_internal_call", None)

            AgentLogger.print_success(
                f"Planning completed: {state.get('execution_plan') is not None}, "
                f"Real-time info: {state.get('web_search_results') is not None}",
                "Parallel Execution",
            )

        except Exception as e:
            logger.error(f"Warning:   Parallel execution error: {e}", exc_info=True)
            state["errors"].append(f"Parallel execution error: {str(e)}")
            state.pop("_internal_call", None)

        return state

    async def _gather_realtime_info(self, state: GraphState) -> GraphState:
        """
        Intelligently gather real-time information:
        1. Decide if needed (LLM-based, async)
        2. Generate queries (async, parallel with decision)
        3. Run tools in parallel
        4. Process results (async)
        """
        state["current_step"] = "gathering_realtime_info"

        query = state["user_query"]
        classified = state.get("classified_query")

        # Get intent
        intent_str = ""
        if classified:
            intent = getattr(classified, "intent", None)
            if hasattr(intent, "value"):
                intent_str = intent.value
            else:
                intent_str = str(intent) if intent else ""

        # Get entities from classifier to enhance query generation
        entities = []
        if classified:
            entities = getattr(classified, "entities", [])

        # Enhance query with entities for better context
        enhanced_query = query
        if entities:
            # Add entities to query for better search context
            entity_suffix = " " + " ".join(entities[:3])  # Add top 3 entities
            enhanced_query = query + entity_suffix
        try:
            # Check if query needs news (from classifier or keywords)
            # Skip real-time info for data queries (yields, bond info) that should use MCP tools
            query_lower = query.lower()
            is_data_query = any(
                kw in query_lower
                for kw in [
                    "yield",
                    "yields",
                    "g-sec",
                    "gsec",
                    "bond price",
                    "bond info",
                    "bond details",
                    "ytm",
                    "coupon",
                    "maturity",
                    "duration",
                    "isin",
                    "bond symbol",
                    "government securities",
                ]
            )

            needs_news = (
                not is_data_query  # Don't use news for data queries - use MCP tools instead
                and (getattr(classified, "needs_news", False) if classified else False)
                or any(
                    kw in query_lower
                    for kw in [
                        "news",
                        "latest",
                        "recent",
                        "update",
                        "current",
                        "today",
                        "market sentiment",
                        "rate cut",
                        "rate hike",
                        "rbi policy",
                    ]
                )
            )

            # Step 1: Intelligent decision (async, fast)
            # If news is needed, we'll force it, but still run decision for consistency
            decision_task = self.realtime_info_agent.should_gather_realtime_info(
                query=enhanced_query, intent=intent_str
            )

            # Step 2: Generate queries in parallel with decision (optimization)
            # Use enhanced query with entities for better keyword extraction
            query_gen_task = self.realtime_info_agent.generate_search_queries(
                query=enhanced_query, intent=intent_str
            )

            # Wait for both decisions and query generation
            decision, search_queries = await asyncio.gather(
                decision_task, query_gen_task, return_exceptions=True
            )

            # Handle decision result
            if isinstance(decision, Exception):
                logger.warning(
                    f"Warning:   Decision error: {decision}, defaulting to skip"
                )
                state["web_search_results"] = None
                # Only append to execution_path if not called internally from parallel execution
                if not state.get("_internal_call", False):
                    state["execution_path"].append("gather_realtime_info")
                return state
            # Override decision if news is explicitly needed
            if needs_news:
                decision["needs_realtime_info"] = True
                decision["priority"] = "high"
                decision["reasoning"] = "Query requires news/latest information"

            needs_realtime = decision.get("needs_realtime_info", False)
            reasoning = decision.get("reasoning", "")
            priority = decision.get("priority", "medium")

            if not needs_realtime:
                AgentLogger.print_info(
                    f"Skipping real-time info: {reasoning}", "Real-Time Info Agent"
                )
                state["web_search_results"] = None
                # Only append to execution_path if not called internally from parallel execution
                if not state.get("_internal_call", False):
                    state["execution_path"].append("gather_realtime_info")
                return state

            AgentLogger.print_success(
                f"Real-time info needed ({priority} priority): {reasoning}",
                "Real-Time Info Agent",
            )

            # Handle query generation result
            if isinstance(search_queries, Exception):
                print(f"Warning:   Query generation error: {search_queries}")
                web_search_query = query
                news_keywords = [query]
            else:
                web_search_query = search_queries.get("web_search_query", query)
                news_keywords = search_queries.get("news_keywords", [query])

            AgentLogger.print_agent_output(
                "Real-Time Info Agent",
                {"Web Search Query": web_search_query, "News Keywords": news_keywords},
                "Search Queries",
            )

            # Step 3: Run web search and news scraping in parallel
            AgentLogger.print_step(
                "Running web search and news scraping in parallel", "running"
            )

            # Check if tools are available
            web_search_tool = self.tools.get(ToolType.WEB_SEARCH)
            news_scraper_tool = self.tools.get(ToolType.NEWS_SCRAPER)

            if not web_search_tool:
                AgentLogger.print_warning(
                    "Web search tool not available", "Real-Time Info Agent"
                )
                web_search_result = None
            else:
                web_search_task = web_search_tool.search(
                    query=web_search_query, num_results=5
                )

            if not news_scraper_tool:
                AgentLogger.print_warning(
                    "News scraper tool not available", "Real-Time Info Agent"
                )
                news_result = None
            else:
                news_task = news_scraper_tool.scrape_news(
                    keywords=news_keywords, max_articles=5, hours_back=24
                )

            # Execute tools in parallel (only if both are available)
            if web_search_tool and news_scraper_tool:
                web_search_result, news_result = await asyncio.gather(
                    web_search_task, news_task, return_exceptions=True
                )
            elif web_search_tool:
                try:
                    web_search_result = await web_search_task
                except Exception as e:
                    web_search_result = e
                news_result = None
            elif news_scraper_tool:
                try:
                    news_result = await news_task
                except Exception as e:
                    news_result = e
                web_search_result = None
            else:
                # Both tools unavailable
                web_search_result = None
                news_result = None

            # Handle exceptions
            if isinstance(web_search_result, Exception):
                AgentLogger.print_error(
                    f"Web search error: {web_search_result}", "Real-Time Info Agent"
                )
                web_search_result = None
            else:
                if web_search_result and web_search_result.success:
                    AgentLogger.print_success(
                        f"Web search: {len(web_search_result.data) if web_search_result.data else 0} results",
                        "Real-Time Info Agent",
                    )
                else:
                    AgentLogger.print_info(
                        f"Web search: {web_search_result.error if web_search_result else 'No results'}",
                        "Real-Time Info Agent",
                    )

            if isinstance(news_result, Exception):
                AgentLogger.print_error(
                    f"News scraping error: {news_result}", "Real-Time Info Agent"
                )
                news_result = None
            else:
                if news_result and news_result.success:
                    AgentLogger.print_success(
                        f"News scraping: {len(news_result.data) if news_result.data else 0} articles",
                        "Real-Time Info Agent",
                    )
                else:
                    AgentLogger.print_info(
                        f"News scraping: {news_result.error if news_result else 'No results'}",
                        "Real-Time Info Agent",
                    )

            # Step 4: Process results asynchronously
            formatted_context = await self.realtime_info_agent.process_realtime_info(
                query=query,
                intent=intent_str,
                web_search_result=web_search_result
                if not isinstance(web_search_result, Exception)
                else None,
                news_result=news_result
                if not isinstance(news_result, Exception)
                else None,
            )

            if formatted_context:
                state["web_search_results"] = formatted_context
                AgentLogger.print_success(
                    "Real-time info processed and formatted", "Real-Time Info Agent"
                )
                # Show preview of formatted context
                preview = (
                    formatted_context[:200] + "..."
                    if len(formatted_context) > 200
                    else formatted_context
                )
                AgentLogger.print_agent_output(
                    "Real-Time Info Agent", preview, "Formatted Context Preview"
                )
            else:
                state["web_search_results"] = None
                AgentLogger.print_info(
                    "No relevant real-time information to process",
                    "Real-Time Info Agent",
                )

            # Store raw results for ML model and other agents if needed
            if web_search_result and not isinstance(web_search_result, Exception):
                state["tool_results"][ToolType.WEB_SEARCH] = web_search_result
            if news_result and not isinstance(news_result, Exception):
                state["tool_results"][ToolType.NEWS_SCRAPER] = news_result
                if news_result.success and news_result.data:
                    state["news_articles"] = news_result.data

        except Exception as e:
            logger.error(
                f"Warning:   Real-time info gathering error: {e}", exc_info=True
            )
            state["web_search_results"] = None
            state["errors"].append(f"Real-time info gathering error: {str(e)}")

        # Only append to execution_path if not called internally from parallel execution
        if not state.get("_internal_call", False):
            state["execution_path"].append("gather_realtime_info")
        return state
    async def _handle_news_only(self, state: GraphState) -> GraphState:
        """
        Handle news-only queries: Gather news and return direct response without full pipeline
        This bypasses ML, analyst, scoring, and advisory agents for pure news queries
        """
        AgentLogger.print_agent_header("News-Only Handler", "DIRECT NEWS RESPONSE")
        state["current_step"] = "handling_news_only"
        state["execution_path"].append("handle_news_only")

        query = state["user_query"]
        classified = state.get("classified_query")

        # Get intent
        intent_str = ""
        if classified:
            intent = getattr(classified, "intent", None)
            if hasattr(intent, "value"):
                intent_str = intent.value
            else:
                intent_str = str(intent) if intent else ""

        try:
            # Generate search queries for news
            search_queries = await self.realtime_info_agent.generate_search_queries(
                query=query, intent=intent_str
            )

            web_search_query = search_queries.get("web_search_query", query)
            news_keywords = search_queries.get("news_keywords", [query])

            # Run web search and news scraping in parallel
            # Check if tools are available
            web_search_tool = self.tools.get(ToolType.WEB_SEARCH)
            news_scraper_tool = self.tools.get(ToolType.NEWS_SCRAPER)

            if not web_search_tool:
                AgentLogger.print_warning(
                    "Web search tool not available", "News-Only Handler"
                )
                web_search_result = None
            else:
                web_search_task = web_search_tool.search(
                    query=web_search_query, num_results=5
                )

            if not news_scraper_tool:
                AgentLogger.print_warning(
                    "News scraper tool not available", "News-Only Handler"
                )
                news_result = None
            else:
                news_task = news_scraper_tool.scrape_news(
                    keywords=news_keywords, max_articles=10, hours_back=24
                )

            # Execute tools in parallel (only if both are available)
            if web_search_tool and news_scraper_tool:
                web_search_result, news_result = await asyncio.gather(
                    web_search_task, news_task, return_exceptions=True
                )
            elif web_search_tool:
                try:
                    web_search_result = await web_search_task
                except Exception as e:
                    web_search_result = e
                news_result = None
            elif news_scraper_tool:
                try:
                    news_result = await news_task
                except Exception as e:
                    news_result = e
                web_search_result = None
            else:
                # Both tools unavailable
                web_search_result = None
                news_result = None

            # Handle exceptions
            if isinstance(web_search_result, Exception):
                AgentLogger.print_error(
                    f"Web search error: {web_search_result}", "News-Only Handler"
                )
                web_search_result = None

            if isinstance(news_result, Exception):
                AgentLogger.print_error(
                    f"News scraping error: {news_result}", "News-Only Handler"
                )
                news_result = None

            # Process results
            formatted_context = await self.realtime_info_agent.process_realtime_info(
                query=query,
                intent=intent_str,
                web_search_result=web_search_result
                if not isinstance(web_search_result, Exception)
                else None,
                news_result=news_result
                if not isinstance(news_result, Exception)
                else None,
            )

            # Create response with news information
            from schemas_v2 import AdvisoryOutput
            from datetime import datetime

            if formatted_context:
                summary = (
                    f"📰 **Latest News and Market Updates:**\n\n{formatted_context}"
                )
            elif (
                news_result
                and not isinstance(news_result, Exception)
                and news_result.success
                and news_result.data
            ):
                # Format news articles directly
                articles = news_result.data[:5]  # Top 5 articles
                summary_parts = [f"📰 **Latest News ({len(articles)} articles):**\n"]
                for i, article in enumerate(articles, 1):
                    if hasattr(article, "title"):
                        summary_parts.append(f"{i}. **{article.title}**")
                        if hasattr(article, "source"):
                            summary_parts.append(f"   Source: {article.source}")
                        if hasattr(article, "summary") and article.summary:
                            summary_parts.append(f"   {article.summary[:200]}...")
                        summary_parts.append("")
                summary = "\n".join(summary_parts)
            else:
                summary = f"I searched for news related to '{query}', but couldn't find recent articles. Please try asking about bond analytics, recommendations, or portfolio analysis instead."
            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=summary,
                portfolio_changes={},
                timestamp=datetime.now(),
            )

            state["web_search_results"] = formatted_context

            AgentLogger.print_success(
                "News-only response generated", "News-Only Handler"
            )

        except Exception as e:
            print(f"Warning:   News-only handler error: {e}")
            import traceback

            traceback.print_exc()
            from schemas_v2 import AdvisoryOutput
            from datetime import datetime

            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=f"I encountered an error while gathering news. Please try again or ask about bond analytics, recommendations, or portfolio analysis.",
                portfolio_changes={},
                timestamp=datetime.now(),
            )
            state["errors"].append(f"News-only handler error: {str(e)}")

        return state

    async def _handle_portfolio_update(self, state: GraphState) -> GraphState:
        """Handle portfolio update queries - parse and execute updates"""
        print(f"\n{'=' * 80}")
        print(f"INFO:  HANDLING PORTFOLIO UPDATE...")
        state["current_step"] = "handling_portfolio_update"
        state["execution_path"].append("handle_portfolio_update")

        query = state["user_query"]
        user_id = state["user_id"]

        try:
            # Get portfolio tool
            portfolio_tool = self.tools[ToolType.PORTFOLIO_MANAGER]

            # Get current portfolio info for context
            portfolio_result = await portfolio_tool.get_portfolio(user_id)
            portfolio_info = ""
            if portfolio_result.success and portfolio_result.data:
                holdings = portfolio_result.data.holdings
                portfolio_info = f"Current holdings: {len(holdings)} positions\n"
                for holding in holdings[:5]:  # Show first 5
                    portfolio_info += f"- {holding.bond_name} ({holding.isin}): {holding.quantity} units at ₹{holding.current_price}\n"

            # Check if query is about adding bonds with market values
            query_lower = query.lower()
            is_add_with_values = any(
                phrase in query_lower for phrase in ["add", "update", "set"]
            ) and any(
                phrase in query_lower
                for phrase in [
                    "with values",
                    "with market",
                    "with prices",
                    "top 5",
                    "first 5",
                    "along with",
                    "with their values",
                    "market data",
                    "current prices",
                ]
            )

            # If query mentions adding bonds with values, use bond analytics
            if (
                is_add_with_values
                and portfolio_result.success
                and portfolio_result.data
            ):
                # Get bond analytics from state or run analyst if needed
                bond_analytics = state.get("bond_analytics", {})
                if not bond_analytics:
                    # Run analyst to get bond analytics
                    print("  Fetching bond analytics for portfolio update...")
                    bonds_universe = (
                        state.get("bonds_universe") or self._get_default_bonds()
                    )
                    analytics_result = await self._run_analyst_for_portfolio_update(
                        state, bonds_universe
                    )
                    bond_analytics = analytics_result.get("bond_analytics", {})

                # Update portfolio with market values
                result = await self._update_portfolio_with_market_values(
                    user_id=user_id,
                    portfolio_tool=portfolio_tool,
                    portfolio_result=portfolio_result,
                    bond_analytics=bond_analytics,
                    query=query,
                )
            else:
                # Parse the update command normally
                update_command = self.portfolio_update_parser.parse(
                    query, portfolio_info
                )

                if not update_command.action:
                    # Not a portfolio update command, return error
                    from schemas_v2 import AdvisoryOutput

                    state["advisory"] = AdvisoryOutput(
                        query=query,
                        recommendations=[],
                        summary="I couldn't parse a portfolio update command from your query. Please use phrases like 'add bond', 'update quantity', 'remove bond', etc.",
                        timestamp=datetime.now(),
                    )
                    return state

                # Execute the update based on action (existing logic)
                portfolio_tool = self.tools[ToolType.PORTFOLIO_MANAGER]
                result = None

                if update_command.action == "add":
                    # Need ISIN or bond name to add
                    if not update_command.isin and not update_command.bond_name:
                        raise ValueError(
                            "Cannot add bond: ISIN or bond name is required"
                        )

                    # For now, if no ISIN, we'll need to search for it or use bond name
                    isin = update_command.isin or "UNKNOWN"
                    result = await portfolio_tool.add_bond(
                        user_id=user_id,
                        isin=isin,
                        bond_name=update_command.bond_name or "Unknown Bond",
                        quantity=update_command.quantity or 0.0,
                        current_price=update_command.current_price or 0.0,
                        avg_cost=update_command.avg_cost,
                    )

                elif update_command.action == "update":
                    if not update_command.isin and not update_command.bond_name:
                        raise ValueError(
                            "Cannot update bond: ISIN or bond name is required"
                        )

                    # Find ISIN from bond name if needed
                    isin = update_command.isin
                    if not isin and update_command.bond_name:
                        # Try to find ISIN from portfolio
                        if portfolio_result.success and portfolio_result.data:
                            for holding in portfolio_result.data.holdings:
                                if (
                                    update_command.bond_name.lower()
                                    in holding.bond_name.lower()
                                ):
                                    isin = holding.isin
                                    break

                    if not isin:
                        raise ValueError(
                            f"Cannot find bond: {update_command.bond_name or 'unknown'}"
                        )

                    result = await portfolio_tool.update_bond(
                        user_id=user_id, isin=isin, updates=update_command.updates
                    )

                elif update_command.action == "remove":
                    if not update_command.isin and not update_command.bond_name:
                        raise ValueError(
                            "Cannot remove bond: ISIN or bond name is required"
                        )

                    # Find ISIN from bond name if needed
                    isin = update_command.isin
                    if not isin and update_command.bond_name:
                        if portfolio_result.success and portfolio_result.data:
                            for holding in portfolio_result.data.holdings:
                                if (
                                    update_command.bond_name.lower()
                                    in holding.bond_name.lower()
                                ):
                                    isin = holding.isin
                                    break

                    if not isin:
                        raise ValueError(
                            f"Cannot find bond: {update_command.bond_name or 'unknown'}"
                        )

                    result = await portfolio_tool.remove_bond(
                        user_id=user_id, isin=isin
                    )

            # Create response based on result
            from schemas_v2 import AdvisoryOutput

            if result and result.success:
                if is_add_with_values:
                    summary = (
                        " Successfully updated your portfolio with market values.\n\n"
                    )
                else:
                    action_desc = {
                        "add": "added to",
                        "update": "updated in",
                        "remove": "removed from",
                    }.get(
                        getattr(update_command, "action", "updated")
                        if "update_command" in locals()
                        else "updated",
                        "modified in",
                    )
                    summary = f" Successfully {action_desc} your portfolio.\n\n"

                if result.data and hasattr(result.data, "holdings"):
                    summary += f"Your portfolio now has {len(result.data.holdings)} positions.\n"
                    summary += (
                        f"Total portfolio value: ₹{result.data.total_value:,.2f}\n"
                    )

                state["advisory"] = AdvisoryOutput(
                    query=query,
                    recommendations=[],
                    summary=summary,
                    timestamp=datetime.now(),
                )

                # Update portfolio in state
                if result.data:
                    state["portfolio"] = result.data
            else:
                error_msg = result.error if result else "Unknown error"
                state["advisory"] = AdvisoryOutput(
                    query=query,
                    recommendations=[],
                    summary=f"Error:  Failed to update portfolio: {error_msg}",
                    timestamp=datetime.now(),
                )

            if result:
                if is_add_with_values:
                    AgentLogger.print_success(
                        "Portfolio updated with market values",
                        "Portfolio Update Handler",
                    )
                elif "update_command" in locals() and update_command:
                    AgentLogger.print_success(
                        f"Portfolio {update_command.action} completed",
                        "Portfolio Update Handler",
                    )
                else:
                    AgentLogger.print_success(
                        "Portfolio update completed", "Portfolio Update Handler"
                    )

        except Exception as e:
            print(f"Error:  Error handling portfolio update: {e}")
            import traceback

            traceback.print_exc()
            from schemas_v2 import AdvisoryOutput

            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=f"Error:  Error updating portfolio: {str(e)}",
                timestamp=datetime.now(),
            )
            state["errors"].append(f"Portfolio update error: {str(e)}")

        return state

    async def _run_analyst_for_portfolio_update(
        self, state: GraphState, bonds_universe: List[Dict]
    ) -> Dict[str, Any]:
        """Run analyst agent to get bond analytics for portfolio update"""
        try:
            # Use the analyst agent to get bond analytics
            analytics_data = await self.analyst.analyze_bonds(bonds_universe)
            return {"bond_analytics": analytics_data}
        except Exception as e:
            print(f"Warning: Could not get bond analytics: {e}")
            return {"bond_analytics": {}}
    async def _update_portfolio_with_market_values(
        self,
        user_id: str,
        portfolio_tool: Any,
        portfolio_result: Any,
        bond_analytics: Dict[str, Any],
        query: str,
    ) -> Any:
        """Update portfolio positions with market values from bond analytics"""
        from schemas_v2 import BondAnalytics

        if not portfolio_result.success or not portfolio_result.data:
            raise ValueError("Portfolio not found")

        holdings = portfolio_result.data.holdings
        if not holdings:
            raise ValueError("No bonds in portfolio to update")

        # Determine how many bonds to update (default: all, or top 5 if specified)
        query_lower = query.lower()
        limit = (
            5 if "top 5" in query_lower or "first 5" in query_lower else len(holdings)
        )
        bonds_to_update = holdings[:limit]

        # Default quantity per bond (1 lakh = 100,000)
        default_quantity = 100000.0

        # Match portfolio bonds with analytics and update
        bond_updates = []
        updated_count = 0

        for holding in bonds_to_update:
            isin = holding.isin
            bond_name = holding.bond_name

            # Try to find matching analytics
            analytics = None
            if isin in bond_analytics:
                analytics = bond_analytics[isin]
            else:
                # Try to match by name
                for key, value in bond_analytics.items():
                    if isinstance(value, BondAnalytics):
                        if (
                            bond_name.lower() in value.name.lower()
                            or value.name.lower() in bond_name.lower()
                        ):
                            analytics = value
                            isin = key  # Update ISIN if found
                            break

            if analytics:
                # Update with market data
                current_price = (
                    analytics.current_price
                    if isinstance(analytics, BondAnalytics)
                    else analytics.get("current_price", 0.0)
                )
                quantity = (
                    holding.quantity if holding.quantity > 0 else default_quantity
                )

                bond_updates.append(
                    {
                        "isin": isin,
                        "current_price": current_price,
                        "quantity": quantity,
                        "avg_cost": current_price,  # Assume bought at current price
                        "name": bond_name,
                    }
                )
                updated_count += 1
            else:
                # If no analytics found, use default values
                bond_updates.append(
                    {
                        "isin": isin,
                        "current_price": 100.0,  # Default price
                        "quantity": default_quantity,
                        "avg_cost": 100.0,
                        "name": bond_name,
                    }
                )

        # Update all bonds at once
        if bond_updates:
            result = await portfolio_tool.update_multiple_bonds(
                user_id=user_id, bond_updates=bond_updates
            )
            return result
        else:
            raise ValueError("No bonds to update")

    async def _handle_non_bond_query(self, state: GraphState) -> GraphState:
        """Handle non-bond queries by routing to general LLM or web search"""
        print(f"\n{'=' * 80}")
        print(f"INFO:  HANDLING NON-BOND QUERY...")
        state["current_step"] = "handling_non_bond_query"

        classified = state.get("classified_query")
        if not classified:
            # Fallback: treat as general LLM query
            routing = NonBondRouting.GENERAL_LLM
        else:
            routing_str = getattr(classified, "non_bond_routing", None)
            if routing_str:
                try:
                    routing = NonBondRouting(routing_str)
                except ValueError:
                    routing = NonBondRouting.GENERAL_LLM
            else:
                routing = NonBondRouting.GENERAL_LLM

        query = state["user_query"]

        # Get conversation history from LangGraph messages
        messages = state.get("messages", [])
        conversation_history = self._messages_to_dict(messages)

        try:
            if routing == NonBondRouting.WEB_SEARCH:
                print(f"  Routing to web search...")

                # Dynamically select model for general LLM (web search synthesis) if available and enabled
                if (
                    self.model_selector
                    and self.config.enable_dynamic_model_selection
                    and ModelSelectorAgentType
                ):
                    model = self.model_selector.get_model_for_agent(
                        ModelSelectorAgentType.GENERAL, query=query
                    )
                    if hasattr(self.general_llm, "model"):
                        if self.general_llm.model != model:
                            self.general_llm.model = model
                            print(f"  Using model: {model} for web search synthesis")

                # Use web search tool
                web_search_result = await self.tools[ToolType.WEB_SEARCH].search(
                    query=query, num_results=5
                )

                if web_search_result.success:
                    search_results = web_search_result.data
                    # Format search results into a summary
                    summary_parts = [f"Here are the search results for '{query}':\n"]
                    for i, result in enumerate(search_results[:3], 1):
                        summary_parts.append(f"{i}. {result.get('title', 'No title')}")
                        summary_parts.append(
                            f"   {result.get('snippet', 'No snippet')}"
                        )
                        summary_parts.append(
                            f"   Source: {result.get('url', 'No URL')}\n"
                        )

                    summary = "\n".join(summary_parts)

                    # Optionally use LLM to synthesize the results
                    synthesis_prompt = ChatPromptTemplate.from_messages(
                        [
                            (
                                "system",
                                """You are a helpful assistant. Based on the search results provided, 
give a clear and concise answer to the user's question. Cite sources when relevant.""",
                            ),
                            (
                                "user",
                                """Question: {query}

Search Results:
{search_results}

Provide a helpful answer based on these results.""",
                            ),
                        ]
                    )

                    search_results_text = "\n\n".join(
                        [
                            f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}\nURL: {r.get('url', '')}"
                            for r in search_results[:5]
                        ]
                    )

                    messages = synthesis_prompt.format_messages(
                        query=query, search_results=search_results_text
                    )
                    llm_response = self.general_llm.invoke(messages)
                    summary = (
                        llm_response.content
                        if hasattr(llm_response, "content")
                        else str(llm_response)
                    )
                else:
                    summary = f"I couldn't perform a web search for '{query}'. {web_search_result.error or 'Please try again later.'}"

            else:  # GENERAL_LLM
                print(f"  Routing to general LLM...")

                # Dynamically select model for general LLM if available and enabled
                if (
                    self.model_selector
                    and self.config.enable_dynamic_model_selection
                    and ModelSelectorAgentType
                ):
                    model = self.model_selector.get_model_for_agent(
                        ModelSelectorAgentType.GENERAL, query=query
                    )
                    if hasattr(self.general_llm, "model"):
                        if self.general_llm.model != model:
                            self.general_llm.model = model
                            print(f"  Using model: {model} for general LLM")

                # Format conversation history for context
                if conversation_history:
                    context_parts = ["Previous conversation:"]
                    # Include last 10 messages for context
                    for msg in conversation_history[-10:]:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        context_parts.append(f"{role.capitalize()}: {content}")
                    conversation_context = "\n".join(context_parts)
                else:
                    conversation_context = "No previous conversation."

                # Use general LLM with conversation history
                prompt_messages = self.general_prompt.format_messages(
                    query=query, conversation_context=conversation_context
                )
                response = self.general_llm.invoke(prompt_messages)
                summary = (
                    response.content if hasattr(response, "content") else str(response)
                )

            # Create advisory output with the response
            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=summary,
                timestamp=datetime.now(),
            )

            state["execution_path"].append("handle_non_bond_query")
            print(f" Non-bond query handled via {routing.value}")

        except Exception as e:
            print(f"  Error handling non-bond query: {e}")
            import traceback

            traceback.print_exc()
            state["errors"].append(f"Non-bond query handling error: {str(e)}")
            # Fallback response
            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=f"I encountered an error while processing your query. Please try rephrasing it or ask about bonds, portfolios, or trading.",
                timestamp=datetime.now(),
            )

        return state

    async def _check_portfolio(self, state: GraphState) -> GraphState:
        """Check if user has portfolio"""
        print(f"\nCHECKING PORTFOLIO...")
        state["current_step"] = "checking_portfolio"
        print("  Portfolio check skipped (will be fetched if needed)")
        state["execution_path"].append("check_portfolio")
        return state
    def _plan_execution(self, state: GraphState) -> GraphState:
        """Create execution plan"""
        AgentLogger.print_agent_header("Planner Agent", "PLANNING")
        state["current_step"] = "planning"
        try:
            # Dynamically select model for planner if model selector available and enabled
            if self.model_selector and self.config.enable_dynamic_model_selection:
                query = state["user_query"]
                # Use ModelSelectorAgentType from utils.model_selector if available
                if ModelSelectorAgentType:
                    model = self.model_selector.get_model_for_agent(
                        ModelSelectorAgentType.PLANNER, query=query
                    )
                else:
                    # Fallback: use default model
                    model = self.config.llm_model
                # Update planner LLM model
                if hasattr(self.planner, "llm") and hasattr(self.planner.llm, "model"):
                    if self.planner.llm.model != model:
                        self.planner.llm.model = model
                        print(f"  Using model: {model} for planning")

            # Get conversation history from LangGraph messages
            messages = state.get("messages", [])
            conversation_history = self._messages_to_dict(messages)

            if self.context_manager:
                context = self.context_manager.extract_relevant_context(
                    conversation_history, state["user_query"], agent_type="planner"
                )

            # Planner decides if portfolio is needed based on query (not based on whether it exists)
            plan = self.planner.create_plan(
                query=state["user_query"],
                has_portfolio=False,  # Planner decides based on query, not pre-existing portfolio
                conversation_history=conversation_history
                if conversation_history
                else None,
            )

            # Success:  CRITICAL: Detect recommendation queries and ensure tools/agents are added
            query_lower = state["user_query"].lower()

            # Get classified query early (needed for comparison query detection)
            classified = state.get("classified_query")

            # Detect portfolio queries that need portfolio tool
            is_portfolio_query = any(
                phrase in query_lower
                for phrase in [
                    "my portfolio",
                    "my bonds",
                    "my holdings",
                    "portfolio",
                    "show bonds",
                    "print bonds",
                    "list bonds",
                    "bonds in",
                    "holdings",
                    "positions",
                ]
            )

            # Detect maturity date queries
            # Distinguish between "mature in 2029" (exact) vs "mature by 2029" (<=)
            import re

            maturity_year = None
            is_exact_year = False  # True if "in 2029", False if "by 2029"

            # Check for "mature in 2029" or "maturing in 2029" (exact year)
            exact_match = re.search(
                r"(?:mature|maturing|maturity).*?\bin\s+(\d{4})\b", query_lower
            )
            if exact_match:
                maturity_year = int(exact_match.group(1))
                is_exact_year = True

            # Check for "mature by 2029" or "maturing by 2029" (<= year)
            if not maturity_year:
                by_match = re.search(
                    r"(?:mature|maturing|maturity).*?(?:by|before|until|till)\s*(\d{4})",
                    query_lower,
                )
                if by_match:
                    maturity_year = int(by_match.group(1))
                    is_exact_year = False

            # Also check for patterns like "bonds in 2032", "bonds 2032", "2032 bonds"
            # Default to exact match if "in" is present, otherwise assume "by"
            if not maturity_year:
                year_match = re.search(r"\b(20\d{2})\b", query_lower)
                if year_match and any(
                    phrase in query_lower
                    for phrase in ["bond", "mature", "maturing", "maturity"]
                ):
                    maturity_year = int(year_match.group(1))
                    # Check if query contains "in" to determine if it's exact
                    is_exact_year = (
                        " in " in query_lower
                        or query_lower.startswith("in ")
                        or query_lower.endswith(" in")
                    )

            is_maturity_query = maturity_year is not None

            # Detect comparison queries (e.g., "compare bond A vs B", "which is better X or Y")
            is_comparison_query = any(
                phrase in query_lower
                for phrase in [
                    "compare",
                    "comparison",
                    "vs",
                    "versus",
                    "difference between",
                    "which is better",
                    "which bond is better",
                    "compare bonds",
                    "comparing",
                    "side by side",
                ]
            )

            # Extract bond identifiers from comparison queries
            bond_identifiers = []
            if is_comparison_query:
                # Extract ISINs (format: INE123A01012 or IN0020230010)
                isin_pattern = r"\b(IN[E0][A-Z0-9]{9,10})\b"
                isins = re.findall(isin_pattern, query_lower.upper())
                bond_identifiers.extend(isins)

                # Extract bond symbols (format: 667GS2035, 717GS2030)
                symbol_pattern = r"\b(\d{3}[A-Z]{2}\d{4})\b"
                symbols = re.findall(symbol_pattern, query_lower.upper())
                bond_identifiers.extend(symbols)

                # Extract from entities if available (from query classifier)
                if classified:
                    # Handle both dict and object formats
                    if isinstance(classified, dict):
                        entities = classified.get("entities", [])
                    else:
                        entities = getattr(classified, "entities", [])

                    if entities:
                        # Filter entities that look like bond identifiers
                        for entity in entities:
                            if isinstance(entity, str):
                                entity_upper = entity.upper()
                                # Check if it's an ISIN or symbol
                                if re.match(
                                    r"^IN[E0][A-Z0-9]{9,10}$", entity_upper
                                ) or re.match(r"^\d{3}[A-Z]{2}\d{4}$", entity_upper):
                                    if entity_upper not in bond_identifiers:
                                        bond_identifiers.append(entity_upper)

            # Detect yield queries that need MCP tools (not news/web search)
            is_yield_query = any(
                phrase in query_lower
                for phrase in [
                    "yield",
                    "yields",
                    "g-sec",
                    "gsec",
                    "government bond yield",
                    "bond yield",
                    "real-time yield",
                    "current yield",
                    "latest yield",
                    "show me yield",
                    "what are the yields",
                    "yield rates",
                    "yield curve",
                    "g-secs",
                    "government securities",
                ]
            )

            # Only detect recommendation queries if they explicitly ask for recommendations/advice
            # "bonds maturing", "list bonds", "find bonds" are informational, NOT recommendations
            is_recommendation_query = any(
                phrase in query_lower
                for phrase in [
                    "what bonds should",
                    "which bonds should",
                    "recommend bonds",
                    "suggest bonds",
                    "what should i buy",
                    "which should i buy",
                    "bonds to buy",
                    "best bonds",
                    "good bonds",
                    "top bonds",
                    "buy tomorrow",
                    "buy today",
                    "should i buy",
                    "high yielding bonds to buy",
                    "best bonds to invest",
                    "recommendations",
                    "what to invest",
                    "which to invest",
                    "should i invest",
                ]
            )

            # Explicitly exclude informational queries that might match above patterns
            # These are informational, not recommendation requests
            informational_patterns = [
                "what are bonds",
                "which are bonds",
                "show me bonds",
                "list bonds",
                "find bonds",
                "bonds maturing",
                "bonds with",
                "bonds that",
            ]
            if any(pattern in query_lower for pattern in informational_patterns):
                # Only treat as recommendation if it ALSO has explicit recommendation keywords
                if not any(
                    phrase in query_lower
                    for phrase in [
                        "should",
                        "recommend",
                        "suggest",
                        "best",
                        "good",
                        "top",
                        "buy",
                    ]
                ):
                    is_recommendation_query = False

            # Also check classified query intent (already retrieved above)
            if classified:
                intent = getattr(classified, "intent", None)
                if hasattr(intent, "value"):
                    intent_str = intent.value
                else:
                    intent_str = str(intent) if intent else ""

                # If intent suggests recommendations, treat as recommendation query
                if intent_str in [
                    "buy_recommendation",
                    "increase_yield",
                    "reduce_duration",
                    "improve_quality",
                ]:
                    is_recommendation_query = True

            if plan.tools_needed:
                tool_names = [t.tool_type.value for t in plan.tools_needed]

                # Queries that need full analysis pipeline (recommendations)
                bond_search_tools = [
                    "search_bonds",
                    "list_bonds",
                    "filter_bonds",
                    "recommend_bonds",
                    "get_bond_info",
                    "compare_bonds",
                    "fetch_bond_universe",
                ]

                # Legacy tool names that also indicate bond discovery needed
                legacy_bond_tools = ["bond_pricer"]

                # Queries that are just informational (don't need pipeline)
                info_only_tools = [
                    "get_latest_yields",
                    "get_current_yields",
                    "get_yield_forecast",
                    "get_yield_curve",
                ]

                has_bond_search = any(tool in tool_names for tool in bond_search_tools)
                has_legacy_bond_tool = any(
                    tool in tool_names for tool in legacy_bond_tools
                )
                is_info_only = all(tool in info_only_tools for tool in tool_names)

                # If it's a portfolio query but no portfolio tool is present, add it
                if is_portfolio_query and not any(
                    tool in tool_names
                    for tool in ["portfolio_manager", "get_user_portfolio"]
                ):
                    from schemas_v2 import ToolCall

                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.PORTFOLIO_MANAGER,
                            parameters={"user_id": state.get("user_id", "")},
                            priority=1,
                        )
                    )
                    print(
                        f"  Success:  Auto-added portfolio_manager for portfolio query"
                    )
                    tool_names.append(
                        "portfolio_manager"
                    )  # Update for subsequent checks

                # If it's a maturity query but no bond discovery tool is present, add filter_bonds
                if is_maturity_query and not any(
                    tool in tool_names
                    for tool in [
                        "filter_bonds",
                        "list_bonds",
                        "fetch_bond_universe",
                        "search_bonds",
                    ]
                ):
                    from schemas_v2 import ToolCall

                    # Use exact year match if "in" was detected, otherwise use "by" (<=)
                    if is_exact_year:
                        # Exact match: set both min and max to the same year
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.FILTER_BONDS,
                                parameters={
                                    "max_maturity_year": int(maturity_year),
                                    "min_maturity_year": int(maturity_year),
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added filter_bonds for maturity query (bonds maturing in {maturity_year})"
                        )
                    else:
                        # "By" match: use max_maturity_year only (<=)
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.FILTER_BONDS,
                                parameters={
                                    "max_maturity_year": int(maturity_year),
                                    "min_maturity_year": 0,
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added filter_bonds for maturity query (bonds maturing by {maturity_year})"
                        )
                    tool_names.append("filter_bonds")  # Update for subsequent checks
                    has_bond_search = True

                # If it's a yield query but no yield tool is present, add it
                if is_yield_query and not any(
                    tool in tool_names
                    for tool in [
                        "get_latest_yields",
                        "get_current_yields",
                        "get_yield_forecast",
                        "get_yield_curve",
                    ]
                ):
                    from schemas_v2 import ToolCall

                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.GET_LATEST_YIELDS,
                            parameters={},
                            priority=1,
                        )
                    )
                    print(f"  Success:  Auto-added get_latest_yields for yield query")
                    tool_names.append(
                        "get_latest_yields"
                    )  # Update for subsequent checks
                    is_info_only = True  # Mark as info-only query

                # If it's a comparison query, add compare_bonds tool
                if is_comparison_query and not any(
                    tool in tool_names for tool in ["compare_bonds"]
                ):
                    from schemas_v2 import ToolCall

                    if bond_identifiers and len(bond_identifiers) >= 2:
                        # We have at least 2 identifiers, use compare_bonds tool
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.COMPARE_BONDS,
                                parameters={
                                    "bond_identifiers": ",".join(
                                        bond_identifiers[:10]
                                    )  # Limit to 10 bonds
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added compare_bonds for comparison query ({len(bond_identifiers)} bonds)"
                        )
                        tool_names.append("compare_bonds")
                    elif bond_identifiers and len(bond_identifiers) == 1:
                        # Only 1 identifier found, try to search for more or get details
                        print(
                            f"  Info:   Only 1 bond identifier found, will get bond details for comparison"
                        )
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.GET_BOND_DETAILS,
                                parameters={
                                    "bond_identifier": bond_identifiers[0],
                                    "days_ahead": 0,
                                },
                                priority=1,
                            )
                        )
                        tool_names.append("get_bond_details")
                    else:
                        # No identifiers found, try to search for bonds mentioned in query
                        print(
                            f"  Warning:   Comparison query detected but no bond identifiers found, will try to extract from query"
                        )
                        # Will be handled in fallback logic below

                # If it's a recommendation query but no bond discovery tools, add them
                if (
                    is_recommendation_query
                    and not has_bond_search
                    and not has_legacy_bond_tool
                ):
                    from schemas_v2 import ToolCall

                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.FETCH_BOND_UNIVERSE,
                            parameters={"limit": 50},
                            priority=1,
                        )
                    )
                    print(
                        f"  Success:  Auto-added fetch_bond_universe for recommendation query"
                    )
                    has_bond_search = True

                # If legacy bond_pricer is requested but no bonds, add bond discovery
                if has_legacy_bond_tool and not has_bond_search:
                    from schemas_v2 import ToolCall

                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.FETCH_BOND_UNIVERSE,
                            parameters={"limit": 50},
                            priority=1,
                        )
                    )
                    print(
                        f"  Success:  Auto-added fetch_bond_universe for bond_pricer tool"
                    )
                    has_bond_search = True

                if (has_bond_search or has_legacy_bond_tool) and not is_info_only:
                    # User is searching for bonds → they want recommendations
                    print(
                        f"  ⚡ Adding full analysis pipeline for bond recommendations"
                    )

                    needed_agents = [
                        AgentType.ML_MODEL,
                        AgentType.ANALYST,
                        AgentType.SCORING,
                        AgentType.ADVISORY,
                    ]
                    for agent in needed_agents:
                        if agent not in plan.agents_needed:
                            plan.agents_needed.append(agent)

                    # Success:  CRITICAL: Ensure we have bonds to analyze
                    # Re-check after adding tools
                    tool_names = [t.tool_type.value for t in plan.tools_needed]
                    has_bond_discovery = any(
                        tool in tool_names
                        for tool in [
                            "list_bonds",
                            "fetch_bond_universe",
                            "search_bonds",
                            "filter_bonds",
                            "recommend_bonds",
                        ]
                    )
                    if not has_bond_discovery:
                        from schemas_v2 import ToolCall

                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.FETCH_BOND_UNIVERSE,
                                parameters={"limit": 50},
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added fetch_bond_universe to get bonds for analysis"
                        )

                    # Success:  Ensure we have latest yields for analyst
                    has_latest_yields = any(
                        t.tool_type.value in ["get_latest_yields", "get_current_yields"]
                        for t in plan.tools_needed
                    )
                    if (
                        not has_latest_yields
                        and AgentType.ANALYST in plan.agents_needed
                    ):
                        from schemas_v2 import ToolCall

                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.GET_LATEST_YIELDS,
                                parameters={},
                                priority=1,
                            )
                        )
                        print(f"  Success:  Auto-added get_latest_yields for analyst")

                    # Ensure we have yield forecasts for ML
                    has_forecasts = any(
                        "forecast" in t.tool_type.value
                        or "yield" in t.tool_type.value
                        or t.tool_type.value == "yield_forecaster"
                        for t in plan.tools_needed
                    )
                    if not has_forecasts:
                        from schemas_v2 import ToolCall

                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.GET_ALL_YIELD_FORECASTS,
                                parameters={},
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added get_all_yield_forecasts for ML model"
                        )
                else:
                    # Info-only query (just yields) → no agents needed
                    print(f"  Info:   Info-only query, skipping analysis pipeline")
            elif is_recommendation_query:
                # Planner didn't add tools, but this is clearly a recommendation query
                # Force add everything needed
                print(f"  ⚡ Detected recommendation query - adding full pipeline")
                from schemas_v2 import ToolCall

                # Initialize tools_needed if empty
                if not plan.tools_needed:
                    plan.tools_needed = []

                # Add bond discovery
                plan.tools_needed.append(
                    ToolCall(
                        tool_type=ToolType.FETCH_BOND_UNIVERSE,
                        parameters={"limit": 50},
                        priority=1,
                    )
                )

                # Add yield tools
                plan.tools_needed.append(
                    ToolCall(
                        tool_type=ToolType.GET_LATEST_YIELDS, parameters={}, priority=1
                    )
                )

                plan.tools_needed.append(
                    ToolCall(
                        tool_type=ToolType.GET_ALL_YIELD_FORECASTS,
                        parameters={},
                        priority=1,
                    )
                )

                # Add all agents
                needed_agents = [
                    AgentType.ML_MODEL,
                    AgentType.ANALYST,
                    AgentType.SCORING,
                    AgentType.ADVISORY,
                ]
                for agent in needed_agents:
                    if agent not in plan.agents_needed:
                        plan.agents_needed.append(agent)

                print(
                    f"  Success:  Force-added bond discovery, yields, and all agents for recommendation"
                )

            # Success:  CRITICAL: Always ensure yields are available if analyst is needed
            if plan and AgentType.ANALYST in plan.agents_needed:
                has_latest_yields = any(
                    t.tool_type.value in ["get_latest_yields", "get_current_yields"]
                    for t in plan.tools_needed
                )
                if not has_latest_yields:
                    from schemas_v2 import ToolCall

                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.GET_LATEST_YIELDS,
                            parameters={},
                            priority=1,
                        )
                    )
                    print(f"  Success:  Force-added get_latest_yields for analyst")

            # If no tools were added by planner, check for portfolio, maturity, comparison, or yield queries
            elif not plan.tools_needed or len(plan.tools_needed) == 0:
                from schemas_v2 import ToolCall

                if not plan.tools_needed:
                    plan.tools_needed = []

                # Add portfolio tool for portfolio queries
                if is_portfolio_query:
                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.PORTFOLIO_MANAGER,
                            parameters={"user_id": state.get("user_id", "")},
                            priority=1,
                        )
                    )
                    print(
                        f"  Success:  Auto-added portfolio_manager for portfolio query (planner didn't add tools)"
                    )
                # Add compare_bonds for comparison queries
                elif is_comparison_query:
                    if bond_identifiers and len(bond_identifiers) >= 2:
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.COMPARE_BONDS,
                                parameters={
                                    "bond_identifiers": ",".join(bond_identifiers[:10])
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added compare_bonds for comparison query ({len(bond_identifiers)} bonds) (planner didn't add tools)"
                        )
                    elif bond_identifiers and len(bond_identifiers) == 1:
                        # Only 1 identifier, get its details
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.GET_BOND_DETAILS,
                                parameters={
                                    "bond_identifier": bond_identifiers[0],
                                    "days_ahead": 0,
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added get_bond_details for comparison query (1 bond found) (planner didn't add tools)"
                        )
                    else:
                        print(
                            f"  Warning:   Comparison query detected but no bond identifiers found (planner didn't add tools)"
                        )
                # Add filter_bonds for maturity queries
                elif is_maturity_query:
                    # Use exact year match if "in" was detected, otherwise use "by" (<=)
                    if is_exact_year:
                        # Exact match: set both min and max to the same year
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.FILTER_BONDS,
                                parameters={
                                    "max_maturity_year": int(maturity_year),
                                    "min_maturity_year": int(maturity_year),
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added filter_bonds for maturity query (bonds maturing in {maturity_year}) (planner didn't add tools)"
                        )
                    else:
                        # "By" match: use max_maturity_year only (<=)
                        plan.tools_needed.append(
                            ToolCall(
                                tool_type=ToolType.FILTER_BONDS,
                                parameters={
                                    "max_maturity_year": int(maturity_year),
                                    "min_maturity_year": 0,
                                },
                                priority=1,
                            )
                        )
                        print(
                            f"  Success:  Auto-added filter_bonds for maturity query (bonds maturing by {maturity_year}) (planner didn't add tools)"
                        )
                # Add yield tool for yield queries
                elif is_yield_query:
                    plan.tools_needed.append(
                        ToolCall(
                            tool_type=ToolType.GET_LATEST_YIELDS,
                            parameters={},
                            priority=1,
                        )
                    )
                    print(
                        f"  Success:  Auto-added get_latest_yields for yield query (planner didn't add tools)"
                    )

            state["execution_plan"] = plan

            # Override plan flags based on classification
            if state.get("needs_explainability"):
                plan.needs_explainability = True
            if state.get("needs_rag"):
                plan.needs_rag = True
            # Note: News gathering is handled by real-time info agent in _gather_realtime_info step
            # No need to inject news_scraper here - real-time info agent will handle it intelligently
            # Only append to execution_path if not called internally from parallel execution
            if not state.get("_internal_call", False):
                state["execution_path"].append("plan_execution")
            AgentLogger.print_agent_output(
                "Planner Agent",
                {
                    "Tools": [t.tool_type.value for t in plan.tools_needed],
                    "Agents": [a.value for a in plan.agents_needed],
                    "Reasoning": plan.reasoning[:200] + "..."
                    if len(plan.reasoning) > 200
                    else plan.reasoning,
                },
                "Execution Plan",
            )
            AgentLogger.print_success("Execution plan created", "Planner Agent")

        except Exception as e:
            print(f" Planning error: {e}")
            import traceback

            traceback.print_exc()
            state["errors"].append(f"Planning error: {str(e)}")
            # Create fallback plan
            from schemas_v2 import ToolCall, DataSource
            state["execution_plan"] = ExecutionPlan(
                plan_id=f"fallback_{hash(state['user_query']) % 10000}",
                query=state["user_query"],
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
                needs_explainability=state.get("needs_explainability", False),
                needs_rag=state.get("needs_rag", False),
                needs_portfolio_access=False,  # Planner will decide
                reasoning="Fallback plan due to planning error",
            )

        return state

    async def _execute_tools(self, state: GraphState) -> GraphState:
        """Execute tools using MCP client"""
        logger.info("EXECUTING TOOLS...")
        state["current_step"] = "execute_tools"
        # Initialize cache tracking if not present
        if "total_tool_calls" not in state:
            state["total_tool_calls"] = 0
        if "cache_hits" not in state:
            state["cache_hits"] = 0

        # Use StateHelper for safe state access
        user_query = self._get_state_value(state, "user_query", "")
        plan = self._get_state_value(state, "execution_plan")

        logger.debug(f"  - User query: {user_query[:100] if user_query else 'N/A'}")
        logger.debug(f"  - Execution plan exists: {plan is not None}")

        if plan and plan.tools_needed:
            logger.debug(f"  - Tools in plan: {len(plan.tools_needed)}")
            for i, tool in enumerate(plan.tools_needed):
                tool_name = self._normalize_tool_name(tool)
                logger.debug(f"    {i + 1}. {tool_name}")
        else:
            logger.debug("  - NO PLAN!")

        logger.debug(f"  - MCP client initialized: {self.mcp_client is not None}")

        if not plan or not plan.tools_needed:
            logger.info("  No tools requested by planner")
            StateHelper.ensure_list(state, "execution_path").append("execute_tools")
            return state

        logger.info(f"  Requested: {len(plan.tools_needed)} tools")

        # Check if MCP client is available
        if not self.mcp_client:
            logger.error("  Error:  MCP client not initialized!")
            StateHelper.ensure_list(state, "errors").append("MCP client not available")
            StateHelper.ensure_list(state, "execution_path").append("execute_tools")
            return state
        # Execute each tool
        for tool_call in plan.tools_needed:
            # Use helper method for tool name normalization
            tool_name = self._normalize_tool_name(tool_call)
            tool_name_normalized = tool_name
            # Success:  NEW: Optimize tool parameters based on current state
            tool_call = self._optimize_tool_parameters(tool_call, state)
            if tool_call is None:
                # Tool was skipped (e.g., data already available)
                continue

            params = tool_call.parameters or {}

            logger.info(f"  -> Executing: {tool_name}")

            try:
                result = None

                # ===== YIELD ANALYTICS TOOLS =====
                if tool_name in ["get_current_yields", "get_latest_yields"]:
                    result = await self.mcp_client.get_latest_yields()
                    result = _parse_mcp_result(result)
                    # Success:  FIX: Extract yields field for analyst compatibility
                    if isinstance(result, dict) and "yields" in result:
                        yields_dict = result["yields"]
                    else:
                        yields_dict = result

                    # Success:  Store raw yields for display (percentages)
                    state["latest_yields_display"] = yields_dict

                    # Success:  FIX: Convert to decimal format for analyst
                    # MCP now returns percentage (5.703), analyst expects decimal (0.05703)
                    yields_decimal = {}
                    for maturity, rate in yields_dict.items():
                        # maturity is already float without 'Y' suffix from mcp_client
                        # Convert percentage to decimal (5.703 -> 0.05703)
                        yields_decimal[maturity] = rate / 100.0

                    state["yield_curve"] = yields_decimal
                    print(f"      Got {len(yields_decimal)} yield points")

                elif tool_name in ["forecast_all_yields", "get_all_yield_forecasts"]:
                    result = await self.mcp_client.get_all_yield_forecasts()
                    result = _parse_mcp_result(result)
                    state["yield_forecasts"] = result  # Just store raw dict
                    print(
                        f"DEBUG  Stored yield forecasts: {list(result.keys()) if isinstance(result, dict) else type(result)}"
                    )
                    print(f"      Got forecasts for {len(result)} maturities")

                elif tool_name in ["forecast_specific_yield", "get_yield_forecast"]:
                    maturity = params.get("maturity", 10)
                    days_ahead = params.get("days_ahead", 21)
                    result = await self.mcp_client.get_yield_forecast(
                        maturity, days_ahead
                    )
                    if not state.get("specific_forecasts"):
                        state["specific_forecasts"] = []
                    state["specific_forecasts"].append(
                        {"maturity": maturity, "forecasts": result}
                    )
                    print(f"      Got {len(result)} forecast points for {maturity}Y")

                elif tool_name == "get_yield_curve":
                    days_ahead = params.get("days_ahead", 1)
                    result = await self.mcp_client.get_yield_curve(days_ahead)
                    if not state.get("market_analysis"):
                        state["market_analysis"] = {}
                    state["market_analysis"]["yield_curve"] = result
                    print(f"      Got yield curve for day {days_ahead}")

                elif tool_name in [
                    "analyze_yield_slope",
                    "calculate_yield_curve_slope",
                ]:
                    # Calculate from current yields
                    yields = await self.mcp_client.get_latest_yields()
                    if 2.0 in yields and 10.0 in yields:
                        slope = yields[10.0] - yields[2.0]
                        result = {
                            "slope_10y_2y": slope * 100,  # Convert to bps
                            "y2": yields[2.0] * 100,
                            "y10": yields[10.0] * 100,
                        }
                        if not state.get("market_analysis"):
                            state["market_analysis"] = {}
                        state["market_analysis"]["yield_slope"] = result
                        print(f"      Calculated slope: {slope * 100:.1f} bps")

                # ===== BOND DISCOVERY TOOLS =====
                elif tool_name in ["fetch_bond_universe", "list_bonds"]:
                    limit = params.get("limit", 0)
                    try:
                        result = await self.mcp_client.list_bonds()
                        result = _parse_mcp_result(result)
                        bonds = self.mcp_client.to_bond_universe(result)

                        # Success:  APPLY MATURITY FILTER (≤10 years)
                        original_count = len(bonds)
                        bonds = MATURITY_FILTER.filter_bonds(bonds)
                        filtered_count = len(bonds)
                    except Exception as e:
                        print(f"      WARNING: Failed to fetch bonds from MCP: {e}")
                        print(f"      Error details: {type(e).__name__}")
                        bonds = []
                        original_count = 0
                        filtered_count = 0

                    if original_count > filtered_count:
                        print(
                            f"     DEBUG  Maturity Filter: {original_count} → {filtered_count} bonds (removed {original_count - filtered_count} bonds >10Y)"
                        )

                    # Apply limit if specified
                    if limit > 0:
                        bonds = bonds[:limit]

                    state["bonds_universe"] = bonds
                    print(f"      Loaded {len(bonds)} bonds (≤10 years maturity)")

                elif tool_name == "search_bonds":
                    search_term = params.get("search_term", "")
                    result = await self.mcp_client.search_bonds(search_term)
                    result = _parse_mcp_result(result)
                    bonds = result.get("bonds", [])
                    # ENRICH bonds with real price, YTM, duration from MCP
                    print(f"     Enriching {len(bonds)} bonds with live data...")
                    enriched_bonds = []

                    for item in bonds:
                        isin = item if isinstance(item, str) else item.get("isin")
                        if not isin:
                            continue

                        try:
                            # Get full bond details (check cache first)
                            # Use get_bond_details which includes LTP, YTM, duration (comprehensive)
                            bond_info = await self.bond_cache.get_bond_details(isin)

                            if not bond_info:
                                # Try get_bond_details first (comprehensive), fallback to get_bond_info
                                if hasattr(self.mcp_client, "get_bond_details"):
                                    bond_info = await self.mcp_client.get_bond_details(
                                        isin, days_ahead=0
                                    )
                                else:
                                    bond_info = await self.mcp_client.get_bond_info(
                                        isin
                                    )
                                bond_info = _parse_mcp_result(bond_info)
                                if bond_info and "error" not in bond_info:
                                    # Cache the result
                                    await self.bond_cache.set_bond_details(
                                        isin, bond_info
                                    )

                            if bond_info and "error" not in bond_info:
                                bond = bond_info
                            else:
                                bond = {"isin": isin, "name": f"Bond {isin}"}

                            # Get price (check cache first)
                            price_result = await self.bond_cache.get_bond_price(
                                isin, days_ahead=0
                            )

                            if not price_result:
                                price_result = await self.mcp_client.get_bond_price(
                                    isin
                                )
                                price_result = _parse_mcp_result(price_result)
                                if price_result and "error" not in price_result:
                                    # Cache the result
                                    await self.bond_cache.set_bond_price(
                                        isin, 0, price_result
                                    )

                            if price_result and "ending_price" in price_result:
                                bond["current_price"] = price_result["ending_price"]
                                bond["last_traded_price"] = price_result["ending_price"]
                            elif price_result and "starting_price" in price_result:
                                bond["current_price"] = price_result["starting_price"]
                                bond["last_traded_price"] = price_result[
                                    "starting_price"
                                ]

                            ytm_result = await self.mcp_client.calculate_bond_ytm(isin)
                            ytm_result = _parse_mcp_result(ytm_result)
                            if ytm_result and "ytm_percent" in ytm_result:
                                bond["ytm"] = ytm_result["ytm_percent"]

                            duration_result = (
                                await self.mcp_client.calculate_bond_duration(isin)
                            )
                            duration_result = _parse_mcp_result(duration_result)
                            if (
                                duration_result
                                and "modified_duration" in duration_result
                            ):
                                bond["duration"] = duration_result["modified_duration"]

                            print(
                                f"         {isin}: Price=₹{bond.get('current_price', 'N/A')}, YTM={bond.get('ytm', 'N/A')}%"
                            )
                            enriched_bonds.append(bond)

                        except Exception as e:
                            print(f"        Warning:  {isin}: {e}")

                    state["bonds_universe"] = enriched_bonds

                    # Success:  APPLY MATURITY FILTER (≤10 years)
                    original_count = len(enriched_bonds)
                    state["bonds_universe"] = MATURITY_FILTER.filter_bonds(
                        enriched_bonds
                    )
                    filtered_count = len(state["bonds_universe"])

                    if original_count > filtered_count:
                        print(
                            f"     DEBUG  Maturity Filter: {original_count} → {filtered_count} bonds (removed {original_count - filtered_count} bonds >10Y)"
                        )

                    print(f"      Enriched bonds count: {len(state['bonds_universe'])}")
                    print(
                        f"     DEBUG  DEBUG: enriched_bonds = {state['bonds_universe'][:1] if state['bonds_universe'] else 'EMPTY!'}"
                    )
                    print(
                        f"      Found {len(state['bonds_universe'])} matching bonds (≤10 years maturity)"
                    )

                elif tool_name == "filter_bonds":
                    # Extract parameters
                    max_years = params.get("max_years_to_maturity", 0.0)
                    max_maturity_year = params.get("max_maturity_year", 0)
                    min_maturity_year = params.get("min_maturity_year", 0)

                    # If max_maturity_year is provided, calculate max_years as a fallback
                    if max_maturity_year > 0 and max_years == 0:
                        current_year = datetime.now().year
                        max_years = (
                            max_maturity_year - current_year + 1
                        )  # Add 1 to be safe
                        if max_years < 0:
                            max_years = 0.0

                    # Call MCP client with all parameters (including maturity_year)
                    result = await self.mcp_client.filter_bonds(
                        min_coupon=params.get("min_coupon", 0.0),
                        max_coupon=params.get("max_coupon", 0.0),
                        min_years_to_maturity=params.get("min_years_to_maturity", 0.0),
                        max_years_to_maturity=max_years,
                        min_maturity_year=min_maturity_year,
                        max_maturity_year=max_maturity_year,
                        symbol_contains=params.get("symbol_contains", ""),
                        name_contains=params.get("name_contains", ""),
                    )

                    bonds = result.get("bonds", [])

                    # Post-process results to filter by maturity_year as a safety net
                    # (MCP server should handle this, but we double-check)
                    if max_maturity_year > 0:
                        filtered_bonds = []
                        # Check if it's an exact year match (min == max) or a range (min < max)
                        is_exact_match = (
                            min_maturity_year > 0
                            and min_maturity_year == max_maturity_year
                        )

                        for bond in bonds:
                            maturity_date_str = bond.get("maturity_date", "")
                            if maturity_date_str:
                                try:
                                    maturity_date = datetime.strptime(
                                        maturity_date_str, "%Y-%m-%d"
                                    )
                                    if is_exact_match:
                                        # Exact match: year must equal the target year
                                        if maturity_date.year == max_maturity_year:
                                            filtered_bonds.append(bond)
                                    else:
                                        # Range match: year must be <= max_maturity_year
                                        if min_maturity_year > 0:
                                            # Both min and max specified
                                            if (
                                                min_maturity_year
                                                <= maturity_date.year
                                                <= max_maturity_year
                                            ):
                                                filtered_bonds.append(bond)
                                        else:
                                            # Only max specified (<=)
                                            if maturity_date.year <= max_maturity_year:
                                                filtered_bonds.append(bond)
                                except Exception as e:
                                    # Skip bonds with invalid dates
                                    continue
                        bonds = filtered_bonds
                        if is_exact_match:
                            print(
                                f"      Post-filtered by maturity_year == {max_maturity_year}: {len(bonds)} bonds (from {len(result.get('bonds', []))} total)"
                            )
                        else:
                            print(
                                f"      Post-filtered by maturity_year <= {max_maturity_year}: {len(bonds)} bonds (from {len(result.get('bonds', []))} total)"
                            )

                    # Only apply 10-year maturity filter if NOT filtering by maturity_year
                    # (maturity_year filter is more specific and should take precedence)
                    if max_maturity_year == 0:
                        # Success:  APPLY MATURITY FILTER (≤10 years) - only if not using maturity_year
                        original_count = len(bonds)
                        bonds = MATURITY_FILTER.filter_bonds(bonds)
                        filtered_count = len(bonds)

                        if original_count > filtered_count:
                            print(
                                f"     DEBUG  Maturity Filter: {original_count} → {filtered_count} bonds (removed {original_count - filtered_count} bonds >10Y)"
                            )

                    state["bonds_universe"] = bonds
                    print(
                        f"      Final filtered bonds: {len(state['bonds_universe'])} bonds"
                    )

                elif tool_name in ["get_bond_info", "get_bond_details"]:
                    bond_id = params.get("bond_identifier", params.get("bond_id", ""))
                    if bond_id:
                        result = await self.mcp_client.get_bond_info(bond_id)
                        if not state.get("bond_details"):
                            state["bond_details"] = {}
                        state["bond_details"][bond_id] = result
                        print(f"      Got details for {bond_id}")
                # ===== BOND VALUATION TOOLS =====
                elif tool_name in ["price_single_bond", "get_bond_price"]:
                    bond_id = params.get("bond_identifier", params.get("bond_id", ""))
                    days_ahead = params.get("days_ahead", 0)

                    if bond_id:
                        # Check cache first
                        cached_price = await self.bond_cache.get_bond_price(
                            bond_id, days_ahead
                        )

                        if cached_price:
                            print(
                                f"      Using cached price prediction (21d) for {bond_id}"
                            )
                            state["cache_hits"] = state.get("cache_hits", 0) + 1
                            if not state.get("bond_price_forecasts"):
                                state["bond_price_forecasts"] = {}
                            state["bond_price_forecasts"][bond_id] = (
                                self._transform_bond_price_forecast(
                                    cached_price, bond_id
                                )
                            )
                            result = {
                                "bond_id": bond_id,
                                "cached": True,
                                "source": "cache",
                            }
                        else:
                            # Fetch from MCP
                            result = await self.mcp_client.get_bond_price(
                                bond_id, days_ahead
                            )
                            result = _parse_mcp_result(result)

                            # Cache the result
                            await self.bond_cache.set_bond_price(
                                bond_id, days_ahead, result
                            )

                            if not state.get("bond_price_forecasts"):
                                state["bond_price_forecasts"] = {}
                            state["bond_price_forecasts"][bond_id] = (
                                self._transform_bond_price_forecast(result, bond_id)
                            )
                            state["total_tool_calls"] = (
                                state.get("total_tool_calls", 0) + 1
                            )

                            if days_ahead > 0:
                                print(
                                    f"      Got price for {bond_id} at day {days_ahead}"
                                )
                            else:
                                print(f"      Got price trajectory for {bond_id}")
                    else:
                        result = {"error": "No bond_identifier provided"}
                elif tool_name == "price_all_bonds":
                    # Price multiple bonds (get first 20 from universe) with caching
                    bonds = state.get("bonds_universe", [])[:20]
                    if not state.get("bond_price_forecasts"):
                        state["bond_price_forecasts"] = {}

                    cached_count = 0
                    fetched_count = 0

                    for bond in bonds:
                        bond_id = bond.get("symbol") or bond.get("isin")
                        if bond_id:
                            try:
                                # Check cache first
                                cached_price = await self.bond_cache.get_bond_price(
                                    bond_id, days_ahead=0
                                )

                                if cached_price:
                                    print(
                                        f"    Using cached price prediction (21d) for {bond_id}"
                                    )
                                    state["cache_hits"] = state.get("cache_hits", 0) + 1
                                    cached_count += 1
                                    state["bond_price_forecasts"][bond_id] = (
                                        self._transform_bond_price_forecast(
                                            cached_price, bond_id
                                        )
                                    )
                                else:
                                    # Fetch from MCP
                                    price = await self.mcp_client.get_bond_price(
                                        bond_id, days_ahead=0
                                    )
                                    price = _parse_mcp_result(price)

                                    # Cache the result
                                    await self.bond_cache.set_bond_price(
                                        bond_id, 0, price
                                    )

                                    state["bond_price_forecasts"][bond_id] = (
                                        self._transform_bond_price_forecast(
                                            price, bond_id
                                        )
                                    )
                                    state["total_tool_calls"] = (
                                        state.get("total_tool_calls", 0) + 1
                                    )
                                    fetched_count += 1
                            except Exception as e:
                                print(
                                    f"       Warning:  Failed to price {bond_id}: {e}"
                                )

                    print(
                        f"      Priced {len(state['bond_price_forecasts'])} bonds ({cached_count} cached, {fetched_count} fetched)"
                    )

                elif tool_name == "calculate_bond_ytm":
                    bond_id = params.get("bond_identifier", "")
                    if bond_id:
                        result = await self.mcp_client.calculate_bond_ytm(bond_id)
                        if not state.get("bond_analytics"):
                            state["bond_analytics"] = {}
                        if bond_id not in state["bond_analytics"]:
                            state["bond_analytics"][bond_id] = {}
                        state["bond_analytics"][bond_id].update(result)
                        print(f"      Calculated YTM for {bond_id}")
                elif tool_name == "calculate_bond_duration":
                    bond_id = params.get("bond_identifier", "")
                    if bond_id:
                        result = await self.mcp_client.calculate_bond_duration(bond_id)
                        if not state.get("bond_analytics"):
                            state["bond_analytics"] = {}
                        if bond_id not in state["bond_analytics"]:
                            state["bond_analytics"][bond_id] = {}
                        state["bond_analytics"][bond_id].update(result)
                        print(f"      Calculated duration for {bond_id}")
                # ===== BOND ANALYSIS TOOLS =====
                elif tool_name == "compare_bonds":
                    bond_ids = params.get("bond_identifiers", "")
                    if bond_ids:
                        result = await self.mcp_client.compare_bonds(bond_ids)
                        state["bond_comparisons"] = result
                        print(f"      Compared {result.get('bonds_compared', 0)} bonds")
                elif tool_name == "recommend_bonds":
                    result = await self.mcp_client.recommend_bonds(
                        target_yield=params.get("target_yield", 0.0),
                        max_risk=params.get("max_risk", "medium"),
                        investment_horizon=params.get("investment_horizon", 0.0),
                        sort_by=params.get("sort_by", "yield"),
                    )
                    result = _parse_mcp_result(result)
                    state["bond_recommendations"] = result

                    # Success:  FIX: Extract bonds and store in bonds_universe for analyst
                    if isinstance(result, dict) and "bonds" in result:
                        state["bonds_universe"] = result["bonds"]
                        print(
                            f"     Success:  Stored {len(result['bonds'])} bonds for analysis"
                        )
                    elif isinstance(result, dict) and "recommendations" in result:
                        state["bonds_universe"] = result["recommendations"]
                        print(
                            f"     Success:  Stored {len(result['recommendations'])} bonds for analysis"
                        )

                    print(
                        f"      Got {result.get('total_recommendations', 0)} recommendations"
                    )

                # ===== LEGACY TOOL NAME MAPPINGS =====
                # Map old tool names to MCP equivalents
                elif (
                    tool_name == "bond_pricer" or tool_name_normalized == "bond_pricer"
                ):
                    # bond_pricer -> price bonds from universe or use recommend_bonds with caching
                    bonds = state.get("bonds_universe", [])
                    if not bonds:
                        # If no bonds, fetch them first
                        print(f"     No bonds in universe, fetching bond list...")
                        try:
                            bonds_result = await self.mcp_client.list_bonds()
                            bonds_result = _parse_mcp_result(bonds_result)
                            bonds = self.mcp_client.to_bond_universe(bonds_result)
                            bonds = MATURITY_FILTER.filter_bonds(bonds)
                            state["bonds_universe"] = bonds[
                                :50
                            ]  # Limit to 50 for pricing
                            print(
                                f"      Fetched {len(state['bonds_universe'])} bonds for pricing"
                            )
                        except Exception as e:
                            print(f"      WARNING: Failed to fetch bonds from MCP: {e}")
                            print(
                                f"      Using empty bond universe (bond_pricer will skip)"
                            )
                            state["bonds_universe"] = []

                    # Price first 20 bonds with caching
                    bonds_to_price = (
                        state["bonds_universe"][:20] if state["bonds_universe"] else []
                    )
                    if not state.get("bond_price_forecasts"):
                        state["bond_price_forecasts"] = {}

                    cached_count = 0
                    fetched_count = 0

                    for bond in bonds_to_price:
                        bond_id = bond.get("symbol") or bond.get("isin")
                        if bond_id:
                            try:
                                # Check cache first
                                cached_price = await self.bond_cache.get_bond_price(
                                    bond_id, days_ahead=0
                                )

                                if cached_price:
                                    print(
                                        f"    Using cached price prediction (21d) for {bond_id}"
                                    )
                                    state["cache_hits"] = state.get("cache_hits", 0) + 1
                                    cached_count += 1
                                    state["bond_price_forecasts"][bond_id] = (
                                        self._transform_bond_price_forecast(
                                            cached_price, bond_id
                                        )
                                    )
                                else:
                                    # Fetch from MCP
                                    price = await self.mcp_client.get_bond_price(
                                        bond_id, days_ahead=0
                                    )
                                    price = _parse_mcp_result(price)

                                    # Cache the result
                                    await self.bond_cache.set_bond_price(
                                        bond_id, 0, price
                                    )

                                    state["bond_price_forecasts"][bond_id] = (
                                        self._transform_bond_price_forecast(
                                            price, bond_id
                                        )
                                    )
                                    state["total_tool_calls"] = (
                                        state.get("total_tool_calls", 0) + 1
                                    )
                                    fetched_count += 1
                            except Exception as e:
                                print(
                                    f"       Warning:  Failed to price {bond_id}: {e}"
                                )

                    result = {"priced_bonds": len(state["bond_price_forecasts"])}
                    print(
                        f"      Priced {len(state['bond_price_forecasts'])} bonds ({cached_count} cached, {fetched_count} fetched)"
                    )

                elif (
                    tool_name == "yield_forecaster"
                    or tool_name_normalized == "yield_forecaster"
                ):
                    # yield_forecaster -> get_all_yield_forecasts
                    result = await self.mcp_client.get_all_yield_forecasts()
                    result = _parse_mcp_result(result)
                    state["yield_forecasts"] = result
                    print(
                        f"DEBUG  Stored yield forecasts: {list(result.keys()) if isinstance(result, dict) else type(result)}"
                    )
                    print(f"      Got forecasts for {len(result)} maturities")

                # ===== LOCAL/NON-MCP TOOLS =====
                elif tool_name in ["get_user_portfolio", "portfolio_manager"]:
                    # Get portfolio from MongoDB using portfolio tool with caching
                    user_id = params.get("user_id", state.get("user_id", ""))
                    # Check if portfolio is already in state (cached from previous step)
                    existing_portfolio = state.get("portfolio")
                    if existing_portfolio and user_id:
                        # Check if it's the same user's portfolio
                        portfolio_user_id = getattr(
                            existing_portfolio, "user_id", None
                        ) or getattr(existing_portfolio, "portfolio_id", None)
                        if portfolio_user_id == user_id or (
                            not portfolio_user_id and user_id
                        ):
                            print(
                                f"      Using cached portfolio from state (user: {user_id})"
                            )
                            state["cache_hits"] = state.get("cache_hits", 0) + 1
                            result = {
                                "user_id": user_id,
                                "portfolio_id": getattr(
                                    existing_portfolio, "portfolio_id", ""
                                ),
                                "total_value": getattr(
                                    existing_portfolio, "total_value", 0.0
                                ),
                                "cash": getattr(existing_portfolio, "cash", 0.0),
                                "num_holdings": len(
                                    getattr(existing_portfolio, "holdings", [])
                                    or getattr(existing_portfolio, "positions", [])
                                ),
                                "cached": True,
                                "source": "state_cache",
                            }
                        else:
                            # Different user, need to fetch
                            existing_portfolio = None

                    if not existing_portfolio:
                        portfolio_tool = self.tools.get(ToolType.PORTFOLIO_MANAGER)

                        if not portfolio_tool:
                            print(f"     Error:  Portfolio tool not available")
                            result = {"error": "Portfolio tool not available"}
                        elif not user_id:
                            print(
                                f"     Error:  No user_id provided for portfolio query"
                            )
                            result = {"error": "No user_id provided"}
                        else:
                            print(f"      Fetching portfolio for user: {user_id}")
                            portfolio_result = await portfolio_tool.get_portfolio(
                                user_id
                            )

                            if portfolio_result.success and portfolio_result.data:
                                # Store portfolio in state for caching
                                state["portfolio"] = portfolio_result.data

                                # Check if result was cached by the tool
                                is_cached = getattr(portfolio_result, "cached", False)

                                result = {
                                    "user_id": user_id,
                                    "portfolio_id": portfolio_result.data.portfolio_id,
                                    "total_value": portfolio_result.data.total_value,
                                    "cash": portfolio_result.data.cash,
                                    "num_holdings": len(portfolio_result.data.holdings),
                                    "holdings": [
                                        {
                                            "isin": h.isin,
                                            "bond_name": h.bond_name,
                                            "quantity": h.quantity,
                                            "current_price": h.current_price,
                                            "market_value": h.market_value,
                                            "weight": h.weight,
                                            "unrealized_pnl": h.unrealized_pnl,
                                        }
                                        for h in portfolio_result.data.holdings
                                    ],
                                    "cached": is_cached,
                                    "source": "mongodb"
                                    if not is_cached
                                    else "file_cache",
                                }
                                print(
                                    f"      Found portfolio with {len(portfolio_result.data.holdings)} holdings (cached: {is_cached})"
                                )
                            else:
                                error_msg = (
                                    portfolio_result.error
                                    if portfolio_result.error
                                    else "Portfolio not found"
                                )
                                print(f"     Warning:  {error_msg}")
                                result = {"error": error_msg, "user_id": user_id}
                                state["total_tool_calls"] = (
                                    state.get("total_tool_calls", 0) + 1
                                )

                elif tool_name in ["scrape_news", "news_scraper"]:
                    # Success:  News scraping is handled by real-time info agent in _gather_realtime_info
                    # Check if we already have news articles from real-time info gathering
                    news_articles = state.get("news_articles", [])
                    tool_result = state.get("tool_results", {}).get(
                        ToolType.NEWS_SCRAPER
                    )

                    if news_articles:
                        print(
                            f"      Using {len(news_articles)} news articles from real-time info agent"
                        )
                        result = {
                            "articles": len(news_articles),
                            "source": "realtime_info_agent",
                            "cached": False,
                        }
                    elif tool_result and tool_result.success and tool_result.data:
                        print(
                            f"      Using {len(tool_result.data)} news articles from real-time info agent"
                        )
                        result = {
                            "articles": len(tool_result.data),
                            "source": "realtime_info_agent",
                            "cached": tool_result.cached,
                        }
                    else:
                        print(
                            f"     Info:   News scraping handled by real-time info agent (already executed or will be executed)"
                        )
                        result = {
                            "articles": 0,
                            "source": "realtime_info_agent",
                            "note": "Handled by real-time info agent",
                        }

                elif tool_name == "web_search":
                    # Success:  Web search is handled by real-time info agent in _gather_realtime_info
                    # Check if we already have web search results from real-time info gathering
                    web_search_formatted = state.get(
                        "web_search_results"
                    )  # This is the formatted context
                    tool_result = state.get("tool_results", {}).get(ToolType.WEB_SEARCH)

                    if web_search_formatted:
                        print(
                            f"      Using web search results from real-time info agent"
                        )
                        result = {
                            "results": 1,
                            "source": "realtime_info_agent",
                            "formatted": True,
                            "cached": False,
                        }
                    elif tool_result and tool_result.success and tool_result.data:
                        print(
                            f"      Using {len(tool_result.data)} web search results from real-time info agent"
                        )
                        result = {
                            "results": len(tool_result.data),
                            "source": "realtime_info_agent",
                            "cached": tool_result.cached,
                        }
                    else:
                        print(
                            f"     Info:   Web search handled by real-time info agent (already executed or will be executed)"
                        )
                        result = {
                            "results": 0,
                            "source": "realtime_info_agent",
                            "note": "Handled by real-time info agent",
                        }

                else:
                    print(f"     Warning:  Unknown tool: {tool_name}")

                # Store result in tool_results
                # Extract cached flag from result if present
                is_cached = (
                    result.get("cached", False) if isinstance(result, dict) else False
                )

                state["tool_results"][tool_name] = ToolResult(
                    tool_type=tool_name, success=True, data=result, cached=is_cached
                )

                # Track tool call (only count non-cached calls)
                if not is_cached:
                    state["total_tool_calls"] = state.get("total_tool_calls", 0) + 1
                else:
                    state["cache_hits"] = state.get("cache_hits", 0) + 1
            except Exception as e:
                error_msg = f"Tool '{tool_name}' failed: {str(e)}"
                logger.error(f"     Error:  {error_msg}", exc_info=True)
                StateHelper.ensure_list(state, "errors").append(error_msg)
                StateHelper.ensure_dict(state, "tool_results")[tool_name] = ToolResult(
                    tool_type=tool_name, success=False, data=None, error=str(e)
                )

        # total_tool_calls is now tracked per-tool (incremented above)
        # Only count non-cached tool calls
        total_executed = state.get("total_tool_calls", 0)
        cache_hits = state.get("cache_hits", 0)
        logger.info(
            f" Tools completed: {total_executed} executed, {cache_hits} cache hits"
        )

        # Success:  FALLBACK: If comparison query but compare_bonds wasn't called, do manual comparison
        query_lower = state.get("user_query", "").lower()
        is_comparison_query = any(
            phrase in query_lower
            for phrase in [
                "compare",
                "comparison",
                "vs",
                "versus",
                "difference between",
                "which is better",
                "which bond is better",
                "compare bonds",
                "comparing",
                "side by side",
            ]
        )

        if is_comparison_query and not state.get("bond_comparisons"):
            # Check if compare_bonds tool was called
            compare_result = state.get("tool_results", {}).get("compare_bonds")
            if not compare_result or not compare_result.success:
                # Fallback: Extract bond identifiers and compare manually
                import re

                bond_identifiers = []

                # Extract ISINs
                isin_pattern = r"\b(IN[E0][A-Z0-9]{9,10})\b"
                isins = re.findall(isin_pattern, query_lower.upper())
                bond_identifiers.extend(isins)

                # Extract bond symbols
                symbol_pattern = r"\b(\d{3}[A-Z]{2}\d{4})\b"
                symbols = re.findall(symbol_pattern, query_lower.upper())
                bond_identifiers.extend(symbols)

                # Extract from classified query entities
                classified = state.get("classified_query")
                if classified:
                    entities = getattr(classified, "entities", [])
                    for entity in entities:
                        if isinstance(entity, str):
                            entity_upper = entity.upper()
                            if re.match(
                                r"^IN[E0][A-Z0-9]{9,10}$", entity_upper
                            ) or re.match(r"^\d{3}[A-Z]{2}\d{4}$", entity_upper):
                                if entity_upper not in bond_identifiers:
                                    bond_identifiers.append(entity_upper)

                # Remove duplicates
                bond_identifiers = list(dict.fromkeys(bond_identifiers))

                if len(bond_identifiers) >= 2:
                    print(
                        f"     Fallback:  Comparison query detected, comparing {len(bond_identifiers)} bonds manually"
                    )
                    try:
                        # Use compare_bonds tool directly
                        result = await self.mcp_client.compare_bonds(
                            ",".join(bond_identifiers[:10])
                        )
                        result = _parse_mcp_result(result)
                        state["bond_comparisons"] = result
                        print(
                            f"      Compared {result.get('bonds_compared', 0)} bonds (fallback)"
                        )
                    except Exception as e:
                        print(f"      Warning:  Fallback comparison failed: {e}")
                        # Try getting individual bond details as last resort
                        if len(bond_identifiers) == 2:
                            try:
                                bond1_details = await self.mcp_client.get_bond_details(
                                    bond_identifiers[0]
                                )
                                bond2_details = await self.mcp_client.get_bond_details(
                                    bond_identifiers[1]
                                )
                                bond1_details = _parse_mcp_result(bond1_details)
                                bond2_details = _parse_mcp_result(bond2_details)

                                # Create manual comparison
                                state["bond_comparisons"] = {
                                    "comparison_date": datetime.now().isoformat(),
                                    "bonds_compared": 2,
                                    "bonds": [bond1_details, bond2_details],
                                    "source": "manual_fallback",
                                }
                                print(f"      Created manual comparison for 2 bonds")
                            except Exception as e2:
                                print(
                                    f"      Error:  Manual comparison also failed: {e2}"
                                )
                elif len(bond_identifiers) == 1:
                    print(
                        f"     Info:   Only 1 bond identifier found in comparison query, getting details"
                    )
                    try:
                        bond_details = await self.mcp_client.get_bond_details(
                            bond_identifiers[0]
                        )
                        bond_details = _parse_mcp_result(bond_details)
                        if not state.get("bond_details"):
                            state["bond_details"] = {}
                        state["bond_details"][bond_identifiers[0]] = bond_details
                    except Exception as e:
                        print(f"      Warning:  Could not get bond details: {e}")
                else:
                    print(
                        f"     Warning:  Comparison query detected but no bond identifiers found"
                    )

        # Success:  NEW: Lightweight re-evaluation of agent needs based on actual tool results
        state = self._re_evaluate_agent_needs(state)

        state["execution_path"].append("execute_tools")
        return state

    def _re_evaluate_agent_needs(self, state: GraphState) -> GraphState:
        """
        Lightweight re-evaluation: Adjust agent plan based on actual tool results.
        This prevents agents from running when prerequisites are missing.
        No bottlenecks - just dict/list checks.
        """
        plan = state.get("execution_plan")
        if not plan:
            return state
        # Check what we actually got from tools
        bonds = state.get("bonds_universe", [])
        yield_curve = state.get("yield_curve")
        yield_forecasts = state.get("yield_forecasts")
        analytics = state.get("bond_analytics", {})

        # Track if we made changes
        changes_made = []

        # If ML was planned but we don't have bonds, remove it
        if AgentType.ML_MODEL in plan.agents_needed:
            if not bonds or len(bonds) == 0:
                plan.agents_needed = [
                    a for a in plan.agents_needed if a != AgentType.ML_MODEL
                ]
                changes_made.append("removed ML (no bonds)")
            elif not yield_forecasts:
                # ML can work without forecasts, but it's less optimal
                logger.warning(
                    "  Warning:   ML will proceed without yield forecasts (using current yields)"
                )

        # If analyst was planned but no bonds, remove it
        if AgentType.ANALYST in plan.agents_needed:
            if not bonds or len(bonds) == 0:
                plan.agents_needed = [
                    a for a in plan.agents_needed if a != AgentType.ANALYST
                ]
                changes_made.append("removed analyst (no bonds)")

        # If scoring was planned but no analytics, remove it
        if AgentType.SCORING in plan.agents_needed:
            if not analytics or len(analytics) == 0:
                plan.agents_needed = [
                    a for a in plan.agents_needed if a != AgentType.SCORING
                ]
                changes_made.append("removed scoring (no analytics)")

        # If we have bonds but no analyst planned, check if we should add it
        if bonds and len(bonds) > 0 and AgentType.ANALYST not in plan.agents_needed:
            # Only add if query type suggests analysis would be useful
            classified = state.get("classified_query")
            if classified:
                intent = getattr(classified, "intent", None)
                if intent:
                    intent_str = (
                        intent.value if hasattr(intent, "value") else str(intent)
                    )
                    if intent_str in [
                        "buy_recommendation",
                        "credit_analysis",
                        "forecast_prices",
                    ]:
                        plan.agents_needed.append(AgentType.ANALYST)
                        changes_made.append(
                            "added analyst (bonds available and query needs analysis)"
                        )

        # If we have analytics but no scoring, check if we should add it
        if (
            analytics
            and len(analytics) > 0
            and AgentType.SCORING not in plan.agents_needed
        ):
            classified = state.get("classified_query")
            if classified:
                intent = getattr(classified, "intent", None)
                if intent:
                    intent_str = (
                        intent.value if hasattr(intent, "value") else str(intent)
                    )
                    if intent_str in ["buy_recommendation", "sell_recommendation"]:
                        plan.agents_needed.append(AgentType.SCORING)
                        changes_made.append(
                            "added scoring (analytics available and query needs recommendations)"
                        )

        if changes_made:
            logger.info(f"  Re-evaluated agent needs: {', '.join(changes_made)}")
            state["execution_plan"] = plan

        return state

    def _optimize_tool_parameters(
        self, tool_call: Any, state: GraphState
    ) -> Optional[Any]:
        """
        Optimize tool parameters based on current state.
        Returns None if tool should be skipped, otherwise returns optimized tool_call.
        Lightweight - just dict/list operations.
        """
        tool_name = (
            tool_call.tool_type.value
            if hasattr(tool_call.tool_type, "value")
            else str(tool_call.tool_type)
        )
        params = tool_call.parameters.copy() if tool_call.parameters else {}

        # Skip if data already available (avoid redundant calls)
        if tool_name in ["get_latest_yields", "get_current_yields"]:
            if state.get("yield_curve") or state.get("latest_yields_display"):
                logger.debug(
                    f"     Skipping {tool_name} (yield data already available)"
                )
                return None

        if tool_name in ["get_all_yield_forecasts", "yield_forecaster"]:
            if state.get("yield_forecasts"):
                logger.debug(
                    f"       Skipping {tool_name} (forecasts already available)"
                )
                return None

        # Optimize bond fetching based on what we already have
        if tool_name in ["fetch_bond_universe", "list_bonds"]:
            existing_bonds = state.get("bonds_universe", [])
            if existing_bonds:
                # Adjust limit to avoid fetching duplicates
                requested_limit = params.get("limit", 50)
                if requested_limit > len(existing_bonds):
                    # Only fetch what we need
                    params["limit"] = max(20, requested_limit - len(existing_bonds))
                    logger.debug(
                        f"     Optimized {tool_name} limit: {requested_limit} → {params['limit']} (already have {len(existing_bonds)})"
                    )
                else:
                    # We already have enough bonds
                    logger.debug(
                        f"       Skipping {tool_name} (already have {len(existing_bonds)} bonds, need {requested_limit})"
                    )
                    return None

        # Optimize news scraping based on query complexity
        if tool_name == "news_scraper":
            # Check if we already have news from real-time info agent
            if state.get("news_articles") or state.get("tool_results", {}).get(
                ToolType.NEWS_SCRAPER
            ):
                logger.debug(
                    f"       Skipping {tool_name} (news already gathered by real-time info agent)"
                )
                return None

            # Adjust article count based on query
            query = state.get("user_query", "")
            if len(query.split()) > 15:  # Complex query
                params["max_articles"] = max(params.get("max_articles", 5), 10)
            else:
                params["max_articles"] = min(params.get("max_articles", 5), 3)

        # Update tool_call with optimized parameters
        tool_call.parameters = params
        return tool_call

    def _should_run_ml(self, state: GraphState) -> str:
        """Conditional: Should we run ML model? (State-aware)"""
        plan = state.get("execution_plan")

        # Check if plan explicitly says no agents needed
        if plan and not plan.agents_needed:
            logger.debug("  Info:   Skipping ML (no agents in plan)")
            return "no"
        # Check if ML agent is in the plan
        if plan and AgentType.ML_MODEL in plan.agents_needed:
            # Success:  OPTIMIZATION: Skip ML for informational queries (no recommendations needed)
            classified = state.get("classified_query")
            if classified:
                intent = getattr(classified, "intent", None)
                if intent:
                    intent_str = (
                        intent.value if hasattr(intent, "value") else str(intent)
                    )
                    # ML is only useful for recommendations, not informational queries
                    if intent_str not in [
                        "buy_recommendation",
                        "sell_recommendation",
                        "switch_bonds",
                        "increase_yield",
                        "reduce_duration",
                    ]:
                        print(
                            f"  Info:   Skipping ML (not needed for informational query: {intent_str})"
                        )
                        return "no"

            # Success:  STATE-AWARE: Validate prerequisites before running
            bonds = state.get("bonds_universe", [])
            yield_forecasts = state.get("yield_forecasts")

            if not bonds or len(bonds) == 0:
                logger.warning(
                    "  Warning:   ML needs bonds but none available - skipping"
                )
                return "no"

            # ML can work without forecasts (uses current yields), but warn
            if not yield_forecasts:
                logger.warning(
                    "  Warning:   ML will use current yields (no forecasts available)"
                )

            return "yes"

        return "no"

    def _should_run_analyst(self, state: GraphState) -> str:
        """Conditional: Should we run analyst? (State-aware)"""
        plan = state.get("execution_plan")

        if plan and not plan.agents_needed:
            return "no"

        if plan and AgentType.ANALYST in plan.agents_needed:
            # Success:  OPTIMIZATION: Skip analyst for informational queries (no recommendations needed)
            classified = state.get("classified_query")
            if classified:
                intent = getattr(classified, "intent", None)
                if intent:
                    intent_str = (
                        intent.value if hasattr(intent, "value") else str(intent)
                    )
                    # Analyst is only useful for recommendations, not informational queries
                    if intent_str not in [
                        "buy_recommendation",
                        "sell_recommendation",
                        "switch_bonds",
                        "increase_yield",
                        "reduce_duration",
                    ]:
                        print(
                            f"  Info:   Skipping analyst (not needed for informational query: {intent_str})"
                        )
                        return "no"

            # Success:  STATE-AWARE: Validate prerequisites
            bonds = state.get("bonds_universe", [])

            if not bonds or len(bonds) == 0:
                logger.warning(
                    "  Warning:   Analyst needs bonds but none available - skipping"
                )
                return "no"

            # Analyst can work without yield curve (uses defaults), but warn
            yield_curve = state.get("yield_curve")
            if not yield_curve:
                print(
                    "  Warning:   Analyst will use default yield curve (no live data)"
                )

            return "yes"

        return "no"

    def _should_run_scoring(self, state: GraphState) -> str:
        """Conditional: Should we run scoring? (State-aware)"""
        plan = state.get("execution_plan")

        if plan and not plan.agents_needed:
            return "no"

        if plan and AgentType.SCORING in plan.agents_needed:
            # Success:  STATE-AWARE: Scoring needs analytics from analyst
            analytics = state.get("bond_analytics", {})

            if not analytics or len(analytics) == 0:
                print(
                    "  Warning:   Scoring needs analytics but none available - skipping"
                )
                return "no"

            # Success:  OPTIMIZATION: Check if scoring is actually needed for this query type
            classified = state.get("classified_query")
            if classified:
                intent = getattr(classified, "intent", None)
                if intent:
                    intent_str = (
                        intent.value if hasattr(intent, "value") else str(intent)
                    )
                    # Scoring is only useful for recommendations
                    if intent_str not in [
                        "buy_recommendation",
                        "sell_recommendation",
                        "switch_bonds",
                        "increase_yield",
                        "reduce_duration",
                    ]:
                        print(
                            f"  Info:   Skipping scoring (not needed for {intent_str})"
                        )
                        return "no"

            return "yes"

        return "no"

    async def _run_ml_model(self, state: GraphState) -> GraphState:
        """Run ML model with Real Forecasts"""
        AgentLogger.print_agent_header("ML Model Agent", "RUNNING")
        state["current_step"] = "ml_model"
        # SKIP if no agents were requested in plan
        plan = state.get("execution_plan")
        if plan and not plan.agents_needed:
            AgentLogger.print_info("Skipping ML (no agents in plan)", "ML Model Agent")
            state["execution_path"].append("run_ml_model")
            return state
        try:
            # 1. Get filtered bonds
            all_bonds = state.get("bonds_universe")
            if not all_bonds:
                AgentLogger.print_warning(
                    "No bonds found in state (Planner did not fetch universe?)",
                    "ML Model Agent",
                )
                return state

            filtered_bonds = self._filter_bonds_by_query(all_bonds, state)

            AgentLogger.print_step(
                f"Processing {len(filtered_bonds)} filtered bonds", "running"
            )

            # 2. Strict Data Injection
            # We pass BOTH current curve (for reference) and future forecasts (for prediction)
            state["ml_predictions"] = await self.ml_agent.predict_batch(
                bonds=filtered_bonds,
                yield_curve=state.get("yield_curve"),  # Current Rates
                yield_forecasts=state.get("yield_forecasts"),  # Future Rates (CRITICAL)
                rbi_policy=self._extract_rbi_from_rag(state),
                news_items=[
                    a.dict() if hasattr(a, "dict") else a
                    for a in state.get("news_articles", [])
                ],
            )

            AgentLogger.print_agent_result(
                "ML Model Agent",
                {
                    "predictions_count": len(state["ml_predictions"]),
                    "bonds_analyzed": len(filtered_bonds),
                    "yield_forecasts_used": state.get("yield_forecasts") is not None,
                },
                f"Generated {len(state['ml_predictions'])} ML predictions",
            )

        except Exception as e:
            AgentLogger.print_error(f"ML model error: {e}", "ML Model Agent")
            state["errors"].append(f"ML model error: {str(e)}")

        state["execution_path"].append("run_ml_model")
        return state

    def _run_analyst(self, state: GraphState) -> GraphState:
        """Run analyst with Real Yield Curve"""
        AgentLogger.print_agent_header("Analyst Agent", "RUNNING")
        state["current_step"] = "analyst"
        # SKIP if not in plan
        plan = state.get("execution_plan")
        if plan and AgentType.ANALYST not in plan.agents_needed:
            AgentLogger.print_info("Skipping Analyst (not in plan)", "Analyst Agent")
            state["execution_path"].append("run_analyst_skipped")
            return state

        try:
            bonds = state.get("bonds_universe")
            if not bonds:
                AgentLogger.print_warning(
                    "No bonds available for analysis", "Analyst Agent"
                )
                return state

            # Get yield curve from state (will be populated by get_latest_yields tool)
            yield_curve = state.get("yield_curve")

            if not yield_curve:
                AgentLogger.print_warning(
                    "No Live Yield Curve available. Valuation will be limited.",
                    "Analyst Agent",
                )

            AgentLogger.print_step(f"Analyzing {len(bonds)} bonds", "running")

            state["bond_analytics"] = self.analyst.analyze_bonds(
                bonds,
                ml_predictions=state.get("ml_predictions", {}),
                credit_data=state.get("credit_ratings", {}),
                yield_curve=yield_curve,  # Passed directly
            )

            # Show sample analytics
            if state["bond_analytics"]:
                sample_analytics = list(state["bond_analytics"].items())[0][1]
                AgentLogger.print_agent_result(
                    "Analyst Agent",
                    {
                        "bonds_analyzed": len(state["bond_analytics"]),
                        "sample_bond": getattr(sample_analytics, "name", "N/A"),
                        "sample_fair_value": f"₹{getattr(sample_analytics, 'fair_value', 0):.2f}",
                        "sample_ytm": f"{getattr(sample_analytics, 'ytm', 0):.1%}",
                    },
                    f"Generated analytics for {len(state['bond_analytics'])} bonds",
                )

        except Exception as e:
            AgentLogger.print_error(f"Analyst error: {e}", "Analyst Agent")
            state["errors"].append(f"Analyst error: {str(e)}")

        state["execution_path"].append("run_analyst")
        return state

    def _run_scoring(self, state: GraphState) -> GraphState:
        """Run scoring"""
        AgentLogger.print_agent_header("Scoring Agent", "RUNNING")
        state["current_step"] = "scoring"
        # SKIP if not in plan
        plan = state.get("execution_plan")
        if plan and AgentType.SCORING not in plan.agents_needed:
            AgentLogger.print_info("Skipping Scoring (not in plan)", "Scoring Agent")
            state["execution_path"].append("run_scoring_skipped")
            return state

        try:
            bond_analytics = state.get("bond_analytics", {})
            if not bond_analytics:
                AgentLogger.print_warning(
                    "No bond analytics available for scoring", "Scoring Agent"
                )
                return state

            AgentLogger.print_step(f"Scoring {len(bond_analytics)} bonds", "running")

            state["bond_scores"] = self.scoring.score_bonds(bond_analytics)

            # Show top scores
            if state["bond_scores"]:
                top_scores = sorted(
                    state["bond_scores"].items(),
                    key=lambda x: getattr(x[1], "total_score", 0),
                    reverse=True,
                )[:3]
                AgentLogger.print_agent_result(
                    "Scoring Agent",
                    {
                        "bonds_scored": len(state["bond_scores"]),
                        "top_bonds": [
                            f"{getattr(s[1], 'name', 'N/A')} (Score: {getattr(s[1], 'total_score', 0):.2f})"
                            for s in top_scores
                        ],
                    },
                    f"Scored {len(state['bond_scores'])} bonds",
                )
        except Exception as e:
            AgentLogger.print_error(f"Scoring error: {e}", "Scoring Agent")
            state["errors"].append(f"Scoring error: {str(e)}")

        state["execution_path"].append("run_scoring")
        return state

    def _run_response(self, state: GraphState) -> GraphState:
        """Run response agent (handles analytics, informational, and advisory queries)"""
        AgentLogger.print_agent_header("Response Agent", "GENERATING")
        state["current_step"] = "response"

        try:
            classified = state.get("classified_query")
            plan = state.get("execution_plan")

            # Check if this is an info-only query (no agents needed)
            if plan and not plan.agents_needed:
                print(
                    "  Info:   Info-only query - generating direct response from tool results"
                )

                summary_parts = []
                tool_results = state.get("tool_results", {})

                # Success:  NEW: Handle bond listing without analysis
                bonds = state.get("bonds_universe", [])
                if bonds and len(bonds) > 0:
                    summary_parts.append(f"**Found {len(bonds)} bonds:**\n")

                    # Sort by maturity date
                    sorted_bonds = sorted(
                        bonds, key=lambda b: b.get("maturity_date", "9999-12-31")
                    )

                    for i, bond in enumerate(sorted_bonds[:10], 1):  # Show top 10
                        name = bond.get("name", "Unknown")
                        symbol = bond.get("symbol", bond.get("isin", "N/A"))
                        coupon = bond.get("coupon_rate", 0)
                        maturity = bond.get("maturity_date", "N/A")
                        ytm = bond.get("ytm", 0)

                        # Convert to decimal if needed
                        if ytm > 1:
                            ytm = ytm / 100.0
                        if coupon > 1:
                            coupon = coupon / 100.0

                        summary_parts.append(f"\n**{i}. {name}**")
                        summary_parts.append(f"   Symbol: {symbol}")
                        summary_parts.append(f"   Coupon: {coupon * 100}%")
                        summary_parts.append(f"   YTM: {ytm * 100}%")
                        summary_parts.append(f"   Maturity: {maturity}")

                    if len(bonds) > 10:
                        summary_parts.append(f"\n*...and {len(bonds) - 10} more bonds*")

                    summary_parts.append("\n---")
                    summary_parts.append(
                        "\n*Need recommendations? Ask me to 'recommend bonds' or 'suggest best bonds'*"
                    )

                # Add yield curve data if present
                elif state.get("yield_curve") or tool_results.get("get_latest_yields"):
                    yield_result = tool_results.get(
                        "get_latest_yields"
                    ) or tool_results.get("get_current_yields")
                    if yield_result and yield_result.success and yield_result.data:
                        summary_parts.append("**Current Government Bond Yields:**\n")
                        yield_data = yield_result.data

                        # Success:  FIX: MCP returns {"yields": {}, "last_update": "..."}
                        # Extract the yields dict if it's wrapped
                        if isinstance(yield_data, dict) and "yields" in yield_data:
                            yields_dict = yield_data["yields"]
                        else:
                            yields_dict = yield_data
                        for maturity, rate in sorted(yields_dict.items()):
                            # Success:  Don't multiply by 100 - values are already percentages
                            summary_parts.append(f"  • {maturity}: {rate:.3f}%")
                        summary_parts.append("")
                    # Try state fallback
                    elif state.get("latest_yields_display"):
                        # Use raw display yields (already percentages)
                        summary_parts.append("**Current Government Bond Yields:**\n")
                        yields_dict = state["latest_yields_display"]

                        for maturity, rate in sorted(yields_dict.items()):
                            summary_parts.append(f"  • {maturity}: {rate:.3f}%")
                        summary_parts.append("")

                    elif state.get("yield_curve"):
                        # Fallback to yield_curve (decimals) - multiply by 100
                        summary_parts.append("**Current Government Bond Yields:**\n")
                        yield_curve_data = state["yield_curve"]

                        for maturity, rate in sorted(yield_curve_data.items()):
                            # Multiply by 100 since these are decimals
                            summary_parts.append(f"  • {maturity}: {rate * 100:.3f}%")
                        summary_parts.append("")

                forecast_result = tool_results.get(
                    "forecast_all_yields"
                ) or tool_results.get("get_all_yield_forecasts")
                if forecast_result and forecast_result.success and forecast_result.data:
                    summary_parts.append("**Yield Forecasts (21-day ahead):**\n")
                    forecasts_dict = forecast_result.data

                    # Get current yields for comparison
                    current_yields = state.get("latest_yields_display") or state.get(
                        "yield_curve", {}
                    )

                    if isinstance(forecasts_dict, dict):
                        for maturity, forecasts in sorted(forecasts_dict.items()):
                            if (
                                forecasts
                                and isinstance(forecasts, list)
                                and len(forecasts) > 0
                            ):
                                # Success:  FIX: Always get day 21 (or closest available)
                                day_21_forecast = None
                                max_day = 0

                                for fc in forecasts:
                                    day_num = (
                                        fc.get("day", 0) if isinstance(fc, dict) else 0
                                    )
                                    if day_num > max_day:
                                        max_day = day_num
                                        day_21_forecast = fc

                                if day_21_forecast:
                                    forecast_val = (
                                        day_21_forecast.get("predicted_yield", 0)
                                        if isinstance(day_21_forecast, dict)
                                        else 0
                                    )
                                    days_ahead = (
                                        day_21_forecast.get("day", 0)
                                        if isinstance(day_21_forecast, dict)
                                        else 0
                                    )

                                    # Convert to decimal if needed
                                    if forecast_val > 1:
                                        forecast_val = forecast_val / 100.0

                                    # Get current yield for this maturity
                                    current_yield = None
                                    if current_yields:
                                        current_yield = (
                                            current_yields.get(float(maturity))
                                            or current_yields.get(int(maturity))
                                            or current_yields.get(maturity)
                                        )

                                        # If yield_curve (decimals), already decimal
                                        # If latest_yields_display (percentages), convert
                                        if current_yield and current_yield > 1:
                                            current_yield = current_yield / 100.0
                                    # Calculate change
                                    if current_yield:
                                        change = forecast_val - current_yield
                                        change_bps = change * 10000  # Basis points
                                        direction = (
                                            ""
                                            if change > 0
                                            else ""
                                            if change < 0
                                            else ""
                                        )

                                        summary_parts.append(
                                            f"  • {maturity}Y: {forecast_val * 100:.3f}% "
                                            f"(currently {current_yield * 100:.3f}%, "
                                            f"{direction} {change_bps:+.1f} bps change)"
                                        )
                                    else:
                                        summary_parts.append(
                                            f"  • {maturity}Y: {forecast_val * 100:.3f}% "
                                            f"(forecast for day +{days_ahead})"
                                        )
                    summary_parts.append("")

                # Success:  NEW: Handle bond comparisons
                bond_comparisons = state.get("bond_comparisons")
                if bond_comparisons:
                    summary_parts.append("**Bond Comparison:**\n")
                    if isinstance(bond_comparisons, dict):
                        bonds = bond_comparisons.get("bonds", [])
                        comparison_date = bond_comparisons.get("comparison_date", "N/A")
                        summary_parts.append(f"Comparison Date: {comparison_date}\n")
                        for i, bond in enumerate(bonds, 1):
                            symbol = bond.get("symbol", "N/A")
                            name = bond.get("name", "Unknown")
                            coupon = bond.get("coupon_rate", 0)
                            ytm = bond.get("ytm_percent", bond.get("ytm", 0))
                            price = bond.get("price", 0)
                            duration = bond.get(
                                "duration", bond.get("modified_duration", 0)
                            )
                            convexity = bond.get("convexity", 0)

                            # Convert to percentage if needed
                            if coupon > 1:
                                coupon = coupon / 100.0
                            if ytm > 1:
                                ytm = ytm / 100.0

                            summary_parts.append(f"\n**{i}. {name} ({symbol})**")
                            summary_parts.append(f"   Coupon Rate: {coupon * 100:.2f}%")
                            summary_parts.append(f"   YTM: {ytm * 100:.3f}%")
                            summary_parts.append(f"   Price: ₹{price:.2f}")
                            summary_parts.append(f"   Duration: {duration:.3f} years")
                            summary_parts.append(f"   Convexity: {convexity:.3f}")
                        summary_parts.append("")

                # Success:  FIX: Add specific yield forecasts (for single maturity queries)
                specific_forecasts = state.get("specific_forecasts")
                if (
                    specific_forecasts
                    and isinstance(specific_forecasts, list)
                    and len(specific_forecasts) > 0
                ):
                    print(
                        f"\n   Found {len(specific_forecasts)} specific forecast(s) to display"
                    )
                    summary_parts.append("**Yield Forecasts:**\n")

                    # Get current yields for comparison
                    current_yields = state.get("latest_yields_display") or state.get(
                        "yield_curve", {}
                    )

                    for forecast_item in specific_forecasts:
                        maturity = forecast_item.get("maturity", "Unknown")
                        forecasts = forecast_item.get("forecasts", [])

                        print(
                            f"   Processing forecast for {maturity}Y maturity: {len(forecasts)} data points"
                        )

                        if (
                            forecasts
                            and isinstance(forecasts, list)
                            and len(forecasts) > 0
                        ):
                            summary_parts.append(
                                f"\n**{maturity}-Year Government Bond Yield Forecast:**\n"
                            )

                            # Get current yield for comparison
                            current_yield = None
                            if current_yields:
                                current_yield = (
                                    current_yields.get(float(maturity))
                                    or current_yields.get(int(maturity))
                                    or current_yields.get(maturity)
                                )
                                if current_yield and current_yield > 1:
                                    current_yield = current_yield / 100.0

                            # Show first 3, last 3 with ellipsis
                            if len(forecasts) <= 5:
                                for fc in forecasts:
                                    day = fc.get("day", 0)
                                    date = fc.get("date", "N/A")
                                    pred_yield = fc.get("predicted_yield", 0)
                                    if pred_yield > 1:
                                        pred_yield = pred_yield / 100.0
                                    summary_parts.append(
                                        f"  • Day {day} ({date}): {pred_yield * 100:.3f}%"
                                    )
                            else:
                                # First 3
                                for fc in forecasts[:3]:
                                    day = fc.get("day", 0)
                                    date = fc.get("date", "N/A")
                                    pred_yield = fc.get("predicted_yield", 0)
                                    if pred_yield > 1:
                                        pred_yield = pred_yield / 100.0
                                    summary_parts.append(
                                        f"  • Day {day} ({date}): {pred_yield * 100:.3f}%"
                                    )

                                summary_parts.append(
                                    f"  • ... ({len(forecasts) - 6} more days) ..."
                                )

                                # Last 3
                                for fc in forecasts[-3:]:
                                    day = fc.get("day", 0)
                                    date = fc.get("date", "N/A")
                                    pred_yield = fc.get("predicted_yield", 0)
                                    if pred_yield > 1:
                                        pred_yield = pred_yield / 100.0
                                    summary_parts.append(
                                        f"  • Day {day} ({date}): {pred_yield * 100:.3f}%"
                                    )

                            # Summary stats
                            if len(forecasts) >= 2:
                                first_yield = forecasts[0].get("predicted_yield", 0)
                                last_yield = forecasts[-1].get("predicted_yield", 0)

                                if first_yield > 1:
                                    first_yield = first_yield / 100.0
                                if last_yield > 1:
                                    last_yield = last_yield / 100.0

                                change_from_forecast_start = last_yield - first_yield
                                change_pct = (
                                    (change_from_forecast_start / first_yield * 100)
                                    if first_yield != 0
                                    else 0
                                )

                                summary_parts.append(f"\n**Forecast Summary:**")

                                # Change from current yield (if available)
                                if current_yield:
                                    change_from_current = last_yield - current_yield
                                    change_bps = change_from_current * 10000
                                    direction = (
                                        ""
                                        if change_from_current > 0
                                        else ""
                                        if change_from_current < 0
                                        else ""
                                    )

                                    summary_parts.append(
                                        f"  Current yield: {current_yield * 100:.3f}%"
                                    )
                                    summary_parts.append(
                                        f"  Forecast (Day 21): {last_yield * 100:.3f}%"
                                    )
                                    summary_parts.append(
                                        f"  {direction} Change from current: {change_bps:+.1f} bps ({change_from_current * 100:+.3f}%)"
                                    )
                                else:
                                    direction = (
                                        ""
                                        if change_from_forecast_start > 0
                                        else ""
                                        if change_from_forecast_start < 0
                                        else ""
                                    )
                                    summary_parts.append(
                                        f"  {direction} Change over 21 days: {change_from_forecast_start * 100:+.3f}% ({change_pct:+.2f}% relative)"
                                    )
                                    summary_parts.append(
                                        f"  Starting: {first_yield * 100:.3f}% → Ending: {last_yield * 100:.3f}%"
                                    )
                        else:
                            print(f"  Warning:  No forecast data for {maturity}Y")

                    summary_parts.append("")
                    print(f"   Added specific forecast display to summary")
                else:
                    print(f"  Info:  No specific_forecasts in state (or empty list)")

                # Add bond price forecasts if present
                price_forecasts = state.get("bond_price_forecasts", {})
                if price_forecasts:
                    # DEBUG: Print what we actually have
                    print(f"\n{'=' * 60}")
                    print(
                        f"DEBUG: bond_price_forecasts contains {len(price_forecasts)} bonds"
                    )
                    for bond_id, data in price_forecasts.items():
                        print(f"\nBond ID: {bond_id}")
                        print(f"Data type: {type(data)}")
                        if isinstance(data, dict):
                            print(f"Keys: {list(data.keys())}")
                            print(f"Values preview: {data}")
                        else:
                            print(f"Object attributes: {dir(data)}")
                    print(f"{'=' * 60}\n")

                    summary_parts.append("**Bond Price Information:**\n")
                    for bond_id, forecast_data in list(price_forecasts.items())[:10]:
                        # Handle both dict and object formats
                        if isinstance(forecast_data, dict):
                            bond_name = (
                                forecast_data.get("bond_name")
                                or forecast_data.get("name")
                                or bond_id
                            )
                            ltp = forecast_data.get("last_traded_price")
                            current_price = forecast_data.get("current_price")
                            predicted_price = forecast_data.get(
                                "predicted_price"
                            ) or forecast_data.get("price")
                            ytm = forecast_data.get("ytm")
                            expected_return = forecast_data.get("expected_return")

                            # DEBUG
                            print(f"\nDEBUG: Processing {bond_id}")
                            print(f"  bond_name: {bond_name}")
                            print(f"  ltp: {ltp}")
                            print(f"  current_price: {current_price}")
                            print(f"  predicted_price: {predicted_price}")
                            print(f"  ytm: {ytm}")
                            print(f"  expected_return: {expected_return}")
                        else:
                            bond_name = (
                                getattr(forecast_data, "bond_name", None)
                                or getattr(forecast_data, "name", None)
                                or bond_id
                            )
                            ltp = getattr(forecast_data, "last_traded_price", None)
                            current_price = getattr(
                                forecast_data, "current_price", None
                            )
                            predicted_price = getattr(
                                forecast_data, "predicted_price", None
                            ) or getattr(forecast_data, "price", None)
                            ytm = getattr(forecast_data, "ytm", None)
                            expected_return = getattr(
                                forecast_data, "expected_return", None
                            )

                        # Display header with cleaned bond name
                        summary_parts.append(f"\n**{bond_name}**")
                        summary_parts.append(f"ISIN: {bond_id}")

                        # DEBUG
                        print(f"\nDEBUG: Checking display conditions:")
                        print(f"  ltp and ltp > 0: {ltp and ltp > 0} (ltp={ltp})")
                        print(
                            f"  current_price and current_price > 0: {current_price and current_price > 0} (current_price={current_price})"
                        )

                        # Show Last Traded Price (most important)
                        if ltp and ltp > 0:
                            line = f" **Last Traded Price:** ₹{ltp:.2f}"
                            summary_parts.append(line)
                            print(f"  Added LTP line: {line}")
                        elif current_price and current_price > 0:
                            line = f" **Current Price:** ₹{current_price:.2f}"
                            summary_parts.append(line)
                            print(f"  Added current price line: {line}")
                        else:
                            print(f"  WARNING: No price to display!")
                        # Show YTM
                        if ytm:
                            line = f" **Yield to Maturity:** {ytm:.3f}%"
                            summary_parts.append(line)
                            print(f"  Added YTM line: {line}")
                        # Show predicted price if available
                        if predicted_price and predicted_price > 0:
                            line = f"🔮 **Predicted Price (21 days):** ₹{predicted_price:.2f}"
                            summary_parts.append(line)
                            print(f"  Added predicted price line: {line}")

                            # Calculate change
                            base_price = ltp if (ltp and ltp > 0) else current_price
                            if base_price and base_price > 0:
                                change = (
                                    (predicted_price - base_price) / base_price
                                ) * 100
                                direction = (
                                    "" if change > 0 else "" if change < 0 else ""
                                )
                                line = f"   {direction} Change: {change:+.2f}%"
                                summary_parts.append(line)
                                print(f"  Added change line: {line}")

                        # Show expected return
                        if expected_return:
                            line = (
                                f"💵 **Expected Return:** {expected_return * 100:.2f}%"
                            )
                            summary_parts.append(line)
                            print(f"  Added return line: {line}")

                        print(f"\nDEBUG: Total lines added for this bond: Check above")

                    summary_parts.append("")

                # Success:  Add real-time market intelligence if available
                realtime_info = state.get("realtime_market_intelligence")
                if realtime_info:
                    if summary_parts:
                        summary_parts.append("\n---\n")
                    summary_parts.append(realtime_info)
                # Success:  Add news articles if available
                news_articles = state.get("news_articles", [])
                if news_articles and len(news_articles) > 0:
                    if summary_parts:
                        summary_parts.append("\n---\n")
                    summary_parts.append(
                        f"**📰 Recent News Articles ({len(news_articles)}):**\n"
                    )
                    for i, article in enumerate(news_articles[:5], 1):  # Show top 5
                        title = (
                            article.get("title", "No title")
                            if isinstance(article, dict)
                            else getattr(article, "title", "No title")
                        )
                        url = (
                            article.get("url", "")
                            if isinstance(article, dict)
                            else getattr(article, "url", "")
                        )
                        summary_parts.append(f"{i}. {title}")
                        if url:
                            summary_parts.append(f"   {url}")
                    if len(news_articles) > 5:
                        summary_parts.append(
                            f"\n*...and {len(news_articles) - 5} more articles*"
                        )

                # Success:  Add web search results if available
                # web_search_results is a formatted string from real-time info agent
                # For raw results, get from tool_results
                web_search_formatted = state.get("web_search_results")
                web_search_tool_result = state.get("tool_results", {}).get(
                    ToolType.WEB_SEARCH
                )

                if web_search_formatted and isinstance(web_search_formatted, str):
                    # Use formatted context from real-time info agent
                    if summary_parts:
                        summary_parts.append("\n---\n")
                    summary_parts.append(web_search_formatted)
                elif (
                    web_search_tool_result
                    and web_search_tool_result.success
                    and web_search_tool_result.data
                ):
                    # Fallback: format raw web search results
                    if summary_parts:
                        summary_parts.append("\n---\n")
                    web_results = web_search_tool_result.data
                    summary_parts.append(
                        f"**DEBUG  Web Search Results ({len(web_results)}):**\n"
                    )
                    for i, result in enumerate(web_results[:3], 1):  # Show top 3
                        title = (
                            result.get("title", "No title")
                            if isinstance(result, dict)
                            else getattr(result, "title", "No title")
                        )
                        snippet = (
                            result.get("snippet", "")
                            if isinstance(result, dict)
                            else getattr(result, "snippet", "")
                        )
                        url = (
                            result.get("url", "")
                            if isinstance(result, dict)
                            else getattr(result, "url", "")
                        )
                        summary_parts.append(f"{i}. **{title}**")
                        if snippet:
                            summary_parts.append(f"   {snippet[:200]}...")
                        if url:
                            summary_parts.append(f"   {url}")
                # Fallback if no data
                if not summary_parts:
                    summary = "No data available for this query. Please try a different question."
                else:
                    summary = "\n".join(summary_parts)

                # Create advisory output with just the summary
                from schemas_v2 import AdvisoryOutput

                state["advisory"] = AdvisoryOutput(
                    query=state["user_query"],
                    recommendations=[],
                    summary=summary,
                    timestamp=datetime.now(),
                )

                state["execution_path"].append("run_response")
                print(f"Success:  Generated info-only response")
                return state

            # Regular advisory/analytical response with full agent pipeline
            if classified:
                portfolio_to_pass = None
                if state.get("portfolio"):
                    # Handle both UserPortfolio (from tool) and Portfolio (from MongoDB) formats
                    portfolio = state["portfolio"]

                    # Check if it's UserPortfolio (has holdings) or Portfolio (has positions)
                    if hasattr(portfolio, "holdings"):
                        # UserPortfolio format - convert to Portfolio
                        positions = []
                        for holding in portfolio.holdings:
                            position_data = {
                                "isin": holding.isin,
                                "name": holding.bond_name,
                                "quantity": holding.quantity,
                                "avg_cost": holding.avg_cost,
                                "current_price": holding.current_price,
                                "market_value": holding.market_value,
                                "weight": holding.weight,
                                "unrealized_pnl": holding.unrealized_pnl,
                            }
                            positions.append(Position(**position_data))

                        portfolio_to_pass = Portfolio(
                            portfolio_id=portfolio.portfolio_id,
                            name=portfolio.user_id,
                            positions=positions,
                            total_value=portfolio.total_value,
                            cash=portfolio.cash,
                        )
                    elif hasattr(portfolio, "positions"):
                        # Already Portfolio format (from MongoDB) - use directly
                        portfolio_to_pass = portfolio
                    else:
                        # Fallback: try to create Portfolio from available data
                        portfolio_to_pass = (
                            portfolio if isinstance(portfolio, Portfolio) else None
                        )

                # Dynamically select model for response agent if model selector available and enabled
                if (
                    self.model_selector
                    and self.config.enable_dynamic_model_selection
                    and ModelSelectorAgentType
                ):
                    query = state["user_query"]
                    response_model = self.model_selector.get_model_for_agent(
                        ModelSelectorAgentType.RESPONSE, query=query
                    )

                    # Update response agent LLM model
                    if hasattr(self.response_agent, "llm") and hasattr(
                        self.response_agent.llm, "model"
                    ):
                        if self.response_agent.llm.model != response_model:
                            self.response_agent.llm.model = response_model
                            print(
                                f"  Using model: {response_model} for response generation"
                            )

                    # If response agent will use advisory, update advisory model too
                    query_type = getattr(classified, "query_type", None)
                    if hasattr(query_type, "value"):
                        query_type_str = query_type.value
                    else:
                        query_type_str = str(query_type) if query_type else "unknown"

                    intent = getattr(classified, "intent", None)
                    if hasattr(intent, "value"):
                        intent_str = intent.value
                    else:
                        intent_str = str(intent) if intent else "unknown"

                    needs_advisory = query_type_str == "advisory" or intent_str in [
                        "buy_recommendation",
                        "sell_recommendation",
                        "switch_bonds",
                    ]

                    if needs_advisory:
                        # Update advisory agent model
                        advisory_model = self.model_selector.get_model_for_agent(
                            ModelSelectorAgentType.ADVISORY, query=query
                        )
                        if hasattr(self.advisory, "llm") and hasattr(
                            self.advisory.llm, "model"
                        ):
                            if self.advisory.llm.model != advisory_model:
                                self.advisory.llm.model = advisory_model
                                print(f"  Using model: {advisory_model} for advisory")
                        # Also update in response agent's advisory reference
                        if hasattr(self.response_agent, "advisory_agent"):
                            if hasattr(
                                self.response_agent.advisory_agent, "llm"
                            ) and hasattr(
                                self.response_agent.advisory_agent.llm, "model"
                            ):
                                self.response_agent.advisory_agent.llm.model = (
                                    advisory_model
                                )

                # Use response agent which handles different query types appropriately
                # Get conversation history from LangGraph messages
                messages = state.get("messages", [])
                conversation_history = self._messages_to_dict(messages)

                # Debug: Log conversation history length
                if conversation_history:
                    print(
                        f"  Passing {len(conversation_history)} messages to response agent"
                    )
                else:
                    print(
                        f"  Warning: No conversation history available for response agent"
                    )

                # Get latest yields for current yield queries (not forecasts)
                latest_yields = state.get("latest_yields_display") or state.get(
                    "yield_curve"
                )

                state["advisory"] = self.response_agent.generate_response(
                    classified_query=classified,
                    bond_analytics=state.get("bond_analytics", {}),
                    bond_scores=state.get("bond_scores", {}),
                    ml_predictions=state.get("ml_predictions", {}),
                    portfolio=portfolio_to_pass,
                    yield_forecasts=state.get("yield_forecasts"),
                    latest_yields=latest_yields,  # Pass current yields for yield queries
                    bond_price_forecasts=state.get("bond_price_forecasts", {}),
                    bond_details=state.get("bond_details", {}),
                    bonds_universe=state.get(
                        "bonds_universe", []
                    ),  # Pass bonds list for maturity queries
                    conversation_history=conversation_history,
                    web_search_results=state.get(
                        "web_search_results"
                    ),  # Pass real-time info
                )

                query_type = getattr(classified, "query_type", None)
                if hasattr(query_type, "value"):
                    query_type_str = query_type.value
                else:
                    query_type_str = str(query_type) if query_type else "unknown"

                if query_type_str == "advisory" or (
                    state.get("advisory") and len(state["advisory"].recommendations) > 0
                ):
                    print(
                        f"Success:  Generated {len(state['advisory'].recommendations)} recommendations"
                    )
                else:
                    print(f"Success:  Generated analytics/informational response")

        except Exception as e:
            print(f"Error:  Response generation error: {e}")
            import traceback

            traceback.print_exc()
            state["errors"].append(f"Response generation error: {str(e)}")

            # Fallback response
            from schemas_v2 import AdvisoryOutput

            state["advisory"] = AdvisoryOutput(
                query=state["user_query"],
                recommendations=[],
                summary="I encountered an error while processing your query. Please try rephrasing or ask about bonds, portfolios, or trading.",
                timestamp=datetime.now(),
            )

        state["execution_path"].append("run_response")
        return state

    def _should_explain(self, state: GraphState) -> str:
        """Conditional: Should we run explainability?"""
        plan = state.get("execution_plan")
        needs_explain = state.get("needs_explainability", False)
        has_advisory = state.get("advisory") is not None
        if plan and plan.needs_explainability:
            return "yes"
        if needs_explain and has_advisory:
            return "yes"
        return "no"
    def _run_explainability(self, state: GraphState) -> GraphState:
        """Run explainability"""
        AgentLogger.print_agent_header("Explainability Agent", "RUNNING")
        state["current_step"] = "explainability"

        try:
            # Dynamically select model for explainability if model selector available and enabled
            if (
                self.model_selector
                and self.config.enable_dynamic_model_selection
                and ModelSelectorAgentType
            ):
                query = state["user_query"]
                model = self.model_selector.get_model_for_agent(
                    ModelSelectorAgentType.EXPLAINABILITY, query=query
                )
                # Update explainability LLM model
                if hasattr(self.explainability, "llm") and hasattr(
                    self.explainability.llm, "model"
                ):
                    if self.explainability.llm.model != model:
                        self.explainability.llm.model = model
                        print(f"  Using model: {model} for explainability")

            if state.get("advisory"):
                state["explanations"] = self.explainability.explain_recommendations(
                    recommendations=state["advisory"].recommendations,
                    bond_analytics=state.get("bond_analytics", {}),
                    bond_scores=state.get("bond_scores", {}),
                    ml_predictions=state.get("ml_predictions", {}),
                    rbi_policy=self._extract_rbi_from_rag(state),
                    news_items=[
                        article.dict() for article in state.get("news_articles", [])
                    ],
                    credit_ratings=state.get("credit_ratings", {}),
                )
                AgentLogger.print_agent_result(
                    "Explainability Agent",
                    {"explanations_count": len(state["explanations"])},
                    f"Generated {len(state['explanations'])} explanations",
                )
                # Show sample explanation
                if state["explanations"]:
                    sample_explanation = state["explanations"][0]
                    if hasattr(sample_explanation, "explanation"):
                        AgentLogger.print_agent_output(
                            "Explainability Agent",
                            sample_explanation.explanation[:300] + "..."
                            if len(sample_explanation.explanation) > 300
                            else sample_explanation.explanation,
                            "Sample Explanation",
                        )
        except Exception as e:
            print(f" Explainability error: {e}")
            state["errors"].append(f"Explainability error: {str(e)}")

        state["execution_path"].append("run_explainability")
        return state

    async def _handle_non_bond_query(self, state: GraphState) -> GraphState:
        """Handle non-bond queries by routing to general LLM or web search"""
        print(f"\n{'=' * 80}")
        print(f"INFO:  HANDLING NON-BOND QUERY...")
        print(f"{'=' * 80}")
        state["current_step"] = "handling_non_bond_query"

        classified = state.get("classified_query")
        if not classified:
            routing = NonBondRouting.GENERAL_LLM
        else:
            routing_str = getattr(classified, "non_bond_routing", None)
            if routing_str:
                try:
                    routing = NonBondRouting(routing_str)
                except ValueError:
                    routing = NonBondRouting.GENERAL_LLM
            else:
                routing = NonBondRouting.GENERAL_LLM

        query = state["user_query"]

        try:
            if routing == NonBondRouting.WEB_SEARCH and self.web_search:
                print(f"  DEBUG  Routing to web search...")

                # Perform web search
                web_search_result = await self.web_search.search(
                    query=query, num_results=5
                )

                if web_search_result.success:
                    search_results = web_search_result.data

                    # Synthesize results with LLM
                    synthesis_prompt = ChatPromptTemplate.from_messages(
                        [
                            (
                                "system",
                                """You are a helpful assistant. Based on the search results provided, 
give a clear and concise answer to the user's question. Cite sources when relevant.""",
                            ),
                            (
                                "user",
                                """Question: {query}

Search Results:
{search_results}

Provide a helpful answer based on these results.""",
                            ),
                        ]
                    )

                    search_results_text = "\n\n".join(
                        [
                            f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}\nURL: {r.get('url', '')}"
                            for r in search_results[:5]
                        ]
                    )

                    messages = synthesis_prompt.format_messages(
                        query=query, search_results=search_results_text
                    )
                    llm_response = self.general_llm.invoke(messages)
                    summary = (
                        llm_response.content
                        if hasattr(llm_response, "content")
                        else str(llm_response)
                    )
                else:
                    summary = f"I couldn't perform a web search for '{query}'. Please try again later."

            else:  # GENERAL_LLM
                print(f"  💬 Routing to general LLM...")

                # Use general LLM
                messages = self.general_prompt.format_messages(query=query)
                response = self.general_llm.invoke(messages)
                summary = (
                    response.content if hasattr(response, "content") else str(response)
                )

            # Create advisory output with the response
            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=summary,
                timestamp=datetime.now(),
            )

            state["execution_path"].append("handle_non_bond_query")
            print(f" Non-bond query handled via {routing.value}")

        except Exception as e:
            print(f"Error:  Error handling non-bond query: {e}")
            import traceback

            traceback.print_exc()

            # Fallback response
            state["advisory"] = AdvisoryOutput(
                query=query,
                recommendations=[],
                summary=f"I encountered an error processing your query: {str(e)}",
                timestamp=datetime.now(),
            )

        return state

    def _finalize(self, state: GraphState) -> GraphState:
        """Finalize and convert to EnhancedAgentState"""
        print(f"\n FINALIZING...")
        state["current_step"] = "finalized"
        state["processing_time"] = time.time() - state.get("start_time", time.time())
        state["timestamp"] = datetime.now()

        # Check output guardrails if enabled (check config dynamically)
        if (
            self.config.enable_guardrails
            and self.config.guardrails_check_output
            and self.guardrails
        ):
            advisory = state.get("advisory")
            if advisory and advisory.summary:
                # Guardrails checker respects its enabled flag, which we set based on config
                if self.guardrails.enabled != self.config.enable_guardrails:
                    self.guardrails.enabled = self.config.enable_guardrails
                guard_result = self.guardrails.check_output(advisory.summary)
                if not guard_result.is_safe:
                    print(f"Warning:   Guardrails: Output flagged as unsafe")
                    print(f"   Reason: {guard_result.reason}")
                    print(f"   Categories: {guard_result.categories}")
                    state["errors"].append(
                        f"Output safety check failed: {guard_result.reason}"
                    )
                    # Replace with safe response
                    from schemas_v2 import AdvisoryOutput

                    state["advisory"] = AdvisoryOutput(
                        query=state["user_query"],
                        recommendations=[],
                        summary="I apologize, but I cannot provide a response that meets safety guidelines. Please try rephrasing your query or ask about bonds, trading, or financial analysis.",
                        timestamp=datetime.now(),
                    )

        # Add assistant response to messages for conversation history
        advisory = state.get("advisory")
        if advisory and advisory.summary:
            messages = state.get("messages", [])
            # Check if assistant message already exists
            if not any(
                isinstance(msg, AIMessage) and msg.content == advisory.summary
                for msg in messages
            ):
                messages.append(AIMessage(content=advisory.summary))
                state["messages"] = messages

        state["execution_path"].append("finalize")

        # Print final summary
        AgentLogger.print_agent_header("Pipeline", "COMPLETE")
        AgentLogger.print_metrics(
            {
                "Processing Time": f"{state['processing_time']:.2f}s",
                "Execution Path": " → ".join(state["execution_path"]),
                "Cache Hits": f"{state.get('cache_hits', 0)}/{state.get('total_tool_calls', 0)}",
                "Recommendations": len(state["advisory"].recommendations)
                if state.get("advisory")
                else 0,
                "Errors": len(state.get("errors", [])),
            },
            "Pipeline",
        )

        return state

    def _messages_to_dict(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangGraph messages to dict format for agents"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
        return result
    def _dict_to_messages(self, history: List[Dict[str, str]]) -> List[BaseMessage]:
        """Convert dict format to LangGraph messages"""
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages
    async def run_async(
        self,
        query: str,
        user_id: str,
        bonds_universe: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None,
        thread_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> EnhancedAgentState:
        """
        Run the LangGraph pipeline

        Args:
            query: User query
            user_id: User identifier
            bonds_universe: Optional bonds universe
            user_profile: Optional user profile
            thread_id: Optional thread identifier for conversation history (uses user_id if not provided)
            conversation_history: Optional conversation history. If not provided, loads from checkpoint
        """
        # Use thread_id for session management (LangGraph's built-in concept)
        if thread_id is None:
            thread_id = f"{user_id}_default"

        # Get existing messages from our manual store
        existing_messages = self._message_store.get(thread_id, [])

        # If conversation_history is provided, use it (for backward compatibility)
        if conversation_history:
            existing_messages = self._dict_to_messages(conversation_history)

        # Add new user message
        messages = existing_messages + [HumanMessage(content=query)]

        # Initialize graph state
        initial_state: GraphState = {
            "user_query": query,
            "user_id": user_id,
            "user_profile": user_profile,
            "bonds_universe": bonds_universe,
            "messages": messages,
            "current_step": "start",
            "execution_path": [],
            "errors": [],
            "classified_query": None,
            "needs_portfolio": False,
            "needs_rag": False,
            "needs_explainability": False,
            "execution_plan": None,
            "tool_results": {},
            "tool_execution_order": [],
            "news_articles": [],
            "credit_ratings": {},
            "portfolio": None,
            "yield_forecasts": None,
            "bond_price_forecasts": {},
            "rag_results": None,
            "web_search_results": None,
            "ml_predictions": {},
            "bond_analytics": {},
            "bond_scores": {},
            "advisory": None,
            "explanations": [],
            "start_time": time.time(),
            "processing_time": 0.0,
            "cache_hits": 0,
            "total_tool_calls": 0,
            "timestamp": datetime.now(),
        }

        # Run graph (without checkpointing to avoid serialization issues)
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            print(f"Warning:   Graph execution error: {e}")
            traceback.print_exc()
            # Return error state
            final_state = initial_state
            final_state["errors"].append(f"Graph execution error: {str(e)}")

        # Save messages to our manual store for conversation history
        # Get messages from final state (should include assistant response from _finalize)
        messages = final_state.get("messages", [])

        # Ensure assistant response is in messages if advisory exists
        # This is a safety check in case _finalize didn't add it properly
        advisory = final_state.get("advisory")
        if advisory and advisory.summary:
            # Check if the LAST message is an assistant message (if not, we need to add it)
            needs_assistant_message = True
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, AIMessage):
                    # Last message is already an assistant message, assume it's the response
                    needs_assistant_message = False

            if needs_assistant_message:
                messages.append(AIMessage(content=advisory.summary))
                print(f"  ➕ Added assistant response to messages (was missing)")

        if messages:
            self._message_store[thread_id] = messages
            print(f"  💾 Saved {len(messages)} messages to conversation history")
        else:
            print(f"  Warning:   Warning: No messages found in final state to save")

        # Convert to EnhancedAgentState
        result = self._convert_to_enhanced_state(final_state)

        return result

    def _convert_advisory_output(
        self, advisory_obj: Any, SchemaAdvisoryOutput: type
    ) -> Any:
        """Convert AdvisoryOutput to the correct schema type for Pydantic validation"""
        if advisory_obj is None:
            return None

        # Always convert via dict to avoid Pydantic v2 model_type validation issues
        # This ensures the output is always a fresh instance of SchemaAdvisoryOutput

        # If it's already a dict, reconstruct directly
        if isinstance(advisory_obj, dict):
            try:
                return SchemaAdvisoryOutput(**advisory_obj)
            except Exception as e:
                print(f"Error: Failed to convert dict to AdvisoryOutput: {e}")
                return None

        # If it has model_dump() (Pydantic v2), use it - this is the preferred method
        if hasattr(advisory_obj, "model_dump"):
            try:
                data = advisory_obj.model_dump()
                # Ensure all nested objects are also converted to dicts
                if "recommendations" in data and data["recommendations"]:
                    # Convert recommendations to ensure they're dicts
                    data["recommendations"] = [
                        rec.model_dump()
                        if hasattr(rec, "model_dump")
                        else (rec.dict() if hasattr(rec, "dict") else rec)
                        for rec in data["recommendations"]
                    ]
                return SchemaAdvisoryOutput(**data)
            except Exception as e:
                print(
                    f"Warning: Failed to convert AdvisoryOutput using model_dump(): {e}"
                )
                import traceback

                traceback.print_exc()

        # If it has dict() (Pydantic v1), use it
        if hasattr(advisory_obj, "dict"):
            try:
                data = advisory_obj.dict()
                # Ensure all nested objects are also converted to dicts
                if "recommendations" in data and data["recommendations"]:
                    data["recommendations"] = [
                        rec.dict() if hasattr(rec, "dict") else rec
                        for rec in data["recommendations"]
                    ]
                return SchemaAdvisoryOutput(**data)
            except Exception as e:
                print(f"Warning: Failed to convert AdvisoryOutput using dict(): {e}")
                import traceback

                traceback.print_exc()

        # Last resort: try to extract attributes manually
        try:
            recommendations = getattr(advisory_obj, "recommendations", [])
            # Convert recommendations to dicts if they're Pydantic models
            recs_data = []
            for rec in recommendations:
                if hasattr(rec, "model_dump"):
                    recs_data.append(rec.model_dump())
                elif hasattr(rec, "dict"):
                    recs_data.append(rec.dict())
                elif isinstance(rec, dict):
                    recs_data.append(rec)
                else:
                    recs_data.append(rec)

            return SchemaAdvisoryOutput(
                query=getattr(advisory_obj, "query", ""),
                recommendations=recs_data,
                summary=getattr(advisory_obj, "summary", ""),
                portfolio_changes=getattr(advisory_obj, "portfolio_changes", {}),
                timestamp=getattr(advisory_obj, "timestamp", datetime.now()),
            )
        except Exception as e:
            print(f"Error: Failed to convert AdvisoryOutput manually: {e}")
            import traceback

            traceback.print_exc()
            # Return None as fallback
            return None

    def _convert_to_enhanced_state(self, graph_state: GraphState) -> EnhancedAgentState:
        """Convert GraphState to EnhancedAgentState"""
        from schemas_v2 import AdvisoryOutput as SchemaAdvisoryOutput

        # Convert classified_query from query_classifier format to schemas_v2 format
        classified_query_raw = graph_state.get("classified_query")
        classified_query = None

        if classified_query_raw:
            from schemas_v2 import (
                ClassifiedQuery as SchemaClassifiedQuery,
                QueryType,
                Intent,
                Constraint,
                ConstraintType,
            )
            from pydantic import BaseModel

            # Always convert to ensure we have the correct schemas_v2.ClassifiedQuery type
            # Check if it's already the correct type by checking the class module
            is_correct_type = False
            try:
                # Check if it's already schemas_v2.ClassifiedQuery by checking the module
                if isinstance(classified_query_raw, BaseModel):
                    # Check if it's from schemas_v2 module
                    class_module = type(classified_query_raw).__module__
                    class_name = type(classified_query_raw).__name__
                    if class_module == "schemas_v2" and class_name == "ClassifiedQuery":
                        # It's already the correct type
                        is_correct_type = True
                        classified_query = classified_query_raw
                    else:
                        # It's a Pydantic model but wrong type, convert it
                        try:
                            if hasattr(classified_query_raw, "model_dump"):
                                data = classified_query_raw.model_dump()
                            elif hasattr(classified_query_raw, "dict"):
                                data = classified_query_raw.dict()
                            else:
                                # Can't convert, treat as query_classifier version
                                raise ValueError("Cannot convert Pydantic model")
                            # Try to create from dict
                            classified_query = SchemaClassifiedQuery(**data)
                            is_correct_type = True
                        except Exception as e:
                            # Conversion failed, treat as query_classifier version
                            print(
                                f"Warning: Could not convert Pydantic ClassifiedQuery: {e}"
                            )
                            is_correct_type = False
                else:
                    # Not a Pydantic model, treat as query_classifier version
                    is_correct_type = False
            except Exception as e:
                print(f"Warning: Error checking ClassifiedQuery type: {e}")
                is_correct_type = False

            if not is_correct_type:
                # It's the query_classifier version (plain Python class), convert it
                # Check if it's bond-related
                is_bond_related = getattr(classified_query_raw, "is_bond_related", True)

                # Handle non-bond queries
                if not is_bond_related:
                    non_bond_routing_str = getattr(
                        classified_query_raw, "non_bond_routing", None
                    )
                    non_bond_routing = None
                    if non_bond_routing_str:
                        try:
                            non_bond_routing = NonBondRouting(non_bond_routing_str)
                        except ValueError:
                            non_bond_routing = NonBondRouting.GENERAL_LLM
                    else:
                        non_bond_routing = NonBondRouting.GENERAL_LLM

                    # Create ClassifiedQuery for non-bond query
                    reasoning = getattr(classified_query_raw, "reasoning", None)
                    if reasoning is None or not isinstance(reasoning, str):
                        reasoning = "Non-bond query"

                    classified_query = SchemaClassifiedQuery(
                        query=getattr(
                            classified_query_raw,
                            "original_query",
                            getattr(
                                classified_query_raw, "query", graph_state["user_query"]
                            ),
                        ),
                        query_type=QueryType.GENERAL,
                        intent=Intent.CUSTOM,
                        constraints=[],
                        reasoning=getattr(classified_query_raw, "reasoning", None)
                        or "",
                        confidence=getattr(classified_query_raw, "confidence", 0.8),
                        is_bond_related=False,
                        non_bond_routing=non_bond_routing,
                    )
                else:
                    # Bond-related query - convert intent and query_type
                    intent_str = getattr(classified_query_raw, "intent", None)
                    if hasattr(intent_str, "value"):
                        intent_str = intent_str.value
                    elif isinstance(intent_str, str):
                        intent_str = intent_str.lower()
                    else:
                        intent_str = (
                            str(intent_str).lower()
                            if intent_str
                            else "buy_recommendation"
                        )

                    # Map to schemas_v2 Intent enum
                    intent_mapping = {
                        "reduce_duration": Intent.REDUCE_DURATION,
                        "increase_yield": Intent.INCREASE_YIELD,
                        "improve_quality": Intent.IMPROVE_QUALITY,
                        "buy_recommendation": Intent.CUSTOM,
                        "sell_recommendation": Intent.CUSTOM,
                        "portfolio_analysis": Intent.CUSTOM,
                    }
                    intent = intent_mapping.get(intent_str, Intent.CUSTOM)

                    # Map query_type (default to ADVISORY)
                    query_type = QueryType.ADVISORY
                    if (
                        "portfolio" in intent_str
                        or "portfolio" in graph_state["user_query"].lower()
                    ):
                        query_type = QueryType.PORTFOLIO
                    elif "analytics" in intent_str:
                        query_type = QueryType.ANALYTICS

                    # Convert constraints
                    constraints = []
                    filters = getattr(classified_query_raw, "filters", {})
                    if filters:
                        if "min_rating" in filters:
                            constraints.append(
                                Constraint(
                                    constraint_type=ConstraintType.RATING,
                                    value=filters["min_rating"],
                                )
                            )
                        if "sectors" in filters:
                            constraints.append(
                                Constraint(
                                    constraint_type=ConstraintType.SECTOR,
                                    value=filters["sectors"],
                                )
                            )
                        if "max_duration" in filters:
                            constraints.append(
                                Constraint(
                                    constraint_type=ConstraintType.DURATION,
                                    value=filters["max_duration"],
                                )
                            )

                    # Create schemas_v2 ClassifiedQuery for bond query
                    reasoning = getattr(classified_query_raw, "reasoning", None)
                    if reasoning is None or not isinstance(reasoning, str):
                        reasoning = ""

                    classified_query = SchemaClassifiedQuery(
                        query=getattr(
                            classified_query_raw,
                            "original_query",
                            getattr(
                                classified_query_raw, "query", graph_state["user_query"]
                            ),
                        ),
                        query_type=query_type,
                        intent=intent,
                        constraints=constraints,
                        reasoning=getattr(classified_query_raw, "reasoning", None)
                        or "",
                        confidence=getattr(classified_query_raw, "confidence", 0.8),
                        is_bond_related=True,
                        non_bond_routing=None,
                    )

        # Ensure classified_query is always a valid schemas_v2.ClassifiedQuery or None
        if classified_query is not None:
            # Double-check it's the correct type
            from schemas_v2 import ClassifiedQuery as SchemaClassifiedQuery
            if not isinstance(classified_query, SchemaClassifiedQuery):
                # Last resort: create a basic ClassifiedQuery from the raw query
                try:
                    query_text = graph_state["user_query"]
                    classified_query = SchemaClassifiedQuery(
                        query=query_text,
                        query_type=QueryType.ADVISORY,
                        intent=Intent.CUSTOM,
                        constraints=[],
                        reasoning="Fallback conversion",
                        confidence=0.5,
                        is_bond_related=True,
                        non_bond_routing=None,
                    )
                except Exception as e:
                    print(f"Error creating fallback ClassifiedQuery: {e}")
                    classified_query = None
        return EnhancedAgentState(
            user_query=graph_state["user_query"],
            user_id=graph_state["user_id"],
            timestamp=graph_state.get("timestamp", datetime.now()),
            execution_plan=graph_state.get("execution_plan"),
            tool_results=graph_state.get("tool_results", {}),
            news_articles=graph_state.get("news_articles", []),
            credit_ratings=graph_state.get("credit_ratings", {}),
            portfolio=graph_state.get("portfolio"),
            yield_forecasts=None,
            bond_price_forecasts=graph_state.get("bond_price_forecasts", {}),
            rag_results=graph_state.get("rag_results"),
            classified_query=classified_query,
            ml_predictions=graph_state.get("ml_predictions", {}),
            bond_analytics=graph_state.get("bond_analytics", {}),
            bond_scores=graph_state.get("bond_scores", {}),
            advisory=(
                None
                if graph_state.get("advisory") is None
                else self._convert_advisory_output(
                    graph_state["advisory"], SchemaAdvisoryOutput
                )
            ),
            explanations=graph_state.get("explanations", []),
            processing_time=graph_state.get("processing_time", 0.0),
            cache_hits=graph_state.get("cache_hits", 0),
            total_tool_calls=graph_state.get("total_tool_calls", 0),
        )

    def _extract_rbi_from_rag(self, state: GraphState) -> Optional[Dict]:
        """Extract RBI policy from RAG results"""
        if not state.get("rag_results"):
            return None

        rbi_data = {
            "repo_rate": 6.5,
            "stance": "neutral",
            "CPI_forecast": 4.5,
            "forward_guidance": "Data dependent",
        }

        return rbi_data

    def _filter_bonds_by_query(
        self, bonds: List[Dict], state: GraphState
    ) -> List[Dict]:
        """Filter bonds based on user query and constraints"""
        from datetime import datetime

        # Success:  STEP 1: Apply 10-year maturity filter FIRST
        original_count = len(bonds)
        bonds = MATURITY_FILTER.filter_bonds(bonds)
        filtered_count = len(bonds)
        if original_count > filtered_count:
            print(f"\n     DEBUG  Maturity Filter Applied:")
            print(f"        • Original bonds: {original_count}")
            print(f"        • After filter: {filtered_count}")
            print(
                f"        • Removed: {original_count - filtered_count} bonds (>10Y maturity)"
            )

        # STEP 2: Apply query-based filters
        classified = state.get("classified_query")
        query_lower = state["user_query"].lower()

        filtered = []

        for bond in bonds:
            # Get bond attributes
            maturity_date_str = bond.get("maturity_date", "")
            ytm = bond.get("ytm", 0)
            coupon = bond.get("coupon_rate", 0)
            name = bond.get("name", "").lower()

            # Convert ytm to decimal if needed
            if ytm > 1:
                ytm = ytm / 100.0

            should_include = True

            # Filter by maturity year if mentioned in query
            if any(
                year in query_lower
                for year in ["2028", "2029", "2030", "2025", "2026", "2027"]
            ):
                for year in ["2025", "2026", "2027", "2028", "2029", "2030"]:
                    if year in query_lower:
                        if year not in maturity_date_str:
                            should_include = False
                        break

            # Filter by yield if "high yield" mentioned
            if "high yield" in query_lower or "high yielding" in query_lower:
                if ytm < 0.07:  # Less than 7%
                    should_include = False

            # Filter by maturity duration
            if "short term" in query_lower or "short-term" in query_lower:
                if maturity_date_str:
                    try:
                        mat_date = datetime.strptime(maturity_date_str, "%Y-%m-%d")
                        years_left = (mat_date - datetime.now()).days / 365.25
                        if years_left > 3:
                            should_include = False
                    except:
                        pass

            if "long term" in query_lower or "long-term" in query_lower:
                if maturity_date_str:
                    try:
                        mat_date = datetime.strptime(maturity_date_str, "%Y-%m-%d")
                        years_left = (mat_date - datetime.now()).days / 365.25
                        if years_left < 7:
                            should_include = False
                    except:
                        pass

            # Apply constraints from classifier (handle both Pydantic and dict)
            if classified and hasattr(classified, "constraints"):
                for constraint in classified.constraints:
                    # Handle Constraint object
                    if hasattr(constraint, "constraint_type"):
                        constraint_type = constraint.constraint_type
                        constraint_value = constraint.value

                        # Extract enum value if needed
                        if hasattr(constraint_type, "value"):
                            constraint_type = constraint_type.value

                        if constraint_type == "duration":
                            max_duration = float(constraint_value)
                            if maturity_date_str:
                                try:
                                    mat_date = datetime.strptime(
                                        maturity_date_str, "%Y-%m-%d"
                                    )
                                    years_left = (
                                        mat_date - datetime.now()
                                    ).days / 365.25
                                    if years_left > max_duration:
                                        should_include = False
                                except:
                                    pass

                        elif constraint_type == "yield":
                            min_yield = float(constraint_value)
                            if ytm < min_yield:
                                should_include = False

            if should_include:
                filtered.append(bond)

        # If no bonds match, return top 10 by yield
        if len(filtered) == 0:
            print("Warning:  No bonds matched filters, returning top 10 by yield")
            sorted_bonds = sorted(bonds, key=lambda b: b.get("ytm", 0), reverse=True)
            return sorted_bonds[:10]

        # Limit to top 20 bonds to avoid overload
        if len(filtered) > 20:
            print(f"Warning:  Limiting from {len(filtered)} to top 20 bonds")
            sorted_filtered = sorted(
                filtered, key=lambda b: b.get("ytm", 0), reverse=True
            )
            return sorted_filtered[:20]

        return filtered

    def _get_yield_curve(self) -> Dict[float, float]:
        if self.mcp_client and self.config.enable_pathway_forecasts:
            try:
                yield_curve = self.mcp_client.get_yield_curve_dict()
                if yield_curve:
                    print(
                        f" Using live yield curve from MCP: {len(yield_curve)} maturities"
                    )
                    return yield_curve
            except Exception as e:
                print(f"Warning: Could not fetch MCP yield curve: {e}")

        # Fallback to static curve
        return {
            0.5: 0.060,
            1.0: 0.065,
            2.0: 0.068,
            5.0: 0.072,
            7.0: 0.074,
            10.0: 0.076,
            15.0: 0.078,
        }

    def _get_default_bonds(self) -> List[Dict]:
        """Get default bond universe from MCP server"""
        if self.mcp_client:
            try:
                result = self.mcp_client.list_available_bonds()
                bonds = result.get("available_bonds", [])

                if bonds:
                    # Convert to expected format
                    default_bonds = []
                    for bond in bonds[:50]:  # Limit to 50 bonds
                        default_bonds.append(
                            {
                                "isin": bond.get("isin", ""),
                                "symbol": bond.get("symbol", ""),
                                "name": bond.get("name", ""),
                                "issuer": bond.get("name", "").split()[0],
                                "bond_type": "Corporate",
                                "sector": "Other",
                                "coupon_rate": bond.get("coupon_rate", 0)
                                / 100.0,  # Convert to decimal
                                "maturity_date": bond.get("maturity_date", ""),
                                "last_traded_price": 100.0,
                                "ytm": bond.get("coupon_rate", 7.0) / 100.0,
                                "rating": "A",
                                "volume": 1000000,
                                "duration": 5.0,
                                "years_to_maturity": 5.0,
                            }
                        )
                    print(f"Success:  Loaded {len(default_bonds)} bonds from MCP")
                    return default_bonds
            except Exception as e:
                print(f"Warning: Could not load bonds from MCP: {e}")
        # Fallback to empty list (forces user to provide bonds_universe)
        print("Warning:  No default bonds available, use bonds_universe parameter")
        return []


def create_orchestrator_v3(
    config: SystemConfigV2,
    rag_system: Optional[RAGSystem] = None,
    mcp_client: Optional[MCPBondsClient] = None,
    model_selector: Optional[ModelSelector] = None,
) -> OrchestratorV3:
    """
    Factory function to create OrchestratorV3

    Uses LangGraph message history for conversation management (no SessionManager needed)
    """
    return OrchestratorV3(
        config=config,
        rag_system=rag_system,
        mcp_client=mcp_client,
        model_selector=model_selector,
    )
