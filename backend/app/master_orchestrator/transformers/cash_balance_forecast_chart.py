"""
Transformer for CashBalanceForecastChart (comp-19)
Maps /cashbalanceforecast endpoint response to UI format
"""
from typing import Any


def transform(api_response: dict[str, Any]) -> dict[str, Any]:
    """
    Transform cashbalanceforecast API response to CashBalanceForecastChart format.
    
    Expected API response format:
    {
        "result": [
            {"day": 0, "balance": 22000000, "date": "2025-01-15"},
            {"day": 1, "balance": 22500000, "date": "2025-01-16"},
            ...
        ]
    }
    
    Target UI format (comp-19):
    {
        "points": [
            {
                "day": 0,
                "amount": 22000000,
                "date": "2025-01-15"
            }
        ]
    }
    """
    result = api_response.get("result", [])
    
    # Handle if result is a dict with nested data
    if isinstance(result, dict):
        # Try to extract forecast data from various possible keys
        forecast_data = result.get("forecast", result.get("data", []))
        if isinstance(forecast_data, list):
            result = forecast_data
    
    points = []
    for idx, item in enumerate(result):
        if isinstance(item, dict):
            point = {
                "day": item.get("day", idx),
                "amount": item.get("balance", item.get("amount", item.get("cash_balance", 0))),
                "date": item.get("date", item.get("forecast_date", ""))
            }
            points.append(point)
        elif isinstance(item, (int, float)):
            # Simple list of amounts
            points.append({
                "day": idx,
                "amount": item,
                "date": ""
            })
    
    # If no points found, try alternative parsing
    if not points and isinstance(api_response, dict):
        # Try to parse from different response structures
        for key in ["forecast", "cashflow_forecast", "balance_forecast", "data"]:
            if key in api_response and isinstance(api_response[key], list):
                for idx, item in enumerate(api_response[key]):
                    if isinstance(item, dict):
                        point = {
                            "day": item.get("day", idx),
                            "amount": item.get("balance", item.get("amount", 0)),
                            "date": item.get("date", "")
                        }
                        points.append(point)
                break
    
    return {
        "points": points
    }
