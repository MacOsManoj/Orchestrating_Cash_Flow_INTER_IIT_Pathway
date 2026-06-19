"""
Position Sizing Module
Implements Kelly Criterion and other position sizing methods.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# Risk-free rate configuration
RF_RATE_ANNUAL = 0.04
RF_RATE_DAILY = 0.04 / 252


@dataclass
class PositionSizeConfig:
    """Configuration for position sizing"""

    method: str = "kelly"  # "kelly", "fixed", "volatility_adjusted", "sharpe"
    kelly_fraction: float = 0.25  # Quarter-Kelly by default
    max_position_pct: float = 0.10  # Maximum 10% per trade
    min_position_pct: float = 0.01  # Minimum 1% per trade
    portfolio_capital: float = 100000.0

    # For volatility-adjusted sizing
    target_volatility: float = 0.02  # 2% daily volatility target

    # For Sharpe-based sizing
    sharpe_scaling: float = (
        0.05  # Position = sharpe_ratio * sharpe_scaling (5% per unit Sharpe)
    )


class KellyCriterion:
    """
    Kelly Criterion Position Sizing

    The Kelly Criterion formula:
    f* = (p * b - q) / b

    Where:
    - f* = fraction of capital to bet
    - p = probability of winning
    - q = probability of losing (1 - p)
    - b = ratio of average win to average loss (payoff ratio)

    For continuous outcomes (like trading):
    f* = (μ - r) / σ²

    Where:
    - μ = expected return
    - r = risk-free rate (usually 0 for short-term)
    - σ² = variance of returns
    """

    def __init__(self, config: PositionSizeConfig):
        self.config = config

    def calculate_kelly_fraction(
        self, win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        """
        Calculate Kelly fraction using discrete outcomes formula.

        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win amount (positive)
            avg_loss: Average loss amount (positive - will be used as absolute)

        Returns:
            Optimal fraction of capital to risk
        """
        p = win_rate
        q = 1 - p

        # Avoid division by zero
        if avg_loss == 0:
            return 0.0

        # b = payoff ratio (average win / average loss)
        b = abs(avg_win) / abs(avg_loss)

        # Kelly formula: f* = (p * b - q) / b
        kelly = (p * b - q) / b

        # Kelly can be negative (meaning don't trade), cap at 0
        kelly = max(kelly, 0.0)

        return kelly

    def calculate_kelly_continuous(
        self,
        expected_return: float,
        return_variance: float,
        risk_free_rate: float = 0.0,
    ) -> float:
        """
        Calculate Kelly fraction using continuous returns formula.

        Args:
            expected_return: Expected return per period
            return_variance: Variance of returns
            risk_free_rate: Risk-free rate (default 0)

        Returns:
            Optimal fraction of capital to risk
        """
        if return_variance == 0:
            return 0.0

        kelly = (expected_return - risk_free_rate) / return_variance
        return max(kelly, 0.0)

    def calculate_from_trades(self, trades: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate Kelly criterion from historical trades.

        Args:
            trades: DataFrame with 'pnl' or 'return' column

        Returns:
            Dict with kelly metrics
        """
        if "pnl" in trades.columns:
            returns = trades["pnl"]
        elif "return" in trades.columns:
            returns = trades["return"]
        elif "net_return" in trades.columns:
            returns = trades["net_return"]
        else:
            raise ValueError(
                "Trades DataFrame must have 'pnl', 'return', or 'net_return' column"
            )

        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(wins) == 0 or len(losses) == 0:
            return {
                "kelly_fraction": 0.0,
                "fractional_kelly": 0.0,
                "win_rate": len(wins) / len(returns) if len(returns) > 0 else 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "payoff_ratio": 0.0,
            }

        win_rate = len(wins) / len(returns)
        avg_win = wins.mean()
        avg_loss = abs(losses.mean())

        # Calculate using discrete formula
        kelly_discrete = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)

        # Calculate using continuous formula
        expected_return = returns.mean()
        return_variance = returns.var()
        kelly_continuous = self.calculate_kelly_continuous(
            expected_return, return_variance
        )

        # Use average of both methods
        full_kelly = (kelly_discrete + kelly_continuous) / 2

        # Apply fractional Kelly
        fractional_kelly = full_kelly * self.config.kelly_fraction

        # Apply bounds
        fractional_kelly = np.clip(
            fractional_kelly, self.config.min_position_pct, self.config.max_position_pct
        )

        return {
            "full_kelly": full_kelly,
            "kelly_discrete": kelly_discrete,
            "kelly_continuous": kelly_continuous,
            "fractional_kelly": fractional_kelly,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "payoff_ratio": avg_win / avg_loss if avg_loss > 0 else 0.0,
            "expected_return": expected_return,
            "return_std": np.sqrt(return_variance),
        }


