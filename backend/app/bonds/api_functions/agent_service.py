"""
This file needs a lot of changes to work with the new orchestrator_v3 and schemas_v2.
It currently serves as a placeholder for the Agent Service implementation.
Agent Service - Handles orchestrator initialization and query processing
"""

import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException

# Agent imports
try:
    from orchestrator_v3 import create_orchestrator_v3
    from schemas_v2 import SystemConfigV2, EnhancedAgentState, AdvisoryOutput

    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Orchestrator not available: {e}")
    ORCHESTRATOR_AVAILABLE = False
    EnhancedAgentState = None
    AdvisoryOutput = None


# In-memory storage for query results
_query_storage: Dict[str, Dict[str, Any]] = {}

# Orchestrator instance cache
_orchestrator_instance = None


def get_orchestrator():
    """Get or create orchestrator instance (singleton pattern)"""
    global _orchestrator_instance

    if not ORCHESTRATOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not available. Please check dependencies.",
        )

    if _orchestrator_instance is None:
        # Load configuration from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500, detail="OPENAI_API_KEY environment variable not set"
            )

        config = SystemConfigV2(
            openai_api_key=openai_api_key,
            serpapi_key=os.getenv("SERPAPI_KEY"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            rag_enabled=os.getenv("RAG_ENABLED", "true").lower() == "true",
            cache_enabled=True,
            enable_pathway_forecasts=False,
            portfolio_db_path=os.getenv("PORTFOLIO_DB_PATH", "files-mock/portfolios"),
            cache_dir=os.getenv("CACHE_DIR", "files-mock/cache"),
            vector_db_path=os.getenv("VECTOR_DB_PATH", "vector_store"),
        )

        try:
            _orchestrator_instance = create_orchestrator_v3(config)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to initialize orchestrator: {str(e)}"
            )

    return _orchestrator_instance


def extract_output_text_from_state(state) -> str:
    """
    Extract text output from ResponseAgent's output stored in the final langraph state.

    The ResponseAgent generates the final text response. The orchestrator stores the
    ResponseAgent's output in state.advisory (which contains AdvisoryOutput with summary field).
    This function extracts the ResponseAgent's output directly.

    Note: For advisory queries, ResponseAgent internally uses AdvisoryAgent but formats
    the final response. The summary field always contains the ResponseAgent's formatted output.
    """
    # TODO
    return "Output extraction not implemented yet."


async def process_query(
    user_id: str, query: str, conversation_history: Optional[list] = None
) -> Dict[str, Any]:
    """
    Process a query through the orchestrator and return results.

    Returns:
        Dictionary with query_id, status, processing_time, timestamp
    """
    if not ORCHESTRATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent orchestrator not available")

    # Generate unique query ID
    query_id = str(uuid.uuid4())
    start_time = datetime.now()

    try:
        # Get orchestrator instance
        orchestrator = get_orchestrator()

        # Run orchestrator
        state = await orchestrator.run_async(
            query=query,
            user_id=user_id,
            conversation_history=conversation_history or [],
        )

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Store results (including full state for output extraction later)
        _query_storage[query_id] = {
            "user_query": query,
            "user_id": user_id,
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "processing_time": processing_time,
        }

        return {
            "query_id": query_id,
            "status": "completed",
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        # Store error state
        _query_storage[query_id] = {
            "user_query": query,
            "user_id": user_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


def get_stored_query(query_id: str) -> Optional[Dict[str, Any]]:
    """Get stored query data by query_id"""
    return _query_storage.get(query_id)


def is_orchestrator_available() -> bool:
    """Check if orchestrator is available"""
    return ORCHESTRATOR_AVAILABLE
