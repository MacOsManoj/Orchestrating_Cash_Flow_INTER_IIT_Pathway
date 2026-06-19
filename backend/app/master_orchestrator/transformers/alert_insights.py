"""
Alert Insights Transformer
==========================

Transforms /api/news/summarized response to comp-5 (AlertInsights) format.
Filters for high-impact/negative news and maps to alert severity levels.

API Response:
{
    "headline": str,
    "published_at": str,
    "liquidity_impact": str (HIGH_POSITIVE, HIGH_NEGATIVE, NEUTRAL, etc.),
    "sentiment_label": str (positive, negative, neutral),
    ...
}

Component Format:
[
    {
        "title": str,
        "timestamp": str,
        "severity": "critical" | "warning" | "info"
    }
]
"""

from typing import Dict, Any, List


def _map_severity(liquidity_impact: str, sentiment_label: str) -> str:
    """
    Map liquidity impact and sentiment to severity level.
    
    - critical: HIGH_NEGATIVE impact or negative sentiment with high impact
    - warning: Medium impact or mixed signals
    - info: Low impact or positive news
    """
    impact_upper = (liquidity_impact or "").upper()
    sentiment_lower = (sentiment_label or "").lower()
    
    if "HIGH_NEGATIVE" in impact_upper or (sentiment_lower == "negative" and "HIGH" in impact_upper):
        return "critical"
    elif "NEGATIVE" in impact_upper or sentiment_lower == "negative":
        return "warning"
    elif "HIGH_POSITIVE" in impact_upper:
        return "info"
    else:
        return "info"


def transform_alert_insights(api_response: Any, **kwargs) -> List[Dict[str, Any]]:
    """
    Transform news/summarized API response to AlertInsights component format.
    
    Args:
        api_response: List of news articles from /api/news/summarized
        **kwargs: Additional parameters (liquidity_impact filter can be applied)
    
    Returns:
        List of alert objects with title, timestamp, severity
    """
    # Handle if response is a list directly
    if isinstance(api_response, list):
        articles = api_response
    elif isinstance(api_response, dict):
        articles = api_response.get("articles", api_response.get("data", []))
    else:
        articles = []
    
    alerts = []
    for article in articles:
        liquidity_impact = article.get("liquidity_impact", "")
        sentiment_label = article.get("sentiment_label", "")
        
        # Only include articles with some significance (not purely neutral)
        if liquidity_impact or sentiment_label in ["negative", "positive"]:
            severity = _map_severity(liquidity_impact, sentiment_label)
            
            alerts.append({
                "title": article.get("headline") or article.get("title", ""),
                "timestamp": article.get("published_at") or article.get("timestamp", ""),
                "severity": severity
            })
    
    # Sort by severity (critical first) and limit to 5 alerts
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))
    
    return alerts[:5]
