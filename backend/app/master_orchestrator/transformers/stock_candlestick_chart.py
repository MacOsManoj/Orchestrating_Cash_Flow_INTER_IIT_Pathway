"""
Transformer for StockCandlestickChart (comp-21)
Maps POST /query response to UI format
Extracts technical_output.json_data which contains OHLC data in timestamp-keyed format
"""
import json
import os
from typing import Any


def transform(api_response: dict[str, Any], base_path: str = "") -> dict[str, Any]:
    """
    Transform stock agent POST /query response to StockCandlestickChart format.
    
    This transformer:
    1. Handles nested response structure (data under 'response' key)
    2. Extracts technical_output.json_data which contains OHLC data
    3. Transforms the indicator data to candlestick chart format
    
    Expected API response format (from POST /query):
    {
        "success": true,
        "ticker": "RELIANCE",
        "response": {
            "technical_output": {
                "json_data": {
                    "2025-11-27 09:15:00 +0530": {
                        "date": "2025-11-27 09:15:00 +0530",
                        "open": 1575.25,
                        "high": 1575.25,
                        "low": 1564.85,
                        "close": 1567.4,
                        ...
                    }
                },
                "ticker": "RELIANCE",
                "signal": "HOLD",
                ...
            }
        }
    }
    
    Target UI format (comp-21):
    {
        "symbol": "RELIANCE",
        "points": [
            {
                "date": "2025-11-27",
                "high": 1575.25,
                "low": 1564.85,
                "open": 1575.25,
                "close": 1567.4
            }
        ]
    }
    """
    # Handle nested response structure (stock agent wraps data in 'response' key)
    response_data = api_response.get("response", api_response)
    
    # Get ticker from response
    symbol = api_response.get("ticker", "")
    if not symbol:
        symbol = response_data.get("tickers", ["STOCK"])[0] if response_data.get("tickers") else "STOCK"
    
    # Extract technical output
    technical_output = response_data.get("technical_output", {})
    
    # Get json_data which contains the OHLC data
    json_data = technical_output.get("json_data", {})
    
    # If json_data is empty, try csv_path as fallback
    if not json_data:
        csv_path = technical_output.get("csv_path", "")
        if csv_path:
            json_data = _try_read_json_file(csv_path, base_path)
    
    # Also try to get symbol from technical_output
    if not symbol or symbol == "STOCK":
        symbol = technical_output.get("ticker", symbol)
    
    # Transform the data to candlestick format
    points = _extract_candlestick_points(json_data)
    
    return {
        "symbol": symbol,
        "points": points
    }


def _try_read_json_file(csv_path: str, base_path: str = "") -> dict:
    """Try to read OHLC data from a JSON file."""
    if not csv_path:
        return {}
    
    full_path = csv_path
    if base_path and not os.path.isabs(csv_path):
        full_path = os.path.join(base_path, csv_path)
    
    try:
        with open(full_path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _extract_candlestick_points(json_data: dict) -> list:
    """
    Extract candlestick points from timestamp-keyed JSON data.
    
    Args:
        json_data: Dict with timestamp keys and OHLC values
        
    Returns:
        List of candlestick point dicts
    """
    points = []
    
    if not isinstance(json_data, dict):
        return points
    
    # Sort timestamps for chronological order
    sorted_timestamps = sorted(json_data.keys())
    
    for timestamp in sorted_timestamps:
        data = json_data[timestamp]
        if not isinstance(data, dict):
            continue
        
        # Extract date (e.g., "2025-11-27 09:15:00 +0530" -> "2025-11-27")
        date_str = data.get("date", timestamp)
        if " " in date_str:
            date_str = date_str.split(" ")[0]
        
        point = {
            "date": date_str,
            "high": data.get("high", 0),
            "low": data.get("low", 0),
            "open": data.get("open", 0),
            "close": data.get("close", 0)
        }
        points.append(point)
    
    return points


def transform_from_indicators_json(indicator_data: dict[str, Any], symbol: str = "") -> dict[str, Any]:
    """
    Direct transformation from indicator JSON data (already loaded).
    Useful when the JSON file is pre-loaded.
    
    Args:
        indicator_data: The loaded JSON data from TA_{SYMBOL}_indicators.json
        symbol: The stock symbol (optional, will be extracted if not provided)
    
    Returns:
        StockCandlestickChart formatted data
    """
    points = _extract_candlestick_points(indicator_data)
    
    return {
        "symbol": symbol or "STOCK",
        "points": points
    }