# Stocks API Endpoints

Base URL: `/api/stocks`

## Overview

The Stocks API provides access to stock market data with technical indicators and trading signals from MongoDB.

---

## Endpoints

### 1. Get Stock Data by Ticker

```
GET /api/stocks/{ticker}
```

Retrieves historical stock data with technical indicators for a specific ticker.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Stock ticker symbol (e.g., "AAPL", "RELIANCE") |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Maximum number of data points to return |

**Response:** `List[StockDataPoint]`

```json
[
  {
    "ticker": "AAPL",
    "date": "2024-12-06",
    "close_price": 150.25,
    "open_price": 149.50,
    "volume": 1234567.0,
    "high_price": 151.00,
    "low_price": 149.00,
    "abs_change": 0.75,
    "pct_change": 0.50,
    "action": "BUY",
    "stop_loss": 147.00,
    "take_profit": 155.00,
    "signal_strength": 0.85,
    "limit_order": 149.75,
    "current_price": 150.25,
    "rsi": 55.3,
    "macd": 1.25,
    "macd_signal": 1.10,
    "macd_hist": 0.15,
    "vwap": 150.10,
    "bol_bands": [148.0, 150.0, 152.0],
    "sma": [149.5, 150.0, 150.5],
    "crsi": 62.5,
    "klinger": [1000.0, 950.0],
    "keltner": [147.5, 150.0, 152.5],
    "cmo": 15.2,
    "reason": "RSI oversold bounce with MACD crossover",
    "time": 1701856800,
    "diff": 3600
  }
]
```

---

### 2. Get Available Tickers

```
GET /api/stocks/
```

Returns a list of all available stock tickers in the database.

**Response:** `List[string]`

```json
["AAPL", "GOOGL", "MSFT", "RELIANCE", "TCS", "INFY"]
```

---

## Data Model

### StockDataPoint

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Stock ticker symbol |
| `date` | string | Date of the data point (YYYY-MM-DD) |
| `close_price` | float | Closing price |
| `open_price` | float | Opening price |
| `volume` | float | Trading volume |
| `high_price` | float | Highest price of the day |
| `low_price` | float | Lowest price of the day |
| `abs_change` | float | Absolute price change |
| `pct_change` | float | Percentage price change |
| `action` | string | Trading signal action (BUY/SELL/HOLD) |
| `stop_loss` | float | Recommended stop loss price |
| `take_profit` | float | Recommended take profit price |
| `signal_strength` | float | Strength of the trading signal (0-1) |
| `limit_order` | float | Recommended limit order price |
| `current_price` | float | Current market price |
| `rsi` | float | Relative Strength Index (0-100) |
| `macd` | float | MACD line value |
| `macd_signal` | float | MACD signal line value |
| `macd_hist` | float | MACD histogram value |
| `vwap` | float | Volume Weighted Average Price |
| `bol_bands` | List[float] | Bollinger Bands [lower, middle, upper] |
| `sma` | List[float] | Simple Moving Averages |
| `crsi` | float | Connors RSI |
| `klinger` | List[float] | Klinger Volume Oscillator [KVO, signal] |
| `keltner` | List[float] | Keltner Channels [lower, middle, upper] |
| `cmo` | float | Chande Momentum Oscillator |
| `reason` | string | Explanation for the trading signal |
| `time` | int | Unix timestamp |
| `diff` | int | Time difference in seconds |

---

## Technical Indicators Explained

### Momentum Indicators
- **RSI (Relative Strength Index)**: Measures overbought/oversold conditions (0-100). Above 70 = overbought, below 30 = oversold
- **CRSI (Connors RSI)**: Composite RSI combining short-term RSI, streak length, and percent rank
- **CMO (Chande Momentum Oscillator)**: Measures momentum on a scale of -100 to +100

### Trend Indicators
- **MACD**: Moving Average Convergence Divergence with signal line and histogram
- **SMA**: Simple Moving Averages at various periods
- **VWAP**: Volume Weighted Average Price - institutional benchmark

### Volatility Indicators
- **Bollinger Bands**: Volatility bands around a moving average [lower, middle, upper]
- **Keltner Channels**: ATR-based volatility channels [lower, middle, upper]

### Volume Indicators
- **Klinger Volume Oscillator**: Volume-based trend indicator [KVO value, signal line]

---

## Example Usage

### Fetch AAPL stock data (last 50 points)
```bash
curl "http://localhost:8000/api/stocks/AAPL?limit=50"
```

### Get all available tickers
```bash
curl "http://localhost:8000/api/stocks/"
```

---

## UI Component Mapping

| Component | Relevant Fields | Notes |
|-----------|-----------------|-------|
| **StockPriceHeader** (comp-14) | `ticker`, `pct_change`, `abs_change`, `time` | Missing: full stock name, currency, exchange |
| **FundamentalsCard** (comp-11) | Technical: `rsi`, `macd`, `vwap`, `bol_bands`, `sma` | Missing: Fundamental data (P/E, EPS, market cap) |
| **StockRiskSensitivity** (comp-7) | None available | Missing: VaR, CVaR, Monte Carlo simulation |
| **AssetPerformance** (comp-8) | `ticker`, `current_price`, `pct_change` | Need to aggregate across multiple tickers |

---

## Database Info

- **Database**: `indicator_signals`
- **Collection**: `indicators`
- **Storage**: MongoDB
