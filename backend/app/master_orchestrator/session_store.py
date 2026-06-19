"""
Session Store
=============

In-memory session storage with LRU eviction for conversation context.
Caches text messages from previous responses for context injection.
"""

from collections import OrderedDict
from typing import Dict, Optional, Any, List
from datetime import datetime
from .schemas import Pipeline, PipelineResponse, SessionContext


class SessionStore:
    """
    Manages session state with message caching for context.
    
    - Caches the `message` field from orchestrator responses
    - Provides context-enriched queries for follow-up conversations
    - Uses LRU eviction for memory management
    """
    
    def __init__(self, max_messages: int = 5):
        """
        Initialize the session store.
        
        Args:
            max_messages: Maximum number of messages to cache per session.
        """
        self.max_messages = max_messages
        self._messages: Dict[str, List[str]] = {}  # session_id -> list of messages
        self._last_queries: Dict[str, str] = {}
        self._last_pipelines: Dict[str, List[Pipeline]] = {}
        self._sessions: Dict[str, OrderedDict[str, PipelineResponse]] = {}  # For backward compat
    
    def _get_or_create_session(self, session_id: str) -> None:
        """Ensure session exists."""
        if session_id not in self._messages:
            self._messages[session_id] = []
            self._last_queries[session_id] = ""
            self._last_pipelines[session_id] = []
            self._sessions[session_id] = OrderedDict()
    
    def add_message(self, session_id: str, message: str) -> None:
        """
        Cache a message from the orchestrator response.
        
        Args:
            session_id: Unique session identifier.
            message: The text message to cache.
        """
        self._get_or_create_session(session_id)
        
        if message and message.strip():
            self._messages[session_id].append(message)
            
            # Evict oldest if limit exceeded
            while len(self._messages[session_id]) > self.max_messages:
                self._messages[session_id].pop(0)
    
    def add_response(
        self, 
        session_id: str, 
        pipeline: Pipeline, 
        endpoint: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Add a pipeline response to the session (backward compatibility).
        
        Args:
            session_id: Unique session identifier.
            pipeline: The pipeline that was called.
            endpoint: The specific endpoint that was called.
            data: The JSON response data from the API.
        """
        self._get_or_create_session(session_id)
        
        key = f"{pipeline.value}:{endpoint}:{datetime.utcnow().timestamp()}"
        
        response = PipelineResponse(
            pipeline=pipeline,
            endpoint=endpoint,
            data=data,
            timestamp=datetime.utcnow()
        )
        
        self._sessions[session_id][key] = response
        
        # Keep limited history
        while len(self._sessions[session_id]) > 7:
            self._sessions[session_id].popitem(last=False)
    
    def update_last_query(
        self, 
        session_id: str, 
        query: str, 
        pipelines: List[Pipeline]
    ) -> None:
        """Update the last query and pipelines called for a session."""
        self._get_or_create_session(session_id)
        self._last_queries[session_id] = query
        self._last_pipelines[session_id] = pipelines
    
    def get_context(self, session_id: str) -> SessionContext:
        """
        Get the current context for a session.
        
        Args:
            session_id: Unique session identifier.
            
        Returns:
            SessionContext with cached messages and query info.
        """
        self._get_or_create_session(session_id)
        
        return SessionContext(
            session_id=session_id,
            previous_messages=self._messages.get(session_id, []).copy(),
            last_query=self._last_queries.get(session_id, ""),
            last_pipelines_called=self._last_pipelines.get(session_id, []),
            previous_responses=list(self._sessions.get(session_id, {}).values())
        )
    
    def build_contextual_query(self, session_id: str, new_query: str) -> str:
        """
        Build a query with context from previous messages.
        
        Args:
            session_id: Unique session identifier.
            new_query: The new user query.
            
        Returns:
            Query with previous context prepended if available.
        """
        context = self.get_context(session_id)
        return context.build_contextual_query(new_query)
    
    def has_context(self, session_id: str) -> bool:
        """Check if session has any cached messages."""
        return bool(self._messages.get(session_id))
    
    def clear_session(self, session_id: str) -> None:
        """Clear all data for a session."""
        if session_id in self._messages:
            del self._messages[session_id]
        if session_id in self._last_queries:
            del self._last_queries[session_id]
        if session_id in self._last_pipelines:
            del self._last_pipelines[session_id]
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def get_message_count(self, session_id: str) -> int:
        """Get the number of cached messages for a session."""
        return len(self._messages.get(session_id, []))


# Global session store instance
_store: Optional[SessionStore] = None


def get_session_store(max_messages: int = 5) -> SessionStore:
    """Get or create the global session store instance."""
    global _store
    if _store is None:
        _store = SessionStore(max_messages=max_messages)
    return _store
