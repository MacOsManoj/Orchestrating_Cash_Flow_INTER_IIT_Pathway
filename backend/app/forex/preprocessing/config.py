from dataclasses import dataclass
from typing import List


@dataclass
class PathwayFeatureConfig:
    """Configuration for Pathway-based feature engineering"""

    # EMA/EWMA settings
    ewma_alpha: float = 0.25

    # Moving average windows (in days for daily data)
    sma_fast: int = 10
    sma_slow: int = 50

    # MACD settings
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # RSI period
    rsi_period: int = 14

    # ATR period
    atr_period: int = 14

    # Number of lagged returns
    lag_returns: int = 10

    # Volatility windows
    vol_windows: List[int] = None

    # Rolling statistics windows
    rolling_skew_window: int = 20
    rolling_kurt_window: int = 20

    # Fractional differencing
    frac_diff_d: float = 0.4
    frac_diff_thresh: float = 1e-5

    # Target settings (FORWARD LOOKING - clearly marked)
    # WARNING: These use FUTURE data and should NEVER be used as features
    horizon: int = 3  # Days ahead for target
    target_scaling: float = 100.0

    # Minimum history required before valid features
    min_history: int = 60

    # Time unit for windows (in milliseconds for daily data)
    # 1 day = 86400000 ms
    time_unit_ms: int = 86400000  # Daily bars

    def __post_init__(self):
        if self.vol_windows is None:
            self.vol_windows = [10, 20, 60]

    def days_to_ms(self, days: int) -> int:
        """Convert days to milliseconds for window bounds"""
        return days * self.time_unit_ms
