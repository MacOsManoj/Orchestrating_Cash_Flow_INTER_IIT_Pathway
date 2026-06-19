"""
Transformer for FxPriceChart (comp-20)
Maps /v1/currency/{pair}/price-data endpoint response to UI format
"""
from typing import Any


def transform(api_response: dict[str, Any], currency_pair: str = "") -> dict[str, Any]:
    """
    Transform currency price-data API response to FxPriceChart format.
    
    Expected API response format (from forex.py CurrencyPriceData):
    {
        "pair": "EUR/USD",
        "date": "2025-01-15",
        "open": 1.0850,
        "high": 1.0890,
        "low": 1.0820,
        "close": 1.0875,
        "volume": 50000,
        "change": 0.0025,
        "change_pct": 0.23,
        "volatility": 0.15
    }
    
    OR a list of such price data points.
    
    Target UI format (comp-20):
    {
        "currencyPair": "EUR/USD",
        "points": [
            {
                "date": "2025-02-01",
                "value": 1.0875
            }
        ]
    }
    """
    # Determine currency pair
    pair = currency_pair
    if isinstance(api_response, dict):
        pair = api_response.get("pair", api_response.get("currency_pair", pair))
    
    points = []
    
    # Handle if response is a list of price data
    if isinstance(api_response, list):
        for item in api_response:
            if isinstance(item, dict):
                point = {
                    "date": item.get("date", item.get("timestamp", "")),
                    "value": item.get("close", item.get("price", item.get("rate", 0)))
                }
                points.append(point)
    
    # Handle if response is a dict with data array
    elif isinstance(api_response, dict):
        data_list = api_response.get("data", api_response.get("prices", api_response.get("history", [])))
        
        if isinstance(data_list, list):
            for item in data_list:
                if isinstance(item, dict):
                    point = {
                        "date": item.get("date", item.get("timestamp", "")),
                        "value": item.get("close", item.get("price", item.get("rate", 0)))
                    }
                    points.append(point)
        
        # If no data array, check if it's a single price point
        if not points and "close" in api_response:
            points.append({
                "date": api_response.get("date", ""),
                "value": api_response.get("close", 0)
            })
    
    return {
        "currencyPair": pair,
        "points": points
    }
