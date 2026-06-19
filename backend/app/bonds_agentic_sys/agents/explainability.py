"""
Explainability Agent V2
CONDITIONAL EXECUTION - Only runs when user explicitly asks
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import SecretStr

from dotenv import load_dotenv

load_dotenv()


class Explanation:
    def __init__(self, **kwargs):
        self.recommendation_id = kwargs.get("recommendation_id", "")
        self.explanation_text = kwargs.get("explanation_text", "")
        self.shap_values = kwargs.get("shap_values", {})
        self.top_positive_factors = kwargs.get("top_positive_factors", [])
        self.top_negative_factors = kwargs.get("top_negative_factors", [])
        self.citations = kwargs.get("citations", [])
        self.charts = kwargs.get("charts", [])


class ExplainabilityAgent:
    """
    Generates explanations for recommendations
    ONLY runs when planner says needs_explainability = True
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

        self.explanation_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at explaining bond trading recommendations.

Your job is to create clear, detailed explanations that help users understand WHY a recommendation was made.

Include:
1. Main reasoning
2. Key factors (positive and negative)
3. Market context
4. Risk considerations
5. Alternative viewpoints

Be specific and cite data sources.""",
                ),
                (
                    "user",
                    """Explain this bond recommendation:

Recommendation:
{recommendation}

Bond Analytics:
{analytics}

ML Factors:
{ml_factors}

Market Context:
- RBI Policy: {rbi_context}
- Recent News: {news_context}
- Credit Rating: {credit_context}

