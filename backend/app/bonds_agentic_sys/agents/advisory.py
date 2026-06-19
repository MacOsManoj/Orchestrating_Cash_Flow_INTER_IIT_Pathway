"""
Advisory Agent
Generates trade recommendations based on query intent and analytics
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional, Any
import json
import asyncio
import concurrent.futures
from dotenv import load_dotenv
load_dotenv()


import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas_v2 import (
    BondAnalytics,
    BondScore,
    Portfolio,
    TradeRecommendation,
    AdvisoryOutput,
    Signal,
)
from .query_classifier import ClassifiedQuery
from utils import optimal_barbell_weights, classify_duration_bucket


class AdvisoryAgent:
    """
    Generates intelligent trade recommendations based on user intent
    """

    def __init__(self, llm: ChatOpenAI, web_search_tool: Optional[Any] = None):
        self.llm = llm
        self.web_search_tool = web_search_tool

        self.advisory_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a senior fixed income portfolio manager providing actionable trade recommendations.

Your job is to:
1. Understand the user's intent and constraints
2. Analyze the scored bonds and portfolio
3. Use real-time market intelligence (web search + news) when provided to make better recommendations
4. Generate specific BUY/SELL/HOLD/SWITCH recommendations
5. Provide clear rationale for each recommendation

Guidelines:
- Be specific: recommend exact bonds with quantities and prices
- Consider portfolio impact: sector concentration, duration, yield
- Respect constraints: user risk profile, liquidity needs, rating requirements
- For SWITCH recommendations, suggest specific replacements
- Limit to top 5-10 recommendations
- Provide expected returns and risk scores
- If real-time market intelligence is provided, incorporate relevant market information, news, or trends into your recommendations

Output format:
{{
    "recommendations": [
        {{
            "action": "BUY" | "SELL" | "HOLD" | "SWITCH",
            "isin": "INE123A01012",
            "name": "Bond Name",
            "quantity": 1000000,
            "target_price": 98.50,
            "stop_loss": 96.00,
            "switch_to_isin": "INE456B01013",  // only for SWITCH
            "switch_to_name": "Replacement Bond",
            "rationale": "Specific reason",
            "expected_return": 0.85,
            "risk_score": 0.25,
            "confidence": 0.80
        }}
    ],
    "summary": "Overall portfolio strategy explanation",
    "portfolio_changes": {{
        "expected_duration_change": -1.2,
        "expected_yield_change": 0.15,
        "sector_rebalancing": {{"Financial": -5, "Infrastructure": +5}}
    }}
}}
""",
                ),
                (
                    "user",
                    """Previous Conversation Context:
{conversation_context}

User Query: {query}
Intent: {intent}
Constraints: {constraints}

Top Scored Bonds:
{top_bonds}

Portfolio (if any):
{portfolio}

Portfolio Analytics:
{portfolio_analytics}

{realtime_info_context}

Generate recommendations.""",
                ),
            ]
        )

    def _should_use_realtime_info(
        self,
        classified_query: ClassifiedQuery,
        bond_analytics: Dict[str, BondAnalytics],
        bond_scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio] = None,
        realtime_info: Optional[str] = None,
    ) -> str:
        """
        Decide whether to use formatted real-time info (web search + news) provided by orchestrator
        Returns the formatted context if it should be used, empty string otherwise
        """
        # If no real-time info provided, return empty
        if not realtime_info:
            return ""

        # Get query text
        query_text = getattr(classified_query, "query", None) or getattr(
            classified_query, "original_query", ""
        )
        query_lower = query_text.lower() if query_text else ""

        # Keywords that suggest real-time info would be valuable
        valuable_keywords = [
            "current",
            "recent",
            "latest",
            "today",
            "now",
            "news",
            "update",
            "trend",
            "market",
            "economic",
            "policy",
            "rbi",
            "rate",
            "inflation",
            "forecast",
            "outlook",
            "expectation",
            "should i",
            "what should",
            "when should",
            "is it a good time",
            "market conditions",
            "macro",
            "gdp",
            "growth",
            "recession",
            "volatility",
            "uncertainty",
            "breaking",
            "hypothetical",
            "if",
            "what if",
            "scenario",
        ]

        # Check if query contains keywords suggesting real-time info would be valuable
        needs_current_info = any(
            keyword in query_lower for keyword in valuable_keywords
        )

        # Check if we have limited bond data (real-time info can help)
        has_limited_data = len(bond_analytics) < 5 or len(bond_scores) < 5

        # Check if query is about market conditions or economic factors
        market_related = any(
            term in query_lower
            for term in [
                "market",
                "economic",
                "macro",
                "policy",
                "rbi",
                "fed",
                "inflation",
                "gdp",
                "growth",
                "recession",
                "volatility",
                "uncertainty",
            ]
        )

        # Use real-time info if:
        # 1. Query suggests need for current information, OR
        # 2. We have limited data and query is market-related, OR
        # 3. Real-time info contains "REAL-TIME MARKET INTELLIGENCE" (indicates processed info)
        should_use = (
            needs_current_info
            or (has_limited_data and market_related)
            or "REAL-TIME MARKET INTELLIGENCE" in realtime_info
        )

        if should_use:
            print(f"   Advisory agent using real-time market intelligence")
            return realtime_info
        else:
            print(
                f"    Advisory agent skipping real-time info (not needed for this query)"
            )
            return ""

    def _start_web_search_background(
        self,
        classified_query: ClassifiedQuery,
        bond_analytics: Dict[str, BondAnalytics],
        portfolio: Optional[Portfolio] = None,
    ) -> Optional[Any]:
        """
        Start web search in background thread (non-blocking)
        Returns a Future object that can be checked later
        """
        import concurrent.futures
        def run_search():
            """Run async web search in new event loop"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(
                    self._perform_web_search(
                        classified_query, bond_analytics, portfolio
                    )
                )
            except Exception as e:
                print(f"    Background web search error: {e}")
                return None
            finally:
                new_loop.close()
        # Submit to thread pool executor (non-blocking)
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_search)
        # Don't wait for result, return future immediately
        return future

    def _get_web_search_result(
        self, web_search_future: Optional[Any], timeout: float = 2.0
    ) -> str:
        """
        Try to get web search result with timeout
        Returns empty string if not ready or failed
        """
        if web_search_future is None:
            return ""
        try:
            # Try to get result with short timeout
            result = web_search_future.result(timeout=timeout)
            return result or ""
        except concurrent.futures.TimeoutError:
            # Web search taking too long, proceed without it
            print(f"  ⚡ Web search timeout ({timeout}s), proceeding without it")
            return ""
        except Exception as e:
            # Web search failed, proceed without it
            print(f"    Web search failed: {e}, proceeding without it")
            return ""
    async def _perform_web_search(
        self,
        classified_query: ClassifiedQuery,
        bond_analytics: Dict[str, BondAnalytics],
        portfolio: Optional[Portfolio] = None,
    ) -> Optional[str]:
        """
        Perform web search to gather additional context for recommendations
        """
        if not self.web_search_tool:
            return None

        try:
            # Get query text
            query_text = getattr(classified_query, "query", None) or getattr(
                classified_query, "original_query", ""
            )

            # Build search query
            search_queries = []

            # Add market context queries
            if portfolio:
                # Search for portfolio-related market conditions
                sectors = set()
                for pos in portfolio.positions:
                    if pos.isin in bond_analytics:
                        sector = str(bond_analytics[pos.isin].sector)
                        sectors.add(sector)

                if sectors:
                    sector_str = " ".join(list(sectors)[:2])  # Limit to 2 sectors
                    search_queries.append(f"{sector_str} bonds market outlook 2024")

            # Add general market query based on user query
            if query_text:
                # Extract key terms from user query
                query_lower = query_text.lower()
                if any(term in query_lower for term in ["duration", "yield", "rate"]):
                    search_queries.append(
                        "Indian bond market interest rate outlook 2024"
                    )
                elif any(term in query_lower for term in ["sector", "industry"]):
                    search_queries.append("Indian corporate bonds sector analysis 2024")
                else:
                    search_queries.append(f"Indian bond market {query_text[:50]}")

            # Default market query
            if not search_queries:
                search_queries.append("Indian bond market outlook 2024")

            # Perform search with the most relevant query
            search_query = search_queries[0]
            print(f"   Advisory agent performing web search: {search_query}")

            result = await self.web_search_tool.search(
                query=search_query, num_results=5
            )

            if result.success and result.data:
                # Format search results for context
                formatted_results = []
                for item in result.data[:3]:  # Use top 3 results
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    if title or snippet:
                        formatted_results.append(f"- {title}: {snippet}")

                if formatted_results:
                    return "Additional Market Context (from web search):\n" + "\n".join(
                        formatted_results
                    )

            return None

        except Exception as e:
            print(f"    Web search error in advisory agent: {e}")
            return None

    def generate_advisory(
        self,
        classified_query: ClassifiedQuery,
        bond_analytics: Dict[str, BondAnalytics],
        bond_scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        web_search_results: Optional[str] = None,
    ) -> AdvisoryOutput:
        """
        Generate trade recommendations based on intent
        Web search results are provided from orchestrator, advisory agent decides whether to use them
        """
        # Decide whether to use formatted real-time info (web search + news processed by real-time info agent)
        realtime_context = self._should_use_realtime_info(
            classified_query, bond_analytics, bond_scores, portfolio, web_search_results
        )

        # Generate recommendations immediately
        # Get intent value (handle both enum and string)
        intent = classified_query.intent
        if hasattr(intent, "value"):
            intent = intent.value
        intent = str(intent)

        # Route to appropriate strategy
        if intent == "reduce_duration":
            recommendations = self._reduce_duration_strategy(
                classified_query, bond_analytics, bond_scores, portfolio
            )
        elif intent == "increase_yield":
            recommendations = self._increase_yield_strategy(
                classified_query, bond_analytics, bond_scores, portfolio
            )
        elif intent == "sector_rebalance":
            recommendations = self._sector_rebalance_strategy(
                classified_query, bond_analytics, bond_scores, portfolio
            )
        elif intent == "barbell_strategy":
            recommendations = self._barbell_strategy(
                classified_query, bond_analytics, bond_scores
            )
        elif intent == "hedge_volatility":
            recommendations = self._hedge_strategy(
                classified_query, bond_analytics, bond_scores, portfolio
            )
        else:
            # Default: buy recommendations
            recommendations = self._buy_recommendation_strategy(
                classified_query, bond_analytics, bond_scores, portfolio
            )
        # Calculate portfolio changes
        portfolio_changes = self._calculate_portfolio_impact(
            recommendations, bond_analytics, portfolio
        )

        # Generate summary using LLM (real-time context included if decided to use)
        summary = self._generate_summary(
            classified_query,
            recommendations,
            portfolio_changes,
            conversation_history,
            realtime_context,
        )

        # Get query text (handle both schemas)
        query_text = getattr(classified_query, "query", None) or getattr(
            classified_query, "original_query", ""
        )

        print(f"\n{'=' * 80}")
        print(f"ADVISORY RECOMMENDATIONS BEING GENERATED")
        print(f"{'=' * 80}")

        for idx, rec in enumerate(recommendations, 1):
            print(f"\n Recommendation {idx}:")
            print(f"   Action: {rec.action}")
            print(f"   ISIN: {rec.isin}")
            print(f"   Name: {rec.name}")
            print(f"   Expected Return: {rec.expected_return * 100:.2f}%")
            print(f"   Confidence: {rec.confidence * 100:.1f}%")
            print(f"   Risk Score: {rec.risk_score}")
            print(f"   Rationale: {rec.rationale[:100]}...")

        print(f"{'=' * 80}\n")

        return AdvisoryOutput(
            query=query_text,
            recommendations=recommendations,
            summary=summary,
            portfolio_changes=portfolio_changes,
        )

    def _reduce_duration_strategy(
        self,
        query: ClassifiedQuery,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio],
    ) -> List[TradeRecommendation]:
        """
        Strategy to reduce portfolio duration while preserving yield
        """
        recommendations = []

        # Always recommend buying low duration bonds (even if portfolio exists)
        buy_recommendations = self._buy_low_duration_bonds(analytics, scores, query)
        recommendations.extend(buy_recommendations)

        if not portfolio:
            return recommendations

        # If portfolio exists, also identify high duration bonds to sell/switch
        # Identify high duration bonds to sell (duration > 5 years or rate sensitive)
        high_duration_positions = []
        for pos in portfolio.positions:
            if pos.isin in analytics:
                bond = analytics[pos.isin]
                # Consider bonds with duration > 5 years or explicitly rate sensitive
                if bond.duration > 5.0 or (
                    hasattr(bond, "is_rate_sensitive") and bond.is_rate_sensitive
                ):
                    high_duration_positions.append(pos)

        # Sort by duration (highest first) or negative expected return
        high_duration_positions.sort(
            key=lambda p: (
                analytics[p.isin].duration,
                -analytics[p.isin].expected_return,
            ),
            reverse=True,
        )

        # Recommend selling/switching worst performers (top 3-5)
        for pos in high_duration_positions[:5]:
            bond = analytics[pos.isin]

            # Find replacement with lower duration
            replacement = self._find_replacement_bond(
                original=bond,
                analytics=analytics,
                scores=scores,
                criteria={"max_duration": 3.0, "preserve_yield": True},
            )

            if replacement:
                # Use score if available, otherwise use default confidence
                replacement_score = scores.get(replacement.isin)
                confidence = replacement_score.total_score if replacement_score else 0.7

                recommendations.append(
                    TradeRecommendation(
                        action="SWITCH",
                        isin=pos.isin,
                        name=bond.name,
                        quantity=pos.quantity,
                        switch_to_isin=replacement.isin,
                        switch_to_name=replacement.name,
                        rationale=f"Reduce duration from {bond.duration:.1f}Y to {replacement.duration:.1f}Y while maintaining yield at {replacement.ytm:.2f}%",
                        expected_return=replacement.expected_return,
                        risk_score=replacement.credit_risk_score,
                        confidence=confidence,
                    )
                )
            else:
                # Just sell if no good replacement
                recommendations.append(
                    TradeRecommendation(
                        action="SELL",
                        isin=pos.isin,
                        name=bond.name,
                        quantity=pos.quantity,
                        rationale=f"High duration ({bond.duration:.1f}Y) bond. Consider replacing with shorter duration bonds to reduce rate sensitivity.",
                        expected_return=bond.expected_return,
                        risk_score=bond.credit_risk_score,
                        confidence=0.7,
                    )
                )

        return recommendations

    def _increase_yield_strategy(
        self,
        query: ClassifiedQuery,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio],
    ) -> List[TradeRecommendation]:
        """
        Strategy to increase portfolio yield
        """
        from datetime import datetime

        # Extract query text to check for maturity year
        query_text = getattr(query, "query", "") or getattr(query, "original_query", "")
        query_lower = query_text.lower() if query_text else ""

        # Check if query specifies a maturity year (e.g., "2028", "2029")
        target_year = None
        for year in [
            "2025",
            "2026",
            "2027",
            "2028",
            "2029",
            "2030",
            "2031",
            "2032",
            "2033",
            "2034",
            "2035",
        ]:
            if year in query_lower:
                target_year = int(year)
                break

        # Find high yield bonds with acceptable risk
        # Lower threshold from 7.5% to 6.0% to match current market conditions
        min_ytm = 6.0
        high_yield_bonds = []

        for isin in scores:
            if isin not in analytics:
                continue

            bond = analytics[isin]
            score = scores[isin]

            # Filter by YTM and score
            if bond.ytm < min_ytm or score.total_score < 0.1:
                continue

            # Filter by maturity year if specified
            if target_year:
                try:
                    maturity_date = datetime.strptime(bond.maturity_date, "%Y-%m-%d")
                    if maturity_date.year != target_year:
                        continue
                except:
                    # If we can't parse maturity date, skip this filter
                    pass

            high_yield_bonds.append((isin, bond, score))

        # If no bonds match strict criteria, fall back to top-scored bonds
        if not high_yield_bonds:
            # Fallback: Get top 5 bonds by score, regardless of YTM
            all_bonds = [
                (isin, analytics[isin], scores[isin])
                for isin in scores
                if isin in analytics and scores[isin].total_score > 0.1
            ]

            # Filter by maturity year if specified
            if target_year:
                filtered_bonds = []
                for isin, bond, score in all_bonds:
                    try:
                        maturity_date = datetime.strptime(
                            bond.maturity_date, "%Y-%m-%d"
                        )
                        if maturity_date.year == target_year:
                            filtered_bonds.append((isin, bond, score))
                    except:
                        pass
                if filtered_bonds:
                    all_bonds = filtered_bonds
            # Sort by score
            all_bonds.sort(key=lambda x: x[2].total_score, reverse=True)
            high_yield_bonds = all_bonds[:5]
        else:
            # Sort by risk-adjusted yield
            high_yield_bonds.sort(
                key=lambda x: x[1].ytm / (1 + x[1].credit_risk_score), reverse=True
            )
            high_yield_bonds = high_yield_bonds[:5]

        recommendations = []
        for isin, bond, score in high_yield_bonds:
            recommendations.append(
                TradeRecommendation(
                    action="BUY",
                    isin=isin,
                    name=bond.name,
                    target_price=bond.current_price * 0.995,  # Slight discount
                    rationale=f"High YTM of {bond.ytm:.2%} with {bond.credit_rating.value if hasattr(bond.credit_rating, 'value') else bond.credit_rating} rating",
                    expected_return=bond.expected_return,
                    risk_score=bond.credit_risk_score,
                    confidence=score.total_score,
                )
            )

        return recommendations

    def _sector_rebalance_strategy(
        self,
        query: ClassifiedQuery,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio],
    ) -> List[TradeRecommendation]:
        """
        Strategy to rebalance sector concentration
        """
        if not portfolio:
            return []

        recommendations = []

        # Identify over-concentrated sectors
        sector_exposures = portfolio.sector_exposures
        over_concentrated = {
            sector: weight
            for sector, weight in sector_exposures.items()
            if weight > 0.30  # More than 30% in one sector
        }

        for sector, weight in over_concentrated.items():
            # Find bonds in this sector to sell
            sector_positions = [
                pos
                for pos in portfolio.positions
                if pos.isin in analytics and str(analytics[pos.isin].sector) == sector
            ]

            # Sort by score (sell worst)
            sector_positions.sort(
                key=lambda p: scores[p.isin].total_score if p.isin in scores else -1
            )

            # Sell bottom 20% of sector holdings
            to_sell = sector_positions[: max(1, len(sector_positions) // 5)]

            for pos in to_sell:
                bond = analytics[pos.isin]

                # Find replacement in different sector
                replacement = self._find_replacement_bond(
                    original=bond,
                    analytics=analytics,
                    scores=scores,
                    criteria={"exclude_sectors": [sector], "preserve_yield": True},
                )

                if replacement:
                    recommendations.append(
                        TradeRecommendation(
                            action="SWITCH",
                            isin=pos.isin,
                            name=bond.name,
                            quantity=pos.quantity,
                            switch_to_isin=replacement.isin,
                            switch_to_name=replacement.name,
                            rationale=f"Reduce {sector} exposure from {weight:.1f}% by switching to {replacement.sector.value}",
                            expected_return=replacement.expected_return,
                            risk_score=replacement.credit_risk_score,
                            confidence=scores[replacement.isin].total_score,
                        )
                    )

        return recommendations

    def _barbell_strategy(
        self,
        query: ClassifiedQuery,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
    ) -> List[TradeRecommendation]:
        """
        Construct barbell strategy: short + long duration bonds
        """
        # Find best short duration bonds (< 3 years)
        short_bonds = [
            (isin, analytics[isin])
            for isin in scores
            if analytics[isin].duration < 3.0
            and scores[isin].total_score > 0.2
            and analytics[isin].is_liquid
        ]
        short_bonds.sort(key=lambda x: scores[x[0]].total_score, reverse=True)

        # Find best long duration bonds (> 7 years)
        long_bonds = [
            (isin, analytics[isin])
            for isin in scores
            if analytics[isin].duration > 7.0 and scores[isin].total_score > 0.2
        ]
        long_bonds.sort(key=lambda x: x[1].ytm, reverse=True)  # High carry

        recommendations = []

        # Short end recommendation
        if short_bonds:
            isin, bond = short_bonds[0]
            recommendations.append(
                TradeRecommendation(
                    action="BUY",
                    isin=isin,
                    name=bond.name,
                    target_price=bond.current_price,
                    rationale=f"Short duration leg ({bond.duration:.1f}Y) - high liquidity, low rate risk",
                    expected_return=bond.expected_return,
                    risk_score=bond.credit_risk_score,
                    confidence=scores[isin].total_score,
                )
            )

        # Long end recommendation
        if long_bonds:
            isin, bond = long_bonds[0]
            recommendations.append(
                TradeRecommendation(
                    action="BUY",
                    isin=isin,
                    name=bond.name,
                    target_price=bond.current_price,
                    rationale=f"Long duration leg ({bond.duration:.1f}Y) - high carry ({bond.ytm:.2f}%), convexity benefit",
                    expected_return=bond.expected_return,
                    risk_score=bond.credit_risk_score,
                    confidence=scores[isin].total_score,
                )
            )

        return recommendations

    def _hedge_strategy(
        self,
        query: ClassifiedQuery,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio],
    ) -> List[TradeRecommendation]:
        """
        Strategy to hedge against rate volatility
        """
        # Recommend floating rate bonds and short duration AAA bonds
        hedge_bonds = [
            (isin, analytics[isin])
            for isin in scores
            if (analytics[isin].duration < 2.0 or "FRB" in analytics[isin].name)
            and analytics[isin].credit_rating.value in ["AAA", "AA+"]
            and analytics[isin].is_liquid
        ]

        hedge_bonds.sort(key=lambda x: x[1].liquidity_score, reverse=True)

        recommendations = []
        for isin, bond in hedge_bonds[:3]:
            recommendations.append(
                TradeRecommendation(
                    action="BUY",
                    isin=isin,
                    name=bond.name,
                    target_price=bond.current_price,
                    rationale=f"Volatility hedge: {bond.credit_rating.value} rated, duration {bond.duration:.1f}Y",
                    expected_return=bond.expected_return,
                    risk_score=bond.credit_risk_score,
                    confidence=scores[isin].total_score,
                )
            )

        return recommendations

    def _buy_recommendation_strategy(
        self,
        query: ClassifiedQuery,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        portfolio: Optional[Portfolio],
    ) -> List[TradeRecommendation]:
        """
        General buy recommendations with support for duration-specific queries
        """
        # Extract query text to check for duration preferences
        query_text = getattr(query, "query", "") or getattr(query, "original_query", "")
        query_lower = query_text.lower() if query_text else ""

        # Check if query is about long-duration or short-duration bonds
        is_long_duration_query = any(
            term in query_lower
            for term in [
                "long-duration",
                "long duration",
                "long term",
                "long-term",
                "extended duration",
                "high duration",
                "longer duration",
            ]
        )
        is_short_duration_query = any(
            term in query_lower
            for term in [
                "short-duration",
                "short duration",
                "short term",
                "short-term",
                "low duration",
                "shorter duration",
            ]
        )

        # Filter bonds based on query intent
        candidate_bonds = []

        # If scores are empty but analytics exist, use analytics directly
        if not scores and analytics:
            # Fallback: use analytics to create recommendations
            for isin, bond in analytics.items():
                # Apply duration filter if specified in query
                if is_long_duration_query:
                    if bond.duration < 7.0:
                        continue
                elif is_short_duration_query:
                    if bond.duration >= 3.0:
                        continue
                # Use expected_return as a proxy for score
                candidate_bonds.append((isin, bond, None))
        else:
            # Normal path: use scores
            for isin in scores:
                if isin not in analytics:
                    continue

                score = scores[isin]
                if score.total_score < 0.1:
                    continue

                bond = analytics[isin]

                # Apply duration filter if specified in query
                if is_long_duration_query:
                    # Long duration typically means > 7 years
                    if bond.duration < 7.0:
                        continue
                elif is_short_duration_query:
                    # Short duration typically means < 3 years
                    if bond.duration >= 3.0:
                        continue

                candidate_bonds.append((isin, bond, score))

        # If no bonds match duration criteria, fall back to all bonds
        if not candidate_bonds:
            if scores:
                candidate_bonds = [
                    (isin, analytics[isin], scores[isin])
                    for isin in scores
                    if isin in analytics and scores[isin].total_score > 0.1
                ]
            else:
                # Fallback: use analytics without scores
                candidate_bonds = [
                    (isin, bond, None) for isin, bond in analytics.items()
                ]

        # Sort by score (or by duration-adjusted score for long-duration queries)
        if is_long_duration_query:
            # For long-duration, prefer higher duration with good scores/returns
            if candidate_bonds and candidate_bonds[0][2] is not None:
                # Has scores
                candidate_bonds.sort(
                    key=lambda x: (x[1].duration * 0.3 + x[2].total_score * 0.7),
                    reverse=True,
                )
            else:
                # No scores, use duration and expected return
                candidate_bonds.sort(
                    key=lambda x: (x[1].duration * 0.4 + x[1].expected_return * 0.6),
                    reverse=True,
                )
        else:
            # Default: sort by total score or expected return
            if candidate_bonds and candidate_bonds[0][2] is not None:
                candidate_bonds.sort(key=lambda x: x[2].total_score, reverse=True)
            else:
                candidate_bonds.sort(key=lambda x: x[1].expected_return, reverse=True)

        # Get top 5-10 bonds
        top_bonds = candidate_bonds[:10]

        recommendations = []
        for isin, bond, score in top_bonds:
            # Build rationale based on query type
            score_val = (
                score.total_score if score else 0.5
            )  # Default confidence if no score
            confidence_val = (
                score.total_score
                if score
                else min(0.7, max(0.5, bond.expected_return / 10.0))
            )

            if is_long_duration_query:
                rationale = (
                    f"Long-duration bond (duration {bond.duration:.1f}Y) suitable for rate decline scenarios. "
                    f"Expected return: {bond.expected_return:.2f}%, YTM: {bond.ytm:.2f}%"
                )
            elif is_short_duration_query:
                rationale = (
                    f"Short-duration bond (duration {bond.duration:.1f}Y) provides rate protection. "
                    f"Expected return: {bond.expected_return:.2f}%, YTM: {bond.ytm:.2f}%"
                )
            else:
                rationale = (
                    f"Strong fundamentals: "
                    f"expected return {bond.expected_return:.2f}%, duration {bond.duration:.1f}Y, YTM {bond.ytm:.2f}%"
                )

            recommendations.append(
                TradeRecommendation(
                    action="BUY",
                    isin=isin,
                    name=bond.name,
                    target_price=bond.current_price * 0.995
                    if bond.current_price
                    else 100.0,
                    rationale=rationale,
                    expected_return=bond.expected_return,
                    risk_score=bond.credit_risk_score,
                    confidence=confidence_val,
                )
            )

        return recommendations

    def _buy_low_duration_bonds(
        self,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        query: ClassifiedQuery,
    ) -> List[TradeRecommendation]:
        """Buy bonds with low duration - robust version that handles missing scores"""
        recommendations = []

        # First try: strict criteria (duration < 3.0, score > 0.1)
        if scores:
            low_duration = [
                (isin, analytics[isin], scores[isin])
                for isin in scores
                if isin in analytics
                and analytics[isin].duration < 3.0
                and scores[isin].total_score > 0.1
            ]

            if low_duration:
                low_duration.sort(key=lambda x: x[2].total_score, reverse=True)

                for isin, bond, score in low_duration[:5]:
                    recommendations.append(
                        TradeRecommendation(
                            action="BUY",
                            isin=isin,
                            name=bond.name,
                            target_price=bond.current_price
                            if bond.current_price
                            else 100.0,
                            rationale=f"Low duration ({bond.duration:.1f}Y) reduces rate sensitivity. YTM: {bond.ytm:.2f}%",
                            expected_return=bond.expected_return,
                            risk_score=bond.credit_risk_score,
                            confidence=score.total_score,
                        )
                    )

        # Fallback 1: If no strict matches, relax to duration < 5.0 with scores
        if not recommendations and scores:
            low_duration = [
                (isin, analytics[isin], scores[isin])
                for isin in scores
                if isin in analytics
                and analytics[isin].duration < 5.0
                and scores[isin].total_score > 0.05  # Lower threshold
            ]

            if low_duration:
                # Sort by duration (lowest first), then by score
                low_duration.sort(key=lambda x: (x[1].duration, -x[2].total_score))

                for isin, bond, score in low_duration[:5]:
                    recommendations.append(
                        TradeRecommendation(
                            action="BUY",
                            isin=isin,
                            name=bond.name,
                            target_price=bond.current_price
                            if bond.current_price
                            else 100.0,
                            rationale=f"Moderate duration ({bond.duration:.1f}Y) suitable for duration reduction. YTM: {bond.ytm:.2f}%",
                            expected_return=bond.expected_return,
                            risk_score=bond.credit_risk_score,
                            confidence=score.total_score,
                        )
                    )

        # Fallback 2: If still no matches and scores exist, use all bonds sorted by duration
        if not recommendations and scores:
            all_bonds = [
                (isin, analytics[isin], scores[isin])
                for isin in scores
                if isin in analytics
            ]

            if all_bonds:
                # Sort by duration (lowest first)
                all_bonds.sort(key=lambda x: x[1].duration)

                for isin, bond, score in all_bonds[:5]:
                    recommendations.append(
                        TradeRecommendation(
                            action="BUY",
                            isin=isin,
                            name=bond.name,
                            target_price=bond.current_price
                            if bond.current_price
                            else 100.0,
                            rationale=f"Duration: {bond.duration:.1f}Y. YTM: {bond.ytm:.2f}%. Recommended for duration reduction strategy.",
                            expected_return=bond.expected_return,
                            risk_score=bond.credit_risk_score,
                            confidence=score.total_score
                            if score.total_score > 0
                            else 0.5,
                        )
                    )

        # Fallback 3: If no scores at all, use analytics only
        if not recommendations and analytics:
            low_duration = [
                (isin, analytics[isin])
                for isin, bond in analytics.items()
                if bond.duration < 5.0
            ]

            if low_duration:
                # Sort by duration (lowest first), then by expected return
                low_duration.sort(key=lambda x: (x[1].duration, -x[1].expected_return))

                for isin, bond in low_duration[:5]:
                    # Use expected return as proxy for confidence
                    confidence = min(0.8, max(0.5, bond.expected_return / 10.0))

                    recommendations.append(
                        TradeRecommendation(
                            action="BUY",
                            isin=isin,
                            name=bond.name,
                            target_price=bond.current_price
                            if bond.current_price
                            else 100.0,
                            rationale=f"Low duration ({bond.duration:.1f}Y) bond suitable for reducing portfolio duration. YTM: {bond.ytm:.2f}%",
                            expected_return=bond.expected_return,
                            risk_score=bond.credit_risk_score,
                            confidence=confidence,
                        )
                    )

        return recommendations

    def _find_replacement_bond(
        self,
        original: BondAnalytics,
        analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        criteria: Dict,
    ) -> Optional[BondAnalytics]:
        """
        Find a suitable replacement bond - robust version with fallbacks
        """
        candidates = []
        for isin, bond in analytics.items():
            # Skip original
            if isin == original.isin:
                continue

            # Apply criteria
            if (
                criteria.get("max_duration")
                and bond.duration > criteria["max_duration"]
            ):
                continue

            if criteria.get("preserve_yield"):
                # Relax yield requirement slightly (90% instead of 95%)
                if bond.ytm < original.ytm * 0.90:
                    continue

            if criteria.get("exclude_sectors"):
                if bond.sector in criteria["exclude_sectors"]:
                    continue

            # Score check - be more lenient
            score_val = scores.get(isin)
            if score_val:
                score = score_val.total_score
            else:
                # If no score, use expected return as proxy
                score = max(0.05, min(0.7, bond.expected_return / 10.0))

            # Lower threshold from 0.1 to 0.05
            if score < 0.05:
                continue

            candidates.append((isin, bond, score))

        if not candidates:
            return None

        # Sort by score (highest first), then by duration (lowest first for duration reduction)
        candidates.sort(key=lambda x: (x[2], -x[1].duration), reverse=True)
        return candidates[0][1]

    def _calculate_portfolio_impact(
        self,
        recommendations: List[TradeRecommendation],
        analytics: Dict[str, BondAnalytics],
        portfolio: Optional[Portfolio],
    ) -> Dict:
        """
        Calculate expected impact on portfolio
        """
        if not portfolio:
            return {}
        # Calculate expected changes
        duration_change = 0.0
        yield_change = 0.0
        sector_changes = {}
        for rec in recommendations:
            if rec.action in ["SELL", "SWITCH"]:
                if rec.isin in analytics:
                    bond = analytics[rec.isin]
                    weight = next(
                        (p.weight for p in portfolio.positions if p.isin == rec.isin), 0
                    )
                    duration_change -= bond.duration * weight
                    yield_change -= bond.ytm * weight

                    sector = str(bond.sector)
                    sector_changes[sector] = sector_changes.get(sector, 0) - weight

            if rec.action in ["BUY", "SWITCH"]:
                target_isin = rec.switch_to_isin if rec.action == "SWITCH" else rec.isin
                if target_isin in analytics:
                    bond = analytics[target_isin]
                    # Assume equal weight
                    weight = (
                        1.0 / len(portfolio.positions) if portfolio.positions else 0.1
                    )
                    duration_change += bond.duration * weight
                    yield_change += bond.ytm * weight

                    sector = str(bond.sector)
                    sector_changes[sector] = sector_changes.get(sector, 0) + weight

        return {
            "expected_duration_change": round(duration_change, 2),
            "expected_yield_change": round(yield_change, 2),
            "sector_rebalancing": {
                k: round(v * 100, 1) for k, v in sector_changes.items()
            },
        }

    def _generate_summary(
        self,
        query: ClassifiedQuery,
        recommendations: List[TradeRecommendation],
        portfolio_changes: Dict,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        web_search_context: str = "",
    ) -> str:
        """
        Generate natural language summary using LLM
        """
        if not recommendations:
            # Check if query is about long-duration bonds and rate outlook
            query_text = getattr(query, "query", "") or getattr(
                query, "original_query", ""
            )
            query_lower = query_text.lower() if query_text else ""

            is_rate_outlook_query = any(
                term in query_lower
                for term in [
                    "rate outlook",
                    "rate forecast",
                    "rate expectation",
                    "rate trend",
                    "interest rate",
                    "yield outlook",
                    "monetary policy",
                ]
            )

            if is_rate_outlook_query and web_search_context:
                # Provide context-aware response about rate outlook
                return (
                    f"Based on current market intelligence, I cannot provide specific bond recommendations at this time. "
                    f"However, regarding long-duration bonds and rate outlook: {web_search_context[:200]}... "
                    f"Please check that bond analytics and scores are available for more specific recommendations."
                )

            return "No actionable recommendations at this time based on current market conditions and your constraints."

        buy_count = sum(1 for r in recommendations if r.action == "BUY")
        sell_count = sum(1 for r in recommendations if r.action == "SELL")
        switch_count = sum(1 for r in recommendations if r.action == "SWITCH")
        hold_count = sum(1 for r in recommendations if r.action == "HOLD")

        # Build context for LLM
        rec_details = []
        for r in recommendations[:5]:  # Top 5 for summary
            rec_details.append(
                f"- {r.action} {r.name}: Expected return {r.expected_return:.2%}, {r.rationale[:100]}"
            )

        portfolio_impact = ""
        if portfolio_changes:
            if "expected_duration_change" in portfolio_changes:
                portfolio_impact += f"Duration change: {portfolio_changes['expected_duration_change']:.1f} years. "
            if "expected_yield_change" in portfolio_changes:
                portfolio_impact += (
                    f"Yield change: {portfolio_changes['expected_yield_change']:.2f}%. "
                )
            if "expected_return" in portfolio_changes:
                portfolio_impact += (
                    f"Expected return: {portfolio_changes['expected_return']:.2%}. "
                )

        try:
            # Get query and intent text
            query_text = getattr(query, "query", None) or getattr(
                query, "original_query", ""
            )
            intent_text = getattr(query, "intent", "")
            if hasattr(intent_text, "value"):
                intent_text = intent_text.value
            intent_text = str(intent_text)

            # Format conversation context
            conversation_context = ""
            if conversation_history:
                recent = conversation_history[-5:]  # Last 5 messages
                context_parts = ["Previous conversation context:"]
                for msg in recent:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        # Extract user preferences
                        if any(
                            kw in content.lower()
                            for kw in ["prefer", "like", "want", "need", "avoid"]
                        ):
                            context_parts.append(f"User preference: {content[:150]}")
                    elif role == "assistant":
                        # Extract previous recommendations
                        if "recommend" in content.lower() or "buy" in content.lower():
                            context_parts.append(
                                f"Previous recommendation: {content[:200]}..."
                            )
                conversation_context = (
                    "\n".join(context_parts)
                    if context_parts
                    else "No relevant previous context."
                )
            else:
                conversation_context = "No previous conversation."

            # Use LLM to generate natural summary
            web_context_section = (
                f"\n\n{web_search_context}" if web_search_context else ""
            )
            summary_prompt = f"""Generate a concise, professional summary (3-4 sentences) for this bond advisory response:

