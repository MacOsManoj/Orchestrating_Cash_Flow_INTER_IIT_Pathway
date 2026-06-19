"""
FastAPI Router for Forex Trading Pipeline and Agent
Provides REST API for trading pipeline operations and forex agent queries.

Endpoints:
- Main Page: Forex pairs overview, recommended trades
- Currency Page: Chart data, risk metrics, portfolio exposure
- Miscellaneous: Correlation matrix, trading records, agent queries
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv

# Load environment variables from .env file
# First try to load from the backend root, then from the local forex directory
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_backend_root, ".env"))  # backend/.env
load_dotenv()  # Also try local .env

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import numpy as np
import pandas as pd

import logging

logger = logging.getLogger(__name__)


# =============================================================================
# =============================================================================
# PYDANTIC MODELS - Request/Response Schemas
# =============================================================================

# Imported from app.forex.schemas
from app.forex.schemas import (
    ForexPairSummary,
    ForexPairsResponse,
    RecommendedTrade,
    RecommendedTradesResponse,
    PositionUpdateRequest,
    TradeActionRequest,
    TradeActionResponse,
    PortfolioSummaryResponse,
    CumulativeProfitResponse,
    AllPairsProfitResponse,
    PositionUpdateResponse,
    PriceDataPoint,
    CurrencyPriceData,
    RiskMetrics,
    PortfolioExposure,
    CorrelationMatrixResponse,
    TradeRecord,
    TradeRecordsResponse,
    QueryRequest,
    QueryResponse,
    PipelineRunRequest,
    PipelineStatusResponse,
    PositionResponse,
    TradesResponse,
    HealthResponse,
    HeadlineNews,
    PairHeadlineSentiment,
    HeadlineSentimentResponse,
    PipelineMode,
)


# =============================================================================
# GLOBAL STATE
# =============================================================================


class AppState:
    """Application state container"""

    def __init__(self):
        self.pipeline = None
        self.agent = None
        self.last_pipeline_run = None
        self.is_pipeline_running = False
        self.data_manager = None

    def initialize_pipeline(self, config_path: str = "config.yaml"):
        """Initialize the trading pipeline"""
        from app.forex.pipeline import ForexTradingPipeline

        self.pipeline = ForexTradingPipeline(config_path)
        self.data_manager = self.pipeline.data_manager
        logger.info("Pipeline initialized")

    def initialize_agent(
        self, api_key: str = None, model: str = "gemini/gemini-2.5-flash-lite"
    ):
        """Initialize the forex agent"""
        from app.forex.forex_agent import create_forex_agent

        self.agent = create_forex_agent(api_key=api_key, model=model)
        logger.info("Agent initialized")


app_state = AppState()


# =============================================================================
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Imported from app.forex.utils
from app.forex.utils import (
    load_price_data,
    calculate_volatility,
    calculate_atr,
    calculate_var,
    load_positions,
    save_positions,
    load_trades,
    save_trades,
    record_closed_trade,
    update_unrealized_pnl,
    update_portfolio_summary,
    get_headline_sentiment_for_pair,
    FOREX_PAIRS,
    PAIR_SEARCH_QUERIES,
)


# =============================================================================
# API ROUTER
# =============================================================================

app = FastAPI(title="Forex Trading API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    initialize_forex_services()


def initialize_forex_services():
    """Initialize forex services - call this from main app startup"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_config = os.path.join(base_dir, "config.yaml")
    config_path = os.environ.get("FOREX_CONFIG_PATH", default_config)

    # Fallback if env path is invalid (e.g. relative path from wrong CWD)
    if not os.path.exists(config_path) and os.path.exists(default_config):
        logger.warning(
            f"Config path '{config_path}' not found, falling back to default: {default_config}"
        )
        config_path = default_config

    try:
        app_state.initialize_pipeline(config_path)
        app_state.initialize_agent()
        logger.info("Forex services initialized")
    except Exception as e:
        logger.error(f"Initialization error: {e}")


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy", timestamp=datetime.now().isoformat(), version="2.0.0"
    )


@app.get("/status", response_model=PipelineStatusResponse, tags=["Pipeline"])
async def get_pipeline_status():
    """Get current pipeline status"""
    if not app_state.pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    return PipelineStatusResponse(
        status="running" if app_state.is_pipeline_running else "idle",
        last_run=app_state.last_pipeline_run,
        models_trained=list(app_state.pipeline.models.keys()),
        current_signals=app_state.pipeline.current_signals,
        positions=app_state.pipeline.positions,
    )


# =============================================================================
# MAIN PAGE ENDPOINTS
# =============================================================================


@app.get("/api/v1/pairs", response_model=ForexPairsResponse, tags=["Main Page"])
async def get_forex_pairs():
    """
    Get all forex pairs with 1-day price change and current spot price.

    Returns summary data for all 6 currency pairs including:
    - Current spot price
    - 1-day price change
    - 1-day percentage change
    """
    pairs = FOREX_PAIRS
    summaries = []

    for pair in pairs:
        df = load_price_data(pair)

        if df.empty or len(df) < 2:
            # Return placeholder data if no price data available
            summaries.append(
                ForexPairSummary(
                    pair=pair,
                    current_price=0.0,
                    previous_close=0.0,
                    price_change_1d=0.0,
                    price_change_pct_1d=0.0,
                )
            )
            continue

        current_price = float(df["close"].iloc[-1])
        previous_close = float(df["close"].iloc[-2])
        price_change = current_price - previous_close
        price_change_pct = (
            (price_change / previous_close) * 100 if previous_close != 0 else 0
        )

        high_1d = float(df["high"].iloc[-1])
        low_1d = float(df["low"].iloc[-1])

        summaries.append(
            ForexPairSummary(
                pair=pair,
                current_price=round(current_price, 5),
                previous_close=round(previous_close, 5),
                price_change_1d=round(price_change, 5),
                price_change_pct_1d=round(price_change_pct, 4),
                high_1d=round(high_1d, 5),
                low_1d=round(low_1d, 5),
            )
        )

    return ForexPairsResponse(pairs=summaries, timestamp=datetime.now().isoformat())


