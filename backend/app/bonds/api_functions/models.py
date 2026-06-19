"""
API Response and Request Models
Pydantic models for FastAPI endpoints
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Bond Models
class BondDetails(BaseModel):
    """Bond details response model"""

    isin: str
    bond_name: str
    symbol: Optional[str] = None
    coupon_rate: Optional[float] = None
    maturity_date: str
    next_coupon_date: Optional[str] = None
    minimum_increment: float
    last_price: float
    clean_price: float
    accrued_interest: float
    duration: float
    convexity: float
    dv01: float
    z_spread: int
    var: float
    ytm: Optional[float] = None  # Yield to Maturity
    interest_rate_volatility: Optional[float] = None  # Annualized volatility (%)
    credit_spread_volatility: Optional[float] = None  # Annualized volatility (%)
    credit_rating: Optional[str] = None


class BondSummary(BaseModel):
    """Bond summary for universe endpoint"""

    isin: str
    bond_name: str
    coupon_rate: Optional[float] = None
    maturity_date: str
    last_price: float


# Agent Query Models
class QueryRequest(BaseModel):
    """Request model for agent query"""

    user_id: str
    query: str
    isin: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for query submission"""

    query_id: str
    status: str
    processing_time: float
    timestamp: str


class OutputResponse(BaseModel):
    """Response model for agent output"""

    query_id: str
    user_query: str
    output: str  # Text output from Response agent
    timestamp: str


# Yield History Models
class YieldDataPoint(BaseModel):
    """Single yield data point"""

    date: str
    yield_value: float = Field(..., serialization_alias="yield")
    time: str

    class Config:
        populate_by_name = True


class YieldMetrics(BaseModel):
    """Yield metrics"""

    current_yielding: float
    current_yielding_percent: float
    one_month_change: float
    one_month_change_unit: str
    volatility_20d: float
    volatility_20d_percent: float
    max_drawdown_1y: float
    max_drawdown_1y_percent: float


class YieldHistoryResponse(BaseModel):
    """Response model for yield history endpoint"""

    isin: str
    period: str
    yield_data: List[YieldDataPoint]
    metrics: YieldMetrics
    last_updated: str


# Rate vs Yield Overlay Models
class RateYieldDataPoint(BaseModel):
    """Single rate vs yield data point"""

    date: str
    policy_rate: float
    yield_10y: float


class SeriesDefinition(BaseModel):
    """Series definition for chart"""

    name: str
    data_key: str
    color: str
    y_axis: str


class YAxisConfig(BaseModel):
    """Y-axis configuration"""

    label: str
    min: float
    max: float


class RateYieldOverlayResponse(BaseModel):
    """Response model for rate vs yield overlay endpoint"""

    isin: str
    period: str
    data: List[RateYieldDataPoint]
    series: List[SeriesDefinition]
    y_axes: Dict[str, YAxisConfig]
    last_updated: str


# Price Statistics Models
class PriceStatisticsDataPoint(BaseModel):
    """Single price data point with percentile bands"""

    date: str
    price: float
    price_5th_percentile: float
    price_95th_percentile: float


class PriceStatisticsMetrics(BaseModel):
    """Price statistics metrics"""

    median_price: float
    price_5th_percentile: float
    price_95th_percentile: float
    implied_volatility: float


class PriceStatisticsResponse(BaseModel):
    """Response model for price statistics endpoint"""

    isin: str
    period: str
    price_data: List[PriceStatisticsDataPoint]
    metrics: PriceStatisticsMetrics
    last_updated: str


# Comparison Models
class BondSearchResult(BaseModel):
    """Single bond search result"""

    isin: str
    name: str
    issuer: str
    coupon_rate: float
    maturity_date: str
    current_yield: float
    current_yield_percent: float
    yield_change: float
    yield_change_direction: str


class SearchResponse(BaseModel):
    """Search results response"""

    results: List[BondSearchResult]
    total_results: int


class ComparisonInstrument(BaseModel):
    """Instrument in comparison list"""

    isin: str
    name: str
    current_yield: float
    current_yield_percent: float
    yield_change: float
    yield_change_direction: str
    yield_change_symbol: str


class ComparisonListResponse(BaseModel):
    """Comparison list response"""

    comparison_id: str
    instruments: List[ComparisonInstrument]
    created_at: str
    last_updated: str


class ComparisonDetailsResponse(BaseModel):
    """Detailed comparison response"""

    comparison_id: str
    instruments: List[ComparisonInstrument]
    created_at: str
    last_updated: str


class AddToComparisonRequest(BaseModel):
    """Request to add bond to comparison"""

    isin: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


# Chat Models
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    prompt: str = Field(..., description="User prompt/query")
    user_id: str = Field(default="api_user", description="User identifier")
    thread_id: Optional[str] = Field(
        default=None, description="Thread ID for conversation history"
    )
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Previous conversation messages"
    )


class RecommendationResponse(BaseModel):
    """Single recommendation in chat response"""
    action: str
    name: str
    isin: str
    rationale: str
    expected_return: float
    confidence: float
    risk_score: float
    quantity: Optional[float] = None
    target_price: Optional[float] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    success: bool
    response: str = Field(..., description="AI generated response text")
    recommendations: Optional[List[RecommendationResponse]] = Field(
        default=None, description="Trade recommendations if any"
    )
    processing_time: float = Field(..., description="Processing time in seconds")
    has_analytics: bool = Field(
        default=False, description="Whether bond analytics are available"
    )
    has_scores: bool = Field(
        default=False, description="Whether bond scores are available"
    )
    has_portfolio: bool = Field(
        default=False, description="Whether portfolio data is available"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")
