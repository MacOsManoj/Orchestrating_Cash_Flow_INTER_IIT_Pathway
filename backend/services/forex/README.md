# Forex MCP Server

Forex analysis MCP server using Pathway Library.

## Tools Exposed

1. **get_trades_summary** - Trading performance summary
2. **get_position_details** - Current position details
3. **get_currency_regime** - Market regime analysis (Hurst exponent)
4. **get_currency_correlation** - Correlation matrix between pairs
5. **get_news_sentiment** - News sentiment analysis

## Environment Variables

- `MCP_HOST` - Host to bind to (default: 0.0.0.0)
- `MCP_PORT` - Port to bind to (default: 8127)
- `PATHWAY_LICENSE_KEY` - Required for Pathway
- `NEWSDATA_API_KEY` - Optional for news sentiment

## Running

```bash
python mcp_server.py
```

Server will be available at: `http://localhost:8127/mcp/`
