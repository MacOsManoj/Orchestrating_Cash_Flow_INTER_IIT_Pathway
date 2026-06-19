"""
Router Agent
============

LLM-powered agent that analyzes user queries and decides which pipelines to activate.
Uses OpenAI-compatible API.
"""

import os
import json
import logging
from typing import Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv

from .schemas import Pipeline, RoutingDecision, SessionContext
from .pipeline_registry import get_all_pipeline_descriptions

load_dotenv()
logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Analyzes user queries and decides which pipeline(s) to activate.
    
    Uses an LLM to:
    1. Understand the user's intent
    2. Consider previous context (for follow-ups)
    3. Select appropriate pipelines
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize the Router Agent.
        
        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            base_url: Optional base URL for OpenAI-compatible providers.
            model: Model to use for routing decisions.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. Router will fail.")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            ) if self.base_url else OpenAI(api_key=self.api_key)
        
        # System prompt for routing
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with pipeline descriptions."""
        pipeline_info = get_all_pipeline_descriptions()
        
        return f"""You are a financial query router. Your job is to analyze user queries and decide which pipeline(s) should be activated to answer the query.

## Available Pipelines:
{pipeline_info}

## Routing Rules:
1. Select ONE or MORE pipelines that are relevant to the query.
2. For **portfolio allocation** or **overall investment strategy** questions, use the CASHFLOW pipeline (it handles portfolio guidance).
3. For **forex/currency** questions (e.g., "EUR/USD trend", "forex trades"), select FOREX.
4. For **stocks/equities** questions, select STOCKS.
5. For **bonds/fixed income** questions, select BONDS.
6. For **comparison queries** (e.g., "compare stocks vs bonds"), select MULTIPLE pipelines in parallel (e.g., both STOCKS and BONDS).
7. For **liquidity/cash management** questions, select CASHFLOW.
8. If a query is a follow-up (e.g., "make it aggressive", "show more details"), use the context to understand what was previously shown.
9. Always explain your reasoning briefly.

## Examples:
- "Show me forex trends" → ["forex"]
- "What's my cashflow situation?" → ["cashflow"]
- "Compare stocks and bonds performance" → ["stocks", "bonds"]
- "How should my portfolio be allocated?" → ["cashflow"]
- "EUR/USD vs GBPUSD correlations" → ["forex"]
- "Stocks sentiment and bond yields" → ["stocks", "bonds"]

## Response Format (JSON):
{{
    "selected_pipelines": ["forex", "stocks", "bonds", "cashflow"],
    "reasoning": "Brief explanation of why these pipelines were selected",
    "requires_context": true/false (true if this is a follow-up query)
}}

Only respond with valid JSON. Do not include any other text."""
    
    def route(
        self,
        query: str,
        context: Optional[SessionContext] = None
    ) -> RoutingDecision:
        """
        Analyze a user query and decide which pipelines to activate.
        
        Args:
            query: The user's query text.
            context: Optional previous session context for follow-ups.
            
        Returns:
            RoutingDecision with selected pipelines and reasoning.
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
        
        # Build user message with context if available
        user_message = self._build_user_message(query, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)
            
            # Parse pipeline names to enums
            selected = []
            for p_name in result_data.get("selected_pipelines", []):
                try:
                    selected.append(Pipeline(p_name.lower()))
                except ValueError:
                    logger.warning(f"Unknown pipeline in response: {p_name}")
            
            # Default to CASHFLOW if nothing selected (for general queries)
            if not selected:
                selected = [Pipeline.CASHFLOW]
            
            return RoutingDecision(
                query=query,
                selected_pipelines=selected,
                reasoning=result_data.get("reasoning", "No reasoning provided."),
                requires_context=result_data.get("requires_context", False)
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback: assume it's a cashflow/general query
            return RoutingDecision(
                query=query,
                selected_pipelines=[Pipeline.CASHFLOW],
                reasoning="Fallback: Could not parse LLM response.",
                requires_context=False
            )
        except Exception as e:
            logger.error(f"Router error: {e}")
            raise
    
    def _build_user_message(
        self,
        query: str,
        context: Optional[SessionContext]
    ) -> str:
        """Build the user message with optional context."""
        if context and context.previous_responses:
            context_summary = context.get_summary()
            return f"""## Previous Context:
{context_summary}

## Current Query:
{query}"""
        else:
            return f"## Query:\n{query}"


# Default router instance
_router: Optional[RouterAgent] = None


def get_router_agent(
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> RouterAgent:
    """Get or create the default router agent."""
    global _router
    if _router is None:
        _router = RouterAgent(api_key=api_key, model=model)
    return _router
