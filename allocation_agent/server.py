from mcp.server.fastmcp import FastMCP
from .agent import OrchestratorAgent

# Initialize the MCP Server
mcp = FastMCP("OrchestratorAgent")

# Initialize the Agent
agent = OrchestratorAgent()

@mcp.tool()
async def get_portfolio_recommendation(query: str) -> str:
    """
    Analyzes the user's financial query and current market conditions to recommend a portfolio allocation.
    
    Args:
        query: The user's natural language query (e.g., "I want to invest safely" or "High growth please").
        
    Returns:
        A JSON string containing the determined intent, market signals, and recommended asset allocation.
    """
    result = await agent.run(query)
    # Convert to string/JSON for MCP output
    import json
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    # Run the server
    mcp.run()
