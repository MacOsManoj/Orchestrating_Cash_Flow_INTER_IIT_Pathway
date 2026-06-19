"""
News Sentiment Transformer
==========================

Transforms /api/news/summarized response to comp-1 (NewsSentimentStream) format.

API Response:
{
    "headline": str,
    "source": str,
    "published_at": str,
    "sentiment_score": float (-1 to 1),
    ...
}

Component Format:
{
    "newsItems": [
        {
            "headline": str,
            "source": str,
            "timestamp": str,
            "sentimentScore": number (-1 to 1)
        }
    ]
}
"""

from typing import Dict, Any, List


def transform_news_sentiment(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform news/summarized API response to NewsSentimentStream component format.
    
    Args:
        api_response: List of news articles from /api/news/summarized
        **kwargs: Additional parameters (company filter applied at API level)
    
    Returns:
        Component-ready JSON with newsItems array
    """
    # Handle if response is a list directly
    if isinstance(api_response, list):
        articles = api_response
    elif isinstance(api_response, dict):
        articles = api_response.get("articles", api_response.get("data", []))
    else:
        articles = []
    
    news_items = []
    for article in articles[:10]:  # Limit to 10 items for UI
        # Extract sentiment score, handle various field names
        sentiment = article.get("sentiment_score") or article.get("sentimentScore") or 0.0
        
        # Ensure sentiment is a number
        if isinstance(sentiment, str):
            try:
                sentiment = float(sentiment)
            except ValueError:
                sentiment = 0.0
        
        news_items.append({
            "headline": article.get("headline") or article.get("title", ""),
            "source": article.get("source", "Unknown"),
            "timestamp": article.get("published_at") or article.get("timestamp", ""),
            "sentimentScore": round(sentiment, 2)
        })
    
    return {
        "newsItems": news_items
    }
