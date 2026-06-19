"""
Transformer for BondYieldTimeChart (comp-22)
Maps /{isin}/yield-history endpoint response to UI format
"""
from typing import Any


def transform(api_response: dict[str, Any], bond_name: str = "") -> dict[str, Any]:
    """
    Transform yield-history API response to BondYieldTimeChart format.
    
    Expected API response format (from bond_router.py YieldHistoryResponse):
    {
        "isin": "INE001A07RX9",
        "period": "1Y",
        "yield_data": [
            {
                "date": "2025-01-15",
                "yield_value": 7.25,
                "time": "10:30:00"
            }
        ],
        "metrics": {
            "current_yield": 7.25,
            "one_month_change": -0.15,
            "volatility_20d": 0.08,
            "max_drawdown_1y": -0.35
        },
        "last_updated": "2025-01-15T10:30:00Z"
    }
    
    Target UI format (comp-22):
    {
        "bondName": "US 10Y Treasury",
        "points": [
            {
                "date": "2025-01-15",
                "yield": 4.25
            }
        ]
    }
    """
    # Extract bond name from response or use provided name
    name = bond_name
    if not name:
        name = api_response.get("bond_name", api_response.get("isin", "Bond"))
    
    points = []
    
    # Extract yield data
    yield_data = api_response.get("yield_data", [])
    
    if isinstance(yield_data, list):
        for item in yield_data:
            if isinstance(item, dict):
                point = {
                    "date": item.get("date", item.get("timestamp", "")),
                    "yield": item.get("yield_value", item.get("yield", item.get("ytm", 0)))
                }
                points.append(point)
    
    # If no yield_data, try alternative structures
    if not points:
        # Try 'data' key
        data = api_response.get("data", [])
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    point = {
                        "date": item.get("date", ""),
                        "yield": item.get("yield_value", item.get("yield", 0))
                    }
                    points.append(point)
        
        # Try 'history' key
        if not points:
            history = api_response.get("history", [])
            if isinstance(history, list):
                for item in history:
                    if isinstance(item, dict):
                        point = {
                            "date": item.get("date", ""),
                            "yield": item.get("yield", item.get("ytm", 0))
                        }
                        points.append(point)
    
    return {
        "bondName": name,
        "points": points
    }
