"""
Pipeline Registry
=================

Configuration mapping pipelines to their FastAPI endpoints.
"""

from .schemas import Pipeline


# Base URL for the FastAPI backend
BACKEND_BASE_URL = "http://localhost:8000"

# Pipeline endpoint configuration
# Format: endpoint_name -> path (relative to base URL)
PIPELINE_ENDPOINTS = {
    Pipeline.FOREX: {
        "base_url": BACKEND_BASE_URL,
        "endpoints": {
            # Main Page endpoints
            "pairs": "/forex/v1/pairs",
            "recommended_trades": "/forex/v1/recommended-trades",
            "trade": "/forex/v1/trade",
            "portfolio": "/forex/v1/portfolio",
            "profit": "/forex/v1/profit",
            # Currency Page endpoints
            "price_data": "/forex/v1/currency/{pair}/price-data",
            "risk_metrics": "/forex/v1/currency/{pair}/risk-metrics",
            "exposure": "/forex/v1/currency/{pair}/portfolio-exposure",
            # Analysis endpoints
            "correlation": "/forex/v1/correlation-matrix",
            "trades_history": "/forex/v1/trades",
            "headline_sentiment": "/forex/news/headlines",
            # Pipeline/Agent endpoints
            "health": "/forex/health",
            "status": "/forex/status",
            "agent_query": "/forex/agent/query",
        },
        "description": "Forex pipeline for currency analysis, trends, and trading signals. Supports 6 pairs: EURINR, GBPINR, JPYINR, EURUSD, GBPUSD, USDJPY."
    },
    
    Pipeline.CASHFLOW: {
        "base_url": BACKEND_BASE_URL,
        "endpoints": {
            "query": "/api/cashflow/query",
            "opening_closing_balance": "/api/cashflow/ocbal",
            "liquidity_regime": "/api/cashflow/liqregime",
            "in_out_flow": "/api/cashflow/inandoutflow",
            "cash_balance_forecast": "/api/cashflow/cashbalanceforecast",
            "market_regime": "/api/cashflow/marketregime",
            "allocation": "/api/cashflow/orchestrator",
            "io": "/api/cashflow/io",
            # Portfolio endpoints (from portfolio_trades router)
            "current_distribution": "/api/portfolio/current-distribution",
            "initial_distribution": "/api/portfolio/initial-distribution",
        },
        "description": "Cashflow pipeline for liquidity management, cash balance forecasting, inflow/outflow analysis, market regime detection, portfolio distribution, and multi-asset portfolio allocation guidance."
    },
    
    Pipeline.STOCKS: {
        "base_url": "http://ec2-13-211-124-214.ap-southeast-2.compute.amazonaws.com:3000",  # External stock agent service
        "endpoints": {
            "query": "/query",  # POST endpoint - Returns full analysis with fundamental_agent, twitter_agent, etc.
        },
        "method_overrides": {
            "query": "POST"  # This endpoint requires POST with JSON body
        },
        "description": "Stocks pipeline for equity analysis including fundamentals, technicals, sentiment, and Monte Carlo simulations. Uses external stock agent service."
    },
    
    Pipeline.BONDS: {
        "base_url": BACKEND_BASE_URL,
        "endpoints": {
            "universe": "/api/bonds/universe",
            "bond_details": "/api/bonds/{isin}",  # Returns coupon_rate, maturity_date, credit_rating, dv01, clean_price, accrued_interest
            "yield_history": "/api/bonds/{isin}/yield-history",
            "rate_yield_overlay": "/api/bonds/{isin}/rate-yield-overlay",  # Returns policy_rate vs yield data
            "price_statistics": "/api/bonds/{isin}/price-statistics",
            "compare": "/api/bonds/compare",
            "chat": "/api/bonds/chat",  # POST endpoint for bond agent chat
        },
        "method_overrides": {
            "chat": "POST"  # This endpoint requires POST with JSON body {prompt, user_id}
        },
        "description": "Bonds pipeline for fixed income analysis including bond terms, pricing, risk metrics (DV01), and yield data."
    },
    
    Pipeline.NEWS: {
        "base_url": BACKEND_BASE_URL,
        "endpoints": {
            "summarized": "/api/news/summarized",  # Returns headline, source, published_at, sentiment_score, liquidity_impact
            "enriched": "/api/news/enriched",
            "clusters": "/api/news/clusters",
            "stats": "/api/news/stats",
        },
        "description": "News pipeline for financial news aggregation with sentiment analysis and liquidity impact assessment."
    },
}


def get_pipeline_description(pipeline: Pipeline) -> str:
    """Get the description for a pipeline (used in LLM prompts)."""
    return PIPELINE_ENDPOINTS.get(pipeline, {}).get("description", "")


def get_all_pipeline_descriptions() -> str:
    """Generate a formatted string of all pipeline descriptions for LLM context."""
    lines = []
    for pipeline, config in PIPELINE_ENDPOINTS.items():
        endpoints = ", ".join(config["endpoints"].keys())
        lines.append(f"- {pipeline.value.upper()}: {config['description']} Endpoints: [{endpoints}]")
    return "\n".join(lines)
