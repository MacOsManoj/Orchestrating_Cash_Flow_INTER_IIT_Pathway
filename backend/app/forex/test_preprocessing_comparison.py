"""
Preprocessing Comparison Test Script

This script compares the preprocessing outputs from:
1. Pathway preprocessor (preprocessing.py)
2. Notebook implementations (notebook_preprocessing.py)

It helps identify any discrepancies that might cause different model results.
"""

import pandas as pd
import numpy as np
import sys
import os

# Add the fx directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing import (
    PathwayFeatureConfig,
    preprocess_forex_data,
    get_feature_columns_from_df,
)
from notebook_preprocessing import (
    StandardFeatureConfig,
    USDJPYFeatureConfig,
    add_features_standard,
    add_features_usdjpy,
    add_labels,
    prepare_model_df,
    get_standard_feature_columns,
    get_usdjpy_feature_columns,
    compare_preprocessing,
    print_comparison_report,
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


def test_standard_preprocessing(data_dir: str, pairs: list):
    """
    Compare standard preprocessing (EURUSD, GBPUSD, etc.)
    """
    print("\n" + "=" * 70)
    print("TEST: STANDARD PREPROCESSING (EURUSD, GBPUSD)")
    print("=" * 70)

    # Pathway preprocessing
    print("\n[1] Running Pathway preprocessor...")
    config = PathwayFeatureConfig(
        ewma_alpha=0.25,
        sma_fast=10,
        sma_slow=50,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        atr_period=14,
        lag_returns=10,
        vol_windows=[10, 20, 60],
        horizon=3,
        target_scaling=100,
        min_history=60,
    )
    pathway_df = preprocess_forex_data(data_dir, pairs, config)
    pathway_features = get_feature_columns_from_df(pathway_df)
    print(f"   Pathway result shape: {pathway_df.shape}")
    print(f"   Pathway feature count: {len(pathway_features)}")

    # Notebook preprocessing
    print("\n[2] Running Notebook preprocessor (xgb_single_train copy 2.ipynb)...")
    notebook_dfs = []
    for pair in pairs:
        raw_df = load_raw_data(data_dir, pair)
        df_features = add_features_standard(raw_df)
        df_labeled = add_labels(df_features, horizon=3, scaling=100)
        notebook_dfs.append(df_labeled)

    notebook_df = pd.concat(notebook_dfs, ignore_index=True)
    notebook_df = prepare_model_df(notebook_df, min_history=60)
    notebook_features = get_standard_feature_columns(notebook_df)
    print(f"   Notebook result shape: {notebook_df.shape}")
    print(f"   Notebook feature count: {len(notebook_features)}")

    # Compare
    print("\n[3] Comparing outputs...")

    # Check feature sets
    pathway_set = set(pathway_features)
    notebook_set = set(notebook_features)

    common_features = pathway_set & notebook_set
    only_pathway = pathway_set - notebook_set
    only_notebook = notebook_set - pathway_set

    print(f"\n   Common features: {len(common_features)}")
    print(f"   Only in Pathway: {len(only_pathway)}")
    if only_pathway:
        print(f"      {sorted(only_pathway)}")
    print(f"   Only in Notebook: {len(only_notebook)}")
    if only_notebook:
        print(f"      {sorted(only_notebook)}")

    # Compare values for common features
    print("\n[4] Comparing feature values...")

    # Align dataframes by timestamp and pair
    pathway_aligned = pathway_df.set_index(["timestamp", "pair"]).sort_index()
    notebook_aligned = notebook_df.set_index(["timestamp", "pair"]).sort_index()

    # Find common indices
    common_idx = pathway_aligned.index.intersection(notebook_aligned.index)
    print(f"   Common data points: {len(common_idx)}")

    if len(common_idx) > 0:
        pathway_aligned = pathway_aligned.loc[common_idx]
        notebook_aligned = notebook_aligned.loc[common_idx]

        mismatches = []
        matches = []

        for col in sorted(common_features):
            if col in pathway_aligned.columns and col in notebook_aligned.columns:
                pw_vals = pathway_aligned[col].values
                nb_vals = notebook_aligned[col].values

                # Handle NaN
                mask = ~(np.isnan(pw_vals) | np.isnan(nb_vals))
                if mask.sum() > 0:
                    pw_valid = pw_vals[mask]
                    nb_valid = nb_vals[mask]

                    if np.allclose(
                        pw_valid, nb_valid, rtol=1e-5, atol=1e-8, equal_nan=True
                    ):
                        matches.append(col)
                    else:
                        max_diff = np.max(np.abs(pw_valid - nb_valid))
                        mean_diff = np.mean(np.abs(pw_valid - nb_valid))
                        rel_diff = np.mean(
                            np.abs(pw_valid - nb_valid) / (np.abs(nb_valid) + 1e-10)
                        )
                        mismatches.append(
                            {
                                "feature": col,
                                "max_diff": max_diff,
                                "mean_diff": mean_diff,
                                "rel_diff": rel_diff,
                                "pw_mean": np.mean(pw_valid),
                                "nb_mean": np.mean(nb_valid),
                                "pw_std": np.std(pw_valid),
                                "nb_std": np.std(nb_valid),
                            }
                        )

        print(f"\n   ✅ Matching features: {len(matches)}")
        print(f"   ❌ Mismatching features: {len(mismatches)}")

        if mismatches:
            print("\n   Mismatch details:")
            for m in sorted(mismatches, key=lambda x: -x["max_diff"])[:10]:
                print(f"      {m['feature']}:")
                print(
                    f"         max_diff={m['max_diff']:.6e}, mean_diff={m['mean_diff']:.6e}, rel_diff={m['rel_diff']:.4f}"
                )
                print(
                    f"         pathway: mean={m['pw_mean']:.6f}, std={m['pw_std']:.6f}"
                )
                print(
                    f"         notebook: mean={m['nb_mean']:.6f}, std={m['nb_std']:.6f}"
                )

    return pathway_df, notebook_df


def test_usdjpy_preprocessing(data_dir: str):
    """
    Compare USDJPY preprocessing.
    """
    print("\n" + "=" * 70)
    print("TEST: USDJPY PREPROCESSING")
    print("=" * 70)

    pairs = ["USDJPY"]

    # Pathway preprocessing
    print("\n[1] Running Pathway preprocessor...")
    config = PathwayFeatureConfig(
        ewma_alpha=0.25,
        sma_fast=10,
        sma_slow=50,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        atr_period=14,
        lag_returns=10,
        vol_windows=[10, 20, 60],
        frac_diff_d=0.4,
        frac_diff_thresh=1e-5,
        horizon=3,
        target_scaling=100,
        min_history=80,  # USDJPY uses 80
    )
    pathway_df = preprocess_forex_data(data_dir, pairs, config)
    pathway_features = get_feature_columns_from_df(pathway_df)
    print(f"   Pathway result shape: {pathway_df.shape}")
    print(f"   Pathway feature count: {len(pathway_features)}")

    # Notebook preprocessing
    print("\n[2] Running Notebook preprocessor (usdjpy.ipynb)...")
    raw_df = load_raw_data(data_dir, "USDJPY")
    df_features = add_features_usdjpy(raw_df)
    df_labeled = add_labels(df_features, horizon=3, scaling=100)
    notebook_df = prepare_model_df(df_labeled, min_history=80)
    notebook_features = get_usdjpy_feature_columns(notebook_df)
    print(f"   Notebook result shape: {notebook_df.shape}")
    print(f"   Notebook feature count: {len(notebook_features)}")

    # Compare
    print("\n[3] Comparing outputs...")

    # Check feature sets
    pathway_set = set(pathway_features)
    notebook_set = set(notebook_features)

    common_features = pathway_set & notebook_set
    only_pathway = pathway_set - notebook_set
    only_notebook = notebook_set - pathway_set

    print(f"\n   Common features: {len(common_features)}")
    print(f"   Only in Pathway: {len(only_pathway)}")
    if only_pathway:
        for f in sorted(only_pathway):
            print(f"      - {f}")
    print(f"   Only in Notebook: {len(only_notebook)}")
    if only_notebook:
        for f in sorted(only_notebook):
            print(f"      - {f}")

    # Compare values for common features
    print("\n[4] Comparing feature values...")

    # Align dataframes by timestamp
    pathway_aligned = pathway_df.set_index("timestamp").sort_index()
    notebook_aligned = notebook_df.set_index("timestamp").sort_index()

    # Find common timestamps
    common_ts = pathway_aligned.index.intersection(notebook_aligned.index)
    print(f"   Common timestamps: {len(common_ts)}")

    if len(common_ts) > 0:
        pathway_aligned = pathway_aligned.loc[common_ts]
        notebook_aligned = notebook_aligned.loc[common_ts]

        mismatches = []
        matches = []

        for col in sorted(common_features):
            if col in pathway_aligned.columns and col in notebook_aligned.columns:
                pw_vals = pathway_aligned[col].values
                nb_vals = notebook_aligned[col].values

                # Handle NaN
                mask = ~(np.isnan(pw_vals) | np.isnan(nb_vals))
                if mask.sum() > 0:
                    pw_valid = pw_vals[mask]
                    nb_valid = nb_vals[mask]

                    if np.allclose(
                        pw_valid, nb_valid, rtol=1e-5, atol=1e-8, equal_nan=True
                    ):
                        matches.append(col)
                    else:
                        max_diff = np.max(np.abs(pw_valid - nb_valid))
                        mean_diff = np.mean(np.abs(pw_valid - nb_valid))
                        rel_diff = np.mean(
                            np.abs(pw_valid - nb_valid) / (np.abs(nb_valid) + 1e-10)
                        )
                        mismatches.append(
                            {
                                "feature": col,
                                "max_diff": max_diff,
                                "mean_diff": mean_diff,
                                "rel_diff": rel_diff,
                                "pw_mean": np.mean(pw_valid),
                                "nb_mean": np.mean(nb_valid),
                                "pw_std": np.std(pw_valid),
                                "nb_std": np.std(nb_valid),
                            }
                        )

        print(f"\n   ✅ Matching features: {len(matches)}")
        print(f"   ❌ Mismatching features: {len(mismatches)}")

        if mismatches:
            print("\n   Mismatch details (top 15 by max_diff):")
            for m in sorted(mismatches, key=lambda x: -x["max_diff"])[:15]:
                print(f"      {m['feature']}:")
                print(
                    f"         max_diff={m['max_diff']:.6e}, mean_diff={m['mean_diff']:.6e}, rel_diff={m['rel_diff']:.4f}"
                )
                print(
                    f"         pathway: mean={m['pw_mean']:.6f}, std={m['pw_std']:.6f}"
                )
                print(
                    f"         notebook: mean={m['nb_mean']:.6f}, std={m['nb_std']:.6f}"
                )

    return pathway_df, notebook_df


def test_single_feature(feature_name: str, data_dir: str, pair: str):
    """
    Deep dive into a single feature comparison.
    """
    print(f"\n" + "=" * 70)
    print(f"DEEP DIVE: {feature_name} for {pair}")
    print("=" * 70)

    # Load and preprocess with both methods
    raw_df = load_raw_data(data_dir, pair)

    # Pathway
    config = PathwayFeatureConfig(min_history=60 if pair != "USDJPY" else 80)
    pathway_df = preprocess_forex_data(data_dir, [pair], config)

    # Notebook
    if pair == "USDJPY":
        notebook_df = add_features_usdjpy(raw_df)
    else:
        notebook_df = add_features_standard(raw_df)
    notebook_df = add_labels(notebook_df, horizon=3, scaling=100)
    notebook_df = prepare_model_df(
        notebook_df, min_history=60 if pair != "USDJPY" else 80
    )

    # Compare the specific feature
    if feature_name in pathway_df.columns and feature_name in notebook_df.columns:
        print(f"\nPathway {feature_name} stats:")
        print(pathway_df[feature_name].describe())

        print(f"\nNotebook {feature_name} stats:")
        print(notebook_df[feature_name].describe())

        # Sample values
        print(f"\nFirst 10 values comparison:")
        print(f"{'Index':<8} {'Pathway':<15} {'Notebook':<15} {'Diff':<15}")
        print("-" * 53)
        for i in range(min(10, len(pathway_df), len(notebook_df))):
            pw_val = pathway_df[feature_name].iloc[i]
            nb_val = notebook_df[feature_name].iloc[i]
            diff = (
                pw_val - nb_val
                if not (np.isnan(pw_val) or np.isnan(nb_val))
                else np.nan
            )
            print(f"{i:<8} {pw_val:<15.6f} {nb_val:<15.6f} {diff:<15.6e}")
    else:
        print(f"Feature {feature_name} not found in one or both dataframes")
        print(f"  In Pathway: {feature_name in pathway_df.columns}")
        print(f"  In Notebook: {feature_name in notebook_df.columns}")


def main():
    """Run all comparison tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare Pathway vs Notebook preprocessing"
    )
    parser.add_argument("--data-dir", default="data/", help="Data directory")
    parser.add_argument(
        "--test", choices=["standard", "usdjpy", "all", "feature"], default="all"
    )
    parser.add_argument("--feature", help="Feature name for deep dive test")
    parser.add_argument("--pair", help="Pair for feature deep dive")

    args = parser.parse_args()

    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if args.test == "feature":
        if not args.feature or not args.pair:
            print("Error: --feature and --pair required for feature test")
            return
        test_single_feature(args.feature, args.data_dir, args.pair)
    elif args.test == "standard":
        test_standard_preprocessing(args.data_dir, ["EURUSD", "GBPUSD"])
    elif args.test == "usdjpy":
        test_usdjpy_preprocessing(args.data_dir)
    else:  # all
        test_standard_preprocessing(args.data_dir, ["EURUSD", "GBPUSD"])
        test_usdjpy_preprocessing(args.data_dir)

    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
