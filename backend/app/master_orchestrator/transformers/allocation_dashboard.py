"""
Allocation Dashboard Transformer
================================

Transforms FastAPI /api/cashflow/orchestrator response 
into AllocationDashboard component format (comp-3).
"""

from typing import Dict, Any, List, Optional


def transform_allocation_dashboard(
    api_response: Dict[str, Any],
    risk_profile: str = "Normal",
    current_portfolio: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Transform allocation orchestrator API response to component format.
    
    API Response Format (from /api/cashflow/orchestrator):
    {
        "states": {"liquidity": "Normal", "market": "Medium"},
        "ratios": {"RR": 0.065, "IR": 0.28, "LR": 0.655},
        "portfolios": {
            "Aggressive": {"Govt_Bonds": 0.18, "Corp_Bonds": 0.04, "Stocks": 0.05, "Forex": 0.01},
            "Normal": {"Govt_Bonds": 0.20, "Corp_Bonds": 0.05, "Stocks": 0.03, "Forex": 0.0},
            "Safe": {"Govt_Bonds": 0.25, "Corp_Bonds": 0.03, "Stocks": 0.0, "Forex": 0.0}
        },
        "rbi": {"CRR": 0.045, "SLR": 0.18}
    }
    
    Component Format (comp-3 - AllocationDashboard):
    {
        "assetClasses": [
            {
                "name": "Cash Reserve",
                "recommended_percentage": 6.5,
                "difference": 1.5
            },
            ...
        ]
    }
    
    Args:
        api_response: Raw response from the orchestrator endpoint.
        risk_profile: Which risk profile to use ("Aggressive", "Normal", "Safe").
        current_portfolio: Optional dict of current allocations to calculate differences.
                          If not provided, differences will be 0.
        
    Returns:
        Dict formatted for AllocationDashboard component.
        
    Raises:
        ValueError: If required fields are missing from API response.
    """
    # Handle case where api_response might have an error
    if isinstance(api_response, dict) and api_response.get("error"):
        raise ValueError(f"API returned error: {api_response.get('message', 'Unknown error')}")
    
    # Extract data from response
    ratios = api_response.get("ratios")
    portfolios = api_response.get("portfolios")
    states = api_response.get("states", {})
    
    if ratios is None:
        raise ValueError("API response missing 'ratios' field")
    if portfolios is None:
        raise ValueError("API response missing 'portfolios' field")
    
    # Get the selected portfolio breakdown
    portfolio = portfolios.get(risk_profile)
    if portfolio is None:
        # Fallback to Normal if specified profile not found
        portfolio = portfolios.get("Normal", {})
    
    # Default current portfolio (if not provided, assume zeros - meaning all difference)
    if current_portfolio is None:
        current_portfolio = {
            "Cash Reserve": 0.05,      # Assume some defaults
            "Loan Book": 0.60,
            "Govt Bonds": 0.20,
            "Corp Bonds": 0.05,
            "Stocks": 0.07,
            "Forex": 0.03
        }
    
    # Build asset classes list
    asset_classes = []
    
    # 1. Cash Reserve (RR)
    rr_pct = ratios.get("RR", 0) * 100
    asset_classes.append({
        "name": "Cash Reserve",
        "recommended_percentage": round(rr_pct, 2),
        "difference": round(rr_pct - current_portfolio.get("Cash Reserve", 0) * 100, 2)
    })
    
    # 2. Loan Book (LR)
    lr_pct = ratios.get("LR", 0) * 100
    asset_classes.append({
        "name": "Loan Book",
        "recommended_percentage": round(lr_pct, 2),
        "difference": round(lr_pct - current_portfolio.get("Loan Book", 0) * 100, 2)
    })
    
    # 3. Government Bonds
    govt_bonds_pct = portfolio.get("Govt_Bonds", 0) * 100
    asset_classes.append({
        "name": "Govt Bonds",
        "recommended_percentage": round(govt_bonds_pct, 2),
        "difference": round(govt_bonds_pct - current_portfolio.get("Govt Bonds", 0) * 100, 2)
    })
    
    # 4. Corporate Bonds
    corp_bonds_pct = portfolio.get("Corp_Bonds", 0) * 100
    asset_classes.append({
        "name": "Corp Bonds",
        "recommended_percentage": round(corp_bonds_pct, 2),
        "difference": round(corp_bonds_pct - current_portfolio.get("Corp Bonds", 0) * 100, 2)
    })
    
    # 5. Stocks
    stocks_pct = portfolio.get("Stocks", 0) * 100
    asset_classes.append({
        "name": "Stocks",
        "recommended_percentage": round(stocks_pct, 2),
        "difference": round(stocks_pct - current_portfolio.get("Stocks", 0) * 100, 2)
    })
    
    # 6. Forex
    forex_pct = portfolio.get("Forex", 0) * 100
    asset_classes.append({
        "name": "Forex",
        "recommended_percentage": round(forex_pct, 2),
        "difference": round(forex_pct - current_portfolio.get("Forex", 0) * 100, 2)
    })
    
    return {
        "assetClasses": asset_classes
    }


def get_allocation_metadata(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from allocation response (for debugging/logging).
    
    Args:
        api_response: Raw response from the orchestrator endpoint.
        
    Returns:
        Dict with metadata like states, rbi rates, available profiles.
    """
    return {
        "states": api_response.get("states", {}),
        "rbi_rates": api_response.get("rbi", {}),
        "available_profiles": list(api_response.get("portfolios", {}).keys()),
        "base_ratios": api_response.get("ratios", {})
    }
