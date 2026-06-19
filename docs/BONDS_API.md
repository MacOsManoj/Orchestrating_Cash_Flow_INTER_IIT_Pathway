# Bond Data API - Complete Endpoint Documentation

This document provides detailed information about all API endpoints, including input parameters, output structures, and feature usage.

---

## Table of Contents

### Core Bond Endpoints
1. [Root Endpoint](#1-root-endpoint)
2. [Get Bond Details](#2-get-bond-details)
3. [Get Bond Universe](#3-get-bond-universe)
4. [Get Yield History](#4-get-yield-history)
5. [Rate vs Yield Overlay Graph](#5-rate-vs-yield-overlay-graph)
6. [Price Statistics](#6-price-statistics)

### Compare Instruments Endpoints
7. [Search Bonds for Comparison](#7-search-bonds-for-comparison)
8. [Get Comparison List](#8-get-comparison-list)
9. [Add Bond to Comparison](#9-add-bond-to-comparison)
10. [Remove Bond from Comparison](#10-remove-bond-from-comparison)
11. [Get Comparison Details by ID](#11-get-comparison-details-by-id)
12. [Get Bond Universe for Comparison](#12-get-bond-universe-for-comparison)

### Agent Query Endpoints
13. [Submit Agent Query](#13-submit-agent-query)
14. [Get Agent Output](#14-get-agent-output)

### System Endpoints
15. [Health Check](#15-health-check)

---

## 1. Root Endpoint

**Endpoint:** `GET /`

**Feature Usage:** API information and endpoint discovery - shows available endpoints to API consumers.

### Input Parameters

None

### Request Example

```http
GET /
```

### Output Response

```json
{
  "message": "Bond Data API v1",
  "endpoints": {
    "bond_details": "/api/v1/bonds/{isin}",
    "bond_universe": "/api/v1/bonds/universe",
    "price_statistics": "/api/v1/bonds/{isin}/price-statistics",
    "agent_query": "POST /api/v1/agent/query",
    "agent_output": "GET /api/v1/agent/output?query_id={query_id}"
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | API welcome message |
| `endpoints` | object | Map of available endpoint paths |

---

## 2. Get Bond Details

**Endpoint:** `GET /api/v1/bonds/{isin}`

**Feature Usage:** Bond detail page - displays comprehensive information about a specific bond including pricing, risk metrics, and bond characteristics.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `isin` | string (path) | Yes | ISIN identifier of the bond | `"IN0020220086"` |

### Request Example

```http
GET /api/v1/bonds/IN0020220086
```

### Output Response

**Response Model:** `BondDetails`

```json
{
  "isin": "IN0020220086",
  "bond_name": "GOVERNMENT OF INDIA 31966 GOI 12SP52 7.36 FV RS 100",
  "symbol": "736GS2052",
  "coupon_rate": 0.0736,
  "maturity_date": "2052-09-12",
  "next_coupon_date": "2025-09-12",
  "minimum_increment": 100.0,
  "last_price": 104.0,
  "clean_price": 101.8,
  "accrued_interest": 1.84,
  "duration": 27.7,
  "convexity": 768.49,
  "dv01": 2.88,
  "z_spread": 400,
  "var": 4.32,
  "ytm": 0.070253,
  "interest_rate_volatility": 0.0383,
  "credit_spread_volatility": 0.0383,
  "credit_rating": null
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isin` | string | ISIN identifier |
| `bond_name` | string | Full bond name from ISIN Description |
| `coupon_rate` | float | Annual coupon rate (as decimal, e.g., 0.0736 = 7.36%) |
| `maturity_date` | string | Maturity date (YYYY-MM-DD format) |
| `next_coupon_date` | string | Next coupon payment date (YYYY-MM-DD format) |
| `minimum_increment` | float | Minimum trading increment (face value) |
| `last_price` | float | Last traded price (LTP) |
| `clean_price` | float | Previous close price (clean price) |
| `accrued_interest` | float | Accrued interest amount |
| `duration` | float | Bond duration in years |
| `convexity` | float | Bond convexity |
| `dv01` | float | Dollar Value of 01 (price change for 1bp yield change) |
| `z_spread` | integer | Zero-volatility spread in basis points |
| `var` | float | Value at Risk (95% confidence) |
| `ytm` | float \| null | Yield to Maturity (as decimal, e.g., 0.070253 = 7.03%) |
| `interest_rate_volatility` | float \| null | Annualized interest rate volatility (%) |
| `credit_spread_volatility` | float \| null | Annualized credit spread volatility (%) |
| `credit_rating` | string \| null | Credit rating (optional, may be null) |

### Data Source

- Reads from `Final_Bond_Data.csv`
- Extracts coupon rate from ISIN Description using regex
- Decodes next coupon date from Raw Date Code
- Calculates risk metrics using bond pricing formulas

### Error Responses

- **404 Not Found:** Bond with the provided ISIN does not exist

---

## 3. Get Bond Universe

**Endpoint:** `GET /api/v1/bonds/universe`

**Feature Usage:** Bond listing page - displays all available bonds in the universe with summary information for browsing and filtering.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `sector` | string | No | Filter by sector | `"Government"` |
| `rating` | string | No | Filter by credit rating | `"AAA"` |
| `region` | string | No | Filter by region | `"India"` |
| `search` | string | No | Search by bond name, ticker, or ISIN | `"GOI"` |

### Request Example

```http
GET /api/v1/bonds/universe?search=GOI
```

### Output Response

**Response Model:** `List[BondSummary]`

```json
[
  {
    "isin": "IN0020220086",
    "bond_name": "GOVERNMENT OF INDIA 31966 GOI 12SP52 7.36 FV RS 100",
    "coupon_rate": 0.0736,
    "maturity_date": "2052-09-12",
    "last_price": 104.0
  },
  {
    "isin": "IN0020210152",
    "bond_name": "GOVERNMENT OF INDIA 30734 GOI 15DC35 6.67 FV RS 100",
    "coupon_rate": 0.0667,
    "maturity_date": "2035-12-15",
    "last_price": 104.79
  }
]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isin` | string | ISIN identifier |
| `bond_name` | string | Full bond name |
| `coupon_rate` | float | Annual coupon rate (as decimal) |
| `maturity_date` | string | Maturity date (YYYY-MM-DD) |
| `last_price` | float | Last traded price |

### Data Source

- Reads from `Final_Bond_Data.csv`
- Returns all bonds (294 bonds in dataset)
- Applies filters if provided

---

## 4. Get Yield History

**Endpoint:** `GET /api/v1/bonds/{isin}/yield-history`

**Feature Usage:** Yield history chart - displays yield over time with metrics dashboard showing current yield, volatility, and drawdown information.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `isin` | string (path) | Yes | ISIN identifier of the bond | `"IN0020220086"` |
| `period` | string | No | Time period filter (default: "1D") | `"1D"`, `"1W"`, `"1M"`, `"1Y"`, `"YTD"`, `"MAX"` |

### Request Example

```http
GET /api/v1/bonds/IN0020220086/yield-history?period=MAX
```

### Output Response

**Response Model:** `YieldHistoryResponse`

```json
{
  "isin": "IN0020220086",
  "period": "MAX",
  "yield_data": [
    {
      "date": "2025-11-05",
      "yield": 0.0596,
      "time": "00:00:00"
    },
    {
      "date": "2025-11-06",
      "yield": 0.0598,
      "time": "00:00:00"
    }
  ],
  "metrics": {
    "current_yielding": 0.0596,
    "current_yielding_percent": 5.96,
    "one_month_change": -8.2,
    "one_month_change_unit": "bps",
    "volatility_20d": 0.0002,
    "volatility_20d_percent": 0.02,
    "max_drawdown_1y": 0.0001,
    "max_drawdown_1y_percent": 0.01
  },
  "last_updated": "2025-12-05T01:09:27.248000"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isin` | string | ISIN identifier |
| `period` | string | Time period filter applied |
| `yield_data` | array | Time series yield data points |
| `yield_data[].date` | string | Date (YYYY-MM-DD format) |
| `yield_data[].yield` | float | Yield value (as decimal) |
| `yield_data[].time` | string | Time (HH:MM:SS format) |
| `metrics` | object | Yield metrics |
| `metrics.current_yielding` | float | Current yield (as decimal) |
| `metrics.current_yielding_percent` | float | Current yield as percentage |
| `metrics.one_month_change` | float | 1-month yield change in basis points |
| `metrics.one_month_change_unit` | string | Unit for change ("bps") |
| `metrics.volatility_20d` | float | 20-day volatility (as decimal) |
| `metrics.volatility_20d_percent` | float | 20-day volatility as percentage |
| `metrics.max_drawdown_1y` | float | Maximum drawdown in last year (as decimal) |
| `metrics.max_drawdown_1y_percent` | float | Maximum drawdown as percentage |
| `last_updated` | string | ISO 8601 timestamp |

### Period Options

| Period | Description | Time Range |
|--------|-------------|------------|
| `1D` | Last 1 day | Current date - 1 day |
| `1W` | Last 1 week | Current date - 7 days |
| `1M` | Last 1 month | Current date - 30 days |
| `1Y` | Last 1 year | Current date - 365 days |
| `YTD` | Year to date | January 1st to today |
| `MAX` | All available data | All historical data |

### Data Source

- Historical data from `bond_price_forecasts.csv`
- Calculates YTM from `Predicted_Price` for each date
- Matches bonds by name between CSV files

### Error Responses

- **400 Bad Request:** Invalid period value
- **404 Not Found:** Bond not found or no yield history available

---

## 5. Rate vs Yield Overlay Graph

**Endpoint:** `GET /api/v1/bonds/{isin}/rate-yield-overlay`

**Feature Usage:** Rate vs Yield Overlay chart - displays Policy Rate and 10Y Yield over time with dual Y-axes for correlation analysis.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `isin` | string (path) | Yes | ISIN identifier of the bond | `"IN0020220086"` |
| `period` | string | No | Time period filter (default: "1Y") | `"5Y"`, `"3Y"`, `"1Y"`, `"YTD"` |

### Request Example

```http
GET /api/v1/bonds/IN0020220086/rate-yield-overlay?period=1Y
```

### Output Response

**Response Model:** `RateYieldOverlayResponse`

```json
{
  "isin": "IN0020220086",
  "period": "1Y",
  "data": [
    {
      "date": "2025-11-05T00:00:00Z",
      "policy_rate": 3.58,
      "yield_10y": 5.96
    },
    {
      "date": "2025-11-06T00:00:00Z",
      "policy_rate": 3.60,
      "yield_10y": 5.98
    }
  ],
  "series": [
    {
      "name": "Policy Rate",
      "data_key": "policy_rate",
      "color": "light_blue",
      "y_axis": "left"
    },
    {
      "name": "10Y Yield",
      "data_key": "yield_10y",
      "color": "white",
      "y_axis": "right"
    }
  ],
  "y_axes": {
    "left": {
      "label": "Policy Rate (%)",
      "min": 3.0,
      "max": 4.0
    },
    "right": {
      "label": "10Y Yield (%)",
      "min": 5.5,
      "max": 6.5
    }
  },
  "last_updated": "2025-12-05T01:09:27.248000Z"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isin` | string | ISIN identifier |
| `period` | string | Time period filter applied |
| `data` | array | Time series data points |
| `data[].date` | string | ISO 8601 timestamp |
| `data[].policy_rate` | float | Policy rate percentage (left Y-axis) |
| `data[].yield_10y` | float | 10Y Yield percentage (right Y-axis) |
| `series` | array | Series definitions for chart |
| `series[].name` | string | Display name |
| `series[].data_key` | string | Key to access data |
| `series[].color` | string | Line color |
| `series[].y_axis` | string | "left" or "right" |
| `y_axes` | object | Y-axis configurations |
| `y_axes.left.label` | string | Left Y-axis label |
| `y_axes.left.min` | float | Left Y-axis minimum |
| `y_axes.left.max` | float | Left Y-axis maximum |
| `y_axes.right.label` | string | Right Y-axis label |
| `y_axes.right.min` | float | Right Y-axis minimum |
| `y_axes.right.max` | float | Right Y-axis maximum |
| `last_updated` | string | ISO 8601 timestamp |

### Period Options

| Period | Description |
|--------|-------------|
| `5Y` | Last 5 years |
| `3Y` | Last 3 years |
| `1Y` | Last 1 year (default) |
| `YTD` | Year to date |

### Error Responses

- **400 Bad Request:** Invalid period value
- **404 Not Found:** Bond not found

---

## 6. Price Statistics

**Endpoint:** `GET /api/v1/bonds/{isin}/price-statistics`

**Feature Usage:** Price statistics chart - displays price history with percentile bands and statistical metrics including median price, percentile prices, and implied volatility.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `isin` | string (path) | Yes | ISIN identifier of the bond | `"IN0020220086"` |
| `period` | string | No | Time period filter (default: "1D") | `"1D"`, `"1W"`, `"1M"`, `"3M"`, `"YTD"`, `"1Y"`, `"MAX"` |

### Request Example

```http
GET /api/v1/bonds/IN0020220086/price-statistics?period=MAX
```

### Output Response

**Response Model:** `PriceStatisticsResponse`

```json
{
  "isin": "IN0020220086",
  "period": "MAX",
  "price_data": [
    {
      "date": "2025-11-05",
      "price": 109.55,
      "price_5th_percentile": 109.55,
      "price_95th_percentile": 109.55
    },
    {
      "date": "2025-11-06",
      "price": 109.55,
      "price_5th_percentile": 109.55,
      "price_95th_percentile": 109.55
    },
    {
      "date": "2025-11-07",
      "price": 109.58,
      "price_5th_percentile": 109.55,
      "price_95th_percentile": 109.57
    }
  ],
  "metrics": {
    "median_price": 109.82,
    "price_5th_percentile": 109.55,
    "price_95th_percentile": 110.1,
    "implied_volatility": 0.24
  },
  "last_updated": "2025-12-05T19:58:50.960959"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isin` | string | ISIN identifier |
| `period` | string | Time period filter applied |
| `price_data` | array | Time series price data points with percentile bands |
| `price_data[].date` | string | Date (YYYY-MM-DD format) |
| `price_data[].price` | float | Current/actual price (solid line) |
| `price_data[].price_5th_percentile` | float | 5th percentile band (dashed line - lower) |
| `price_data[].price_95th_percentile` | float | 95th percentile band (dashed line - upper) |
| `metrics` | object | Price statistics metrics |
| `metrics.median_price` | float | Median price for the period |
| `metrics.price_5th_percentile` | float | 5th percentile price |
| `metrics.price_95th_percentile` | float | 95th percentile price |
| `metrics.implied_volatility` | float | Implied volatility (annualized, as percentage) |
| `last_updated` | string | ISO 8601 timestamp |

### Period Options

| Period | Description | Time Range |
|--------|-------------|------------|
| `1D` | Last 1 day | Current date - 1 day |
| `1W` | Last 1 week | Current date - 7 days |
| `1M` | Last 1 month | Current date - 30 days |
| `3M` | Last 3 months | Current date - 90 days |
| `YTD` | Year to date | January 1st to today |
| `1Y` | Last 1 year | Current date - 365 days |
| `MAX` | All available data | All historical data |

### Data Source

- Historical price data from `bond_price_forecasts.csv`
- Uses `Predicted_Price` column for price values
- Matches bonds by name between CSV files
- Calculates percentiles and volatility from historical data

### Error Responses

- **400 Bad Request:** Invalid period value
- **404 Not Found:** Bond not found or no price history available

---

## 7. Search Bonds for Comparison

**Endpoint:** `GET /api/v1/bonds/compare/search`

**Feature Usage:** Search bar in the "Compare Instruments" panel - allows users to search for bonds by ISIN or name before adding them to comparison.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `query` | string | Yes | Search query (ISIN or bond name) | `"GOI"` or `"IN0020220086"` |
| `limit` | integer | No | Maximum number of results (default: 10) | `5`, `20` |

### Request Example

```http
GET /api/v1/bonds/compare/search?query=GOI&limit=5
```

### Output Response

**Response Model:** `SearchResponse`

```json
{
  "results": [
    {
      "isin": "IN0020220086",
      "name": "GOI 12SP52",
      "issuer": "GOVERNMENT OF INDIA",
      "coupon_rate": 0.0736,
      "maturity_date": "2052-09-12",
      "current_yield": 0.0708,
      "current_yield_percent": 7.08,
      "yield_change": 0.0216,
      "yield_change_direction": "up"
    },
    {
      "isin": "IN0020210152",
      "name": "GOI 15DC35",
      "issuer": "GOVERNMENT OF INDIA",
      "coupon_rate": 0.0667,
      "maturity_date": "2035-12-15",
      "current_yield": 0.0638,
      "current_yield_percent": 6.38,
      "yield_change": 0.0173,
      "yield_change_direction": "up"
    }
  ],
  "total_results": 2
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | List of matching bonds |
| `results[].isin` | string | ISIN identifier |
| `results[].name` | string | Bond name (extracted from ISIN Description) |
| `results[].issuer` | string | Issuer name (e.g., "GOVERNMENT OF INDIA") |
| `results[].coupon_rate` | float | Annual coupon rate (as decimal, e.g., 0.0736 = 7.36%) |
| `results[].maturity_date` | string | Maturity date (YYYY-MM-DD format) |
| `results[].current_yield` | float | Current yield (as decimal) |
| `results[].current_yield_percent` | float | Current yield as percentage |
| `results[].yield_change` | float | Yield change (as decimal, from %CHNG column) |
| `results[].yield_change_direction` | string | Change direction: "up", "down", or "neutral" |
| `total_results` | integer | Total number of matching results |

### Error Responses

- **400 Bad Request:** Missing required `query` parameter
- **200 OK with empty results:** No bonds match the search query

---

## 8. Get Comparison List

**Endpoint:** `GET /api/v1/bonds/compare`

**Feature Usage:** Displays the current list of bonds in the "Compare Instruments" panel - shows all bonds the user has added for comparison.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `user_id` | string | No | User identifier for persistent comparisons | `"user123"` |
| `session_id` | string | No | Session identifier for temporary comparisons | `"session_abc"` |

**Note:** If neither `user_id` nor `session_id` is provided, uses `"default"` as the key.

### Request Example

```http
GET /api/v1/bonds/compare?session_id=abc123
```

### Output Response

**Response Model:** `ComparisonListResponse`

```json
{
  "comparison_id": "e91de360-69be-4b5c-8ecf-9e0bd4b023b2",
  "instruments": [
    {
      "isin": "IN0020220086",
      "name": "GOI 12SP52",
      "current_yield": 0.0708,
      "current_yield_percent": 7.08,
      "yield_change": 0.0216,
      "yield_change_direction": "up",
      "yield_change_symbol": "▲"
    },
    {
      "isin": "IN0020210152",
      "name": "GOI 15DC35",
      "current_yield": 0.0638,
      "current_yield_percent": 6.38,
      "yield_change": 0.0173,
      "yield_change_direction": "up",
      "yield_change_symbol": "▲"
    }
  ],
  "created_at": "2025-12-05T01:07:14.765000",
  "last_updated": "2025-12-05T01:07:27.301000"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `comparison_id` | string | Unique UUID identifier for this comparison |
| `instruments` | array | List of bonds in the comparison |
| `instruments[].isin` | string | ISIN identifier |
| `instruments[].name` | string | Bond name |
| `instruments[].current_yield` | float | Current yield (as decimal) |
| `instruments[].current_yield_percent` | float | Current yield as percentage (for display) |
| `instruments[].yield_change` | float | Yield change (as decimal) |
| `instruments[].yield_change_direction` | string | "up", "down", or "neutral" |
| `instruments[].yield_change_symbol` | string | Visual symbol: "▲" (up), "▼" (down), "—" (neutral) |
| `created_at` | string | ISO 8601 timestamp when comparison was created |
| `last_updated` | string | ISO 8601 timestamp when comparison was last modified |

### Special Behavior

- **Empty List:** If no comparison exists for the user/session, creates a new empty comparison and returns it with `instruments: []`
- **Storage:** Comparisons are stored in-memory (temporary, lost on server restart)

---

## 9. Add Bond to Comparison

**Endpoint:** `POST /api/v1/bonds/compare/add`

**Feature Usage:** "Add Bond to Compare" button - adds a selected bond to the comparison list.

### Input Parameters

**Request Body:** `AddToComparisonRequest`

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `isin` | string | Yes | ISIN identifier of bond to add | `"IN0020220086"` |
| `user_id` | string | No | User identifier | `"user123"` |
| `session_id` | string | No | Session identifier | `"session_abc"` |

### Request Example

```http
POST /api/v1/bonds/compare/add
Content-Type: application/json

{
  "isin": "IN0020220086",
  "session_id": "abc123"
}
```

### Output Response

**Response Model:** `ComparisonListResponse` (same structure as Get Comparison List)

```json
{
  "comparison_id": "e91de360-69be-4b5c-8ecf-9e0bd4b023b2",
  "instruments": [
    {
      "isin": "IN0020220086",
      "name": "GOI 12SP52",
      "current_yield": 0.0708,
      "current_yield_percent": 7.08,
      "yield_change": 0.0216,
      "yield_change_direction": "up",
      "yield_change_symbol": "▲"
    }
  ],
  "created_at": "2025-12-05T01:07:14.765000",
  "last_updated": "2025-12-05T01:07:27.301000"
}
```

### Response Fields

Same as [Get Comparison List](#7-get-comparison-list) response.

### Special Behavior

- **Duplicate Prevention:** If the bond is already in the comparison list, it is not added again (no error, returns existing list)
- **Auto-calculation:** Automatically calculates current yield and yield change from bond data

### Error Responses

- **404 Not Found:** Bond with the provided ISIN does not exist in `Final_Bond_Data.csv`
- **422 Unprocessable Entity:** Invalid request body format

---

## 10. Remove Bond from Comparison

**Endpoint:** `DELETE /api/v1/bonds/compare/remove`

**Feature Usage:** "X" button on each bond in the comparison panel - removes a bond from the comparison list.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `isin` | string | Yes | ISIN identifier of bond to remove | `"IN0020220086"` |
| `user_id` | string | No | User identifier | `"user123"` |
| `session_id` | string | No | Session identifier | `"session_abc"` |

### Request Example

```http
DELETE /api/v1/bonds/compare/remove?isin=IN0020220086&session_id=abc123
```

### Output Response

**Response Model:** `ComparisonListResponse` (same structure as Get Comparison List)

```json
{
  "comparison_id": "e91de360-69be-4b5c-8ecf-9e0bd4b023b2",
  "instruments": [
    {
      "isin": "IN0020210152",
      "name": "GOI 15DC35",
      "current_yield": 0.0638,
      "current_yield_percent": 6.38,
      "yield_change": 0.0173,
      "yield_change_direction": "up",
      "yield_change_symbol": "▲"
    }
  ],
  "created_at": "2025-12-05T01:07:14.765000",
  "last_updated": "2025-12-05T01:07:27.301000"
}
```

### Response Fields

Same as [Get Comparison List](#7-get-comparison-list) response.

### Error Responses

- **404 Not Found:** Comparison list does not exist for the provided user_id/session_id
- **400 Bad Request:** Missing required `isin` parameter

---

## 11. Get Comparison Details by ID

**Endpoint:** `GET /api/v1/bonds/compare/{comparison_id}/details`

**Feature Usage:** Retrieve a specific comparison by its unique ID - useful for sharing comparisons via link or retrieving saved comparisons.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `comparison_id` | string (path) | Yes | Unique UUID identifier of the comparison | `"e91de360-69be-4b5c-8ecf-9e0bd4b023b2"` |

### Request Example

```http
GET /api/v1/bonds/compare/e91de360-69be-4b5c-8ecf-9e0bd4b023b2/details
```

### Output Response

**Response Model:** `ComparisonDetailsResponse`

```json
{
  "comparison_id": "e91de360-69be-4b5c-8ecf-9e0bd4b023b2",
  "instruments": [
    {
      "isin": "IN0020220086",
      "name": "GOI 12SP52",
      "current_yield": 0.0708,
      "current_yield_percent": 7.08,
      "yield_change": 0.0216,
      "yield_change_direction": "up",
      "yield_change_symbol": "▲"
    },
    {
      "isin": "IN0020210152",
      "name": "GOI 15DC35",
      "current_yield": 0.0638,
      "current_yield_percent": 6.38,
      "yield_change": 0.0173,
      "yield_change_direction": "up",
      "yield_change_symbol": "▲"
    }
  ],
  "created_at": "2025-12-05T01:07:14.765000",
  "last_updated": "2025-12-05T01:07:27.301000"
}
```

### Response Fields

Same as [Get Comparison List](#8-get-comparison-list) response.

### Difference from Endpoint #8

- **Endpoint #8:** Uses `user_id` or `session_id` to find your current comparison
- **Endpoint #11:** Uses `comparison_id` to find any specific comparison (if you know the ID)

### Error Responses

- **404 Not Found:** Comparison with the provided ID does not exist

---

## 12. Get Bond Universe for Comparison

**Endpoint:** `GET /api/v1/bonds/universe/compare`

**Feature Usage:** Get all available bonds formatted for comparison - used to populate dropdowns, lists, or show the full bond universe for selection.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `search` | string | No | Filter by bond name or ISIN | `"GOI"` |
| `sector` | string | No | Filter by sector (not fully implemented) | - |
| `rating` | string | No | Filter by credit rating (not fully implemented) | - |

### Request Example

```http
GET /api/v1/bonds/universe/compare?search=GOI
```

### Output Response

**Response Model:** `SearchResponse` (same structure as Search endpoint)

```json
{
  "results": [
    {
      "isin": "IN0020220086",
      "name": "GOI 12SP52",
      "issuer": "GOVERNMENT OF INDIA",
      "coupon_rate": 0.0736,
      "maturity_date": "2052-09-12",
      "current_yield": 0.0708,
      "current_yield_percent": 7.08,
      "yield_change": 0.0216,
      "yield_change_direction": "up"
    },
    {
      "isin": "IN0020210152",
      "name": "GOI 15DC35",
      "issuer": "GOVERNMENT OF INDIA",
      "coupon_rate": 0.0667,
      "maturity_date": "2035-12-15",
      "current_yield": 0.0638,
      "current_yield_percent": 6.38,
      "yield_change": 0.0173,
      "yield_change_direction": "up"
    }
    // ... all matching bonds (no limit)
  ],
  "total_results": 106
}
```

### Response Fields

Same as [Search Bonds](#7-search-bonds-for-comparison) response.

### Key Differences from Search Endpoint

| Feature | Search Endpoint | Universe Endpoint |
|---------|----------------|-------------------|
| **Limit** | Limited results (default 10, max by limit) | All matching bonds (no limit) |
| **Use Case** | Quick search with pagination | Full universe display |
| **Performance** | Faster (limited results) | Slower (processes all bonds) |

### Data Source

- Reads from `Final_Bond_Data.csv` (294 bonds total)
- Processes every row and formats for comparison
- Applies search filter if provided


---

## 13. Submit Agent Query

**Endpoint:** `POST /api/v1/agent/query`

**Feature Usage:** AI agent query interface - allows users to ask natural language questions about bonds. Returns a query_id that can be used to retrieve the response output.

### Input Parameters

**Request Body:** `QueryRequest`

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `user_id` | string | Yes | User identifier | `"user123"` |
| `query` | string | Yes | User query text (natural language) | `"What is the risk profile of IN0020220086?"` |
| `isin` | string | No | Optional ISIN for bond-specific queries | `"IN0020220086"` |
| `context` | object | No | Optional context dictionary | `{"portfolio_id": "p123"}` |

### Request Example

```http
POST /api/v1/agent/query
Content-Type: application/json

{
  "user_id": "user123",
  "query": "What is the risk profile of IN0020220086?",
  "isin": "IN0020220086",
  "context": null
}
```

### Output Response

**Response Model:** `QueryResponse`

```json
{
  "query_id": "abc-123-def-456",
  "status": "completed",
  "processing_time": 2.45,
  "timestamp": "2025-12-05T01:00:02.450000"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `query_id` | string | Unique UUID identifier for this query (use this to retrieve output) |
| `status` | string | Query status: "completed", "processing", or "error" |
| `processing_time` | float | Processing time in seconds |
| `timestamp` | string | ISO 8601 timestamp of response |

### Special Behavior

- **Async Processing:** Query is processed asynchronously through OrchestratorV3
- **Storage:** Results are stored in-memory and can be retrieved later using `query_id`
- **Orchestrator Required:** Requires OrchestratorV3 to be available and configured
- **Output Retrieval:** Use the returned `query_id` with `GET /api/v1/agent/output` to retrieve the final response text

### Error Responses

- **503 Service Unavailable:** Orchestrator not available or not configured
- **500 Internal Server Error:** Failed to initialize orchestrator or process query
- **422 Unprocessable Entity:** Invalid request body format

---

## 14. Get Agent Output

**Endpoint:** `GET /api/v1/agent/output`

**Feature Usage:** Agent output display - retrieves the final text response from the ResponseAgent. The output is extracted from the ResponseAgent's generated response stored in the langraph state.

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `query_id` | string | Yes | Query identifier from agent response | `"abc-123-def-456"` |
| `user_id` | string | No | User identifier for validation | `"user123"` |

### Request Example

```http
GET /api/v1/agent/output?query_id=abc-123-def-456&user_id=user123
```

### Output Response

**Response Model:** `OutputResponse`

```json
{
  "query_id": "abc-123-def-456",
  "user_query": "What is the risk profile of IN0020220086?",
  "output": "The bond IN0020220086 (GOI 12SP52) has a moderate to high risk profile. With a duration of 27.7 years, it is highly sensitive to interest rate changes. The bond has a convexity of 768.49, indicating significant price volatility. The Value at Risk (VaR) at 95% confidence is 4.32%, suggesting moderate downside risk. Consider shorter duration bonds if you want to reduce interest rate risk.",
  "timestamp": "2025-12-05T01:00:02.450000"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `query_id` | string | Query identifier |
| `user_query` | string | Original user query |
| `output` | string | Final text response from ResponseAgent (formatted answer with analysis, recommendations, etc.) |
| `timestamp` | string | ISO 8601 timestamp of response |

### Error Responses

- **404 Not Found:** Query ID not found or output data not available
- **403 Forbidden:** Query ID does not belong to the provided user_id

---

## 15. Health Check

**Endpoint:** `GET /health`

**Feature Usage:** System health monitoring - used by monitoring systems, load balancers, and deployment tools to check API availability and orchestrator status.

### Input Parameters

None

### Request Example

```http
GET /health
```

### Output Response

```json
{
  "status": "healthy",
  "orchestrator_available": true
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | API status: "healthy" or "unhealthy" |
| `orchestrator_available` | boolean | Whether OrchestratorV3 is available and configured |

### Use Cases

- **Load Balancer Health Checks:** Verify API is responding
- **Monitoring Systems:** Track API availability
- **Deployment Verification:** Confirm successful deployment
- **Dependency Check:** Verify orchestrator availability

---

## Complete Workflow Example

### Scenario: Compare Multiple Bonds and View Graph

1. **Search for bonds:**
   ```http
   GET /api/v1/bonds/compare/search?query=GOI&limit=5
   ```

2. **Add first bond to comparison:**
   ```http
   POST /api/v1/bonds/compare/add
   Content-Type: application/json
   
   {
     "isin": "IN0020220086",
     "session_id": "user_session_123"
   }
   ```

3. **Add second bond to comparison:**
   ```http
   POST /api/v1/bonds/compare/add
   Content-Type: application/json
   
   {
     "isin": "IN0020210152",
     "session_id": "user_session_123"
   }
   ```

4. **View comparison list:**
   ```http
   GET /api/v1/bonds/compare?session_id=user_session_123
   ```

5. **View rate-yield overlay graph for first bond:**
   ```http
   GET /api/v1/bonds/IN0020220086/rate-yield-overlay?period=1Y
   ```

6. **Remove a bond from comparison:**
   ```http
   DELETE /api/v1/bonds/compare/remove?isin=IN0020210152&session_id=user_session_123
   ```

7. **Get comparison details by ID (for sharing):**
   ```http
   GET /api/v1/bonds/compare/e91de360-69be-4b5c-8ecf-9e0bd4b023b2/details
   ```

---

## Data Storage

### Comparison Storage

- **Type:** In-memory dictionary
- **Key:** `user_id` or `session_id` or `"default"`
- **Persistence:** Temporary (lost on server restart)
- **Structure:**
  ```python
  {
    "user_session_123": {
      "comparison_id": "uuid-here",
      "instruments": [...],
      "created_at": "timestamp",
      "last_updated": "timestamp"
    }
  }
  ```

### Agent Query Storage

- **Type:** In-memory dictionary
- **Key:** `query_id` (UUID)
- **Persistence:** Temporary (lost on server restart)
- **Structure:**
  ```python
  {
    "query_id": {
      "user_query": "query text",
      "user_id": "user123",
      "state": EnhancedAgentState,
      "state": EnhancedAgentState,
      "timestamp": "timestamp",
      "processing_time": 2.45
    }
  }
  ```

### Data Sources

| Endpoint | Data Source |
|----------|-------------|
| Get Bond Details, Get Bond Universe | `Final_Bond_Data.csv` |
| Get Yield History | `bond_price_forecasts.csv` (historical) |
| Rate-Yield Overlay | `bond_price_forecasts.csv` (historical) + `Final_Bond_Data.csv` (current) |
| Price Statistics | `bond_price_forecasts.csv` (historical price data) |
| Search, Universe Compare, Add, Remove | `Final_Bond_Data.csv` |
| Agent Query | OrchestratorV3 (uses RAG, bond data, and external APIs) |

---

## Notes

- All yield values are returned as decimals (e.g., 0.0708 = 7.08%)
- Percentage values are also provided for display (e.g., 7.08)
- Bond names are extracted from ISIN Description using regex patterns
- Yield changes are calculated from the `%CHNG` column in CSV
- Current yields are calculated from LTP/PREV.CLOSE and coupon rate
- All timestamps are in ISO 8601 format

---

## Error Handling

All endpoints follow standard HTTP status codes:
- **200 OK:** Successful request
- **400 Bad Request:** Invalid parameters
- **404 Not Found:** Resource not found (bond, comparison, etc.)
- **422 Unprocessable Entity:** Invalid request body format
- **500 Internal Server Error:** Server-side error

Error responses include a `detail` field with error message:
```json
{
  "detail": "Bond with ISIN INVALID_ISIN not found"
}
```

