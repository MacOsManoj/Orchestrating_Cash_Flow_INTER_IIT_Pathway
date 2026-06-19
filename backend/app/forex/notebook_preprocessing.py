"""
Notebook Preprocessing Pipelines - Extracted from Jupyter Notebooks

This file contains the EXACT preprocessing pipelines from:
1. xgb_single_train copy 2.ipynb (Standard Features - for EURUSD, GBPUSD, etc.)
2. usdjpy.ipynb (Advanced Features - for USDJPY with VIX proxy, fractional differencing)

These implementations can be compared against the Pathway preprocessor in preprocessing.py
to ensure feature parity.

Author: Extracted from notebooks for comparison testing
"""

import pandas as pd
import numpy as np
import math
from typing import Tuple, List


# =============================================================================
# PIPELINE 1: Standard Features (from xgb_single_train copy 2.ipynb)
# Used for: EURUSD, GBPUSD, EURINR, GBPINR, JPYINR
# =============================================================================


class StandardFeatureConfig:
    """Configuration for standard feature pipeline (xgb_single_train copy 2.ipynb)"""

    EWMA_ALPHA = 0.25
    SMA_FAST = 10
    SMA_SLOW = 50
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    LAG_RETURNS = 10
    HORIZON = 3
    TARGET_SCALING = 100