Provide a detailed explanation with specific reasons and data.""",
                ),
            ]
        )

    def explain_recommendations(
        self,
        recommendations: List[Any],
        bond_analytics: Dict[str, Any],
        bond_scores: Dict[str, Any],
        ml_predictions: Dict[str, Any],
        rbi_policy: Optional[Dict] = None,
        news_items: Optional[List[Any]] = None,
        credit_ratings: Optional[Dict] = None,
    ) -> List[Explanation]:
        """
        Generate explanations for recommendations

        Args:
            recommendations: List of recommendations to explain
            bond_analytics: Bond analytics dict
            bond_scores: Scoring results
            ml_predictions: ML predictions
            rbi_policy: RBI policy data
            news_items: News articles
            credit_ratings: Credit rating data
        """
        explanations = []

        for rec in recommendations:
            # Safely get analytics, score, and predictions
            analytics = (
                bond_analytics.get(rec.isin)
                if isinstance(bond_analytics, dict)
                else None
            )
            score = bond_scores.get(rec.isin) if isinstance(bond_scores, dict) else None
            ml_pred = (
                ml_predictions.get(rec.isin)
                if isinstance(ml_predictions, dict)
                else None
            )
            credit_rating = (
                credit_ratings.get(rec.isin)
                if credit_ratings and isinstance(credit_ratings, dict)
                else None
            )

            explanation = self._explain_single_recommendation(
                rec,
                analytics or {},
                score or {},
                ml_pred or {},
                rbi_policy,
                news_items,
                credit_rating,
            )
            explanations.append(explanation)

        return explanations

    def _explain_single_recommendation(
        self,
        recommendation: Any,
        analytics: Dict,
        score: Dict,
        ml_pred: Dict,
        rbi_policy: Optional[Dict],
        news_items: Optional[List[Any]],
        credit_rating: Optional[Dict],
    ) -> Explanation:
        """Generate explanation for single recommendation"""

        # Calculate SHAP-like attribution
        shap_values = self._calculate_attribution(analytics, score, ml_pred)

        # Get top factors
        sorted_factors = sorted(
            shap_values.items(), key=lambda x: abs(x[1]), reverse=True
        )
        top_positive = [(k, v) for k, v in sorted_factors if v > 0][:5]
        top_negative = [(k, v) for k, v in sorted_factors if v < 0][:5]

        # Prepare context
        rbi_context = (
            self._format_rbi_context(rbi_policy) if rbi_policy else "No RBI data"
        )
        news_context = (
            self._format_news_context(news_items) if news_items else "No news data"
        )
        credit_context = (
            self._format_credit_context(credit_rating)
            if credit_rating
            else "No credit data"
        )

        # Generate explanation with LLM
        messages = self.explanation_prompt.format_messages(
            recommendation=self._format_recommendation(recommendation),
            analytics=self._format_analytics(analytics),
            ml_factors=self._format_ml_factors(ml_pred),
            rbi_context=rbi_context,
            news_context=news_context,
            credit_context=credit_context,
        )

        response = self.llm.invoke(messages)
        explanation_text = response.content

        # Create citations
        citations = self._create_citations(
            analytics, rbi_policy, news_items, credit_rating
        )

        # Generate chart specs
        charts = self._generate_chart_specs(shap_values, analytics)

        return Explanation(
            recommendation_id=recommendation.isin,
            explanation_text=explanation_text,
            shap_values=shap_values,
            top_positive_factors=[self._format_factor(k, v) for k, v in top_positive],
            top_negative_factors=[self._format_factor(k, v) for k, v in top_negative],
            citations=citations,
            charts=charts,
        )

    def _calculate_attribution(
        self, analytics: Any, score: Any, ml_pred: Any
    ) -> Dict[str, float]:
        """Calculate SHAP-like feature attribution"""

        def _get_attr(obj, key, default):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        shap_values = {}

        # Valuation impact
        valuation_gap = _get_attr(analytics, "valuation_gap", 0.0)
        shap_values["valuation"] = (valuation_gap / 5.0) * 0.3  # Normalized

        # Expected return impact
        expected_return = _get_attr(ml_pred, "expected_return", 0.0)
        shap_values["expected_return"] = (expected_return / 2.0) * 0.3

        # Credit quality impact
        credit_risk = _get_attr(analytics, "credit_risk_score", 0.1)
        shap_values["credit_quality"] = (1.0 - credit_risk) * 0.25

        # Liquidity impact
        liquidity = _get_attr(analytics, "liquidity_score", 0.5)
        shap_values["liquidity"] = liquidity * 0.2

        # ML factors
        factors = _get_attr(ml_pred, "factors", {})
        if isinstance(factors, dict):
            for factor_name, factor_value in factors.items():
                shap_values[f"ml_{factor_name}"] = factor_value * 0.1

        # Duration risk
        if _get_attr(analytics, "is_rate_sensitive", False):
            rate_sensitivity = _get_attr(analytics, "rate_sensitivity", 0.0)
            shap_values["duration_risk"] = -abs(rate_sensitivity) * 0.1

        # Carry
        current_yield = _get_attr(analytics, "current_yield", 0.07)
        shap_values["carry"] = (current_yield / 10.0) * 0.05

        return shap_values

    def _format_factor(self, name: str, value: float) -> str:
        """Format factor for display"""
        # Convert technical names to readable
        name_map = {
            "valuation": "Valuation Gap",
            "expected_return": "Expected Return",
            "credit_quality": "Credit Quality",
            "liquidity": "Liquidity",
            "duration_risk": "Duration Risk",
            "carry": "Carry (Yield)",
            "ml_yield_curve": "Yield Curve Movement",
            "ml_credit_spread": "Credit Spread",
            "ml_sentiment": "Market Sentiment",
            "ml_carry": "Carry Component",
        }

        readable_name = name_map.get(name, name.replace("_", " ").title())

        if value > 0:
            return f"+ {readable_name} ({value:+.2%})"
        else:
            return f"- {readable_name} ({value:+.2%})"

    def _format_recommendation(self, rec: Any) -> str:
        """Format recommendation for LLM"""
        return f"""
Action: {rec.action}
Bond: {rec.name} ({rec.isin})
Rationale: {rec.rationale}
Expected Return: {rec.expected_return:.2%}
Confidence: {rec.confidence:.2%}
        """.strip()

    def _format_analytics(self, analytics: Any) -> str:
        """Format analytics for LLM"""

        # Handle both dict and BondAnalytics object
        def _get_attr(obj, key, default):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        return f"""
