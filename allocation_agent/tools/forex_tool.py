"""
Forex Tool - MCP Client for Forex Pipeline (Pathway MCP)
=========================================================

Connects to the Forex MCP Server (Pathway) using streamable-http transport.

Server: http://localhost:8123/mcp/

Response Structure from get_currency_regime:
{
    "error": False,
    "data": {
        "EURINR": {
            "current_price": 89.12345,
            "trend": {
                "direction": "BULLISH" | "BEARISH" | "SIDEWAYS",
                "price_change_60d_pct": 2.5
            },
            "volatility": {
                "level": "HIGH" | "MODERATE" | "LOW",
                "annualized_pct": 12.5,
                "atr_14": 0.5,
                "atr_pct": 0.6
            },
            "market_character": {
                "type": "TRENDING" | "MEAN_REVERTING" | "RANDOM_WALK",
                "hurst_exponent": 0.65,
                "strategy_recommendation": "..."
            },
            "price_stats_60d": {...}
        },
        ...
    }
}
"""
import asyncio
import json
from typing import Dict, List
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

# Configuration
FOREX_SERVER_URL = "http://10.42.14.151:8123/mcp/"
CURRENCY_PAIRS = ["EURINR", "GBPINR", "JPYINR", "EURUSD", "GBPUSD", "USDJPY"]

async def _call_remote_tool(session, tool_name: str, arguments: Dict) -> any:
    """
    Helper to call a remote tool on the MCP server.
    """
    try:
        result = await session.call_tool(tool_name, arguments=arguments)
        if result.content and hasattr(result.content[0], 'text'):
             return result.content[0].text
        return result
    except Exception as e:
        print(f"Error calling {tool_name}: {e}")
        return None

async def get_forex_data_async() -> Dict:
    """
    Fetches regime and trade data for all pairs.
    Returns raw data for further processing.
    """
    try:
        async with streamablehttp_client(FOREX_SERVER_URL) as (read, write, get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call get_currency_regime for all pairs
                regime_json = await _call_remote_tool(
                    session, 
                    "get_currency_regime", 
                    {"pairs": CURRENCY_PAIRS}
                )
                
                # Call get_trades_summary for Sharpe ratio
                trades_json = await _call_remote_tool(
                    session, 
                    "get_trades_summary", 
                    {"pairs": CURRENCY_PAIRS}
                )
                
                # Parse JSON responses
                regime_data = None
                trades_data = None
                
                if regime_json:
                    try:
                        regime_data = json.loads(regime_json) if isinstance(regime_json, str) else regime_json
                    except json.JSONDecodeError as e:
                        print(f"Error parsing regime JSON: {e}")
                
                if trades_json:
                    try:
                        trades_data = json.loads(trades_json) if isinstance(trades_json, str) else trades_json
                    except json.JSONDecodeError as e:
                        print(f"Error parsing trades JSON: {e}")
                
                return {
                    "regime": regime_data,
                    "trades": trades_data,
                    "success": True
                }
                
    except Exception as e:
        print(f"Failed to connect to Forex MCP Server: {e}")
        return {"success": False, "error": str(e)}

async def get_forex_opportunity_index_async() -> float:
    """
    Connects to MCP Server and calculates the Net Conviction Score.
    
    Logic:
    1. For each pair, check trend direction (from regime -> trend -> direction)
    2. Check volatility (from regime -> volatility -> level, atr_pct)
    3. Weight by Sharpe ratio (from trades -> sharpe_ratio)
    4. Average to get overall opportunity index
    """
    data = await get_forex_data_async()
    
    if not data.get("success"):
        return 0.0  # Fallback
    
    regime_response = data.get("regime", {})
    trades_response = data.get("trades", {})
    
    # Check for errors in response
    if regime_response.get("error"):
        print(f"Regime error: {regime_response.get('message')}")
        return 0.0
    
    regime_data = regime_response.get("data", {})
    trades_data = trades_response.get("data", {}) if trades_response else {}
    
    if not regime_data:
        return 0.0
    
    total_score = 0.0
    valid_pairs = 0
    
    for pair in CURRENCY_PAIRS:
        pair_regime = regime_data.get(pair, {})
        pair_trades = trades_data.get(pair, {})
        
        # Skip if error for this pair
        if pair_regime.get("error"):
            continue
        
        # 1. Get trend direction: regime -> trend -> direction
        trend_info = pair_regime.get("trend", {})
        trend_direction = trend_info.get("direction", "SIDEWAYS")
        
        # 2. Get volatility: regime -> volatility -> level, atr_pct
        vol_info = pair_regime.get("volatility", {})
        vol_level = vol_info.get("level", "MODERATE")
        atr_pct = vol_info.get("atr_pct", 0)
        
        # Skip if volatility is too high (> 3% ATR)
        if vol_level == "HIGH" and atr_pct > 3.0:
            continue
        
        # 3. Get Sharpe ratio: trades -> sharpe_ratio
        sharpe = 0
        if pair_trades and not pair_trades.get("error"):
            sharpe = pair_trades.get("sharpe_ratio", 0)
        
        # 4. Calculate quality score based on Sharpe
        quality = 0.1  # Base
        if sharpe > 1.5:
            quality = 1.0
        elif sharpe > 0.5:
            quality = 0.5
        elif sharpe > 0:
            quality = 0.3
        
        # 5. Direction check (both BULLISH and BEARISH are opportunities)
        if trend_direction in ["BULLISH", "BEARISH"]:
            score = quality
        else:  # SIDEWAYS
            score = 0.0
        
        total_score += score
        valid_pairs += 1
    
    if valid_pairs == 0:
        return 0.0
    
    final_index = total_score / len(CURRENCY_PAIRS)
    return round(min(final_index, 1.0), 3)  # Cap at 1.0
