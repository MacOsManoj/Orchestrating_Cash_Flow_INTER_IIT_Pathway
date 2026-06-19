import random
from ..schema import LiquidityRisk

def get_liquidity_risk():
    """
    Mock tool to get Cashflow Liquidity Risk.
    Returns a dict with 'liquidity_risk'.
    """
    risk = random.choice(list(LiquidityRisk))
    
    return {
        "liquidity_risk": risk
    }
