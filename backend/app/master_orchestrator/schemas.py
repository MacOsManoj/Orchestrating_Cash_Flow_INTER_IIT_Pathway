"""
Master Orchestrator Schemas
===========================

Pydantic models for the Router Agent and session management.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Pipeline(str, Enum):
    """Available pipelines that can be activated by the Router Agent."""
    FOREX = "forex"
    STOCKS = "stocks"
    BONDS = "bonds"
    CASHFLOW = "cashflow"
    NEWS = "news"


class PipelineResponse(BaseModel):
    """Wrapper for a pipeline API response."""
    pipeline: Pipeline
    endpoint: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class SessionContext(BaseModel):
    """
    Context from previous interactions in a session.
    Used for follow-up queries.
    
    Stores cached message texts from previous responses to append to new queries.
    """
    session_id: str = ""
    previous_messages: List[str] = Field(default_factory=list)
    last_query: str = ""
    last_pipelines_called: List[Pipeline] = Field(default_factory=list)
    # Keep previous_responses for backward compatibility
    previous_responses: List[PipelineResponse] = Field(default_factory=list)
    
    def get_summary(self) -> str:
        """Generate a text summary for LLM context injection."""
        if not self.previous_messages:
            return "No previous context."
        
        # Include the last few message summaries
        context_parts = []
        for i, msg in enumerate(self.previous_messages[-3:]):  # Last 3 messages only
            # Truncate long messages
            truncated = msg[:500] + "..." if len(msg) > 500 else msg
            context_parts.append(f"[Previous response {i+1}]: {truncated}")
        
        return "\n".join(context_parts)
    
    def build_contextual_query(self, new_query: str) -> str:
        """
        Build a query with context from previous messages appended.
        
        Args:
            new_query: The new user query
            
        Returns:
            Query with previous context prepended if available
        """
        if not self.previous_messages:
            return new_query
        
        # Build context from last few messages
        context_parts = []
        for i, msg in enumerate(self.previous_messages[-2:]):  # Last 2 messages for context
            # Truncate very long messages
            truncated = msg[:800] + "..." if len(msg) > 800 else msg
            context_parts.append(f"[Previous analysis]: {truncated}")
        
        context_str = "\n".join(context_parts)
        
        return f"""Context from previous conversation:
{context_str}

Current query: {new_query}"""


class RoutingDecision(BaseModel):
    """
    The Router Agent's decision on which pipelines to activate.
    """
    query: str
    selected_pipelines: List[Pipeline]
    reasoning: str
    requires_context: bool = False  # True if this is a follow-up query
    
    class Config:
        use_enum_values = True


class ComponentData(BaseModel):
    """
    Data for a single UI component.
    """
    component_id: str
    type: str
    data: Dict[str, Any]
    
    class Config:
        use_enum_values = True


class OrchestratorResponse(BaseModel):
    """
    Complete response from the orchestrator.
    Matches the schema.json format: { message: str, components: [...] }
    """
    message: str = Field(
        description="Text response from the relevant pipeline's query endpoint"
    )
    components: List[ComponentData] = Field(
        default_factory=list,
        description="List of UI components with their data"
    )
    pipelines_used: List[Pipeline] = Field(
        default_factory=list,
        description="Which pipelines were queried"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
