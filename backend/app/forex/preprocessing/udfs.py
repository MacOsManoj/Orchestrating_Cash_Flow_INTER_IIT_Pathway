import math
import pathway as pw
from pathway import reducers

# =============================================================================
# UDF Functions - Core Calculations
# These are pure functions that operate on values, not future data
# =============================================================================


@pw.udf
def compute_log_return(close_current: float, close_prev: float) -> float:
    """
    Compute log return between two consecutive closes.
    Uses ONLY past data: log(close_t / close_{t-1})
    """
    if close_prev is None or close_prev <= 0 or close_current <= 0:
        return 0.0
    return math.log(close_current / close_prev)


@pw.udf
def compute_true_range(high: float, low: float, prev_close: float) -> float:
    """
    Compute True Range for ATR calculation.
    Uses current bar's H/L and PREVIOUS close (no forward leakage).
    """
    if prev_close is None or prev_close <= 0:
        return high - low

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    return max(tr1, tr2, tr3)


@pw.udf
def safe_divide(numerator: float, denominator: float) -> float:
    """Safe division with NaN handling"""
    if denominator is None or denominator == 0:
        return 0.0
    if numerator is None:
        return 0.0
    return numerator / denominator


@pw.udf
def compute_body_ratio(
    open_price: float, close: float, high: float, low: float
) -> float:
    """Compute candle body ratio - uses only current bar data"""
    body = abs(close - open_price)
    total_range = high - low
    if total_range <= 0:
        return 0.0
    return body / total_range


@pw.udf
def compute_price_position(close: float, low: float, high: float) -> float:
    """Compute price position within bar - uses only current bar data"""
    total_range = high - low
    if total_range <= 0:
        return 0.5
    return (close - low) / total_range


@pw.udf
def compute_hl_spread(high: float, low: float) -> float:
    """Compute high-low spread - uses only current bar data"""
    return high - low


@pw.udf
def compute_dow_sin(timestamp: pw.DateTimeUtc) -> float:
    """Compute day-of-week sine encoding - uses only current timestamp"""
    # Monday = 0, Sunday = 6
    dow = timestamp.weekday()
    return math.sin(2 * math.pi * dow / 7)


@pw.udf
def compute_dow_cos(timestamp: pw.DateTimeUtc) -> float:
    """Compute day-of-week cosine encoding - uses only current timestamp"""
    dow = timestamp.weekday()
    return math.cos(2 * math.pi * dow / 7)


@pw.udf
def compute_garman_klass_component(
    open_price: float, high: float, low: float, close: float
) -> float:
    """
    Compute Garman-Klass volatility component for a single bar.
    Uses only current bar data.
    """
    if high <= 0 or low <= 0 or open_price <= 0 or close <= 0:
        return 0.0
    if high <= low:
        return 0.0

    log_hl = math.log(high / low) ** 2
    log_co = math.log(close / open_price) ** 2

    # GK component (will be averaged in rolling window)
    return 0.5 * log_hl - (2 * math.log(2) - 1) * log_co


@pw.udf
def compute_parkinson_component(high: float, low: float) -> float:
    """
    Compute Parkinson volatility component for a single bar.
    Uses only current bar data.
    """
    if high <= 0 or low <= 0 or high <= low:
        return 0.0

    log_hl = math.log(high / low) ** 2
    return log_hl / (4 * math.log(2))


@pw.udf
def sqrt_safe(value: float) -> float:
    """Safe square root"""
    if value is None or value < 0:
        return 0.0
    return math.sqrt(value)


@pw.udf
def log_safe(value: float, eps: float = 1e-9) -> float:
    """Safe logarithm with epsilon"""
    if value is None or value <= 0:
        return 0.0
    return math.log(value + eps)


@pw.udf
def compute_roc(close_current: float, close_past: float) -> float:
    """
    Compute Rate of Change.
    close_past is the close from N periods ago (PAST data only).
    """
    if close_past is None or close_past <= 0:
        return 0.0
    return (close_current - close_past) / close_past


@pw.udf
def clamp_value(value: float, min_val: float = -1e6, max_val: float = 1e6) -> float:
    """Clamp value to prevent inf/-inf"""
    if value is None:
        return 0.0
    if math.isinf(value) or math.isnan(value):
        return 0.0
    return max(min_val, min(max_val, value))


# =============================================================================
# Rolling Window Statistics UDFs
# These take lists of PAST values and compute statistics
# =============================================================================


