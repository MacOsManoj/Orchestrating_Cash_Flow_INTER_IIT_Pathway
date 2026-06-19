from .schema import (
    MarketSignals, PortfolioAllocation, PortfolioRecommendation,
    UserIntent, LiquidityRisk, MarketSentiment, Volatility, YieldTrend, CurrencyStrength
)

def calculate_allocation(signals: MarketSignals) -> PortfolioRecommendation:
    """
    Determines the asset allocation based on the Rule Matrix.
    """
    reasoning = []
    
    # --- 1. Base Anchors ---
    if signals.intent == UserIntent.CONSERVATIVE:
        alloc = {"Stocks": 0.20, "Bonds": 0.70, "Forex": 0.00, "Cash": 0.10}
        reasoning.append("Base Anchor: Conservative (S:20, B:70, F:0, C:10)")
    elif signals.intent == UserIntent.BALANCED:
        alloc = {"Stocks": 0.40, "Bonds": 0.50, "Forex": 0.05, "Cash": 0.05}
        reasoning.append("Base Anchor: Balanced (S:40, B:50, F:5, C:5)")
    else: # Aggressive
        alloc = {"Stocks": 0.70, "Bonds": 0.20, "Forex": 0.05, "Cash": 0.05}
        reasoning.append("Base Anchor: Aggressive (S:70, B:20, F:5, C:5)")

    # Helper to safely adjust allocation
    def adjust(target, amount, source=None):
        """
        Adjusts target asset by amount.
        If source is provided, subtracts from source.
        If source is NOT provided, we just change target and assume we balance later?
        No, the rules say "If you Add (+), you must Subtract (-) from another class."
        So we must specify source for every move, OR we normalize at the end?
        The rules specify sources in some cases, but not all.
        Let's follow the rules explicitly.
        """
        # We will modify 'alloc' directly
        pass

    # --- 2. Market State Rules (Priority 2) ---
    # Applied first so Priority 1 can override them
    
    # Rule 2.1: Risk-On (Bull Market)
    if signals.sentiment == MarketSentiment.BULLISH and signals.volatility != Volatility.HIGH:
        alloc["Stocks"] += 0.10
        alloc["Bonds"] -= 0.10
        reasoning.append("Rule 2.1 (Risk-On): Stocks +10%, Bonds -10%")

    # Rule 2.2: Flight to Safety (Bear/Crash)
    if signals.sentiment == MarketSentiment.BEARISH or signals.volatility == Volatility.HIGH:
        alloc["Stocks"] -= 0.15
        alloc["Bonds"] += 0.10
        alloc["Cash"] += 0.05
        reasoning.append("Rule 2.2 (Flight to Safety): Stocks -15%, Bonds +10%, Cash +5%")

    # Rule 2.3: Interest Rate Hedge (Rising Yields)
    if signals.yield_trend == YieldTrend.RISING:
        alloc["Bonds"] -= 0.10
        alloc["Cash"] += 0.10
        reasoning.append("Rule 2.3 (Rate Hedge): Bonds -10%, Cash +10%")

    # Rule 2.4: Forex Opportunity Scaling (New Logic)
    # Base Forex is usually low (0-5%). We scale it up to 10% based on Opportunity Index.
    # Formula: Target Forex = 0.10 * signals.forex_opportunity_index
    # We take the difference from Stocks (Risk Asset) or Cash (Safe Asset) depending on Intent.
    
    target_forex = 0.10 * signals.forex_opportunity_index
    current_forex = alloc["Forex"]
    
    if target_forex > current_forex:
        diff = target_forex - current_forex
        alloc["Forex"] = target_forex
        
        # Fund it from Stocks (if Aggressive/Balanced) or Cash (if Conservative)
        if signals.intent == UserIntent.CONSERVATIVE:
             alloc["Cash"] -= diff
             reasoning.append(f"Forex Opportunity ({signals.forex_opportunity_index:.2f}): Increased Forex to {target_forex*100:.1f}%, funded by Cash.")
        else:
             alloc["Stocks"] -= diff
             reasoning.append(f"Forex Opportunity ({signals.forex_opportunity_index:.2f}): Increased Forex to {target_forex*100:.1f}%, funded by Stocks.")

    # --- 3. Survival Rules (Priority 1) ---
    # These override previous settings
    
    # Rule 1.1: Liquidity Crisis
    if signals.liquidity_risk == LiquidityRisk.HIGH:
        current_cash = alloc["Cash"]
        if current_cash < 0.25:
            deficit = 0.25 - current_cash
            alloc["Cash"] = 0.25
            reasoning.append(f"Rule 1.1 (Liquidity Crisis): Cash set to 25% (Needed +{deficit:.2f})")
            
            # Pull from Bonds first (as per Scenario A example), then Stocks
            # Strategy: Try to take from Bonds first
            if alloc["Bonds"] >= deficit:
                alloc["Bonds"] -= deficit
                reasoning.append(f"  -> Pulled {deficit:.2f} from Bonds")
            else:
                # Take all from Bonds
                remaining = deficit - alloc["Bonds"]
                reasoning.append(f"  -> Pulled {alloc['Bonds']:.2f} from Bonds")
                alloc["Bonds"] = 0.0
                # Take rest from Stocks
                alloc["Stocks"] -= remaining
                reasoning.append(f"  -> Pulled {remaining:.2f} from Stocks")

    # Rule 1.2: Surplus Optimization
    if signals.liquidity_risk == LiquidityRisk.LOW and signals.volatility == Volatility.LOW:
        if alloc["Cash"] > 0.02:
            surplus = alloc["Cash"] - 0.02
            alloc["Cash"] = 0.02
            alloc["Bonds"] += surplus
            reasoning.append(f"Rule 1.2 (Surplus Opt): Cash reduced to 2%, moved {surplus:.2f} to Bonds")

    # --- 4. Final Validation & Normalization ---
    # Ensure no negative values
    for k in alloc:
        if alloc[k] < 0:
            reasoning.append(f"Warning: {k} was negative ({alloc[k]:.2f}), clipped to 0.")
            alloc[k] = 0.0
            
    # Normalize to 1.0
    total = sum(alloc.values())
    if abs(total - 1.0) > 0.001:
        reasoning.append(f"Normalization: Total was {total:.2f}, rescaling.")
        for k in alloc:
            alloc[k] /= total

    final_alloc = PortfolioAllocation(
        stocks=round(alloc["Stocks"], 3),
        bonds=round(alloc["Bonds"], 3),
        forex=round(alloc["Forex"], 3),
        cash=round(alloc["Cash"], 3)
    )

    return PortfolioRecommendation(
        allocation=final_alloc,
        reasoning="\n".join(reasoning)
    )
