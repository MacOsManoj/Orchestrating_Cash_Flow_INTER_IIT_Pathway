# Correlation-Based Risk Mitigation Strategy

## 1. The Core Concept: "The Only Free Lunch in Finance"
The goal is to construct a portfolio where assets have **negative or low correlation**.
*   **Positive Correlation (+1.0)**: Assets move together. (High Risk: If one crashes, all crash).
*   **Negative Correlation (-1.0)**: Assets move opposite. (Hedge: If one crashes, the other profits).
*   **Zero Correlation (0.0)**: Assets are independent. (Diversification).

**Objective**: Dynamically adjust weights not just based on *individual* asset signals (Bullish/Bearish), but on how they *interact* with each other.

---

## 2. New Tool Requirements

To implement this, the Orchestrator needs a "Macro View" of asset relationships. We need a new tool or an enhancement to existing ones.

### A. The `CorrelationMatrixTool` (New)
This tool calculates the rolling correlation between major asset classes over a specific lookback period (e.g., 30 days, 90 days).

**Input**: `lookback_period` (e.g., "30d")
**Output**:
```json
{
  "correlations": {
    "stocks_bonds": -0.4,  # Good (Traditional Hedge)
    "stocks_forex": 0.1,   # Neutral
    "bonds_forex": -0.2
  },
  "regime": "NORMAL_DIVERSIFICATION" # or "CORRELATION_BREAKDOWN"
}
```

### B. Pipeline Enhancements (Data Requirements)
To calculate correlation, the Orchestrator needs **Time-Series Data**, not just a single snapshot.

Each Pipeline (Stocks, Bonds, Forex) must expose a new tool/endpoint: `get_historical_returns`.

**1. API Signature**
*   **Function**: `get_historical_returns(lookback_days: int)`
*   **Returns**: A list of daily percentage returns for the *Benchmark Index* of that asset class.

**2. Specific Inputs per Pipeline**
*   **Stocks Pipeline**:
    *   *Input*: `lookback_days=90`
    *   *Data Source*: NIFTY 50 or S&P 500 Daily Returns.
    *   *Why Index?* We are correlating the "Stock Market" (Asset Class), not individual stocks.
    *   *JSON Output*:
        ```json
        [
          {"date": "2023-10-01", "value": 0.012},  // +1.2%
          {"date": "2023-10-02", "value": -0.005}, // -0.5%
          ...
        ]
        ```

*   **Bonds Pipeline**:
    *   *Data Source*: 10-Year Government Bond Yield Returns (or Bond ETF returns).
    *   *Critical*: Must be the *Price Return* of the bond, not just the yield. (Price moves inverse to Yield).

*   **Forex Pipeline**:
    *   *Data Source*: USD/INR (or user's home currency pair) Daily Returns.

**3. The Calculation (Orchestrator Side)**
The `CorrelationMatrixTool` will:
1.  Fetch these 3 JSON arrays.
2.  Align them by Date (Inner Join).
3.  Compute Pearson Correlation Coefficient ($r$) between the arrays.
    *   $r = \frac{\sum(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum(x_i - \bar{x})^2 \sum(y_i - \bar{y})^2}}$

---

## 3. Orchestrator Logic Updates

We will add a **"Risk Parity / Correlation Check"** layer *after* the Rule Engine but *before* Final Allocation.

### Logic Flow
1.  **Rule Engine**: Generates initial split (e.g., Stocks 60%, Bonds 40%).
2.  **Correlation Check**:
    *   **Scenario 1 (Ideal)**: `Corr(Stocks, Bonds) < -0.2`.
        *   *Action*: Keep allocation. The hedge is working.
    *   **Scenario 2 (Danger - Correlation Breakdown)**: `Corr(Stocks, Bonds) > 0.5`.
        *   *Meaning*: Stocks and Bonds are falling together (e.g., Inflation Shock).
        *   *Action*: **Trigger "Alternative Flight"**.
            *   Reduce BOTH Stocks and Bonds.
            *   Increase **Cash** or **Forex** (if negatively correlated).
            *   *New Rule*: `If Corr(S, B) > 0.5, Reduce (S+B) by 20%, Move to Cash/Gold.`

---

## 4. Example: "The Inflation Shock" (Stocks & Bonds Fall Together)

*   **Initial Rule Output**: Stocks 50%, Bonds 40%, Cash 10%.
*   **Correlation Signal**: `stocks_bonds_corr = +0.8` (High Positive! Danger!).
*   **Risk Mitigation Logic**:
    *   "Traditional 60/40 hedge is broken."
    *   Identify asset with lowest correlation to Stocks (e.g., Cash or USD).
    *   **Adjustment**:
        *   Stocks: 50% -> 30%
        *   Bonds: 40% -> 20%
        *   Cash: 10% -> 50%
*   **Final Allocation**: S:30, B:20, C:50.

## 5. Summary of Changes
1.  **New Tool**: `CorrelationMatrixTool`.
2.  **New Logic Layer**: `apply_correlation_adjustment(allocation, correlation_matrix)`.
3.  **Data Requirement**: Pipelines must stream historical data for real-time correlation updates.
