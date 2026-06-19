"""
Test script to verify MCP Client-Server connections.
Tests Forex (Pathway MCP) pipeline.
"""
import asyncio
import json
from orchestrator.tools import forex_tool, bonds_tool

async def test_forex_connection():
    """Test connection to Forex MCP Server (Pathway)."""
    print("\n" + "="*60)
    print("TESTING FOREX MCP CONNECTION (Pathway)")
    print(f"Server URL: {forex_tool.FOREX_SERVER_URL}")
    print(f"Currency Pairs: {forex_tool.CURRENCY_PAIRS}")
    print("="*60)
    
    try:
        # Test raw data fetch
        data = await forex_tool.get_forex_data_async()
        
        if data.get("success"):
            print("✅ Connection successful!")
            
            # Show regime data
            regime = data.get("regime", {})
            if regime and not regime.get("error") and regime.get("data"):
                print("\n📊 Currency Regime Data:")
                for pair, info in regime["data"].items():
                    if not info.get("error"):
                        # Correct field access based on mcp_server.py structure
                        trend_dir = info.get("trend", {}).get("direction", "N/A")
                        price_chg = info.get("trend", {}).get("price_change_60d_pct", "N/A")
                        vol_level = info.get("volatility", {}).get("level", "N/A")
                        vol_pct = info.get("volatility", {}).get("annualized_pct", "N/A")
                        atr_pct = info.get("volatility", {}).get("atr_pct", "N/A")
                        hurst = info.get("market_character", {}).get("hurst_exponent", "N/A")
                        trend_type = info.get("market_character", {}).get("type", "N/A")
                        current_price = info.get("current_price", "N/A")
                        
                        print(f"\n  {pair}:")
                        print(f"    Price: {current_price}")
                        print(f"    Trend: {trend_dir} ({price_chg:+.2f}% over 60d)" if isinstance(price_chg, (int, float)) else f"    Trend: {trend_dir}")
                        print(f"    Volatility: {vol_level} (Ann: {vol_pct}%, ATR: {atr_pct}%)")
                        print(f"    Market Type: {trend_type} (Hurst: {hurst})")
                    else:
                        print(f"\n  {pair}: ❌ {info.get('message', 'Error')}")
            else:
                print(f"\n⚠️ Regime data: {regime}")
            
            # Show trades data
            trades = data.get("trades", {})
            if trades and not trades.get("error") and trades.get("data"):
                print("\n📈 Trades Summary:")
                for pair, info in trades["data"].items():
                    if not info.get("error"):
                        sharpe = info.get("sharpe_ratio", "N/A")
                        win_rate = info.get("win_rate", "N/A")
                        total_profit = info.get("total_profit_pct", "N/A")
                        max_dd = info.get("max_drawdown_pct", "N/A")
                        total_trades = info.get("total_trades", "N/A")
                        
                        print(f"\n  {pair}:")
                        print(f"    Trades: {total_trades}, Win Rate: {win_rate}%")
                        print(f"    Sharpe: {sharpe}, Profit: {total_profit}%, Max DD: {max_dd}%")
                    else:
                        print(f"\n  {pair}: ❌ {info.get('message', 'No trade data')}")
            else:
                print(f"\n⚠️ Trades data: {trades}")
            
            # Calculate opportunity index
            index = await forex_tool.get_forex_opportunity_index_async()
            print(f"\n🎯 Forex Opportunity Index: {index}")
            return True
        else:
            print(f"❌ Connection failed: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_bonds_connection():
    """Test connection to Bonds MCP Server."""
    print("\n" + "="*60)
    print("TESTING BONDS MCP CONNECTION")
    print(f"Server URL: {bonds_tool.BONDS_SERVER_URL}")
    print("="*60)
    
    try:
        bond_data = await bonds_tool.get_bond_yield_trend_async()
        print(f"✅ SUCCESS! Yield Trend: {bond_data['yield_trend']}")
        if bond_data.get('confidence'):
            print(f"   Confidence: {bond_data['confidence']}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def main():
    print("\n🔍 MCP CLIENT-SERVER CONNECTION TEST")
    print("="*60)
    
    # Test Forex
    forex_ok = await test_forex_connection()
    
    # Skip bonds for now
    bonds_ok = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Forex Pipeline: {'✅ Connected' if forex_ok else '❌ Not Available'}")
    print(f"Bonds Pipeline: ⏸️  Not tested (server not running)")

if __name__ == "__main__":
    asyncio.run(main())