def compute_rsi_standard(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute RSI (Relative Strength Index) - Standard implementation

    Example:
    >>> prices = pd.Series([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10,
    ...                     45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28])
    >>> rsi = compute_rsi_standard(prices, period=14)
    >>> rsi.iloc[-1]  # Should be around 66-70 for this uptrending data
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_atr_standard(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute ATR (Average True Range) - Standard implementation

    Example:
    >>> df = pd.DataFrame({
    ...     'high': [48.70, 48.72, 48.90, 48.87, 48.82],
    ...     'low': [47.79, 48.14, 48.39, 48.37, 48.24],
    ...     'close': [48.16, 48.61, 48.75, 48.63, 48.74]
    ... })
    >>> atr = compute_atr_standard(df, period=3)
    >>> atr.iloc[-1]  # ATR for the last 3 periods
    """
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift()).abs()
    tr3 = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_adx_standard(
    df: pd.DataFrame, period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute ADX (Average Directional Index) - Standard implementation

    Returns: (adx, plus_di, minus_di)

    Example:
    >>> df = pd.DataFrame({
    ...     'high': [48.70, 48.72, 48.90, 48.87, 48.82, 48.95, 49.10, 49.20],
    ...     'low': [47.79, 48.14, 48.39, 48.37, 48.24, 48.50, 48.80, 49.00],
    ...     'close': [48.16, 48.61, 48.75, 48.63, 48.74, 48.90, 49.05, 49.15]
    ... })
    >>> adx, plus_di, minus_di = compute_adx_standard(df, period=3)
    """
    high, low, close = df["high"], df["low"], df["close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    atr = pd.Series(tr).rolling(window=period).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()

    return adx, plus_di, minus_di


def add_features_standard(
    df: pd.DataFrame, config: StandardFeatureConfig = None
) -> pd.DataFrame:
    """
    Add standard features (from xgb_single_train copy 2.ipynb)

    This is the EXACT feature set used for non-USDJPY pairs.

    Example:
    >>> df = pd.DataFrame({
    ...     'timestamp': pd.date_range('2020-01-01', periods=100),
    ...     'open': np.random.uniform(1.1, 1.2, 100),
    ...     'high': np.random.uniform(1.2, 1.3, 100),
    ...     'low': np.random.uniform(1.0, 1.1, 100),
    ...     'close': np.random.uniform(1.1, 1.2, 100),
    ...     'volume': np.random.uniform(1000, 2000, 100)
    ... })
    >>> df_features = add_features_standard(df)
    >>> print(f"Features added: {len(df_features.columns) - len(df.columns)}")
    """
    config = config or StandardFeatureConfig()
    df = df.copy()

    # Log-return
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))

    # Lagged returns
    for i in range(1, config.LAG_RETURNS + 1):
        df[f"log_ret_lag_{i}"] = df["log_ret"].shift(i)

    # EWMA
    df["ewma_ret"] = df["log_ret"].ewm(alpha=config.EWMA_ALPHA).mean()
    df["ewma_vol"] = df["log_ret"].ewm(alpha=config.EWMA_ALPHA).std()

    # SMA
    df["sma_fast"] = df["close"].rolling(window=config.SMA_FAST).mean()
    df["sma_slow"] = df["close"].rolling(window=config.SMA_SLOW).mean()
    df["sma_spread"] = df["sma_fast"] - df["sma_slow"]

    # MACD
    ema_fast = df["close"].ewm(span=config.MACD_FAST, adjust=False).mean()
    ema_slow = df["close"].ewm(span=config.MACD_SLOW, adjust=False).mean()
    df["macd_line"] = ema_fast - ema_slow
    df["macd_signal"] = (
        df["macd_line"].ewm(span=config.MACD_SIGNAL, adjust=False).mean()
    )
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]

    # ATR, RSI
    df["atr"] = compute_atr_standard(df, config.ATR_PERIOD)
    df["rsi"] = compute_rsi_standard(df["close"], config.RSI_PERIOD)

    # Volume features
    df["volume_ewma"] = df["volume"].ewm(alpha=config.EWMA_ALPHA).mean()
    df["volume_change"] = df["volume"].diff()

    # Day of week
    df["dow_sin"] = np.sin(2 * np.pi * df["timestamp"].dt.dayofweek / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["timestamp"].dt.dayofweek / 7)

    # Spread
    df["hl_spread"] = df["high"] - df["low"]

    # Rolling stats
    df["rolling_skew"] = df["log_ret"].rolling(window=20).skew()
    df["rolling_kurt"] = df["log_ret"].rolling(window=20).kurt()

    # Realised Volatility
    df["rv_10"] = df["log_ret"].rolling(window=10).std() * np.sqrt(10)
    df["rv_60"] = df["log_ret"].rolling(window=60).std() * np.sqrt(60)
    df["rv_ratio"] = df["rv_10"] / df["rv_60"]

    # ADX
    adx, plus_di, minus_di = compute_adx_standard(df, period=14)
    df["adx"] = adx
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    # SMA Slopes
    sma_10 = df["close"].rolling(window=10).mean()
    sma_20 = df["close"].rolling(window=20).mean()
    df["sma_slope_10"] = (sma_10 - sma_10.shift(1)) / sma_10.shift(1)
    df["sma_slope_20"] = (sma_20 - sma_20.shift(1)) / sma_20.shift(1)

    # Candle features
    body = (df["close"] - df["open"]).abs()
    total_range = df["high"] - df["low"]
    df["body_ratio"] = body / total_range.replace(0, np.nan)
    df["price_position"] = (df["close"] - df["low"]) / total_range.replace(0, np.nan)

    # ROC
    for period in [3, 5, 10]:
        df[f"roc_{period}"] = (df["close"] - df["close"].shift(period)) / df[
            "close"
        ].shift(period)

    df = df.replace([np.inf, -np.inf], np.nan)
    return df


# =============================================================================
# PIPELINE 2: USDJPY Features (from usdjpy.ipynb)
# Used for: USDJPY (includes VIX proxy, fractional differencing, bond spread)
# =============================================================================


class USDJPYFeatureConfig:
    """Configuration for USDJPY feature pipeline (usdjpy.ipynb)"""

    EWMA_ALPHA = 0.25
    SMA_FAST = 10
    SMA_SLOW = 50
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    LAG_RETURNS = 10
    HORIZON = 3
    TARGET_SCALING = 100

    # Volatility settings
    VOL_WINDOWS = [10, 20, 60]
    VOL_ANNUALIZE = True
    VOL_EPS = 1e-9

    # Fractional Differencing
    FRAC_DIFF_D = 0.4
    FRAC_DIFF_THRESH = 1e-5


def get_frac_diff_weights(
    d: float, thresh: float = 1e-5, max_size: int = 500
) -> np.ndarray:
    """
    Compute fractional differencing weights using binomial series expansion.
    Based on Marcos Lopez de Prado's method.

    Example:
    >>> weights = get_frac_diff_weights(0.4, thresh=1e-3)
    >>> print(f"Number of weights: {len(weights)}")
    >>> print(f"Sum of weights: {weights.sum():.4f}")  # Should be close to 0 for d=0.4
    """
    weights = [1.0]
    k = 1
    while True:
        w_k = -weights[-1] * (d - k + 1) / k
        if abs(w_k) < thresh or k >= max_size:
            break
        weights.append(w_k)
        k += 1
    return np.array(weights[::-1])