class VolatilityAdjustedSizing:
    """Position sizing based on volatility targeting"""

    def __init__(self, config: PositionSizeConfig):
        self.config = config

    def calculate_position_size(self, current_volatility: float, price: float) -> float:
        """
        Calculate position size based on volatility.

        Args:
            current_volatility: Current realized volatility (annualized)
            price: Current price of the asset

        Returns:
            Position size as fraction of capital
        """
        if current_volatility == 0:
            return self.config.min_position_pct

        # Convert annualized vol to daily
        daily_vol = current_volatility / np.sqrt(252)

        # Position size = target_vol / current_vol
        position_pct = self.config.target_volatility / daily_vol

        # Apply bounds
        position_pct = np.clip(
            position_pct, self.config.min_position_pct, self.config.max_position_pct
        )

        return position_pct


class SharpeFractionSizing:
    """
    Sharpe Fraction Position Sizing

    Position size is proportional to the strategy's Sharpe ratio.
    Higher Sharpe = higher confidence = larger position.

    Formula:
    f* = Sharpe_ratio * sharpe_scaling

    Where:
    - Sharpe_ratio = (mean_return / std_return) * sqrt(252) for annualized
    - sharpe_scaling = scaling factor (default 5% per unit Sharpe)

    Example: Sharpe of 2.0 with 5% scaling = 10% position
    """

    def __init__(self, config: PositionSizeConfig):
        self.config = config

    def calculate_from_trades(self, trades: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate position size based on Sharpe ratio from historical trades.

        Args:
            trades: DataFrame with 'pnl', 'return', or 'net_return' column

        Returns:
            Dict with sharpe metrics and position size
        """
        if "pnl" in trades.columns:
            returns = trades["pnl"]
        elif "return" in trades.columns:
            returns = trades["return"]
        elif "net_return" in trades.columns:
            returns = trades["net_return"]
        else:
            raise ValueError(
                "Trades DataFrame must have 'pnl', 'return', or 'net_return' column"
            )

        if len(returns) < 2 or returns.std() == 0:
            return {
                "sharpe_ratio": 0.0,
                "annualized_sharpe": 0.0,
                "position_pct": self.config.min_position_pct,
                "mean_return": 0.0,
                "std_return": 0.0,
            }

        mean_return = returns.mean()
        std_return = returns.std()

        # Daily Sharpe (subtracting risk-free rate)
        daily_sharpe = (
            (mean_return - RF_RATE_DAILY) / std_return if std_return > 0 else 0.0
        )

        # Annualized Sharpe
        annualized_sharpe = daily_sharpe * np.sqrt(252)

        # Position size = Sharpe * scaling factor
        # Only use positive Sharpe for sizing
        position_pct = max(annualized_sharpe, 0.0) * self.config.sharpe_scaling

        # Apply bounds
        position_pct = np.clip(
            position_pct, self.config.min_position_pct, self.config.max_position_pct
        )

        # Win/loss statistics for reference
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.0

        return {
            "sharpe_ratio": daily_sharpe,
            "annualized_sharpe": annualized_sharpe,
            "position_pct": position_pct,
            "mean_return": mean_return,
            "std_return": std_return,
            "win_rate": win_rate,
            "num_trades": len(returns),
        }


class PositionSizer:
    """Main position sizing class that combines different methods"""

    def __init__(self, config: PositionSizeConfig):
        self.config = config
        self.kelly = KellyCriterion(config)
        self.vol_adjusted = VolatilityAdjustedSizing(config)
        self.sharpe = SharpeFractionSizing(config)

    def calculate_position_size(
        self,
        signal_strength: float,
        trades_history: Optional[pd.DataFrame] = None,
        current_volatility: Optional[float] = None,
        current_price: Optional[float] = None,
        model_confidence: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate position size using the configured method.

        Args:
            signal_strength: Strength of the trading signal (-1 to 1)
            trades_history: Historical trades for Kelly calculation
            current_volatility: Current realized volatility
            current_price: Current asset price
            model_confidence: Model prediction confidence (0-1)

        Returns:
            Dict with position sizing information
        """
        result = {
            "method": self.config.method,
            "signal_strength": signal_strength,
            "position_pct": 0.0,
            "position_value": 0.0,
            "direction": "flat",
        }

        # For Sharpe method, don't filter by signal strength - allocate based on historical Sharpe
        # For other methods, require minimum signal strength
        if self.config.method != "sharpe" and abs(signal_strength) < 0.001:
            return result

        # Set direction based on signal (or default to long for Sharpe method with no signal)
        if signal_strength > 0:
            result["direction"] = "long"
        elif signal_strength < 0:
            result["direction"] = "short"
        elif self.config.method == "sharpe":
            result["direction"] = (
                "long"  # Default to long for Sharpe when signal is neutral
            )
        else:
            return result  # No direction for other methods

        # Calculate base position size based on method
        if (
            self.config.method == "kelly"
            and trades_history is not None
            and len(trades_history) > 10
        ):
            kelly_metrics = self.kelly.calculate_from_trades(trades_history)
            base_position = kelly_metrics["fractional_kelly"]
            result["kelly_metrics"] = kelly_metrics
            # Adjust by signal strength
            position_pct = base_position * abs(signal_strength)
            # Adjust by model confidence if available
            if model_confidence is not None:
                position_pct *= model_confidence

        elif (
            self.config.method == "sharpe"
            and trades_history is not None
            and len(trades_history) > 10
        ):
            sharpe_metrics = self.sharpe.calculate_from_trades(trades_history)
            base_position = sharpe_metrics["position_pct"]
            result["sharpe_metrics"] = sharpe_metrics
            # Sharpe method: use full calculated position, no additional scaling
            position_pct = base_position

        elif (
            self.config.method == "volatility_adjusted"
            and current_volatility is not None
        ):
            base_position = self.vol_adjusted.calculate_position_size(
                current_volatility, current_price or 1.0
            )
            # Adjust by signal strength
            position_pct = base_position * abs(signal_strength)
            # Adjust by model confidence if available
            if model_confidence is not None:
                position_pct *= model_confidence

        else:
            # Fixed position sizing
            base_position = self.config.max_position_pct / 2  # Half of max as default
            # Adjust by signal strength
            position_pct = base_position * abs(signal_strength)
            # Adjust by model confidence if available
            if model_confidence is not None:
                position_pct *= model_confidence

        # Apply bounds
        position_pct = np.clip(
            position_pct, self.config.min_position_pct, self.config.max_position_pct
        )

        result["position_pct"] = position_pct
        result["position_value"] = position_pct * self.config.portfolio_capital

        return result

    def calculate_portfolio_allocation(
        self,
        signals: Dict[str, float],
        trades_history: Optional[Dict[str, pd.DataFrame]] = None,
        volatilities: Optional[Dict[str, float]] = None,
        prices: Optional[Dict[str, float]] = None,
        model_confidences: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Dict]:
        """
        Calculate position sizes for multiple assets.

        Args:
            signals: Dict of {pair: signal_strength}
            trades_history: Dict of {pair: trades_df}
            volatilities: Dict of {pair: volatility}
            prices: Dict of {pair: current_price}
            model_confidences: Dict of {pair: confidence}

        Returns:
            Dict of {pair: position_info}
        """
        allocations = {}
        total_allocation = 0.0

        for pair, signal in signals.items():
            pair_trades = trades_history.get(pair) if trades_history else None
            pair_vol = volatilities.get(pair) if volatilities else None
            pair_price = prices.get(pair) if prices else None
            pair_conf = model_confidences.get(pair) if model_confidences else None

            allocation = self.calculate_position_size(
                signal_strength=signal,
                trades_history=pair_trades,
                current_volatility=pair_vol,
                current_price=pair_price,
                model_confidence=pair_conf,
            )

            allocations[pair] = allocation
            total_allocation += allocation["position_pct"]

        # Scale down if total allocation exceeds 100%
        if total_allocation > 1.0:
            scale_factor = 1.0 / total_allocation
            for pair in allocations:
                allocations[pair]["position_pct"] *= scale_factor
                allocations[pair]["position_value"] *= scale_factor
            logger.warning(
                f"Total allocation exceeded 100%, scaled down by {scale_factor:.2f}"
            )

        # Add portfolio summary
        allocations["_portfolio_summary"] = {
            "total_allocation_pct": min(total_allocation, 1.0),
            "total_allocation_value": min(total_allocation, 1.0)
            * self.config.portfolio_capital,
            "num_positions": len(
                [
                    p
                    for p, a in allocations.items()
                    if p != "_portfolio_summary" and a["direction"] != "flat"
                ]
            ),
        }

        return allocations


def calculate_comprehensive_metrics(
    signals_df: pd.DataFrame, strategy_name: str = "Strategy"
) -> Dict:
    """
    Calculate comprehensive trading metrics for strategy evaluation.
    Used for Kelly criterion inputs and performance tracking.
    """
    df = signals_df.drop_duplicates(subset="timestamp", keep="last").reset_index(
        drop=True
    )

    strategy_returns = df["net_return"]
    actual_returns = df["actual"]
    positions = df["position"]

    # Total profit
    cum_return = (1 + strategy_returns).cumprod().iloc[-1]
    total_profit = cum_return - 1

    # Buy & Hold Return
    buyhold_return = (1 + actual_returns).cumprod().iloc[-1] - 1

    # Sharpe Ratio
    sharpe = (
        (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
        if strategy_returns.std() > 0
        else 0.0
    )

    # Information Ratio
    excess_returns = strategy_returns - actual_returns
    ir = (
        (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
        if excess_returns.std() > 0
        else 0.0
    )

    # Max Drawdown
    cum_returns = (1 + strategy_returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdown = (cum_returns - rolling_max) / rolling_max
    max_dd = drawdown.min()

    # Win/Loss statistics
    wins = strategy_returns[strategy_returns > 0]
    losses = strategy_returns[strategy_returns < 0]
    win_rate = len(wins) / len(strategy_returns) if len(strategy_returns) > 0 else 0.0
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.0

    # Profit Factor
    gross_profit = wins.sum() if len(wins) > 0 else 0.0
    gross_loss = abs(losses.sum()) if len(losses) > 0 else 1e-9
    profit_factor = gross_profit / gross_loss

    # Position distribution
    long_pct = (positions == 1).mean() * 100
    short_pct = (positions == -1).mean() * 100
    flat_pct = (positions == 0).mean() * 100

    # Sortino Ratio
    downside_returns = strategy_returns[strategy_returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 1e-9
    sortino = (
        (strategy_returns.mean() / downside_std) * np.sqrt(252)
        if downside_std > 0
        else 0.0
    )

    # Turnover
    pos_changes = positions.diff().abs().fillna(0)
    turnover = pos_changes.mean()

    # Calmar Ratio
    annualized_return = (
        (1 + total_profit) ** (252 / len(df)) - 1 if len(df) > 0 else 0.0
    )
    calmar = annualized_return / abs(max_dd) if max_dd != 0 else 0.0

    return {
        "strategy_name": strategy_name,
        "total_samples": len(df),
        "total_profit_pct": round(total_profit * 100, 4),
        "buyhold_return_pct": round(buyhold_return * 100, 4),
        "cumulative_return": round(cum_return, 4),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "information_ratio": round(ir, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "calmar_ratio": round(calmar, 4),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "avg_win_pct": round(avg_win * 100, 6),
        "avg_loss_pct": round(avg_loss * 100, 6),
        "turnover_ratio": round(turnover, 4),
        "annualized_return_pct": round(annualized_return * 100, 4),
        "position_distribution": {
            "long_pct": round(long_pct, 2),
            "short_pct": round(short_pct, 2),
            "flat_pct": round(flat_pct, 2),
        },
    }
