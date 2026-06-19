# Forex Strategy & Allocation Logic

You asked for a detailed explanation of the Forex component in our pipeline. Here is the breakdown based on financial principles.

## 1. What is `dom_currency`?

**`dom_currency`** stands for **Domestic Currency Strength**.
*   **Definition**: The strength of *your* home currency (e.g., USD for a US investor, INR for an Indian investor) relative to a basket of major foreign currencies.
*   **Impact**:
    *   **Strong Domestic Currency**: Reduces the value of foreign investments when converted back. (e.g., You own Apple stock in USD. If INR gets stronger, your USD is worth fewer Rupees).
    *   **Weak Domestic Currency**: Increases the value of foreign investments. (The "Currency Boost").

**Rule Logic**:
*   If `dom_currency == WEAK`: We **increase** Forex/Foreign Asset allocation to capture the currency gain.
*   If `dom_currency == STRONG`: We **reduce** Forex exposure to avoid currency drag.

## 2. Why is Forex Allocation Low (even in Aggressive)?

You noticed that even in "Aggressive" portfolios, Forex is often capped at 5-10%. This is intentional.

### Reason A: Forex is a Zero-Sum Game
Unlike Stocks (which grow with human productivity) or Bonds (which pay interest), Currencies do not generate inherent value. For one currency to go up, another *must* go down.
*   *Implication*: Long-term expected return of holding a currency is **Zero** (excluding interest). It is a **Hedge**, not a Growth Engine.

### Reason B: Volatility without Reward
Unhedged currency exposure adds significant volatility to a portfolio (often 2nd highest after Equities) without adding proportional expected returns [Vanguard, MSCI].
*   *Citation*: "Currency contribution to portfolio volatility is significant... often outweighing diversification benefits." [MSCI]

### Reason C: The "Carry Trade" Risk
Aggressive Forex strategies (Carry Trade) involve borrowing low-yield currencies to buy high-yield ones. This works in calm markets but crashes spectacularly in crises (e.g., 2008 Yen unwind). We limit allocation to prevent "blowing up" the portfolio.

## 3. Better Signals for Forex Allocation

To make smarter decisions than just "Strong/Weak", we can add these signals:

### A. Interest Rate Differential (IRD)
*   **Logic**: Money flows to currencies with higher interest rates.
*   **Signal**: `(Target Rate - Home Rate)`.
*   **Action**: If Positive & Growing -> Bullish for that Forex pair.

### B. Geopolitical Risk Index (GPR)
*   **Logic**: In times of war/instability, money flees to "Safe Havens" (USD, CHF, Gold).
*   **Action**: If GPR is High -> Shift Forex allocation to Safe Havens.

### C. Purchasing Power Parity (PPP)
*   **Logic**: Long-term valuation metric. Is the currency overvalued?
*   **Action**: Avoid currencies that are historically expensive vs. PPP.

## 4. Proposed Changes to Base Rules

Based on this, we can refine the `allocation_rules.md`:

1.  **Split "Forex" into "Foreign Equities" vs "Pure Currency"**:
    *   Most "Forex" allocation should actually be **Unhedged Foreign Stocks** (to get Growth + Currency play).
    *   Pure Currency trading should remain < 5%.

2.  **New Rule**:
    *   *If IRD > 2% AND Volatility is Low*: Increase Carry Trade allocation (up to 10%).
    *   *If Volatility is High*: Cut all Carry Trades immediately.

## Summary
*   **`dom_currency`** protects you from your own currency getting too strong.
*   **Low Allocation** is because Forex doesn't "grow" like companies do.
*   **New Signals**: Interest Rate Differentials are the best next step.
