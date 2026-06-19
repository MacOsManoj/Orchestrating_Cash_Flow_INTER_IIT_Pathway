# Forex Signal Aggregation & Allocation Design

## The Challenge
We have 6 Currency Pairs (e.g., USD/INR, EUR/INR, USD/JPY...).
*   **Inputs per Pair**: Volatility, Sharpe Ratio, Sentiment (Bullish/Bearish).
*   **Constraint**: Shorting is allowed (Bearish = Profit Opportunity).
*   **Goal**: Decide the *Total Portfolio Allocation* to Forex (0% to 10%?).

## The Logic: "Net Conviction Score"

Since we can profit from both Up (Long) and Down (Short) moves, a "Bearish" signal is just as valuable as a "Bullish" one, *provided the trend is strong*.

We will calculate a **Conviction Score** for each pair and aggregate them to decide the total "Forex Appetite".

### Step 1: Pair-Level Scoring (Client-Side Tool)
The `forex_tool.py` (Client) will query the Pipeline for the 6 pairs and compute a score for each.

**Formula per Pair:**
`Score = Direction_Multiplier * Quality_Factor`

1.  **Direction_Multiplier**:
    *   Bullish: `1.0` (Long)
    *   Bearish: `1.0` (Short) -> *Crucial: We treat direction magnitude equally.*
    *   Neutral: `0.0`

2.  **Quality_Factor** (The "Intelligence"):
    *   Based on **Sharpe Ratio** (Risk-Adjusted Return).
    *   *If Sharpe > 1.5*: `High Conviction (1.0)`
    *   *If Sharpe 0.5 - 1.5*: `Medium Conviction (0.5)`
    *   *If Sharpe < 0.5*: `Low Conviction (0.1)`

3.  **Volatility Penalty**:
    *   If Volatility is *Extreme* (> 99th percentile), force Score to 0 (Too risky to trade).

**Result**: Each pair gets a score from `0.0` to `1.0` representing "How good is this trade opportunity?"

### Step 2: Portfolio-Level Aggregation (Orchestrator Rule Engine)
Now we sum the opportunities to decide the **Total Allocation**.

`Total_Forex_Opportunity = Sum(Pair_Scores) / Total_Pairs`
*   Range: 0.0 (No good trades) to 1.0 (All 6 pairs are screaming buys/sells).

### Step 3: Allocation Mapping
We map the `Total_Forex_Opportunity` to our Portfolio Weight limits (e.g., 0% to 10%).

| Opportunity Score | Logic | Allocation Action |
| :--- | :--- | :--- |
| **< 0.2** | Market is choppy/risky. No clear trends. | **Min Allocation (0-2%)** |
| **0.2 - 0.6** | Some decent trends (Long or Short). | **Base Allocation (5%)** |
| **> 0.6** | Strong trends across board (e.g., USD breakout). | **Max Allocation (10%)** |

## Implementation Plan

### 1. `forex_tool.py` (Client)
*   **Input**: JSON list of 6 pairs from Pipeline.
*   **Process**:
    ```python
    total_opportunity = 0
    for pair in pairs:
        if pair.volatility == "EXTREME": continue
        
        strength = 0.1
        if pair.sharpe > 1.5: strength = 1.0
        elif pair.sharpe > 0.5: strength = 0.5
        
        # Direction doesn't matter for allocation size, only that a trend EXISTS
        if pair.sentiment != "NEUTRAL":
            total_opportunity += strength
            
    return {"forex_opportunity_index": total_opportunity / 6}
    ```

### 2. `rules_engine.py` (Orchestrator)
*   **Input**: `forex_opportunity_index` (0.0 - 1.0).
*   **Logic**:
    ```python
    target_forex_allocation = 0.10 * signals.forex_opportunity_index
    # Clip to min/max bounds based on User Intent (Conservative vs Aggressive)
    ```

## Why this works?
1.  **Handles Shorting**: By treating Bullish/Bearish as equal "Trend Opportunities", we allocate capital whenever there is money to be made, regardless of direction.
2.  **Risk-Adjusted**: Using Sharpe Ratio ensures we don't allocate capital to volatile, choppy pairs.
3.  **Dynamic**: If the forex market goes dead (low volatility, low sharpe), the allocation naturally drops to near 0%, preserving capital for Stocks/Bonds.
