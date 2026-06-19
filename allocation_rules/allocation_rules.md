# Asset Allocation Logic & Rule Engine

## 1. System Inputs (Standardized Signals)
The Orchestrator accepts the following standardized signals from the Pathway MCP Tools:

| Pipeline | Signal Name | Possible Values | Meaning |
| :--- | :--- | :--- | :--- |
| **User** | `intent` | `Conservative`, `Balanced`, `Aggressive` | The starting anchor point. |
| **Cashflow** | `liquidity_risk` | `LOW`, `MEDIUM`, `HIGH` | Probability of needing immediate cash. |
| **Stocks** | `sentiment` | `BULLISH`, `BEARISH`, `NEUTRAL` | General market direction. |
| **Stocks** | `volatility` | `LOW`, `NORMAL`, `HIGH` | Market fear gauge (VIX/ATR). |
| **Bonds** | `yield_trend` | `RISING`, `FALLING`, `FLAT` | Interest rate direction (Price inverse to yield). |
| **Forex** | `dom_currency` | `STRONG`, `WEAK` | Strength of domestic currency vs basket. |

---

## 2. Base Anchors (Starting Point)
Before looking at the market, set the baseline based on User Intent.

| Asset Class | Conservative | Balanced | Aggressive |
| :--- | :--- | :--- | :--- |
| **Stocks** | 20% | 40% | 70% |
| **Bonds** | 70% | 50% | 20% |
| **Forex** | 0% | 5% | 5% |
| **Cash** | 10% | 5% | 5% |
| **TOTAL** | **100%** | **100%** | **100%** |

---

## 3. The Rule Matrix (Shifting Logic)
Apply these rules sequentially. Rules with higher priority override lower ones.
**Constraint:** *Total Allocation must always sum to 100%. If you Add (+), you must Subtract (-) from another class.*

### Priority 1: Survival Rules (Cashflow Veto)
*These rules trigger first to ensure solvency.*

**Rule 1.1: The Liquidity Crisis Protocol**
> **IF** `liquidity_risk` == `HIGH`
> **THEN** > * **Cash:** Increase to **Minimum 25%** (Pull from Stocks first, then Bonds).
> * **Reasoning:** "High probability of operational outflow detected. Liquidating assets to prevent default."

**Rule 1.2: The Surplus Optimization**
> **IF** `liquidity_risk` == `LOW` **AND** `volatility` == `LOW`
> **THEN**
> * **Cash:** Reduce to **2%** (Move surplus to Bonds).
> * **Reasoning:** "Excess idle cash detected with low risk. Deploying to income-generating Bonds."

---

### Priority 2: Market State Rules (Tactical Shifts)
*These rules adjust for market opportunities and threats.*

**Rule 2.1: The "Risk-On" Boost (Bull Market)**
> **IF** `sentiment` == `BULLISH` **AND** `volatility` != `HIGH`
> **THEN**
> * **Stocks:** +10% 
> * **Bonds:** -10%
> * **Reasoning:** "Positive market momentum identified. Overweighting Equities to capture alpha."

**Rule 2.2: The "Flight to Safety" (Bear Market/Crash)**
> **IF** `sentiment` == `BEARISH` **OR** `volatility` == `HIGH`
> **THEN**
> * **Stocks:** -15%
> * **Bonds:** +10%
> * **Cash:** +5%
> * **Reasoning:** "High volatility or negative sentiment detected. Reducing Equity exposure to preserve capital."

**Rule 2.3: The Interest Rate Hedge (Bond Rout)**
> **IF** `yield_trend` == `RISING` (Means Bond Prices are Falling)
> **THEN**
> * **Bonds:** -10%
> * **Cash:** +10% (Or move to Ultra-Short Duration Bonds)
> * **Reasoning:** "Rising yield environment hurts bond prices. Shortening duration and moving to Cash."

**Rule 2.4: The Forex Hedge (Currency Weakness)**
> **IF** `dom_currency` == `WEAK` **AND** `intent` != `Conservative`
> **THEN**
> * **Forex:** +5%
> * **Stocks:** -5%
> * **Reasoning:** "Domestic currency weakening. Increasing foreign currency exposure to hedge purchasing power."

---

## 4. Conflict Resolution (The Tie-Breaker)
If rules conflict (e.g., Stock Market is Bullish, but Cashflow Risk is High), follow this hierarchy:

1.  **Cashflow Constraint** (Always wins).
2.  **Volatility Constraint** (Safety second).
3.  **Market Sentiment** (Growth third).

---

## 5. Example Calculations

**Scenario A: "The Perfect Storm"**
* **User:** Balanced (Start: S:40, B:50, F:5, C:5)
* **Signals:**
    * Cashflow: `HIGH` (Need money)
    * Sentiment: `BEARISH` (Market crashing)
    * Volatility: `HIGH` (Panic)

* **Logic Steps:**
    1.  *Base:* S:40, B:50, F:5, C:5.
    2.  *Rule 2.2 (Bear):* Stocks -15% (to 25), Bonds +10% (to 60), Cash +5% (to 10). -> State: S:25, B:60, F:5, C:10.
    3.  *Rule 1.1 (High Liquidity Risk - OVERRIDE):* Cash must be 25%. Currently 10%. Need +15%.
    4.  *Source of Cash:* Pull from Bonds (most liquid after cash). Bonds -15% (to 45).
    
* **Final Output:**
    * **Stocks:** 25%
    * **Bonds:** 45%
    * **Forex:** 5%
    * **Cash:** 25%

**Scenario B: "Aggressive Growth"**
* **User:** Aggressive (Start: S:70, B:20, F:5, C:5)
* **Signals:**
    * Cashflow: `LOW`
    * Sentiment: `BULLISH`
    * Yields: `FLAT`

* **Logic Steps:**
    1.  *Base:* S:70, B:20, F:5, C:5.
    2.  *Rule 2.1 (Bull):* Stocks +10% (to 80), Bonds -10% (to 10).
    3.  *Rule 1.2 (Surplus):* Cash -3% (to 2%), Add to Bonds (+3% to 13%).
    
* **Final Output:**
    * **Stocks:** 80%
    * **Bonds:** 13%
    * **Forex:** 5%
    * **Cash:** 2%