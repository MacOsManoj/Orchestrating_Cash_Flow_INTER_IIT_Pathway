"""
Transformer for RateVsYieldChart (comp-23)
Maps /{isin}/rate-yield-overlay endpoint response to UI format
"""
from typing import Any


def transform(api_response: dict[str, Any], curve_name: str = "") -> dict[str, Any]:
    """
    Transform rate-yield-overlay API response to RateVsYieldChart format.
    
    Expected API response format (from bond_router.py RateYieldOverlayResponse):
    {
        "isin": "INE001A07RX9",
        "period": "1Y",
        "data": [
            {
                "date": "2025-01-15",
                "policy_rate": 6.50,
                "yield_10y": 7.25
            }
        ],
        "series": [
            {
                "key": "policy_rate",
                "label": "Policy Rate",
                "color": "#4CAF50"
            },
            {
                "key": "yield_10y",
                "label": "10Y Yield",
                "color": "#2196F3"
            }
        ],
        "y_axes": {...},
        "last_updated": "2025-01-15T10:30:00Z"
    }
    
    Target UI format (comp-23):
    {
        "curveName": "Credit Spread Curve",
        "points": [
            {
                "rate": 6.50,
                "yield": 7.25
            }
        ]
    }
    """
    # Extract curve name from response or use provided
    name = curve_name
    if not name:
        name = api_response.get("curve_name", api_response.get("name", "Rate vs Yield"))
    
    points = []
    
    # Extract data from response
    data = api_response.get("data", [])
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Map policy_rate to rate, yield_10y to yield
                point = {
                    "rate": item.get("policy_rate", item.get("rate", item.get("coupon_rate", 0))),
                    "yield": item.get("yield_10y", item.get("yield", item.get("ytm", 0)))
                }
                points.append(point)
    
    # If no data, try alternative structures
    if not points:
        # Try 'points' key directly
        points_data = api_response.get("points", [])
        if isinstance(points_data, list):
            for item in points_data:
                if isinstance(item, dict):
                    point = {
                        "rate": item.get("rate", item.get("x", 0)),
                        "yield": item.get("yield", item.get("y", 0))
                    }
                    points.append(point)
        
        # Try 'overlay' key
        if not points:
            overlay = api_response.get("overlay", api_response.get("curve_data", []))
            if isinstance(overlay, list):
                for item in overlay:
                    if isinstance(item, dict):
                        point = {
                            "rate": item.get("rate", item.get("policy_rate", 0)),
                            "yield": item.get("yield", item.get("yield_10y", 0))
                        }
                        points.append(point)
    
    return {
        "curveName": name,
        "points": points
    }
