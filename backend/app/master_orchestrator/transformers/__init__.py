"""
Transformers Module
===================

Pure functions to transform FastAPI responses into component-ready JSON formats.
Each transformer maps API response data to the schema expected by frontend components.
"""

from .correlation_matrix import transform_correlation_matrix
from .allocation_dashboard import transform_allocation_dashboard
from .news_sentiment import transform_news_sentiment
from .alert_insights import transform_alert_insights
from .bond_risk_sensitivity import transform_bond_risk_sensitivity
from .cash_allocation import transform_cash_allocation
from .liquidity_dashboard import transform_liquidity_dashboard
from .fundamentals_card import transform_fundamentals_card
from .sentiment_analysis import transform_sentiment_analysis
from .stock_price_header import transform_stock_price_header
from .bond_terms import transform_bond_terms
from .bond_pricing import transform_bond_pricing
from .bond_chat_recommendations import transform_bond_chat_recommendations
from .cashflow_table import transform_cashflow_table
from .cash_balance_forecast_chart import transform as transform_cash_balance_forecast_chart
from .fx_price_chart import transform as transform_fx_price_chart
from .stock_candlestick_chart import transform as transform_stock_candlestick_chart
from .bond_yield_time_chart import transform as transform_bond_yield_time_chart
from .rate_vs_yield_chart import transform as transform_rate_vs_yield_chart
from .bond_price_time_chart import transform as transform_bond_price_time_chart
from .montecarlo_output import transform_montecarlo_output

__all__ = [
    # Forex transformers
    "transform_correlation_matrix",
    "transform_fx_price_chart",
    
    # Cashflow transformers
    "transform_allocation_dashboard",
    "transform_cash_allocation",
    "transform_liquidity_dashboard",
    "transform_cashflow_table",
    "transform_cash_balance_forecast_chart",
    
    # News transformers
    "transform_news_sentiment",
    "transform_alert_insights",
    
    # Stocks transformers
    "transform_fundamentals_card",
    "transform_sentiment_analysis",
    "transform_stock_price_header",
    "transform_stock_candlestick_chart",
    "transform_montecarlo_output",
    
    # Bonds transformers
    "transform_bond_risk_sensitivity",
    "transform_bond_terms",
    "transform_bond_pricing",
    "transform_bond_chat_recommendations",
    "transform_bond_yield_time_chart",
    "transform_rate_vs_yield_chart",
    "transform_bond_price_time_chart",
]
