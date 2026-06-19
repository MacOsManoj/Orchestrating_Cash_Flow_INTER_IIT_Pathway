# Forex Agent MCP Server

A Model Context Protocol (MCP) server built with [Pathway](https://pathway.com) that exposes forex trading tools for integration with Claude Desktop, VS Code, and other MCP-compatible clients.

Based on the official [Pathway MCP Server documentation](https://pathway.com/developers/user-guide/llm-xpack/pathway_mcp_server/).

## Features

| Tool | Description |
|------|-------------|
| `get_forex_overview` | Quick overview of all forex pairs with current prices, positions, and profit |
| `get_trades_summary` | Trading performance metrics (profit, win rate, Sharpe ratio, drawdown) |
| `get_position_details` | Current position information (entry, P&L, stop loss, take profit) |
| `get_currency_regime` | Market regime analysis using Hurst exponent (trending vs mean-reverting) |
| `get_currency_correlation` | Correlation matrix between forex pairs for portfolio risk |
| `get_news_sentiment` | News sentiment analysis for currency pairs |
| `get_live_indicators` | Real-time technical indicators (RSI, MACD, SMA, EMA, ATR) |

## Supported Forex Pairs

- EURINR, GBPINR, JPYINR (INR crosses)
- EURUSD, GBPUSD, USDJPY (Major pairs)

## Installation

### 1. Install Dependencies

```bash
pip install "pathway[xpack-llm]" python-dotenv pandas numpy
pip install fastmcp  # For testing
```

### 2. Set Environment Variables

```bash
# Required: Get free license key from https://pathway.com/get-license
export PATHWAY_LICENSE_KEY="your_license_key"

# Optional: For news sentiment tool
export NEWSDATA_API_KEY="your_newsdata_api_key"

# Optional: Server configuration
export MCP_HOST="localhost"
export MCP_PORT="8123"
```

### 3. Start the Server

```bash
cd /path/to/forex/fx
python mcp_server.py
```

The server will start at `http://localhost:8123/mcp/`

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration file (`claude_desktop_config.json`):

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "forex-agent": {
      "command": "python",
      "args": ["/full/path/to/forex/fx/mcp_server.py"],
      "env": {
        "PATHWAY_LICENSE_KEY": "your_license_key",
        "NEWSDATA_API_KEY": "your_newsdata_key"
      }
    }
  }
}
```

### With Python Client

```python
import asyncio
from fastmcp import Client

PATHWAY_MCP_URL = "http://localhost:8123/mcp/"
client = Client(PATHWAY_MCP_URL)

async def main():
    # List available tools
    async with client:
        tools = await client.list_tools()
        print(tools)
    
    # Call a tool
    async with client:
        result = await client.call_tool(
            name="get_forex_overview",
            arguments={}
        )
        print(result)
    
    # Get trades summary for specific pairs
    async with client:
        result = await client.call_tool(
            name="get_trades_summary",
            arguments={"pairs": "EURUSD,GBPUSD"}
        )
        print(result)

asyncio.run(main())
```

### Test the Server

```bash
# Start the server in one terminal
python mcp_server.py

# Run tests in another terminal
python test_mcp_client.py
```

## Tool Parameters

### `pairs` Parameter

Most tools accept a `pairs` parameter:
- **Format:** Comma-separated string of forex pairs
- **Example:** `"EURUSD,GBPUSD,USDJPY"`
- **Default:** All available pairs if empty

### Example Queries

| Query | Tool | Arguments |
|-------|------|-----------|
| "What's the market overview?" | `get_forex_overview` | `{}` |
| "Show EURUSD trading performance" | `get_trades_summary` | `{"pairs": "EURUSD"}` |
| "Current positions for major pairs" | `get_position_details` | `{"pairs": "EURUSD,GBPUSD,USDJPY"}` |
| "Is USDJPY trending or mean-reverting?" | `get_currency_regime` | `{"pairs": "USDJPY"}` |
| "Portfolio correlation risk" | `get_currency_correlation` | `{"pairs": "EURUSD,GBPUSD,USDJPY"}` |
| "News sentiment for euro pairs" | `get_news_sentiment` | `{"pairs": "EURUSD,EURINR"}` |
| "Technical indicators for GBPUSD" | `get_live_indicators` | `{"pairs": "GBPUSD"}` |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Desktop / VS Code                     │
│                        (MCP Client)                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP (streamable-http)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pathway MCP Server                            │
│                  http://localhost:8123/mcp/                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ ForexToolsServ  │  │   PathwayMcp    │  │   pw.run()      │  │
│  │   (McpServable) │◄─┤   (Server)      │◄─┤   (Engine)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Tools (UDFs)                            ││
│  │  • get_forex_overview    • get_currency_regime              ││
│  │  • get_trades_summary    • get_currency_correlation         ││
│  │  • get_position_details  • get_news_sentiment               ││
│  │  • get_live_indicators                                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Sources                              │
│  • data/*.csv (Price data)                                       │
│  • positions.json (Current positions)                            │
│  • trades.json (Trade history)                                   │
│  • NewsData API (News sentiment)                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### "Pathway license key not found"

```bash
export PATHWAY_LICENSE_KEY="your_key"
# Get free key at https://pathway.com/get-license
```

### "Connection refused" when testing

Make sure the server is running:
```bash
python mcp_server.py
```

### "No data available" for a pair

Ensure price data CSV files exist in the `data/` directory:
```bash
ls data/
# Should show: EURUSD.csv, GBPUSD.csv, etc.
```

### News sentiment not working

Set the NewsData API key:
```bash
export NEWSDATA_API_KEY="your_key"
# Get key at https://newsdata.io/
```

## Files

| File | Description |
|------|-------------|
| `mcp_server.py` | Main MCP server implementation |
| `mcp_config.yaml` | Server configuration |
| `test_mcp_client.py` | Test client for verification |
| `MCP_README.md` | This documentation |
| `positions.json` | Current trading positions |
| `trades.json` | Historical trade data |
| `data/*.csv` | Price data for each pair |

## References

- [Pathway MCP Server Documentation](https://pathway.com/developers/user-guide/llm-xpack/pathway_mcp_server/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Pathway Framework](https://pathway.com/)
- [Claude Desktop](https://claude.ai/download)

## License

MIT License - See LICENSE file for details.

