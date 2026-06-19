"""
Bond Pricing Card Transformer
==============================

Transforms /bond/{isin} response to comp-16 (BondPricingCard) format.

API Response (BondDetails):
{
    "last_price": float,
    "clean_price": float,
    "accrued_interest": float,
    ...
}

Component Format:
{
    "lastPrice": number,
    "cleanPrice": number,
    "accruedInterest": number
}
"""

from typing import Dict, Any


def transform_bond_pricing(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform bond/{isin} API response to BondPricingCard component format.
    
    Args:
        api_response: Bond details from /bond/{isin}
        **kwargs: Additional parameters (isin used at API call level)
    
    Returns:
        Component-ready JSON with bond pricing data
    """
    if not isinstance(api_response, dict):
        return {
            "lastPrice": 0.0,
            "cleanPrice": 0.0,
            "accruedInterest": 0.0
        }
    
    # Helper function to safely extract numeric values
    def safe_float(val, default=0.0):
        if val is None:
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default
    
    # Extract pricing data
    last_price = safe_float(api_response.get("last_price"))
    clean_price = safe_float(api_response.get("clean_price"))
    accrued_interest = safe_float(api_response.get("accrued_interest"))
    
    return {
        "lastPrice": round(last_price, 2),
        "cleanPrice": round(clean_price, 2),
        "accruedInterest": round(accrued_interest, 4)
    }
