"""
Response Agent
General response agent that formats appropriate responses based on query type
Handles analytics, informational, and advisory queries differently
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

from schemas_v2 import (
    BondAnalytics,
    BondScore,
    Portfolio,
    TradeRecommendation,
    AdvisoryOutput,
    QueryType,
    Intent,
    ClassifiedQuery as SchemaClassifiedQuery,
)
from .query_classifier import ClassifiedQuery as QueryClassifierClassifiedQuery
from .advisory import AdvisoryAgent


class ResponseAgent:
    """
    General response agent that provides appropriate responses based on query type
    - Analytics queries: Returns formatted analytics data
    - Informational queries: Answers questions directly
    - Advisory queries: Generates trade recommendations
    """

    def __init__(self, llm: ChatOpenAI, advisory_agent: AdvisoryAgent):
        self.llm = llm
        self.advisory_agent = advisory_agent

        # Prompt for analytics/informational queries
        self.response_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a helpful bond market analyst assistant. Your job is to answer user queries about bonds, yields, analytics, and market data.

CRITICAL RULES:
1. Answer ONLY what the user asked - do not provide recommendations unless explicitly asked
2. For informational queries (e.g., "tell me about X", "what is Y"), provide information only
3. Do NOT suggest buying, selling, or any actions unless the user explicitly asks for recommendations
4. Be direct and factual - present data and information, not advice
5. If the user asks about specific bonds/companies, focus on those only
6. **CRITICAL: If a Bonds List is provided in the data, you MUST ONLY mention, discuss, or reference bonds that appear in that list. Do NOT add, invent, or mention any bonds that are not in the provided Bonds List. The Bonds List has already been filtered based on the user's query (e.g., maturity year, coupon rate, etc.), so you should only discuss the bonds shown in that list.**
7. If the user asks follow-up questions (e.g., "explain how you got this", "why is that", "which is the next best", "give me the exact split"), you MUST reference the previous conversation context to understand what they're referring to
8. For follow-up questions like "which is the next best", "what about the second one", "give me the exact split", etc., look at the previous conversation to understand what was discussed:
   - If they asked about the highest yielding bond, "next best" means the second highest yielding bond
   - If they asked for recommendations with a budget, "exact split" means the specific allocation of that budget across the recommended bonds
   - If they mentioned their name, remember it and use it when appropriate
9. Always check the conversation context first to understand what the user is referring to in follow-up questions
10. If user context is provided (name, budget, etc.), use it to personalize your responses
11. For questions like "what is my name", check the user context and conversation history - if the user mentioned their name earlier, tell them what it is

Based on the query type and available data, provide:
- For analytics queries: Present the analytics data in a clear, structured format
- For informational queries: Answer the question directly using available data
- For follow-up questions: Reference previous conversation and explain based on context
- Be concise but comprehensive
- Use tables or lists when appropriate
- Cite specific numbers and metrics
- ALWAYS show percentages with 2 decimal places (e.g., 8.07% not 8%, 5.84% not 6%)

Available data may include:
- Bond analytics (prices, yields, duration, ratings)
- Bond scores (valuation, return, quality, liquidity scores)
- ML predictions (expected returns, price forecasts)
- Portfolio information
- Yield forecasts
- Bond details (ISIN, coupon, maturity, and other bond information)
- Credit ratings

Format your response clearly and helpfully. Do NOT add recommendations unless explicitly requested.""",
                ),
                (
                    "user",
                    """Previous Conversation Context:
{conversation_context}

Current User Query: {query}
Query Type: {query_type}
Intent: {intent}

Bond Analytics:
{analytics_data}

Bond Scores:
{scores_data}

ML Predictions:
{ml_predictions}

Portfolio:
{portfolio_data}

Yield Forecasts:
{yield_forecasts}

Bond Details:
{bond_details}

Bonds List:
{bonds_list}

CRITICAL: If a Bonds List is provided above, you MUST ONLY use bonds from that list in your response. Do NOT add, mention, or reference any bonds that are not in the provided Bonds List. The Bonds List has already been filtered based on the user's query (e.g., maturity year, coupon rate, etc.), so you should only discuss the bonds shown in that list.

Answer the user's query using the available data and conversation context. Be specific and cite numbers.

IMPORTANT FOR FOLLOW-UP QUESTIONS:
- If the user asks "which is the next best", "what about the second one", "show me another", etc., look at the previous conversation to understand what they're referring to
- For example, if they previously asked about the "highest yielding bond", then "next best" means the second highest yielding bond
- If they asked about the "best bond", then "next best" means the second best bond
- Always sort the data appropriately (by yield, score, etc.) and provide the next item in that sorted list
- Reference the previous conversation explicitly in your response to show you understand the context

SPECIFIC FOLLOW-UP HANDLING:
- "give me the exact split" or "exact split": If the user previously asked for recommendations with a budget (e.g., "I have Rs. 2000"), provide the exact allocation of that budget across the recommended bonds with quantities
- "what is my name" or "my name": Check the user context and conversation history - if the user mentioned their name earlier (e.g., "my name is Johnny"), tell them their name
- "what is the next best" or "third best": Reference the previous query about "best" or "highest" and provide the next item in that ranking
- Always check the conversation context FIRST before answering any question""",
                ),
            ]
        )

    def generate_response(
        self,
        classified_query: Any,
        bond_analytics: Dict[str, BondAnalytics],
        bond_scores: Dict[str, BondScore],
        ml_predictions: Dict[str, Any],
        portfolio: Optional[Portfolio] = None,
        yield_forecasts: Optional[Any] = None,
        latest_yields: Optional[Dict[str, float]] = None,
        bond_price_forecasts: Optional[Dict[str, Any]] = None,
        bond_details: Optional[Dict[str, Any]] = None,
        bonds_universe: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        web_search_results: Optional[str] = None,
    ) -> AdvisoryOutput:
        # NEW: Extract focus and detail level from query
        query = getattr(classified_query, "original_query", "") or getattr(
            classified_query, "query", ""
        )
        focus, detail_level = self._extract_focus_from_query(query)

        print(f"\n Query Focus: {focus}")
        print(f" Detail Level: {detail_level}\n")

        # NEW: Filter analytics based on focus
        filtered_analytics = self._filter_analytics_by_focus(
            bond_analytics, focus, detail_level
        )
        """
        Generate appropriate response based on query type
        """
        # Handle both ClassifiedQuery types
        if hasattr(classified_query, "query"):
            # Pydantic model from schemas_v2
            query = classified_query.query
            query_type = classified_query.query_type
            intent = classified_query.intent
        else:
            # Plain Python class from query_classifier
            query = getattr(classified_query, "original_query", "")
            query_type = getattr(classified_query, "query_type", None)
            intent = getattr(classified_query, "intent", None)

        # Get query type value
        if hasattr(query_type, "value"):
            query_type_str = query_type.value
        elif query_type:
            query_type_str = str(query_type)
        else:
            query_type_str = (
                QueryType.ANALYTICS.value
            )  # Default to analytics, not advisory

        # Get intent value
        if hasattr(intent, "value"):
            intent_str = intent.value
        elif intent:
            intent_str = str(intent)
        else:
            intent_str = (
                "custom"  # Default to custom (informational), not recommendation
            )

        # Analyze the actual query text to determine if it's asking for recommendations
        query_lower = query.lower()

        # Keywords that indicate the user wants recommendations/advice
        recommendation_keywords = [
            "recommend",
            "should i",
            "what should",
            "advice",
            "suggest",
            "suggestion",
            "help me choose",
            "which should",
            "what bonds should",
            "what should i",
            "buy",
            "sell",
            "hold",
            "switch",
            "rebalance",
            "strategy",
            "what bonds",
            "which bonds",
            "help me",
            "guide me",
            "tell me what to",
        ]

        # Keywords that indicate the user wants information/analytics (NOT recommendations)
        informational_keywords = [
            "tell me about",
            "what is",
            "what are",
            "show me",
            "tell me",
            "how much",
            "what is the",
            "what are the",
            "list",
            "display",
            "information about",
            "details about",
            "about",
            "explain",
            "describe",
            "give me information",
            "what do you know",
        ]

        # Check if query explicitly asks for recommendations
        asks_for_recommendations = any(
            keyword in query_lower for keyword in recommendation_keywords
        )

        # Check if query is asking for information (not recommendations)
        is_informational = any(
            keyword in query_lower for keyword in informational_keywords
        )

        # Check if intent indicates recommendations are needed
        recommendation_intents = [
            "buy_recommendation",
            "sell_recommendation",
            "switch_bonds",
            "reduce_duration",
            "increase_yield",
            "hedge_volatility",
            "sector_rebalance",
            "barbell_strategy",
        ]
        has_recommendation_intent = intent_str in recommendation_intents

        # Route to advisory if:
        # 1. Query explicitly asks for recommendations OR intent is recommendation type, AND
        # 2. Query type is ADVISORY or intent is a recommendation type, AND
        # 3. If it has informational keywords, it must ALSO have recommendation keywords or intent
        needs_recommendations = (
            (
                asks_for_recommendations or has_recommendation_intent
            )  # Must ask for recommendations or have recommendation intent
            and (
                not is_informational
                or asks_for_recommendations
                or has_recommendation_intent
            )  # If informational, must also have recommendation signal
            and (
                query_type_str == QueryType.ADVISORY.value or has_recommendation_intent
            )
        )

        if needs_recommendations:
            # Dynamically update advisory agent model if needed
            # Note: Advisory agent model should be updated before calling generate_advisory
            # This is handled by the orchestrator

            # Use advisory agent for recommendation queries
            advisory_output = self.advisory_agent.generate_advisory(
                classified_query=classified_query,
                bond_analytics=bond_analytics,
                bond_scores=bond_scores,
                portfolio=portfolio,
                conversation_history=conversation_history,
                web_search_results=web_search_results,  # Pass web search results
            )

            # Format the advisory response for better readability
            return self._format_advisory_response(
                advisory_output, bond_analytics, bond_scores
            )

        # For analytics/informational queries, format a direct response
        return self._generate_analytics_response(
            query=query,
            query_type_str=query_type_str,
            intent_str=intent_str,
            bond_analytics=bond_analytics,
            bond_scores=bond_scores,
            ml_predictions=ml_predictions,
            portfolio=portfolio,
            yield_forecasts=yield_forecasts,
            latest_yields=latest_yields,
            bond_price_forecasts=bond_price_forecasts,
            bond_details=bond_details,
            bonds_universe=bonds_universe,
            conversation_history=conversation_history,
        )

    def _generate_analytics_response(
        self,
        query: str,
        query_type_str: str,
        intent_str: str,
        bond_analytics: Dict[str, BondAnalytics],
        bond_scores: Dict[str, BondScore],
        ml_predictions: Dict[str, Any],
        portfolio: Optional[Portfolio] = None,
        yield_forecasts: Optional[Any] = None,
        latest_yields: Optional[Dict[str, float]] = None,
        bond_price_forecasts: Optional[Dict[str, Any]] = None,
        bond_details: Optional[Dict[str, Any]] = None,
        bonds_universe: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AdvisoryOutput:
        """
        Generate response for analytics/informational queries
        """
        # Filter data based on query (e.g., if asking about TATA bonds, filter to TATA)
        query_lower = query.lower()
        filtered_analytics = self._filter_by_query(bond_analytics, query_lower)
        filtered_scores = self._filter_by_query(bond_scores, query_lower)
        filtered_ml = self._filter_by_query(ml_predictions, query_lower)
        filtered_prices = (
            self._filter_by_query(bond_price_forecasts, query_lower)
            if bond_price_forecasts
            else {}
        )

        # Format analytics data (use filtered data)
        analytics_text = self._format_analytics(
            filtered_analytics if filtered_analytics else bond_analytics
        )
        scores_text = self._format_scores(
            filtered_scores if filtered_scores else bond_scores
        )
        ml_text = self._format_ml_predictions(
            filtered_ml if filtered_ml else ml_predictions
        )
        portfolio_text = self._format_portfolio(portfolio)
        # Use current yields if available (for yield queries), otherwise use forecasts
        if latest_yields:
            yield_text = self._format_current_yields(latest_yields)
        else:
            yield_text = self._format_yield_forecasts(yield_forecasts)
        price_text = self._format_price_forecasts(
            filtered_prices if filtered_prices else bond_price_forecasts
        )
        bond_details_text = self._format_bond_details(bond_details)
        bonds_list_text = (
            self._format_bonds_universe(bonds_universe) if bonds_universe else ""
        )

        # Format conversation context using context manager if available
        conversation_context = ""
        user_context_info = ""

        # Ensure conversation_history is not None and not empty
        if conversation_history is not None and len(conversation_history) > 0:
            # Extract user context (name, budget, preferences)
            try:
                from utils.context_manager import ContextManager

                user_context = ContextManager.extract_user_context(conversation_history)

                # Build user context string
                context_parts = []
                if user_context.get("name"):
                    context_parts.append(f"User's name: {user_context['name']}")
                if user_context.get("budget"):
                    context_parts.append(
                        f"User's budget: Rs. {user_context['budget']:,.0f}"
                    )
                if user_context.get("investment_goals"):
                    context_parts.append(
                        f"Investment goals: {', '.join(user_context['investment_goals'])}"
                    )
                if user_context.get("previous_queries"):
                    context_parts.append(
                        f"Recent queries: {len(user_context['previous_queries'])} previous questions"
                    )
                if user_context.get("recommendations_received"):
                    context_parts.append(
                        f"Previous recommendations: User has received {len(user_context['recommendations_received'])} recommendations"
                    )

                if context_parts:
                    user_context_info = (
                        "User Context:\n" + "\n".join(context_parts) + "\n\n"
                    )
            except Exception as e:
                # If context extraction fails, continue without it
                pass

            # Check if this is a follow-up question
            query_lower = query.lower()
            follow_up_keywords = [
                "this",
                "that",
                "these",
                "those",
                "it",
                "they",
                "how",
                "why",
                "explain",
                "next",
                "best",
                "another",
                "second",
                "third",
                "other",
                "also",
                "more",
                "what about",
                "tell me more",
                "give me",
                "show me",
                "what else",
                "previous",
                "earlier",
                "before",
                "last time",
                "above",
                "mentioned",
                "exact",
                "split",
                "my name",
                "what is my",
            ]
            is_follow_up = any(keyword in query_lower for keyword in follow_up_keywords)

            # Always include more context for better understanding
            if is_follow_up:
                # For follow-up questions, include more context
                recent_messages = conversation_history[
                    -15:
                ]  # Last 15 messages for follow-ups
            else:
                recent_messages = conversation_history[
                    -8:
                ]  # Last 8 messages for regular queries

            context_parts = []
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Truncate very long messages
                if len(content) > 500:
                    content = content[:500] + "..."
                context_parts.append(f"{role.capitalize()}: {content}")
            conversation_context = "\n".join(context_parts)

            # Add a note if it's a follow-up
            if is_follow_up:
                conversation_context = f"IMPORTANT: This appears to be a follow-up question. You MUST reference the previous conversation to understand what the user is asking about. Look at the conversation history below to understand the context.\n\n{conversation_context}"
        else:
            conversation_context = "No previous conversation context."

        # Combine user context and conversation context
        full_context = user_context_info + conversation_context

        # Generate response using LLM
        messages = self.response_prompt.format_messages(
            conversation_context=full_context,
            query=query,
            query_type=query_type_str,
            intent=intent_str,
            analytics_data=analytics_text,
            scores_data=scores_text,
            ml_predictions=ml_text,
            portfolio_data=portfolio_text,
            yield_forecasts=yield_text,
            bond_details=bond_details_text,
            bonds_list=bonds_list_text,
        )

        response = self.llm.invoke(messages)
        summary = response.content if hasattr(response, "content") else str(response)

        return AdvisoryOutput(
            query=query,
            recommendations=[],  # No recommendations for analytics queries
            summary=summary,
            timestamp=datetime.now(),
        )

    def _format_analytics(self, analytics: Dict[str, Any]) -> str:
        """Format analytics for display - now context-aware"""
        if not analytics:
            return "No analytics available."

        lines = ["Bond Analytics:"]

        for isin, bond_data in list(analytics.items()):
            # Handle both dict and Pydantic model
            if isinstance(bond_data, dict):
                name = bond_data.get("name", isin)
                items = bond_data.items()
            else:
                # It's a Pydantic model (BondAnalytics)
                name = getattr(bond_data, "name", isin)
                items = bond_data.__dict__.items()

            lines.append(f"\n{name}:")

            # Format each metric
            for key, value in items:
                if key in ["name", "isin"]:
                    continue  # Skip these, already shown

                # Format value based on type
                if isinstance(value, float):
                    if (
                        "percent" in key
                        or "yield" in key
                        or "return" in key
                        or "ytm" in key
                    ):
                        formatted = f"{value * 100:.2f}%"
                    elif "price" in key or "value" in key:
                        formatted = f"₹{value:.2f}"
                    elif "score" in key:
                        formatted = f"{value:.3f}"
                    else:
                        formatted = f"{value:.2f}"
                elif isinstance(value, (int, str)):
                    formatted = str(value)
                else:
                    formatted = str(value)

                # Pretty name
                display_name = key.replace("_", " ").title()
                lines.append(f"  {display_name}: {formatted}")

        return "\n".join(lines)

    def _format_scores(self, scores: Dict[str, BondScore]) -> str:
        """Format bond scores for LLM"""
        if not scores:
            return "No scoring data available."

        # Sort by total score
        sorted_scores = sorted(
            scores.items(), key=lambda x: x[1].total_score, reverse=True
        )

        lines = ["Bond Scores (sorted by total score):"]
        for isin, score in sorted_scores[:10]:  # Top 10
            lines.append(f"\n{score.name} ({isin}):")
            lines.append(f"  Total Score: {score.total_score:.2f}")
            lines.append(f"  Valuation: {score.valuation_score:.2f}")
            lines.append(f"  Return: {score.return_score:.2f}")
            lines.append(f"  Quality: {score.quality_score:.2f}")
            lines.append(f"  Liquidity: {score.liquidity_score:.2f}")
            lines.append(f"  Rank: {score.rank}")

        return "\n".join(lines)

    def _format_ml_predictions(self, predictions: Dict[str, Any]) -> str:
        """Format ML predictions for LLM"""
        if not predictions:
            return "No ML predictions available."

        lines = ["ML Predictions:"]
        for isin, pred in list(predictions.items())[:10]:
            if isinstance(pred, dict):
                lines.append(f"\n{isin}:")
                lines.append(f"  Expected Return: {pred.get('expected_return', 'N/A')}")
                lines.append(f"  Predicted Price: {pred.get('predicted_price', 'N/A')}")
                lines.append(f"  Confidence: {pred.get('confidence', 'N/A')}")
            else:
                # Assume it's an MLPrediction object
                lines.append(f"\n{isin}:")
                lines.append(
                    f"  Expected Return: {getattr(pred, 'expected_return', 'N/A')}"
                )
                lines.append(
                    f"  Predicted Price: {getattr(pred, 'predicted_price', 'N/A')}"
                )
                lines.append(f"  Confidence: {getattr(pred, 'confidence', 'N/A')}")

        return "\n".join(lines)

    def _format_portfolio(self, portfolio: Optional[Portfolio]) -> str:
        """Format portfolio for LLM"""
        if not portfolio:
            return "No portfolio data available."

        lines = [f"**Portfolio: {portfolio.name}**"]
        lines.append(f"Total Value: ₹{portfolio.total_value:,.2f}")
        if portfolio.cash is not None:
            lines.append(f"Cash: ₹{portfolio.cash:,.2f}")
        if portfolio.duration:
            lines.append(f"Portfolio Duration: {portfolio.duration:.2f} years")
        if portfolio.ytm:
            lines.append(f"Portfolio YTM: {portfolio.ytm:.2%}")

        if not portfolio.positions:
            lines.append("\nNo positions in portfolio.")
            return "\n".join(lines)

        lines.append(f"\n**Bonds in Portfolio ({len(portfolio.positions)} total):**")
        lines.append("")

        # Show all positions (not limited to 10 for "print all bonds" queries)
        for i, pos in enumerate(portfolio.positions, 1):
            lines.append(f"{i}. **{pos.name}** ({pos.isin})")
            lines.append(f"   - Quantity: {pos.quantity:,.0f}")
            lines.append(f"   - Current Price: ₹{pos.current_price:,.2f}")
            lines.append(f"   - Market Value: ₹{pos.market_value:,.2f}")
            if pos.weight:
                lines.append(f"   - Weight: {pos.weight:.2%}")
            if pos.unrealized_pnl is not None:
                pnl_sign = "+" if pos.unrealized_pnl >= 0 else ""
                lines.append(
                    f"   - Unrealized P&L: {pnl_sign}₹{pos.unrealized_pnl:,.2f}"
                )
            lines.append("")

        return "\n".join(lines)

    def _filter_by_query(
        self, data: Dict[str, Any], query_lower: str
    ) -> Optional[Dict[str, Any]]:
        """
        Filter data dictionary based on query keywords
        Returns filtered dict if matches found, None otherwise
        """
        if not data:
            return None

        # Extract potential company/bond names from query
        # Common patterns: "tell me about X bonds", "what is X", "X bonds"
        # Split query and look for capitalized words (likely company names)
        words = query_lower.split()

        # Look for company name patterns (usually before "bond", "bonds", or standalone)
        keywords = []
        for i, word in enumerate(words):
            # If word is "bond" or "bonds", the previous word might be a company name
            if word in ["bond", "bonds"] and i > 0:
                keywords.append(words[i - 1])
            # Also check for common company name patterns
            if word in [
                "tata",
                "hdfc",
                "icici",
                "sbi",
                "axis",
                "reliance",
                "ntpc",
                "pfc",
                "rec",
            ]:
                keywords.append(word)

        # Also check for ISIN patterns
        import re

        isin_pattern = r"\b(INE[A-Z0-9]{9})\b"
        isins = re.findall(isin_pattern, query_lower.upper())
        keywords.extend(isins)

        if not keywords:
            return None  # No specific filter keywords found

        # Filter data based on keywords
        filtered = {}
        for key, value in data.items():
            # Check if key (ISIN) or value contains keywords
            key_lower = str(key).lower()
            value_str = str(value).lower()

            # For BondAnalytics, BondScore, etc., check the name/isin fields
            if hasattr(value, "name"):
                value_name = str(value.name).lower()
            elif hasattr(value, "bond_name"):
                value_name = str(value.bond_name).lower()
            else:
                value_name = value_str

            if hasattr(value, "isin"):
                value_isin = str(value.isin).upper()
            else:
                value_isin = key_lower.upper()

            # Check if any keyword matches
            matches = False
            for keyword in keywords:
                keyword_lower = keyword.lower()
                keyword_upper = keyword.upper()
                if (
                    keyword_lower in key_lower
                    or keyword_lower in value_name
                    or keyword_upper in value_isin
                    or keyword_lower in value_str
                ):
                    matches = True
                    break

            if matches:
                filtered[key] = value

        return filtered if filtered else None

    def _format_current_yields(self, latest_yields: Dict[str, float]) -> str:
        """Format current yields into readable text"""
        if not latest_yields:
            return "No current yield data available."

        lines = ["**Current Government Bond Yields:**\n"]

        # Sort by maturity (handle both "1Y" format and numeric keys)
        def get_maturity_key(key):
            if isinstance(key, str):
                # Extract number from "1Y", "2Y", etc.
                try:
                    return float(key.replace("Y", "").replace("y", ""))
                except:
                    return 0.0
            return float(key)

        sorted_yields = sorted(
            latest_yields.items(), key=lambda x: get_maturity_key(x[0])
        )

        for maturity, yield_val in sorted_yields:
            # Handle percentage format (5.703) or decimal format (0.05703)
            if yield_val > 1:
                # Already in percentage format
                yield_display = yield_val
            else:
                # Convert decimal to percentage
                yield_display = yield_val * 100

            # Format maturity key nicely
            maturity_str = str(maturity)
            if not maturity_str.endswith("Y") and not maturity_str.endswith("y"):
                maturity_str = f"{maturity_str}Y"

            lines.append(f"  {maturity_str}: {yield_display:.3f}%")

        return "\n".join(lines)

    def _format_yield_forecasts(self, yield_forecasts):
        """Format yield forecasts into readable text"""
        if not yield_forecasts:
            return "No yield forecasts available."

        lines = ["**Yield Forecasts:**\n"]

        if isinstance(yield_forecasts, dict):
            for maturity, forecasts in sorted(yield_forecasts.items()):
                #  FIX: Extract the actual yield value from the forecast list
                if isinstance(forecasts, list) and len(forecasts) > 0:
                    last_forecast = forecasts[-1]

                    # Get predicted_yield from the forecast dict
                    if isinstance(last_forecast, dict):
                        yield_val = last_forecast.get("predicted_yield", 0)
                    else:
                        yield_val = 0

                    # Convert to decimal if needed
                    if yield_val > 1:
                        yield_val = yield_val / 100.0

                    lines.append(f"  {maturity}Y: {yield_val:.2%}")
                else:
                    lines.append(f"  {maturity}Y: No forecast available")

        return "\n".join(lines)

    def _format_price_forecasts(self, forecasts: Optional[Dict[str, Any]]) -> str:
        """Format bond price forecasts for LLM"""
        if not forecasts:
            return "No price forecasts available."

        lines = ["Bond Price Forecasts:"]
        for isin, forecast in list(forecasts.items())[:10]:
            if isinstance(forecast, dict):
                lines.append(f"\n{isin}:")
                lines.append(
                    f"  Predicted Price: {forecast.get('predicted_price', 'N/A')}"
                )
                lines.append(
                    f"  Expected Return: {forecast.get('expected_return', 'N/A')}"
                )
            else:
                # Assume it's a BondPriceForecast object
                lines.append(f"\n{isin}:")
                lines.append(
                    f"  Predicted Price: {getattr(forecast, 'predicted_price', 'N/A')}"
                )
                lines.append(
                    f"  Expected Return: {getattr(forecast, 'expected_return', 'N/A')}"
                )

        return "\n".join(lines)

    def _format_bond_details(self, bond_details: Optional[Dict[str, Any]]) -> str:
        """Format bond details (ISIN, coupon, maturity, etc.) for LLM"""
        if not bond_details:
            return "No bond details available."

        lines = ["Bond Details:"]
        for bond_id, details in bond_details.items():
            if details and isinstance(details, dict):
                lines.append(f"\n{bond_id}:")
                for key, value in details.items():
                    if value is not None and value != "":
                        # Format key nicely
                        display_key = key.replace("_", " ").title()
                        lines.append(f"  {display_key}: {value}")

        return "\n".join(lines)

    def _format_bonds_universe(
        self, bonds_universe: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Format bonds universe list for LLM"""
        if not bonds_universe or len(bonds_universe) == 0:
            return "No bonds available."

        lines = [f"**Bonds List ({len(bonds_universe)} bonds):**\n"]

        for i, bond in enumerate(bonds_universe[:50], 1):  # Limit to 50 bonds
            if isinstance(bond, dict):
                symbol = bond.get("symbol", bond.get("isin", "N/A"))
                name = bond.get("name", bond.get("description", "N/A"))
                coupon = bond.get("coupon_rate", bond.get("coupon", 0))
                maturity_date = bond.get("maturity_date", "N/A")
                isin = bond.get("isin", "N/A")

                # Format coupon as percentage if it's a decimal
                if coupon and coupon < 1:
                    coupon_display = f"{coupon * 100:.2f}%"
                elif coupon:
                    coupon_display = f"{coupon:.2f}%"
                else:
                    coupon_display = "N/A"

                lines.append(f"{i}. **{symbol}** ({isin})")
                lines.append(f"   Name: {name}")
                lines.append(f"   Coupon Rate: {coupon_display}")
                lines.append(f"   Maturity Date: {maturity_date}")

                # Add years to maturity if available
                if "years_to_maturity" in bond:
                    lines.append(
                        f"   Years to Maturity: {bond['years_to_maturity']:.2f}"
                    )

        if len(bonds_universe) > 50:
            lines.append(f"\n... and {len(bonds_universe) - 50} more bonds")

        return "\n".join(lines)

    def _extract_focus_from_query(self, query: str) -> tuple[list, str]:
        """
        Quick extraction of what user cares about
        Returns: (focus_metrics, detail_level)
        """
        query_lower = query.lower()
        focus = []

        # Detect focus metrics
        metric_map = {
            "yield": ["yield", "ytm", "income", "coupon"],
            "duration": ["duration", "risk", "sensitivity", "rate"],
            "price": ["price", "value", "cost", "valuation"],
            "return": ["return", "profit", "gain", "performance"],
            "rating": ["rating", "quality", "credit", "safe"],
            "liquidity": ["liquid", "volume", "trade"],
        }

        for metric_type, keywords in metric_map.items():
            if any(kw in query_lower for kw in keywords):
                focus.append(metric_type)

        # Detect detail level
        if any(
            kw in query_lower for kw in ["what is", "what's", "show me", "tell me the"]
        ):
            detail_level = "minimal"  # Just answer the question
        elif any(kw in query_lower for kw in ["detailed", "full", "complete", "all"]):
            detail_level = "detailed"  # Show everything
        else:
            detail_level = "summary"  # Show key info

        # If asking for recommendations, show all
        if any(
            kw in query_lower
            for kw in ["recommend", "buy", "sell", "suggest", "should i"]
        ):
            focus = ["all"]
            detail_level = "detailed"

        # If no specific focus detected, show all
        if not focus:
            focus = ["all"]

        return focus, detail_level

    def _filter_analytics_by_focus(
        self, analytics: Dict[str, BondAnalytics], focus: list, detail_level: str
    ) -> Dict:
        """
        Filter analytics to show only relevant metrics
        """
        if "all" in focus or detail_level == "detailed":
            return analytics  # Show everything

        # Define what metrics belong to each focus area
        focus_metric_map = {
            "yield": [
                "ytm",
                "current_yield",
                "coupon_rate",
                "name",
                "isin",
                "current_price",
            ],
            "duration": [
                "duration",
                "modified_duration",
                "convexity",
                "rate_sensitivity",
                "name",
                "isin",
            ],
            "price": [
                "current_price",
                "fair_value",
                "valuation_gap",
                "last_traded_price",
                "name",
                "isin",
            ],
            "return": [
                "expected_return",
                "predicted_price",
                "ml_confidence",
                "name",
                "isin",
                "current_price",
            ],
            "rating": ["credit_rating", "credit_risk_score", "sector", "name", "isin"],
            "liquidity": [
                "liquidity_score",
                "volume",
                "is_liquid",
                "name",
                "isin",
                "current_price",
            ],
        }

        # Collect all relevant metrics
        relevant_metrics = set(["name", "isin"])  # Always show these
        for focus_area in focus:
            if focus_area in focus_metric_map:
                relevant_metrics.update(focus_metric_map[focus_area])

        # Filter each bond's analytics
        filtered = {}
        for isin, bond_analytics in analytics.items():
            # Convert to dict
            if hasattr(bond_analytics, "model_dump"):
                bond_dict = bond_analytics.model_dump()
            elif hasattr(bond_analytics, "dict"):
                bond_dict = bond_analytics.dict()
            else:
                bond_dict = dict(bond_analytics)

            # Keep only relevant metrics
            filtered_bond = {
                k: v for k, v in bond_dict.items() if k in relevant_metrics
            }

            filtered[isin] = filtered_bond

        # Limit number of bonds for minimal queries
        if detail_level == "minimal":
            filtered = dict(list(filtered.items())[:5])
        elif detail_level == "summary":
            filtered = dict(list(filtered.items())[:10])

        return filtered

    def _format_advisory_response(
        self,
        advisory_output: AdvisoryOutput,
        bond_analytics: Dict[str, BondAnalytics],
        bond_scores: Dict[str, BondScore],
    ) -> AdvisoryOutput:
        """
        Format advisory response for better readability and structure
        Improves the summary and recommendations formatting with clear sections and metrics
        """
        if not advisory_output:
            return advisory_output

        formatted_parts = []

        # Extract recommendations
        recommendations = advisory_output.recommendations or []
        summary = advisory_output.summary or ""

        # If we have recommendations, format them nicely in a structured table-like format
        if recommendations:
            formatted_parts.append("##  Recommended Bonds\n")

            for i, rec in enumerate(recommendations, 1):
                # Get bond details for better formatting
                isin = getattr(rec, "isin", "") or getattr(rec, "bond_identifier", "")
                bond_name = getattr(rec, "bond_name", "") or getattr(
                    rec, "name", "Unknown Bond"
                )
                action = getattr(rec, "action", "BUY").upper()
                quantity = getattr(rec, "quantity", None)
                rationale = getattr(rec, "rationale", "")
                expected_return = getattr(rec, "expected_return", None)
                risk_level = getattr(rec, "risk_level", "")

                # Get additional details from analytics if available
                duration = None
                ytm = None
                current_price = None

                if isin and isin in bond_analytics:
                    analytics = bond_analytics[isin]
                    duration = getattr(analytics, "duration", None) or (
                        analytics.get("duration")
                        if isinstance(analytics, dict)
                        else None
                    )
                    ytm = getattr(analytics, "ytm", None) or (
                        analytics.get("ytm") if isinstance(analytics, dict) else None
                    )
                    current_price = getattr(analytics, "current_price", None) or (
                        analytics.get("current_price")
                        if isinstance(analytics, dict)
                        else None
                    )

                # Format recommendation with clear structure
                formatted_parts.append(f"### {i}. {bond_name}")

                # Key information in a compact format
                info_lines = []
                if isin:
                    info_lines.append(f"**ISIN:** `{isin}`")
                info_lines.append(f"**Action:** {action}")

                # Metrics in a clean format
                metrics_section = []
                if duration is not None:
                    metrics_section.append(f"Duration: **{duration:.1f} years**")
                if ytm is not None:
                    ytm_pct = ytm * 100 if ytm < 1 else ytm
                    metrics_section.append(f"YTM: **{ytm_pct:.2f}%**")
                if current_price is not None:
                    metrics_section.append(f"Price: **₹{current_price:.2f}**")
                if expected_return is not None:
                    ret_pct = (
                        expected_return * 100
                        if expected_return < 1
                        else expected_return
                    )
                    metrics_section.append(f"Expected Return: **{ret_pct:.2f}%**")
                if risk_level:
                    risk_label = (
                        "Low"
                        if risk_level.lower() in ["low", "low risk"]
                        else "Medium"
                        if risk_level.lower() in ["medium", "medium risk"]
                        else "High"
                    )
                    metrics_section.append(f"Risk ({risk_label}): **{risk_level}**")
                if quantity:
                    metrics_section.append(f"Quantity: **{quantity:,.0f} units**")

                # Combine info and metrics
                if info_lines:
                    formatted_parts.append(" | ".join(info_lines))
                if metrics_section:
                    formatted_parts.append("\n".join(metrics_section))

                # Add rationale with better formatting
                if rationale:
                    # Clean up rationale - remove redundant phrases
                    clean_rationale = rationale.strip()
                    if not clean_rationale.endswith("."):
                        clean_rationale += "."
                    formatted_parts.append(f"\n**Why this bond:** {clean_rationale}")

                formatted_parts.append("")  # Empty line between recommendations

        # Format summary section - extract and enhance market context
        if summary:
            # Check if summary already has structured formatting
            has_structured_format = "##" in summary or "###" in summary or "" in summary

            if recommendations and not has_structured_format:
                # Summary is plain text, add our formatted recommendations at the top
                if formatted_parts:
                    formatted_summary = (
                        "\n".join(formatted_parts)
                        + "\n\n---\n\n## Market Analysis\n\n"
                        + summary
                    )
                else:
                    formatted_summary = summary
            elif recommendations and has_structured_format:
                # Summary already has some formatting, prepend our recommendations if not present
                if "" not in summary and "Recommended" not in summary:
                    formatted_summary = (
                        "\n".join(formatted_parts) + "\n\n---\n\n" + summary
                    )
                else:
                    # Recommendations already in summary, just ensure proper formatting
                    formatted_summary = summary
            else:
                # No recommendations but has summary
                formatted_summary = summary
        else:
            # No summary, use just the formatted recommendations
            if formatted_parts:
                formatted_summary = "\n".join(formatted_parts)
            else:
                formatted_summary = "No recommendations available at this time based on current market conditions."

        # Clean up excessive newlines (max 2 consecutive newlines)
        import re

        formatted_summary = re.sub(r"\n{3,}", "\n\n", formatted_summary).strip()

        # Create new AdvisoryOutput with formatted summary
        return AdvisoryOutput(
            query=advisory_output.query,
            recommendations=advisory_output.recommendations,
            summary=formatted_summary,
            portfolio_changes=advisory_output.portfolio_changes,
            timestamp=advisory_output.timestamp,
        )


def create_response_agent(
    api_key: str,
    model: str = "gpt-4-turbo-preview",
    advisory_agent: Optional[AdvisoryAgent] = None,
    web_search_tool: Optional[Any] = None,
) -> ResponseAgent:
    """Factory function

    Args:
        api_key: OpenAI API key
        model: Model name to use
        advisory_agent: Optional pre-created advisory agent
        web_search_tool: Optional web search tool to pass to advisory agent if creating one
    """
    llm = ChatOpenAI(model=model, temperature=0.0, api_key=api_key)

    # Create advisory agent if not provided
    if advisory_agent is None:
        from .advisory import create_advisory_agent

        advisory_agent = create_advisory_agent(
            api_key, model, web_search_tool=web_search_tool
        )

    return ResponseAgent(llm, advisory_agent)
