"""
Transformer for BondPriceTimeChart (comp-24)
Maps /{isin}/price-statistics endpoint response to UI format
"""
from typing import Any


def transform(api_response: dict[str, Any], bond_name: str = "") -> dict[str, Any]:
    """
    Transform price-statistics API response to BondPriceTimeChart format.
    
    Expected API response format (from bond_router.py PriceStatisticsResponse):
    {
        "isin": "INE001A07RX9",
        "period": "1Y",
        "price_data": [
            {
                "date": "2025-01-15",
                "price": 101.50,
                "percentile_5": 99.50,
                "percentile_95": 103.00,
                "median": 101.25
            }
        ],
        "metrics": {
            "median_price": 101.25,
            "percentile_5": 99.50,
            "percentile_95": 103.00,
            "implied_volatility": 0.12
        },
        "last_updated": "2025-01-15T10:30:00Z"
    }
    
    Target UI format (comp-24):
    {
        "bondName": "US Treasury 10Y",
        "points": [
            {
                "date": "2025-01-15",
                "price": 101.50
            }
        ]
    }
    """
    # Extract bond name from response or use provided
    name = bond_name
    if not name:
        name = api_response.get("bond_name", api_response.get("isin", "Bond"))
    
    points = []
    
    # Extract price data
    price_data = api_response.get("price_data", [])
    
    if isinstance(price_data, list):
        for item in price_data:
            if isinstance(item, dict):
                point = {
                    "date": item.get("date", item.get("timestamp", "")),
                    "price": item.get("price", item.get("clean_price", item.get("close", 0)))
                }
                points.append(point)
    
    # If no price_data, try alternative structures
    if not points:
        # Try 'data' key
        data = api_response.get("data", [])
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    point = {
                        "date": item.get("date", ""),
                        "price": item.get("price", item.get("close", 0))
                    }
                    points.append(point)
        
        # Try 'history' key
        if not points:
            history = api_response.get("history", api_response.get("price_history", []))
            if isinstance(history, list):
                for item in history:
                    if isinstance(item, dict):
                        point = {
                            "date": item.get("date", ""),
                            "price": item.get("price", item.get("clean_price", 0))
                        }
                        points.append(point)
        
        # Try 'prices' key
        if not points:
            prices = api_response.get("prices", [])
            if isinstance(prices, list):
                for idx, item in enumerate(prices):
                    if isinstance(item, dict):
                        point = {
                            "date": item.get("date", ""),
                            "price": item.get("price", 0)
                        }
                        points.append(point)
                    elif isinstance(item, (int, float)):
                        # Simple list of prices without dates
                        point = {
                            "date": "",
                            "price": item
                        }
                        points.append(point)
    
    return {
        "bondName": name,
        "points": points
    }
