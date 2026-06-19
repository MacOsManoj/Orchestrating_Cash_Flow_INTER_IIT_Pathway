"""
Advanced Schemas for Bond Agent V2
Includes RAG, Tools, Planner, and all new components
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class ToolType(str, Enum):
    NEWS_SCRAPER = "news_scraper"
    WEB_SEARCH = "web_search"
    CRISIL_SCRAPER = "crisil_scraper"
    PORTFOLIO_MANAGER = "portfolio_manager"
    BOND_PRICER = "bond_pricer"
    YIELD_FORECASTER = "yield_forecaster"
    RAG_RETRIEVER = "rag_retriever"
    # MCP Tools
    FETCH_BOND_UNIVERSE = "fetch_bond_universe"
    GET_LATEST_YIELDS = "get_latest_yields"
    GET_ALL_YIELD_FORECASTS = "get_all_yield_forecasts"
    FILTER_BONDS = "filter_bonds"
    LIST_BONDS = "list_bonds"
    SEARCH_BONDS = "search_bonds"
    COMPARE_BONDS = "compare_bonds"
    GET_BOND_INFO = "get_bond_info"
    GET_BOND_DETAILS = "get_bond_details"
    GET_BOND_PRICE = "get_bond_price"
    RECOMMEND_BONDS = "recommend_bonds"


class AgentType(str, Enum):
    QUERY_CLASSIFIER = "query_classifier"
    ML_MODEL = "ml_model"
    ANALYST = "analyst"
    SCORING = "scoring"
    ADVISORY = "advisory"
    EXPLAINABILITY = "explainability"


class DataSource(str, Enum):
    NSE = "nse"
    RBI = "rbi"
    CRISIL = "crisil"
    NEWS = "news"
    USER_PORTFOLIO = "user_portfolio"
    RAG_STORE = "rag_store"


class Rating(str, Enum):
    """Credit rating enum"""
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB_PLUS = "BB+"
    BB = "BB"
    UNRATED = "Unrated"


class Sector(str, Enum):
    """Bond sector enum"""
    SOVEREIGN = "Sovereign"
    PSU_ENERGY = "PSU_Energy"
    PSU_INFRASTRUCTURE = "PSU_Infrastructure"
    PSU_FINANCIAL = "PSU_Financial"
    PRIVATE_FINANCIAL = "Private_Financial"
    PRIVATE_CORPORATE = "Private_Corporate"
    NBFC = "NBFC"
    INFRASTRUCTURE = "Infrastructure"
    REAL_ESTATE = "Real_Estate"
    OTHER = "Other"


class BondType(str, Enum):
    """Bond type enum"""
    GSEC = "G-Sec"
    SDL = "SDL"
    TBILL = "T-Bill"
    CORPORATE = "Corporate"
    PSU = "PSU"
    FLOATING_RATE = "Floating_Rate"


class Signal(str, Enum):
    """Trading signal enum"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class QueryType(str, Enum):
    """Query type enum"""
    ADVISORY = "advisory"
    ANALYTICS = "analytics"
    PORTFOLIO = "portfolio"
    GENERAL = "general"
    UNKNOWN = "unknown"


class Intent(str, Enum):
    """Query intent enum"""
    INCREASE_YIELD = "increase_yield"
    REDUCE_DURATION = "reduce_duration"
    IMPROVE_QUALITY = "improve_quality"
    CUSTOM = "custom"


class NonBondRouting(str, Enum):
    """Routing for non-bond queries"""
    GENERAL_LLM = "general_llm"  # For conversational/general questions
    WEB_SEARCH = "web_search"  # For factual/current information


class ConstraintType(str, Enum):
    """Constraint type enum"""
    RATING = "rating"
    SECTOR = "sector"
    DURATION = "duration"
    YIELD = "yield"


# ==================== BOND DATA SCHEMAS ====================


