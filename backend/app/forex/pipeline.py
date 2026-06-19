"""
Forex Trading Pipeline
Main orchestration module that ties together all components.
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from .models import (
    ModelConfig,
    XGBSingleTrainModel,
    XGBWalkForwardModel,
    create_model,
    TrainingResult,
)
from .preprocessing import (
    FeatureConfig,
    DataPreprocessor,
    preprocess_forex_data,
    get_feature_columns_from_df,
)
from .position_sizing import (
    PositionSizeConfig,
    PositionSizer,
    calculate_comprehensive_metrics,
    RF_RATE_DAILY,
)
from .position_sizing import (
    PositionSizeConfig,
    PositionSizer,
    calculate_comprehensive_metrics,
    RF_RATE_DAILY,
)
from .data_fetcher import DataManager, PolygonForexFetcher
from .utils import save_positions, save_trades, load_positions, load_trades


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Complete pipeline configuration loaded from config.yaml"""

    # Model configurations
    active_models: List[Dict]
    model_dir: str
    save_models: bool
    load_existing: bool

    # Feature configurations
    feature_config: FeatureConfig

    # Training configurations
    training_config: Dict

    # XGBoost configurations
    xgboost_config: ModelConfig

    # Trading configurations
    trading_config: Dict
    position_size_config: PositionSizeConfig

    # Data configurations
    data_dir: str
    polygon_api_key: Optional[str]
    all_pairs: List[str]

    # Output configurations
    positions_file: str
    trades_file: str
    signals_file: str

    @classmethod
    def from_yaml(cls, config_path: str) -> "PipelineConfig":
        """Load configuration from YAML file"""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Parse feature config
        feat_cfg = config.get("features", {})
        feature_config = FeatureConfig(
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
            frac_diff_d=feat_cfg.get("frac_diff", {}).get("d", 0.4),
            frac_diff_thresh=feat_cfg.get("frac_diff", {}).get("threshold", 1e-5),
            horizon=config.get("training", {}).get("horizon", 3),
            target_scaling=config.get("training", {}).get("target_scaling", 100),
        )

        # Parse XGBoost config
        xgb_cfg = config.get("xgboost", {})
        xgboost_config = ModelConfig(
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

        # Parse position sizing config
        pos_cfg = config.get("trading", {}).get("position_sizing", {})
        position_size_config = PositionSizeConfig(
            method=pos_cfg.get("method", "kelly"),
            kelly_fraction=pos_cfg.get("kelly_fraction", 0.25),
            max_position_pct=pos_cfg.get("max_position_pct", 0.10),
            min_position_pct=pos_cfg.get("min_position_pct", 0.01),
            portfolio_capital=pos_cfg.get("portfolio_capital", 100000),
            sharpe_scaling=pos_cfg.get("sharpe_scaling", 0.05),
        )

        # Get Polygon API key from environment or config
        polygon_key = config.get("data", {}).get("polygon", {}).get("api_key", "")
        if polygon_key.startswith("${") and polygon_key.endswith("}"):
            env_var = polygon_key[2:-1]
            polygon_key = os.environ.get(env_var, '')
            
        # Resolve data_dir relative to config file
        base_dir = os.path.dirname(os.path.abspath(config_path))
        raw_data_dir = config.get('data', {}).get('data_dir', 'data/')
        if not os.path.isabs(raw_data_dir):
            data_dir = os.path.join(base_dir, raw_data_dir)
        else:
            data_dir = raw_data_dir
        
        return cls(
            active_models=config.get("models", {}).get("active_models", []),
            model_dir=config.get("models", {}).get("model_dir", "trained_models/"),
            save_models=config.get("models", {}).get("save_models", True),
            load_existing=config.get("models", {}).get("load_existing", True),
            feature_config=feature_config,
            training_config=config.get("training", {}),
            xgboost_config=xgboost_config,
            trading_config=config.get("trading", {}),
            position_size_config=position_size_config,
            data_dir=data_dir,
            polygon_api_key=polygon_key if polygon_key else None,
            all_pairs=config.get("data", {}).get("all_pairs", []),
            positions_file=config.get("output", {}).get(
                "positions_file", "positions.json"
            ),
            trades_file=config.get("output", {}).get("trades_file", "trades.json"),
            signals_file=config.get("output", {}).get("signals_file", "signals.json"),
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
        """
        Generate trading signals from predictions.

        Args:
            results_df: DataFrame with 'predicted' and 'actual' columns
            include_stop_loss: Whether to include stop loss logic

        Returns:
            DataFrame with signals and returns
        """
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

    def get_current_signal(self, prediction: float) -> Tuple[int, str, float]:
        """
        Get current trading signal from prediction.

        Args:
            prediction: Model prediction (log return)

        Returns:
            Tuple of (position, direction_str, signal_strength)
        """
        tau = (self.spread_cost / 2) + self.pct_cost + self.slippage

        if prediction > tau:
            return 1, "long", abs(prediction) / tau
        elif prediction < -tau:
            return -1, "short", abs(prediction) / tau
        else:
            return 0, "flat", 0.0


class ForexTradingPipeline:
    """Main trading pipeline that orchestrates all components"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize pipeline from config file.

        Args:
            config_path: Path to config.yaml
        """
        self.config_path = config_path
        self.config = PipelineConfig.from_yaml(config_path)

        # Initialize components
        self.preprocessor = DataPreprocessor(self.config.feature_config)
        self.signal_generator = TradingSignalGenerator(self.config.trading_config)
        self.position_sizer = PositionSizer(self.config.position_size_config)

        # Initialize data manager
        self.data_manager = DataManager(
            api_key=self.config.polygon_api_key,
            data_dir=self.config.data_dir,
            pairs=self.config.all_pairs,
        )

        # Storage for trained models and results
        self.models: Dict[str, Any] = {}
        self.training_results: Dict[str, TrainingResult] = {}
        self.current_signals: Dict[str, Dict] = {}

        # Load persisted signals
        loaded_signals = self._load_json(self.config.signals_file)
        if loaded_signals:
            self.current_signals = loaded_signals

        self.positions: Dict[str, Dict] = {}
        self.trades: Dict[str, Dict] = {}

        # Cache for processed data
        self._cached_processed_data: Optional[pd.DataFrame] = None

        logger.info(
            f"Pipeline initialized with {len(self.config.active_models)} active models"
        )

    def _get_processed_data(self, pairs: List[str]) -> pd.DataFrame:
        """
        Helper method to get processed data using Pandas-based preprocessor.
        Replaces Pathway implementation for significantly faster batch processing.
        """
        # Return cached data if available and contains all requested pairs
        if self._cached_processed_data is not None:
            cached_pairs = self._cached_processed_data["pair"].unique()
            if all(p in cached_pairs for p in pairs):
                return self._cached_processed_data[
                    self._cached_processed_data["pair"].isin(pairs)
                ].copy()

        # If cache miss or partial data, process all fully
        all_pairs = self.config.all_pairs

        logger.info(
            f"Starting generic (Pandas) preprocessing for all pairs: {all_pairs}"
        )

        # Use Pandas-based preprocessor (same as run.py)
        # passing config.feature_config which contains horizon/scaling for targets
        df = preprocess_forex_data(
            data_dir=self.config.data_dir,
            pairs=all_pairs,
            config=self.config.feature_config,
        )

        # Update cache
        self._cached_processed_data = df

        logger.info(f"Preprocessing complete. Shape: {df.shape}")

        # Return only requested pairs
        result = df[df["pair"].isin(pairs)].copy()
        # Drop columns that are all NaN for the requested pairs
        # This handles cases where some pairs lack features (e.g. VIX for EURUSD)
        return result.dropna(axis=1, how="all")

    def train_all_models(
        self, force_retrain: bool = False
    ) -> Dict[str, TrainingResult]:
        """
        Train all configured models.

        Args:
            force_retrain: Force retraining even if saved models exist

        Returns:
            Dict of training results
        """
        os.makedirs(self.config.model_dir, exist_ok=True)

        results = {}

        for model_cfg in self.config.active_models:
            model_name = model_cfg["name"]
            model_type = model_cfg["type"]
            pairs = model_cfg["pairs"]

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing model: {model_name}")
            logger.info(f"Type: {model_type}, Pairs: {pairs}")
            logger.info(f"{'=' * 60}")

            # Create model instance
            model = create_model(model_type, self.config.xgboost_config, model_name)

            # Try to load existing model if configured
            if self.config.load_existing and not force_retrain:
                if model.load(self.config.model_dir):
                    logger.info(f"Loaded existing model: {model_name}")
                    self.models[model_name] = model

                    # Still need to generate predictions on data for signals
                    df_model = self._get_processed_data(pairs)
                    from .preprocessing import get_feature_columns_from_df

                    feature_cols = get_feature_columns_from_df(df_model)

                    # Generate predictions using loaded model
                    predictions_list = []
                    for pair in df_model["pair"].unique():
                        pair_df = (
                            df_model[df_model["pair"] == pair]
                            .copy()
                            .sort_values("timestamp")
                            .reset_index(drop=True)
                        )
                        # Use last 20% of data for signals (similar to test set)
                        split_idx = int(len(pair_df) * 0.8)
                        test_df = pair_df.iloc[split_idx:]

                        if len(test_df) > 0:
                            X_test = test_df[feature_cols]
                            predictions = model.predict(
                                X_test,
                                scale_factor=self.config.feature_config.target_scaling,
                            )
                            actuals = (
                                test_df["target"].values
                                / self.config.feature_config.target_scaling
                            )

                            pred_df = pd.DataFrame(
                                {
                                    "timestamp": test_df["timestamp"].values,
                                    "pair": pair,
                                    "actual": actuals,
                                    "predicted": predictions,
                                }
                            )
                            predictions_list.append(pred_df)

                    if predictions_list:
                        all_predictions = pd.concat(predictions_list, ignore_index=True)

                        # Create a TrainingResult for signal generation
                        from sklearn.metrics import (
                            mean_squared_error,
                            mean_absolute_error,
                        )

                        mse = mean_squared_error(
                            all_predictions["actual"], all_predictions["predicted"]
                        )
                        rmse = np.sqrt(mse)
                        mae = mean_absolute_error(
                            all_predictions["actual"], all_predictions["predicted"]
                        )

                        result = TrainingResult(
                            model=model.model,
                            scaler=model.scaler,
                            feature_cols=feature_cols,
                            metrics={
                                "mse": mse,
                                "rmse": rmse,
                                "mae": mae,
                                "test_samples": len(all_predictions),
                            },
                            predictions=all_predictions,
                            feature_importance=None,
                        )
                        self.training_results[model_name] = result
                        results[model_name] = result
                        logger.info(
                            f"Generated predictions for loaded model: {model_name} (RMSE: {rmse:.6f})"
                        )

                    continue

            # Load and preprocess data
            logger.info(f"Preprocessing data for {model_name} using Pathway...")

            df_model = self._get_processed_data(pairs)

            from .preprocessing import get_feature_columns_from_df

            feature_cols = get_feature_columns_from_df(df_model)

        logger.info(f"Data shape: {df_model.shape}")
        logger.info(f"Number of features: {len(feature_cols)}")

        # Train based on model type
        if model_type == "single_train":
            result = model.train(
                df=df_model,
                feature_cols=feature_cols,
                target_col="target",
                train_ratio=self.config.training_config.get("train_ratio", 0.8),
                target_scaling=self.config.feature_config.target_scaling,
            )
        elif model_type == "walk_forward":
            wf_config = self.config.training_config.get("walk_forward", {})
            result = model.train(
                df=df_model,
                feature_cols=feature_cols,
                target_col="target",
                train_window=wf_config.get("train_window", 444),
                test_window=wf_config.get("test_window", 111),
                step_size=wf_config.get("step_size", 111),
                target_scaling=self.config.feature_config.target_scaling,
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Store model and results
        self.models[model_name] = model
        self.training_results[model_name] = result
        results[model_name] = result

        # Save model if configured
        if self.config.save_models:
            model.save(self.config.model_dir)

        # Log metrics
        logger.info(f"\nModel {model_name} Metrics:")
        for key, value in result.metrics.items():
            logger.info(f"  {key}: {value}")

        return results

    def generate_trading_signals(self) -> Dict[str, pd.DataFrame]:
        """
        Generate trading signals for all models.

        Returns:
            Dict of signals DataFrames
        """
        all_signals = {}

        for model_name, result in self.training_results.items():
            if result.predictions is not None:
                signals = self.signal_generator.generate_signals(result.predictions)
                all_signals[model_name] = signals

                # Store current signals per pair
                for pair in signals["pair"].unique():
                    pair_signals = signals[signals["pair"] == pair].sort_values(
                        "timestamp"
                    )
                    latest = pair_signals.iloc[-1]

                    self.current_signals[pair] = {
                        "model": model_name,
                        "position": int(latest["position"]),
                        "direction": "long"
                        if latest["position"] == 1
                        else ("short" if latest["position"] == -1 else "flat"),
                        "predicted_return": float(latest["predicted"]),
                        "signal_strength": abs(latest["predicted"]) * 100,
                        "timestamp": str(latest["timestamp"]),
                    }

        return all_signals

    def calculate_position_sizes(self) -> Dict[str, Dict]:
        """
        Calculate position sizes using Sharpe-proportional allocation.

        Formula: Fraction(A) = Sharpe(A) / Sum(all Sharpes)

        Returns:
            Dict of position sizes per pair
        """
        allocations = {}
        pair_sharpes = {}

        # Step 1: Calculate Sharpe ratio for each pair
        for pair, signal_info in self.current_signals.items():
            model_name = signal_info["model"]
            sharpe_ratio = 0.0

            if model_name in self.training_results:
                result = self.training_results[model_name]
                if result.predictions is not None:
                    pair_predictions = result.predictions[
                        result.predictions["pair"] == pair
                    ]
                    if len(pair_predictions) > 0:
                        signals = self.signal_generator.generate_signals(
                            pair_predictions
                        )
                        returns = signals["net_return"]

                        if len(returns) > 1 and returns.std() > 0:
                            # Annualized Sharpe ratio (using risk-free rate)
                            sharpe_ratio = (
                                (returns.mean() - RF_RATE_DAILY) / returns.std()
                            ) * np.sqrt(252)

            # Only use positive Sharpe ratios for allocation
            pair_sharpes[pair] = max(sharpe_ratio, 0.0)

        # Step 2: Calculate sum of all Sharpe ratios
        total_sharpe = sum(pair_sharpes.values())

        # Step 3: Allocate proportionally by Sharpe
        portfolio_capital = self.config.position_size_config.portfolio_capital

        for pair, signal_info in self.current_signals.items():
            sharpe = pair_sharpes[pair]

            # Fraction = Sharpe(A) / Sum(all Sharpes)
            if total_sharpe > 0:
                position_pct = sharpe / total_sharpe
            else:
                position_pct = 0.0

            position_value = position_pct * portfolio_capital

            allocations[pair] = {
                **signal_info,
                "position_pct": position_pct,
                "position_value": position_value,
                "sharpe_ratio": sharpe,
                "total_sharpe": total_sharpe,
            }

        return allocations

    def update_positions_and_trades(self, allocations: Dict[str, Dict]):
        """
        Update positions.json and trades.json files.

        Args:
            allocations: Position allocations from calculate_position_sizes
        """
        current_time = datetime.now()

        # Load existing positions and trades
        existing_positions = load_positions() or {}
        existing_trades = load_trades() or {}

        # Get current prices
        prices = self.data_manager.get_latest_prices()

        portfolio_summary = {
            "total_open_positions": 0,
            "total_exposure_long": 0,
            "total_exposure_short": 0,
            "net_exposure": 0,
            "total_unrealized_pnl_pct": 0.0,
            "portfolio_heat": 0.0,
            "max_correlation_risk": "N/A",
            "last_updated": current_time.isoformat(),
        }

        for pair, allocation in allocations.items():
            current_price = prices.get(pair, 0.0)
            position_value = allocation["position_value"]
            direction = allocation["direction"]

            # Update position
            if direction == "flat":
                # Check if we had a position before
                prev_position = existing_positions.get(pair, {})
                if prev_position.get("current_position") not in ["flat", None]:
                    # Position was closed, record trade
                    self._record_trade(
                        existing_trades,
                        pair,
                        prev_position,
                        current_price,
                        current_time,
                    )

                self.positions[pair] = {
                    "current_position": "flat",
                    "last_exit_date": current_time.strftime("%Y-%m-%d"),
                    "last_exit_price": current_price,
                    "last_trade_pnl_pct": 0.0,
                    "days_since_last_trade": 0,
                    "pending_signal": f"potential_{allocation.get('kelly_info', {}).get('direction', 'none')}",
                    "signal_strength": "weak"
                    if allocation["signal_strength"] < 30
                    else (
                        "moderate" if allocation["signal_strength"] < 60 else "strong"
                    ),
                    "reason": "Waiting for stronger signal confirmation",
                }
            else:
                # Active position
                entry_price = (
                    current_price  # Simplified - in production, track actual entry
                )
                if (
                    pair in existing_positions
                    and existing_positions[pair].get("current_position") == direction
                ):
                    # Existing position, keep entry price
                    entry_price = existing_positions[pair].get(
                        "entry_price", current_price
                    )
                    entry_date = existing_positions[pair].get(
                        "entry_date", current_time.strftime("%Y-%m-%d")
                    )
                    days_held = (
                        current_time - datetime.strptime(entry_date, "%Y-%m-%d")
                    ).days
                else:
                    entry_date = current_time.strftime("%Y-%m-%d")
                    days_held = 0

                # Calculate unrealized P&L
                if entry_price > 0:
                    if direction == "long":
                        unrealized_pnl = (
                            (current_price - entry_price) / entry_price * 100
                        )
                    else:
                        unrealized_pnl = (
                            (entry_price - current_price) / entry_price * 100
                        )
                else:
                    unrealized_pnl = 0.0

                # Calculate stop loss and take profit
                stop_loss_pct = self.config.trading_config.get("stop_loss", 0.01)
                if direction == "long":
                    stop_loss = entry_price * (1 - stop_loss_pct)
                    take_profit = entry_price * (1 + stop_loss_pct * 2)
                else:
                    stop_loss = entry_price * (1 + stop_loss_pct)
                    take_profit = entry_price * (1 - stop_loss_pct * 2)

                # Calculate model confidence as float
                signal_str = float(allocation.get("signal_strength", 0))
                model_conf = float(round(signal_str / 100, 4))

                self.positions[pair] = {
                    "current_position": direction,
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 5),
                    "current_price": round(current_price, 5),
                    "unrealized_pnl_pct": round(unrealized_pnl, 2),
                    "position_size": int(position_value),
                    "stop_loss": round(stop_loss, 5),
                    "take_profit": round(take_profit, 5),
                    "risk_reward_ratio": 2.0,
                    "days_held": days_held,
                    "model_confidence": model_conf,
                    "signal_strength": "weak"
                    if signal_str < 30
                    else ("moderate" if signal_str < 60 else "strong"),
                    "entry_reason": f"Model prediction: {allocation.get('predicted_return', 0):.6f}",
                }

                # Update portfolio summary
                portfolio_summary["total_open_positions"] += 1
                if direction == "long":
                    portfolio_summary["total_exposure_long"] += position_value
                else:
                    portfolio_summary["total_exposure_short"] += position_value
                portfolio_summary["total_unrealized_pnl_pct"] += unrealized_pnl

        # Finalize portfolio summary
        portfolio_summary["net_exposure"] = (
            portfolio_summary["total_exposure_long"]
            - portfolio_summary["total_exposure_short"]
        )
        total_exposure = (
            portfolio_summary["total_exposure_long"]
            + portfolio_summary["total_exposure_short"]
        )
        portfolio_summary["portfolio_heat"] = round(
            total_exposure / self.config.position_size_config.portfolio_capital, 2
        )

        self.positions["portfolio_summary"] = portfolio_summary
        self.trades = existing_trades

        # Save files (Dual-write to Mongo and JSON via utils)
        save_positions(self.positions)
        save_trades(self.trades)

        logger.info(f"Updated positions and trades files")

    def _record_trade(
        self,
        trades: Dict,
        pair: str,
        prev_position: Dict,
        exit_price: float,
        exit_time: datetime,
    ):
        """Record a completed trade"""
        if pair not in trades:
            trades[pair] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "information_ratio": 0.0,
                "turnover_ratio": 0.0,
                "avg_win_pct": 0.0,
                "avg_loss_pct": 0.0,
                "profit_factor": 0.0,
                "avg_holding_period_days": 0.0,
                "largest_win_pct": 0.0,
                "largest_loss_pct": 0.0,
                "consecutive_wins_max": 0,
                "consecutive_losses_max": 0,
                "recent_trades": [],
            }

        entry_price = prev_position.get("entry_price", exit_price)
        direction = prev_position.get("current_position", "long")

        if direction == "long":
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        trade_record = {
            "date": exit_time.strftime("%Y-%m-%d"),
            "side": direction,
            "entry": round(entry_price, 5),
            "exit": round(exit_price, 5),
            "pnl_pct": round(pnl_pct, 2),
        }

        # Update statistics
        trades[pair]["total_trades"] += 1
        if pnl_pct > 0:
            trades[pair]["winning_trades"] += 1
        else:
            trades[pair]["losing_trades"] += 1

        trades[pair]["total_profit_pct"] += pnl_pct
        trades[pair]["win_rate"] = (
            trades[pair]["winning_trades"] / trades[pair]["total_trades"]
        )

        # Add to recent trades
        trades[pair]["recent_trades"].insert(0, trade_record)
        trades[pair]["recent_trades"] = trades[pair]["recent_trades"][
            :10
        ]  # Keep last 10

    def _load_json(self, filename: str) -> Optional[Dict]:
        """Load JSON file"""
        filepath = os.path.join(os.path.dirname(self.config_path), filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
        return None

    def _save_json(self, data: Dict, filename: str):
        """Save JSON file"""
        filepath = os.path.join(os.path.dirname(self.config_path), filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def run_full_pipeline(self, force_retrain: bool = False, train: bool = False) -> Dict[str, Any]:
        """
        Run the complete trading pipeline.

        Args:
            force_retrain: Force model retraining
            train: Alias for force_retrain (used by API)
        
        Returns:
            Dict with pipeline results
        """
        logger.info("\n" + "=" * 60)
        logger.info("FOREX TRADING PIPELINE")
        logger.info("=" * 60)

        # Step 1: Train models
        logger.info("\n[Step 1/4] Training models...")
        training_results = self.train_all_models(force_retrain or train)
        
        # Step 2: Generate signals
        logger.info("\n[Step 2/4] Generating trading signals...")
        logger.info("\n[Step 2/4] Generating trading signals...")
        signals = self.generate_trading_signals()

        # Save signals
        self._save_json(self.current_signals, self.config.signals_file)
        logger.info(f"Saved signals to {self.config.signals_file}")

        # Step 3: Calculate position sizes (Kelly Criterion)
        logger.info("\n[Step 3/4] Calculating position sizes (Kelly Criterion)...")
        allocations = self.calculate_position_sizes()

        # Step 4: Update positions and trades
        logger.info("\n[Step 4/4] Updating positions and trades...")
        self.update_positions_and_trades(allocations)

        # Calculate comprehensive metrics for each model
        metrics = {}
        for model_name, signals_df in signals.items():
            for pair in signals_df["pair"].unique():
                pair_signals = signals_df[signals_df["pair"] == pair]
                pair_metrics = calculate_comprehensive_metrics(
                    pair_signals, f"{model_name}_{pair}"
                )
                metrics[f"{model_name}_{pair}"] = pair_metrics

        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)

        return {
            "training_results": {k: v.metrics for k, v in training_results.items()},
            "current_signals": self.current_signals,
            "allocations": allocations,
            "positions": self.positions,
            "metrics": metrics,
        }

    def update_data_and_run(
        self, days_back: int = 30, force_retrain: bool = False
    ) -> Dict[str, Any]:
        """
        Update data from Polygon.io and run pipeline.

        Args:
            days_back: Number of days of data to fetch
            force_retrain: Force model retraining

        Returns:
            Pipeline results
        """
        if self.config.polygon_api_key:
            logger.info("Updating data from Polygon.io...")
            update_results = self.data_manager.update_all_pairs(days_back)
            logger.info(f"Data update results: {update_results}")
        else:
            logger.warning("No Polygon API key configured, using existing data")

        return self.run_full_pipeline(force_retrain)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Forex Trading Pipeline")
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to config file"
    )
    parser.add_argument("--retrain", action="store_true", help="Force model retraining")
    parser.add_argument(
        "--update-data", action="store_true", help="Update data from Polygon.io"
    )
    parser.add_argument(
        "--days-back", type=int, default=30, help="Days of data to fetch"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = ForexTradingPipeline(args.config)

    # Run pipeline
    if args.update_data:
        results = pipeline.update_data_and_run(args.days_back)
    else:
        results = pipeline.run_full_pipeline(args.retrain)

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS SUMMARY")
    print("=" * 60)

    print("\nCurrent Signals:")
    for pair, signal in results["current_signals"].items():
        print(
            f"  {pair}: {signal['direction']} (strength: {signal['signal_strength']:.1f}%)"
        )

    print("\nPosition Allocations:")
    for pair, alloc in results["allocations"].items():
        print(
            f"  {pair}: {alloc['position_pct'] * 100:.2f}% (${alloc['position_value']:,.0f})"
        )

    print("\nModel Metrics:")
    for name, metrics in results["metrics"].items():
        print(f"\n  {name}:")
        print(f"    Sharpe: {metrics['sharpe_ratio']:.3f}")
        print(f"    Win Rate: {metrics['win_rate'] * 100:.1f}%")
        print(f"    Total Profit: {metrics['total_profit_pct']:.2f}%")


if __name__ == "__main__":
    main()
