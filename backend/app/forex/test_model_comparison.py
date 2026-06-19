"""
Direct comparison: Run the exact notebook logic vs run.py logic
and compare the model training results.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math
import os
import sys

# Add fx directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing import (
    PathwayFeatureConfig,
    preprocess_forex_data,
    get_feature_columns_from_df,
)
from notebook_preprocessing import (
    add_features_standard,
    add_features_usdjpy,
    add_labels,
    prepare_model_df,
    get_standard_feature_columns,
    get_usdjpy_feature_columns,
)


def load_raw_data(data_dir: str, pair: str) -> pd.DataFrame:
    """Load raw data for a currency pair."""
    csv_path = os.path.join(data_dir, f"{pair}.csv")
    df = pd.read_csv(csv_path)
    df["pair"] = pair
    df = df.sort_values("ts_ms").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.tz_localize(
        None
    )
    return df


def train_xgb_model(X_train, y_train, X_test, y_test, target_scaling=100):
    """Train XGBoost model and return results."""
    XGB_PARAMS = {
        "n_estimators": 200,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "reg:squarederror",
        "n_jobs": -1,
        "random_state": 42,
        "early_stopping_rounds": 20,
    }

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Create validation set
    val_split = int(len(X_train_scaled) * 0.9)
    X_tr, X_val = X_train_scaled[:val_split], X_train_scaled[val_split:]
    y_tr, y_val = y_train.iloc[:val_split], y_train.iloc[val_split:]

    # Train model
    model = xgb.XGBRegressor(**XGB_PARAMS)
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

    # Predict
    predictions_scaled = model.predict(X_test_scaled)

    # Clip predictions
    train_std = y_train.std()
    train_mean = y_train.mean()
    clip_range = (train_mean - 3 * train_std, train_mean + 3 * train_std)
    predictions_scaled = np.clip(predictions_scaled, clip_range[0], clip_range[1])

    # Convert to log-return scale
    predictions = predictions_scaled / target_scaling
    actuals = y_test.values / target_scaling

    # Metrics
    mse = mean_squared_error(actuals, predictions)
    rmse = math.sqrt(mse)
    mae = mean_absolute_error(actuals, predictions)

    return {
        "model": model,
        "scaler": scaler,
        "rmse": rmse,
        "mae": mae,
        "best_iteration": model.best_iteration,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "predictions": predictions,
        "actuals": actuals,
    }


def test_standard_pairs():
    """Test standard pairs (EURUSD, GBPUSD)"""
    print("\n" + "=" * 70)
    print("TEST: STANDARD PAIRS (EURUSD, GBPUSD)")
    print("=" * 70)

    pairs = ["EURUSD", "GBPUSD"]
    data_dir = "data/"

    # ============ NOTEBOOK APPROACH ============
    print("\n[NOTEBOOK] Running exact notebook preprocessing...")
    notebook_dfs = []
    for pair in pairs:
        raw_df = load_raw_data(data_dir, pair)
        df_features = add_features_standard(raw_df)
        df_labeled = add_labels(df_features, horizon=3, scaling=100)
        notebook_dfs.append(df_labeled)

    notebook_df = pd.concat(notebook_dfs, ignore_index=True)
    notebook_df = prepare_model_df(notebook_df, min_history=60)

    # Split per pair
    feature_cols = get_standard_feature_columns(notebook_df)
    # Remove ts_ms if present (notebook doesn't include it)
    feature_cols = [c for c in feature_cols if c != "ts_ms"]

    train_dfs = []
    test_dfs = []
    for pair in pairs:
        pair_df = (
            notebook_df[notebook_df["pair"] == pair]
            .copy()
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        split_idx = int(len(pair_df) * 0.8)
        train_dfs.append(pair_df.iloc[:split_idx])
        test_dfs.append(pair_df.iloc[split_idx:])

    train_df = pd.concat(train_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)

    print(
        f"[NOTEBOOK] Train: {len(train_df)}, Test: {len(test_df)}, Features: {len(feature_cols)}"
    )

    X_train = train_df[feature_cols]
    y_train = train_df["target"]
    X_test = test_df[feature_cols]
    y_test = test_df["target"]

    notebook_results = train_xgb_model(X_train, y_train, X_test, y_test)
    print(
        f"[NOTEBOOK] RMSE: {notebook_results['rmse']:.6f}, MAE: {notebook_results['mae']:.6f}"
    )
    print(f"[NOTEBOOK] Best iteration: {notebook_results['best_iteration']}")

    # ============ PATHWAY APPROACH ============
    print("\n[PATHWAY] Running Pathway preprocessing...")
    config = PathwayFeatureConfig(min_history=60)
    pathway_df = preprocess_forex_data(data_dir, pairs, config)
    pathway_features = get_feature_columns_from_df(pathway_df)
    # Keep ts_ms for pathway (it's included in get_feature_columns_from_df)

    train_dfs = []
    test_dfs = []
    for pair in pairs:
        pair_df = (
            pathway_df[pathway_df["pair"] == pair]
            .copy()
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        split_idx = int(len(pair_df) * 0.8)
        train_dfs.append(pair_df.iloc[:split_idx])
        test_dfs.append(pair_df.iloc[split_idx:])

    train_df = pd.concat(train_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)

    print(
        f"[PATHWAY] Train: {len(train_df)}, Test: {len(test_df)}, Features: {len(pathway_features)}"
    )

    X_train = train_df[pathway_features]
    y_train = train_df["target"]
    X_test = test_df[pathway_features]
    y_test = test_df["target"]

    pathway_results = train_xgb_model(X_train, y_train, X_test, y_test)
    print(
        f"[PATHWAY] RMSE: {pathway_results['rmse']:.6f}, MAE: {pathway_results['mae']:.6f}"
    )
    print(f"[PATHWAY] Best iteration: {pathway_results['best_iteration']}")

    # ============ COMPARE ============
    print("\n[COMPARISON]")
    print(f"  RMSE diff: {abs(notebook_results['rmse'] - pathway_results['rmse']):.8f}")
    print(f"  MAE diff: {abs(notebook_results['mae'] - pathway_results['mae']):.8f}")

    return notebook_results, pathway_results


def test_usdjpy():
    """Test USDJPY with advanced features"""
    print("\n" + "=" * 70)
    print("TEST: USDJPY (with VIX proxy, fractional differencing)")
    print("=" * 70)

    pairs = ["USDJPY"]
    data_dir = "data/"

    # ============ NOTEBOOK APPROACH ============
    print("\n[NOTEBOOK] Running exact notebook preprocessing...")
    raw_df = load_raw_data(data_dir, "USDJPY")
    df_features = add_features_usdjpy(raw_df)
    df_labeled = add_labels(df_features, horizon=3, scaling=100)
    notebook_df = prepare_model_df(df_labeled, min_history=80)

    feature_cols = get_usdjpy_feature_columns(notebook_df)
    # Remove ts_ms if present
    feature_cols = [c for c in feature_cols if c != "ts_ms"]

    pair_df = notebook_df.copy().sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(pair_df) * 0.8)
    train_df = pair_df.iloc[:split_idx]
    test_df = pair_df.iloc[split_idx:]

    print(
        f"[NOTEBOOK] Train: {len(train_df)}, Test: {len(test_df)}, Features: {len(feature_cols)}"
    )

    if len(train_df) < 10 or len(test_df) < 5:
        print("[NOTEBOOK] WARNING: Not enough data for meaningful training!")
        return None, None

    X_train = train_df[feature_cols]
    y_train = train_df["target"]
    X_test = test_df[feature_cols]
    y_test = test_df["target"]

    notebook_results = train_xgb_model(X_train, y_train, X_test, y_test)
    print(
        f"[NOTEBOOK] RMSE: {notebook_results['rmse']:.6f}, MAE: {notebook_results['mae']:.6f}"
    )
    print(f"[NOTEBOOK] Best iteration: {notebook_results['best_iteration']}")

    # ============ PATHWAY APPROACH ============
    print("\n[PATHWAY] Running Pathway preprocessing...")
    config = PathwayFeatureConfig(
        min_history=80, frac_diff_d=0.4, frac_diff_thresh=1e-5
    )
    pathway_df = preprocess_forex_data(data_dir, pairs, config)
    pathway_features = get_feature_columns_from_df(pathway_df)

    pair_df = pathway_df.copy().sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(pair_df) * 0.8)
    train_df = pair_df.iloc[:split_idx]
    test_df = pair_df.iloc[split_idx:]

    print(
        f"[PATHWAY] Train: {len(train_df)}, Test: {len(test_df)}, Features: {len(pathway_features)}"
    )

    if len(train_df) < 10 or len(test_df) < 5:
        print("[PATHWAY] WARNING: Not enough data for meaningful training!")
        return None, None

    X_train = train_df[pathway_features]
    y_train = train_df["target"]
    X_test = test_df[pathway_features]
    y_test = test_df["target"]

    pathway_results = train_xgb_model(X_train, y_train, X_test, y_test)
    print(
        f"[PATHWAY] RMSE: {pathway_results['rmse']:.6f}, MAE: {pathway_results['mae']:.6f}"
    )
    print(f"[PATHWAY] Best iteration: {pathway_results['best_iteration']}")

    # ============ COMPARE ============
    print("\n[COMPARISON]")
    print(f"  RMSE diff: {abs(notebook_results['rmse'] - pathway_results['rmse']):.8f}")
    print(f"  MAE diff: {abs(notebook_results['mae'] - pathway_results['mae']):.8f}")

    return notebook_results, pathway_results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70)
    print("NOTEBOOK vs PATHWAY MODEL TRAINING COMPARISON")
    print("=" * 70)

    std_nb, std_pw = test_standard_pairs()
    usdjpy_nb, usdjpy_pw = test_usdjpy()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\nStandard Pairs (EURUSD, GBPUSD):")
    if std_nb and std_pw:
        print(f"  Notebook RMSE: {std_nb['rmse']:.6f}")
        print(f"  Pathway RMSE:  {std_pw['rmse']:.6f}")
        print(f"  Difference:    {abs(std_nb['rmse'] - std_pw['rmse']):.8f}")

    print("\nUSDJPY (advanced features):")
    if usdjpy_nb and usdjpy_pw:
        print(f"  Notebook RMSE: {usdjpy_nb['rmse']:.6f}")
        print(f"  Pathway RMSE:  {usdjpy_pw['rmse']:.6f}")
        print(f"  Difference:    {abs(usdjpy_nb['rmse'] - usdjpy_pw['rmse']):.8f}")
    else:
        print("  Insufficient data for comparison")