class BondData(BaseModel):
    """Core bond data"""

    isin: str
    name: str
    issuer: str
    coupon_rate: float
    maturity_date: datetime
    face_value: float = 100.0
    # Optional market data
    last_traded_price: Optional[float] = None
    ytm: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    volume: Optional[float] = None
    # Classification
    bond_type: BondType = BondType.CORPORATE
    sector: Sector = Sector.OTHER
    rating: Optional[Rating] = None
    # Calculated fields
    duration: Optional[float] = None
    modified_duration: Optional[float] = None
    convexity: Optional[float] = None


class Constraint(BaseModel):
    """A single constraint for a query"""
    constraint_type: ConstraintType
    value: Any


class MLPrediction(BaseModel):
    """ML model prediction for a bond"""
    isin: str
    expected_return: float
    predicted_price: Optional[float] = None
    confidence: float = 0.5
    prediction_date: datetime = Field(default_factory=datetime.now)
    model_type: str = "ensemble"
    features_used: List[str] = []


class CreditRiskData(BaseModel):
    """Credit risk data for a bond"""

    isin: str
    probability_default: float = 0.0
    credit_spread: float = 0.0  # basis points
    rating: Optional[Rating] = None
    rating_outlook: str = "Stable"
    recovery_rate: float = 0.4


class YieldCurve(BaseModel):
    """Yield curve data"""
    date: datetime = Field(default_factory=datetime.now)
    rates: Dict[float, float] = {}  # {tenor: yield}
    source: str = "RBI"


class BondAnalytics(BaseModel):
    """Comprehensive bond analytics"""
    isin: str
    name: str
    current_price: float
    fair_value: float
    valuation_gap: float  # percentage
    # Duration metrics
    duration: float
    modified_duration: float
    convexity: float
    rate_sensitivity: float

    # Risk metrics
    credit_risk_score: float

    # Yield metrics
    current_yield: float
    ytm: float
    expected_return: float

    # Liquidity
    liquidity_score: float

    # Classification
    credit_rating: Rating
    sector: Sector

    # Signals
    ml_signal: Signal
    ml_confidence: float

    # Flags
    is_rate_sensitive: bool = False
    is_liquid: bool = True
    is_defensive: bool = False


class BondScore(BaseModel):
    """Scoring result for a bond"""

    isin: str
    name: str

    # Component scores
    valuation_score: float
    return_score: float
    quality_score: float
    liquidity_score: float

    # Total score
    total_score: float

    # Rank
    rank: int = 0

    # Weights used
    weights: Dict[str, float] = {}


class Position(BaseModel):
    """Portfolio position"""
    isin: str
    name: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    weight: float
    unrealized_pnl: float = 0.0


class Portfolio(BaseModel):
    """User portfolio"""
    portfolio_id: str
    name: str
    positions: List[Position]
    total_value: float
    cash: float = 0.0
    # Aggregates
    duration: float = 0.0
    ytm: float = 0.0
    sector_exposures: Dict[str, float] = {}
    rating_exposures: Dict[str, float] = {}


class TradeRecommendation(BaseModel):
    """Single trade recommendation"""
    action: Literal["BUY", "SELL", "HOLD", "SWITCH"]
    isin: str
    name: str
    quantity: float = 0.0
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

    # For SWITCH
    switch_to_isin: Optional[str] = None
    switch_to_name: Optional[str] = None

    # Analysis
    rationale: str
    expected_return: float = 0.0
    risk_score: float = 0.0
    confidence: float = 0.5


class AdvisoryOutput(BaseModel):
    """Output from advisory agent"""
    query: str
    recommendations: List[TradeRecommendation]
    summary: str
    portfolio_changes: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)


