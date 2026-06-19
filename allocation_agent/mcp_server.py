"""
Forex MCP Server using Pathway Library
======================================

This MCP server exposes 5 forex analysis tools using Pathway's MCP framework.

Tools:
1. get_trades_summary - Trading performance summary
2. get_position_details - Current position details  
3. get_currency_regime - Market regime analysis (Hurst exponent)
4. get_currency_correlation - Correlation matrix between pairs
5. get_news_sentiment - News sentiment analysis

Run the server:
    python mcp_server.py

The server will be available at: http://localhost:8123/mcp/

Requires:
    - pip install pathway[xpack-llm]
    - PATHWAY_LICENSE_KEY environment variable
    - NEWSDATA_API_KEY for news sentiment (optional)
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List

import pathway as pw
from pathway.xpacks.llm.mcp_server import McpServable, McpServer, PathwayMcp
pw.set_license_key("A311E3-DB2893-6F1E5B-4576CE-8C11B3-V3")

from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

FOREX_PAIRS = ["EURINR", "GBPINR", "JPYINR", "EURUSD", "GBPUSD", "USDJPY"]
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BASE_DIR = os.path.dirname(__file__)

MCP_HOST = os.environ.get("MCP_HOST", "localhost")
MCP_PORT = int(os.environ.get("MCP_PORT", "8123"))


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class PairsRequestSchema(pw.Schema):
    """Schema for tools that require a list of forex pairs."""
    pairs: list[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_price_data(pair: str) -> pd.DataFrame:
    """Load price data for a currency pair."""
    csv_path = os.path.join(DATA_DIR, f"{pair}.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    
    df = pd.read_csv(csv_path)
    
    if 'ts_ms' in df.columns:
        df['date'] = pd.to_datetime(df['ts_ms'], unit='ms')
    elif 'timestamp' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp'])
    else:
        df['date'] = pd.to_datetime(df.iloc[:, 0])
    
    df = df.sort_values('date').reset_index(drop=True)
    return df


def load_positions() -> dict:
    """Load positions from JSON file."""
    positions_path = os.path.join(BASE_DIR, "positions.json")
    try:
        with open(positions_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_trades() -> dict:
    """Load trades from JSON file."""
    trades_path = os.path.join(BASE_DIR, "trades.json")
    try:
        with open(trades_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def calculate_hurst_exponent(prices: np.ndarray, max_lag: int = 20) -> float:
    """Calculate Hurst exponent using R/S analysis."""
    lags = range(2, min(max_lag, len(prices) // 4))
    tau = []
    rs_values = []
    
    for lag in lags:
        chunks = len(prices) // lag
        if chunks < 2:
            continue
            
        rs_chunk = []
        for i in range(chunks):
            chunk = prices[i*lag:(i+1)*lag]
            if len(chunk) < 2:
                continue
            
            returns = np.diff(chunk)
            if len(returns) == 0:
                continue
                
            mean_adj = returns - np.mean(returns)
            cumsum = np.cumsum(mean_adj)
            R = np.max(cumsum) - np.min(cumsum)
            S = np.std(returns, ddof=1)
            
            if S > 0:
                rs_chunk.append(R / S)
        
        if rs_chunk:
            tau.append(lag)
            rs_values.append(np.mean(rs_chunk))
    
    if len(tau) < 3:
        return 0.5
    
    log_tau = np.log(tau)
    log_rs = np.log(rs_values)
    slope, _ = np.polyfit(log_tau, log_rs, 1)
    
    return float(np.clip(slope, 0, 1))


# ============================================================================
# TOOL IMPLEMENTATIONS (Pure Functions - Return JSON)
# ============================================================================

def get_trades_summary_impl(pairs: List[str]) -> str:
    """
    Get trading performance summary including profit, max drawdown, win rate,
    Sharpe ratio, information ratio, turnover, average win/loss from trades history.
    
    Returns: JSON string with structured trade data.
    """
    trades_data = load_trades()
    
    if not trades_data:
        return json.dumps({"error": True, "message": "trades.json not found. No trade history available."})
    
    valid_pairs = [p.upper() for p in pairs if p.upper() in FOREX_PAIRS]
    if not valid_pairs:
        return json.dumps({"error": True, "message": f"No valid pairs provided. Valid pairs are: {FOREX_PAIRS}"})
    
    results = {}
    for pair in valid_pairs:
        if pair in trades_data:
            data = trades_data[pair]
            results[pair] = {
                "total_trades": data.get('total_trades', 0),
                "winning_trades": data.get('winning_trades', 0),
                "losing_trades": data.get('losing_trades', 0),
                "win_rate": round(data.get('win_rate', 0) * 100, 1),
                "total_profit_pct": round(data.get('total_profit_pct', 0), 2),
                "max_drawdown_pct": round(data.get('max_drawdown_pct', 0), 2),
                "sharpe_ratio": round(data.get('sharpe_ratio', 0), 2),
                "information_ratio": round(data.get('information_ratio', 0), 2),
                "profit_factor": round(data.get('profit_factor', 0), 2),
                "avg_win_pct": round(data.get('avg_win_pct', 0), 2),
                "avg_loss_pct": round(data.get('avg_loss_pct', 0), 2),
                "largest_win_pct": round(data.get('largest_win_pct', 0), 2),
                "largest_loss_pct": round(data.get('largest_loss_pct', 0), 2),
                "avg_holding_period_days": round(data.get('avg_holding_period_days', 0), 1),
                "recent_trades": [
                    {
                        "date": trade.get('date', 'N/A'),
                        "side": trade.get('side', 'N/A'),
                        "entry": trade.get('entry', 0),
                        "exit": trade.get('exit', 0),
                        "pnl_pct": round(trade.get('pnl_pct', 0), 2),
                        "result": "WIN" if trade.get('pnl_pct', 0) > 0 else "LOSS"
                    }
                    for trade in data.get('recent_trades', [])[:5]
                ]
            }
        else:
            results[pair] = {"error": True, "message": "No trade data available for this pair"}
    
    return json.dumps({"error": False, "data": results})


def get_position_details_impl(pairs: List[str]) -> str:
    """
    Get current position details including entry price, unrealized P&L,
    stop loss, take profit levels, and model confidence for each pair.
    
    Returns: JSON string with structured position data.
    """
    positions_data = load_positions()
    
    if not positions_data:
        return json.dumps({"error": True, "message": "positions.json not found. No position data available."})
    
    valid_pairs = [p.upper() for p in pairs if p.upper() in FOREX_PAIRS]
    if not valid_pairs:
        return json.dumps({"error": True, "message": f"No valid pairs provided. Valid pairs are: {FOREX_PAIRS}"})
    
    results = {}
    for pair in valid_pairs:
        if pair in positions_data:
            data = positions_data[pair]
            pos = data.get('current_position', 'flat')
            
            model_conf = data.get('model_confidence', 0)
            if isinstance(model_conf, str):
                try:
                    model_conf = float(model_conf)
                except:
                    model_conf = 0
            
            results[pair] = {
                "position": pos.upper() if pos != "flat" else "FLAT",
                "entry_date": data.get('entry_date', data.get('last_exit_date', 'N/A')),
                "entry_price": data.get('entry_price', data.get('last_exit_price', 0)),
                "current_price": data.get('current_price', 0),
                "unrealized_pnl_pct": round(data.get('unrealized_pnl_pct', data.get('last_trade_pnl_pct', 0)), 2),
                "position_size": data.get('position_size', 0),
                "stop_loss": data.get('stop_loss', 0),
                "take_profit": data.get('take_profit', 0),
                "risk_reward_ratio": round(data.get('risk_reward_ratio', 0), 2),
                "days_held": data.get('days_held', data.get('days_since_last_trade', 0)),
                "model_confidence": round(model_conf * 100, 0),
                "signal_strength": str(data.get('signal_strength', 'N/A')).upper(),
                "entry_reason": data.get('entry_reason', data.get('reason', 'N/A')),
                "pending_signal": data.get('pending_signal', None)
            }
        else:
            results[pair] = {"error": True, "message": "No position data available"}
    
    # Add portfolio summary if available
    portfolio_summary = None
    if "portfolio_summary" in positions_data and len(valid_pairs) > 1:
        ps = positions_data["portfolio_summary"]
        portfolio_summary = {
            "total_open_positions": ps.get('total_open_positions', 0),
            "total_exposure_long": ps.get('total_exposure_long', 0),
            "total_exposure_short": ps.get('total_exposure_short', 0),
            "net_exposure": ps.get('net_exposure', 0),
            "total_unrealized_pnl_pct": round(ps.get('total_unrealized_pnl_pct', 0), 2),
            "portfolio_heat": round(ps.get('portfolio_heat', 0) * 100, 0),
            "max_correlation_risk": ps.get('max_correlation_risk', 'N/A')
        }
    
    return json.dumps({"error": False, "data": results, "portfolio_summary": portfolio_summary})


def get_currency_regime_impl(pairs: List[str]) -> str:
    """
    Analyze currency regime including bull/bear market, volatility level,
    and trend type (momentum vs mean reversion) using Hurst exponent analysis.
    
    Returns: JSON string with structured regime data.
    """
    valid_pairs = [p.upper() for p in pairs if p.upper() in FOREX_PAIRS]
    if not valid_pairs:
        return json.dumps({"error": True, "message": f"No valid pairs provided. Valid pairs are: {FOREX_PAIRS}"})
    
    results = {}
    
    for pair in valid_pairs:
        df = load_price_data(pair)
        
        if df.empty:
            results[pair] = {"error": True, "message": f"Data file not found for {pair}"}
            continue
        
        try:
            prices = df['close'].values
            prices = prices[-252:] if len(prices) > 252 else prices
            
            returns = np.diff(np.log(prices)) * 100
            recent_prices = prices[-60:] if len(prices) >= 60 else prices
            price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
            
            # Determine trend
            if price_change > 2:
                trend = "BULLISH"
            elif price_change < -2:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"
            
            # Calculate volatility
            volatility = float(np.std(returns) * np.sqrt(252))
            if volatility > 15:
                vol_level = "HIGH"
            elif volatility > 8:
                vol_level = "MODERATE"
            else:
                vol_level = "LOW"
            
            # Calculate Hurst exponent
            hurst = calculate_hurst_exponent(prices)
            
            if hurst > 0.6:
                trend_type = "TRENDING"
                strategy_recommendation = "Trend-following strategies recommended"
            elif hurst < 0.4:
                trend_type = "MEAN_REVERTING"
                strategy_recommendation = "Mean reversion strategies recommended"
            else:
                trend_type = "RANDOM_WALK"
                strategy_recommendation = "Mixed approach or reduced position size recommended"
            
            # ATR calculation
            atr_14 = 0
            atr_pct = 0
            if 'high' in df.columns and 'low' in df.columns:
                df['tr'] = np.maximum(
                    df['high'] - df['low'],
                    np.maximum(
                        abs(df['high'] - df['close'].shift(1)),
                        abs(df['low'] - df['close'].shift(1))
                    )
                )
                atr_14 = float(df['tr'].tail(14).mean())
                atr_pct = (atr_14 / prices[-1]) * 100
            
            results[pair] = {
                "current_price": round(float(prices[-1]), 5),
                "trend": {
                    "direction": trend,
                    "price_change_60d_pct": round(price_change, 2)
                },
                "volatility": {
                    "level": vol_level,
                    "annualized_pct": round(volatility, 2),
                    "atr_14": round(atr_14, 5),
                    "atr_pct": round(atr_pct, 2)
                },
                "market_character": {
                    "type": trend_type,
                    "hurst_exponent": round(hurst, 3),
                    "strategy_recommendation": strategy_recommendation
                },
                "price_stats_60d": {
                    "high": round(float(np.max(recent_prices)), 5),
                    "low": round(float(np.min(recent_prices)), 5),
                    "range_pct": round(((np.max(recent_prices) - np.min(recent_prices)) / np.min(recent_prices) * 100), 2)
                }
            }
            
        except Exception as e:
            results[pair] = {"error": True, "message": f"Error analyzing regime: {str(e)}"}
    
    return json.dumps({"error": False, "data": results})


def get_currency_correlation_impl(pairs: List[str]) -> str:
    """
    Calculate and display correlation matrix between forex pairs.
    Helps understand portfolio diversification and risk.
    
    Returns: JSON string with correlation matrix and insights.
    """
    valid_pairs = [p.upper() for p in pairs if p.upper() in FOREX_PAIRS]
    if len(valid_pairs) < 2:
        return json.dumps({"error": True, "message": "Need at least 2 valid pairs to calculate correlation."})
    
    returns_dict = {}
    
    for pair in valid_pairs:
        df = load_price_data(pair)
        if not df.empty:
            df['returns'] = np.log(df['close'] / df['close'].shift(1))
            returns_dict[pair] = df.set_index('date')['returns']
    
    if len(returns_dict) < 2:
        return json.dumps({"error": True, "message": "Could not load sufficient data for correlation analysis."})
    
    returns_df = pd.DataFrame(returns_dict)
    returns_df = returns_df.dropna()
    
    corr_matrix = returns_df.corr()
    
    # Build correlation matrix as nested dict
    correlation_data = {}
    for p1 in corr_matrix.columns:
        correlation_data[p1] = {}
        for p2 in corr_matrix.columns:
            correlation_data[p1][p2] = round(float(corr_matrix.loc[p1, p2]), 3)
    
    # Find high and low correlations
    pairs_list = list(corr_matrix.columns)
    high_correlations = []
    negative_correlations = []
    
    for i, p1 in enumerate(pairs_list):
        for j, p2 in enumerate(pairs_list):
            if i < j:
                val = float(corr_matrix.loc[p1, p2])
                if val > 0.7:
                    high_correlations.append({
                        "pair1": p1,
                        "pair2": p2,
                        "correlation": round(val, 3),
                        "risk": "May increase portfolio risk"
                    })
                elif val < -0.3:
                    negative_correlations.append({
                        "pair1": p1,
                        "pair2": p2,
                        "correlation": round(val, 3),
                        "benefit": "Good for diversification"
                    })
    
    return json.dumps({
        "error": False,
        "data": {
            "correlation_matrix": correlation_data,
            "high_correlations": high_correlations,
            "negative_correlations": negative_correlations,
            "data_period": {
                "observations": len(returns_df),
                "start_date": returns_df.index.min().strftime('%Y-%m-%d'),
                "end_date": returns_df.index.max().strftime('%Y-%m-%d')
            }
        }
    })


def get_news_sentiment_impl(pairs: List[str]) -> str:
    """
    Get news sentiment analysis for forex pairs using FinancialNewsScraperTool.
    Summarizes recent news, explains potential currency movements, and provides sentiment scores.
    
    Returns: JSON string with structured sentiment data.
    """
    valid_pairs = [p.upper() for p in pairs if p.upper() in FOREX_PAIRS]
    if not valid_pairs:
        return json.dumps({"error": True, "message": f"No valid pairs provided. Valid pairs are: {FOREX_PAIRS}"})
    
    newsdata_api_key = os.environ.get('NEWSDATA_API_KEY', '')
    
    if not newsdata_api_key:
        return json.dumps({
            "error": True,
            "message": "NEWSDATA_API_KEY environment variable is not set. Get an API key from https://newsdata.io/"
        })
    
    try:
        from news_tool import FinancialNewsScraperTool
        news_tool = FinancialNewsScraperTool(newsdata_api_key)
    except Exception as e:
        return json.dumps({
            "error": True,
            "message": f"Failed to initialize news tool: {str(e)}"
        })
    
    pair_queries = {
        'EURUSD': 'euro dollar currency',
        'GBPUSD': 'pound dollar sterling currency',
        'USDJPY': 'dollar yen japan currency',
        'EURINR': 'euro rupee india currency',
        'GBPINR': 'pound rupee india currency',
        'JPYINR': 'yen rupee india currency',
    }
    
    results = {}
    
    for pair in valid_pairs:
        query = pair_queries.get(pair, f"{pair[:3]} {pair[3:]} currency")
        
        try:
            result = news_tool.search_news_global(query, max_articles=5, verbose=False)
            
            if not result.get('success') or not result.get('articles'):
                results[pair] = {
                    "error": True,
                    "message": f"No news articles found for {pair}"
                }
                continue
            
            articles = result['articles']
            scores = [a.get('sentiment_score', 0) for a in articles]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            # Determine sentiment label
            if avg_score > 0.1:
                sentiment_label = "BULLISH"
            elif avg_score < -0.1:
                sentiment_label = "BEARISH"
            else:
                sentiment_label = "NEUTRAL"
            
            results[pair] = {
                "sentiment": sentiment_label,
                "sentiment_score": round(avg_score, 3),
                "article_count": len(articles),
                "articles": [
                    {
                        "title": article.get('title', 'No title'),
                        "source": article.get('source', 'Unknown'),
                        "sentiment": article.get('sentiment', 'neutral'),
                        "sentiment_score": round(article.get('sentiment_score', 0), 3),
                        "url": article.get('url', '')
                    }
                    for article in articles[:5]
                ]
            }
            
        except Exception as e:
            results[pair] = {
                "error": True,
                "message": f"Failed to fetch news: {str(e)}"
            }
    
    return json.dumps({
        "error": False,
        "data": results,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    })


# ============================================================================
# PATHWAY MCP SERVABLE - All 5 tools in one class
# ============================================================================

class ForexTools(McpServable):
    """
    Forex analysis tools exposed via Pathway MCP Server.
    
    Tools:
    - get_trades_summary: Trading performance summary
    - get_position_details: Current position details
    - get_currency_regime: Market regime analysis
    - get_currency_correlation: Correlation matrix
    - get_news_sentiment: News sentiment analysis
    """
    
    def get_trades_summary(self, input_table: pw.Table) -> pw.Table:
        """
        Get trading performance summary including profit, max drawdown, win rate, 
        Sharpe ratio, information ratio, turnover, average win/loss from trades history.
        """
        @pw.udf
        def _process(pairs: list) -> str:
            return get_trades_summary_impl(pairs or FOREX_PAIRS)
        
        return input_table.select(result=_process(pw.this.pairs))
    
    def get_position_details(self, input_table: pw.Table) -> pw.Table:
        """
        Get current position details including entry price, unrealized P&L,
        stop loss, take profit levels, and model confidence for each pair.
        """
        @pw.udf
        def _process(pairs: list) -> str:
            return get_position_details_impl(pairs or FOREX_PAIRS)
        
        return input_table.select(result=_process(pw.this.pairs))
    
    def get_currency_regime(self, input_table: pw.Table) -> pw.Table:
        """
        Analyze currency regime including bull/bear market, volatility level,
        and trend type (momentum vs mean reversion) using Hurst exponent analysis.
        """
        @pw.udf
        def _process(pairs: list) -> str:
            return get_currency_regime_impl(pairs or FOREX_PAIRS)
        
        return input_table.select(result=_process(pw.this.pairs))
    
    def get_currency_correlation(self, input_table: pw.Table) -> pw.Table:
        """
        Calculate and display correlation matrix between forex pairs.
        Helps understand portfolio diversification and risk.
        """
        @pw.udf
        def _process(pairs: list) -> str:
            return get_currency_correlation_impl(pairs or FOREX_PAIRS)
        
        return input_table.select(result=_process(pw.this.pairs))
    
    def get_news_sentiment(self, input_table: pw.Table) -> pw.Table:
        """
        Get news sentiment analysis for forex pairs.
        Summarizes recent news, explains potential currency movements, and provides sentiment scores.
        """
        @pw.udf
        def _process(pairs: list) -> str:
            return get_news_sentiment_impl(pairs or FOREX_PAIRS)
        
        return input_table.select(result=_process(pw.this.pairs))
    
    def register_mcp(self, server: McpServer):
        """Register all tools with the MCP server."""
        
        server.tool(
            "get_trades_summary",
            request_handler=self.get_trades_summary,
            schema=PairsRequestSchema,
        )
        
        server.tool(
            "get_position_details",
            request_handler=self.get_position_details,
            schema=PairsRequestSchema,
        )
        
        server.tool(
            "get_currency_regime",
            request_handler=self.get_currency_regime,
            schema=PairsRequestSchema,
        )
        
        server.tool(
            "get_currency_correlation",
            request_handler=self.get_currency_correlation,
            schema=PairsRequestSchema,
        )
        
        server.tool(
            "get_news_sentiment",
            request_handler=self.get_news_sentiment,
            schema=PairsRequestSchema,
        )


# ============================================================================
# MAIN - Start the Pathway MCP Server
# ============================================================================

if __name__ == "__main__":
    print(f"Starting Forex MCP Server on http://{MCP_HOST}:{MCP_PORT}/mcp/")
    print(f"Available tools: get_trades_summary, get_position_details, get_currency_regime, get_currency_correlation, get_news_sentiment")
    print(f"Valid forex pairs: {FOREX_PAIRS}")
    
    # Create tool instance
    forex_tools = ForexTools()
    
    # Create and configure Pathway MCP Server
    pathway_mcp_server = PathwayMcp(
        name="Forex Analysis MCP Server",
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        serve=[forex_tools],
    )
    
    # Run Pathway (this blocks and runs the server)
    pw.run(
        monitoring_level=pw.MonitoringLevel.NONE,
        terminate_on_error=False,
    )
