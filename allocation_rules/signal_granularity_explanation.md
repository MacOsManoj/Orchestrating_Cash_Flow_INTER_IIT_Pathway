# Signal Granularity: Macro Allocation vs. Micro Selection

You asked a critical question: *How can "Stocks" have a single sentiment when every stock is different?*

The answer lies in separating **Asset Allocation** (The Orchestrator's Job) from **Asset Selection** (The Tool's Job).

## 1. The Top-Down Approach (Current Design)

The Orchestrator operates at the **Macro Level**. Its job is to decide *how much money* goes into the "Stock Bucket" vs. the "Bond Bucket".

To do this, it needs **Broad Market Signals**, not individual stock signals.

*   **Sentiment**: Refers to the **Benchmark Index** (e.g., NIFTY 50, S&P 500).
    *   *Why?* If the NIFTY 50 is crashing (Bearish), the *asset class* "Stocks" is risky, even if a few specific stocks are doing well.
*   **Volatility**: Refers to the **VIX** (Volatility Index) or the standard deviation of the Benchmark.

### The Workflow
1.  **Orchestrator (Macro)**:
    *   Input: "NIFTY 50 is Bearish, VIX is High."
    *   Decision: "Reduce Stock Allocation to 20%."
2.  **Stock Tool (Micro)**:
    *   Input: "Find me the best stocks to fill this 20% bucket."
    *   Action: Scans individual stocks. Finds the few "Defensive" or "Contra-trend" stocks that are surviving the crash.

---

## 2. The Bottom-Up Approach (Alternative)

If you have a specific **Watchlist** (e.g., "My 10 Tech Stocks"), the signals can be aggregated.

*   **Sentiment**: % of stocks in your watchlist above their 200-day Moving Average.
    *   *Example*: "8 out of 10 stocks are Bullish" -> **Aggregate Sentiment: Bullish**.
*   **Volatility**: Average Beta or ATR of your watchlist.

## 3. Recommendation for this Pipeline

We should stick to the **Top-Down Approach** for the Orchestrator because:
1.  **Stability**: Macro signals (Indices) are less noisy than individual stocks.
2.  **Purpose**: The Rule Engine is designed to protect capital from *Systemic Risk* (Market Crashes), which is best measured by Indices.

### How it works in practice:

| Step | Component | Input Signal | Decision |
| :--- | :--- | :--- | :--- |
| **1** | **Orchestrator** | **NIFTY 50 Trend** (Bearish) | "Allocate only 20% to Stocks" |
| **2** | **Stock Tool** | **Individual Tickers** | "Fill that 20% with ITC and HUL (Defensive Stocks)" |

**Conclusion**: The "Sentiment" and "Volatility" in `allocation_rules.md` refer to the **Market Regime** (The Ocean), not the individual boats.
