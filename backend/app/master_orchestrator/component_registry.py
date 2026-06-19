"""
Component Registry
==================

Maps UI components to their required API endpoints and transformers.
This is the rule-based mapping layer of the hybrid architecture.

Each component defines:
- type: Component type name (matches frontend component)
- description: What the component shows (used by LLM for selection)
- pipeline: Which pipeline this component belongs to
- endpoints: List of API endpoints to call
- transformer: Function to transform API response to component format
- params: Parameters that can be extracted from user query
"""

from typing import Dict, Any, List, Callable, Optional
from enum import Enum

from .schemas import Pipeline
from .transformers import (
    transform_correlation_matrix,
    transform_allocation_dashboard,
    transform_news_sentiment,
    transform_alert_insights,
    transform_bond_risk_sensitivity,
    transform_cash_allocation,
    transform_liquidity_dashboard,
    transform_fundamentals_card,
    transform_sentiment_analysis,
    transform_stock_price_header,
    transform_bond_terms,
    transform_bond_pricing,
    transform_bond_chat_recommendations,
    transform_cashflow_table,
    transform_cash_balance_forecast_chart,
    transform_fx_price_chart,
    transform_stock_candlestick_chart,
    transform_bond_yield_time_chart,
    transform_rate_vs_yield_chart,
    transform_bond_price_time_chart,
    transform_montecarlo_output,
)


class ComponentType(str, Enum):
    """Available UI components."""
    NEWS_SENTIMENT_STREAM = "NewsSentimentStream"
    CORRELATION_MATRIX_FX = "CorrelationMatrixFX"
    ALLOCATION_DASHBOARD = "AllocationDashboard"
    OPTIMIZATION_CARD = "OptimizationCard"
    ALERT_INSIGHTS = "AlertInsights"
    BOND_RISK_SENSITIVITY = "BondRiskSensitivity"
    MONTE_CARLO_OUTPUT_CARD = "MonteCarloOutputCard"
    ASSET_PERFORMANCE = "AssetPerformance"
    CASH_ALLOCATION_CARD = "CashAllocationCard"
    LIQUIDITY_DASHBOARD = "LiquidityDashboard"
    FUNDAMENTALS_CARD = "FundamentalsCard"
    SENTIMENT_ANALYSIS_CARD = "SentimentAnalysisCard"
    CURRENT_VALUE_CARD = "CurrentValueCard"
    STOCK_PRICE_HEADER = "StockPriceHeader"
    BOND_TERMS_CARD = "BondTermsCard"
    BOND_PRICING_CARD = "BondPricingCard"
    CASHFLOW_TABLE = "CashFlowTable"
    CASH_BALANCE_FORECAST_CHART = "CashBalanceForecastChart"
    FX_PRICE_CHART = "FxPriceChart"
    STOCK_CANDLESTICK_CHART = "StockCandlestickChart"
    BOND_YIELD_TIME_CHART = "BondYieldTimeChart"
    RATE_VS_YIELD_CHART = "RateVsYieldChart"
    BOND_PRICE_TIME_CHART = "BondPriceTimeChart"


