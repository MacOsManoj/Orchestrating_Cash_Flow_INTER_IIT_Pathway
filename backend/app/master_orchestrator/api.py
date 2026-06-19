"""
Master Orchestrator FastAPI Server
==================================

Exposes the orchestrator as a REST API endpoint.

Usage:
    cd /home/sinosuke/Documents/pw-2/upgraded-octo-spork
    uvicorn master_orchestrator.api:app --reload --port 8001

Endpoints:
    GET  /query?prompt=<text>           - Process a query and return JSON response
    GET  /query?prompt=<text>&session_id=<id>  - Process with session context
    GET  /health                        - Health check
    GET  /components                    - List available components
"""

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from master_orchestrator import (
    process_query,
    get_ready_components,
    COMPONENT_REGISTRY
)


# =============================================================================
# Pydantic Response Models (matching schema.json)
# =============================================================================

class ComponentData(BaseModel):
    """Generic component data structure."""
    type: str = Field(..., description="Component type (e.g., 'CorrelationMatrixFX', 'CashFlowTable')")
    data: Dict[str, Any] = Field(..., description="Component-specific data payload")


class OrchestratorResponse(BaseModel):
    """
    Response format matching schema.json.
    
    This is the exact format expected by the frontend.
    """
    message: str = Field(
        default="",
        description="Text response to the query"
    )
    components: List[ComponentData] = Field(
        default=[],
        description="List of UI components with their data"
    )


class FullOrchestratorResponse(OrchestratorResponse):
    """
    Extended response with debugging/routing info.
    
    Use this when you need additional context about the routing decision.
    """
    routing: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Router's decision (pipelines selected)"
    )
    selection: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Selector's decision (components selected)"
    )
    errors: Optional[List[str]] = Field(
        default=None,
        description="Any errors encountered during processing"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the response"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    ready_components: int
    total_components: int


class ComponentInfo(BaseModel):
    """Component information for listing."""
    id: str
    type: str
    description: str
    pipeline: str
    ready: bool


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Master Orchestrator API",
    description="REST API for the Master Orchestrator - routes queries to appropriate pipelines and returns structured UI components.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get(
    "/query",
    response_model=OrchestratorResponse,
    summary="Process a natural language query",
    description="""
    Process a natural language query and return structured JSON for the frontend.
    
    The response contains:
    - `message`: Text response explaining the analysis
    - `components`: List of UI components with their data (matching schema.json)
    
    Examples:
    - "Show me the forex correlation matrix"
    - "Display cash flow table for 7 days"
    - "What are the bond risk metrics for IN0020220025?"
    - "Show stock analysis for RELIANCE"
    """,
    tags=["Query"]
)
async def query_orchestrator(
    prompt: str = Query(
        ...,
        description="Natural language query to process",
        min_length=1,
        max_length=1000,
        examples=["Show me the forex correlation matrix", "Display cash flow for next week"]
    ),
    session_id: Optional[str] = Query(
        default=None,
        description="Optional session ID for maintaining conversation context"
    )
) -> OrchestratorResponse:
    """
    Process a query and return the response in schema.json format.
    
    This endpoint returns only `message` and `components` - the exact format
    expected by the frontend as defined in schema.json.
    """
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not configured. Please set it in environment variables."
        )
    
    try:
        # Process the query
        result = await process_query(prompt, session_id=session_id)
        
        # Return only the frontend-compatible fields
        return OrchestratorResponse(
            message=result.get("message", ""),
            components=[
                ComponentData(type=comp["type"], data=comp["data"])
                for comp in result.get("components", [])
            ]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@app.get(
    "/query/full",
    response_model=FullOrchestratorResponse,
    summary="Process query with full debugging info",
    description="Same as /query but includes routing decisions, component selection reasoning, and errors.",
    tags=["Query"]
)
async def query_orchestrator_full(
    prompt: str = Query(
        ...,
        description="Natural language query to process",
        min_length=1,
        max_length=1000
    ),
    session_id: Optional[str] = Query(
        default=None,
        description="Optional session ID for maintaining conversation context"
    )
) -> FullOrchestratorResponse:
    """
    Process a query and return the full response with debugging info.
    
    This includes routing decisions, component selection reasoning, and any errors.
    Useful for debugging and understanding the orchestrator's decisions.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not configured. Please set it in environment variables."
        )
    
    try:
        result = await process_query(prompt, session_id=session_id)
        
        return FullOrchestratorResponse(
            message=result.get("message", ""),
            components=[
                ComponentData(type=comp["type"], data=comp["data"])
                for comp in result.get("components", [])
            ],
            routing=result.get("routing"),
            selection=result.get("selection"),
            errors=result.get("errors"),
            timestamp=result.get("timestamp")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the orchestrator API is running and ready.",
    tags=["System"]
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    ready = get_ready_components()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        ready_components=len(ready),
        total_components=len(COMPONENT_REGISTRY)
    )


@app.get(
    "/components",
    response_model=List[ComponentInfo],
    summary="List available components",
    description="Get a list of all available UI components and their status.",
    tags=["System"]
)
async def list_components() -> List[ComponentInfo]:
    """List all available components."""
    ready = get_ready_components()
    components = []
    
    for comp_id, config in COMPONENT_REGISTRY.items():
        comp_type = config.get("type", "Unknown")
        if hasattr(comp_type, "value"):
            comp_type = comp_type.value
        
        pipeline = config.get("pipeline", "Unknown")
        if hasattr(pipeline, "value"):
            pipeline = pipeline.value
        
        components.append(ComponentInfo(
            id=comp_id,
            type=str(comp_type),
            description=config.get("description", ""),
            pipeline=str(pipeline),
            ready=comp_id in ready
        ))
    
    return components


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set. Set it before making queries.")
        print("   export OPENAI_API_KEY='your-key-here'")
    
    print("Starting Master Orchestrator API...")
    print("Docs available at: http://localhost:8001/docs")
    
    uvicorn.run(
        "master_orchestrator.api:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