class ClassifiedQuery(BaseModel):
    """Classified user query"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    query_type: QueryType
    intent: Intent
    constraints: List[Constraint] = []
    reasoning: str = ""
    confidence: float = 0.8

    # Non-bond query routing
    is_bond_related: bool = True
    non_bond_routing: Optional[NonBondRouting] = (
        None  # Only set if is_bond_related=False
    )


# ==================== TOOL SCHEMAS ====================


class ToolCall(BaseModel):
    """A single tool invocation"""

    tool_type: ToolType
    parameters: Dict[str, Any]
    priority: int = 1
    cache_duration_hours: int = 24
    required: bool = True


class ToolResult(BaseModel):
    """Result from tool execution"""
    tool_type: ToolType
    success: bool
    data: Any
    error: Optional[str] = None
    cached: bool = False
    execution_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== NEWS SCHEMAS ====================


class NewsArticle(BaseModel):
    """Individual news article"""

    title: str
    url: str
    source: str
    content: Optional[str] = None
    summary: Optional[str] = None
    sentiment_score: float = 0.0  # -1 to 1
    relevance_score: float = 0.0  # 0 to 1
    entities: List[str] = []
    published_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.now)
    # For RAG
    embedding: Optional[List[float]] = None
    doc_id: Optional[str] = None


# ==================== CRISIL SCHEMAS ====================


class CreditRating(BaseModel):
    """CRISIL credit rating"""

    issuer: str
    isin: Optional[str] = None
    rating: str  # e.g., "AAA", "AA+"
    outlook: str  # "Stable", "Positive", "Negative"
    rating_date: datetime
    previous_rating: Optional[str] = None
    rating_rationale: Optional[str] = None

    # Financial metrics
    probability_default: float = 0.0
    credit_spread: float = 0.0  # basis points

    # Source document
    source_url: str
    doc_id: Optional[str] = None

    # RAG
    embedding: Optional[List[float]] = None


# ==================== PORTFOLIO SCHEMAS ====================


class PortfolioTransaction(BaseModel):
    """Portfolio transaction record"""

    transaction_id: str
    isin: str
    action: Literal["BUY", "SELL"]
    quantity: float
    price: float
    transaction_date: datetime
    settlement_date: datetime
    fees: float = 0.0


class PortfolioHolding(BaseModel):
    """Current portfolio holding"""
    isin: str
    bond_name: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    weight: float
    # Analytics
    duration: Optional[float] = None
    ytm: Optional[float] = None
    sector: Optional[str] = None
    rating: Optional[str] = None


class UserPortfolio(BaseModel):
    """Complete user portfolio"""
    user_id: str
    portfolio_id: str
    holdings: List[PortfolioHolding]
    total_value: float
    cash: float
    # Aggregates
    portfolio_duration: float = 0.0
    portfolio_ytm: float = 0.0
    sector_exposures: Dict[str, float] = {}
    rating_exposures: Dict[str, float] = {}
    last_updated: datetime = Field(default_factory=datetime.now)


# ==================== YIELD FORECASTING SCHEMAS ====================


class YieldForecast(BaseModel):
    """Yield forecast from Pathway model"""

    maturity_years: float
    forecast_date: datetime
    predicted_yield: float
    predicted_return: float
    confidence: float = 0.0
    model_type: str = "ElasticNet"


class YieldCurveForecast(BaseModel):
    """Complete yield curve forecast"""
    forecast_date: datetime
    forecasts: List[YieldForecast]
    regime: Optional[str] = None  # "steepening", "flattening", etc.


# ==================== BOND PRICING SCHEMAS ====================


class BondPriceForecast(BaseModel):
    """Bond price forecast"""

    isin: str
    bond_name: str
    forecast_date: datetime
    predicted_price: float
    current_price: Optional[float] = None
    expected_return: float = 0.0
    # Components
    yield_component: float = 0.0
    carry_component: float = 0.0
    spread_component: float = 0.0


# ==================== RAG SCHEMAS ====================


class DocumentChunk(BaseModel):
    """Chunk of document for RAG"""

    doc_id: str
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    source: DataSource
    created_at: datetime = Field(default_factory=datetime.now)


class RAGQuery(BaseModel):
    """Query to RAG system"""
    query_text: str
    filters: Dict[str, Any] = {}
    top_k: int = 5
    min_relevance: float = 0.7


class RAGResult(BaseModel):
    """Result from RAG retrieval"""
    query: str
    chunks: List[DocumentChunk]
    relevance_scores: List[float]
    sources: List[str]


# ==================== PLANNER SCHEMAS ====================


class ExecutionPlan(BaseModel):
    """Execution plan from planner"""

    plan_id: str
    query: str
    intent: str

    # Tools to call
    tools_needed: List[ToolCall]

    # Agents to invoke
    agents_needed: List[AgentType]

    # Data sources
    data_sources: List[DataSource]

    # Execution strategy
    parallel_tasks: List[List[str]] = []  # Tasks that can run in parallel
    sequential_tasks: List[str] = []  # Tasks that must run sequentially

    # Flags
    needs_explainability: bool = False
    needs_rag: bool = False
    needs_portfolio_access: bool = False

    # Estimates
    estimated_time_seconds: float = 0.0
    estimated_cost: float = 0.0  # API costs

    # Reasoning
    reasoning: str = ""

    created_at: datetime = Field(default_factory=datetime.now)


# ==================== ENHANCED AGENT STATE ====================


class EnhancedAgentState(BaseModel):
    """Enhanced state with all new components"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Original
    user_query: str
    user_id: str

    # Planning
    execution_plan: Optional[ExecutionPlan] = None

    # Tool results
    tool_results: Dict[ToolType, ToolResult] = {}

    # News data
    news_articles: List[NewsArticle] = []

    # Credit ratings
    credit_ratings: Dict[str, CreditRating] = {}  # isin -> rating

    # Portfolio
    portfolio: Optional[UserPortfolio] = None

    # Forecasts
    yield_forecasts: Optional[YieldCurveForecast] = None
    bond_price_forecasts: Dict[str, BondPriceForecast] = {}

    # RAG
    rag_results: Optional[RAGResult] = None

    # Agent outputs (original)
    classified_query: Optional[ClassifiedQuery] = None
    ml_predictions: Dict[str, MLPrediction] = {}
    bond_analytics: Dict[str, BondAnalytics] = {}
    bond_scores: Dict[str, BondScore] = {}
    advisory: Optional[AdvisoryOutput] = None
    explanations: List[Any] = []
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time: float = 0.0
    cache_hits: int = 0
    total_tool_calls: int = 0