@pw.udf
def rolling_mean(values: list) -> float:
    """Compute mean of a list of past values"""
    if not values or len(values) == 0:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


@pw.udf
def rolling_std(values: list) -> float:
    """Compute standard deviation of a list of past values"""
    if not values or len(values) < 2:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if len(valid) < 2:
        return 0.0
    mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1)
    return math.sqrt(variance) if variance > 0 else 0.0


@pw.udf
def rolling_skew(values: list) -> float:
    """Compute skewness of a list of past values"""
    if not values or len(values) < 3:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if len(valid) < 3:
        return 0.0

    n = len(valid)
    mean = sum(valid) / n

    m2 = sum((x - mean) ** 2 for x in valid) / n
    m3 = sum((x - mean) ** 3 for x in valid) / n

    if m2 <= 0:
        return 0.0

    return m3 / (m2**1.5) if m2 > 0 else 0.0


@pw.udf
def rolling_kurt(values: list) -> float:
    """Compute kurtosis of a list of past values"""
    if not values or len(values) < 4:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if len(valid) < 4:
        return 0.0

    n = len(valid)
    mean = sum(valid) / n

    m2 = sum((x - mean) ** 2 for x in valid) / n
    m4 = sum((x - mean) ** 4 for x in valid) / n

    if m2 <= 0:
        return 0.0

    return (m4 / (m2**2)) - 3.0  # Excess kurtosis


@pw.udf
def ewma_update(prev_ewma: float, current_value: float, alpha: float) -> float:
    """
    Update EWMA with new value.
    EWMA uses exponentially decaying weights on PAST values only.
    Formula: EWMA_t = alpha * value_t + (1-alpha) * EWMA_{t-1}
    """
    if prev_ewma is None:
        return current_value if current_value is not None else 0.0
    if current_value is None:
        return prev_ewma
    return alpha * current_value + (1 - alpha) * prev_ewma


@pw.udf
def compute_rsi_from_gains_losses(avg_gain: float, avg_loss: float) -> float:
    """
    Compute RSI from average gain and loss.
    RSI = 100 - (100 / (1 + RS)) where RS = avg_gain / avg_loss
    Uses PAST average gains and losses.
    """
    if avg_loss is None or avg_loss == 0:
        if avg_gain is None or avg_gain == 0:
            return 50.0  # Neutral
        return 100.0  # All gains
    if avg_gain is None:
        return 0.0  # All losses

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


@pw.udf
def compute_macd_histogram(macd_line: float, macd_signal: float) -> float:
    """Compute MACD histogram from line and signal"""
    if macd_line is None or macd_signal is None:
        return 0.0
    return macd_line - macd_signal


@pw.udf
def compute_vol_regime(volatility: float, vol_median: float) -> float:
    """Compute volatility regime indicator"""
    if volatility is None or vol_median is None:
        return 0.0
    return 1.0 if volatility > vol_median else 0.0


@pw.udf
def compute_vol_zscore(vol: float, vol_mean: float, vol_std: float) -> float:
    """Compute volatility z-score"""
    if vol is None or vol_mean is None or vol_std is None or vol_std == 0:
        return 0.0
    return (vol - vol_mean) / vol_std


# =============================================================================
# Target Label Computation
# CLEARLY MARKED AS FORWARD-LOOKING - Must be computed separately
# =============================================================================


@pw.udf
def compute_forward_target(
    close_current: float, close_future: float, scaling: float
) -> float:
    """
    FORWARD-LOOKING TARGET LABEL

    ⚠️ WARNING: This uses FUTURE data (close_future) and should ONLY be used
    for creating training labels, NEVER as a feature.
    """
    if close_current is None or close_future is None:
        return float("nan")
    if close_current <= 0 or close_future <= 0:
        return float("nan")
    return math.log(close_future / close_current) * scaling


# =============================================================================
# Fractional Differencing UDF
# Uses PAST data only through the weight vector
# =============================================================================


@pw.udf
def frac_diff_series(values: list, d: float = 0.4, thresh: float = 1e-5) -> float:
    """
    Apply fractional differencing to a series of PAST values.
    """
    if not values or len(values) == 0:
        return 0.0

    # Compute weights
    weights = [1.0]
    k = 1
    while k < len(values):
        w_k = -weights[-1] * (d - k + 1) / k
        if abs(w_k) < thresh:
            break
        weights.append(w_k)
        k += 1

    # Reverse weights (oldest weight first)
    weights = weights[::-1]

    # Ensure we have enough values
    width = len(weights)
    if len(values) < width:
        return 0.0

    # Apply weights to most recent 'width' values
    recent_values = values[-width:]
    valid = [v for v in recent_values if v is not None and not math.isnan(v)]

    if len(valid) < width:
        return 0.0

    result = sum(w * v for w, v in zip(weights, valid))
    return result if not math.isnan(result) and not math.isinf(result) else 0.0


