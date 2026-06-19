# API Endpoints Documentation

This document provides a comprehensive overview of all available API endpoints across the different routers.

## Table of Contents

1. [Cashflow Router](#cashflow-router)
2. [Forex Router](#forex-router)

---

# Cashflow Router

**Base Path:** `/api/cashflow`

## Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | GET | Query the cashflow agent |
| `/ocbal` | GET | Get opening/closing balance |
| `/liqregime` | GET | Get liquidity regime prediction |
| `/inandoutflow` | GET | Get 28-day inflow/outflow analysis |
| `/cashbalanceforecast` | GET | Get 30-day cash balance forecast |
| `/marketregime` | GET | Get market regime classification |
| `/orchestrator` | GET | Get multi-asset allocation recommendations |
| `/io` | GET | Get cashflow data by dataset number |

---

## Endpoint Details

### 1. Query Cashflow Agent

**Endpoint:** `GET /api/cashflow/query`

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Natural language query for the agent |

**Response Format:**
```json
{
  "result": "string (agent response)"
}
```

---

### 2. Opening/Closing Balance

**Endpoint:** `GET /api/cashflow/ocbal`

**Description:** Returns the opening and closing cash balance for the most recent date.

**Response Format:**
```json
{
  "opening_balance": 1500000.00,
  "closing_balance": 1650000.00,
  "net-cash-flow": 150000.00,
  "liquidity_buffer": 1575750.00,
  "date": "2025-12-06"
}
```

**Field Descriptions:**
| Field | Type | Description |
|-------|------|-------------|
| `opening_balance` | float | Opening cash balance for the day |
| `closing_balance` | float | Closing cash balance for the day |
| `net-cash-flow` | float | Difference between closing and opening |
| `liquidity_buffer` | float | Closing balance adjusted for CRR (4.5%) |
| `date` | string | Date of the data (YYYY-MM-DD) |

---

### 3. Liquidity Regime

**Endpoint:** `GET /api/cashflow/liqregime`

**Description:** Predicts the current liquidity regime using ML models.

**Response Format:**
```json
{
  "file_path": "path/to/model",
  "current_regime_prob": 0.75,
  "alert_status": false,
  "message": "Normal liquidity conditions",
  "features_used": ["feature1", "feature2", "..."]
}
```

**Field Descriptions:**
| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Path to the model used |
| `current_regime_prob` | float | Probability of current regime (0-1) |
| `alert_status` | boolean | True if high liquidity risk |
| `message` | string | Human-readable status message |
| `features_used` | array | Features used for prediction |

---

### 4. Inflow/Outflow Analysis

**Endpoint:** `GET /api/cashflow/inandoutflow`

**Description:** Analyzes the last 28 days of cash inflows and outflows.

**Response Format:**
```json
{
  "Total Deposit": {
    "Last Week": 5048742.0,
    "Second Last Week": 1233407.0,
    "Third Last Week": 0.0,
    "Fourth Last Week": 0.0
  },
  "Job Income": {
    "Last Week": 0.0,
    "Second Last Week": 0.0,
    "Third Last Week": 0.0,
    "Fourth Last Week": 0.0
  },
  "Interest": {
    "Last Week": 803126.4,
    "Second Last Week": 0.0,
    "Third Last Week": 0.0,
    "Fourth Last Week": 0.0
  },
  "Loans": {
    "Last Week": 0.0,
    "Second Last Week": 0.0,
    "Third Last Week": 0.0,
    "Fourth Last Week": 0.0
  },
  "Online Withdrawal": {
    "Last Week": 150000.0,
    "Second Last Week": 200000.0,
    "Third Last Week": 0.0,
    "Fourth Last Week": 0.0
  },
  "Offline Withdrawal": {
    "Last Week": 50000.0,
    "Second Last Week": 75000.0,
    "Third Last Week": 0.0,
    "Fourth Last Week": 0.0
  }
}
```

> ⚠️ **Note:** This endpoint returns a JSON string, not a dict. Parse accordingly.

**Categories:**
| Category | Description |
|----------|-------------|
| `Total Deposit` | All deposits (operation = DEPOSIT) |
| `Job Income` | Transfer from account |
| `Interest` | Interest income (operation = NaN) |
| `Loans` | Transfer to account |
| `Online Withdrawal` | Card withdrawals |
| `Offline Withdrawal` | Cash withdrawals |

---

### 5. Cash Balance Forecast

**Endpoint:** `GET /api/cashflow/cashbalanceforecast`

**Description:** Forecasts cash balance for the next 30 days.

**Response Format:**
```json
{
  "result": {
    "forecast": [...],
    "dates": [...],
    "confidence_intervals": {...}
  }
}
```

---

### 6. Market Regime

**Endpoint:** `GET /api/cashflow/marketregime`

**Description:** Returns simplified market regime classification.

**Response Format:**
```json
{
  "regime": "Medium",
  "description": "Normal market conditions",
  "indicators": {...}
}
```

**Regime Values:**
| Regime | Description |
|--------|-------------|
| `High` | High volatility/risk market |
| `Medium` | Normal market conditions |
| `Low` | Low volatility/calm market |

---

### 7. Portfolio Allocation Orchestrator ⭐

**Endpoint:** `GET /api/cashflow/orchestrator`

**Description:** Returns comprehensive multi-asset allocation recommendations based on liquidity and market conditions.

**Response Format:**
```json
{
  "states": {
    "liquidity": "Normal",
    "market": "Medium"
  },
  "ratios": {
    "RR": 0.065,
    "IR": 0.28,
    "LR": 0.655
  },
  "portfolios": {
    "Aggressive": {
      "Govt_Bonds": 0.18,
      "Corp_Bonds": 0.04,
      "Stocks": 0.05,
      "Forex": 0.01
    },
    "Normal": {
      "Govt_Bonds": 0.20,
      "Corp_Bonds": 0.05,
      "Stocks": 0.03,
      "Forex": 0.0
    },
    "Safe": {
      "Govt_Bonds": 0.25,
      "Corp_Bonds": 0.03,
      "Stocks": 0.0,
      "Forex": 0.0
    }
  },
  "rbi": {
    "CRR": 0.045,
    "SLR": 0.18
  }
}
```

**Field Descriptions:**

| Field | Description |
|-------|-------------|
| `states.liquidity` | Current liquidity state: "Normal" or "High Risk" |
| `states.market` | Market regime: "High", "Medium", or "Low" |
| `ratios.RR` | Cash Reserve Ratio (regulatory + buffer) |
| `ratios.IR` | Investment Ratio |
| `ratios.LR` | Loan Book Ratio |
| `portfolios` | Allocation breakdown for each risk profile |
| `rbi.CRR` | RBI mandated Cash Reserve Ratio |
| `rbi.SLR` | RBI mandated Statutory Liquidity Ratio |

**Portfolio Breakdown (within IR):**
| Asset | Description |
|-------|-------------|
| `Govt_Bonds` | Government bonds (SLR qualifying) |
| `Corp_Bonds` | Corporate bonds |
| `Stocks` | Equity investments |
| `Forex` | Foreign exchange exposure |

---

### 8. Cashflow Data by Number

**Endpoint:** `GET /api/cashflow/io`

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `number` | string | Yes | Dataset number (e.g., "1", "2") |

**Response Format:**
```json
[
  {
    "date": "2025-12-01",
    "net-cash-flow": 150000.0,
    "history_window_end_year": 2025,
    "history_window_end_month": 12,
    "history_window_end_day": 1,
    "...": "other columns"
  }
]
```

Returns the last 48 days of data as an array of records.

---

# Forex Router

**Base Path:** `/forex`

## Endpoints Overview

### Health & Status
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Pipeline status |

### Main Page
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pairs` | GET | All forex pairs overview |
| `/api/v1/recommended-trades` | GET | Trade recommendations |
| `/api/v1/trade` | POST | Execute trade action |
| `/api/v1/portfolio` | GET | Portfolio summary |
| `/api/v1/portfolio/refresh` | POST | Refresh portfolio P&L |
| `/api/v1/positions/update` | POST | Update position |

### Profits
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/profits/{pair}` | GET | Cumulative profit for pair |
| `/api/v1/profits` | GET | All pairs profit summary |
| `/api/v1/profits/{pair}/chart-data` | GET | Profit chart data |

### Currency Page
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/currency/{pair}/price-data` | GET | Price data for charting |
| `/api/v1/currency/{pair}/risk-metrics` | GET | Risk metrics |
| `/api/v1/currency/{pair}/exposure` | GET | Portfolio exposure |

### Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/correlation-matrix` | GET | Correlation matrix |
| `/api/v1/trade-records` | GET | Trade history |

### News
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/news/headlines` | GET | All pairs news sentiment |
| `/news/headlines/{pair}` | GET | Single pair news sentiment |

### Agent
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agent/query` | POST | Query forex agent |
| `/api/v1/agent/query/stream` | GET | Streaming agent query |

---

## Endpoint Details

### 1. Health Check

**Endpoint:** `GET /forex/health`

**Response Format:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-06T10:30:00.000Z",
  "version": "2.0.0"
}
```

---

### 2. Forex Pairs Overview

**Endpoint:** `GET /forex/api/v1/pairs`

**Description:** Returns all 6 forex pairs with current prices and daily changes.

**Supported Pairs:** `EURINR`, `GBPINR`, `JPYINR`, `EURUSD`, `GBPUSD`, `USDJPY`

**Response Format:**
```json
{
  "pairs": [
    {
      "pair": "EURUSD",
      "current_price": 1.0856,
      "previous_close": 1.0842,
      "price_change_1d": 0.0014,
      "price_change_pct_1d": 0.129,
      "high_1d": 1.0875,
      "low_1d": 1.0820
    }
  ],
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

---

### 3. Recommended Trades

**Endpoint:** `GET /forex/api/v1/recommended-trades`

**Description:** Returns ML-based trade recommendations for all pairs.

**Response Format:**
```json
{
  "trades": [
    {
      "pair": "EURUSD",
      "current_price": 1.0856,
      "price_change_pct": 0.129,
      "action": "buy",
      "signal_strength": "moderate",
      "model_confidence": 0.72,
      "predicted_return": 0.0015,
      "stop_loss": 1.0800,
      "take_profit": 1.0920
    }
  ],
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

**Action Values:** `buy`, `sell`, `hold`
**Signal Strength:** `weak`, `moderate`, `strong`

---

### 4. Execute Trade

**Endpoint:** `POST /forex/api/v1/trade`

**Request Body:**
```json
{
  "pair": "EURUSD",
  "action": "buy",
  "amount": 10000,
  "price": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pair` | string | Yes | Currency pair |
| `action` | string | Yes | "buy", "sell", or "hold" |
| `amount` | float | No | Trade amount (default: 10000) |
| `price` | float | No | Execution price (uses market if null) |

**Response Format:**
```json
{
  "success": true,
  "pair": "EURUSD",
  "action": "BUY",
  "executed_price": 1.0856,
  "amount": 10000,
  "position_after": "long",
  "message": "Opened long position",
  "trade_id": "a1b2c3d4",
  "portfolio_summary": {...},
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

---

### 5. Portfolio Summary

**Endpoint:** `GET /forex/api/v1/portfolio`

**Response Format:**
```json
{
  "total_open_positions": 3,
  "total_exposure_long": 25000,
  "total_exposure_short": 10000,
  "net_exposure": 15000,
  "total_unrealized_pnl_pct": 1.25,
  "portfolio_heat": 0.35,
  "long_exposure_pct": 25.0,
  "short_exposure_pct": 10.0,
  "positions": {
    "EURUSD": {
      "current_position": "long",
      "position_size": 10000,
      "entry_price": 1.0840,
      "unrealized_pnl_pct": 0.15
    }
  },
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

---

### 6. Correlation Matrix ⭐

**Endpoint:** `GET /forex/api/v1/correlation-matrix`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 60 | Number of days for calculation |

**Response Format:**
```json
{
  "pairs": ["EURINR", "GBPINR", "JPYINR", "EURUSD", "GBPUSD", "USDJPY"],
  "matrix": [
    [1.00, 0.85, 0.42, 0.78, 0.72, -0.35],
    [0.85, 1.00, 0.38, 0.71, 0.82, -0.28],
    [0.42, 0.38, 1.00, 0.25, 0.22, 0.65],
    [0.78, 0.71, 0.25, 1.00, 0.92, -0.55],
    [0.72, 0.82, 0.22, 0.92, 1.00, -0.48],
    [-0.35, -0.28, 0.65, -0.55, -0.48, 1.00]
  ],
  "period_days": 60,
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

**Matrix Interpretation:**
- Values range from -1 to 1
- 1.0 = Perfect positive correlation
- -1.0 = Perfect negative correlation
- 0 = No correlation

---

### 7. Currency Price Data

**Endpoint:** `GET /forex/api/v1/currency/{pair}/price-data`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `pair` | string | Currency pair (e.g., "EURUSD") |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 90 | Number of days of data |

**Response Format:**
```json
{
  "pair": "EURUSD",
  "data": [
    {
      "timestamp": "2025-12-06T00:00:00.000Z",
      "open": 1.0842,
      "high": 1.0875,
      "low": 1.0820,
      "close": 1.0856,
      "volume": 125000
    }
  ],
  "spot_rate": 1.0856,
  "realized_volatility_10d": 0.085,
  "realized_volatility_20d": 0.092,
  "atr_14d": 0.0045,
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

---

### 8. Risk Metrics

**Endpoint:** `GET /forex/api/v1/currency/{pair}/risk-metrics`

**Response Format:**
```json
{
  "pair": "EURUSD",
  "volatility_10d": 0.085,
  "volatility_20d": 0.092,
  "volatility_60d": 0.088,
  "value_at_risk_95": -0.0125,
  "value_at_risk_99": -0.0185,
  "position_size": 10000,
  "strategy_sharpe": 1.45,
  "max_drawdown_pct": -3.25,
  "beta_to_usd": 0.85,
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

---

### 9. News Headlines Sentiment ⭐

**Endpoint:** `GET /forex/news/headlines`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `pairs` | string | Comma-separated pairs (optional) |

**Response Format:**
```json
{
  "pairs": [
    {
      "pair": "EURUSD",
      "overall_sentiment": "BULLISH",
      "sentiment_score": 0.45,
      "confidence": "high",
      "headline_count": 12,
      "positive_count": 7,
      "negative_count": 3,
      "neutral_count": 2,
      "headlines": [
        {
          "title": "ECB signals rate stability",
          "source": "Reuters",
          "sentiment": "positive",
          "sentiment_score": 0.65,
          "url": "https://...",
          "published_date": "2025-12-06"
        }
      ]
    }
  ],
  "market_sentiment": "BULLISH",
  "market_sentiment_score": 0.35,
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

**Sentiment Values:**
| Field | Values |
|-------|--------|
| `overall_sentiment` | "BULLISH", "BEARISH", "NEUTRAL" |
| `sentiment` (headline) | "positive", "negative", "neutral" |
| `confidence` | "high", "medium", "low" |

---

### 10. Cumulative Profit

**Endpoint:** `GET /forex/api/v1/profits/{pair}`

**Response Format:**
```json
{
  "pair": "EURUSD",
  "total_profit_pct": 5.25,
  "total_profit_amount": 5250.00,
  "total_trades": 25,
  "winning_trades": 15,
  "losing_trades": 10,
  "win_rate": 0.60,
  "avg_profit_per_trade": 0.21,
  "largest_win_pct": 2.15,
  "largest_loss_pct": -1.25,
  "current_streak": 3,
  "profit_history": [
    {
      "date": "2025-12-05",
      "pnl_pct": 0.45,
      "cumulative_pct": 5.25
    }
  ],
  "timestamp": "2025-12-06T10:30:00.000Z"
}
```

---

## Quick Reference: Data Types

### Currency Pairs
```
EURINR - Euro / Indian Rupee
GBPINR - British Pound / Indian Rupee
JPYINR - Japanese Yen / Indian Rupee
EURUSD - Euro / US Dollar
GBPUSD - British Pound / US Dollar
USDJPY - US Dollar / Japanese Yen
```

### Common Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | Response generation time |
| `success` | boolean | Operation success status |
| `error` | boolean | Error flag (when present) |
| `message` | string | Human-readable message |

---

## Error Responses

All endpoints may return error responses in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (resource doesn't exist) |
| 500 | Internal Server Error |
