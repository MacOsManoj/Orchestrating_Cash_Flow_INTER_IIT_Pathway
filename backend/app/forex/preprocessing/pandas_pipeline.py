import os
import pandas as pd
import numpy as np
import logging
from typing import List, Tuple

from app.forex.preprocessing.config import PathwayFeatureConfig

logger = logging.getLogger(__name__)


def preprocess_forex_data(
    data_dir: str, pairs: List[str], config: PathwayFeatureConfig = None
) -> pd.DataFrame:
    """
    Complete batch preprocessing for XGBoost models (Pandas implementation).
    """
    config = config or PathwayFeatureConfig()
    results = []

    for pair in pairs:
        csv_path = os.path.join(data_dir, f"{pair}.csv")
        if not os.path.exists(csv_path):
            logger.warning(f"File not found: {csv_path}")
            continue

        df = pd.read_csv(csv_path)
        df["pair"] = pair
        if "ts_ms" in df.columns:
            df = df.sort_values("ts_ms").reset_index(drop=True)
            # Convert timestamp
            df["timestamp"] = pd.to_datetime(
                df["ts_ms"], unit="ms", utc=True
            ).dt.tz_localize(None)
        else:
            # Handle case where ts_ms might be missing
            pass

        # Point-in-time
        body = (df["close"] - df["open"]).abs()
        total_range = df["high"] - df["low"]
        df["body_ratio"] = body / total_range.replace(0, np.nan)
        df["price_position"] = (df["close"] - df["low"]) / total_range.replace(
            0, np.nan
        )
        df["hl_spread"] = df["high"] - df["low"]

        if pair == "USDJPY":
            df["log_close"] = np.log(df["close"])

        df["log_ret"] = np.log(df["close"] / df["close"].shift(1))

        for lag in range(1, config.lag_returns + 1):
            df[f"log_ret_lag_{lag}"] = df["log_ret"].shift(lag)

        df["sma_fast"] = df["close"].rolling(window=config.sma_fast).mean()
        df["sma_slow"] = df["close"].rolling(window=config.sma_slow).mean()
        df["sma_spread"] = df["sma_fast"] - df["sma_slow"]

        sma_10 = df["close"].rolling(window=10).mean()
        sma_20 = df["close"].rolling(window=20).mean()
        df["sma_slope_10"] = (sma_10 - sma_10.shift(1)) / sma_10.shift(1)
        df["sma_slope_20"] = (sma_20 - sma_20.shift(1)) / sma_20.shift(1)

        ema_fast = df["close"].ewm(span=config.macd_fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=config.macd_slow, adjust=False).mean()
        df["macd_line"] = ema_fast - ema_slow
        df["macd_signal"] = (
            df["macd_line"].ewm(span=config.macd_signal, adjust=False).mean()
        )
        df["macd_hist"] = df["macd_line"] - df["macd_signal"]

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=config.rsi_period).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - df["close"].shift(1)).abs()
        tr3 = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=config.atr_period).mean()

        # ADX
        high, low = df["high"], df["low"]
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        atr_14 = tr.rolling(window=14).mean()
        df["plus_di"] = 100 * pd.Series(plus_dm).rolling(window=14).mean() / atr_14
        df["minus_di"] = 100 * pd.Series(minus_dm).rolling(window=14).mean() / atr_14
        dx = (
            100
            * (df["plus_di"] - df["minus_di"]).abs()
            / (df["plus_di"] + df["minus_di"])
        )
        df["adx"] = dx.rolling(window=14).mean()

        for period in [3, 5, 10]:
            df[f"roc_{period}"] = (df["close"] - df["close"].shift(period)) / df[
                "close"
            ].shift(period)

        df["volume_ewma"] = df["volume"].ewm(alpha=config.ewma_alpha).mean()
        df["volume_change"] = df["volume"].diff()

        df["rv_10"] = df["log_ret"].rolling(window=10).std() * np.sqrt(10)
        df["rv_60"] = df["log_ret"].rolling(window=60).std() * np.sqrt(60)
        df["rv_ratio"] = df["rv_10"] / df["rv_60"].replace(0, np.nan)

        if pair == "USDJPY":
            for window in config.vol_windows:
                rv = df["log_ret"].rolling(window=window).std()
                df[f"vol_{window}"] = rv * np.sqrt(252)

            if "vol_10" in df.columns and "vol_60" in df.columns:
                df["vol_ratio_10_60"] = df["vol_10"] / df["vol_60"].replace(0, np.nan)
            if "vol_20" in df.columns and "vol_60" in df.columns:
                df["vol_ratio_20_60"] = df["vol_20"] / df["vol_60"].replace(0, np.nan)

            if "vol_20" in df.columns:
                df["vol_of_vol"] = df["vol_20"].rolling(window=20).std()
                df["log_vol_20"] = np.log(df["vol_20"].replace(0, np.nan) + 1e-9)
                df["vol_ewma"] = df["log_ret"].ewm(span=20).std()

        df["ewma_ret"] = df["log_ret"].ewm(alpha=config.ewma_alpha).mean()
        df["ewma_vol"] = df["log_ret"].ewm(alpha=config.ewma_alpha).std()

        df["rolling_skew"] = (
            df["log_ret"].rolling(window=config.rolling_skew_window).skew()
        )
        df["rolling_kurt"] = (
            df["log_ret"].rolling(window=config.rolling_kurt_window).kurt()
        )

        df["dow_sin"] = np.sin(2 * np.pi * df["timestamp"].dt.dayofweek / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df["timestamp"].dt.dayofweek / 7)

        if pair == "USDJPY":
            # VIX features
            log_hl = np.log(df["high"] / df["low"]) ** 2
            log_co = np.log(df["close"] / df["open"]) ** 2
            gk_vol = np.sqrt(0.5 * log_hl - (2 * np.log(2) - 1) * log_co)
            df["vol_gk_20"] = gk_vol.rolling(window=20).mean()
            df["vol_gk_60"] = gk_vol.rolling(window=60).mean()

            parkinson = np.sqrt(log_hl / (4 * np.log(2)))
            df["vol_parkinson_20"] = parkinson.rolling(window=20).mean()

            log_ho = np.log(df["high"] / df["open"])
            log_lo = np.log(df["low"] / df["open"])
            log_co_yz = np.log(df["close"] / df["open"])
            rs_yz = log_ho * (log_ho - log_co_yz) + log_lo * (log_lo - log_co_yz)
            log_oc = np.log(df["open"] / df["close"].shift(1))
            overnight_var = log_oc.rolling(window=20).var()
            open_close_var = log_co_yz.rolling(window=20).var()
            rs_var = rs_yz.rolling(window=20).mean()
            k = 0.34
            yz_var = overnight_var + k * open_close_var + (1 - k) * rs_var
            df["vol_yang_zhang_20"] = np.sqrt(yz_var)

            # Simple approximation for rest of YZ features and VIX proxy
            realized_vol = df["log_ret"].rolling(window=20).std() * np.sqrt(252)
            yz_vol_ann = df["vol_yang_zhang_20"] * np.sqrt(252)
            df["vix_proxy"] = (0.5 * realized_vol + 0.5 * yz_vol_ann) * 100

        df["target"] = (
            np.log(df["close"].shift(-config.horizon) / df["close"])
            * config.target_scaling
        )
        df = df.replace([np.inf, -np.inf], np.nan)
        results.append(df)

    if not results:
        raise ValueError("No data loaded")

    combined = pd.concat(results, ignore_index=True)

    min_history = config.min_history
    processed_dfs = []

    # Feature columns identification
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
        "ts_ms",
    ]
    feature_cols = [c for c in combined.columns if c not in base_cols]

    for pair_name in combined["pair"].unique():
        pair_data = combined[combined["pair"] == pair_name].copy()
        if "timestamp" in pair_data.columns:
            pair_data = pair_data.sort_values("timestamp").reset_index(drop=True)
            pair_data = pair_data.iloc[min_history:].reset_index(drop=True)
            pair_data[feature_cols] = pair_data[feature_cols].ffill()
            pair_data = pair_data.dropna(subset=["target"])
            pair_data = pair_data.dropna().reset_index(drop=True)
            processed_dfs.append(pair_data)

    if not processed_dfs:
        return pd.DataFrame()

    combined = pd.concat(processed_dfs, ignore_index=True)
    return combined