# =============================================================================
# ADX Computation UDFs
# =============================================================================


@pw.udf
def compute_plus_dm(
    high_current: float, high_prev: float, low_current: float, low_prev: float
) -> float:
    """Compute +DM (positive directional movement) - uses current and previous bar"""
    if high_prev is None or low_prev is None:
        return 0.0
    up_move = high_current - high_prev
    down_move = low_prev - low_current
    if up_move > down_move and up_move > 0:
        return up_move
    return 0.0


@pw.udf
def compute_minus_dm(
    high_current: float, high_prev: float, low_current: float, low_prev: float
) -> float:
    """Compute -DM (negative directional movement) - uses current and previous bar"""
    if high_prev is None or low_prev is None:
        return 0.0
    up_move = high_current - high_prev
    down_move = low_prev - low_current
    if down_move > up_move and down_move > 0:
        return down_move
    return 0.0


@pw.udf
def compute_di(dm_avg: float, atr: float) -> float:
    """Compute directional indicator (+DI or -DI)"""
    if atr is None or atr == 0:
        return 0.0
    return 100 * dm_avg / atr


@pw.udf
def compute_dx(plus_di: float, minus_di: float) -> float:
    """Compute DX (directional index)"""
    if plus_di is None or minus_di is None:
        return 0.0
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return 0.0
    return 100 * abs(plus_di - minus_di) / di_sum


# =============================================================================
# VIX Proxy Computation UDFs (for USDJPY)
# =============================================================================


@pw.udf
def compute_yang_zhang_components(
    open_price: float, high: float, low: float, close: float, prev_close: float
) -> tuple:
    """
    Compute Yang-Zhang volatility components for a single bar.
    Returns (overnight_var_component, open_close_var_component, rs_component)
    """
    if prev_close is None or prev_close <= 0:
        return (0.0, 0.0, 0.0)
    if open_price <= 0 or high <= 0 or low <= 0 or close <= 0:
        return (0.0, 0.0, 0.0)

    log_ho = math.log(high / open_price)
    log_lo = math.log(low / open_price)
    log_co = math.log(close / open_price)
    log_oc = math.log(open_price / prev_close)

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    return (log_oc**2, log_co**2, rs)


@pw.udf
def compute_rogers_satchell_component(
    open_price: float, high: float, low: float, close: float
) -> float:
    """Compute Rogers-Satchell volatility component for a single bar"""
    if open_price <= 0 or high <= 0 or low <= 0 or close <= 0:
        return 0.0

    log_ho = math.log(high / open_price)
    log_hc = math.log(high / close)
    log_lo = math.log(low / open_price)
    log_lc = math.log(low / close)

    return log_ho * log_hc + log_lo * log_lc


# =============================================================================
# Tuple-based Computation UDFs
# =============================================================================


@pw.udf
def compute_std_from_tuple(values: tuple) -> float:
    """Compute standard deviation from a tuple of values"""
    if not values or len(values) < 2:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if len(valid) < 2:
        return 0.0
    mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1)
    return math.sqrt(variance) if variance > 0 else 0.0


@pw.udf
def compute_skew_from_tuple(values: tuple) -> float:
    """Compute skewness from a tuple of values"""
    if not values or len(values) < 3:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if len(valid) < 3:
        return 0.0
    n = len(valid)
    mean = sum(valid) / n
    m2 = sum((x - mean) ** 2 for x in valid) / n
    m3 = sum((x - mean) ** 3 for x in valid) / n
    if m2 <= 0:
        return 0.0
    return m3 / (m2**1.5)


@pw.udf
def compute_kurt_from_tuple(values: tuple) -> float:
    """Compute excess kurtosis from a tuple of values"""
    if not values or len(values) < 4:
        return 0.0
    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if len(valid) < 4:
        return 0.0
    n = len(valid)
    mean = sum(valid) / n
    m2 = sum((x - mean) ** 2 for x in valid) / n
    m4 = sum((x - mean) ** 4 for x in valid) / n
    if m2 <= 0:
        return 0.0
    return (m4 / (m2**2)) - 3.0


