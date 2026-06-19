"""
Orchestrator
============

Main orchestrator that ties together:
1. Router Agent - Selects pipelines based on query
2. Component Selector - Chooses UI components to display
3. API Client - Fetches data from FastAPI endpoints
4. Transformers - Converts API responses to component format
5. Query Service - Gets text message from pipeline agents
6. Session Store - Manages context caching for follow-up queries

This is the main entry point for processing user queries.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .schemas import Pipeline, SessionContext, RoutingDecision, OrchestratorResponse, ComponentData
from .router_agent import RouterAgent, get_router_agent
from .component_selector import ComponentSelector, get_component_selector
from .api_client import PipelineAPIClient, get_api_client
from .component_registry import COMPONENT_REGISTRY, get_component_config
from .query_service import get_pipeline_message
from .session_store import SessionStore, get_session_store

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator for the hybrid architecture.
    
    Flow:
    1. Router Agent analyzes query → selects pipelines
    2. Component Selector chooses components → returns component configs
    3. For each component, fetch data from API endpoints
    4. Apply transformers to convert API data to component format
    5. Return list of component JSONs ready for frontend
    """
    
    def __init__(
        self,
        router: Optional[RouterAgent] = None,
        selector: Optional[ComponentSelector] = None,
        api_client: Optional[PipelineAPIClient] = None,
        session_store: Optional[SessionStore] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            router: RouterAgent instance. Creates default if not provided.
            selector: ComponentSelector instance. Creates default if not provided.
            api_client: PipelineAPIClient instance. Creates default if not provided.
            session_store: SessionStore instance. Creates default if not provided.
        """
        self.router = router or get_router_agent()
        self.selector = selector or get_component_selector()
        self.api_client = api_client or get_api_client()
        self.session_store = session_store or get_session_store()
    
    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[SessionContext] = None,
        limit_to_ready: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user query end-to-end.
        
        Args:
            query: User's natural language query.
            session_id: Optional session ID for context management.
            context: Optional session context for follow-up queries (deprecated, use session_id).
            limit_to_ready: If True, only use components with transformers.
            
        Returns:
            Dict containing:
                - message: Text response from pipeline's query endpoint
                - components: List of component JSONs ready for frontend
                - routing: Router's decision (pipelines selected)
                - selection: Selector's decision (components selected)
                - errors: Any errors encountered
        """
        errors = []
        
        # Build contextual query if session exists
        # This is the SAME query used for both routing AND pipeline queries
        if session_id and self.session_store.has_context(session_id):
            context = self.session_store.get_context(session_id)
            contextual_query = context.build_contextual_query(query)
            logger.info(f"Built contextual query with {len(context.previous_messages)} cached messages")
        else:
            contextual_query = query
            if session_id:
                context = self.session_store.get_context(session_id)
        
        # Step 1: Route query to pipelines (using contextual query)
        logger.info(f"Processing query: {query}")
        logger.debug(f"Contextual query: {contextual_query}")
        try:
            routing_decision = self.router.route(contextual_query, context)
            logger.info(f"Router selected pipelines: {routing_decision.selected_pipelines}")
        except Exception as e:
            logger.error(f"Router failed: {e}")
            return {
                "message": f"Unable to process query: {str(e)}",
                "components": [],
                "routing": None,
                "selection": None,
                "errors": [f"Router error: {str(e)}"]
            }
        
        # Step 2: Select components based on query and pipelines (using contextual query)
        try:
            selection_result = self.selector.select(
                query=contextual_query,
                available_pipelines=routing_decision.selected_pipelines,
                limit_to_ready=limit_to_ready
            )
            logger.info(f"Selector chose components: {selection_result['selected_components']}")
        except Exception as e:
            logger.error(f"Selector failed: {e}")
            pipeline_values = [
                p.value if hasattr(p, 'value') else str(p) 
                for p in routing_decision.selected_pipelines
            ]
            return {
                "message": f"Unable to select components: {str(e)}",
                "components": [],
                "routing": {
                    "query": query,  # Return original query in response
                    "pipelines": pipeline_values,
                    "reasoning": routing_decision.reasoning
                },
                "selection": None,
                "errors": [f"Selector error: {str(e)}"]
            }
        
        # Step 3: Get text message from primary pipeline's query endpoint
        # IMPORTANT: Use the SAME contextual_query for pipeline queries
        message = ""
        if routing_decision.selected_pipelines:
            primary_pipeline = routing_decision.selected_pipelines[0]
            if isinstance(primary_pipeline, str):
                primary_pipeline = Pipeline(primary_pipeline)
            
            query_params = selection_result.get("extracted_params", {})
            
            try:
                # Pass contextual_query to pipeline (same as router/selector)
                message = await get_pipeline_message(primary_pipeline, contextual_query, query_params)
                logger.info(f"Got message from {primary_pipeline.value} pipeline")
            except Exception as e:
                logger.warning(f"Failed to get message from {primary_pipeline.value}: {e}")
                message = "Analysis completed. Please refer to the data components for detailed information."
        
        # Step 4: Fetch data and transform for each component
        components = []
        for comp_config in selection_result["component_configs"]:
            try:
                # Pass the contextual query to component processing (needed for POST endpoints like stocks)
                component_result = await self._process_component(comp_config, contextual_query)
                if component_result:
                    # Handle both single component and list of components
                    if isinstance(component_result, list):
                        components.extend(component_result)
                    else:
                        components.append(component_result)
            except Exception as e:
                error_msg = f"Error processing {comp_config['id']}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Step 5: Cache the message for future context
        if session_id and message:
            self.session_store.add_message(session_id, message)
            self.session_store.update_last_query(
                session_id, 
                query,  # Store original query
                routing_decision.selected_pipelines
            )
            logger.info(f"Cached message for session {session_id}")
        
        pipeline_values = [
            p.value if hasattr(p, 'value') else str(p) 
            for p in routing_decision.selected_pipelines
        ]
        
        return {
            "message": message,
            "components": components,
            "routing": {
                "query": query,  # Return original query
                "pipelines": pipeline_values,
                "reasoning": routing_decision.reasoning,
                "requires_context": routing_decision.requires_context
            },
            "selection": {
                "components": selection_result["selected_components"],
                "reasoning": selection_result["reasoning"]
            },
            "errors": errors if errors else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _process_component(self, comp_config: Dict[str, Any], query: str = "") -> Optional[Any]:
        """
        Process a single component: fetch API data and transform.
        
        Args:
            comp_config: Component configuration from selector.
            query: User's original query (used for POST endpoints like stock agent).
            
        Returns:
            Component JSON ready for frontend (dict), list of components (list), or None if failed.
            Some transformers may return multiple components (e.g., bond chat recommendations).
        """
        comp_id = comp_config["id"]
        comp_type = comp_config["type"]
        pipeline = Pipeline(comp_config["pipeline"])
        endpoints = comp_config["endpoints"]
        transformer = comp_config["transformer"]
        params = comp_config.get("params", {})  # Component-specific params from LLM
        
        if not transformer:
            logger.warning(f"Component {comp_id} has no transformer")
            return None
        
        # Fetch data from all required endpoints
        if not endpoints:
            logger.warning(f"Component {comp_id} has no endpoints configured")
            return None
        
        # Handle single vs multiple endpoints
        if len(endpoints) == 1:
            # Single endpoint - fetch directly
            endpoint = endpoints[0]
            logger.info(f"Fetching {pipeline.value}/{endpoint} for {comp_id}")
            api_response = await self.api_client.call_endpoint(pipeline, endpoint, query=query)
            
            # Check for API errors
            if isinstance(api_response, dict) and api_response.get("error"):
                raise ValueError(f"API error: {api_response.get('message')}")
        else:
            # Multiple endpoints - fetch all and combine into dict keyed by endpoint name
            logger.info(f"Fetching multiple endpoints for {comp_id}: {endpoints}")
            api_response = {}
            for endpoint in endpoints:
                logger.info(f"Fetching {pipeline.value}/{endpoint}")
                endpoint_response = await self.api_client.call_endpoint(pipeline, endpoint, query=query)
                
                # Check for API errors but don't fail completely - log and continue
                if isinstance(endpoint_response, dict) and endpoint_response.get("error"):
                    logger.warning(f"API error for {endpoint}: {endpoint_response.get('message')}")
                    endpoint_response = {}  # Use empty dict for failed endpoint
                
                api_response[endpoint] = endpoint_response
        
        # Apply transformer with any component-specific params
        logger.info(f"Transforming data for {comp_id} with params: {params}")
        
        # Check if transformer is async
        import inspect
        import asyncio
        is_async = inspect.iscoroutinefunction(transformer)
        
        if is_async:
            # Async transformer
            sig = inspect.signature(transformer)
            if len(sig.parameters) > 1:
                transformed_data = await transformer(api_response, **params)
            else:
                transformed_data = await transformer(api_response)
        else:
            # Sync transformer
            sig = inspect.signature(transformer)
            if len(sig.parameters) > 1:
                transformed_data = transformer(api_response, **params)
            else:
                transformed_data = transformer(api_response)
        
        # Check if transformer returned a list of components (special case)
        if isinstance(transformed_data, list):
            # Transformer returned multiple components - return them as-is
            # Each item should already have type and data fields
            return transformed_data
        
        # Return single component JSON
        return {
            "type": comp_type,
            "data": transformed_data
        }


# Default orchestrator instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create the default orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def process_query(
    query: str,
    session_id: Optional[str] = None,
    context: Optional[SessionContext] = None
) -> Dict[str, Any]:
    """
    Convenience function to process a query using the default orchestrator.
    
    Args:
        query: User's natural language query.
        session_id: Optional session ID for context management.
        context: Optional session context (deprecated, use session_id).
        
    Returns:
        Result dict with message, components, routing info, and any errors.
    """
    orchestrator = get_orchestrator()
    return await orchestrator.process_query(query, session_id, context)
