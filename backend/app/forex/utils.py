import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from app.forex.schemas import HeadlineNews, PairHeadlineSentiment

logger = logging.getLogger(__name__)

# Base directory for forex data files (positions.json, trades.json, data/, etc.)
FOREX_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "forex")

FOREX_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "EURINR", "GBPINR", "JPYINR"]

# Pair to search query mapping for more relevant results
PAIR_SEARCH_QUERIES = {
    "EURUSD": "EUR USD euro dollar forex ECB Federal Reserve",
    "GBPUSD": "GBP USD pound dollar forex Bank of England Fed",
    "USDJPY": "USD JPY dollar yen forex Bank of Japan Fed BOJ",
    "EURINR": "EUR INR euro rupee forex ECB RBI India",
    "GBPINR": "GBP INR pound rupee forex BOE RBI India",
    "JPYINR": "JPY INR yen rupee forex BOJ RBI India",
    "USDINR": "USD INR dollar rupee forex Fed RBI India",
}


def load_price_data(pair: str, data_dir: str = "data") -> pd.DataFrame:
    """Load price data for a currency pair"""
    csv_path = os.path.join(FOREX_DATA_DIR, data_dir, f"{pair}.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
        if "ts_ms" in df.columns:
            df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms")
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error loading price data for {pair}: {e}")
        return pd.DataFrame()


def calculate_volatility(returns: pd.Series, window: int = 20) -> float:
    """Calculate annualized volatility"""
    if len(returns) < window:
        return 0.0
    vol = returns.tail(window).std() * np.sqrt(252)
    return float(vol) if not np.isnan(vol) else 0.0


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Calculate Average True Range"""
    if len(df) < period:
        return 0.0

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]

    return float(atr) if not np.isnan(atr) else 0.0


def calculate_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Value at Risk"""
    if len(returns) < 30:
        return 0.0
    var = np.percentile(returns.dropna(), (1 - confidence) * 100)
    return float(var) if not np.isnan(var) else 0.0


# Global MongoDB Manager instance (lazy initialized)
_mongo_manager = None


def get_mongo_manager():
    """Get or create singleton MongoDB manager"""
    global _mongo_manager
    if _mongo_manager is None:
        try:
            # Load config to get DB settings
            import yaml

            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.environ.get(
                "FOREX_CONFIG_PATH", os.path.join(base_dir, "config.yaml")
            )

            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
            else:
                config = {}

            from app.forex.db import MongoDBManager

            _mongo_manager = MongoDBManager(config)
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB manager: {e}")
            return None

    return _mongo_manager


def load_positions() -> Dict:
    """
    Load positions from MongoDB.
    Falls back to JSON file if MongoDB is unavailable or empty (and migrates if needed).
    """
    positions_path = os.path.join(FOREX_DATA_DIR, "positions.json")
    json_positions = {}

    # helper to load local JSON
    if os.path.exists(positions_path):
        try:
            with open(positions_path, "r") as f:
                json_positions = json.load(f)
        except Exception as e:
            logger.error(f"Error reading positions.json: {e}")

    manager = get_mongo_manager()
    if False and manager and manager.is_connected():
        # Try to load from Mongo
        mongo_positions = manager.load_positions()

        # MIGRATION CHECK: If Mongo is empty but we have local JSON, migrate it
        if not mongo_positions and json_positions:
            logger.info("Migrating positions from JSON to MongoDB...")
            manager.save_positions(json_positions)
            return json_positions

        # If we have data in Mongo, use it.
        # Note: If Mongo returns empty and JSON is empty, we return empty.
        # If Mongo returns empty (and migration didn't happen above), it means we really have no positions.
        if mongo_positions:
            return mongo_positions

    # Fallback to local JSON if Mongo is down
    return json_positions


def save_positions(positions: Dict):
    """
    Save positions to MongoDB.
    Also saves to JSON file for backup/backward compatibility.
    """
    # 1. Save to MongoDB
    manager = get_mongo_manager()
    if False and manager and manager.is_connected():
        manager.save_positions(positions)

    # 2. Save to JSON (Backup)
    positions_path = os.path.join(FOREX_DATA_DIR, "positions.json")
    try:
        with open(positions_path, "w") as f:
            json.dump(positions, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving positions.json: {e}")


def load_trades() -> Dict:
    """
    Load trades from MongoDB.
    Falls back to JSON file if MongoDB is unavailable or empty (and migrates if needed).
    """
    trades_path = os.path.join(FOREX_DATA_DIR, "trades.json")
    json_trades = {}

    # helper to load local JSON
    if os.path.exists(trades_path):
        try:
            with open(trades_path, "r") as f:
                json_trades = json.load(f)
        except Exception as e:
            logger.error(f"Error reading trades.json: {e}")

    manager = get_mongo_manager()
    if False and manager and manager.is_connected():
        mongo_trades = manager.load_trades()

        # MIGRATION CHECK
        if not mongo_trades and json_trades:
            logger.info("Migrating trades from JSON to MongoDB...")
            manager.save_trades(json_trades)
            return json_trades

        if mongo_trades:
            return mongo_trades

    return json_trades


def save_trades(trades: Dict):
    """
    Save trades to MongoDB.
    Also saves to JSON file for backup/backward compatibility.
    """
    # 1. Save to MongoDB
    manager = get_mongo_manager()
    if False and manager and manager.is_connected():
        manager.save_trades(trades)

    # 2. Save to JSON (Backup)
    trades_path = os.path.join(FOREX_DATA_DIR, "trades.json")
    try:
        with open(trades_path, "w") as f:
            json.dump(trades, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving trades.json: {e}")


def _append_to_trade_history_csv(
    pair: str,
    entry_date: str,
    entry_price: float,
    exit_date: str,
    exit_price: float,
    trade_type: str,
    position_size: float,
    profit: float,
    pnl_pct: float,
    holding_days: int,
):
    """Append a trade record to trade_history.csv"""
    csv_path = os.path.join(FOREX_DATA_DIR, "trade_history.csv")

    # Read existing data to get capital
    capital_before = 100000.0
    try:
        existing_df = pd.read_csv(csv_path)
        if len(existing_df) > 0 and "Capital_After" in existing_df.columns:
            capital_before = float(existing_df["Capital_After"].iloc[-1])
    except:
        pass

    capital_after = capital_before + profit

    # Create new row
    new_row = {
        "Entry_Date": entry_date,
        "Entry_Price": entry_price,
        "Exit_Date": exit_date,
        "Exit_Price": exit_price,
        "Type": trade_type,
        "USD_Amount": position_size,
        "Profit": profit,
        "Profit_Pct": pnl_pct,
        "Holding_Days": holding_days,
        "Capital_Before": capital_before,
        "Capital_After": capital_after,
        "Pair": pair,  # Add pair column
    }

    # Append to CSV
    new_df = pd.DataFrame([new_row])

    if os.path.exists(csv_path):
        new_df.to_csv(csv_path, mode="a", header=False, index=False)
    else:
        new_df.to_csv(csv_path, index=False)

    logger.info(
        f"Trade recorded in trade_history.csv: {pair} {trade_type} P&L: {pnl_pct:.2f}%"
    )


def record_closed_trade(
    trades_data: Dict,
    pair: str,
    prev_position: Dict,
    exit_price: float,
    exit_time: datetime,
):
    """Helper to record a closed trade in trades.json and trade_history.csv"""
    if pair not in trades_data:
        trades_data[pair] = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_profit_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "recent_trades": [],
        }

    entry_price = prev_position.get("entry_price", exit_price)
    entry_date = prev_position.get("entry_date", exit_time.strftime("%Y-%m-%d"))
    direction = prev_position.get("current_position", "long")
    position_size = prev_position.get("position_size", 10000)

    # Calculate P&L
    if direction == "long":
        pnl_pct = (
            ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        )
        profit = (exit_price - entry_price) * position_size
    else:
        pnl_pct = (
            ((entry_price - exit_price) / entry_price) * 100 if entry_price > 0 else 0
        )
        profit = (entry_price - exit_price) * position_size

    # Calculate holding days
    try:
        entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
        holding_days = (exit_time - entry_dt).days
    except:
        holding_days = 0

    trade_record = {
        "date": exit_time.strftime("%Y-%m-%d"),
        "side": direction,
        "entry": round(entry_price, 5),
        "exit": round(exit_price, 5),
        "pnl_pct": round(pnl_pct, 4),
    }

    # Update trades.json stats
    trades_data[pair]["total_trades"] += 1
    trades_data[pair]["total_profit_pct"] += pnl_pct
    if pnl_pct > 0:
        trades_data[pair]["winning_trades"] += 1
    else:
        trades_data[pair]["losing_trades"] += 1

    total = trades_data[pair]["total_trades"]
    trades_data[pair]["win_rate"] = (
        trades_data[pair]["winning_trades"] / total if total > 0 else 0
    )

    trades_data[pair]["recent_trades"].insert(0, trade_record)
    trades_data[pair]["recent_trades"] = trades_data[pair]["recent_trades"][:10]

    # Calculate Sharpe ratio from recent trades
    recent_pnls = [t["pnl_pct"] for t in trades_data[pair]["recent_trades"]]
    if len(recent_pnls) > 1:
        avg_pnl = np.mean(recent_pnls)
        std_pnl = np.std(recent_pnls)
        if std_pnl > 0:
            trades_data[pair]['recent_sharpe_ratio'] = round((avg_pnl / std_pnl) * np.sqrt(252), 4)
    
    # Append to trade_history.csv
    _append_to_trade_history_csv(
        pair=pair,
        entry_date=entry_date,
        entry_price=entry_price,
        exit_date=exit_time.strftime("%Y-%m-%d"),
        exit_price=exit_price,
        trade_type=f"{direction.upper()} (Manual)",
        position_size=position_size,
        profit=profit,
        pnl_pct=pnl_pct,
        holding_days=holding_days,
    )


def update_unrealized_pnl(positions: Dict):
    """Update unrealized P&L for all open positions based on current prices"""
    pairs = FOREX_PAIRS

    for pair in pairs:
        pos = positions.get(pair, {})
        position_type = pos.get("current_position")

        if position_type in ["long", "short"]:
            df = load_price_data(pair)
            if not df.empty:
                current_price = float(df["close"].iloc[-1])
                entry_price = pos.get("entry_price", current_price)

                if position_type == "long":
                    unrealized_pnl_pct = (
                        ((current_price - entry_price) / entry_price) * 100
                        if entry_price > 0
                        else 0
                    )
                else:
                    unrealized_pnl_pct = (
                        ((entry_price - current_price) / entry_price) * 100
                        if entry_price > 0
                        else 0
                    )

                positions[pair]["current_price"] = round(current_price, 5)
                positions[pair]["unrealized_pnl_pct"] = round(unrealized_pnl_pct, 4)

                # Update days held
                entry_date = pos.get("entry_date")
                if entry_date:
                    try:
                        entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
                        positions[pair]["days_held"] = (datetime.now() - entry_dt).days
                    except:
                        pass


def update_portfolio_summary(positions: Dict):
    """Helper to update comprehensive portfolio summary"""
    pairs = FOREX_PAIRS

    total_long = 0
    total_short = 0
    total_unrealized_pnl = 0.0
    open_positions = 0

    for pair in pairs:
        pos = positions.get(pair, {})
        position_type = pos.get("current_position")
        position_size = pos.get("position_size", 0)

        if position_type == "long":
            total_long += position_size
            open_positions += 1
            total_unrealized_pnl += pos.get("unrealized_pnl_pct", 0)
        elif position_type == "short":
            total_short += position_size
            open_positions += 1
            total_unrealized_pnl += pos.get("unrealized_pnl_pct", 0)

    portfolio_capital = 100000  # Default capital
    total_exposure = total_long + total_short

    positions["portfolio_summary"] = {
        "total_open_positions": open_positions,
        "total_exposure_long": total_long,
        "total_exposure_short": total_short,
        "net_exposure": total_long - total_short,
        "total_unrealized_pnl_pct": round(total_unrealized_pnl, 4),
        "portfolio_heat": round(total_exposure / portfolio_capital, 4)
        if portfolio_capital > 0
        else 0,
        "long_exposure_pct": round((total_long / portfolio_capital) * 100, 2)
        if portfolio_capital > 0
        else 0,
        "short_exposure_pct": round((total_short / portfolio_capital) * 100, 2)
        if portfolio_capital > 0
        else 0,
        "max_correlation_risk": "N/A",
        "last_updated": datetime.now().isoformat(),
    }


def get_headline_sentiment_for_pair(pair: str, news_tool) -> PairHeadlineSentiment:
    """Get headline sentiment for a single pair"""
    query = PAIR_SEARCH_QUERIES.get(pair, f"{pair[:3]} {pair[3:]} forex currency")

    try:
        # Use global search for faster headline-only fetching
        result = news_tool.search_news_global(query, max_articles=10, verbose=False)

        if not result.get("success") or not result.get("articles"):
            return PairHeadlineSentiment(
                pair=pair,
                overall_sentiment="NEUTRAL",
                sentiment_score=0.0,
                confidence="low",
                headline_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                headlines=[],
            )

        articles = result["articles"]
        headlines = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for article in articles:
            sentiment = article.get("sentiment", "neutral")
            score = article.get("sentiment_score", 0.0)

            if sentiment == "positive":
                positive_count += 1
            elif sentiment == "negative":
                negative_count += 1
            else:
                neutral_count += 1

            headlines.append(
                HeadlineNews(
                    title=article.get("title", ""),
                    source=article.get("source", "Unknown"),
                    sentiment=sentiment,
                    sentiment_score=score,
                    url=article.get("url"),
                    published_date=article.get("published_date"),
                )
            )

        # Calculate overall sentiment
        total_count = len(articles)
        if total_count == 0:
            avg_score = 0.0
        else:
            avg_score = sum(h.sentiment_score for h in headlines) / total_count

        # Determine overall sentiment label
        if avg_score > 0.15:
            overall_sentiment = "BULLISH"
        elif avg_score < -0.15:
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"

        # Determine confidence based on article count and sentiment consistency
        if total_count >= 5:
            dominant_count = max(positive_count, negative_count, neutral_count)
            if dominant_count / total_count > 0.6:
                confidence = "high"
            elif dominant_count / total_count > 0.4:
                confidence = "medium"
            else:
                confidence = "low"
        elif total_count >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return PairHeadlineSentiment(
            pair=pair,
            overall_sentiment=overall_sentiment,
            sentiment_score=round(avg_score, 3),
            confidence=confidence,
            headline_count=total_count,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            headlines=headlines,
        )

    except Exception as e:
        logger.error(f"Error getting headlines for {pair}: {e}")
        return PairHeadlineSentiment(
            pair=pair,
            overall_sentiment="NEUTRAL",
            sentiment_score=0.0,
            confidence="low",
            headline_count=0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            headlines=[],
        )
