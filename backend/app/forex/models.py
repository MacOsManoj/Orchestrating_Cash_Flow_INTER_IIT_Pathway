"""
XGBoost Trading Models
Implements Single Train and Walk-Forward validation models for forex trading.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for XGBoost models"""

    n_estimators: int = 200
    max_depth: int = 4
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    objective: str = "reg:squarederror"
    n_jobs: int = -1
    random_state: int = 42
    early_stopping_rounds: int = 20


@dataclass
class TrainingResult:
    """Results from model training"""

    model: Any
    scaler: StandardScaler
    feature_cols: List[str]
    metrics: Dict[str, float]
    predictions: Optional[pd.DataFrame] = None
    feature_importance: Optional[pd.DataFrame] = None


class BaseForexModel:
    """Base class for forex trading models"""

    def __init__(self, config: ModelConfig, model_name: str = "base"):
        self.config = config
        self.model_name = model_name
        self.model = None
        self.scaler = None
        self.feature_cols = None
        self.is_trained = False

    def get_xgb_params(self) -> Dict:
        """Get XGBoost parameters from config"""
        return {
            "n_estimators": self.config.n_estimators,
            "max_depth": self.config.max_depth,
            "learning_rate": self.config.learning_rate,
            "subsample": self.config.subsample,
            "colsample_bytree": self.config.colsample_bytree,
            "reg_alpha": self.config.reg_alpha,
            "reg_lambda": self.config.reg_lambda,
            "objective": self.config.objective,
            "n_jobs": self.config.n_jobs,
            "random_state": self.config.random_state,
            "early_stopping_rounds": self.config.early_stopping_rounds,
        }

    def save(self, model_dir: str) -> str:
        """Save model to disk"""
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, f"{self.model_name}.pkl")

        save_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "config": self.config,
            "is_trained": self.is_trained,
        }

        with open(model_path, "wb") as f:
            pickle.dump(save_data, f)

        logger.info(f"Model saved to {model_path}")
        return model_path

    def load(self, model_dir: str) -> bool:
        """Load model from disk"""
        model_path = os.path.join(model_dir, f"{self.model_name}.pkl")

        if not os.path.exists(model_path):
            logger.warning(f"Model file not found: {model_path}")
            return False

        try:
            with open(model_path, "rb") as f:
                save_data = pickle.load(f)

            self.model = save_data["model"]
            self.scaler = save_data["scaler"]
            self.feature_cols = save_data["feature_cols"]
            self.config = save_data["config"]
            self.is_trained = save_data["is_trained"]

            logger.info(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def predict(self, X: pd.DataFrame, scale_factor: float = 100) -> np.ndarray:
        """Generate predictions"""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        X_features = X[self.feature_cols] if isinstance(X, pd.DataFrame) else X
        X_scaled = self.scaler.transform(X_features)
        predictions_scaled = self.model.predict(X_scaled)

        return predictions_scaled / scale_factor


class XGBSingleTrainModel(BaseForexModel):
    """
    XGBoost Single Train Model
    Trains once on training data, predicts on test data without retraining.
    Used for: EUR,GBP,JPY/INR | USDJPY | EUR,GBP/USD
    """

    def __init__(self, config: ModelConfig, model_name: str = "single_train"):
        super().__init__(config, model_name)
        self.training_stats = {}

    def train(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = "target",
        train_ratio: float = 0.8,
        target_scaling: float = 100,
    ) -> TrainingResult:
        """
        Train the model using single train/test split.

        Args:
            df: DataFrame with features and target
            feature_cols: List of feature column names
            target_col: Target column name
            train_ratio: Ratio of data for training
            target_scaling: Scaling factor for target

        Returns:
            TrainingResult with model and metrics
        """
        self.feature_cols = feature_cols

        # Split data per pair to avoid data leakage
        train_dfs = []
        test_dfs = []

        for pair in df["pair"].unique():
            pair_df = (
                df[df["pair"] == pair]
                .copy()
                .sort_values("timestamp")
                .reset_index(drop=True)
            )
            split_idx = int(len(pair_df) * train_ratio)
            train_dfs.append(pair_df.iloc[:split_idx])
            test_dfs.append(pair_df.iloc[split_idx:])

        train_df = pd.concat(train_dfs, ignore_index=True)
        test_df = pd.concat(test_dfs, ignore_index=True)

        logger.info(f"Training samples: {len(train_df)}, Test samples: {len(test_df)}")

        # Prepare data
        X_train = train_df[feature_cols]
        y_train = train_df[target_col]
        X_test = test_df[feature_cols]
        y_test = test_df[target_col]

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Create validation set for early stopping
        val_split = int(len(X_train_scaled) * 0.9)
        X_tr, X_val = X_train_scaled[:val_split], X_train_scaled[val_split:]
        y_tr, y_val = y_train.iloc[:val_split], y_train.iloc[val_split:]

        # Train model
        logger.info(f"Training XGBoost model with {len(feature_cols)} features...")
        self.model = xgb.XGBRegressor(**self.get_xgb_params())
        self.model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

        logger.info(f"Best iteration: {self.model.best_iteration}")

        # Generate predictions
        predictions_scaled = self.model.predict(X_test_scaled)

        # Clip predictions
        train_std = y_train.std()
        train_mean = y_train.mean()
        clip_range = (train_mean - 3 * train_std, train_mean + 3 * train_std)
        predictions_scaled = np.clip(predictions_scaled, clip_range[0], clip_range[1])

        # Convert to log-return scale
        predictions = predictions_scaled / target_scaling
        actuals = y_test.values / target_scaling

        # Create results dataframe
        results = pd.DataFrame(
            {
                "timestamp": test_df["timestamp"].values,
                "pair": test_df["pair"].values,
                "actual": actuals,
                "predicted": predictions,
            }
        )

        # Calculate metrics
        mse = mean_squared_error(actuals, predictions)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(actuals, predictions)

        metrics = {
            "mse": mse,
            "rmse": rmse,
            "mae": mae,
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "best_iteration": self.model.best_iteration,
        }

        # Feature importance
        importance_df = pd.DataFrame(
            {"feature": feature_cols, "importance": self.model.feature_importances_}
        ).sort_values("importance", ascending=False)

        self.is_trained = True
        self.training_stats = {
            "train_mean": train_mean,
            "train_std": train_std,
            "target_scaling": target_scaling,
        }

        logger.info(f"Training complete. RMSE: {rmse:.6f}, MAE: {mae:.6f}")

        return TrainingResult(
            model=self.model,
            scaler=self.scaler,
            feature_cols=feature_cols,
            metrics=metrics,
            predictions=results,
            feature_importance=importance_df,
        )


class XGBWalkForwardModel(BaseForexModel):
    """
    XGBoost Walk-Forward Validation Model
    Retrains model at each step for more robust out-of-sample testing.
    """

    def __init__(self, config: ModelConfig, model_name: str = "walk_forward"):
        super().__init__(config, model_name)
        self.walk_forward_models = []

    def train(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = "target",
        train_window: int = 444,
        test_window: int = 111,
        step_size: int = 111,
        target_scaling: float = 100,
    ) -> TrainingResult:
        """
        Train using walk-forward validation.

        Args:
            df: DataFrame with features and target
            feature_cols: List of feature column names
            target_col: Target column name
            train_window: Number of bars for training
            test_window: Number of bars for testing
            step_size: Step size for walk-forward
            target_scaling: Scaling factor for target

        Returns:
            TrainingResult with model and metrics
        """
        self.feature_cols = feature_cols

        all_results = []
        all_importance = []

        for pair in df["pair"].unique():
            logger.info(f"Processing {pair}...")
            pair_df = (
                df[df["pair"] == pair]
                .copy()
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

            pair_results, pair_importance = self._walk_forward_single_pair(
                pair_df,
                feature_cols,
                target_col,
                train_window,
                test_window,
                step_size,
                target_scaling,
            )

            if pair_results is not None:
                pair_results["pair"] = pair
                all_results.append(pair_results)
                all_importance.append(pair_importance)
                logger.info(f"  {pair}: {len(pair_results)} test samples")

        if not all_results:
            raise ValueError("Walk-forward validation produced no results")

        # Combine results
        results = pd.concat(all_results, ignore_index=True)

        # Average feature importance
        importance_df = (
            pd.concat(all_importance)
            .groupby("feature")["importance"]
            .mean()
            .sort_values(ascending=False)
            .reset_index()
        )

        # Calculate overall metrics
        mse = mean_squared_error(results["actual"], results["predicted"])
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(results["actual"], results["predicted"])

        metrics = {
            "mse": mse,
            "rmse": rmse,
            "mae": mae,
            "total_samples": len(results),
            "train_window": train_window,
            "test_window": test_window,
        }

        # Store the last trained model and scaler for inference
        self.is_trained = True

        logger.info(f"Walk-forward complete. RMSE: {rmse:.6f}, MAE: {mae:.6f}")

        return TrainingResult(
            model=self.model,
            scaler=self.scaler,
            feature_cols=feature_cols,
            metrics=metrics,
            predictions=results,
            feature_importance=importance_df,
        )

    def _walk_forward_single_pair(
        self,
        pair_df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        train_window: int,
        test_window: int,
        step_size: int,
        target_scaling: float,
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Run walk-forward validation for a single pair"""

        n_samples = len(pair_df)
        if n_samples <= test_window:
            return None, None

        effective_train = min(train_window, n_samples - test_window)
        if effective_train <= 0:
            return None, None

        predictions_scaled = []
        actuals_scaled = []
        dates = []
        importance_records = []

        current_idx = effective_train

        while current_idx + test_window <= n_samples:
            train_start = current_idx - effective_train
            train_end = current_idx
            test_end = current_idx + test_window

            X_train = pair_df.iloc[train_start:train_end][feature_cols]
            y_train = pair_df.iloc[train_start:train_end][target_col]

            X_test = pair_df.iloc[train_end:test_end][feature_cols]
            y_test = pair_df.iloc[train_end:test_end][target_col]
            test_dates = pair_df.iloc[train_end:test_end]["timestamp"]

            if len(X_train) == 0 or len(X_test) == 0:
                break

            # Scale and train
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Remove early_stopping_rounds for walk-forward (no validation set)
            params = self.get_xgb_params()
            params.pop("early_stopping_rounds", None)

            model = xgb.XGBRegressor(**params)
            model.fit(X_train_scaled, y_train)

            preds = model.predict(X_test_scaled)

            # Clip predictions
            train_std = y_train.std()
            train_mean = y_train.mean()
            clip_range = (train_mean - 3 * train_std, train_mean + 3 * train_std)
            preds = np.clip(preds, clip_range[0], clip_range[1])

            predictions_scaled.extend(preds)
            actuals_scaled.extend(y_test)
            dates.extend(test_dates)
            importance_records.append(
                pd.Series(model.feature_importances_, index=feature_cols)
            )

            # Store latest model and scaler
            self.model = model
            self.scaler = scaler

            current_idx += step_size

        if not predictions_scaled:
            return None, None

        # Feature importance
        importance_df = (
            pd.concat(importance_records, axis=1)
            .mean(axis=1)
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"index": "feature", 0: "importance"})
        )

        # Convert to log-return scale
        predictions = np.array(predictions_scaled) / target_scaling
        actuals = np.array(actuals_scaled) / target_scaling

        results_df = pd.DataFrame(
            {"timestamp": dates, "actual": actuals, "predicted": predictions}
        )

        results_df = (
            results_df.sort_values("timestamp")
            .drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True)
        )

        return results_df, importance_df


def create_model(
    model_type: str, config: ModelConfig, model_name: str
) -> BaseForexModel:
    """Factory function to create appropriate model"""
    if model_type == "single_train":
        return XGBSingleTrainModel(config, model_name)
    elif model_type == "walk_forward":
        return XGBWalkForwardModel(config, model_name)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
