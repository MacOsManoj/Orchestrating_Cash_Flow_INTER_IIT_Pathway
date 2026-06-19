from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

# --- Main Page Models ---


class ForexPairSummary(BaseModel):
    """Summary data for a single forex pair"""

    pair: str
    current_price: float
    previous_close: float
    price_change_1d: float
    price_change_pct_1d: float
    high_1d: Optional[float] = None
    low_1d: Optional[float] = None


class ForexPairsResponse(BaseModel):
    """Response for all forex pairs overview"""

    pairs: List[ForexPairSummary]
    timestamp: str


class RecommendedTrade(BaseModel):
    """Recommended trade for a currency pair"""

    pair: str
    current_price: float
    price_change_pct: float
    action: str  # "buy", "sell", "hold"
    signal_strength: str  # "weak", "moderate", "strong"
    model_confidence: float
    predicted_return: float
    stop_loss_pct: float  # Stop loss percentage from config (e.g., 0.01 = 1%)


class RecommendedTradesResponse(BaseModel):
    """Response for recommended trades"""

    trades: List[RecommendedTrade]
    timestamp: str


class PositionUpdateRequest(BaseModel):
    """Request to update a position"""

    pair: str
    action: str = Field(
        ..., description="Action: 'open_long', 'open_short', 'close', 'update_size'"
    )
    size: Optional[float] = Field(default=None, description="Position size (optional)")
    price: Optional[float] = Field(
        default=None,
        description="Entry/exit price (optional, uses current if not provided)",
    )


class TradeActionRequest(BaseModel):
    """Request for buy/sell/hold button action"""

    pair: str = Field(..., description="Currency pair (e.g., 'EURUSD')")
    action: str = Field(..., description="Action: 'buy', 'sell', or 'hold'")
    amount: Optional[float] = Field(
        default=10000, description="Trade amount in base currency"
    )
    price: Optional[float] = Field(
        default=None,
        description="Execution price (optional, uses current market price if not provided)",
    )


class TradeActionResponse(BaseModel):
    """Response after executing a trade action"""

    success: bool
    pair: str
    action: str
    executed_price: float
    amount: float
    position_after: str  # "long", "short", "flat"
    message: str
    trade_id: Optional[str] = None
    portfolio_summary: Optional[Dict[str, Any]] = None
    timestamp: str


class PortfolioSummaryResponse(BaseModel):
    """Full portfolio summary response"""

    total_open_positions: int
    total_exposure_long: float
    total_exposure_short: float
    net_exposure: float
    total_unrealized_pnl_pct: float
    portfolio_heat: float
    long_exposure_pct: float
    short_exposure_pct: float
    positions: Dict[str, Any]
    timestamp: str


class CumulativeProfitResponse(BaseModel):
    """Cumulative profit response for a currency pair"""

    pair: str
    total_profit_pct: float
    total_profit_amount: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit_per_trade: float
    largest_win_pct: float
    largest_loss_pct: float
    current_streak: int  # Positive for wins, negative for losses
    profit_history: List[Dict[str, Any]]  # List of trades with cumulative profit
    timestamp: str


class AllPairsProfitResponse(BaseModel):
    """Cumulative profit response for all pairs"""

    pairs: Dict[str, Dict[str, Any]]
    total_portfolio_profit_pct: float
    total_portfolio_profit_amount: float
    best_performing_pair: str
    worst_performing_pair: str
    timestamp: str


class PositionUpdateResponse(BaseModel):
    """Response after position update"""

    success: bool
    pair: str
    action: str
    message: str
    updated_position: Optional[Dict[str, Any]] = None
    timestamp: str


# --- Currency Page Models ---


class PriceDataPoint(BaseModel):
    """Single price data point for chart"""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class CurrencyPriceData(BaseModel):
    """Price data response for charting"""

    pair: str
    data: List[PriceDataPoint]
    spot_rate: float
    realized_volatility_10d: float
    realized_volatility_20d: float
    atr_14d: float
    timestamp: str


class RiskMetrics(BaseModel):
    """Risk tracking metrics for a currency pair"""

    pair: str
    volatility_10d: float
    volatility_20d: float
    volatility_60d: float
    value_at_risk_95: float  # 95% VaR
    value_at_risk_99: float  # 99% VaR
    position_size: float
    strategy_sharpe: float
    max_drawdown_pct: float
    beta_to_usd: Optional[float] = None
    timestamp: str


class PortfolioExposure(BaseModel):
    """Portfolio exposure and PnL metrics"""

    pair: str
    avg_buy_price: Optional[float] = None
    avg_sell_price: Optional[float] = None
    current_position: str  # "long", "short", "flat"
    position_size: float
    realized_pnl: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    portfolio_exposure_pct: float
    entry_date: Optional[str] = None
    days_held: int
    timestamp: str


# --- Miscellaneous Models ---


class CorrelationMatrixResponse(BaseModel):
    """Correlation matrix response"""

    pairs: List[str]
    matrix: List[List[float]]  # 2D correlation matrix
    period_days: int
    timestamp: str


class TradeRecord(BaseModel):
    """Single trade record"""

    pair: str
    action: str  # "long", "short"
    entry_price: float
    exit_price: Optional[float] = None
    entry_datetime: str
    exit_datetime: Optional[str] = None
    pnl_pct: Optional[float] = None
    status: str  # "open", "closed"


class TradeRecordsResponse(BaseModel):
    """Trade records response"""

    records: List[TradeRecord]
    total_count: int
    timestamp: str


class QueryRequest(BaseModel):
    """Request model for agent queries"""

    query: str = Field(..., description="User query for the forex agent")


class QueryResponse(BaseModel):
    """Response model for agent queries"""

    response: str
    tools_called: List[Any]  # List of tool call details: [{name, arguments, output}]
    processing_time_ms: float
    timestamp: str


class PipelineMode(str, Enum):
    NORMAL = "normal"
    TRAIN = "train"
    UPDATE_DATA = "update_data"


class PipelineRunRequest(BaseModel):
    """Request model for running the pipeline"""

    mode: Optional[PipelineMode] = Field(
        default=PipelineMode.NORMAL,
        description="Run mode: 'normal', 'train', 'update_data'",
    )


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline status"""

    status: str
    last_run: Optional[str]
    models_trained: List[str]
    current_signals: Dict[str, Any]
    positions: Dict[str, Any]


class PositionResponse(BaseModel):
    """Response model for position data"""

    pair: str
    position: Dict[str, Any]


class TradesResponse(BaseModel):
    """Response model for trades data"""

    pair: str
    trades: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: str
    version: str


# --- News Sentiment Models ---


class HeadlineNews(BaseModel):
    """Single news headline with sentiment"""

    title: str
    source: str
    sentiment: str  # "positive", "negative", "neutral"
    sentiment_score: float  # -1 to 1
    url: Optional[str] = None
    published_date: Optional[str] = None


class PairHeadlineSentiment(BaseModel):
    """Headline sentiment for a single currency pair"""

    pair: str
    overall_sentiment: str  # "BULLISH", "BEARISH", "NEUTRAL"
    sentiment_score: float  # -1 to 1
    confidence: str  # "high", "medium", "low"
    headline_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    headlines: List[HeadlineNews]


class HeadlineSentimentResponse(BaseModel):
    """Response for headline sentiment endpoint"""

    pairs: List[PairHeadlineSentiment]
    market_sentiment: str  # Overall market sentiment: "BULLISH", "BEARISH", "NEUTRAL"
    market_sentiment_score: float
    timestamp: str
