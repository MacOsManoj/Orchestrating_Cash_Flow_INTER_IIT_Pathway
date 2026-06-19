from app.cash_flow.market_tools import (
    get_fii_dii_via_nsepython,
    get_india_vix,
    get_advance_decline_analysis,
    get_bond_yields,
)


def get_market_regime_simplified():
    """
    Returns 'High', 'Medium', or 'Low' representing Market Strength,
    along with detailed metrics and explanations.
    """
    vix_data = get_india_vix()
    fii_dii_data = get_fii_dii_via_nsepython()
    breadth_data = get_advance_decline_analysis()
    bond_data = get_bond_yields()

    score = 0
    indicators = {}

    # --- 1. Volatility (VIX) ---
    vix = vix_data.get("current_vix", 15)
    vix_z = vix_data.get("zscore", 0)

    if vix < 13:
        if vix_z < -2:
            score += 18
            vix_explanation = (
                "Complacent - VIX extremely low, potential for volatility spike"
            )
        else:
            score += 25
            vix_explanation = "Stable - Low fear, bullish sentiment"
    elif vix <= 17:
        score += 15
        vix_explanation = "Normal - Market volatility within expected range"
    else:
        score += 0
        vix_explanation = "High Fear - Elevated volatility, risk-off sentiment"

    indicators["vix"] = {"value": vix, "zscore": vix_z, "explanation": vix_explanation}

    # --- 2. Liquidity (FII/DII) ---
    net_flow = sum(float(str(p["netValue"]).replace(",", "")) for p in fii_dii_data)

    if net_flow > 1500:
        score += 30
        flow_explanation = "Heavy Buying - Strong institutional inflows"
    elif net_flow > 0:
        score += 20
        flow_explanation = "Net Positive - Mild institutional buying"
    elif net_flow > -500:
        score += 10
        flow_explanation = "Neutral - Mild institutional selling, not alarming"
    else:
        score += 0
        flow_explanation = "Heavy Selling - Significant institutional outflows"

    indicators["net_flow"] = {"value": net_flow, "explanation": flow_explanation}

    # --- 3. Breadth (AD Ratio) ---
    ad_ratio = breadth_data.get("ad_ratio", 1.0)

    if ad_ratio >= 1.5:
        score += 25
        ad_explanation = "Strong Participation - Broad market rally, healthy trend"
    elif ad_ratio >= 1.0:
        score += 15
        ad_explanation = "Positive - More stocks advancing than declining"
    else:
        score += 0
        ad_explanation = "Negative - More stocks declining, weak breadth"

    indicators["ad_ratio"] = {"value": ad_ratio, "explanation": ad_explanation}

    # --- 4. Macro (10Y Yields) ---
    bond_10y = next((i for i in bond_data if i["Bonds"] == "India 10Y"), None)
    if bond_10y:
        day_change = bond_10y["Day"]
        if day_change < 0:
            score += 20
            bond_explanation = "Yields Falling - Flight to safety easing, risk-on"
        elif day_change < 0.05:
            score += 10
            bond_explanation = "Flat - Stable bond market, no major macro shifts"
        else:
            score += 0
            bond_explanation = (
                "Yields Rising - Tightening conditions, headwind for equities"
            )

        indicators["bond_10y"] = {
            "yield": bond_10y.get("Yield"),
            "day_change": day_change,
            "explanation": bond_explanation,
        }
    else:
        indicators["bond_10y"] = {
            "yield": None,
            "day_change": None,
            "explanation": "Data unavailable",
        }

    # --- SIMPLIFIED CLASSIFICATION ---
    if score > 66:
        regime = "High"
        regime_explanation = "Bullish - Strong market conditions favoring risk assets"
    elif score > 33:
        regime = "Medium"
        regime_explanation = "Sideways - Mixed signals, selective opportunities"
    else:
        regime = "Low"
        regime_explanation = "Bearish - Weak conditions, caution advised"

    return {
        "score": score,
        "regime": regime,
        "regime_explanation": regime_explanation,
        "indicators": indicators,
    }


print(get_market_regime_simplified())