# ==================== CONFIGURATION ====================


class SystemConfigV2(BaseModel):
    """Enhanced system configuration"""

    # API Keys
    openai_api_key: str
    serpapi_key: Optional[str] = None

    # Models
    llm_model: str = "gpt-4-turbo-preview"
    llm_temperature: float = 0.0
    embedding_model: str = "text-embedding-3-small"
    # RAG settings
    rag_enabled: bool = True
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    vector_db_path: str = "data/vectordb"
    # Cache settings
    cache_enabled: bool = True
    cache_dir: str = "data/cache"
    default_cache_ttl_hours: int = 24
    # Tool settings
    enable_web_scraping: bool = True
    enable_crisil_scraper: bool = True
    max_concurrent_tools: int = 5
    tool_timeout_seconds: int = 30

    # Portfolio settings
    portfolio_db_path: str = "data/portfolios"

    # Forecast settings
    yield_forecast_days: int = 14
    enable_pathway_forecasts: bool = True
    forecast_cache_hours: int = 6
    # Scoring weights
    valuation_weight: float = 0.25
    return_weight: float = 0.30
    quality_weight: float = 0.25
    liquidity_weight: float = 0.20

    # Feature flags
    enable_pathway_forecasts: bool = False
    enable_guardrails: bool = False  # Enable/disable guardrails for safety checks
    enable_dynamic_model_selection: bool = (
        False  # Enable/disable dynamic model selection (use fixed model if False)
    )

    # Guardrails settings
    groq_api_key: Optional[str] = None  # Groq API key for Llama Guard
    guardrails_check_input: bool = False  # Check user inputs
    guardrails_check_output: bool = False  # Check AI outputs

    # Limits
    max_news_articles: int = 10
    max_crisil_docs: int = 3
    max_portfolio_positions: int = 50

    # Paths - using .cache for real data (not files-mock since we use real MCP data)
    portfolio_db_path: str = (
        ".cache/portfolios/"  # MongoDB is primary, this is fallback
    )
    cache_dir: str = ".cache/"  # Cache directory for real data
    vector_db_path: str = "vector_store/"
