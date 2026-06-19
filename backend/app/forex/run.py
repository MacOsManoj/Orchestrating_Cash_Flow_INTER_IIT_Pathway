"""
Run Forex Trading Pipeline with Pathway Preprocessor

This script runs the complete trading pipeline using the Pathway-based
preprocessor instead of the original pandas preprocessor.

All features are backward-looking (no data leakage).
Target labels use future data and are only for training.
"""

import os
import sys
import json
import yaml
import re
from dotenv import load_dotenv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

# Fix path to allow imports from app.forex
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import from the existing pipeline components
# Import from the existing pipeline components
from app.forex.models import ModelConfig, create_model, TrainingResult
from app.forex.position_sizing import (
    PositionSizeConfig,
    PositionSizer,
    calculate_comprehensive_metrics,
)

# Import Pathway preprocessor for streaming-ready preprocessing
from app.forex.preprocessing.pathway_pipeline import (
    PathwayFeatureConfig,
    preprocess_forex_data,
    get_feature_columns_from_df,
)
from app.forex.data_fetcher import DataManager


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file with environment variable substitution"""
    # Load .env file
    load_dotenv()

    with open(config_path, "r") as f:
        content = f.read()

    # Simple regex substitution for ${VAR}
    # Matches ${VAR} or ${VAR:default}
    pattern = re.compile(r"\$\{([^}^{]+)\}")

    def repl(match):
        env_var = match.group(1)
        default = None
        if ":" in env_var:
            env_var, default = env_var.split(":", 1)

        value = os.environ.get(env_var, default)
        if value is None:
            # Leave it as is if not found and no default
            return match.group(0)
        return value

    content = pattern.sub(repl, content)

    return yaml.safe_load(content)


def create_pathway_config(yaml_config: Dict) -> PathwayFeatureConfig:
    """Create PathwayFeatureConfig from YAML config"""
    feat_cfg = yaml_config.get("features", {})
    train_cfg = yaml_config.get("training", {})

    return PathwayFeatureConfig(
        ewma_alpha=feat_cfg.get("ewma_alpha", 0.25),
        sma_fast=feat_cfg.get("sma_fast", 10),
        sma_slow=feat_cfg.get("sma_slow", 50),
        macd_fast=feat_cfg.get("macd_fast", 12),
        macd_slow=feat_cfg.get("macd_slow", 26),
        macd_signal=feat_cfg.get("macd_signal", 9),
        rsi_period=feat_cfg.get("rsi_period", 14),
        atr_period=feat_cfg.get("atr_period", 14),
        lag_returns=feat_cfg.get("lag_returns", 10),
        vol_windows=feat_cfg.get("volatility", {}).get("windows", [10, 20, 60]),
        rolling_skew_window=20,
        rolling_kurt_window=20,
        frac_diff_d=feat_cfg.get("frac_diff", {}).get("d", 0.4),
        frac_diff_thresh=feat_cfg.get("frac_diff", {}).get("threshold", 1e-5),
        horizon=train_cfg.get("horizon", 3),
        target_scaling=train_cfg.get("target_scaling", 100.0),
        min_history=80,
    )


def create_model_config(yaml_config: Dict) -> ModelConfig:
    """Create ModelConfig from YAML config"""
    xgb_cfg = yaml_config.get("xgboost", {})

    return ModelConfig(
        n_estimators=xgb_cfg.get("n_estimators", 200),
        max_depth=xgb_cfg.get("max_depth", 4),
        learning_rate=xgb_cfg.get("learning_rate", 0.05),
        subsample=xgb_cfg.get("subsample", 0.8),
        colsample_bytree=xgb_cfg.get("colsample_bytree", 0.8),
        reg_alpha=xgb_cfg.get("reg_alpha", 0.1),
        reg_lambda=xgb_cfg.get("reg_lambda", 1.0),
        objective=xgb_cfg.get("objective", "reg:squarederror"),
        n_jobs=xgb_cfg.get("n_jobs", -1),
        random_state=xgb_cfg.get("random_state", 42),
        early_stopping_rounds=xgb_cfg.get("early_stopping_rounds", 20),
    )


class TradingSignalGenerator:
    """Generates trading signals from model predictions"""

    def __init__(self, config: Dict):
        self.spread_cost = config.get("spread_cost", 0.0002)
        self.pct_cost = config.get("pct_cost", 0.0001)
        self.slippage = config.get("slippage", 0.0001)
        self.stop_loss = config.get("stop_loss", 0.01)

    def generate_signals(
        self, results_df: pd.DataFrame, include_stop_loss: bool = True
    ) -> pd.DataFrame:
        """Generate trading signals from predictions (matches pipeline.py logic exactly)"""
        tau = (self.spread_cost / 2) + self.pct_cost + self.slippage

        positions = []
        stop_loss_triggered = []
        current_position = 0
        cumulative_pnl = 0.0

        actuals = results_df["actual"].values
        predictions = results_df["predicted"].values

        for i, pred in enumerate(predictions):
            triggered = False

            # Check stop loss
            if include_stop_loss and current_position != 0 and i > 0:
                bar_return = current_position * actuals[i - 1]
                cumulative_pnl += bar_return

                if cumulative_pnl <= -self.stop_loss:
                    current_position = 0
                    cumulative_pnl = 0.0
                    triggered = True

            # Generate signal if not stopped out
            if not triggered:
                new_position = current_position

                if pred > tau:
                    new_position = 1
                elif pred < -tau:
                    new_position = -1

                if new_position != current_position:
                    cumulative_pnl = 0.0
                    current_position = new_position

            positions.append(current_position)
            stop_loss_triggered.append(triggered)

        # Calculate returns
        enriched = results_df.copy()
        enriched["position"] = positions
        enriched["stop_loss_triggered"] = stop_loss_triggered
        enriched["strategy_return"] = enriched["position"] * enriched["actual"]
        enriched["pos_change"] = enriched["position"].diff().abs().fillna(0)
        cost_per_turn = (self.spread_cost / 2) + self.pct_cost + self.slippage
        enriched["costs"] = enriched["pos_change"] * cost_per_turn
        enriched["net_return"] = enriched["strategy_return"] - enriched["costs"]
        enriched["cum_actual"] = (1 + enriched["actual"]).cumprod()
        enriched["cum_strategy"] = (1 + enriched["net_return"]).cumprod()

        return enriched


def run_pipeline_with_pathway(
    train: bool = True, update_data: bool = False, config_path: str = "config.yaml"
):
    """Run the complete pipeline with Pathway preprocessor

    Args:
        train: If True, retrain models. If False, load existing models for inference.
        update_data: If True, fetch new data from Polygon before running pipeline.
        config_path: Path to configuration file
    """

    print("\n" + "=" * 70)
    print("FOREX TRADING PIPELINE WITH PATHWAY PREPROCESSOR")
    print(f"Mode: {'TRAINING' if train else 'INFERENCE (using existing models)'}")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70 + "\n")

    # Load configuration
    logger.info(f"Loading configuration from {config_path}...")
    config = load_config(config_path)

    # Create configurations
    pathway_config = create_pathway_config(config)
    model_config = create_model_config(config)

    # Resolve data directory relative to config file
    config_dir = os.path.dirname(os.path.abspath(config_path))
    data_dir = config.get("data", {}).get("data_dir", "data/")
    if not os.path.isabs(data_dir):
        data_dir = os.path.join(config_dir, data_dir)
    train_ratio = config.get("training", {}).get("train_ratio", 0.8)
    target_scaling = config.get("training", {}).get("target_scaling", 100)

    # Resolve model directory relative to config file
    model_dir = config.get("models", {}).get("model_dir", "trained_models/")
    if not os.path.isabs(model_dir):
        model_dir = os.path.join(config_dir, model_dir)

    log_dir = config.get("logging", {}).get("log_dir", "logs/")

    os.makedirs(model_dir, exist_ok=True)

    # Get active models from config
    active_models = config.get("models", {}).get("active_models", [])

    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Active models: {len(active_models)}")

    # Results storage
    all_results = {}
    all_metrics = {}

    # Update data if requested
    if update_data:
        print("\n" + "=" * 60)
        print("UPDATING DATA")
        print("=" * 60)

        # Get Polygon API key
        polygon_key = config.get("data", {}).get("polygon", {}).get("api_key", "")
        if polygon_key.startswith("${") and polygon_key.endswith("}"):
            env_var = polygon_key[2:-1]
            polygon_key = os.environ.get(env_var, "")

        if not polygon_key:
            logger.warning("No Polygon API key found. Skipping data update.")
        else:
            all_pairs = config.get("data", {}).get("all_pairs", [])
            logger.info(f"Updating data for pairs: {all_pairs}")

            data_manager = DataManager(
                api_key=polygon_key, data_dir=data_dir, pairs=all_pairs
            )

            results = data_manager.update_all_pairs()
            for pair, success in results.items():
                status = "Success" if success else "Failed/No Data"
                logger.info(f"  {pair}: {status}")

    # Process each model configuration
    for model_cfg in active_models:
        model_name = model_cfg["name"]
        model_type = model_cfg["type"]
        pairs = model_cfg["pairs"]

        print("\n" + "=" * 60)
        print(f"PROCESSING MODEL: {model_name}")
        print(f"Type: {model_type}")
        print(f"Pairs: {pairs}")
        print("=" * 60)

        if train:
            # =====================================================
            # STEP 1: Preprocess data with Pathway preprocessor
            # =====================================================
            logger.info(f"[Step 1] Preprocessing data with Pathway preprocessor...")

            df = preprocess_forex_data(data_dir, pairs, pathway_config)
            feature_cols = get_feature_columns_from_df(df)

            logger.info(f"  Preprocessed data shape: {df.shape}")
            logger.info(f"  Number of features: {len(feature_cols)}")
            logger.info(f"  Pairs in data: {df['pair'].unique().tolist()}")

            # =====================================================
            # STEP 2: Create and train model
            # =====================================================
            logger.info(f"[Step 2] Training {model_type} model...")

            model = create_model(model_type, model_config, model_name)

            if model_type == "single_train":
                result = model.train(
                    df=df,
                    feature_cols=feature_cols,
                    target_col="target",
                    train_ratio=train_ratio,
                    target_scaling=target_scaling,
                )
            elif model_type == "walk_forward":
                wf_config = config.get("training", {}).get("walk_forward", {})
                result = model.train(
                    df=df,
                    feature_cols=feature_cols,
                    target_col="target",
                    train_window=wf_config.get("train_window", 444),
                    test_window=wf_config.get("test_window", 111),
                    step_size=wf_config.get("step_size", 111),
                    target_scaling=target_scaling,
                )
            else:
                logger.error(f"Unknown model type: {model_type}")
                continue

            # Save model
            model.save(model_dir)
            logger.info(f"  Model saved to {model_dir}")
        else:
            # =====================================================
            # STEP 1: Load existing model for inference
            # =====================================================
            logger.info(f"[Step 1] Loading existing {model_type} model...")

            model = create_model(model_type, model_config, model_name)
            if not model.load(model_dir):
                logger.error(f"Failed to load model from {model_dir}")
                continue

            logger.info(f"  Model loaded successfully")

            # =====================================================
            # STEP 2: Preprocess data and generate predictions
            # =====================================================
            logger.info(f"[Step 2] Preprocessing data for inference...")

            df = preprocess_forex_data(data_dir, pairs, pathway_config)
            feature_cols = get_feature_columns_from_df(df)

            logger.info(f"  Preprocessed data shape: {df.shape}")
            logger.info(f"  Number of features: {len(feature_cols)}")

            # Split data per pair to get TEST SET ONLY (matching notebook behavior)
            # We only evaluate on the test portion to avoid inflated metrics from training data
            test_dfs = []
            for pair in df["pair"].unique():
                pair_df = (
                    df[df["pair"] == pair]
                    .copy()
                    .sort_values("timestamp")
                    .reset_index(drop=True)
                )
                split_idx = int(len(pair_df) * train_ratio)
                test_dfs.append(pair_df.iloc[split_idx:])

            test_df = pd.concat(test_dfs, ignore_index=True)
            logger.info(
                f"  Test data shape: {test_df.shape} (using last {(1 - train_ratio) * 100:.0f}% per pair)"
            )

            # Generate predictions on TEST data only
            try:
                X = test_df[feature_cols].copy()
                y_pred = model.predict(X, scale_factor=target_scaling)

                # Create results dataframe similar to training
                # Note: target is scaled, so we need to unscale it to match predictions
                results_df = test_df[["timestamp", "pair", "close", "target"]].copy()
                results_df["predicted"] = y_pred
                results_df["actual"] = (
                    test_df["target"].values / target_scaling
                )  # Unscale target

                result = TrainingResult(
                    model=model.model,
                    scaler=model.scaler,
                    feature_cols=feature_cols,
                    metrics={"mode": "inference"},
                    predictions=results_df,
                )
            except Exception as e:
                logger.error(f"Error during inference: {e}")
                continue

        # Store results
        all_results[model_name] = result

        # =====================================================
        # STEP 3: Generate trading signals
        # =====================================================
        logger.info(f"[Step 3] Generating trading signals...")

        trading_config = config.get("trading", {})
        signal_generator = TradingSignalGenerator(trading_config)

        if result.predictions is not None:
            signals = signal_generator.generate_signals(result.predictions)

            # Calculate metrics per pair
            for pair in signals["pair"].unique():
                pair_signals = signals[signals["pair"] == pair]
                metrics = calculate_comprehensive_metrics(
                    pair_signals, f"{model_name}_{pair}"
                )
                all_metrics[f"{model_name}_{pair}"] = metrics

                print(f"\n  {pair} Metrics:")
                print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
                print(f"    Sortino Ratio: {metrics['sortino_ratio']:.4f}")
                print(f"    Win Rate: {metrics['win_rate'] * 100:.1f}%")
                print(f"    Total Return: {metrics['total_profit_pct']:.2f}%")
                print(f"    Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
                print(f"    Calmar Ratio: {metrics['calmar_ratio']:.4f}")

        # Log training metrics
        print(f"\n  Training Metrics:")
        for key, value in result.metrics.items():
            if isinstance(value, float):
                print(f"    {key}: {value:.6f}")
            else:
                print(f"    {key}: {value}")

    # =====================================================
    # SUMMARY
    # =====================================================
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)

    print("\n📊 Models Trained:")
    for model_name, result in all_results.items():
        rmse = result.metrics.get("rmse", "N/A")
        if isinstance(rmse, (int, float)):
            print(f"  - {model_name}: RMSE={rmse:.6f}")
        else:
            print(f"  - {model_name}: RMSE={rmse}")

    print("\n📈 Trading Metrics by Pair:")
    for key, metrics in all_metrics.items():
        print(f"  - {key}:")
        print(f"      Sharpe: {metrics['sharpe_ratio']:.4f}")
        print(f"      Sortino: {metrics['sortino_ratio']:.4f}")
        print(f"      Win Rate: {metrics['win_rate'] * 100:.1f}%")
        print(f"      Return: {metrics['total_profit_pct']:.2f}%")
        print(f"      Max DD: {metrics['max_drawdown_pct']:.2f}%")

    # =====================================================
    # SAVE METRICS TO TRADES.JSON
    # =====================================================
    print("\n💾 Saving metrics to trades.json...")

    # Save to forex directory (same as config.yaml), not data/ subdirectory
    trades_json_path = os.path.join(config_dir, "trades.json")

    # Load existing trades.json or create new
    if os.path.exists(trades_json_path):
        with open(trades_json_path, "r") as f:
            trades_data = json.load(f)
    else:
        trades_data = {}

    # Update with computed metrics for each pair
    for key, metrics in all_metrics.items():
        # Key format: "model_name_PAIR" -> extract pair
        parts = key.rsplit("_", 1)
        if len(parts) == 2:
            pair = parts[1]
        else:
            pair = key

        if pair not in trades_data:
            trades_data[pair] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit_pct": 0.0,
                "recent_trades": [],
            }

        # Update with backtest metrics
        trades_data[pair]["sharpe_ratio"] = metrics.get("sharpe_ratio", 0.0)
        trades_data[pair]["sortino_ratio"] = metrics.get("sortino_ratio", 0.0)
        trades_data[pair]["max_drawdown_pct"] = metrics.get("max_drawdown_pct", 0.0)
        trades_data[pair]["calmar_ratio"] = metrics.get("calmar_ratio", 0.0)
        trades_data[pair]["win_rate"] = metrics.get("win_rate", 0.0)
        trades_data[pair]["total_profit_pct"] = metrics.get("total_profit_pct", 0.0)

    # Save updated trades.json
    with open(trades_json_path, "w") as f:
        json.dump(trades_data, f, indent=2)

    print(f"  ✓ Saved metrics for {len(all_metrics)} pairs to {trades_json_path}")

    print("\n✅ Pipeline completed successfully!")
    print("=" * 70)

    return all_results, all_metrics


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Forex Trading Pipeline with Pathway Preprocessor"
    )
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Retrain models (default: run inference only)",
    )
    parser.add_argument(
        "--update-data",
        action="store_true",
        help="Update historical data from Polygon before running",
    )

    args = parser.parse_args()

    # Change to script directory
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # os.chdir(script_dir)

    # Run pipeline
    # Run pipeline
    results, metrics = run_pipeline_with_pathway(
        train=args.train, update_data=args.update_data, config_path=args.config
    )

    return results, metrics


if __name__ == "__main__":
    main()
