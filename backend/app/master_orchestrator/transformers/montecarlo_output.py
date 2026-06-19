"""
Monte Carlo Output Card Transformer
====================================

Transforms POST /query response to comp-7 (MonteCarloOutputCard) format.
Extracts montecarlo_output.results from the stock agent response.

API Response (from POST /query):
{
    "success": true,
    "ticker": "RELIANCE",
    "response": {
        "montecarlo_output": {
            "results": {
                "Min Return": -0.15,
                "Max Return": 0.35,
                "Mean Return": 0.08,
                "Median Return": 0.07,
                "Std Deviation": 0.12,
                "Probability of Loss": 0.25,
                "Num Simulations": 10000,
                "Num Days": 30,
                "ticker": "RELIANCE",
                "Analysis Date": "2025-12-07",
                "History Days": 365
            }
        },
        ...
    }
}

Component Format (comp-7):
{
    "results": {
        "Min Return": number,
        "Max Return": number,
        "Mean Return": number,
        "Median Return": number,
        "Std Deviation": number,
        "Probability of Loss": number,
        "Num Simulations": number,
        "Num Days": number,
        "ticker": string,
        "Analysis Date": string,
        "History Days": number
    }
}
"""

from typing import Dict, Any


def transform_montecarlo_output(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform stocks POST /query API response to MonteCarloOutputCard component format.
    
    Args:
        api_response: Full analysis response from POST /query
        **kwargs: ticker param may be passed
    
    Returns:
        Component-ready JSON with Monte Carlo simulation results
    """
    if not isinstance(api_response, dict):
        return {
            "results": _empty_results()
        }
    
    # Handle nested response structure (stock agent wraps data in 'response' key)
    response_data = api_response.get("response", api_response)
    
    # Extract montecarlo_output
    montecarlo_output = response_data.get("montecarlo_output", {})
    results = montecarlo_output.get("results", {})
    
    # Check if there's an error
    if results.get("error"):
        return {
            "results": {
                "error": results.get("error"),
                **_empty_results()
            }
        }
    
    # Get ticker from response or kwargs
    ticker = kwargs.get("ticker") or api_response.get("ticker", "")
    if not ticker:
        ticker = results.get("ticker", response_data.get("tickers", [""])[0] if response_data.get("tickers") else "")
    
    # Build the results object
    formatted_results = {
        "Min Return": _safe_number(results.get("Min Return")),
        "Max Return": _safe_number(results.get("Max Return")),
        "Mean Return": _safe_number(results.get("Mean Return")),
        "Median Return": _safe_number(results.get("Median Return")),
        "Std Deviation": _safe_number(results.get("Std Deviation")),
        "Probability of Loss": _safe_number(results.get("Probability of Loss")),
        "Num Simulations": _safe_int(results.get("Num Simulations", 10000)),
        "Num Days": _safe_int(results.get("Num Days", 30)),
        "ticker": ticker or results.get("ticker", ""),
        "Analysis Date": results.get("Analysis Date", ""),
        "History Days": _safe_int(results.get("History Days", 365))
    }
    
    return {
        "results": formatted_results
    }


def _empty_results() -> Dict[str, Any]:
    """Return empty/default results structure."""
    return {
        "Min Return": 0,
        "Max Return": 0,
        "Mean Return": 0,
        "Median Return": 0,
        "Std Deviation": 0,
        "Probability of Loss": 0,
        "Num Simulations": 0,
        "Num Days": 0,
        "ticker": "",
        "Analysis Date": "",
        "History Days": 0
    }


def _safe_number(value: Any) -> float:
    """Safely convert value to float."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    """Safely convert value to int."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