def batch_preprocess_with_pathway(
    data_dir: str,
    pairs: List[str],
    output_dir: str = None,
    config: PathwayFeatureConfig = None,
    add_targets: bool = True,
) -> pd.DataFrame:
    """Wrapper calling pandas preprocessing."""
    config = config or PathwayFeatureConfig()
    df = preprocess_forex_data(data_dir, pairs, config)

    if not add_targets and "target" in df.columns:
        df = df.drop(columns=["target"])

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "processed_features.csv")
        df.to_csv(output_path, index=False)

    return df


def get_feature_columns_from_df(df: pd.DataFrame) -> List[str]:
    """Get list of feature columns from df."""
    exclude_cols = [
        "timestamp",
        "pair",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "target",
        "log_close",
        "ts_ms",
    ]
    # Filter for numeric columns only and exclude base cols
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if c not in exclude_cols]


def get_feature_columns(exclude_cols: List[str] = None) -> Tuple[List[str], List[str]]:
    """Get list of feature column names."""
    exclude = exclude_cols or [
        "ts_ms",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "pair",
        "target",
        "future_close",
        "close_history",
        "returns_tuple_rsi",
        "tr_tuple",
        "ret_tuple_moments",
    ]
    exclude_patterns = ["_tuple_", "close_tuple_", "ret_tuple_"]
    return exclude, exclude_patterns