# Component configuration registry
# Maps component ID to its configuration
COMPONENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # comp-1: NewsSentimentStream
    # Maps to: /api/news/summarized
    # =========================================================================
    "comp-1": {
        "type": ComponentType.NEWS_SENTIMENT_STREAM,
        "description": "Shows a stream of news headlines relevant to assets along with sentiment scores.",
        "pipeline": Pipeline.NEWS,
        "endpoints": ["summarized"],
        "transformer": transform_news_sentiment,
        "params": ["company"],  # Can filter by company from query
        "keywords": ["news", "sentiment", "headlines", "market news", "forex news", "stock news"]
    },
    
    # =========================================================================
    # comp-2: CorrelationMatrixFX
    # Maps to: /forex/api/v1/correlation-matrix
    # =========================================================================
    "comp-2": {
        "type": ComponentType.CORRELATION_MATRIX_FX,
        "description": "Shows correlation between various forex currency pairs. Displays a matrix showing how EUR/INR, GBP/INR, JPY/INR, GBP/USD, EUR/USD, and USD/JPY correlate with each other.",
        "pipeline": Pipeline.FOREX,
        "endpoints": ["correlation"],
        "transformer": transform_correlation_matrix,
        "params": [],
        "keywords": ["correlation", "matrix", "forex correlation", "currency correlation", "pair correlation", "how correlated"]
    },
    
    # =========================================================================
    # comp-3: AllocationDashboard
    # Maps to: /api/cashflow/orchestrator
    # =========================================================================
    "comp-3": {
        "type": ComponentType.ALLOCATION_DASHBOARD,
        "description": "Shows recommended allocation across asset classes including Cash Reserve, Loan Book, Govt Bonds, Corp Bonds, Stocks, and Forex. Based on current market regime and liquidity conditions.",
        "pipeline": Pipeline.CASHFLOW,
        "endpoints": ["allocation"],
        "transformer": transform_allocation_dashboard,
        "params": ["risk_profile"],  # Aggressive/Normal/Safe extracted from query
        "keywords": ["allocation", "portfolio allocation", "asset allocation", "recommended allocation", "how to allocate", "portfolio split", "investment split", "multi-asset", "asset mix"]
    },
    
    # =========================================================================
    # comp-5: AlertInsights
    # Maps to: /api/news/summarized with severity filter
    # =========================================================================
    "comp-5": {
        "type": ComponentType.ALERT_INSIGHTS,
        "description": "Shows critical alerts relevant to forex trading, stocks, or bonds with severity levels (critical, warning, info).",
        "pipeline": Pipeline.NEWS,
        "endpoints": ["summarized"],
        "transformer": transform_alert_insights,
        "params": ["company", "liquidity_impact"],
        "keywords": ["alerts", "warnings", "critical", "risk alerts", "market alerts", "high impact", "urgent"]
    },
    
    # =========================================================================
    # comp-6: BondRiskSensitivity
    # Maps to: /bond/{isin} - extracts DV01 from risk metrics
    # =========================================================================
    "comp-6": {
        "type": ComponentType.BOND_RISK_SENSITIVITY,
        "description": "Shows the DV01 (Dollar Value of 01) for bonds - how much the bond price changes for a 1bp move in yield.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["bond_details"],
        "transformer": transform_bond_risk_sensitivity,
        "params": ["isin"],  # Bond ISIN extracted from query
        "keywords": ["bond risk", "DV01", "bond sensitivity", "interest rate risk", "duration risk"]
    },
    
    # =========================================================================
    # comp-7: MonteCarloOutputCard
    # Maps to: POST /query - extracts montecarlo_output.results
    # =========================================================================
    "comp-7": {
        "type": ComponentType.MONTE_CARLO_OUTPUT_CARD,
        "description": "Displays Monte Carlo simulation metrics for a stock including min/max/mean/median return, standard deviation, probability of loss, and simulation parameters.",
        "pipeline": Pipeline.STOCKS,
        "endpoints": ["query"],
        "transformer": transform_montecarlo_output,
        "params": ["ticker"],  # Stock ticker extracted from query
        "keywords": ["monte carlo", "simulation", "probability", "risk analysis", "return distribution", "forecast", "VaR", "value at risk"]
    },
    
    # =========================================================================
    # comp-9: CashAllocationCard
    # Maps to: /api/portfolio/current-distribution - returns free cash and invested amounts
    # =========================================================================
    "comp-9": {
        "type": ComponentType.CASH_ALLOCATION_CARD,
        "description": "Shows portfolio-level free cash available and amount invested across all asset classes.",
        "pipeline": Pipeline.CASHFLOW,
        "endpoints": ["current_distribution"],
        "transformer": transform_cash_allocation,
        "params": [],
        "keywords": ["cash", "free cash", "invested", "cash position", "available cash", "investment amount"]
    },
    
    # =========================================================================
    # comp-10: LiquidityDashboard
    # Maps to: /api/cashflow/ocbal + /api/cashflow/cashbalanceforecast
    # Multi-endpoint component - orchestrator fetches all and combines
    # =========================================================================
    "comp-10": {
        "type": ComponentType.LIQUIDITY_DASHBOARD,
        "description": "Displays high-level liquidity metrics including Cash Flow Forecast, Liquidity Coverage Ratio (LCR), and Total Cash Position.",
        "pipeline": Pipeline.CASHFLOW,
        "endpoints": ["opening_closing_balance", "cash_balance_forecast"],  # Multiple endpoints
        "transformer": transform_liquidity_dashboard,
        "params": [],
        "keywords": ["liquidity", "LCR", "liquidity ratio", "cash flow forecast", "cash position", "liquidity metrics"]
    },
    
    # =========================================================================
    # comp-11: FundamentalsCard
    # Maps to: POST /query - extracts fundamental_output from response
    # =========================================================================
    "comp-11": {
        "type": ComponentType.FUNDAMENTALS_CARD,
        "description": "Shows fundamental and technical metrics for a stock including P/E ratio, EPS, revenue, EBITDA, and technical signals like RSI and MACD.",
        "pipeline": Pipeline.STOCKS,
        "endpoints": ["query"],
        "transformer": transform_fundamentals_card,
        "params": ["ticker"],  # Stock ticker extracted from query
        "keywords": ["fundamentals", "P/E", "EPS", "revenue", "EBITDA", "stock analysis", "financial metrics", "balance sheet", "income statement"]
    },
    
    # =========================================================================
    # comp-12: SentimentAnalysisCard
    # Maps to: POST /query - extracts twitter_output sentiment
    # =========================================================================
    "comp-12": {
        "type": ComponentType.SENTIMENT_ANALYSIS_CARD,
        "description": "Displays sentiment score and reasoning from Twitter/social media analysis for a stock.",
        "pipeline": Pipeline.STOCKS,
        "endpoints": ["query"],
        "transformer": transform_sentiment_analysis,
        "params": ["ticker"],  # Stock ticker extracted from query
        "keywords": ["sentiment", "twitter sentiment", "social sentiment", "market sentiment", "bullish", "bearish", "social media"]
    },
    
    # =========================================================================
    # comp-14: StockPriceHeader
    # Maps to: POST /query - extracts price data from technical_output
    # =========================================================================
    "comp-14": {
        "type": ComponentType.STOCK_PRICE_HEADER,
        "description": "Shows stock name, daily price movement (percentage and absolute change), and timestamp. Currency is INR, exchange is BSE.",
        "pipeline": Pipeline.STOCKS,
        "endpoints": ["query"],
        "transformer": transform_stock_price_header,
        "params": ["ticker", "stock_name"],  # stock_name must be extracted from query
        "keywords": ["stock price", "price header", "stock quote", "current price", "price change", "daily change"]
    },
    
    # =========================================================================
    # comp-15: BondTermsCard
    # Maps to: /bond/{isin}
    # =========================================================================
    "comp-15": {
        "type": ComponentType.BOND_TERMS_CARD,
        "description": "Displays key bond terms including coupon rate, maturity date, coupon frequency, and credit rating.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["bond_details"],
        "transformer": transform_bond_terms,
        "params": ["isin"],  # Bond ISIN extracted from query
        "keywords": ["bond terms", "coupon", "maturity", "bond details", "credit rating", "bond info"]
    },
    
    # =========================================================================
    # comp-16: BondPricingCard
    # Maps to: /bond/{isin}
    # =========================================================================
    "comp-16": {
        "type": ComponentType.BOND_PRICING_CARD,
        "description": "Shows bond pricing information including last price, clean price, and accrued interest.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["bond_details"],
        "transformer": transform_bond_pricing,
        "params": ["isin"],  # Bond ISIN extracted from query
        "keywords": ["bond price", "bond pricing", "clean price", "dirty price", "accrued interest", "bond quote"]
    },
    
    # =========================================================================
    # comp-16b: BondChatRecommendations
    # Maps to: POST /api/bonds/chat
    # Special component that extracts ISINs from chat recommendations and
    # creates multiple BondTermsCard and BondPricingCard components
    # =========================================================================
    "comp-16b": {
        "type": ComponentType.BOND_TERMS_CARD,  # Will return multiple components
        "description": "Processes bond chat recommendations, extracts ISINs, and displays bond terms and pricing for each recommended bond. Returns multiple BondTermsCard and BondPricingCard components.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["chat"],  # POST endpoint
        "transformer": transform_bond_chat_recommendations,
        "params": [],  # No params needed - uses chat response
        "keywords": ["bond recommendations", "bond chat", "recommend bonds", "suggest bonds", "bond advice", "bond suggestions", "which bonds", "bond portfolio"]
    },
    
    # =========================================================================
    # comp-17: CashFlowTable
    # Maps to: /api/cashflow/inandoutflow
    # =========================================================================
    "comp-17": {
        "type": ComponentType.CASHFLOW_TABLE,
        "description": "Shows period-wise cash inflows, outflows, net cash flow, opening/ending balances, and LCR percentage.",
        "pipeline": Pipeline.CASHFLOW,
        "endpoints": ["in_out_flow"],
        "transformer": transform_cashflow_table,
        "params": [],
        "keywords": ["cash flow", "inflows", "outflows", "cash table", "cash balance", "LCR", "treasury"]
    },
    
    # =========================================================================
    # comp-19: CashBalanceForecastChart
    # Maps to: /api/cashflow/cashbalanceforecast
    # =========================================================================
    "comp-19": {
        "type": ComponentType.CASH_BALANCE_FORECAST_CHART,
        "description": "Shows a 30-day projected cash balance trend chart.",
        "pipeline": Pipeline.CASHFLOW,
        "endpoints": ["cash_balance_forecast"],
        "transformer": transform_cash_balance_forecast_chart,
        "params": [],
        "keywords": ["cash forecast", "balance forecast", "cash projection", "30 day forecast", "cash trend", "projected balance"]
    },
    
    # =========================================================================
    # comp-20: FxPriceChart
    # Maps to: /forex/api/v1/currency/{pair}/price-data
    # =========================================================================
    "comp-20": {
        "type": ComponentType.FX_PRICE_CHART,
        "description": "Shows the FX rate over time for a specific currency pair (e.g., EUR/USD, GBP/INR).",
        "pipeline": Pipeline.FOREX,
        "endpoints": ["price_data"],
        "transformer": transform_fx_price_chart,
        "params": ["currency_pair"],  # Currency pair extracted from query
        "keywords": ["fx chart", "forex chart", "currency chart", "exchange rate chart", "price history", "rate trend", "EUR/USD", "GBP/INR"]
    },
    
    # =========================================================================
    # comp-21: StockCandlestickChart
    # Maps to: POST /query → extract technical_output.json_data for OHLC data
    # =========================================================================
    "comp-21": {
        "type": ComponentType.STOCK_CANDLESTICK_CHART,
        "description": "Renders a candlestick chart showing high/low/open/close for each day for a stock.",
        "pipeline": Pipeline.STOCKS,
        "endpoints": ["query"],
        "transformer": transform_stock_candlestick_chart,
        "params": ["ticker"],  # Stock ticker extracted from query
        "keywords": ["candlestick", "stock chart", "OHLC", "price chart", "technical chart", "stock candlestick", "daily chart"]
    },
    
    # =========================================================================
    # comp-22: BondYieldTimeChart
    # Maps to: /bond/{isin}/yield-history
    # =========================================================================
    "comp-22": {
        "type": ComponentType.BOND_YIELD_TIME_CHART,
        "description": "Shows the bond yield over time (1Y window) as a line chart.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["yield_history"],
        "transformer": transform_bond_yield_time_chart,
        "params": ["isin"],  # Bond ISIN extracted from query
        "keywords": ["yield chart", "yield history", "bond yield trend", "yield over time", "yield graph"]
    },
    
    # =========================================================================
    # comp-23: RateVsYieldChart
    # Maps to: /bond/{isin}/rate-yield-overlay
    # =========================================================================
    "comp-23": {
        "type": ComponentType.RATE_VS_YIELD_CHART,
        "description": "Shows the relationship between policy rate and yield as a scatter/curve chart.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["rate_yield_overlay"],
        "transformer": transform_rate_vs_yield_chart,
        "params": ["isin"],  # Bond ISIN extracted from query
        "keywords": ["rate vs yield", "rate yield curve", "credit spread", "policy rate", "yield overlay", "rate comparison"]
    },
    
    # =========================================================================
    # comp-24: BondPriceTimeChart
    # Maps to: /bond/{isin}/price-statistics
    # =========================================================================
    "comp-24": {
        "type": ComponentType.BOND_PRICE_TIME_CHART,
        "description": "Shows the bond price over time (1Y) as a line chart.",
        "pipeline": Pipeline.BONDS,
        "endpoints": ["price_statistics"],
        "transformer": transform_bond_price_time_chart,
        "params": ["isin"],  # Bond ISIN extracted from query
        "keywords": ["bond price chart", "price history", "bond price trend", "price over time", "bond graph"]
    },
}


