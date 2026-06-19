"""
Component Selector
==================

LLM-powered selector that chooses which UI components to display based on user query.
This is the LLM-based layer of the hybrid architecture.

Flow:
1. Router Agent identifies pipelines (FOREX, CASHFLOW, etc.)
2. Component Selector chooses specific components within those pipelines
3. Components are rendered with data from their associated API endpoints
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

from .schemas import Pipeline
from .component_registry import (
    COMPONENT_REGISTRY,
    get_component_descriptions_for_llm,
    get_ready_components,
    get_components_for_pipeline,
    ComponentType
)

load_dotenv()
logger = logging.getLogger(__name__)


class ComponentSelector:
    """
    Selects which UI components to display based on user query and available pipelines.
    
    Uses an LLM to:
    1. Understand what the user wants to see
    2. Select the most appropriate component(s)
    3. Return component IDs for the orchestrator to process
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize the Component Selector.
        
        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            base_url: Optional base URL for OpenAI-compatible providers.
            model: Model to use for component selection.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. Component Selector will fail.")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            ) if self.base_url else OpenAI(api_key=self.api_key)
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with component descriptions."""
        component_info = get_component_descriptions_for_llm()
        ready_components = get_ready_components()
        
        return f"""You are a UI component selector for a financial dashboard. Your job is to analyze user queries and decide which component(s) should be displayed.

## Available Components:
{component_info}

## Currently Ready Components (have data transformers implemented):
{ready_components}

## Selection Rules:
1. **FOREX or CASHFLOW queries**: If the query is ONLY about forex or cashflow (not mixed with other topics like stocks/bonds), you MUST select ALL components from those pipelines. Do not skip any.
2. **Other queries** (stocks, bonds, news, or mixed topics): Select a MINIMUM of 4 components that best match the user's query. Choose the closest and most relevant ones.
3. You may select more than 4 components if multiple are highly relevant.
4. Prefer components from the "ready" list when possible, but you can suggest others if they're more relevant.
5. Consider what visualization would best help the user understand the information.
6. Be comprehensive for forex/cashflow, but still relevant for other pipelines.

## Component-Specific Parameters:
For certain components, you must also extract parameters from the user query:

### comp-3 (AllocationDashboard):
Extract the user's risk appetite/sentiment from the query:
- "Aggressive" - if user wants high risk, aggressive growth, maximum returns, risky investments
- "Safe" - if user wants low risk, conservative, safe investments, capital preservation
- "Normal" - if user wants balanced, moderate, or doesn't specify any risk preference

## Examples:
- "Show me forex correlation" → {{"selected_components": ["comp-2"]}}
- "What's the news sentiment?" → {{"selected_components": ["comp-1"]}}
- "How should I allocate my portfolio?" → {{"selected_components": ["comp-3"], "params": {{"comp-3": {{"risk_profile": "Normal"}}}}}}
- "Give me an aggressive portfolio allocation" → {{"selected_components": ["comp-3"], "params": {{"comp-3": {{"risk_profile": "Aggressive"}}}}}}
- "Show me a safe, conservative investment split" → {{"selected_components": ["comp-3"], "params": {{"comp-3": {{"risk_profile": "Safe"}}}}}}
- "I want maximum growth, show allocation" → {{"selected_components": ["comp-3"], "params": {{"comp-3": {{"risk_profile": "Aggressive"}}}}}}

## Response Format (JSON):
{{
    "selected_components": ["comp-1", "comp-2"],
    "reasoning": "Brief explanation of why these components were selected",
    "params": {{
        "comp-3": {{"risk_profile": "Normal"}}
    }}
}}

