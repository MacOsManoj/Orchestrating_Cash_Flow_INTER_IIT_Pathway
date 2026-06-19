import unittest
from .schema import (
    MarketSignals, UserIntent, LiquidityRisk, MarketSentiment, 
    Volatility, YieldTrend, CurrencyStrength
)
from .rules_engine import calculate_allocation

class TestRuleEngine(unittest.TestCase):
    
    def test_scenario_a_perfect_storm(self):
        """
        Scenario A: "The Perfect Storm"
        User: Balanced (Start: S:40, B:50, F:5, C:5)
        Signals: Cashflow: HIGH, Sentiment: BEARISH, Volatility: HIGH
        Expected: Stocks: 25%, Bonds: 45%, Forex: 5%, Cash: 25%
        """
        signals = MarketSignals(
            intent=UserIntent.BALANCED,
            liquidity_risk=LiquidityRisk.HIGH,
            sentiment=MarketSentiment.BEARISH,
            volatility=Volatility.HIGH,
            yield_trend=YieldTrend.FLAT, # Not specified in scenario, assuming neutral
            dom_currency=CurrencyStrength.STRONG # Not specified, assuming neutral
        )
        
        rec = calculate_allocation(signals)
        alloc = rec.allocation
        
        print("\n--- Scenario A Results ---")
        print(rec.reasoning)
        print(alloc)
        
        # Assertions (Allowing small float diffs)
        self.assertAlmostEqual(alloc.stocks, 0.25, delta=0.01)
        self.assertAlmostEqual(alloc.bonds, 0.45, delta=0.01)
        self.assertAlmostEqual(alloc.forex, 0.05, delta=0.01)
        self.assertAlmostEqual(alloc.cash, 0.25, delta=0.01)

    def test_scenario_b_aggressive_growth(self):
        """
        Scenario B: "Aggressive Growth"
        User: Aggressive (Start: S:70, B:20, F:5, C:5)
        Signals: Cashflow: LOW, Sentiment: BULLISH, Yields: FLAT
        Expected: Stocks: 80%, Bonds: 13%, Forex: 5%, Cash: 2%
        """
        signals = MarketSignals(
            intent=UserIntent.AGGRESSIVE,
            liquidity_risk=LiquidityRisk.LOW,
            sentiment=MarketSentiment.BULLISH,
            volatility=Volatility.LOW, # Implied by "Surplus Optimization" rule triggering
            yield_trend=YieldTrend.FLAT,
            dom_currency=CurrencyStrength.STRONG
        )
        
        rec = calculate_allocation(signals)
        alloc = rec.allocation
        
        print("\n--- Scenario B Results ---")
        print(rec.reasoning)
        print(alloc)
        
        self.assertAlmostEqual(alloc.stocks, 0.80, delta=0.01)
        self.assertAlmostEqual(alloc.bonds, 0.13, delta=0.01)
        self.assertAlmostEqual(alloc.forex, 0.05, delta=0.01)
        self.assertAlmostEqual(alloc.cash, 0.02, delta=0.01)

if __name__ == '__main__':
    unittest.main()
