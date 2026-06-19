"""
Bond Risk Sensitivity Transformer
==================================

Transforms /bond/{isin} response to comp-6 (BondRiskSensitivity) format.
Extracts DV01 from bond risk metrics.

API Response (BondDetails):
{
    "bond_name": str,
    "dv01": float,
    ...
}

Component Format:
[
    {"bond_1 name": ["DV01 value"]},
    {"bond_2 name": ["DV01 value"]}
]
"""

from typing import Dict, Any, List


def transform_bond_risk_sensitivity(api_response: Any, **kwargs) -> List[Dict[str, List[str]]]:
    """
    Transform bond/{isin} API response to BondRiskSensitivity component format.
    
    Args:
        api_response: Bond details from /bond/{isin}
        **kwargs: Additional parameters (isin used at API call level)
    
    Returns:
        List of bond risk objects with bond name as key and DV01 as value
    """
    # Handle single bond response
    if isinstance(api_response, dict):
        bonds = [api_response]
    elif isinstance(api_response, list):
        bonds = api_response
    else:
        bonds = []
    
    result = []
    for bond in bonds:
        bond_name = bond.get("bond_name", "Unknown Bond")
        dv01 = bond.get("dv01", 0.0)
        
        # Format DV01 value - typically in INR
        if isinstance(dv01, (int, float)):
            dv01_formatted = f"₹{dv01:,.2f}"
        else:
            dv01_formatted = str(dv01)
        
        result.append({
            bond_name: [dv01_formatted]
        })
    
    return result