@app.get(
    "/api/v1/recommended-trades",
    response_model=RecommendedTradesResponse,
    tags=["Main Page"],
)
async def get_recommended_trades():
    """
    Get recommended trades for all currency pairs based on model predictions.

    This endpoint:
    1. Loads latest price data for each pair
    2. Generates model predictions using the trading pipeline
    3. Returns buy/sell/hold recommendations with stop_loss % from config
    """
    if not app_state.pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    pairs = FOREX_PAIRS
    trades = []

    # Get stop_loss percentage from config (e.g., 0.01 = 1%)
    # Default to 1% stop loss, override from config if available
    stop_loss_pct = 0.01
    if (
        app_state.pipeline
        and hasattr(app_state.pipeline, "config")
        and app_state.pipeline.config
    ):
        stop_loss_pct = app_state.pipeline.config.trading_config.get("stop_loss", 0.01)

    # Generate predictions for all pairs using the pipeline
    try:
        # This will load latest data and run predictions
        current_signals = app_state.pipeline.current_signals

        # If no signals, try to generate them
        if not current_signals:
            app_state.pipeline.generate_signals()
            current_signals = app_state.pipeline.current_signals
    except Exception as e:
        logger.warning(f"Could not generate signals: {e}")
        current_signals = {}

    # Load current positions to check if trade already made
    positions = load_positions()

    for pair in pairs:
        df = load_price_data(pair)

        if df.empty or len(df) < 2:
            current_price = 0.0
            price_change_pct = 0.0
        else:
            current_price = float(df["close"].iloc[-1])
            prev_price = float(df["close"].iloc[-2])
            price_change_pct = (
                ((current_price - prev_price) / prev_price) * 100
                if prev_price != 0
                else 0
            )

        # Get signal from model prediction
        signal_info = current_signals.get(pair, {})
        model_direction = (
            signal_info.get("direction", "flat") if signal_info else "flat"
        )
        predicted_return = float(signal_info.get("predicted_return", 0))
        signal_strength = float(signal_info.get("signal_strength", 0))

        # Check current position
        pos_info = positions.get(pair, {})
        current_position = pos_info.get("current_position", "flat")

        # Determine action based on model signal
        if model_direction == "long":
            action = "buy"
        elif model_direction == "short":
            action = "sell"
        else:
            action = "hold"

        # If trade already made (position matches recommendation), mark as already executed
        already_in_position = False
        if action == "buy" and current_position == "long":
            already_in_position = True
        elif action == "sell" and current_position == "short":
            already_in_position = True
        elif action == "hold" and current_position == "flat":
            already_in_position = True

        # Map signal strength to string
        strength_str = "weak"
        if signal_strength > 60:
            strength_str = "strong"
        elif signal_strength > 30:
            strength_str = "moderate"

        trades.append(
            RecommendedTrade(
                pair=pair,
                current_price=round(current_price, 5),
                price_change_pct=round(price_change_pct, 4),
                action=action if not already_in_position else "already_executed",
                signal_strength=strength_str,
                model_confidence=round(signal_strength / 100, 4),
                predicted_return=round(predicted_return, 6),
                stop_loss_pct=stop_loss_pct,
            )
        )

    return RecommendedTradesResponse(
        trades=trades, timestamp=datetime.now().isoformat()
    )


@app.post(
    "/api/v1/positions/update",
    response_model=PositionUpdateResponse,
    tags=["Main Page"],
)
async def update_position(request: PositionUpdateRequest):
    """
    Update a position based on user action (button click).

    Actions:
    - open_long: Open a long position
    - open_short: Open a short position
    - close: Close the current position
    - update_size: Update position size
    """
    positions = load_positions()
    trades_data = load_trades()

    pair = request.pair.upper()
    action = request.action.lower()

    # Get current price if not provided
    df = load_price_data(pair)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {pair}")

    current_price = request.price if request.price else float(df["close"].iloc[-1])
    current_time = datetime.now()

    prev_position = positions.get(pair, {})

    if action == "open_long":
        # Open a long position
        positions[pair] = {
            "current_position": "long",
            "entry_date": current_time.strftime("%Y-%m-%d"),
            "entry_price": round(current_price, 5),
            "current_price": round(current_price, 5),
            "unrealized_pnl_pct": 0.0,
            "position_size": int(request.size) if request.size else 10000,
            "stop_loss": round(current_price * 0.99, 5),
            "take_profit": round(current_price * 1.02, 5),
            "risk_reward_ratio": 2.0,
            "days_held": 0,
            "model_confidence": 0.5,
            "signal_strength": "moderate",
            "entry_reason": f"Manual entry: {action}",
        }
        message = f"Opened long position for {pair} at {current_price}"

    elif action == "open_short":
        # Open a short position
        positions[pair] = {
            "current_position": "short",
            "entry_date": current_time.strftime("%Y-%m-%d"),
            "entry_price": round(current_price, 5),
            "current_price": round(current_price, 5),
            "unrealized_pnl_pct": 0.0,
            "position_size": int(request.size) if request.size else 10000,
            "stop_loss": round(current_price * 1.01, 5),
            "take_profit": round(current_price * 0.98, 5),
            "risk_reward_ratio": 2.0,
            "days_held": 0,
            "model_confidence": 0.5,
            "signal_strength": "moderate",
            "entry_reason": f"Manual entry: {action}",
        }
        message = f"Opened short position for {pair} at {current_price}"

    elif action == "close":
        # Close existing position
        if pair not in positions or positions[pair].get("current_position") == "flat":
            raise HTTPException(status_code=400, detail=f"No open position for {pair}")

        entry_price = prev_position.get("entry_price", current_price)
        direction = prev_position.get("current_position", "long")

        # Calculate P&L
        if direction == "long":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Record the trade
        if pair not in trades_data:
            trades_data[pair] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit_pct": 0.0,
                "recent_trades": [],
            }

        trade_record = {
            "date": current_time.strftime("%Y-%m-%d"),
            "side": direction,
            "entry": round(entry_price, 5),
            "exit": round(current_price, 5),
            "pnl_pct": round(pnl_pct, 4),
        }

        trades_data[pair]["total_trades"] += 1
        trades_data[pair]["total_profit_pct"] += pnl_pct
        if pnl_pct > 0:
            trades_data[pair]["winning_trades"] += 1
        else:
            trades_data[pair]["losing_trades"] += 1
        trades_data[pair]["win_rate"] = (
            trades_data[pair]["winning_trades"] / trades_data[pair]["total_trades"]
        )
        trades_data[pair]["recent_trades"].insert(0, trade_record)
        trades_data[pair]["recent_trades"] = trades_data[pair]["recent_trades"][:10]

        # Update position to flat
        positions[pair] = {
            "current_position": "flat",
            "last_exit_date": current_time.strftime("%Y-%m-%d"),
            "last_exit_price": round(current_price, 5),
            "last_trade_pnl_pct": round(pnl_pct, 4),
            "days_since_last_trade": 0,
            "pending_signal": "none",
            "signal_strength": "weak",
            "reason": "Position closed manually",
        }

        save_trades(trades_data)
        message = f"Closed {direction} position for {pair} at {current_price}, P&L: {pnl_pct:.2f}%"

    elif action == "update_size":
        if pair not in positions:
            raise HTTPException(status_code=400, detail=f"No position for {pair}")

        if request.size is None:
            raise HTTPException(
                status_code=400, detail="Size required for update_size action"
            )

        positions[pair]["position_size"] = int(request.size)
        message = f"Updated position size for {pair} to {request.size}"

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    # Update portfolio summary
    total_long = sum(
        p.get("position_size", 0)
        for pair, p in positions.items()
        if pair != "portfolio_summary" and p.get("current_position") == "long"
    )
    total_short = sum(
        p.get("position_size", 0)
        for pair, p in positions.items()
        if pair != "portfolio_summary" and p.get("current_position") == "short"
    )

    positions["portfolio_summary"] = {
        "total_open_positions": sum(
            1
            for pair, p in positions.items()
            if pair != "portfolio_summary"
            and p.get("current_position") not in ["flat", None]
        ),
        "total_exposure_long": total_long,
        "total_exposure_short": total_short,
        "net_exposure": total_long - total_short,
        "last_updated": current_time.isoformat(),
    }

    save_positions(positions)

    return PositionUpdateResponse(
        success=True,
        pair=pair,
        action=action,
        message=message,
        updated_position=positions.get(pair),
        timestamp=current_time.isoformat(),
    )


