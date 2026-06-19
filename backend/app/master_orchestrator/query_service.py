"""
Query Service
=============

Handles text message queries for different pipelines.
Each pipeline has a different query pattern:

- STOCKS: POST /api/stocks/agent/query → extract final_response.summary
- BONDS: POST /api/bonds/agent/chat → GET /api/bonds/agent/output?query_id=X → extract output
- CASHFLOW: GET /api/cashflow/query?query=X → extract result
- FOREX: POST /forex/v1/agent/query → extract response
- NEWS: No query endpoint (use component data instead)
"""

import asyncio
import logging
from typing import Any, Optional
import httpx

from .schemas import Pipeline
from .pipeline_registry import PIPELINE_ENDPOINTS, BACKEND_BASE_URL

logger = logging.getLogger(__name__)


class QueryService:
    """Service to get text messages from pipeline query endpoints."""
    
    def __init__(self, timeout: float = 60.0):
        """
        Initialize QueryService.
        
        Args:
            timeout: Request timeout in seconds (default 60s for agent queries)
        """
        self.timeout = timeout
        self.base_url = BACKEND_BASE_URL
    
    async def get_message(
        self, 
        pipeline: Pipeline, 
        query: str,
        params: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Get text message from the appropriate pipeline query endpoint.
        
        Args:
            pipeline: The pipeline to query
            query: The user's natural language query
            params: Optional parameters (e.g., ticker, isin, currency_pair)
        
        Returns:
            Text message from the pipeline's agent/query response
        """
        params = params or {}
        
        try:
            if pipeline == Pipeline.STOCKS:
                return await self._query_stocks(query, params)
            elif pipeline == Pipeline.BONDS:
                return await self._query_bonds(query, params)
            elif pipeline == Pipeline.CASHFLOW:
                return await self._query_cashflow(query)
            elif pipeline == Pipeline.FOREX:
                return await self._query_forex(query, params)
            elif pipeline == Pipeline.NEWS:
                # NEWS pipeline doesn't have a query endpoint
                return "News sentiment data retrieved from market sources."
            else:
                return f"Query service not available for {pipeline.value} pipeline."
        except Exception as e:
            logger.error(f"Error querying {pipeline.value} pipeline: {e}")
            return f"Unable to retrieve detailed analysis. Error: {str(e)}"
    
    async def _query_stocks(self, query: str, params: dict[str, Any]) -> str:
        """
        Query stocks agent.
        
        POST http://35.238.12.76:3000/query
        Response: { success: true, response: { summary: "..." }, ticker: "..." }
        """
        # Use external stock agent endpoint
        url = "http://ec2-13-211-124-214.ap-southeast-2.compute.amazonaws.com:3000/query"
        
        
        # Build request body
        request_body = {
            "query": query,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            # Extract summary from response (nested under 'response' key)
            response_data = data.get("response", {})
            summary = response_data.get("summary", "")
            
            if summary:
                return summary
            
            # Fallback: try twitter_output.summary from nested response
            twitter_output = response_data.get("twitter_output", {})
            if twitter_output.get("summary"):
                return twitter_output["summary"]
            
            return "Stock analysis completed. Please refer to the data components for details."
    
    async def _query_bonds(self, query: str, params: dict[str, Any]) -> str:
        """
        Query bonds agent via /chat POST endpoint.
        
        POST /api/bond/chat
        Request: {"prompt": "...", "user_id": "orchestrator"}
        Response: {"success": true, "response": "...", "recommendations": [...], ...}
        """
        url = f"{self.base_url}/api/bonds/chat"
        
        # Build request body matching ChatRequest model
        request_body = {
            "prompt": query,
            "user_id": "orchestrator",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            # Check if successful
            if not data.get("success", False):
                error_msg = data.get("error", "Unknown error")
                return f"Bond analysis encountered an error: {error_msg}"
            
            # Extract response text
            response_text = data.get("response", "")
            if response_text:
                return response_text
            
            return "Bond analysis completed. Please refer to the data components for details."
    
    async def _query_cashflow(self, query: str) -> str:
        """
        Query cashflow agent (simple GET).
        
        GET /api/cashflow/query?query=X
        Response: { result: "..." }
        """
        url = f"{self.base_url}/api/cashflow/query"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params={"query": query})
            response.raise_for_status()
            data = response.json()
            
            # Extract result
            result = data.get("result", "")
            if result:
                return result
            
            return "Cashflow analysis completed. Please refer to the data components for details."
    
    async def _query_forex(self, query: str, params: dict[str, Any]) -> str:
        """
        Query forex agent.
        
        POST /forex/v1/agent/query
        Response: { response: "...", tools_called: [...] }
        """
        url = f"{self.base_url}/forex/v1/agent/query"
        
        # Build request body
        request_body = {
            "query": query,
        }
        if "pairs" in params:
            request_body["pairs"] = params["pairs"]
        elif "currency_pair" in params:
            # Convert single pair to list
            request_body["pairs"] = [params["currency_pair"]]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            # Extract response text
            response_text = data.get("response", "")
            if response_text:
                return response_text
            
            return "Forex analysis completed. Please refer to the data components for details."


# Singleton instance
_query_service: Optional[QueryService] = None


def get_query_service() -> QueryService:
    """Get or create the query service singleton."""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service


async def get_pipeline_message(
    pipeline: Pipeline, 
    query: str,
    params: Optional[dict[str, Any]] = None
) -> str:
    """
    Convenience function to get message from a pipeline.
    
    Args:
        pipeline: The pipeline to query
        query: The user's natural language query
        params: Optional parameters
    
    Returns:
        Text message from the pipeline
    """
    service = get_query_service()
    return await service.get_message(pipeline, query, params)
