# Master Orchestrator - Technical Documentation

> **For Teams:** This document explains how the Master Orchestrator works, how to use its API, and how data flows from user queries to frontend components.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Usage](#api-usage)
4. [Data Flow](#data-flow)
5. [Session & Context Management](#session--context-management)
6. [Available Pipelines](#available-pipelines)
7. [Component Reference](#component-reference)
8. [Adding New Components](#adding-new-components)

---

## Overview

The Master Orchestrator is an intelligent query router that:

1. **Understands** natural language queries about finance (forex, stocks, bonds, cashflow, news)
2. **Routes** queries to the appropriate data pipelines
3. **Selects** UI components to visualize the results
4. **Transforms** API data into frontend-ready JSON
5. **Maintains** conversation context for follow-up queries

### Quick Start

```bash
# Start the orchestrator API
cd /home/sinosuke/Documents/pw-2/upgraded-octo-spork
uvicorn master_orchestrator.api:app --reload --port 8001

# Make a query
curl "http://localhost:8001/query?prompt=Show%20me%20the%20forex%20correlation%20matrix"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
│                    "Show me RELIANCE fundamentals"                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ROUTER AGENT (LLM)                                │
│                                                                              │
│  • Analyzes query intent                                                     │
│  • Selects pipelines: [STOCKS]                                              │
│  • Considers session context for follow-ups                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPONENT SELECTOR (LLM)                              │
│                                                                              │
│  • Matches query to components: [comp-11, comp-12]                          │
│  • Extracts parameters: {ticker: "RELIANCE"}                                │
│  • Uses component descriptions & keywords                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ORCHESTRATOR                                      │
│                                                                              │
│  For each selected component:                                                │
│    1. Look up endpoint in Component Registry                                 │
│    2. Call FastAPI endpoint via API Client                                  │
│    3. Apply transformer to convert response                                  │
│    4. Return formatted component JSON                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESPONSE (JSON)                                    │
│                                                                              │
│  {                                                                           │
│    "message": "RELIANCE shows strong fundamentals with P/E of 22.21...",    │
│    "components": [                                                           │
│      { "type": "FundamentalsCard", "data": {...} },                         │
│      { "type": "SentimentAnalysisCard", "data": {...} }                     │
│    ]                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Usage

### Base URL
```
http://localhost:8001
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | GET | Process query → returns `{message, components}` |
| `/query/full` | GET | Full response with routing/selection info |
| `/health` | GET | Health check |
| `/components` | GET | List all available components |
| `/docs` | GET | Swagger UI documentation |

### Query Endpoint

**Request:**
```bash
GET /query?prompt=<text>&session_id=<optional>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | ✅ | Natural language query |
| `session_id` | string | ❌ | Session ID for context continuity |

**Response Format (matches schema.json):**
```json
{
  "message": "Text response explaining the analysis",
  "components": [
    {
      "type": "ComponentTypeName",
      "data": { /* component-specific data */ }
    }
  ]
}
```

### Example Queries

```bash
# Forex correlation matrix
curl "http://localhost:8001/query?prompt=Show%20forex%20correlation%20matrix"

# Stock fundamentals with ticker extraction
curl "http://localhost:8001/query?prompt=Show%20me%20RELIANCE%20fundamentals"

# Bond details with ISIN extraction
curl "http://localhost:8001/query?prompt=Get%20bond%20details%20for%20IN0020220025"

# Cash flow analysis
curl "http://localhost:8001/query?prompt=Display%20cash%20flow%20table"

# With session context (for follow-up queries)
curl "http://localhost:8001/query?prompt=What%20about%20sentiment&session_id=user123"
```

---

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Query      │────▶│   Router     │────▶│  Component   │────▶│ Orchestrator │
│   Service    │     │   Agent      │     │  Selector    │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
                     ┌─────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         COMPONENT PROCESSING LOOP                             │
│                                                                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐ │
│  │  Component  │────▶│  API Client │────▶│ Transformer │────▶│  Component │ │
│  │  Registry   │     │  (HTTP)     │     │  Function   │     │  JSON      │ │
│  └─────────────┘     └─────────────┘     └─────────────┘     └────────────┘ │
│        │                   │                   │                    │        │
│        │                   │                   │                    │        │
│   Get endpoint        Call FastAPI        Transform raw        Return to    │
│   & transformer       endpoint            response to          frontend     │
│                                           component format                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Example: Forex Correlation Query

```
Query: "Show forex correlation matrix"
         │
         ▼
Router Agent: Selects Pipeline.FOREX
         │
         ▼
Component Selector: Selects comp-2 (CorrelationMatrixFX)
         │
         ▼
Component Registry: 
  - endpoint: "correlation" → /forex/v1/correlation-matrix
  - transformer: transform_correlation_matrix()
         │
         ▼
API Client: GET http://localhost:8000/forex/v1/correlation-matrix
         │
         ▼
Raw API Response:
{
  "correlation_matrix": {
    "EURINR": {"EURINR": 1.0, "GBPINR": 0.85, ...},
    ...
  }
}
         │
         ▼
Transformer: transform_correlation_matrix()
         │
         ▼
Component JSON:
{
  "type": "CorrelationMatrixFX",
  "data": {
    "labels": ["EUR/INR", "GBP/INR", "JPY/INR", "EUR/USD", "GBP/USD", "USD/JPY"],
    "matrix": [[1.0, 0.85, ...], ...]
  }
}
```

---

## Session & Context Management

The orchestrator maintains conversation context for follow-up queries using a **Session Store**.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SESSION STORE                                    │
│                                                                          │
│  session_id: "user123"                                                  │
│  ├── previous_messages: ["Analysis shows RELIANCE has...", ...]        │
│  ├── last_query: "Show RELIANCE fundamentals"                          │
│  └── last_pipelines: [STOCKS]                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Context Flow

```
Query 1: "Show me RELIANCE fundamentals"
    └── session_id: "user123"
    └── Response cached: "RELIANCE shows P/E of 22.21..."

Query 2: "What about the sentiment?"
    └── session_id: "user123"
    └── Context injected:
        """
        Context from previous conversation:
        [Previous analysis]: RELIANCE shows P/E of 22.21...
        
        Current query: What about the sentiment?
        """
    └── Router understands: This is about RELIANCE sentiment
    └── Selects: comp-12 (SentimentAnalysisCard) with ticker=RELIANCE
```

### Session Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `max_messages` | 5 | Max messages cached per session |
| Context window | Last 2 messages | Messages included in contextual query |
| Truncation | 800 chars | Max length per cached message |

### Using Sessions

```bash
# First query - establishes context
curl "http://localhost:8001/query?prompt=Show%20RELIANCE%20fundamentals&session_id=user123"

# Follow-up - uses context to understand "it" refers to RELIANCE
curl "http://localhost:8001/query?prompt=What%20is%20the%20sentiment%20for%20it&session_id=user123"
```

---

## Available Pipelines

| Pipeline | Description | Backend Base Path |
|----------|-------------|-------------------|
| **FOREX** | Currency analysis, correlation, trends | `/forex/v1/...` |
| **STOCKS** | Equity analysis, fundamentals, sentiment | `/api/stocks/...` |
| **BONDS** | Fixed income analysis, yields, pricing | `/bond/...` |
| **CASHFLOW** | Liquidity, cash forecasting, allocation | `/api/cashflow/...` |
| **NEWS** | Financial news with sentiment | `/api/news/...` |

### Pipeline Endpoints

<details>
<summary><b>FOREX Pipeline</b></summary>

| Endpoint Key | API Path |
|--------------|----------|
| `pairs` | `/forex/v1/pairs` |
| `recommended_trades` | `/forex/v1/recommended-trades` |
| `correlation` | `/forex/v1/correlation-matrix` |
| `price_data` | `/forex/v1/currency/{pair}/price-data` |
| `risk_metrics` | `/forex/v1/currency/{pair}/risk-metrics` |
| `headline_sentiment` | `/forex/news/headlines` |
| `agent_query` | `/forex/agent/query` |

</details>

<details>
<summary><b>STOCKS Pipeline</b></summary>

| Endpoint Key | API Path |
|--------------|----------|
| `tickers` | `/api/stocks/` |
| `ticker_data` | `/api/stocks/{ticker}` |
| `agent_query` | `/api/stocks/agent/query` |

</details>

<details>
<summary><b>BONDS Pipeline</b></summary>

| Endpoint Key | API Path |
|--------------|----------|
| `universe` | `/bond/universe` |
| `bond_details` | `/bond/{isin}` |
| `yield_history` | `/bond/{isin}/yield-history` |
| `rate_yield_overlay` | `/bond/{isin}/rate-yield-overlay` |
| `price_statistics` | `/bond/{isin}/price-statistics` |
| `agent_query` | `/bond/agent/query` |

</details>

<details>
<summary><b>CASHFLOW Pipeline</b></summary>

| Endpoint Key | API Path |
|--------------|----------|
| `query` | `/api/cashflow/query` |
| `opening_closing_balance` | `/api/cashflow/ocbal` |
| `liquidity_regime` | `/api/cashflow/liqregime` |
| `in_out_flow` | `/api/cashflow/inandoutflow` |
| `cash_balance_forecast` | `/api/cashflow/cashbalanceforecast` |
| `allocation` | `/api/cashflow/orchestrator` |

</details>

<details>
<summary><b>NEWS Pipeline</b></summary>

| Endpoint Key | API Path |
|--------------|----------|
| `summarized` | `/api/news/summarized` |
| `enriched` | `/api/news/enriched` |
| `clusters` | `/api/news/clusters` |
| `stats` | `/api/news/stats` |

</details>

---

## Component Reference

### Component Status Overview

| ID | Type | Pipeline | Status |
|----|------|----------|--------|
| `comp-1` | NewsSentimentStream | NEWS | ✅ Ready |
| `comp-2` | CorrelationMatrixFX | FOREX | ✅ Ready |
| `comp-3` | AllocationDashboard | CASHFLOW | ✅ Ready |
| `comp-5` | AlertInsights | NEWS | ✅ Ready |
| `comp-6` | BondRiskSensitivity | BONDS | ✅ Ready |
| `comp-7` | MonteCarloOutputCard | STOCKS | ⏳ Pending |
| `comp-8` | AssetPerformance | - | ⏳ Pending |
| `comp-9` | CashAllocationCard | CASHFLOW | ✅ Ready |
| `comp-10` | LiquidityDashboard | CASHFLOW | ✅ Ready |
| `comp-11` | FundamentalsCard | STOCKS | ✅ Ready |
| `comp-12` | SentimentAnalysisCard | STOCKS | ✅ Ready |
| `comp-13` | CurrentValueCard | - | ⏳ Pending |
| `comp-14` | StockPriceHeader | STOCKS | ✅ Ready |
| `comp-15` | BondTermsCard | BONDS | ✅ Ready |
| `comp-16` | BondPricingCard | BONDS | ✅ Ready |
| `comp-17` | CashFlowTable | CASHFLOW | ✅ Ready |
| `comp-18` | GeneralCard | - | ⏳ Pending |
| `comp-19` | CashBalanceForecastChart | CASHFLOW | ✅ Ready |
| `comp-20` | FxPriceChart | FOREX | ✅ Ready |
| `comp-21` | StockCandlestickChart | STOCKS | ✅ Ready |
| `comp-22` | BondYieldTimeChart | BONDS | ✅ Ready |
| `comp-23` | RateVsYieldChart | BONDS | ✅ Ready |
| `comp-24` | BondPriceTimeChart | BONDS | ✅ Ready |

---

### Component Details

#### comp-1: NewsSentimentStream
**Pipeline:** NEWS | **Endpoint:** `/api/news/summarized`

Shows news headlines with sentiment scores.

```json
{
  "type": "NewsSentimentStream",
  "data": {
    "newsItems": [
      {
        "headline": "S&P raises Reliance rating",
        "source": "Reuters",
        "timestamp": "2025-12-06T10:30:00Z",
        "sentimentScore": 0.65
      }
    ]
  }
}
```

**Trigger Keywords:** `news`, `sentiment`, `headlines`, `market news`

---

#### comp-2: CorrelationMatrixFX
**Pipeline:** FOREX | **Endpoint:** `/forex/v1/correlation-matrix`

Shows 6×6 correlation matrix for forex pairs.

```json
{
  "type": "CorrelationMatrixFX",
  "data": {
    "labels": ["EUR/INR", "GBP/INR", "JPY/INR", "EUR/USD", "GBP/USD", "USD/JPY"],
    "matrix": [
      [1.00, 0.85, 0.42, 0.78, 0.72, -0.35],
      [0.85, 1.00, 0.38, 0.71, 0.82, -0.28]
    ]
  }
}
```

**Trigger Keywords:** `correlation`, `matrix`, `forex correlation`, `currency correlation`

---

#### comp-3: AllocationDashboard
**Pipeline:** CASHFLOW | **Endpoint:** `/api/cashflow/orchestrator`

Shows recommended portfolio allocation.

```json
{
  "type": "AllocationDashboard",
  "data": {
    "assetClasses": [
      {"name": "Cash Reserve", "recommended percentage": 6.5},
      {"name": "Loan Book", "recommended percentage": 65.5},
      {"name": "Govt Bonds", "recommended percentage": 20.0},
      {"name": "Corp Bonds", "recommended percentage": 5.0},
      {"name": "Stocks", "recommended percentage": 3.0}
    ]
  }
}
```

**Parameters:** `risk_profile` (Aggressive/Normal/Safe)  
**Trigger Keywords:** `allocation`, `portfolio allocation`, `asset allocation`

---

#### comp-5: AlertInsights
**Pipeline:** NEWS | **Endpoint:** `/api/news/summarized`

Shows critical alerts with severity levels.

```json
{
  "type": "AlertsInsights",
  "data": [
    {
      "title": "High volatility in EUR/USD",
      "timestamp": "2025-12-06T10:30:00Z",
      "severity": "warning"
    }
  ]
}
```

**Severity:** `critical` | `warning` | `info`  
**Trigger Keywords:** `alerts`, `warnings`, `critical`, `risk alerts`

---

#### comp-6: BondRiskSensitivity
**Pipeline:** BONDS | **Endpoint:** `/bond/{isin}`

Shows DV01 (Dollar Value of 01) for bonds.

```json
{
  "type": "BondRiskSensitivity",
  "data": [
    {"GOI 10Y 8.5% 2040": ["₹45.23"]}
  ]
}
```

**Parameters:** `isin`  
**Trigger Keywords:** `DV01`, `bond risk`, `bond sensitivity`

---

#### comp-7: MonteCarloOutputCard
**Pipeline:** STOCKS | **Endpoint:** `/api/stocks/agent/query`

Shows Monte Carlo simulation results.

```json
{
  "type": "MonteCarloOutputCard",
  "data": {
    "results": {
      "Min Return": -15.2,
      "Max Return": 45.8,
      "Mean Return": 12.3,
      "Median Return": 11.5,
      "Std Deviation": 8.7,
      "Probability of Loss": 18.5,
      "Num Simulations": 10000,
      "Num Days": 252,
      "ticker": "RELIANCE"
    }
  }
}
```

**Parameters:** `ticker`  
**Trigger Keywords:** `monte carlo`, `simulation`, `risk simulation`

---

#### comp-9: CashAllocationCard
**Pipeline:** CASHFLOW | **Endpoint:** `/api/cashflow/query`

Shows free cash and invested amounts.

```json
{
  "type": "CashAllocationCard",
  "data": {
    "title": "Cash & Investments",
    "subtitle": "Across all asset classes",
    "freeCashLabel": "Free Cash Available",
    "investedLabel": "Amount Invested",
    "freeCashAmount": 5000000,
    "investedAmount": 45000000,
    "currencySymbol": "₹"
  }
}
```

**Trigger Keywords:** `cash`, `free cash`, `invested`, `cash position`

---

#### comp-10: LiquidityDashboard
**Pipeline:** CASHFLOW | **Endpoint:** `/api/cashflow/liqregime`

Shows liquidity metrics.

```json
{
  "type": "LiquidityDashboard",
  "data": {
    "metrics": [
      {"title": "Cash Flow Forecast (Next 7D)", "value": 2500000},
      {"title": "Liquidity Coverage Ratio (LCR)", "value": 128.5},
      {"title": "Total Cash Position", "value": 50000000}
    ]
  }
}
```

**Trigger Keywords:** `liquidity`, `LCR`, `liquidity ratio`, `cash flow forecast`

---

#### comp-11: FundamentalsCard
**Pipeline:** STOCKS | **Endpoint:** `/api/stocks/agent/query`

Shows fundamental and technical metrics for a stock.

```json
{
  "type": "FundamentalsCard",
  "data": {
    "companyName": "RELIANCE",
    "fundamentals": [
      {"label": "Fiscal Year", "value": "2025"},
      {"label": "Revenue", "value": "₹980,136 Cr"},
      {"label": "P/E Ratio", "value": 22.21}
    ],
    "technical": [
      {"label": "Signal", "value": "HOLD"},
      {"label": "Analysis", "value": "Mixed signals (Buy: 2, Sell: 4)"}
    ]
  }
}
```

**Parameters:** `ticker`  
**Trigger Keywords:** `fundamentals`, `P/E`, `EPS`, `revenue`, `stock analysis`

---

#### comp-12: SentimentAnalysisCard
**Pipeline:** STOCKS | **Endpoint:** `/api/stocks/agent/query`

Shows Twitter/social sentiment.

```json
{
  "type": "SentimentAnalysisCard",
  "data": {
    "sentimentScore": "0.4 (Neutral)",
    "reasoning": "Mixed sentiment due to recent investigation news..."
  }
}
```

**Parameters:** `ticker`  
**Trigger Keywords:** `sentiment`, `twitter`, `social sentiment`, `bullish`, `bearish`

---

#### comp-14: StockPriceHeader
**Pipeline:** STOCKS | **Endpoint:** `/api/stocks/{ticker}`

Shows stock price with daily change.

```json
{
  "type": "StockPriceHeader",
  "data": {
    "stockName": "Reliance Industries Ltd",
    "percentageChange": -1.25,
    "absoluteChange": -15.30,
    "timestamp": "2025-12-06T15:30:00Z"
  }
}
```

**Parameters:** `ticker`, `stock_name`  
**Trigger Keywords:** `stock price`, `current price`, `price change`

---

#### comp-15: BondTermsCard
**Pipeline:** BONDS | **Endpoint:** `/bond/{isin}`

Shows bond terms.

```json
{
  "type": "BondTermsCard",
  "data": {
    "bondName": "2026 8.50% GOI Bond",
    "couponRate": "8.50%",
    "maturityDate": "2040-10-15",
    "rating": "AAA"
  }
}
```

**Parameters:** `isin`  
**Trigger Keywords:** `bond terms`, `coupon`, `maturity`, `credit rating`

---

#### comp-16: BondPricingCard
**Pipeline:** BONDS | **Endpoint:** `/bond/{isin}`

Shows bond pricing.

```json
{
  "type": "BondPricingCard",
  "data": {
    "lastPrice": 105.25,
    "cleanPrice": 104.68,
    "accruedInterest": 0.57
  }
}
```

**Parameters:** `isin`  
**Trigger Keywords:** `bond price`, `clean price`, `accrued interest`

---

#### comp-17: CashFlowTable
**Pipeline:** CASHFLOW | **Endpoint:** `/api/cashflow/inandoutflow`

Shows period-wise cash flows.

```json
{
  "type": "CashFlowTable",
  "data": {
    "rows": [
      {
        "date": "Last Week",
        "openingBalance": "₹1.00 Cr",
        "inflows": 8500000,
        "outflows": 6000000,
        "netCashFlow": 2500000,
        "endingBalance": "₹1.25 Cr",
        "lcrPercentage": 128
      }
    ]
  }
}
```

**Trigger Keywords:** `cash flow`, `inflows`, `outflows`, `cash table`, `treasury`

---

#### comp-19: CashBalanceForecastChart
**Pipeline:** CASHFLOW | **Endpoint:** `/api/cashflow/cashbalanceforecast`

Shows 30-day cash balance forecast.

```json
{
  "type": "CashBalanceForecastChart",
  "data": {
    "points": [
      {"day": 0, "amount": 22000000, "date": "2025-12-06"},
      {"day": 1, "amount": 22500000, "date": "2025-12-07"}
    ]
  }
}
```

**Trigger Keywords:** `cash forecast`, `balance forecast`, `30 day forecast`

---

#### comp-20: FxPriceChart
**Pipeline:** FOREX | **Endpoint:** `/forex/v1/currency/{pair}/price-data`

Shows FX rate over time.

```json
{
  "type": "FxPriceChart",
  "data": {
    "currencyPair": "EUR/USD",
    "points": [
      {"date": "2025-02-01", "value": 1.0823},
      {"date": "2025-02-02", "value": 1.0845}
    ]
  }
}
```

**Parameters:** `currency_pair`  
**Trigger Keywords:** `fx chart`, `forex chart`, `exchange rate chart`

---

#### comp-21: StockCandlestickChart
**Pipeline:** STOCKS | **Endpoint:** `/api/stocks/agent/query`

Shows OHLC candlestick chart.

```json
{
  "type": "StockCandlestickChart",
  "data": {
    "symbol": "RELIANCE",
    "points": [
      {"date": "2025-02-01", "high": 2850, "low": 2780, "open": 2800, "close": 2830}
    ]
  }
}
```

**Parameters:** `ticker`  
**Trigger Keywords:** `candlestick`, `OHLC`, `stock chart`, `technical chart`

---

#### comp-22: BondYieldTimeChart
**Pipeline:** BONDS | **Endpoint:** `/bond/{isin}/yield-history`

Shows bond yield over time.

```json
{
  "type": "BondYieldTimeChart",
  "data": {
    "bondName": "GOI 10Y Treasury",
    "points": [
      {"date": "2025-01-15", "yield": 7.25},
      {"date": "2025-01-16", "yield": 7.28}
    ]
  }
}
```

**Parameters:** `isin`  
**Trigger Keywords:** `yield chart`, `yield history`, `bond yield trend`

---

#### comp-23: RateVsYieldChart
**Pipeline:** BONDS | **Endpoint:** `/bond/{isin}/rate-yield-overlay`

Shows rate vs yield relationship.

```json
{
  "type": "RateVsYieldChart",
  "data": {
    "curveName": "Credit Spread Curve",
    "points": [
      {"rate": 6.5, "yield": 7.25},
      {"rate": 6.75, "yield": 7.45}
    ]
  }
}
```

**Parameters:** `isin`  
**Trigger Keywords:** `rate vs yield`, `credit spread`, `policy rate`

---

#### comp-24: BondPriceTimeChart
**Pipeline:** BONDS | **Endpoint:** `/bond/{isin}/price-statistics`

Shows bond price over time.

```json
{
  "type": "BondPriceTimeChart",
  "data": {
    "bondName": "GOI 10Y Treasury",
    "points": [
      {"date": "2025-01-15", "price": 104.50},
      {"date": "2025-01-16", "price": 104.75}
    ]
  }
}
```

**Parameters:** `isin`  
**Trigger Keywords:** `bond price chart`, `price history`, `bond price trend`

---

## Adding New Components

### Step 1: Create Transformer

```python
# master_orchestrator/transformers/my_component.py

def transform_my_component(api_response: Any, **kwargs) -> Dict[str, Any]:
    """Transform API response to component format."""
    # Extract params
    my_param = kwargs.get("my_param", "default")
    
    # Handle JSON string (from pandas)
    if isinstance(api_response, str):
        api_response = json.loads(api_response)
    
    # Transform and return
    return {
        "field1": api_response.get("source_field"),
        "field2": my_param
    }
```

### Step 2: Export Transformer

```python
# master_orchestrator/transformers/__init__.py

from .my_component import transform_my_component

__all__ = [
    # ... existing ...
    "transform_my_component",
]
```

### Step 3: Register Component

```python
# master_orchestrator/component_registry.py

"comp-XX": {
    "type": ComponentType.MY_COMPONENT,
    "description": "Description for LLM selection",
    "pipeline": Pipeline.CASHFLOW,
    "endpoints": ["my_endpoint"],
    "transformer": transform_my_component,
    "params": ["my_param"],
    "keywords": ["trigger", "keywords"]
},
```

### Step 4: Add Endpoint (if new)

```python
# master_orchestrator/pipeline_registry.py

Pipeline.CASHFLOW: {
    "endpoints": {
        "my_endpoint": "/api/cashflow/my-endpoint",
    }
}
```

### Step 5: Update schema.json

```json
{
  "comp-XX": {
    "type": "MyComponent",
    "data": {
      "field1": "string",
      "field2": "number"
    },
    "description": "Component description"
  }
}
```

---

## Testing

### Interactive Test

```bash
cd /home/sinosuke/Documents/pw-2/upgraded-octo-spork
python master_orchestrator/test_orchestrator.py
```

### Test Queries

| Query | Expected Components |
|-------|---------------------|
| "Show forex correlation" | comp-2 |
| "Show RELIANCE fundamentals" | comp-11 |
| "What's the sentiment for TATAMOTORS?" | comp-12 |
| "Get bond details for IN0020220025" | comp-15, comp-16 |
| "Display cash flow table" | comp-17 |
| "Show portfolio allocation" | comp-3 |
| "Show me liquidity metrics" | comp-10 |
| "Get EUR/USD price chart" | comp-20 |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not set` | Export key: `export OPENAI_API_KEY='sk-...'` |
| `HTTP 404` on endpoint | Check pipeline_registry.py paths match backend |
| Empty component data | Verify transformer handles API response format |
| Wrong component selected | Improve keywords in component_registry.py |
| Context not working | Ensure session_id is passed consistently |

---

## Contact

For issues with the Master Orchestrator, contact the **Platform Team**.

For component-specific issues:
- **FOREX components**: Forex Pipeline Team
- **STOCKS components**: Equities Team  
- **BONDS components**: Fixed Income Team
- **CASHFLOW components**: Treasury Team
- **NEWS components**: Data Engineering Team