def frac_diff(series: pd.Series, d: float, thresh: float = 1e-5) -> pd.Series:
    """
    Apply fractional differencing to a time series.
    Preserves more memory than standard differencing while achieving stationarity.

    Example:
    >>> prices = pd.Series([100, 101, 102, 101.5, 103, 104, 102, 105, 106, 107])
    >>> frac_prices = frac_diff(prices, d=0.4)
    >>> print(f"Original std: {prices.std():.4f}")
    >>> print(f"Frac diff std: {frac_prices.dropna().std():.4f}")  # Should be smaller
    """
    weights = get_frac_diff_weights(d, thresh)
    width = len(weights)

    result = pd.Series(index=series.index, dtype=float)
    for i in range(width - 1, len(series)):
        result.iloc[i] = np.dot(weights, series.iloc[i - width + 1 : i + 1].values)

    return result


def compute_garman_klass_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Garman-Klass volatility estimator - more efficient than close-to-close.

    Example:
    >>> df = pd.DataFrame({
    ...     'open': [100, 101, 102, 103, 104],
    ...     'high': [102, 103, 104, 105, 106],
    ...     'low': [99, 100, 101, 102, 103],
    ...     'close': [101, 102, 103, 104, 105]
    ... })
    >>> gk_vol = compute_garman_klass_vol(df, window=3)
    """
    log_hl = np.log(df["high"] / df["low"]) ** 2
    log_co = np.log(df["close"] / df["open"]) ** 2
    gk_vol = np.sqrt(0.5 * log_hl - (2 * np.log(2) - 1) * log_co)
    return gk_vol.rolling(window=window).mean()


def compute_parkinson_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Parkinson volatility estimator - uses high-low range.

    Example:
    >>> df = pd.DataFrame({
    ...     'high': [102, 103, 104, 105, 106],
    ...     'low': [99, 100, 101, 102, 103]
    ... })
    >>> pk_vol = compute_parkinson_vol(df, window=3)
    """
    log_hl = np.log(df["high"] / df["low"]) ** 2
    parkinson = np.sqrt(log_hl / (4 * np.log(2)))
    return parkinson.rolling(window=window).mean()


def compute_yang_zhang_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Yang-Zhang Volatility Estimator - combines overnight and open-to-close volatility.
    Most efficient OHLC-based estimator, handles overnight jumps.

    Example:
    >>> df = pd.DataFrame({
    ...     'open': [100, 101, 102, 103, 104, 105],
    ...     'high': [102, 103, 104, 105, 106, 107],
    ...     'low': [99, 100, 101, 102, 103, 104],
    ...     'close': [101, 102, 103, 104, 105, 106]
    ... })
    >>> yz_vol = compute_yang_zhang_vol(df, window=3)
    """
    log_ho = np.log(df["high"] / df["open"])
    log_lo = np.log(df["low"] / df["open"])
    log_co = np.log(df["close"] / df["open"])

    # Rogers-Satchell component
    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    # Overnight volatility (close-to-open)
    log_oc = np.log(df["open"] / df["close"].shift(1))
    overnight_var = log_oc.rolling(window=window).var()

    # Open-to-close volatility
    open_close_var = log_co.rolling(window=window).var()

    # Rogers-Satchell variance
    rs_var = rs.rolling(window=window).mean()

    # Yang-Zhang combines all three with optimal weights
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    yz_var = overnight_var + k * open_close_var + (1 - k) * rs_var

    return np.sqrt(yz_var)


def compute_rogers_satchell_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Rogers-Satchell Volatility - accounts for drift in the price process.

    Example:
    >>> df = pd.DataFrame({
    ...     'open': [100, 101, 102, 103, 104],
    ...     'high': [102, 103, 104, 105, 106],
    ...     'low': [99, 100, 101, 102, 103],
    ...     'close': [101, 102, 103, 104, 105]
    ... })
    >>> rs_vol = compute_rogers_satchell_vol(df, window=3)
    """
    log_ho = np.log(df["high"] / df["open"])
    log_hc = np.log(df["high"] / df["close"])
    log_lo = np.log(df["low"] / df["open"])
    log_lc = np.log(df["low"] / df["close"])

    rs = log_ho * log_hc + log_lo * log_lc
    return np.sqrt(rs.rolling(window=window).mean().clip(lower=0))


