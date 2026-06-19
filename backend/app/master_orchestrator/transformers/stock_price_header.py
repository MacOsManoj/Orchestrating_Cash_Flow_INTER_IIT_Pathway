"""
Stock Price Header Transformer
===============================

Transforms POST /query response to comp-14 (StockPriceHeader) format.
Extracts price data from technical_output.json_data.

API Response (from POST /query):
{
    "success": true,
    "ticker": "RELIANCE",
    "response": {
        "technical_output": {
            "json_data": {
                "2025-12-05 15:15:00 +0530": {
                    "date": "2025-12-05 15:15:00 +0530",
                    "open": 1285.0,
                    "high": 1290.0,
                    "low": 1280.0,
                    "close": 1287.5,
                    ...
                }
            },
            "ticker": "RELIANCE",
            ...
        }
    }
}

Component Format:
{
    "stockName": str (from user query),
    "percentageChange": number,
    "absoluteChange": number,
    "timestamp": str,
    "currency": "INR",
    "exchange": "BSE"
}
"""

from typing import Dict, Any, List
from datetime import datetime


def transform_stock_price_header(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform POST /query API response to StockPriceHeader component format.
    
    Args:
        api_response: Full response from POST /query
        **kwargs: Must include stock_name extracted from user query
    
    Returns:
        Component-ready JSON with stock price header data
    """
    # stock_name must come from user query (passed via params)
    stock_name = kwargs.get("stock_name", "Unknown Stock")
    ticker = kwargs.get("ticker", "")
    
    # Handle nested response structure
    response_data = api_response.get("response", api_response) if isinstance(api_response, dict) else {}
    
    # Get ticker from response if not in kwargs
    if not ticker:
        ticker = api_response.get("ticker", "")
    if not ticker:
        tickers = response_data.get("tickers", [])
        ticker = tickers[0] if tickers else ""
    
    # If stock_name is same as ticker or empty, format it nicely
    if stock_name == ticker or not stock_name or stock_name == "Unknown Stock":
        stock_name = f"{ticker} Ltd" if ticker else "Unknown Stock"
    
    # Extract technical_output to get price data
    technical_output = response_data.get("technical_output", {})
    json_data = technical_output.get("json_data", {})
    
    # Get the latest data point from json_data
    pct_change = 0.0
    abs_change = 0.0
    timestamp = datetime.now().isoformat() + "Z"
    
    if json_data and isinstance(json_data, dict):
        # Sort timestamps and get the last two for calculating change
        sorted_timestamps = sorted(json_data.keys())
        if sorted_timestamps:
            latest_key = sorted_timestamps[-1]
            latest = json_data[latest_key]
            
            # Get timestamp from latest data
            date_str = latest.get("date", latest_key)
            if date_str:
                # Convert "2025-12-05 15:15:00 +0530" to ISO format
                try:
                    dt = datetime.strptime(date_str.split(" +")[0].split(" -")[0], "%Y-%m-%d %H:%M:%S")
                    timestamp = dt.isoformat() + "Z"
                except ValueError:
                    timestamp = date_str
            
            # Calculate price change if we have at least 2 data points
            if len(sorted_timestamps) >= 2:
                prev_key = sorted_timestamps[-2]
                prev = json_data[prev_key]
                
                current_close = latest.get("close", 0)
                prev_close = prev.get("close", 0)
                
                if prev_close and current_close:
                    abs_change = current_close - prev_close
                    pct_change = (abs_change / prev_close) * 100
    
    # Ensure numeric values
    try:
        pct_change = float(pct_change)
    except (TypeError, ValueError):
        pct_change = 0.0
    
    try:
        abs_change = float(abs_change)
    except (TypeError, ValueError):
        abs_change = 0.0
    
    return {
        "stockName": stock_name,
        "percentageChange": round(pct_change, 2),
        "absoluteChange": round(abs_change, 2),
        "timestamp": timestamp,
        "currency": "INR",
        "exchange": "BSE"
    }
