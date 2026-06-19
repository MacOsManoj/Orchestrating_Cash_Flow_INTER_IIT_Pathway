"""
Query Classifier Agent V2
Enhanced with better intent detection and filter extraction
Now supports routing non-bond queries to general LLM or web search
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List, Optional
from enum import Enum
import json
import re
from dotenv import load_dotenv

load_dotenv()


class QueryIntent(str, Enum):
    BUY_RECOMMENDATION = "buy_recommendation"
    SELL_RECOMMENDATION = "sell_recommendation"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    REDUCE_DURATION = "reduce_duration"
    INCREASE_YIELD = "increase_yield"
    HEDGE_VOLATILITY = "hedge_volatility"
    SECTOR_REBALANCE = "sector_rebalance"
    BARBELL_STRATEGY = "barbell_strategy"
    SWITCH_BONDS = "switch_bonds"
    EXPLAIN_RECOMMENDATION = "explain_recommendation"
    MARKET_OUTLOOK = "market_outlook"
    CREDIT_ANALYSIS = "credit_analysis"
    FORECAST_PRICES = "forecast_prices"


class ClassifiedQuery:
    def __init__(self, **kwargs):
        self.original_query = kwargs.get("original_query", "")
        self.is_bond_related = kwargs.get("is_bond_related", True)
        self.non_bond_routing = kwargs.get("non_bond_routing", None)
        self.intent = kwargs.get("intent", QueryIntent.BUY_RECOMMENDATION)
        self.sub_intent = kwargs.get("sub_intent", "")
        self.filters = kwargs.get("filters", {})
        self.constraints = kwargs.get("constraints", {})
        self.entities = kwargs.get("entities", [])
        self.confidence = kwargs.get("confidence", 0.8)
        self.reasoning = kwargs.get("reasoning", "")
        self.needs_news = kwargs.get(
            "needs_news", False
        )  # Flag for news-related queries


class QueryClassifierAgent:
    """
    Classifies user queries and extracts structured information
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

        self.classification_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at understanding queries and routing them appropriately.

FIRST, determine if the query is bond-related or not.

Bond-related keywords include: bond, yield, duration, credit, rating, portfolio, invest, buy, sell, hold, isin, maturity, coupon, g-sec, corporate, psu, sovereign, interest rate, spread, liquidity, risk, return, recommendation, trading, fixed income, debt securities.

If the query is NOT bond-related:
- Determine if it needs web search (factual/current information, news, specific data) or general LLM (conversational, general knowledge, explanations)
- Set "is_bond_related": false
- Set "non_bond_routing": "web_search" or "general_llm"

If the query IS bond-related:
- Classify the intent and extract structured information
- Set "is_bond_related": true
- Set "non_bond_routing": null

Available Bond Intents:
- buy_recommendation: User wants bond recommendations to buy
- sell_recommendation: User wants to sell bonds
- portfolio_analysis: Analyze current portfolio
- reduce_duration: Reduce interest rate sensitivity
- increase_yield: Find higher yielding bonds
- hedge_volatility: Hedge against rate volatility
- sector_rebalance: Rebalance sector exposure
- barbell_strategy: Create barbell strategy
- switch_bonds: Switch from one bond to another
- explain_recommendation: Explain previous recommendation
- market_outlook: Get market view
- credit_analysis: Analyze credit quality (ONLY use if query explicitly asks about credit risk, default ratings, creditworthiness, or credit analysis)
- forecast_prices: Forecast bond prices

IMPORTANT: For comparison queries (e.g., "compare bond A vs B", "which is better X or Y"), use intent based on what they're comparing:
- If comparing to decide what to buy: use "buy_recommendation"
- If comparing existing bonds: use "portfolio_analysis" or "switch_bonds"
- If just informational comparison: use "buy_recommendation" (default)

Do NOT use "credit_analysis" unless the query explicitly asks about credit risk, ratings, or creditworthiness analysis.

Extract (for bond queries):
1. Primary intent
2. Filters: sectors, ratings, maturities, bond types
3. Constraints: preserve_yield, maintain_liquidity, max_concentration, etc.
4. Entities: ISINs, company names, bond names, state names (e.g., "Telangana", "Maharashtra")
5. Needs news: Set "needs_news": true if query asks for news, latest updates, recent developments, or current events

