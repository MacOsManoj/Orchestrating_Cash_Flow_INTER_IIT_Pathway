"""
Cash Allocation Transformer
===========================

Transforms /api/cashflow/query response to comp-9 (CashAllocationCard) format.

API Response (expected from /query):
{
    "free_cash": float,
    "invested_amount": float,
    ...
}

Component Format:
{
    "title": "Cash & Investments",
    "subtitle": "Across all asset classes",
    "freeCashLabel": "Free Cash Available",
    "investedLabel": "Amount Invested",
    "freeCashAmount": number,
    "investedAmount": number,
    "currencySymbol": "₹"
}
"""

from typing import Dict, Any


def transform_cash_allocation(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform cashflow/query API response to CashAllocationCard component format.
    
    Args:
        api_response: Response from /api/cashflow/query
        **kwargs: Additional parameters
    
    Returns:
        Component-ready JSON with cash allocation data
    """
    if not isinstance(api_response, dict):
        api_response = {}
    
    # Extract values from various possible field names
    free_cash = (
        api_response.get("free_cash") or 
        api_response.get("freeCash") or 
        api_response.get("available_cash") or
        api_response.get("cash_available") or
        0.0
    )
    
    invested = (
        api_response.get("invested_amount") or 
        api_response.get("investedAmount") or
        api_response.get("total_invested") or
        api_response.get("amount_invested") or
        0.0
    )
    
    # Ensure numeric values
    try:
        free_cash = float(free_cash)
    except (TypeError, ValueError):
        free_cash = 0.0
    
    try:
        invested = float(invested)
    except (TypeError, ValueError):
        invested = 0.0
    
    return {
        "title": "Cash & Investments",
        "subtitle": "Across all asset classes",
        "freeCashLabel": "Free Cash Available",
        "investedLabel": "Amount Invested",
        "freeCashAmount": free_cash,
        "investedAmount": invested,
        "currencySymbol": "₹"
    }
