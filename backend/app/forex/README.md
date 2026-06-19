# Forex Trading Pipeline

A comprehensive, production-ready forex trading system with XGBoost models, Kelly Criterion position sizing, real-time data integration, and an AI-powered explainability agent.

## Features

- **Multiple XGBoost Models**: Single-train and walk-forward validation models
- **Kelly Criterion Position Sizing**: Optimal position sizing based on historical performance
- **Real-time Data**: Polygon.io integration with Pathway connectors
- **AI Agent**: LangGraph-based agent with parallel tool execution
- **News Sentiment**: Financial news scraping with LLM analysis
- **FastAPI**: RESTful API for all pipeline operations
- **Streamlit UI**: Interactive dashboard for analysis

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export POLYGON_API_KEY="your_polygon_api_key"
export GEMINI_API_KEY="your_gemini_api_key"
export NEWSDATA_API_KEY="your_newsdata_api_key"
```

### 3. Run the Pipeline

```bash
# Run full pipeline (train models, generate signals, update positions)
python run.py

# Force model retraining
python run.py --train

# Update data from Polygon.io and run pipeline
python run.py --update-data

# Start API server
python run.py --api

# Start Streamlit UI
python run.py --streamlit

# Run a single agent query
python run.py --agent "Analyze EURUSD trading performance and market regime"
```

## Architecture

```
forex/
├── config.yaml          # Main configuration file
├── run.py               # Main entry point
├── pipeline.py          # Trading pipeline orchestration
├── models.py            # XGBoost model implementations
├── preprocessing.py     # Feature engineering
├── position_sizing.py   # Kelly Criterion implementation
├── data_fetcher.py      # Polygon.io data fetcher
├── forex_agent_v2.py    # AI explainability agent
├── api.py               # FastAPI endpoints
├── news_tool.py         # Financial news scraper
├── streamlit_app.py     # Streamlit UI
├── positions.json       # Current positions (auto-updated)
├── trades.json          # Trade history (auto-updated)
├── data/                # Historical CSV data
└── trained_models/      # Saved model files
```

## Models

### 1. Single Train Model
- Trains once on historical data (80/20 split)
- Best for stable market conditions
- Lower computational cost

### 2. Walk-Forward Model
- Retrains at each step
- More robust out-of-sample testing
- Better for changing market conditions

### Model Configurations

| Model Name | Type | Pairs | Description |
|------------|------|-------|-------------|
| `inr_model` | single_train | EURINR, GBPINR, JPYINR | INR pairs model |
| `usdjpy_model` | single_train | USDJPY | USD/JPY without bond yield |
| `usd_model` | single_train | EURUSD, GBPUSD | USD pairs model |

## Position Sizing (Kelly Criterion)

The pipeline uses the Kelly Criterion for optimal position sizing:

```
f* = (p * b - q) / b

where:
- f* = optimal fraction of capital
- p = win probability
- b = payoff ratio (avg win / avg loss)
- q = loss probability (1 - p)
```

Default configuration uses **Quarter-Kelly** (25% of full Kelly) for risk management.

## API Endpoints

### Agent Endpoints
- `POST /agent/query` - Query the AI agent
- `GET /agent/query/stream` - Stream agent response

### Pipeline Endpoints
- `POST /pipeline/run` - Run trading pipeline
- `GET /pipeline/signals` - Get current signals
- `GET /pipeline/allocations` - Get position allocations

### Data Endpoints
- `GET /positions` - Get all positions
- `GET /positions/{pair}` - Get position for a pair
- `GET /trades` - Get trade history
- `GET /trades/{pair}` - Get trades for a pair

### Analysis Endpoints
- `GET /analysis/regime/{pair}` - Market regime analysis
- `GET /analysis/correlation` - Correlation matrix
- `GET /analysis/news/{pair}` - News sentiment

## Configuration

All settings are in `config.yaml`:

```yaml
models:
  active_models:
    - name: "inr_model"
      type: "single_train"
      pairs: ["EURINR", "GBPINR", "JPYINR"]

trading:
  position_sizing:
    method: "kelly"
    kelly_fraction: 0.25
    max_position_pct: 0.10
    portfolio_capital: 100000

data:
  polygon:
    api_key: "${POLYGON_API_KEY}"
```

## AI Agent Tools

The forex agent has access to these tools (executed in parallel):

1. **get_trades_summary** - Trading performance metrics
2. **get_position_details** - Current position info
3. **get_currency_regime** - Market regime analysis (Hurst exponent)
4. **get_currency_correlation** - Correlation matrix
5. **get_news_sentiment** - News analysis with LLM insights

### Example Queries

```python
# Full portfolio analysis
"Give me a complete analysis of all my forex positions"

# Specific pair analysis
"Analyze EURUSD including trades, position, regime, and news"

# Correlation analysis
"What's the correlation between EURUSD, GBPUSD, and USDJPY?"

# Risk assessment
"What are the main risks in my current portfolio?"
```

## Data Sources

### Historical Data (CSV)
- Located in `data/` directory
- Format: `ts_ms, open, high, low, close, volume`

### Real-time Data (Polygon.io)
- Daily OHLCV bars
- Automatic CSV updates
- Pathway streaming integration

## Output Files

### positions.json
```json
{
  "EURUSD": {
    "current_position": "long",
    "entry_price": 1.0485,
    "unrealized_pnl_pct": 0.34,
    "stop_loss": 1.0445,
    "take_profit": 1.0585,
    "model_confidence": 0.78
  }
}
```

### trades.json
```json
{
  "EURUSD": {
    "total_trades": 61,
    "win_rate": 0.574,
    "sharpe_ratio": 1.56,
    "recent_trades": [...]
  }
}
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Models
1. Add configuration to `config.yaml`
2. Implement feature engineering in `preprocessing.py` if needed
3. Add model to `models.py` if new type needed

### Adding New Agent Tools
1. Define tool function with `@tool` decorator in `forex_agent_v2.py`
2. Add to tools list in `create_forex_agent()`
3. Update system prompt

## License

MIT License