Current Price: {_get_attr(analytics, "current_price", 0):.2f}
Fair Value: {_get_attr(analytics, "fair_value", 0):.2f}
Valuation Gap: {_get_attr(analytics, "valuation_gap", 0):.2%}
Duration: {_get_attr(analytics, "duration", 0):.2f}
YTM: {_get_attr(analytics, "ytm", 0):.2%}
Credit Risk Score: {_get_attr(analytics, "credit_risk_score", 0):.3f}
Liquidity Score: {_get_attr(analytics, "liquidity_score", 0):.2f}
ML Signal: {_get_attr(analytics, "ml_signal", "HOLD")}
        """.strip()

    def _format_ml_factors(self, ml_pred: Any) -> str:
        """Format ML factors for LLM"""

        def _get_attr(obj, key, default):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        factors = _get_attr(ml_pred, "factors", {})
        if not isinstance(factors, dict):
            factors = {}

        lines = []
        for name, value in factors.items():
            lines.append(f"{name.title()}: {value:+.2%}")
        return "\n".join(lines) if lines else "No ML factors available"

    def _format_rbi_context(self, rbi_policy: Dict) -> str:
        """Format RBI context for LLM"""
        return f"""
Repo Rate: {rbi_policy.get("repo_rate", 6.5):.2%}
Stance: {rbi_policy.get("stance", "neutral").title()}
CPI Forecast: {rbi_policy.get("CPI_forecast", 4.5):.1%}
Forward Guidance: {rbi_policy.get("forward_guidance", "Neutral")}
        """.strip()

    def _format_news_context(self, news_items: Optional[List[Any]]) -> str:
        """Format news context for LLM"""
        if not news_items:
            return "No recent news"

        # Take top 3 by relevance
        top_news = sorted(
            news_items, key=lambda x: x.get("relevance_score", 0), reverse=True
        )[:3]

        lines = []
        for item in top_news:
            lines.append(
                f"- {item.get('title', '')} (Sentiment: {item.get('sentiment_score', 0):+.2f})"
            )

        return "\n".join(lines)

    def _format_credit_context(self, credit_rating: Dict) -> str:
        """Format credit context for LLM"""
        if not credit_rating:
            return "No credit data"

        return f"""
Rating: {credit_rating.get("rating", "N/A")}
Outlook: {credit_rating.get("outlook", "N/A")}
Probability of Default: {credit_rating.get("probability_default", 0):.2%}
Credit Spread: {credit_rating.get("credit_spread", 0):.0f} bps
        """.strip()

    def _create_citations(
        self,
        analytics: Any,
        rbi_policy: Optional[Dict],
        news_items: Optional[List[Any]],
        credit_rating: Optional[Dict],
    ) -> List[str]:
        """Create citations for explanation"""

        def _get_attr(obj, key, default):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        citations = []

        current_price = _get_attr(analytics, "current_price", 0)
        ytm = _get_attr(analytics, "ytm", 0)
        citations.append(f"NSE Bond Data (Price: ₹{current_price:.2f}, YTM: {ytm:.2%})")

        if credit_rating:
            rating = _get_attr(credit_rating, "rating", "N/A")
            outlook = _get_attr(credit_rating, "outlook", "N/A")
            citations.append(f"CRISIL Rating: {rating} ({outlook})")

        if rbi_policy:
            repo_rate = _get_attr(rbi_policy, "repo_rate", 6.5)
            stance = _get_attr(rbi_policy, "stance", "neutral")
            citations.append(f"RBI MPC: Repo Rate {repo_rate:.2%}, Stance: {stance}")

        if news_items:
            citations.append(f"Market Sentiment Analysis ({len(news_items)} articles)")

        ml_signal = _get_attr(analytics, "ml_signal", "N/A")
        citations.append(f"ML Model Prediction (Signal: {ml_signal})")

        return citations

    def _generate_chart_specs(
        self, shap_values: Dict[str, float], analytics: Any
    ) -> List[Dict]:
        """Generate chart specifications"""

        def _get_attr(obj, key, default):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        charts = []

        # SHAP waterfall chart
        charts.append(
            {
                "type": "waterfall",
                "title": "Factor Attribution (SHAP Values)",
                "data": shap_values,
            }
        )

        # Risk-return scatter
        charts.append(
            {
                "type": "scatter",
                "title": "Risk-Return Profile",
                "data": {
                    "expected_return": _get_attr(analytics, "expected_return", 0),
                    "risk": _get_attr(analytics, "credit_risk_score", 0),
                },
            }
        )

        return charts


def create_explainability_agent(
    api_key: str, model: str = "gpt-4-turbo-preview"
) -> ExplainabilityAgent:
    """Factory function"""
    llm = ChatOpenAI(model=model, temperature=0.0, api_key=api_key)
    return ExplainabilityAgent(llm)
