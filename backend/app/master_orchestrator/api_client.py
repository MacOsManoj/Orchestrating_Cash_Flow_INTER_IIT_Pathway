"""
API Client
==========

Async HTTP client for calling pipeline FastAPI endpoints.
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
import logging

from .schemas import Pipeline, PipelineResponse
from .pipeline_registry import PIPELINE_ENDPOINTS

logger = logging.getLogger(__name__)


class PipelineAPIClient:
    """
    Async HTTP client for calling pipeline APIs.
    
    Features:
    - Parallel execution for multiple pipelines
    - Timeout handling
    - Error resilience
    """
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize the API client.
        
        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
    
    async def call_endpoint(
        self,
        pipeline: Pipeline,
        endpoint_name: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call a specific pipeline endpoint.
        
        Args:
            pipeline: The pipeline to call.
            endpoint_name: Name of the endpoint (e.g., "regime", "trades").
            params: Query parameters.
            json_body: JSON body for POST requests.
            method: HTTP method (GET, POST, etc.). Can be overridden by registry.
            query: User's original query (used for stock agent POST requests).
            
        Returns:
            JSON response as dict, or error dict if failed.
        """
        config = PIPELINE_ENDPOINTS.get(pipeline)
        if not config:
            return {"error": True, "message": f"Unknown pipeline: {pipeline}"}
        
        endpoint_path = config["endpoints"].get(endpoint_name)
        if not endpoint_path:
            return {"error": True, "message": f"Unknown endpoint: {endpoint_name} for {pipeline}"}
        
        url = f"{config['base_url']}{endpoint_path}"
        
        # Check for method override in registry
        method_overrides = config.get("method_overrides", {})
        if endpoint_name in method_overrides:
            method = method_overrides[endpoint_name]
        
        # For POST endpoints that need query in body
        if method.upper() == "POST" and query and not json_body:
            # Special handling for bonds/chat endpoint
            if pipeline == Pipeline.BONDS and endpoint_name == "chat":
                json_body = {
                    "prompt": query,
                    "user_id": "orchestrator"
                }
            else:
                # Default for other POST endpoints (e.g., stock agent)
                json_body = {"query": query}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, json=json_body, params=params)
                else:
                    response = await client.request(method, url, json=json_body, params=params)
                
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"Timeout calling {url}")
            return {"error": True, "message": f"Timeout calling {pipeline.value}/{endpoint_name}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} calling {url}")
            return {"error": True, "message": f"HTTP {e.response.status_code}: {str(e)}"}
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
            return {"error": True, "message": str(e)}
    
    async def call_pipelines_parallel(
        self,
        calls: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Call multiple pipeline endpoints in parallel.
        
        Args:
            calls: List of call specs, each with:
                - pipeline: Pipeline enum
                - endpoint: endpoint name
                - params: optional query params
                - json_body: optional POST body
                - method: HTTP method (default GET)
                
        Returns:
            Dict mapping "pipeline:endpoint" to response data.
        """
        async def make_call(call_spec: Dict) -> tuple:
            pipeline = call_spec["pipeline"]
            endpoint = call_spec["endpoint"]
            result = await self.call_endpoint(
                pipeline=pipeline,
                endpoint_name=endpoint,
                params=call_spec.get("params"),
                json_body=call_spec.get("json_body"),
                method=call_spec.get("method", "GET")
            )
            key = f"{pipeline.value}:{endpoint}"
            return key, result
        
        tasks = [make_call(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel call failed: {result}")
                continue
            key, data = result
            output[key] = data
        
        return output


# Default client instance
_client: Optional[PipelineAPIClient] = None


def get_api_client(timeout: float = 30.0) -> PipelineAPIClient:
    """Get or create the default API client."""
    global _client
    if _client is None:
        _client = PipelineAPIClient(timeout=timeout)
    return _client
