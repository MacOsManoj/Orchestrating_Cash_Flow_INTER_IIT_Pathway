"""
Correlation Matrix Transformer
==============================

Transforms FastAPI /forex/api/v1/correlation-matrix response 
into CorrelationMatrixFX component format (comp-2).
"""

from typing import Dict, Any, List


def transform_correlation_matrix(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform correlation matrix API response to component format.
    
    API Response Format (from /forex/v1/correlation-matrix):
    {
        "pairs": ["EURINR", "GBPINR", ...],
        "matrix": [[1.0, 0.85, ...], [0.85, 1.0, ...], ...],
        "period_days": 60,
        "timestamp": "2025-12-06T..."
    }
    
    Component Format (comp-2 - CorrelationMatrixFX):
    {
        "labels": ["EUR/INR", "GBP/INR", ...],
        "matrix": [[1.0, 0.85, ...], [0.85, 1.0, ...], ...]
    }
    
    Args:
        api_response: Raw response from the correlation matrix endpoint.
        
    Returns:
        Dict formatted for CorrelationMatrixFX component.
        
    Raises:
        ValueError: If required fields are missing from API response.
    """
    # Handle case where api_response might have an error
    if isinstance(api_response, dict) and api_response.get("error"):
        raise ValueError(f"API returned error: {api_response.get('message', 'Unknown error')}")
    
    # Extract matrix from response
    matrix = api_response.get("matrix")
    
    if matrix is None:
        raise ValueError("API response missing 'matrix' field")
    
    if not isinstance(matrix, list):
        raise ValueError(f"Expected 'matrix' to be a list, got {type(matrix).__name__}")
    
    # Validate matrix structure (should be 2D list of numbers)
    for i, row in enumerate(matrix):
        if not isinstance(row, list):
            raise ValueError(f"Matrix row {i} is not a list")
        for j, val in enumerate(row):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Matrix value at [{i}][{j}] is not a number")
    
    # Extract currency pair labels from API response
    pairs = api_response.get("pairs", [])
    
    # Convert pairs to display format (e.g., "EURINR" -> "EUR/INR")
    labels = _format_currency_labels(pairs)
    
    # Default labels if not provided by API
    if not labels:
        labels = ["EUR/INR", "GBP/INR", "JPY/INR", "GBP/USD", "EUR/USD", "USD/JPY"]
    
    # Return component-ready format with labels
    return {
        "labels": labels,
        "matrix": matrix
    }


def _format_currency_labels(pairs: List[str]) -> List[str]:
    """
    Convert API pair format to display format.
    
    E.g., "EURINR" -> "EUR/INR", "GBPUSD" -> "GBP/USD"
    
    Args:
        pairs: List of currency pair codes from API
        
    Returns:
        List of formatted currency pair labels
    """
    formatted = []
    for pair in pairs:
        if not pair:
            continue
        pair = pair.upper()
        # Try to split 6-character codes (e.g., EURINR, GBPUSD)
        if len(pair) == 6:
            formatted.append(f"{pair[:3]}/{pair[3:]}")
        # Try to split 7-character codes (e.g., USDJPY)
        elif len(pair) == 7:
            # Handle cases like EUR/USD that might come as EURUSD
            formatted.append(f"{pair[:3]}/{pair[3:]}")
        # If already has separator
        elif "/" in pair:
            formatted.append(pair)
        else:
            formatted.append(pair)
    return formatted


def get_correlation_matrix_metadata(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from correlation matrix response (for debugging/logging).
    
    Args:
        api_response: Raw response from the correlation matrix endpoint.
        
    Returns:
        Dict with metadata like pairs, period_days, timestamp.
    """
    return {
        "pairs": api_response.get("pairs", []),
        "period_days": api_response.get("period_days"),
        "timestamp": api_response.get("timestamp")
    }