@pw.udf
def compute_rsi_from_tuple(returns: tuple) -> float:
    """
    Compute RSI from a tuple of returns.
    """
    if not returns or len(returns) < 2:
        return 50.0  # Neutral

    valid = [
        r for r in returns if r is not None and not math.isnan(r) and not math.isinf(r)
    ]
    if len(valid) < 2:
        return 50.0

    gains = [r for r in valid if r > 0]
    losses = [-r for r in valid if r < 0]

    avg_gain = sum(gains) / len(valid) if gains else 0
    avg_loss = sum(losses) / len(valid) if losses else 0

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


@pw.udf
def compute_ewma_from_tuple(values: tuple, alpha: float) -> float:
    """
    Compute EWMA from a tuple of values (oldest to newest).
    """
    if not values or len(values) == 0:
        return 0.0

    valid = [
        v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if not valid:
        return 0.0

    # EWMA: start from oldest, weight more recent values higher
    ewma = valid[0]
    for v in valid[1:]:
        ewma = alpha * v + (1 - alpha) * ewma
    return ewma


@pw.udf
def get_lagged_value_from_tuple(values: tuple, lag: int) -> float:
    """
    Get the value from lag periods ago.
    """
    if not values or len(values) <= lag:
        return 0.0
    # values[-1] is current, values[-2] is t-1, etc.
    idx = len(values) - 1 - lag
    if idx < 0:
        return 0.0
    val = values[idx]
    if val is None or math.isnan(val) or math.isinf(val):
        return 0.0
    return val


@pw.udf
def compute_atr_from_tuples(tr_values: tuple) -> float:
    """Compute ATR (Average True Range) from tuple of TR values"""
    if not tr_values or len(tr_values) == 0:
        return 0.0
    valid = [
        v
        for v in tr_values
        if v is not None and not math.isnan(v) and not math.isinf(v)
    ]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


@pw.udf
def compute_volatility_annualized(std: float, annualize: bool = True) -> float:
    """Annualize volatility (assuming daily data)"""
    if std is None or std <= 0:
        return 0.0
    if annualize:
        return std * math.sqrt(252)
    return std


@pw.udf
def compute_log_return_from_history(close_history: tuple) -> float:
    """Compute log return from close price history tuple"""
    if not close_history or len(close_history) < 2:
        return 0.0
    current = close_history[-1]
    prev = close_history[-2]
    if prev is None or prev <= 0 or current is None or current <= 0:
        return 0.0
    return math.log(current / prev)


@pw.udf
def get_lagged_return(close_history: tuple, lag: int) -> float:
    """Get log return from lag periods ago"""
    if not close_history or len(close_history) < lag + 2:
        return 0.0
    idx_current = len(close_history) - 1 - lag
    idx_prev = idx_current - 1
    if idx_prev < 0:
        return 0.0
    current = close_history[idx_current]
    prev = close_history[idx_prev]
    if prev is None or prev <= 0 or current is None or current <= 0:
        return 0.0
    return math.log(current / prev)


@pw.udf
def compute_true_range_from_history(
    high: float, low: float, close_history: tuple
) -> float:
    """Compute True Range using previous close from history"""
    if not close_history or len(close_history) < 2:
        return high - low
    prev_close = close_history[-2]
    if prev_close is None or prev_close <= 0:
        return high - low

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    return max(tr1, tr2, tr3)


@pw.udf
def compute_ewma_vol_from_tuple(returns: tuple, alpha: float) -> float:
    """Compute EWMA volatility from returns tuple"""
    if not returns or len(returns) < 2:
        return 0.0

    valid = [
        r for r in returns if r is not None and not math.isnan(r) and not math.isinf(r)
    ]
    if len(valid) < 2:
        return 0.0

    # Compute squared returns
    sq_returns = [r**2 for r in valid]

    # EWMA of squared returns
    ewma_sq = sq_returns[0]
    for sq in sq_returns[1:]:
        ewma_sq = alpha * sq + (1 - alpha) * ewma_sq

    return math.sqrt(ewma_sq) if ewma_sq > 0 else 0.0


@pw.udf
def compute_dow_sin_from_ms(ts_ms: int) -> float:
    """Compute day-of-week sine encoding from timestamp in ms"""
    from datetime import datetime

    dt = datetime.utcfromtimestamp(ts_ms / 1000)
    dow = dt.weekday()  # Monday=0, Sunday=6
    return math.sin(2 * math.pi * dow / 7)


@pw.udf
def compute_dow_cos_from_ms(ts_ms: int) -> float:
    """Compute day-of-week cosine encoding from timestamp in ms"""
    from datetime import datetime

    dt = datetime.utcfromtimestamp(ts_ms / 1000)
    dow = dt.weekday()
    return math.cos(2 * math.pi * dow / 7)


@pw.udf
def compute_gk_vol(components: tuple) -> float:
    """Compute Garman-Klass volatility from components"""
    if not components:
        return 0.0
    valid = [c for c in components if c is not None and not math.isnan(c) and c > 0]
    if not valid:
        return 0.0
    avg = sum(valid) / len(valid)
    return math.sqrt(avg) * math.sqrt(252) if avg > 0 else 0.0


@pw.udf
def compute_parkinson_vol(components: tuple) -> float:
    """Compute Parkinson volatility from components"""
    if not components:
        return 0.0
    valid = [c for c in components if c is not None and not math.isnan(c) and c > 0]
    if not valid:
        return 0.0
    avg = sum(valid) / len(valid)
    return math.sqrt(avg) * math.sqrt(252) if avg > 0 else 0.0


@pw.udf
def compute_rs_vol(components: tuple) -> float:
    """Compute Rogers-Satchell volatility from components"""
    if not components:
        return 0.0
    valid = [c for c in components if c is not None and not math.isnan(c)]
    if not valid:
        return 0.0
    avg = sum(valid) / len(valid)
    return math.sqrt(max(0, avg)) * math.sqrt(252)


@pw.udf
def compute_vix_proxy_combined(rv: float, gk: float, pk: float) -> float:
    """Combine different volatility estimators into VIX-like proxy"""
    if rv is None:
        rv = 0.0
    if gk is None:
        gk = 0.0
    if pk is None:
        pk = 0.0

    # Weighted average of estimators
    return (0.4 * rv + 0.3 * gk + 0.3 * pk) * 100  # Scale like VIX


@pw.udf
def compute_sma_slope_from_tuple(values: tuple, window: int) -> float:
    """Compute SMA slope using history tuple"""
    if not values or len(values) < window + 1:
        return 0.0

    # Needs valid values
    valid = [v for v in values if v is not None and not math.isnan(v)]
    if len(valid) < window + 1:
        return 0.0

    # SMA at T
    sma_t = sum(valid[-window:]) / window

    # SMA at T-1
    sma_prev = sum(valid[-(window + 1) : -1]) / window

    if sma_prev == 0:
        return 0.0

    return (sma_t - sma_prev) / sma_prev


@pw.udf
def compute_macd_tuple_from_history(
    values: tuple, fast: int, slow: int, signal: int
) -> tuple:
    """
    Compute MACD (line, signal, hist) from history tuple.
    Re-computes EMAs over the tuple history.
    """
    if not values or len(values) < slow:
        return (0.0, 0.0, 0.0)

    valid = [v for v in values if v is not None and not math.isnan(v)]
    if len(valid) < slow:
        return (0.0, 0.0, 0.0)

    # Calculate EMAs
    # Fast EMA
    k_fast = 2 / (fast + 1)
    ema_fast = valid[0]
    ema_fast_series = [ema_fast]
    for v in valid[1:]:
        ema_fast = v * k_fast + ema_fast * (1 - k_fast)
        ema_fast_series.append(ema_fast)

    # Slow EMA
    k_slow = 2 / (slow + 1)
    ema_slow = valid[0]
    ema_slow_series = [ema_slow]
    for v in valid[1:]:
        ema_slow = v * k_slow + ema_slow * (1 - k_slow)
        ema_slow_series.append(ema_slow)

    # MACD Line
    macd_line_series = []
    for f, s in zip(ema_fast_series, ema_slow_series):
        macd_line_series.append(f - s)

    # Signal Line (EMA of MACD Line)
    k_signal = 2 / (signal + 1)
    signal_line = macd_line_series[0]  # Not quite right if series starts at 0 but ok
    # Actually we should start signal calculation after we have enough macd points?
    # Standard practice: start from beginning.

    for m in macd_line_series[1:]:
        signal_line = m * k_signal + signal_line * (1 - k_signal)

    current_macd_line = macd_line_series[-1]
    current_signal_line = signal_line
    current_hist = current_macd_line - current_signal_line

    return (current_macd_line, current_signal_line, current_hist)


@pw.udf
def compute_adx_tuple_from_history(
    highs: tuple, lows: tuple, closes: tuple, period: int = 14
) -> tuple:
    """
    Compute (plus_di, minus_di, adx) from history.
    """
    if not highs or not lows or not closes:
        return (0.0, 0.0, 0.0)

    # Unpack and validate
    h = [v for v in highs if v is not None and not math.isnan(v)]
    l = [v for v in lows if v is not None and not math.isnan(v)]
    c = [v for v in closes if v is not None and not math.isnan(v)]

    if len(h) != len(l) or len(h) != len(c):
        length = min(len(h), len(l), len(c))
        h = h[-length:]
        l = l[-length:]
        c = c[-length:]

    if len(h) < period * 2:
        return (0.0, 0.0, 0.0)

    # Compute TR, +DM, -DM
    tr_list = []
    pdm_list = []
    mdm_list = []

    # First TR etc. needs previous close
    # We start from index 1
    for i in range(1, len(h)):
        # TR
        tr1 = h[i] - l[i]
        tr2 = abs(h[i] - c[i - 1])
        tr3 = abs(l[i] - c[i - 1])
        tr_list.append(max(tr1, tr2, tr3))

        # DM
        up_move = h[i] - h[i - 1]
        down_move = l[i - 1] - l[i]

        if up_move > down_move and up_move > 0:
            pdm_list.append(up_move)
        else:
            pdm_list.append(0.0)

        if down_move > up_move and down_move > 0:
            mdm_list.append(down_move)
        else:
            mdm_list.append(0.0)

    # Need to smooth these. Wilder's smoothing.
    # First smoothed value is sum of first 'period' values
    if len(tr_list) < period:
        return (0.0, 0.0, 0.0)

    tr_smooth = sum(tr_list[:period])
    pdm_smooth = sum(pdm_list[:period])
    mdm_smooth = sum(mdm_list[:period])

    # Calculate initial DX?
    # Just iterate through the rest
    dx_list = []

    # Helper for DX
    def calc_dx(pdm_s, mdm_s, tr_s):
        if tr_s == 0:
            return 0.0
        pdi = 100 * pdm_s / tr_s
        mdi = 100 * mdm_s / tr_s
        if pdi + mdi == 0:
            return 0.0
        return 100 * abs(pdi - mdi) / (pdi + mdi)

    dx_list.append(calc_dx(pdm_smooth, mdm_smooth, tr_smooth))

    for i in range(period, len(tr_list)):
        curr_tr = tr_list[i]
        curr_pdm = pdm_list[i]
        curr_mdm = mdm_list[i]

        # Wilder's smoothing: previous - (previous / period) + current
        tr_smooth = tr_smooth - (tr_smooth / period) + curr_tr
        pdm_smooth = pdm_smooth - (pdm_smooth / period) + curr_pdm
        mdm_smooth = mdm_smooth - (mdm_smooth / period) + curr_mdm

        dx_list.append(calc_dx(pdm_smooth, mdm_smooth, tr_smooth))

    # ADX is SMA of DX over period
    # We take the last ADX value
    if len(dx_list) < period:
        return (0.0, 0.0, 0.0)

    # If we want exact ADX matching pandas `rolling(14).mean()` of DX?
    # Pandas `rolling` is simple moving average.
    # Standard ADX uses Wilder's smoothing on DX too usually, or SMA.
    # TA-Lib uses Wilder's. Pandas implementation in `pandas_pipeline.py` used `rolling(window=14).mean()`.
    # So we will use SMA of DX.

    adx = sum(dx_list[-period:]) / period

    # Current +DI, -DI are based on latest smoothed values
    pdi = 100 * pdm_smooth / tr_smooth if tr_smooth > 0 else 0.0
    mdi = 100 * mdm_smooth / tr_smooth if tr_smooth > 0 else 0.0

    return (pdi, mdi, adx)


@pw.udf
def compute_roc_from_tuple(values: tuple, period: int) -> float:
    """Compute ROC from history tuple"""
    if not values or len(values) < period + 1:
        return 0.0

    valid = [v for v in values if v is not None and not math.isnan(v)]
    if len(valid) < period + 1:
        return 0.0

    current = valid[-1]
    prev = valid[-(period + 1)]

    if prev == 0:
        return 0.0

    return (current - prev) / prev
