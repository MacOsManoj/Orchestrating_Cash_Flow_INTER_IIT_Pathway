import asyncio
import json
from typing import Dict
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from ..schema import YieldTrend

# Configuration
BONDS_SERVER_URL = "http://localhost:8002/mcp"  # Bonds Pipeline MCP Server

async def _call_remote_tool(session, tool_name: str, arguments: Dict) -> any:
    """
    Helper to call a remote tool on the MCP server.
    """
    try:
        result = await session.call_tool(tool_name, arguments=arguments)
        if result.content and hasattr(result.content[0], 'text'):
             return result.content[0].text
        return result
    except Exception as e:
        print(f"Error calling {tool_name}: {e}")
        return None

async def get_bond_yield_trend_async() -> Dict:
    """
    Calls the Bonds MCP Server to get the predicted yield trend.
    
    The Bonds Pipeline:
    1. Reads the user's current portfolio state internally
    2. Runs the prediction through its agents
    3. Returns the yield trend prediction
    
    Returns:
        Dict with 'yield_trend' (YieldTrend enum) and optional details
    """
    try:
        async with sse_client(BONDS_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call the prediction tool
                # The pipeline handles portfolio reading internally
                prediction_json = await _call_remote_tool(
                    session, 
                    "get_predicted_yield_trend",  # Tool exposed by Bonds Pipeline
                    {}  # No arguments needed - pipeline reads portfolio internally
                )
                
                if not prediction_json:
                    return {"yield_trend": YieldTrend.FLAT}
                
                # Parse JSON response
                data = json.loads(prediction_json) if isinstance(prediction_json, str) else prediction_json
                
                # Expected response format from Bonds Pipeline:
                # {
                #   "trend": "RISING" | "FALLING" | "FLAT",
                #   "confidence": 0.85,           # optional
                #   "predicted_change": 0.25,     # optional, in percentage points
                #   "reasoning": "..."            # optional, from LLM
                # }
                
                # Map string to YieldTrend enum
                trend_str = data.get("trend", "FLAT").upper()
                
                if trend_str == "RISING" or trend_str == "UP":
                    yield_trend = YieldTrend.RISING
                elif trend_str == "FALLING" or trend_str == "DOWN":
                    yield_trend = YieldTrend.FALLING
                else:
                    yield_trend = YieldTrend.FLAT
                
                return {
                    "yield_trend": yield_trend,
                    "confidence": data.get("confidence"),
                    "predicted_change": data.get("predicted_change"),
                    "reasoning": data.get("reasoning")
                }
                
    except Exception as e:
        print(f"Failed to connect to Bonds MCP Server: {e}")
        # Fallback: Return FLAT (neutral) if connection fails
        return {"yield_trend": YieldTrend.FLAT}
