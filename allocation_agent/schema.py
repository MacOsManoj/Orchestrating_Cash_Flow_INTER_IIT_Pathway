from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional

# --- Enums for Standardized Signals ---

class UserIntent(str, Enum):
    CONSERVATIVE = "Conservative"
    BALANCED = "Balanced"
    AGGRESSIVE = "Aggressive"

class LiquidityRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class MarketSentiment(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class Volatility(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"

class YieldTrend(str, Enum):
    RISING = "RISING"
    FALLING = "FALLING"
    FLAT = "FLAT"

class CurrencyStrength(str, Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"

# --- Data Models ---

class MarketSignals(BaseModel):
    """
    Aggregated signals from all pipelines.
    """
    intent: UserIntent
    liquidity_risk: LiquidityRisk
    sentiment: MarketSentiment
    volatility: Volatility
    yield_trend: YieldTrend
    # dom_currency: CurrencyStrength
    forex_opportunity_index: float = Field(..., ge=0.0, le=1.0, description="Aggregated Forex Conviction Score (0.0-1.0)")

class PortfolioAllocation(BaseModel):
    """
    The target allocation split (must sum to 100%).
    """
    stocks: float = Field(..., ge=0.0, le=1.0, description="Percentage allocation to Stocks (0.0-1.0)")
    bonds: float = Field(..., ge=0.0, le=1.0, description="Percentage allocation to Bonds (0.0-1.0)")
    forex: float = Field(..., ge=0.0, le=1.0, description="Percentage allocation to Forex (0.0-1.0)")
    cash: float = Field(..., ge=0.0, le=1.0, description="Percentage allocation to Cash (0.0-1.0)")

    @field_validator('cash')
    @classmethod
    def check_sum(cls, v, values):
        # We can't easily check sum here because validation happens field by field.
        # But we can add a method to validate or use a root validator if needed.
        # For now, we trust the Rule Engine to produce valid sums, 
        # but we can add a helper property.
        return v

    def validate_total(self):
        total = self.stocks + self.bonds + self.forex + self.cash
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Allocation must sum to 1.0, got {total}")

class Constraints(BaseModel):
    """
    User-defined constraints extracted from the query.
    """
    max_stocks: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum allocation for Stocks")
    min_stocks: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum allocation for Stocks")
    max_bonds: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum allocation for Bonds")
    min_bonds: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum allocation for Bonds")
    # Add others as needed

class ConflictWarning(BaseModel):
    """
    Warning raised when User Intent conflicts with Market Signals.
    """
    detected: bool
    message: str

class PortfolioRecommendation(BaseModel):
    """
    Final output to the user.
    """
    allocation: PortfolioAllocation
    reasoning: str
    conflict_warning: Optional[ConflictWarning] = None
    # In Phase 2, we will add lists of specific assets here
    # stocks_to_buy: List[str]
    # bonds_to_buy: List[str]
