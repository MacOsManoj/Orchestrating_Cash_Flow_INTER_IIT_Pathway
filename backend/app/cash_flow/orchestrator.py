import sys
import os
import requests
from bs4 import BeautifulSoup
import re

from app.cash_flow.liquidity_risk_tools import predict_liquidity_regime
from app.cash_flow.market_regime import get_market_regime_simplified


def get_rbi_policy_rates() -> dict:
    """
    Fetch current RBI Policy Rates (CRR and SLR).
    """
    rates = {"CRR": 0.0450, "SLR": 0.1800}
    try:
        url = "https://tradingeconomics.com/india/cash-reserve-ratio"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text()
            summary_match = re.search(
                r"Cash Reserve Ratio in India.*?(\d+\.\d+)\s+percent",
                text,
                re.IGNORECASE,
            )
            if summary_match:
                rates["CRR"] = float(summary_match.group(1)) / 100.0
        return rates
    except Exception:
        return rates


def calculate_portfolio_breakdown(investment_ratio, base_slr, market_state, preference):
    """
    Breaks down the Investment Ratio (IR) into asset classes.
    Mandatory: G-Secs must cover base_slr first.
    """
    mandatory_gsec = base_slr
    discretionary_capital = max(0, investment_ratio - mandatory_gsec)

    weights = {}

    if preference == "Aggressive":
        if market_state == "High":
            weights = {"Stocks": 0.70, "CorpBonds": 0.20, "Forex": 0.10, "GSec": 0.00}
        elif market_state == "Medium":
            weights = {"Stocks": 0.50, "CorpBonds": 0.30, "Forex": 0.10, "GSec": 0.10}
        else:
            weights = {"Stocks": 0.30, "CorpBonds": 0.40, "Forex": 0.10, "GSec": 0.20}

    elif preference == "Safe":
        if market_state == "High":
            weights = {"Stocks": 0.20, "CorpBonds": 0.40, "Forex": 0.05, "GSec": 0.35}
        else:
            weights = {"Stocks": 0.05, "CorpBonds": 0.20, "Forex": 0.05, "GSec": 0.70}

    else:  # Normal
        if market_state == "High":
            weights = {"Stocks": 0.50, "CorpBonds": 0.30, "Forex": 0.10, "GSec": 0.10}
        elif market_state == "Medium":
            weights = {"Stocks": 0.30, "CorpBonds": 0.40, "Forex": 0.10, "GSec": 0.20}
        else:
            weights = {"Stocks": 0.10, "CorpBonds": 0.40, "Forex": 0.10, "GSec": 0.40}

    allocation = {
        "Govt_Bonds": mandatory_gsec + (discretionary_capital * weights.get("GSec", 0)),
        "Corp_Bonds": discretionary_capital * weights.get("CorpBonds", 0),
        "Stocks": discretionary_capital * weights.get("Stocks", 0),
        "Forex": discretionary_capital * weights.get("Forex", 0),
    }
    return allocation


def determine_allocation_ratios():
    """
    Main Orchestrator Function.
    Returns base allocation ratios AND detailed portfolio breakdowns for all risk profiles.
    """

    # --- Step 0: Regulatory Base ---
    print("Fetching Real-time RBI Policy Rates...")
    rbi_rates = get_rbi_policy_rates()
    base_crr = rbi_rates.get("CRR", 0.045)
    base_slr = rbi_rates.get("SLR", 0.18)
    print(f"RBI Mandates -> CRR: {base_crr:.2%}, SLR: {base_slr:.2%}")

    # --- Step 1: Liquidity Regime ---
    print("\nFetching Liquidity Regime...")
    try:
        liquidity_result = predict_liquidity_regime()
        is_high_liquidity_risk = liquidity_result.get("alert_status", False)
        liquidity_state = "High Risk" if is_high_liquidity_risk else "Normal"
        print(f"Liquidity State: {liquidity_state}")
    except Exception:
        is_high_liquidity_risk = True
        liquidity_state = "High Risk (Default)"

    # --- Step 2: Market Regime ---
    print("\nFetching Market Data...")
    try:
        market_result = get_market_regime_simplified()
        market_state = market_result.get("regime", "Medium")
        print(f"Market State:    {market_state}")
    except Exception:
        market_state = "Medium"

    # --- Step 3: Calculate Base Buffers ---
    if liquidity_state == "Normal":
        rr_buffer = 0.02
    else:
        rr_buffer = 0.10

    if market_state == "High":
        ir_buffer = 0.20
    elif market_state == "Medium":
        ir_buffer = 0.10
    else:
        ir_buffer = 0.02

    if is_high_liquidity_risk:
        ir_buffer *= 0.5

    final_rr = base_crr + rr_buffer
    final_ir = base_slr + ir_buffer
    final_lr = 1.0 - (final_rr + final_ir)

    if final_lr < 0:
        scale = 1.0 / (final_rr + final_ir)
        final_rr *= scale
        final_ir *= scale
        final_lr = 0.0

    # --- Step 4: Calculate Portfolios for ALL preferences ---
    strategies = ["Aggressive", "Normal", "Safe"]
    portfolios = {}

    for strat in strategies:
        portfolios[strat] = calculate_portfolio_breakdown(
            final_ir, base_slr, market_state, strat
        )

    return {
        "states": {"liquidity": liquidity_state, "market": market_state},
        "ratios": {"RR": final_rr, "IR": final_ir, "LR": final_lr},
        "portfolios": portfolios,
        "rbi": {"CRR": base_crr, "SLR": base_slr},
    }


if __name__ == "__main__":
    result = determine_allocation_ratios()

    r = result["ratios"]

    print("\n" + "=" * 60)
    print(" FINAL STRATEGY & PORTFOLIO ALLOCATION")
    print("=" * 60)
    print(
        f"CONDITIONS: Liquidity={result['states']['liquidity']} | Market={result['states']['market']}"
    )
    print("-" * 60)
    print(
        f"1. CASH RESERVE (RR):   {r['RR']:.2%} (Min CRR: {result['rbi']['CRR']:.2%})"
    )
    print(f"2. LOAN BOOK (LR):      {r['LR']:.2%}")
    print(
        f"3. INVESTMENTS (IR):    {r['IR']:.2%} (Min SLR: {result['rbi']['SLR']:.2%})"
    )
    print("-" * 60)

    for strategy, p in result["portfolios"].items():
        print(f"\n[{strategy.upper()} PORTFOLIO BREAKDOWN]")
        print(f"   > Govt Bonds (SLR+): {p['Govt_Bonds']:.2%}")
        print(f"   > Corporate Bonds:   {p['Corp_Bonds']:.2%}")
        print(f"   > Equity / Stocks:   {p['Stocks']:.2%}")
        print(f"   > Forex / Hedging:   {p['Forex']:.2%}")
    print("=" * 60)