# =========================================================================
# COMPONENTS ON HOLD (comp-4, comp-8, comp-13)
# These will be implemented separately per user request
# =========================================================================
# comp-4: OptimizationCard - waiting for specific endpoint
# comp-8: AssetPerformance - waiting for specific mapping
# comp-13: CurrentValueCard - waiting for specific mapping


def get_component_config(component_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific component."""
    return COMPONENT_REGISTRY.get(component_id)


def get_components_for_pipeline(pipeline: Pipeline) -> List[str]:
    """Get all component IDs that belong to a specific pipeline."""
    return [
        comp_id 
        for comp_id, config in COMPONENT_REGISTRY.items() 
        if config["pipeline"] == pipeline
    ]


def get_component_descriptions_for_llm() -> str:
    """
    Generate a formatted string of all component descriptions for LLM context.
    Used by the Component Selector to understand what each component does.
    """
    lines = []
    for comp_id, config in COMPONENT_REGISTRY.items():
        comp_type = config["type"].value if isinstance(config["type"], Enum) else config["type"]
        params = config.get("params", [])
        param_str = f" [Params: {', '.join(params)}]" if params else ""
        lines.append(f"- {comp_id} ({comp_type}): {config['description']}{param_str}")
    return "\n".join(lines)


def get_ready_components() -> List[str]:
    """Get list of component IDs that have transformers implemented (ready to use)."""
    return [
        comp_id 
        for comp_id, config in COMPONENT_REGISTRY.items() 
        if config["transformer"] is not None
    ]


def get_component_params(component_id: str) -> List[str]:
    """Get the list of parameters that a component expects from the query."""
    config = COMPONENT_REGISTRY.get(component_id)
    return config.get("params", []) if config else []
