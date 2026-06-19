"""
Feature Extraction Module
- Liquidity impact calculation
- Critical event detection
- Investment decision signals
"""

from typing import Any, Dict, List

# Critical event keywords
CRITICAL_EVENTS = {
    "earnings": [
        "earnings",
        "quarterly report",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "revenue",
        "profit",
    ],
    "merger_acquisition": ["merger", "acquisition", "buyout", "takeover", "M&A"],
    "lawsuit": ["lawsuit", "legal action", "sued", "court", "litigation"],
    "product_launch": ["launch", "unveil", "announce", "new product", "release"],
    "executive_change": [
        "CEO",
        "CFO",
        "CTO",
        "resign",
        "appointed",
        "steps down",
        "retire",
    ],
    "regulatory_action": [
        "SEC",
        "regulation",
        "regulatory",
        "compliance",
        "fine",
        "penalty",
    ],
    "dividend": ["dividend", "payout", "shareholder return"],
    "stock_split": ["stock split", "share split"],
    "guidance": ["guidance", "outlook", "forecast", "projection"],
    "rating_change": ["upgrade", "downgrade", "rating", "analyst"],
    "partnership": ["partnership", "collaboration", "joint venture", "alliance"],
    "restructuring": ["restructuring", "layoff", "cost cutting", "reorganization"],
}


def calculate_liquidity_impact(sentiment: Dict[str, Any]) -> str:
    """Calculate expected liquidity impact from sentiment"""
    label = sentiment.get("label", "neutral")
    score = sentiment.get("score", 0.5)

    if label == "positive":
        return "HIGH_POSITIVE" if score > 0.8 else "MODERATE_POSITIVE"
    elif label == "negative":
        return "HIGH_NEGATIVE" if score > 0.8 else "MODERATE_NEGATIVE"
    return "NEUTRAL"


def detect_critical_events(title: str, content: str) -> List[str]:
    """Detect critical financial events from text"""
    text = f"{title} {content}".lower()

    return [
        event_type
        for event_type, keywords in CRITICAL_EVENTS.items()
        if any(kw.lower() in text for kw in keywords)
    ]


def generate_decisions(
    sentiment: Dict[str, Any],
    liquidity_impact: str,
    critical_events: List[str],
    factor_type: str,
) -> List[str]:
    """Generate investment decision signals"""
    decisions = []

    label = sentiment.get("label", "neutral")
    score = sentiment.get("score", 0.5)

    # Sentiment-based
    if label == "positive" and score > 0.7:
        decisions.append("CONSIDER_BUY")
    elif label == "negative" and score > 0.7:
        decisions.append("CONSIDER_SELL")
    else:
        decisions.append("HOLD_MONITOR")

    # Volatility
    if "HIGH" in liquidity_impact:
        decisions.append("HIGH_VOLATILITY_EXPECTED")

    # Event alerts
    event_alerts = {
        "earnings": "EARNINGS_ALERT",
        "merger_acquisition": "M&A_ALERT",
        "lawsuit": "RISK_ALERT",
        "regulatory_action": "REGULATORY_ALERT",
    }
    for event, alert in event_alerts.items():
        if event in critical_events:
            decisions.append(alert)

    # Factor signals
    factor_signals = {
        "political": "POLITICAL_FACTOR",
        "regulatory": "REGULATORY_FACTOR",
        "economic": "ECONOMIC_FACTOR",
    }
    if factor_type in factor_signals:
        decisions.append(factor_signals[factor_type])

    return decisions


def extract_features(
    title: str, content: str, sentiment: Dict[str, Any], factor_type: str
) -> Dict[str, Any]:
    """
    Extract all features from article.

    Returns: {
        'liquidity_impact': str,
        'critical_events': List[str],
        'decisions': List[str]
    }
    """
    liquidity = calculate_liquidity_impact(sentiment)
    events = detect_critical_events(title, content)
    decisions = generate_decisions(sentiment, liquidity, events, factor_type)

    return {
        "liquidity_impact": liquidity,
        "critical_events": events,
        "decisions": decisions,
    }