{conversation_context}

User Query: {query_text}
Intent: {intent_text}

Recommendations ({len(recommendations)} total):
- {buy_count} BUY, {sell_count} SELL, {switch_count} SWITCH, {hold_count} HOLD

Top Recommendations:
{chr(10).join(rec_details)}

Portfolio Impact: {portfolio_impact if portfolio_impact else "N/A"}{web_context_section}

Write a natural, conversational summary explaining what you recommend and why. Be specific about the key bonds and expected outcomes. Reference previous conversation if relevant. If web search context is provided, incorporate relevant market information into your summary."""

            response = self.llm.invoke(summary_prompt)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            return content.strip() if isinstance(content, str) else str(content)

        except Exception as e:
            # Fallback to basic summary
            intent_text = getattr(query, "intent", "")
            if hasattr(intent_text, "value"):
                intent_text = intent_text.value
            intent_text = str(intent_text).replace("_", " ")
            summary = f"Based on your query to {intent_text}, I recommend:\n\n"

            if buy_count > 0:
                summary += f"• **{buy_count} BUY** recommendations\n"
            if sell_count > 0:
                summary += f"• **{sell_count} SELL** recommendations\n"
            if switch_count > 0:
                summary += f"• **{switch_count} SWITCH** recommendations\n"
            if portfolio_changes:
                summary += f"\n**Expected portfolio impact:**\n"
                if "expected_duration_change" in portfolio_changes:
                    summary += f"• Duration change: {portfolio_changes['expected_duration_change']:.1f} years\n"
                if "expected_yield_change" in portfolio_changes:
                    summary += f"• Yield change: {portfolio_changes['expected_yield_change']:.2f}%\n"
            return summary


from pydantic import SecretStr


def create_advisory_agent(
    api_key: str,
    model: str = "gpt-4-turbo-preview",
    web_search_tool: Optional[Any] = None,
) -> AdvisoryAgent:
    """Factory function to create advisory agent

    Args:
        api_key: OpenAI API key
        model: Model name to use
        web_search_tool: Optional web search tool for gathering additional market context
    """
    llm = ChatOpenAI(model=model, temperature=0.2, api_key=SecretStr(api_key))
    return AdvisoryAgent(llm, web_search_tool=web_search_tool)
