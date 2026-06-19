"""
Bond Terms Card Transformer
============================

Transforms /bond/{isin} response to comp-15 (BondTermsCard) format.

API Response (BondDetails):
{
    "bond_name": str,
    "coupon_rate": float,
    "maturity_date": str,
    "next_coupon_date": str,
    "credit_rating": str,
    ...
}

Component Format:
{
    "bondName": "2026 8.50% GOI Bond",
    "couponRate": "8.50%",
    "maturityDate": "2040-10-15",
    "couponFrequency": "Semi-Annual",
    "credit_rating": "AAA"
}
"""

from typing import Dict, Any


def transform_bond_terms(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform bond/{isin} API response to BondTermsCard component format.
    
    Args:
        api_response: Bond details from /bond/{isin}
        **kwargs: Additional parameters (isin used at API call level)
    
    Returns:
        Component-ready JSON with bond terms
    """
    if not isinstance(api_response, dict):
        return {
            "bondName": "Unknown Bond",
            "couponRate": "N/A",
            "maturityDate": "N/A",
            "couponFrequency": "N/A",
            "credit_rating": "N/A"
        }
    
    # Extract bond name
    bond_name = api_response.get("bond_name", "Unknown Bond")
    
    # Extract and format coupon rate
    coupon_rate = api_response.get("coupon_rate")
    if coupon_rate is not None:
        try:
            coupon_rate_num = float(coupon_rate)
            # If it's already a percentage (>1), format directly
            if coupon_rate_num > 1:
                coupon_rate_str = f"{coupon_rate_num:.2f}%"
            else:
                # Convert decimal to percentage
                coupon_rate_str = f"{coupon_rate_num * 100:.2f}%"
        except (TypeError, ValueError):
            coupon_rate_str = str(coupon_rate)
    else:
        coupon_rate_str = "N/A"
    
    # Extract maturity date
    maturity_date = api_response.get("maturity_date", "N/A")
    
    # Extract coupon frequency (default to Semi-Annual for bonds)
    coupon_frequency = api_response.get("coupon_frequency", "Semi-Annual")
    
    # Extract credit rating
    credit_rating = api_response.get("credit_rating", "N/A")
    
    return {
        "bondName": bond_name,
        "couponRate": coupon_rate_str,
        "maturityDate": maturity_date,
        "couponFrequency": coupon_frequency,
        "credit_rating": credit_rating
    }