The "params" field is optional and only needed for components that require parameters.
Only respond with valid JSON. Select at least 1 component."""
    
    def select(
        self,
        query: str,
        available_pipelines: List[Pipeline],
        limit_to_ready: bool = True
    ) -> Dict[str, Any]:
        """
        Select components based on user query and available pipelines.
        
        Args:
            query: The user's query text.
            available_pipelines: Pipelines that the Router has already selected.
            limit_to_ready: If True, only return components that have transformers.
            
        Returns:
            Dict with:
                - selected_components: List of component IDs
                - reasoning: LLM's explanation
                - component_configs: Full config for each selected component
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
        
        # Build context about available pipelines (handle both enum and string)
        pipeline_names = [
            p.value.upper() if hasattr(p, 'value') else str(p).upper() 
            for p in available_pipelines
        ]
        pipeline_context = f"The router has determined these pipelines are relevant: {pipeline_names}"
        
        user_message = f"""## Context:
{pipeline_context}

## User Query:
{query}

Select the most appropriate component(s) to display."""
        
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
            
            selected = result_data.get("selected_components", [])
            reasoning = result_data.get("reasoning", "No reasoning provided.")
            params = result_data.get("params", {})  # Component-specific parameters
            
            # =====================================================================
            # ENFORCE SELECTION RULES (post-LLM)
            # =====================================================================
            pipeline_values = set(
                p.value.lower() if hasattr(p, 'value') else str(p).lower()
                for p in available_pipelines
            )
            
            # Rule 1: FOREX or CASHFLOW only → select ALL components from those pipelines
            is_forex_cashflow_only = pipeline_values.issubset({"forex", "cashflow"}) and len(pipeline_values) > 0
            
            if is_forex_cashflow_only:
                # Get ALL components for the relevant pipelines
                all_pipeline_components = []
                for p in available_pipelines:
                    all_pipeline_components.extend(get_components_for_pipeline(p))
                
                # Filter to ready components if requested
                if limit_to_ready:
                    ready = get_ready_components()
                    all_pipeline_components = [c for c in all_pipeline_components if c in ready]
                
                # Use all pipeline components (override LLM selection)
                selected = list(set(all_pipeline_components))  # deduplicate
                reasoning = f"Forex/Cashflow query: returning all {len(selected)} components for these pipelines. " + reasoning
            else:
                # Rule 2: Other queries → minimum 4 components
                # Filter to only ready components if requested
                if limit_to_ready:
                    ready = get_ready_components()
                    selected = [c for c in selected if c in ready]
                    
                    # If less than 4, add more relevant components from the pipelines
                    if len(selected) < 4:
                        # Get all components from the selected pipelines
                        pipeline_components = []
                        for p in available_pipelines:
                            pipeline_components.extend(get_components_for_pipeline(p))
                        
                        # Filter to ready and not already selected
                        additional = [c for c in pipeline_components if c in ready and c not in selected]
                        
                        # Add until we have at least 4
                        needed = 4 - len(selected)
                        selected.extend(additional[:needed])
                        
                        if len(selected) < 4:
                            reasoning += f" (Note: Only {len(selected)} relevant components available)"
                
                # Fallback if all selections were filtered out
                if not selected and limit_to_ready:
                    ready = get_ready_components()
                    if ready:
                        logger.warning("All selected components were not ready. Using first ready component.")
                        selected = [ready[0]]
                        reasoning += " (Fallback: original selections not ready)"
            
            # Get full configs for selected components
            component_configs = []
            for comp_id in selected:
                config = COMPONENT_REGISTRY.get(comp_id)
                if config:
                    component_configs.append({
                        "id": comp_id,
                        "type": config["type"].value if hasattr(config["type"], "value") else config["type"],
                        "pipeline": config["pipeline"].value if hasattr(config["pipeline"], "value") else config["pipeline"],
                        "endpoints": config["endpoints"],
                        "transformer": config["transformer"],
                        "params": params.get(comp_id, {})  # Include component-specific params
                    })
            
            return {
                "selected_components": selected,
                "reasoning": reasoning,
                "component_configs": component_configs,
                "params": params
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback to first ready component
            ready = get_ready_components()
            fallback = ready[0] if ready else "comp-2"
            config = COMPONENT_REGISTRY.get(fallback, {})
            
            return {
                "selected_components": [fallback],
                "reasoning": f"Fallback: Could not parse LLM response. Error: {e}",
                "component_configs": [{
                    "id": fallback,
                    "type": config.get("type", ComponentType.CORRELATION_MATRIX_FX).value,
                    "pipeline": config.get("pipeline", Pipeline.FOREX).value,
                    "endpoints": config.get("endpoints", []),
                    "transformer": config.get("transformer")
                }]
            }
        except Exception as e:
            logger.error(f"Component selector error: {e}")
            raise


# Default selector instance
_selector: Optional[ComponentSelector] = None


def get_component_selector(
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> ComponentSelector:
    """Get or create the default component selector."""
    global _selector
    if _selector is None:
        _selector = ComponentSelector(api_key=api_key, model=model)
    return _selector