Output JSON:
{{
    "is_bond_related": true/false,
    "non_bond_routing": "web_search" | "general_llm" | null,
    "intent": "buy_recommendation" (only if bond-related),
    "sub_intent": "defensive bonds given rate volatility",
    "filters": {{
        "min_rating": "AA",
        "sectors": ["Sovereign", "PSU_Energy"],
        "max_duration": 5.0,
        "min_liquidity": 0.6
    }},
    "constraints": {{
        "preserve_yield": true,
        "maintain_sector_diversity": true
    }},
    "entities": ["HDFC Bank", "INE001A01036", "Telangana"],
    "confidence": 0.9,
    "reasoning": "User wants safe bonds due to rate concerns",
    "needs_news": true/false
}}""",
                ),
                (
                    "user",
                    """Query: {query}

User Profile:
- Risk Level: {risk_level}
- Preferred Sectors: {preferred_sectors}
- Min Rating: {min_rating}

Classify this query and determine if it's bond-related. If not, route it appropriately.""",
                ),
            ]
        )

    def classify(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ClassifiedQuery:
        """
        Classify user query
        """
        # Default profile
        if user_profile is None:
            user_profile = {
                "risk_level": "moderate",
                "preferred_sectors": [],
                "min_rating": "A",
            }

        # Format conversation history for context
        context_text = ""
        if conversation_history:
            # Get last few messages for context
            recent_messages = conversation_history[-5:]  # Last 5 messages
            context_parts = ["Previous conversation:"]
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_parts.append(f"{role.capitalize()}: {content}")
            context_text = "\n".join(context_parts)

        # Enhance query with context if it's a follow-up question
        enhanced_query = query
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
        ]
        if conversation_history and any(
            keyword in query.lower() for keyword in follow_up_keywords
        ):
            # It's likely a follow-up question, include context
            enhanced_query = f"{context_text}\n\nCurrent query: {query}"

        # Invoke LLM
        messages = self.classification_prompt.format_messages(
            query=enhanced_query,
            risk_level=user_profile.get("risk_level", "moderate"),
            preferred_sectors=user_profile.get("preferred_sectors", []),
            min_rating=user_profile.get("min_rating", "A"),
        )

        response = self.llm.invoke(messages)

        # Parse JSON
        try:
            content = response.content
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            result = json.loads(content)
        except json.JSONDecodeError:
            # Fallback to keyword-based classification
            result = self._keyword_classification(query, user_profile)

        # Normalize and validate
        result = self._normalize_classification(result)

        # Always include the original query
        result["original_query"] = query

        return ClassifiedQuery(**result)

    def _keyword_classification(
        self, query: str, user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback keyword-based classification
        """
        query_lower = query.lower()

        # First check if it's bond-related
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
            "trading",
            "fixed income",
            "debt securities",
            "fixed deposit",
            "fd",
            "government securities",
            "treasury",
        ]

        is_bond_related = any(keyword in query_lower for keyword in bond_keywords)

        if not is_bond_related:
            # Determine routing for non-bond queries
            # Web search for: current events, news, specific facts, recent data
            web_search_keywords = [
                "what is",
                "who is",
                "when did",
                "where is",
                "how many",
                "current",
                "latest",
                "recent",
                "news",
                "today",
                "now",
                "price of",
                "stock price",
                "weather",
                "time",
                "date",
            ]

            needs_web_search = any(
                keyword in query_lower for keyword in web_search_keywords
            )
            non_bond_routing = "web_search" if needs_web_search else "general_llm"

            return {
                "is_bond_related": False,
                "non_bond_routing": non_bond_routing,
                "intent": QueryIntent.BUY_RECOMMENDATION,  # Default, won't be used
                "sub_intent": "",
                "filters": {},
                "constraints": {},
                "entities": [],
                "confidence": 0.7,
                "reasoning": f"Non-bond query routed to {non_bond_routing}",
            }

        # Detect intent for bond queries
        # Check for comparison queries first (should be treated as buy_recommendation or switch_bonds)
        is_comparison = any(
            kw in query_lower
            for kw in [
                "compare",
                "comparison",
                "vs",
                "versus",
                "difference between",
                "which is better",
                "which bond is better",
            ]
        )

        if any(
            kw in query_lower for kw in ["explain", "why", "reasoning", "rationale"]
        ):
            intent = QueryIntent.EXPLAIN_RECOMMENDATION
        elif is_comparison:
            # Comparison queries: if comparing to decide what to buy, use buy_recommendation
            # If comparing existing bonds, use switch_bonds
            if any(kw in query_lower for kw in ["switch", "replace", "alternative"]):
                intent = QueryIntent.SWITCH_BONDS
            else:
                intent = QueryIntent.BUY_RECOMMENDATION  # Default for comparisons
        elif any(
            kw in query_lower
            for kw in [
                "reduce duration",
                "lower duration",
                "rate sensitivity",
                "reduce my portfolio duration",
                "reduce portfolio duration",
                "decrease duration",
                "shorten duration",
                "reduce interest rate risk",
                "reduce rate risk",
                "lower portfolio duration",
                "short duration bonds",
            ]
        ) or ("reduce" in query_lower and "duration" in query_lower):
            intent = QueryIntent.REDUCE_DURATION
        elif any(
            kw in query_lower
            for kw in ["high yield", "increase yield", "better return"]
        ):
            intent = QueryIntent.INCREASE_YIELD
        elif any(kw in query_lower for kw in ["hedge", "volatility", "protect"]):
            intent = QueryIntent.HEDGE_VOLATILITY
        elif any(
            kw in query_lower for kw in ["rebalance", "diversify", "sector exposure"]
        ):
            intent = QueryIntent.SECTOR_REBALANCE
        elif any(kw in query_lower for kw in ["barbell", "short and long"]):
            intent = QueryIntent.BARBELL_STRATEGY
        elif any(kw in query_lower for kw in ["switch", "replace", "alternative"]):
            intent = QueryIntent.SWITCH_BONDS
        elif any(kw in query_lower for kw in ["sell", "exit"]):
            intent = QueryIntent.SELL_RECOMMENDATION
        elif any(
            kw in query_lower for kw in ["forecast", "predict", "price prediction"]
        ):
            intent = QueryIntent.FORECAST_PRICES
        elif any(
            kw in query_lower for kw in ["portfolio", "my bonds", "holdings", "my"]
        ):
            intent = QueryIntent.PORTFOLIO_ANALYSIS
        elif any(
            kw in query_lower
            for kw in [
                "credit risk",
                "creditworthiness",
                "credit quality",
                "default risk",
                "credit analysis",
            ]
        ):
            # Only use credit_analysis if explicitly asking about credit
            intent = QueryIntent.CREDIT_ANALYSIS
        else:
            intent = QueryIntent.BUY_RECOMMENDATION

        # Extract filters
        filters = {}

        # Rating
        rating_match = re.search(r"(AAA|AA\+|AA|A\+|A|BBB)", query, re.IGNORECASE)
        if rating_match:
            filters["min_rating"] = rating_match.group(1).upper()
        elif "safe" in query_lower or "defensive" in query_lower:
            filters["min_rating"] = "AA"

        # Duration
        if "short" in query_lower or "low duration" in query_lower:
            filters["max_duration"] = 3.0
        elif "long" in query_lower or "high duration" in query_lower:
            filters["min_duration"] = 7.0

        # Sectors
        sectors = []
        if (
            "government" in query_lower
            or "sovereign" in query_lower
            or "g-sec" in query_lower
        ):
            sectors.append("Sovereign")
        if "psu" in query_lower:
            sectors.append("PSU_Energy")
        if "corporate" in query_lower:
            sectors.append("Corporate")
        if "financial" in query_lower or "bank" in query_lower:
            sectors.append("Financial")
        if sectors:
            filters["sectors"] = sectors

        # Yield
        if "high yield" in query_lower:
            filters["min_yield"] = 7.5

        # Constraints
        constraints = {}
        if "maintain yield" in query_lower or "preserve yield" in query_lower:
            constraints["preserve_yield"] = True
        if "liquid" in query_lower:
            constraints["maintain_liquidity"] = True

        # Extract entities
        entities = self._extract_entities(query)

        # Check if query needs news
        news_keywords = [
            "news",
            "latest",
            "recent",
            "update",
            "current",
            "today",
            "breaking",
            "announcement",
            "developments",
        ]
        needs_news = any(kw in query_lower for kw in news_keywords)

        return {
            "is_bond_related": True,
            "non_bond_routing": None,
            "intent": intent,
            "sub_intent": query[:100],
            "filters": filters,
            "constraints": constraints,
            "entities": entities,
            "confidence": 0.6,
            "reasoning": "Keyword-based classification",
            "needs_news": needs_news,
        }

    def _extract_entities(self, query: str) -> List[str]:
        """Extract ISINs and company names"""
        entities = []

        # Extract ISINs (format: INE123A01012)
        isin_pattern = r"\b(INE[A-Z0-9]{9})\b"
        isins = re.findall(isin_pattern, query)
        entities.extend(isins)

        # Extract common company names
        companies = [
            "HDFC Bank",
            "ICICI Bank",
            "SBI",
            "NTPC",
            "PFC",
            "REC",
            "L&T",
            "Reliance",
            "Tata",
            "Adani",
            "Bharti Airtel",
            "Power Finance",
            "Rural Electrification",
        ]

        for company in companies:
            if company.lower() in query.lower():
                entities.append(company)

        # Extract Indian state names (for state bonds)
        indian_states = [
            "Andhra Pradesh",
            "Arunachal Pradesh",
            "Assam",
            "Bihar",
            "Chhattisgarh",
            "Goa",
            "Gujarat",
            "Haryana",
            "Himachal Pradesh",
            "Jharkhand",
            "Karnataka",
            "Kerala",
            "Madhya Pradesh",
            "Maharashtra",
            "Manipur",
            "Meghalaya",
            "Mizoram",
            "Nagaland",
            "Odisha",
            "Punjab",
            "Rajasthan",
            "Sikkim",
            "Tamil Nadu",
            "Telangana",
            "Tripura",
            "Uttar Pradesh",
            "Uttarakhand",
            "West Bengal",
            "Delhi",
            "Puducherry",
        ]

        query_lower = query.lower()
        for state in indian_states:
            if state.lower() in query_lower:
                entities.append(state)

        return entities

    def _normalize_classification(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate classification result"""

        # Ensure is_bond_related is boolean
        result["is_bond_related"] = result.get("is_bond_related", True)

        # Set non_bond_routing only if not bond-related
        if not result.get("is_bond_related", True):
            non_bond_routing = result.get("non_bond_routing", "general_llm")
            if non_bond_routing not in ["web_search", "general_llm"]:
                non_bond_routing = "general_llm"
            result["non_bond_routing"] = non_bond_routing
        else:
            result["non_bond_routing"] = None

        # Ensure intent is valid (only for bond queries)
        if result.get("is_bond_related", True):
            try:
                result["intent"] = QueryIntent(
                    result.get("intent", "buy_recommendation")
                )
            except ValueError:
                result["intent"] = QueryIntent.BUY_RECOMMENDATION
        else:
            result["intent"] = None

        # Ensure filters is dict
        if not isinstance(result.get("filters"), dict):
            result["filters"] = {}

        # Ensure constraints is dict
        if not isinstance(result.get("constraints"), dict):
            result["constraints"] = {}

        # Ensure entities is list
        if not isinstance(result.get("entities"), list):
            result["entities"] = []

        # Ensure confidence is float
        try:
            result["confidence"] = float(result.get("confidence", 0.8))
        except (ValueError, TypeError):
            result["confidence"] = 0.8

        # Ensure reasoning is always a string (required by Pydantic schema)
        reasoning = result.get("reasoning")
        if reasoning is None or not isinstance(reasoning, str):
            result["reasoning"] = ""

        # Ensure needs_news is boolean
        result["needs_news"] = bool(result.get("needs_news", False))

        return result


def create_query_classifier(
    api_key: str, model: str = "gpt-4-turbo-preview"
) -> QueryClassifierAgent:
    """Factory function"""
    llm = ChatOpenAI(model=model, temperature=0.0, api_key=api_key)
    return QueryClassifierAgent(llm)