@app.post("/api/v1/trade", response_model=TradeActionResponse, tags=["Main Page"])
async def execute_trade_action(request: TradeActionRequest):
    """
    Execute a trade action when user clicks Buy, Sell, or Hold button.

    Actions:
    - **buy**: Open a long position or add to existing long
    - **sell**: Open a short position or add to existing short
    - **hold**: Close any open position and stay flat

    Example request:
    ```json
    {
        "pair": "EURUSD",
        "action": "buy",
        "amount": 10000
    }
    ```
    """
    import uuid

    positions = load_positions()
    trades_data = load_trades()

    pair = request.pair.upper()
    action = request.action.lower()
    amount = request.amount or 10000

    # Validate action
    if action not in ["buy", "sell", "hold"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {action}. Must be 'buy', 'sell', or 'hold'",
        )

    # Get current market price
    df = load_price_data(pair)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {pair}")

    current_price = request.price if request.price else float(df["close"].iloc[-1])
    current_time = datetime.now()
    trade_id = str(uuid.uuid4())[:8]

    prev_position = positions.get(pair, {})
    prev_state = prev_position.get("current_position", "flat")

    # Process based on action
    if action == "buy":
        # Open long position or close short and go long
        if prev_state == "short":
            # Close short first, record trade
            record_closed_trade(
                trades_data, pair, prev_position, current_price, current_time
            )

        positions[pair] = {
            "current_position": "long",
            "entry_date": current_time.strftime("%Y-%m-%d"),
            "entry_price": round(current_price, 5),
            "current_price": round(current_price, 5),
            "unrealized_pnl_pct": 0.0,
            "position_size": int(amount),
            "stop_loss": round(current_price * 0.99, 5),
            "take_profit": round(current_price * 1.02, 5),
            "risk_reward_ratio": 2.0,
            "days_held": 0,
            "model_confidence": 0.5,
            "signal_strength": "moderate",
            "entry_reason": f"Manual BUY at {current_price}",
        }
        message = f"BUY order executed for {pair} at {current_price:.5f}"
        position_after = "long"

    elif action == "sell":
        # Open short position or close long and go short
        if prev_state == "long":
            # Close long first, record trade
            record_closed_trade(
                trades_data, pair, prev_position, current_price, current_time
            )

        positions[pair] = {
            "current_position": "short",
            "entry_date": current_time.strftime("%Y-%m-%d"),
            "entry_price": round(current_price, 5),
            "current_price": round(current_price, 5),
            "unrealized_pnl_pct": 0.0,
            "position_size": int(amount),
            "stop_loss": round(current_price * 1.01, 5),
            "take_profit": round(current_price * 0.98, 5),
            "risk_reward_ratio": 2.0,
            "days_held": 0,
            "model_confidence": 0.5,
            "signal_strength": "moderate",
            "entry_reason": f"Manual SELL at {current_price}",
        }
        message = f"SELL order executed for {pair} at {current_price:.5f}"
        position_after = "short"

    else:  # hold
        # Close any open position
        if prev_state in ["long", "short"]:
            record_closed_trade(
                trades_data, pair, prev_position, current_price, current_time
            )
            message = f"Position closed for {pair} at {current_price:.5f}. Now holding (flat)."
        else:
            message = f"No position to close for {pair}. Staying flat."

        positions[pair] = {
            "current_position": "flat",
            "last_exit_date": current_time.strftime("%Y-%m-%d"),
            "last_exit_price": round(current_price, 5),
            "days_since_last_trade": 0,
            "pending_signal": "none",
            "signal_strength": "weak",
            "reason": "Manual HOLD - position closed",
        }
        position_after = "flat"

    # Update unrealized P&L for all positions
    update_unrealized_pnl(positions)

    # Update portfolio summary
    update_portfolio_summary(positions)

    # Save changes
    save_positions(positions)
    save_trades(trades_data)

    logger.info(f"Portfolio updated: {action.upper()} {pair} @ {current_price}")

    return TradeActionResponse(
        success=True,
        pair=pair,
        action=action.upper(),
        executed_price=round(current_price, 5),
        amount=amount,
        position_after=position_after,
        message=message,
        trade_id=trade_id,
        portfolio_summary=positions.get("portfolio_summary"),
        timestamp=current_time.isoformat(),
    )


