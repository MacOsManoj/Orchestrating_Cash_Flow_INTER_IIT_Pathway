"""
Sentiment Analysis Card Transformer
====================================

Transforms /api/stocks/agent/query response to comp-12 (SentimentAnalysisCard) format.
Extracts twitter_agent sentiment from the full analysis response.

API Response (sample_output.json):
{
    "twitter_output": {
        "summary": "The sentiment around $RELIANCE is mixed...",
        "sentiment_score": 0.4,
        "timestamp": "2025-12-06T17:07:26.262715"
    },
    ...
}

Component Format:
{
    "sentimentScore": "0.4 (Neutral/Bearish/Bullish)",
    "reasoning": "string (reasoning for the sentiment score)"
}
"""

from typing import Dict, Any


def _get_sentiment_label(score: float) -> str:
    """Convert sentiment score to label."""
    if score >= 0.6:
        return "Bullish"
    elif score >= 0.4:
        return "Neutral"
    elif score >= 0.2:
        return "Slightly Bearish"
    else:
        return "Bearish"


def transform_sentiment_analysis(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform stocks POST /query API response to SentimentAnalysisCard component format.
    
    The stock agent response has data nested under 'response' key:
    {
        "success": true,
        "ticker": "RELIANCE",
        "response": {
            "twitter_output": {...},
            ...
        }
    }
    
    Args:
        api_response: Full analysis response from POST /query
        **kwargs: ticker param may be passed
    
    Returns:
        Component-ready JSON with sentiment score and reasoning
    """
    if not isinstance(api_response, dict):
        return {
            "sentimentScore": "N/A",
            "reasoning": "No sentiment data available"
        }
    
    # Handle nested response structure (stock agent wraps data in 'response' key)
    response_data = api_response.get("response", api_response)
    
    # Extract twitter_output from nested response
    twitter_output = response_data.get("twitter_output", {})
    
    # Get sentiment score
    sentiment_score = twitter_output.get("sentiment_score")
    
    if sentiment_score is None:
        return {
            "sentimentScore": "N/A",
            "reasoning": "No Twitter sentiment data available"
        }
    
    # Ensure score is a float
    try:
        sentiment_score = float(sentiment_score)
    except (TypeError, ValueError):
        sentiment_score = 0.0
    
    # Get the sentiment label
    label = _get_sentiment_label(sentiment_score)
    
    # Format score with label
    score_display = f"{sentiment_score:.1f} ({label})"
    
    # Get reasoning from summary
    reasoning = twitter_output.get("summary", "No detailed analysis available")
    
    return {
        "sentimentScore": score_display,
        "reasoning": reasoning
    }