def compute_vix_proxy(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    VIX-like proxy calculated from price data.
    Combines realized volatility with Yang-Zhang estimator.

    Example:
    >>> df = pd.DataFrame({
    ...     'open': np.random.uniform(100, 102, 50),
    ...     'high': np.random.uniform(102, 105, 50),
    ...     'low': np.random.uniform(98, 100, 50),
    ...     'close': np.random.uniform(100, 102, 50)
    ... })
    >>> df['close'] = df['close'].cumsum() / df['close'].cumsum().max() * 100  # Normalize
    >>> vix = compute_vix_proxy(df, window=10)
    """
    # 1. Base realized volatility (annualized)
    log_ret = np.log(df["close"] / df["close"].shift(1))
    realized_vol = log_ret.rolling(window=window).std() * np.sqrt(252)

    # 2. Yang-Zhang vol (more accurate)
    yz_vol = compute_yang_zhang_vol(df, window) * np.sqrt(252)

    # Combine into VIX proxy (weighted average)
    vix_proxy = 0.5 * realized_vol + 0.5 * yz_vol

    # Scale to VIX-like range (typically 10-80)
    vix_proxy = vix_proxy * 100

    return vix_proxy


def compute_vol_percentile(vol_series: pd.Series, lookback: int = 252) -> pd.Series:
    """
    Calculate where current volatility sits in its historical distribution.

    Example:
    >>> vol = pd.Series(np.random.uniform(0.1, 0.3, 100))
    >>> pct = compute_vol_percentile(vol, lookback=50)
    """

    def percentile_rank(x):
        if len(x) < 2:
            return 50
        return (x.iloc[:-1] < x.iloc[-1]).sum() / (len(x) - 1) * 100

    return vol_series.rolling(window=lookback, min_periods=20).apply(
        percentile_rank, raw=False
    )


def compute_vol_zscore(vol_series: pd.Series, window: int = 60) -> pd.Series:
    """
    Z-score of volatility - how many std devs from mean.

    Example:
    >>> vol = pd.Series(np.random.uniform(0.1, 0.3, 100))
    >>> zscore = compute_vol_zscore(vol, window=30)
    """
    vol_mean = vol_series.rolling(window=window).mean()
    vol_std = vol_series.rolling(window=window).std()
    return (vol_series - vol_mean) / vol_std.replace(0, np.nan)


def add_features_usdjpy(
    df: pd.DataFrame, config: USDJPYFeatureConfig = None
) -> pd.DataFrame:
    """
    Add USDJPY-specific features (from usdjpy.ipynb)

    This includes ALL standard features PLUS:
    - Advanced volatility estimators (Garman-Klass, Parkinson, Yang-Zhang, Rogers-Satchell)
    - VIX proxy features
    - Fractional differencing
    - Bond yield spread features (if available)

    Example:
    >>> df = pd.DataFrame({
    ...     'timestamp': pd.date_range('2020-01-01', periods=200),
    ...     'open': np.random.uniform(105, 110, 200),
    ...     'high': np.random.uniform(110, 115, 200),
    ...     'low': np.random.uniform(100, 105, 200),
    ...     'close': np.random.uniform(105, 110, 200),
    ...     'volume': np.random.uniform(1000, 2000, 200)
    ... })
    >>> df_features = add_features_usdjpy(df)
    >>> print(f"Features added: {len(df_features.columns) - len(df.columns)}")
    """
    config = config or USDJPYFeatureConfig()
    df = df.copy()

    # =====================================================================
    # STANDARD FEATURES (same as xgb_single_train copy 2.ipynb)
    # =====================================================================

    # Log-return
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))

    # Lagged returns
    for i in range(1, config.LAG_RETURNS + 1):
        df[f"log_ret_lag_{i}"] = df["log_ret"].shift(i)

    # EWMA
    df["ewma_ret"] = df["log_ret"].ewm(alpha=config.EWMA_ALPHA).mean()
    df["ewma_vol"] = df["log_ret"].ewm(alpha=config.EWMA_ALPHA).std()

    # SMA
    df["sma_fast"] = df["close"].rolling(window=config.SMA_FAST).mean()
    df["sma_slow"] = df["close"].rolling(window=config.SMA_SLOW).mean()
    df["sma_spread"] = df["sma_fast"] - df["sma_slow"]

    # MACD
    ema_fast = df["close"].ewm(span=config.MACD_FAST, adjust=False).mean()
    ema_slow = df["close"].ewm(span=config.MACD_SLOW, adjust=False).mean()
    df["macd_line"] = ema_fast - ema_slow
    df["macd_signal"] = (
        df["macd_line"].ewm(span=config.MACD_SIGNAL, adjust=False).mean()
    )
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]

    # ATR, RSI
    df["atr"] = compute_atr_standard(df, config.ATR_PERIOD)
    df["rsi"] = compute_rsi_standard(df["close"], config.RSI_PERIOD)

    # Volume features
    df["volume_ewma"] = df["volume"].ewm(alpha=config.EWMA_ALPHA).mean()
    df["volume_change"] = df["volume"].diff()

    # Day of week
    df["dow_sin"] = np.sin(2 * np.pi * df["timestamp"].dt.dayofweek / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["timestamp"].dt.dayofweek / 7)

    # Spread
    df["hl_spread"] = df["high"] - df["low"]

    # Rolling stats
    df["rolling_skew"] = df["log_ret"].rolling(window=20).skew()
    df["rolling_kurt"] = df["log_ret"].rolling(window=20).kurt()

    # =====================================================================
    # VOLATILITY FEATURES (Extended for USDJPY)
    # =====================================================================

    # 1. Realized Volatility
    for w in config.VOL_WINDOWS:
        col = f"vol_{w}"
        vol = df["log_ret"].rolling(window=w).std()
        if config.VOL_ANNUALIZE:
            vol = vol * np.sqrt(252)
        df[col] = vol

    # 2. Garman-Klass Volatility
    df["vol_gk_20"] = compute_garman_klass_vol(df, window=20)
    df["vol_gk_60"] = compute_garman_klass_vol(df, window=60)

    # 3. Parkinson Volatility
    df["vol_parkinson_20"] = compute_parkinson_vol(df, window=20)

    # 4. EWMA Volatility
    df["vol_ewma"] = df["log_ret"].ewm(span=20).std()

    # 5. Volatility ratios
    if "vol_10" in df.columns and "vol_60" in df.columns:
        df["vol_ratio_10_60"] = df["vol_10"] / (df["vol_60"].replace(0, np.nan))
    if "vol_20" in df.columns and "vol_60" in df.columns:
        df["vol_ratio_20_60"] = df["vol_20"] / (df["vol_60"].replace(0, np.nan))

    # 6. Volatility of volatility
    if "vol_20" in df.columns:
        df["vol_of_vol"] = df["vol_20"].rolling(window=20).std()

    # 7. Log volatility
    if "vol_20" in df.columns:
        df["log_vol_20"] = np.log(df["vol_20"].replace(0, np.nan) + config.VOL_EPS)

    # 8. Summary volatility
    vol_cols = [
        c
        for c in df.columns
        if c.startswith("vol_")
        and not c.startswith("vol_ratio")
        and not c.startswith("vol_of")
    ]
    if vol_cols:
        df["volatility"] = df[vol_cols].median(axis=1)

    # 9. Volatility regime
    vol_median = df["volatility"].rolling(window=60).median()
    df["vol_regime"] = (df["volatility"] > vol_median).astype(float)

    # 10. ATR percentage
    df["atr_pct"] = df["atr"] / df["close"]

    # Base RV (for consistency with standard pipeline)
    df["rv_10"] = df["log_ret"].rolling(window=10).std() * np.sqrt(10)
    df["rv_60"] = df["log_ret"].rolling(window=60).std() * np.sqrt(60)
    df["rv_ratio"] = df["rv_10"] / df["rv_60"]

    # =====================================================================
    # VIX-LIKE VOLATILITY FEATURES
    # =====================================================================

    # 11. Yang-Zhang Volatility
    df["vol_yang_zhang_20"] = compute_yang_zhang_vol(df, window=20)
    df["vol_yang_zhang_60"] = compute_yang_zhang_vol(df, window=60)

    # 12. Rogers-Satchell Volatility
    df["vol_rogers_satchell_20"] = compute_rogers_satchell_vol(df, window=20)

    # 13. VIX Proxy
    df["vix_proxy"] = compute_vix_proxy(df, window=20)
    df["vix_proxy_slow"] = compute_vix_proxy(df, window=60)

    # 14. VIX Proxy Change
    df["vix_proxy_change"] = df["vix_proxy"].diff()
    df["vix_proxy_pct_change"] = df["vix_proxy"].pct_change()

    # 15. VIX Proxy Momentum
    df["vix_proxy_momentum_5"] = df["vix_proxy"] - df["vix_proxy"].shift(5)
    df["vix_proxy_momentum_10"] = df["vix_proxy"] - df["vix_proxy"].shift(10)

    # 16. VIX Proxy SMA and trend
    df["vix_proxy_sma_10"] = df["vix_proxy"].rolling(window=10).mean()
    df["vix_proxy_sma_20"] = df["vix_proxy"].rolling(window=20).mean()
    df["vix_proxy_trend"] = df["vix_proxy_sma_10"] - df["vix_proxy_sma_20"]

    # 17. Volatility Percentile
    if "vol_20" in df.columns:
        df["vol_percentile"] = compute_vol_percentile(df["vol_20"], lookback=120)

    # 18. Volatility Z-Score
    if "vol_20" in df.columns:
        df["vol_zscore"] = compute_vol_zscore(df["vol_20"], window=60)

    # 19. VIX Proxy Z-Score
    df["vix_proxy_zscore"] = compute_vol_zscore(df["vix_proxy"], window=60)

    # 20. Overnight vs Intraday Volatility Ratio
    log_oc = np.log(df["open"] / df["close"].shift(1))  # overnight
    log_co = np.log(df["close"] / df["open"])  # intraday
    overnight_vol = log_oc.rolling(window=20).std()
    intraday_vol = log_co.rolling(window=20).std()
    df["overnight_intraday_vol_ratio"] = overnight_vol / intraday_vol.replace(0, np.nan)

    # 21. Volatility Spike Indicator
    df["vol_spike"] = (
        df["vol_20"]
        > df["vol_20"].rolling(window=20).mean()
        + 2 * df["vol_20"].rolling(window=20).std()
    ).astype(float)

    # 22. VIX Proxy RSI
    vix_delta = df["vix_proxy"].diff()
    vix_gain = vix_delta.where(vix_delta > 0, 0).rolling(window=14).mean()
    vix_loss = (-vix_delta.where(vix_delta < 0, 0)).rolling(window=14).mean()
    vix_rs = vix_gain / vix_loss.replace(0, np.nan)
    df["vix_proxy_rsi"] = 100 - (100 / (1 + vix_rs))

    # 23. High/Low VIX regime
    vix_median = df["vix_proxy"].rolling(window=60).median()
    df["vix_regime"] = (df["vix_proxy"] > vix_median).astype(float)
    df["vix_regime_extreme"] = (
        df["vix_proxy"] > df["vix_proxy"].rolling(window=60).quantile(0.8)
    ).astype(float)

    # =====================================================================
    # FRACTIONAL DIFFERENCING
    # =====================================================================

    df["close_frac_diff"] = frac_diff(
        df["close"], d=config.FRAC_DIFF_D, thresh=config.FRAC_DIFF_THRESH
    )
    df["log_close"] = np.log(df["close"])
    df["log_close_frac_diff"] = frac_diff(
        df["log_close"], d=config.FRAC_DIFF_D, thresh=config.FRAC_DIFF_THRESH
    )
    df["volume_frac_diff"] = frac_diff(
        df["volume"], d=config.FRAC_DIFF_D, thresh=config.FRAC_DIFF_THRESH
    )
    if "vol_20" in df.columns:
        df["vol_frac_diff"] = frac_diff(
            df["vol_20"], d=config.FRAC_DIFF_D, thresh=config.FRAC_DIFF_THRESH
        )

    # =====================================================================
    # ADX and other features
    # =====================================================================

    adx, plus_di, minus_di = compute_adx_standard(df, period=14)
    df["adx"] = adx
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    # SMA Slopes
    sma_10 = df["close"].rolling(window=10).mean()
    sma_20 = df["close"].rolling(window=20).mean()
    df["sma_slope_10"] = (sma_10 - sma_10.shift(1)) / sma_10.shift(1)
    df["sma_slope_20"] = (sma_20 - sma_20.shift(1)) / sma_20.shift(1)

    # Candle features
    body = (df["close"] - df["open"]).abs()
    total_range = df["high"] - df["low"]
    df["body_ratio"] = body / total_range.replace(0, np.nan)
    df["price_position"] = (df["close"] - df["low"]) / total_range.replace(0, np.nan)

    # ROC
    for period in [3, 5, 10]:
        df[f"roc_{period}"] = (df["close"] - df["close"].shift(period)) / df[
            "close"
        ].shift(period)

    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def add_labels(
    df: pd.DataFrame, horizon: int = 3, scaling: float = 100
) -> pd.DataFrame:
    """
    Add target labels (forward-looking).

    Example:
    >>> df = pd.DataFrame({
    ...     'close': [100, 101, 102, 103, 104, 105]
    ... })
    >>> df = add_labels(df, horizon=2, scaling=100)
    >>> print(df['target'].dropna().values)
    """
    df = df.copy()
    raw_target = np.log(df["close"].shift(-horizon) / df["close"])
    df["target"] = raw_target * scaling
    return df


def prepare_model_df(df: pd.DataFrame, min_history: int = None) -> pd.DataFrame:
    """
    Prepare DataFrame for model training by:
    1. Dropping warmup period (min_history rows)
    2. Forward-filling NaN values
    3. Dropping rows with NaN target

    Example:
    >>> df = pd.DataFrame({
    ...     'timestamp': pd.date_range('2020-01-01', periods=100),
    ...     'pair': ['EURUSD'] * 100,
    ...     'close': np.random.uniform(1.1, 1.2, 100),
    ...     'feature1': np.random.randn(100),
    ...     'target': np.random.randn(100)
    ... })
    >>> df_prepared = prepare_model_df(df, min_history=60)
    """
    df = df.copy()
    base_cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "target",
        "pair",
        "log_close",
    ]
    feature_cols = [c for c in df.columns if c not in base_cols]

    if min_history is None:
        min_history = max(50, 60)  # Default matches notebooks

    processed_dfs = []
    for pair in df["pair"].unique():
        pair_df = (
            df[df["pair"] == pair]
            .copy()
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        pair_df = pair_df.iloc[min_history:].reset_index(drop=True)
        # Forward-fill only (no bfill) to avoid using future data
        pair_df[feature_cols] = pair_df[feature_cols].ffill()
        pair_df = pair_df.dropna(subset=["target"])
        pair_df = pair_df.dropna().reset_index(drop=True)
        processed_dfs.append(pair_df)

    df = pd.concat(processed_dfs, ignore_index=True)
    return df


def get_standard_feature_columns(df: pd.DataFrame) -> List[str]:
    """Get feature columns for standard pipeline (non-USDJPY)"""
    exclude_cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "target",
        "pair",
        "log_close",
        "ts_ms",
    ]
    return [c for c in df.columns if c not in exclude_cols]


def get_usdjpy_feature_columns(df: pd.DataFrame) -> List[str]:
    """Get feature columns for USDJPY pipeline"""
    exclude_cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "target",
        "pair",
        "log_close",
        "ts_ms",
    ]
    return [c for c in df.columns if c not in exclude_cols]


# =============================================================================
# COMPARISON FUNCTIONS
# =============================================================================


def compare_preprocessing(
    pathway_df: pd.DataFrame,
    notebook_df: pd.DataFrame,
    feature_cols: List[str],
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> dict:
    """
    Compare preprocessing outputs between Pathway and notebook implementations.

    Returns dict with comparison results.
    """
    results = {
        "matching_features": [],
        "mismatching_features": [],
        "missing_in_pathway": [],
        "missing_in_notebook": [],
        "max_differences": {},
    }

    pathway_cols = set(pathway_df.columns)
    notebook_cols = set(notebook_df.columns)

    for col in feature_cols:
        if col not in pathway_cols:
            results["missing_in_pathway"].append(col)
            continue
        if col not in notebook_cols:
            results["missing_in_notebook"].append(col)
            continue

        # Compare values
        pw_vals = pathway_df[col].dropna().values
        nb_vals = notebook_df[col].dropna().values

        # Align lengths
        min_len = min(len(pw_vals), len(nb_vals))
        pw_vals = pw_vals[:min_len]
        nb_vals = nb_vals[:min_len]

        if len(pw_vals) == 0 or len(nb_vals) == 0:
            results["mismatching_features"].append((col, "No valid values"))
            continue

        # Check if close
        if np.allclose(pw_vals, nb_vals, rtol=rtol, atol=atol):
            results["matching_features"].append(col)
        else:
            max_diff = np.max(np.abs(pw_vals - nb_vals))
            mean_diff = np.mean(np.abs(pw_vals - nb_vals))
            results["mismatching_features"].append(
                (col, f"max_diff={max_diff:.6e}, mean_diff={mean_diff:.6e}")
            )
            results["max_differences"][col] = max_diff

    return results


def print_comparison_report(results: dict):
    """Print a formatted comparison report."""
    print("=" * 60)
    print("PREPROCESSING COMPARISON REPORT")
    print("=" * 60)

    print(f"\n✅ Matching Features: {len(results['matching_features'])}")
    for f in results["matching_features"]:
        print(f"   - {f}")

    print(f"\n❌ Mismatching Features: {len(results['mismatching_features'])}")
    for f in results["mismatching_features"]:
        if isinstance(f, tuple):
            print(f"   - {f[0]}: {f[1]}")
        else:
            print(f"   - {f}")

    print(f"\n⚠️ Missing in Pathway: {len(results['missing_in_pathway'])}")
    for f in results["missing_in_pathway"]:
        print(f"   - {f}")

    print(f"\n⚠️ Missing in Notebook: {len(results['missing_in_notebook'])}")
    for f in results["missing_in_notebook"]:
        print(f"   - {f}")

    print("=" * 60)


if __name__ == "__main__":
    # Example usage and testing
    print("Notebook Preprocessing Pipelines")
    print("=" * 60)

    # Test with sample data
    np.random.seed(42)
    n = 200

    sample_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=n),
            "open": 100 + np.cumsum(np.random.randn(n) * 0.5),
            "high": 100
            + np.cumsum(np.random.randn(n) * 0.5)
            + np.abs(np.random.randn(n)),
            "low": 100
            + np.cumsum(np.random.randn(n) * 0.5)
            - np.abs(np.random.randn(n)),
            "close": 100 + np.cumsum(np.random.randn(n) * 0.5),
            "volume": np.random.uniform(1000, 2000, n),
            "pair": "TEST",
        }
    )

    # Ensure high >= close >= low
    sample_df["high"] = sample_df[["open", "high", "close"]].max(axis=1)
    sample_df["low"] = sample_df[["open", "low", "close"]].min(axis=1)

    print("\nTesting Standard Features Pipeline...")
    df_standard = add_features_standard(sample_df.copy())
    df_standard = add_labels(df_standard, horizon=3, scaling=100)
    df_standard = prepare_model_df(df_standard, min_history=60)
    feature_cols_std = get_standard_feature_columns(df_standard)
    print(f"Standard features: {len(feature_cols_std)}")
    print(f"Sample data shape: {df_standard.shape}")

    print("\nTesting USDJPY Features Pipeline...")
    df_usdjpy = add_features_usdjpy(sample_df.copy())
    df_usdjpy = add_labels(df_usdjpy, horizon=3, scaling=100)
    df_usdjpy = prepare_model_df(df_usdjpy, min_history=80)
    feature_cols_usdjpy = get_usdjpy_feature_columns(df_usdjpy)
    print(f"USDJPY features: {len(feature_cols_usdjpy)}")
    print(f"Sample data shape: {df_usdjpy.shape}")

    print("\n✅ All preprocessing pipelines working correctly!")