@app.get(
    "/api/v1/portfolio", response_model=PortfolioSummaryResponse, tags=["Main Page"]
)
async def get_portfolio_summary():
    """
    Get the full portfolio summary with all positions and their current P&L.

    This endpoint:
    - Updates unrealized P&L for all positions based on current market prices
    - Calculates total portfolio exposure
    - Returns comprehensive portfolio metrics
    """
    positions = load_positions()

    # Update unrealized P&L for all positions
    update_unrealized_pnl(positions)

    # Update portfolio summary
    update_portfolio_summary(positions)

    # Save updated positions
    save_positions(positions)

    summary = positions.get("portfolio_summary", {})

    # Get all position details (excluding portfolio_summary)
    position_details = {
        pair: pos for pair, pos in positions.items() if pair != "portfolio_summary"
    }

    return PortfolioSummaryResponse(
        total_open_positions=summary.get("total_open_positions", 0),
        total_exposure_long=summary.get("total_exposure_long", 0),
        total_exposure_short=summary.get("total_exposure_short", 0),
        net_exposure=summary.get("net_exposure", 0),
        total_unrealized_pnl_pct=summary.get("total_unrealized_pnl_pct", 0),
        portfolio_heat=summary.get("portfolio_heat", 0),
        long_exposure_pct=summary.get("long_exposure_pct", 0),
        short_exposure_pct=summary.get("short_exposure_pct", 0),
        positions=position_details,
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/v1/portfolio/refresh", tags=["Main Page"])
async def refresh_portfolio():
    """
    Refresh all portfolio data - updates unrealized P&L based on latest market prices.

    Call this endpoint periodically to keep portfolio values current.
    """
    positions = load_positions()

    # Update unrealized P&L for all positions
    update_unrealized_pnl(positions)

    # Update portfolio summary
    update_portfolio_summary(positions)

    # Save updated positions
    save_positions(positions)

    return {
        "success": True,
        "message": "Portfolio refreshed with latest market prices",
        "portfolio_summary": positions.get("portfolio_summary"),
        "timestamp": datetime.now().isoformat(),
    }


@app.get(
    "/api/v1/profits/{pair}", response_model=CumulativeProfitResponse, tags=["Profits"]
)
async def get_cumulative_profit(pair: str):
    """
    Get cumulative profit for a specific currency pair.

    Returns:
    - Total profit percentage and amount
    - Trade statistics (wins, losses, win rate)
    - Profit history with running total
    - Current winning/losing streak
    """
    pair = pair.upper()
    trades_data = load_trades()

    if pair not in trades_data:
        # Return empty stats if no trades for this pair
        return CumulativeProfitResponse(
            pair=pair,
            total_profit_pct=0.0,
            total_profit_amount=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_profit_per_trade=0.0,
            largest_win_pct=0.0,
            largest_loss_pct=0.0,
            current_streak=0,
            profit_history=[],
            timestamp=datetime.now().isoformat(),
        )

    trade_info = trades_data[pair]
    recent_trades = trade_info.get("recent_trades", [])

    # Calculate statistics
    total_profit_pct = float(trade_info.get("total_profit_pct", 0))
    total_trades = int(trade_info.get("total_trades", 0))
    winning_trades = int(trade_info.get("winning_trades", 0))
    losing_trades = int(trade_info.get("losing_trades", 0))
    win_rate = float(trade_info.get("win_rate", 0))

    # Calculate average profit per trade
    avg_profit = total_profit_pct / total_trades if total_trades > 0 else 0

    # Find largest win and loss
    pnls = [t.get("pnl_pct", 0) for t in recent_trades]
    largest_win = max(pnls) if pnls else 0
    largest_loss = min(pnls) if pnls else 0

    # Calculate current streak
    current_streak = 0
    if recent_trades:
        first_pnl = recent_trades[0].get("pnl_pct", 0)
        streak_positive = first_pnl > 0
        for trade in recent_trades:
            pnl = trade.get("pnl_pct", 0)
            if (pnl > 0) == streak_positive:
                current_streak += 1 if streak_positive else -1
            else:
                break

    # Build profit history with cumulative totals (filtered to 1 month)
    profit_history = []
    cumulative = 0.0
    one_month_ago = datetime.now() - timedelta(days=30)

    # Filter trades to last 1 month
    filtered_trades = []
    for trade in recent_trades:
        trade_date_str = trade.get("date", "")
        if trade_date_str:
            try:
                trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
                if trade_date >= one_month_ago:
                    filtered_trades.append(trade)
            except:
                filtered_trades.append(trade)  # Include if date parsing fails

    # Reverse to show oldest first for cumulative calculation
    for trade in reversed(filtered_trades):
        pnl = trade.get("pnl_pct", 0)
        cumulative += pnl
        profit_history.append(
            {
                "date": trade.get("date", ""),
                "side": trade.get("side", ""),
                "entry_price": trade.get("entry", 0),
                "exit_price": trade.get("exit", 0),
                "pnl_pct": round(pnl, 4),
                "cumulative_pnl_pct": round(cumulative, 4),
            }
        )

    # Reverse back to show most recent first
    profit_history.reverse()

    # Estimate profit amount (assuming 100k base capital)
    base_capital = 100000
    total_profit_amount = base_capital * (total_profit_pct / 100)

    return CumulativeProfitResponse(
        pair=pair,
        total_profit_pct=round(total_profit_pct, 4),
        total_profit_amount=round(total_profit_amount, 2),
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 4),
        avg_profit_per_trade=round(avg_profit, 4),
        largest_win_pct=round(largest_win, 4),
        largest_loss_pct=round(largest_loss, 4),
        current_streak=current_streak,
        profit_history=profit_history,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/v1/profits", response_model=AllPairsProfitResponse, tags=["Profits"])
async def get_all_cumulative_profits():
    """
    Get cumulative profits for all currency pairs.

    Returns:
    - Profit summary for each pair
    - Total portfolio profit
    - Best and worst performing pairs
    """
    trades_data = load_trades()
    pairs = FOREX_PAIRS

    pair_profits = {}
    total_portfolio_profit_pct = 0.0
    base_capital = 100000

    for pair in pairs:
        trade_info = trades_data.get(pair, {})

        total_profit_pct = float(trade_info.get("total_profit_pct", 0))
        total_trades = int(trade_info.get("total_trades", 0))
        winning_trades = int(trade_info.get("winning_trades", 0))
        losing_trades = int(trade_info.get("losing_trades", 0))
        win_rate = float(trade_info.get("win_rate", 0))
        sharpe = float(trade_info.get("sharpe_ratio", 0))
        max_dd = float(trade_info.get("max_drawdown_pct", 0))

        pair_profits[pair] = {
            "total_profit_pct": round(total_profit_pct, 4),
            "total_profit_amount": round(base_capital * (total_profit_pct / 100), 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown_pct": round(max_dd, 4),
        }

        total_portfolio_profit_pct += total_profit_pct

    # Find best and worst performing pairs
    sorted_pairs = sorted(
        pair_profits.items(), key=lambda x: x[1]["total_profit_pct"], reverse=True
    )
    best_pair = sorted_pairs[0][0] if sorted_pairs else "N/A"
    worst_pair = sorted_pairs[-1][0] if sorted_pairs else "N/A"

    return AllPairsProfitResponse(
        pairs=pair_profits,
        total_portfolio_profit_pct=round(total_portfolio_profit_pct, 4),
        total_portfolio_profit_amount=round(
            base_capital * (total_portfolio_profit_pct / 100), 2
        ),
        best_performing_pair=best_pair,
        worst_performing_pair=worst_pair,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/v1/profits/{pair}/chart-data", tags=["Profits"])
async def get_profit_chart_data(
    pair: str,
    include_csv_history: bool = Query(
        default=True, description="Include full history from trade_history.csv"
    ),
):
    """
    Get daily cumulative profit data for charting over the last 1 month.

    Returns one data point per day with:
    - Date
    - Daily P&L (sum of all trades that day)
    - Cumulative P&L up to that date
    - Capital value at end of day
    """
    pair = pair.upper()

    base_capital = 100000
    one_month_ago = datetime.now() - timedelta(days=30)
    today = datetime.now()

    # Dictionary to aggregate daily profits: {date_str: daily_pnl_pct}
    daily_profits = {}

    if include_csv_history:
        # Try to load from trade_history.csv for full history
        FOREX_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
        csv_path = os.path.join(FOREX_DATA_DIR, "trade_history.csv")

        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)

                # Filter by pair if Pair column exists
                if "Pair" in df.columns:
                    df = df[df["Pair"] == pair]

                # Filter to 1 month of data
                date_col = "Exit_Date" if "Exit_Date" in df.columns else "Entry_Date"
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df[df[date_col] >= one_month_ago]

                if len(df) > 0:
                    for _, row in df.iterrows():
                        pnl_pct = float(row.get("Profit_Pct", 0))
                        date_val = row.get("Exit_Date", row.get("Entry_Date", ""))
                        if pd.notna(date_val):
                            if isinstance(date_val, pd.Timestamp):
                                date_str = date_val.strftime("%Y-%m-%d")
                            else:
                                date_str = str(date_val)[:10]
                            daily_profits[date_str] = (
                                daily_profits.get(date_str, 0) + pnl_pct
                            )
            except Exception as e:
                logger.warning(f"Could not load trade_history.csv: {e}")

    # If no CSV data, fall back to trades.json
    if not daily_profits:
        trades_data = load_trades()
        trade_info = trades_data.get(pair, {})
        recent_trades = trade_info.get("recent_trades", [])

        for trade in recent_trades:
            trade_date_str = trade.get("date", "")
            if trade_date_str:
                try:
                    trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
                    if trade_date >= one_month_ago:
                        pnl_pct = trade.get("pnl_pct", 0)
                        daily_profits[trade_date_str] = (
                            daily_profits.get(trade_date_str, 0) + pnl_pct
                        )
                except:
                    pass

    # Generate data points for each day in the last 30 days
    chart_data = []
    cumulative_pnl = 0.0
    capital = base_capital

    current_date = one_month_ago
    while current_date <= today:
        date_str = current_date.strftime("%Y-%m-%d")
        daily_pnl = daily_profits.get(date_str, 0)
        cumulative_pnl += daily_pnl
        capital += capital * (daily_pnl / 100)

        chart_data.append(
            {
                "date": date_str,
                "daily_pnl_pct": round(daily_pnl, 4),
                "cumulative_pnl_pct": round(cumulative_pnl, 4),
                "capital": round(capital, 2),
            }
        )

        current_date += timedelta(days=1)

    return {
        "pair": pair,
        "data_points": chart_data,
        "total_data_points": len(chart_data),
        "starting_capital": base_capital,
        "final_capital": chart_data[-1]["capital"] if chart_data else base_capital,
        "total_return_pct": chart_data[-1]["cumulative_pnl_pct"] if chart_data else 0,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# CURRENCY PAGE ENDPOINTS
# =============================================================================


@app.get(
    "/api/v1/currency/{pair}/price-data",
    response_model=CurrencyPriceData,
    tags=["Currency Page"],
)
async def get_currency_price_data(
    pair: str, days: int = Query(default=90, description="Number of days of price data")
):
    """
    Get price data for charting a specific currency pair.

    Returns:
    - OHLCV data for the specified period
    - Current spot rate
    - Realized volatility (10d and 20d)
    - ATR (14-day)
    """
    pair = pair.upper()
    df = load_price_data(pair)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {pair}")

    # Filter to requested days
    cutoff_date = datetime.now() - timedelta(days=days)
    df = df[df["timestamp"] >= cutoff_date]

    # Calculate returns for volatility
    df["returns"] = df["close"].pct_change()

    # Calculate metrics
    spot_rate = float(df["close"].iloc[-1])
    vol_10d = calculate_volatility(df["returns"], 10)
    vol_20d = calculate_volatility(df["returns"], 20)
    atr_14d = calculate_atr(df, 14)

    # Format price data
    price_data = []
    for _, row in df.iterrows():
        price_data.append(
            PriceDataPoint(
                timestamp=row["timestamp"].isoformat(),
                open=round(float(row["open"]), 5),
                high=round(float(row["high"]), 5),
                low=round(float(row["low"]), 5),
                close=round(float(row["close"]), 5),
                volume=float(row.get("volume", 0)),
            )
        )

    return CurrencyPriceData(
        pair=pair,
        data=price_data,
        spot_rate=round(spot_rate, 5),
        realized_volatility_10d=round(vol_10d, 4),
        realized_volatility_20d=round(vol_20d, 4),
        atr_14d=round(atr_14d, 5),
        timestamp=datetime.now().isoformat(),
    )


@app.get(
    "/api/v1/currency/{pair}/risk-metrics",
    response_model=RiskMetrics,
    tags=["Currency Page"],
)
async def get_risk_metrics(pair: str):
    """
    Get risk tracking metrics for a specific currency pair.

    Returns:
    - Volatility (10d, 20d, 60d)
    - Value at Risk (95% and 99%)
    - Position size
    - Strategy Sharpe ratio
    - Max drawdown
    """
    pair = pair.upper()
    df = load_price_data(pair)
    positions = load_positions()
    trades_data = load_trades()

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {pair}")

    # Calculate returns
    df["returns"] = df["close"].pct_change()
    returns = df["returns"].dropna()

    # Volatility at different windows
    vol_10d = calculate_volatility(returns, 10)
    vol_20d = calculate_volatility(returns, 20)
    vol_60d = calculate_volatility(returns, 60)

    # Value at Risk
    var_95 = calculate_var(returns, 0.95)
    var_99 = calculate_var(returns, 0.99)

    # Get position size
    pos_info = positions.get(pair, {})
    position_size = float(pos_info.get("position_size", 0))

    # Get Sharpe ratio from trades data
    trade_info = trades_data.get(pair, {})
    sharpe = float(trade_info.get("sharpe_ratio", 0))
    max_dd = float(trade_info.get("max_drawdown_pct", 0))

    # Calculate beta to USD (correlation with USDINR for INR pairs)
    beta_to_usd = None
    if pair.endswith("INR"):
        usd_df = load_price_data("USDINR")
        if not usd_df.empty:
            usd_df["returns"] = usd_df["close"].pct_change()
            merged = pd.merge(
                df[["timestamp", "returns"]].rename(columns={"returns": "pair_ret"}),
                usd_df[["timestamp", "returns"]].rename(columns={"returns": "usd_ret"}),
                on="timestamp",
            )
            if len(merged) > 30:
                cov = merged["pair_ret"].cov(merged["usd_ret"])
                var_usd = merged["usd_ret"].var()
                if var_usd > 0:
                    beta_to_usd = round(cov / var_usd, 4)

    return RiskMetrics(
        pair=pair,
        volatility_10d=round(vol_10d, 4),
        volatility_20d=round(vol_20d, 4),
        volatility_60d=round(vol_60d, 4),
        value_at_risk_95=round(var_95 * 100, 4),  # As percentage
        value_at_risk_99=round(var_99 * 100, 4),
        position_size=position_size,
        strategy_sharpe=round(sharpe, 4),
        max_drawdown_pct=round(max_dd, 4),
        beta_to_usd=beta_to_usd,
        timestamp=datetime.now().isoformat(),
    )


@app.get(
    "/api/v1/currency/{pair}/exposure",
    response_model=PortfolioExposure,
    tags=["Currency Page"],
)
async def get_portfolio_exposure(pair: str):
    """
    Get portfolio exposure and PnL metrics for a specific currency pair.

    Returns:
    - Average buy/sell price
    - Realized and unrealized P&L
    - Portfolio exposure percentage
    """
    pair = pair.upper()
    positions = load_positions()
    trades_data = load_trades()
    df = load_price_data(pair)

    pos_info = positions.get(pair, {})
    trade_info = trades_data.get(pair, {})

    current_price = float(df["close"].iloc[-1]) if not df.empty else 0.0

    # Determine current position state
    current_position = pos_info.get("current_position", "flat")
    position_size = float(pos_info.get("position_size", 0))
    entry_price = pos_info.get("entry_price")
    entry_date = pos_info.get("entry_date")

    # Calculate unrealized P&L
    unrealized_pnl = 0.0
    unrealized_pnl_pct = 0.0
    if current_position == "long" and entry_price:
        unrealized_pnl = (current_price - entry_price) * position_size
        unrealized_pnl_pct = (
            ((current_price - entry_price) / entry_price) * 100
            if entry_price > 0
            else 0
        )
    elif current_position == "short" and entry_price:
        unrealized_pnl = (entry_price - current_price) * position_size
        unrealized_pnl_pct = (
            ((entry_price - current_price) / entry_price) * 100
            if entry_price > 0
            else 0
        )

    # Realized P&L from trade history
    realized_pnl = float(trade_info.get("total_profit_pct", 0))

    # Calculate days held
    days_held = 0
    if entry_date:
        try:
            entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
            days_held = (datetime.now() - entry_dt).days
        except:
            pass

    # Calculate average buy/sell prices from recent trades
    recent_trades = trade_info.get("recent_trades", [])
    buy_prices = [t["entry"] for t in recent_trades if t.get("side") == "long"]
    sell_prices = [t["entry"] for t in recent_trades if t.get("side") == "short"]

    avg_buy_price = round(np.mean(buy_prices), 5) if buy_prices else None
    avg_sell_price = round(np.mean(sell_prices), 5) if sell_prices else None

    # Portfolio exposure percentage (relative to total capital, assuming 100k)
    portfolio_capital = 100000
    portfolio_summary = positions.get("portfolio_summary", {})
    total_exposure = portfolio_summary.get(
        "total_exposure_long", 0
    ) + portfolio_summary.get("total_exposure_short", 0)
    portfolio_exposure_pct = (
        (position_size / portfolio_capital) * 100 if portfolio_capital > 0 else 0
    )

    return PortfolioExposure(
        pair=pair,
        avg_buy_price=avg_buy_price,
        avg_sell_price=avg_sell_price,
        current_position=current_position,
        position_size=position_size,
        realized_pnl=round(realized_pnl, 4),
        unrealized_pnl=round(unrealized_pnl, 2),
        unrealized_pnl_pct=round(unrealized_pnl_pct, 4),
        portfolio_exposure_pct=round(portfolio_exposure_pct, 2),
        entry_date=entry_date,
        days_held=days_held,
        timestamp=datetime.now().isoformat(),
    )


# =============================================================================
# MISCELLANEOUS ENDPOINTS
# =============================================================================


@app.get(
    "/api/v1/correlation-matrix",
    response_model=CorrelationMatrixResponse,
    tags=["Analysis"],
)
async def get_correlation_matrix(
    days: int = Query(
        default=60, description="Number of days for correlation calculation"
    ),
):
    """
    Get correlation matrix for all currency pairs.

    Returns a correlation matrix showing how pairs move relative to each other.
    """
    pairs = FOREX_PAIRS

    # Load returns for all pairs
    returns_dict = {}
    for pair in pairs:
        df = load_price_data(pair)
        if not df.empty:
            df["returns"] = df["close"].pct_change()
            # Filter to requested days
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df["timestamp"] >= cutoff_date]
            returns_dict[pair] = df.set_index("timestamp")["returns"]

    # Create correlation matrix
    if not returns_dict:
        raise HTTPException(status_code=404, detail="No price data available")

    returns_df = pd.DataFrame(returns_dict)
    corr_matrix = returns_df.corr().fillna(0)

    # Convert to list of lists
    matrix = corr_matrix.values.tolist()
    matrix = [[round(val, 4) for val in row] for row in matrix]

    return CorrelationMatrixResponse(
        pairs=list(corr_matrix.columns),
        matrix=matrix,
        period_days=days,
        timestamp=datetime.now().isoformat(),
    )


@app.get(
    "/api/v1/trade-records", response_model=TradeRecordsResponse, tags=["Analysis"]
)
async def get_trade_records(
    pair: Optional[str] = Query(default=None, description="Filter by currency pair"),
    limit: int = Query(default=50, description="Maximum number of records"),
):
    """
    Get trading records history.

    Returns:
    - Currency pair
    - Action (long/short)
    - Entry price
    - Entry datetime
    """
    trades_data = load_trades()
    positions = load_positions()

    records = []

    pairs_to_process = [pair.upper()] if pair else FOREX_PAIRS

    for p in pairs_to_process:
        trade_info = trades_data.get(p, {})
        recent_trades = trade_info.get("recent_trades", [])

        for trade in recent_trades:
            records.append(
                TradeRecord(
                    pair=p,
                    action=trade.get("side", "unknown"),
                    entry_price=trade.get("entry", 0),
                    exit_price=trade.get("exit"),
                    entry_datetime=trade.get("date", ""),
                    exit_datetime=trade.get(
                        "date", ""
                    ),  # Same as exit was on this date
                    pnl_pct=trade.get("pnl_pct"),
                    status="closed",
                )
            )

        # Add current open position if exists
        pos_info = positions.get(p, {})
        if pos_info.get("current_position") not in ["flat", None]:
            records.append(
                TradeRecord(
                    pair=p,
                    action=pos_info.get("current_position", "unknown"),
                    entry_price=pos_info.get("entry_price", 0),
                    exit_price=None,
                    entry_datetime=pos_info.get("entry_date", ""),
                    exit_datetime=None,
                    pnl_pct=pos_info.get("unrealized_pnl_pct"),
                    status="open",
                )
            )

    # Sort by date (most recent first) and limit
    records.sort(key=lambda x: x.entry_datetime or "", reverse=True)
    records = records[:limit]

    return TradeRecordsResponse(
        records=records, total_count=len(records), timestamp=datetime.now().isoformat()
    )


# =============================================================================
# AGENT ENDPOINTS
# =============================================================================


@app.post("/api/v1/agent/query", response_model=QueryResponse, tags=["Agent"])
async def query_agent(request: QueryRequest):
    """
    Query the forex explainability agent.

    The agent can:
    - Analyze trading performance
    - Explain current positions
    - Analyze market regime
    - Calculate correlations
    - Provide news sentiment analysis

    Returns:
    - response: LLM's final answer
    - tools_called: List of tool call details (name, arguments, output)
    - processing_time_ms: Time taken to process
    """
    if not app_state.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    start_time = datetime.now()

    try:
        from app.forex.forex_agent import run_agent_async

        result = await run_agent_async(app_state.agent, request.query)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return QueryResponse(
            response=result["response"],
            tools_called=result.get(
                "tool_calls_detailed", []
            ),  # Detailed tool calls with args/output
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Agent query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agent/query/stream", tags=["Agent"])
async def query_agent_stream(query: str = Query(..., description="User query")):
    """
    Stream query response from the forex agent.
    Returns server-sent events with progress updates.
    """
    if not app_state.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    async def generate():
        try:
            from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

            messages = [HumanMessage(content=query)]

            # Stream events using async astream
            async for event in app_state.agent.astream(
                {"messages": messages}, stream_mode="values"
            ):
                msgs = event.get("messages", [])
                if msgs:
                    last_msg = msgs[-1]

                    if isinstance(last_msg, AIMessage):
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tc in last_msg.tool_calls:
                                tool_name = (
                                    tc.get("name", "unknown")
                                    if isinstance(tc, dict)
                                    else getattr(tc, "name", "unknown")
                                )
                                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"
                        elif last_msg.content:
                            yield f"data: {json.dumps({'type': 'response', 'content': last_msg.content})}\n\n"

                    elif isinstance(last_msg, ToolMessage):
                        # Stream the actual tool output content
                        yield f"data: {json.dumps({'type': 'tool_result', 'content': last_msg.content})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Agent stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# =============================================================================
# PIPELINE ENDPOINTS
# =============================================================================


@app.post("/api/v1/pipeline/run", tags=["Pipeline"])
async def run_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    """
    Run the trading pipeline.

    This will:
    1. Optionally update data from Polygon.io
    2. Train/load models
    3. Generate trading signals
    4. Calculate position sizes
    5. Update positions.json and trades.json
    """
    if not app_state.pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if app_state.is_pipeline_running:
        raise HTTPException(status_code=409, detail="Pipeline is already running")

    def run_pipeline_task():
        app_state.is_pipeline_running = True
        try:
            # Default flags
            force_retrain = False
            update_data = False
            days_back = 30  # Default internally

            # Determine flags based on mode
            mode = request.mode or PipelineMode.NORMAL

            if mode == PipelineMode.TRAIN:
                force_retrain = True
            elif mode == PipelineMode.UPDATE_DATA:
                update_data = True

            if update_data:
                result = app_state.pipeline.update_data_and_run(
                    days_back, force_retrain
                )
            else:
                result = app_state.pipeline.run_full_pipeline(force_retrain)

            app_state.last_pipeline_run = datetime.now().isoformat()
            return result
        finally:
            app_state.is_pipeline_running = False

    background_tasks.add_task(run_pipeline_task)

    return {
        "status": "started",
        "message": "Pipeline execution started in background",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/pipeline/signals", tags=["Pipeline"])
async def get_signals():
    """
    Get current trading signals for all pairs.

    Returns signals from:
    1. In-memory pipeline state (if available and not empty)
    2. Fallback to signals.json file if in-memory is empty

    Signal structure per pair:
    - model: Name of the model that generated the signal
    - position: 1 (long), -1 (short), or 0 (flat)
    - direction: 'long', 'short', or 'flat'
    - predicted_return: Model's predicted return
    - signal_strength: Strength of the signal (0-100)
    - timestamp: When the signal was generated
    """
    signals = {}
    source = "none"

    # Try to get signals from in-memory pipeline state
    if app_state.pipeline and app_state.pipeline.current_signals:
        signals = app_state.pipeline.current_signals
        source = "pipeline"

    # Fallback to signals.json file if in-memory is empty
    if not signals:
        try:
            signals_path = os.path.join(os.path.dirname(__file__), "signals.json")
            with open(signals_path, "r") as f:
                signals = json.load(f)
                source = "file"
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load signals from file: {e}")
            signals = {}

    return {
        "signals": signals,
        "source": source,
        "pairs_with_signals": list(signals.keys()),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/pipeline/allocations", tags=["Pipeline"])
async def get_allocations():
    """
    Get position allocation fractions based on Sharpe ratios from backtests.

    Formula: Fraction(A) = Sharpe(A) / Sum(all Sharpes)

    Returns each pair's Sharpe ratio and allocation fraction.
    """
    # Load Sharpe ratios from trades.json (backtest metrics)
    trades_data = load_trades()

    # Get Sharpe ratios for all pairs
    pair_sharpes = {}
    for pair in FOREX_PAIRS:
        trade_info = trades_data.get(pair, {})
        sharpe = float(trade_info.get("sharpe_ratio", 0))
        # Only use positive Sharpe ratios for allocation
        pair_sharpes[pair] = max(sharpe, 0.0)

    # Calculate total Sharpe
    total_sharpe = sum(pair_sharpes.values())

    # Calculate allocation fraction for each pair
    allocations = {}
    for pair in FOREX_PAIRS:
        sharpe = pair_sharpes[pair]
        fraction = sharpe / total_sharpe if total_sharpe > 0 else 0.0

        allocations[pair] = {
            "sharpe_ratio": round(sharpe, 4),
            "fraction": round(fraction, 4),
        }

    return {
        "allocations": allocations,
        "total_sharpe": round(total_sharpe, 4),
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# LEGACY ENDPOINTS (for backward compatibility)
# =============================================================================


@app.get("/positions", tags=["Data"])
async def get_all_positions():
    """Get all current positions"""
    positions = load_positions()
    return positions


@app.get("/positions/{pair}", response_model=PositionResponse, tags=["Data"])
async def get_position(pair: str):
    """Get position for a specific pair"""
    positions = load_positions()
    pair = pair.upper()

    if pair not in positions:
        raise HTTPException(status_code=404, detail=f"No position data for {pair}")

    return PositionResponse(pair=pair, position=positions[pair])


@app.get("/trades", tags=["Data"])
async def get_all_trades():
    """Get all trade history"""
    trades = load_trades()
    return trades


@app.get("/trades/{pair}", response_model=TradesResponse, tags=["Data"])
async def get_trades(pair: str):
    """Get trade history for a specific pair"""
    trades = load_trades()
    pair = pair.upper()

    if pair not in trades:
        raise HTTPException(status_code=404, detail=f"No trade data for {pair}")

    return TradesResponse(pair=pair, trades=trades[pair])


@app.get("/analysis/regime/{pair}", tags=["Analysis"])
async def get_regime_analysis(pair: str):
    """Get market regime analysis for a specific pair"""
    from app.forex.forex_agent import run_agent_async

    if not app_state.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = await run_agent_async(
            app_state.agent, f"Analyze the market regime for {pair.upper()}"
        )
        return {
            "pair": pair.upper(),
            "analysis": result.get("response", ""),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/news/{pair}", tags=["Analysis"])
async def get_news_analysis(pair: str):
    """Get news sentiment analysis for a specific pair"""
    from app.forex.forex_agent import run_agent_async

    if not app_state.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = await run_agent_async(
            app_state.agent, f"Get news sentiment analysis for {pair.upper()}"
        )
        return {
            "pair": pair.upper(),
            "analysis": result.get("response", ""),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEWS HEADLINE SENTIMENT ENDPOINT
# =============================================================================


@app.get("/news/headlines", response_model=HeadlineSentimentResponse, tags=["News"])
async def get_headline_sentiment(
    pairs: Optional[str] = Query(
        default=None,
        description="Comma-separated list of forex pairs (e.g., 'EURUSD,GBPUSD'). If not provided, returns all pairs.",
    ),
):
    """
    Get bullish/bearish sentiment from news headlines for forex pairs.

    This endpoint scrapes recent news headlines and analyzes their sentiment
    to provide a quick bullish/bearish/neutral signal for each pair.

    **Returns:**
    - Overall market sentiment (BULLISH/BEARISH/NEUTRAL)
    - Per-pair sentiment with confidence levels
    - Individual headlines with sentiment scores

    **Sentiment Interpretation:**
    - BULLISH: Score > 0.15, positive news dominates
    - BEARISH: Score < -0.15, negative news dominates
    - NEUTRAL: Score between -0.15 and 0.15

    **Confidence Levels:**
    - high: 5+ articles with >60% sentiment consistency
    - medium: 2-4 articles or moderate consistency
    - low: <2 articles or mixed sentiment
    """
    try:
        from app.forex.news_tool import FinancialNewsScraperTool

        # Get API key
        api_key = os.getenv("NEWSDATA_API_KEY")
        if not api_key:
            logger.error("NEWSDATA_API_KEY environment variable not set")
            raise HTTPException(
                status_code=500, detail="NEWSDATA_API_KEY environment variable not set"
            )

        # Parse pairs
        if pairs:
            requested_pairs = [p.strip().upper() for p in pairs.split(",")]
            # Validate pairs
            invalid_pairs = [p for p in requested_pairs if p not in FOREX_PAIRS]
            if invalid_pairs:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid pairs: {invalid_pairs}. Valid pairs are: {FOREX_PAIRS}",
                )
            target_pairs = requested_pairs
        else:
            target_pairs = FOREX_PAIRS

        # Initialize news tool
        logger.info(f"Initializing news tool for pairs: {target_pairs}")
        news_tool = FinancialNewsScraperTool(api_key)

        # Get sentiment for each pair
        pair_sentiments = []
        all_scores = []

        for pair in target_pairs:
            logger.debug(f"Fetching headlines for {pair}")
            sentiment = get_headline_sentiment_for_pair(pair, news_tool)
            pair_sentiments.append(sentiment)
            if sentiment.headline_count > 0:
                all_scores.append(sentiment.sentiment_score)

        # Calculate overall market sentiment
        if all_scores:
            market_score = sum(all_scores) / len(all_scores)
            if market_score > 0.15:
                market_sentiment = "BULLISH"
            elif market_score < -0.15:
                market_sentiment = "BEARISH"
            else:
                market_sentiment = "NEUTRAL"
        else:
            market_sentiment = "NEUTRAL"
            market_score = 0.0

        return HeadlineSentimentResponse(
            pairs=pair_sentiments,
            market_sentiment=market_sentiment,
            market_sentiment_score=round(market_score, 3),
            timestamp=datetime.now().isoformat(),
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"News headlines error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch news: {type(e).__name__}: {str(e)}",
        )


@app.get("/news/headlines/{pair}", response_model=PairHeadlineSentiment, tags=["News"])
async def get_pair_headline_sentiment(pair: str):
    """
    Get bullish/bearish sentiment from news headlines for a specific forex pair.

    **Path Parameters:**
    - pair: Currency pair (e.g., EURUSD, GBPUSD, USDJPY)

    **Returns:**
    - Sentiment label: BULLISH / BEARISH / NEUTRAL
    - Sentiment score: -1 (very bearish) to +1 (very bullish)
    - Confidence level based on article count and consistency
    - Individual headlines with their sentiment
    """
    try:
        from app.forex.news_tool import FinancialNewsScraperTool

        pair_upper = pair.upper()
        if pair_upper not in FOREX_PAIRS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pair: {pair_upper}. Valid pairs are: {FOREX_PAIRS}",
            )

        # Get API key
        api_key = os.getenv("NEWSDATA_API_KEY")
        if not api_key:
            logger.error("NEWSDATA_API_KEY environment variable not set")
            raise HTTPException(
                status_code=500, detail="NEWSDATA_API_KEY environment variable not set"
            )

        # Initialize news tool and get sentiment
        logger.info(f"Fetching news headlines for {pair_upper}")
        news_tool = FinancialNewsScraperTool(api_key)
        sentiment = get_headline_sentiment_for_pair(pair_upper, news_tool)

        return sentiment

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"News headlines error for {pair}: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch news: {type(e).__name__}: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
