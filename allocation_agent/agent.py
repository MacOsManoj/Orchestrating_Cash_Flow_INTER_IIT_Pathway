import logging
from typing import Dict, Any
from .schema import (
    UserIntent, MarketSignals, PortfolioRecommendation,
    LiquidityRisk, MarketSentiment, Volatility, YieldTrend, CurrencyStrength
)
from .rules_engine import calculate_allocation
from .tools import stocks_tool, bonds_tool, forex_tool, cashflow_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .llm_utils import analyze_intent_and_constraints, check_conflict

class OrchestratorAgent:
    """
    The central agent that coordinates User Intent, Market Signals, and Rules.
    """
    
    def __init__(self):
        pass

    async def gather_signals(self, intent: UserIntent) -> MarketSignals:
        """
        Calls all pipeline tools to gather current market signals.
        """
        logger.info("Gathering signals from pipelines...")
        
        # 1. Stocks (Still mock/sync for now)
        stock_data = stocks_tool.get_market_status()
        
        # 2. Bonds (Async MCP call to Bonds Pipeline)
        bond_data = await bonds_tool.get_bond_yield_trend_async()
        
        # 3. Forex (Async MCP call to Forex Pipeline)
        forex_index = await forex_tool.get_forex_opportunity_index_async()
        
        # 4. Cashflow (Still mock/sync for now)
        cash_data = cashflow_tool.get_liquidity_risk()
        
        # Aggregate
        signals = MarketSignals(
            intent=intent,
            liquidity_risk=cash_data['liquidity_risk'],
            sentiment=stock_data['sentiment'],
            volatility=stock_data['volatility'],
            yield_trend=bond_data['yield_trend'],
            forex_opportunity_index=forex_index
        )
        
        logger.info(f"Aggregated Signals: {signals}")
        return signals

    async def run(self, user_query: str) -> Dict[str, Any]:
        """
        Main execution flow.
        """
        logger.info(f"Received query: {user_query}")
        
        # 1. Determine Intent & Constraints (LLM)
        intent, constraints = analyze_intent_and_constraints(user_query)
        logger.info(f"Identified Intent: {intent}")
        logger.info(f"Extracted Constraints: {constraints}")
        
        # 2. Gather Signals (Async)
        signals = await self.gather_signals(intent)
        
        # 3. Check for Conflicts (LLM)
        conflict_warning = check_conflict(intent, signals)
        if conflict_warning.detected:
            logger.warning(f"Conflict Detected: {conflict_warning.message}")
        
        # 4. Apply Rules
        recommendation = calculate_allocation(signals)
        
        # 5. Apply Constraints (Override Rules)
        alloc = recommendation.allocation
        reasoning = [recommendation.reasoning]
        
        if constraints.max_stocks is not None and alloc.stocks > constraints.max_stocks:
            diff = alloc.stocks - constraints.max_stocks
            alloc.stocks = constraints.max_stocks
            # Redistribute diff to Cash (safest)
            alloc.cash += diff
            reasoning.append(f"Constraint Applied: Max Stocks {constraints.max_stocks*100}%. Moved {diff*100:.1f}% to Cash.")
            
        if constraints.min_bonds is not None and alloc.bonds < constraints.min_bonds:
            diff = constraints.min_bonds - alloc.bonds
            alloc.bonds = constraints.min_bonds
            # Take from Stocks (riskiest)
            if alloc.stocks >= diff:
                alloc.stocks -= diff
            else:
                # If not enough stocks, take from Cash
                remaining = diff - alloc.stocks
                alloc.stocks = 0.0
                alloc.cash = max(0.0, alloc.cash - remaining)
            reasoning.append(f"Constraint Applied: Min Bonds {constraints.min_bonds*100}%. Adjusted Stocks/Cash.")

        # Re-normalize just in case
        total = alloc.stocks + alloc.bonds + alloc.forex + alloc.cash
        if abs(total - 1.0) > 0.001:
             alloc.stocks /= total
             alloc.bonds /= total
             alloc.forex /= total
             alloc.cash /= total
        
        recommendation.allocation = alloc
        recommendation.reasoning = "\n".join(reasoning)
        recommendation.conflict_warning = conflict_warning
        
        return {
            "query": user_query,
            "intent": intent,
            "constraints": constraints.model_dump(),
            "signals": signals.model_dump(),
            "allocation": recommendation.allocation.model_dump(),
            "reasoning": recommendation.reasoning,
            "conflict_warning": conflict_warning.model_dump()
        }
