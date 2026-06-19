"""
Master Orchestrator
===================

Router Agent for multi-pipeline query handling with session management.
Hybrid architecture: Router → Component Selector → API → Transformers → Frontend
"""

from .schemas import Pipeline, PipelineResponse, SessionContext, RoutingDecision
from .router_agent import RouterAgent, get_router_agent
from .session_store import SessionStore, get_session_store
from .api_client import PipelineAPIClient, get_api_client
from .pipeline_registry import PIPELINE_ENDPOINTS
from .component_registry import (
    COMPONENT_REGISTRY,
    ComponentType,
    get_component_config,
    get_components_for_pipeline,
    get_ready_components
)
from .component_selector import ComponentSelector, get_component_selector
from .orchestrator import Orchestrator, get_orchestrator, process_query

__all__ = [
    # Schemas
    "Pipeline",
    "PipelineResponse", 
    "SessionContext",
    "RoutingDecision",
    # Router
    "RouterAgent",
    "get_router_agent",
    # Component Selector
    "ComponentSelector",
    "get_component_selector",
    # Component Registry
    "COMPONENT_REGISTRY",
    "ComponentType",
    "get_component_config",
    "get_components_for_pipeline",
    "get_ready_components",
    # Orchestrator
    "Orchestrator",
    "get_orchestrator",
    "process_query",
    # Session
    "SessionStore",
    "get_session_store",
    # API Client
    "PipelineAPIClient",
    "get_api_client",
    # Config
    "PIPELINE_ENDPOINTS",
]
