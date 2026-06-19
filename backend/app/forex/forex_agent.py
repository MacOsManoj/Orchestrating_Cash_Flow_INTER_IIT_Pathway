"""
Forex Explainability Agent - Uses MCP Server for tools
"""

import os
import asyncio
import json
import logging
from typing import Literal, Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_community.chat_models import ChatLiteLLM
from langgraph.graph import StateGraph, MessagesState, START, END

from app.forex.mcp_client import list_tools_sync, call_tool_async

logger = logging.getLogger(__name__)

FOREX_PAIRS = ["EURINR", "GBPINR", "JPYINR", "EURUSD", "GBPUSD", "USDJPY"]
MCP_URL = os.environ.get("PATHWAY_MCP_URL", "http://localhost:8123/mcp/")


def get_tool_schemas() -> List[Dict]:
    """
    Get tool schemas from MCP server in OpenAI function format.
    Dynamically fetches available tools.
    """
    try:
        tools = list_tools_sync(MCP_URL)
        schemas = []

        for tool in tools:
            # Handle both object and dict styles
            if isinstance(tool, dict):
                name = tool.get("name")
                description = tool.get("description")
                parameters = tool.get("inputSchema") or tool.get("parameters")
            else:
                name = getattr(tool, "name", None)
                description = getattr(tool, "description", None)
                parameters = getattr(tool, "inputSchema", None) or getattr(
                    tool, "parameters", None
                )

            if not name:
                continue

            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description or "",
                    "parameters": parameters or {"type": "object", "properties": {}},
                },
            }
            schemas.append(schema)

        return schemas

    except Exception as e:
        logger.error(f"Error fetching tool schemas: {e}")
        # Fallback to hardcoded schema if dynamic fetch fails
        return get_fallback_schemas()


def get_fallback_schemas() -> List[Dict]:
    """Fallback hardcoded schemas if MCP is down - includes all 5 tools"""
    pairs_param = {
        "type": "object",
        "properties": {
            "pairs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of forex pairs (e.g., ['EURUSD', 'GBPUSD'])",
            }
        },
        "required": ["pairs"],
    }

    return [
        {
            "type": "function",
            "function": {
                "name": "get_trades_summary",
                "description": "Get trading performance summary including profit, max drawdown, win rate, Sharpe ratio, and recent trades.",
                "parameters": pairs_param,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_position_details",
                "description": "Get current position details including entry price, unrealized P&L, stop loss, take profit, and model confidence.",
                "parameters": pairs_param,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_currency_regime",
                "description": "Analyze currency regime including bull/bear market, volatility level, and trend type using Hurst exponent.",
                "parameters": pairs_param,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_currency_correlation",
                "description": "Calculate correlation matrix between forex pairs for portfolio diversification analysis.",
                "parameters": pairs_param,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_news_sentiment",
                "description": "Get news sentiment analysis for forex pairs with article summaries and sentiment scores.",
                "parameters": pairs_param,
            },
        },
    ]


async def execute_mcp_tool_async(name: str, args: dict) -> str:
    """Execute an MCP tool asynchronously."""
    try:
        # Normalize arguments
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {"pairs": [p.strip() for p in args.split(",") if p.strip()]}

        if "pairs" in args and isinstance(args["pairs"], str):
            args["pairs"] = [args["pairs"]]

        return await call_tool_async(name, args, MCP_URL)
    except Exception as e:
        return f"Error calling MCP tool {name}: {str(e)}"


def create_forex_agent(api_key: str = None, model: str = "gemini/gemini-2.0-flash"):
    """Create the forex explainability agent (Async)."""
    if api_key:
        if model.startswith("anthropic/"):
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif model.startswith("openai/") or model.startswith("gpt"):
            os.environ["OPENAI_API_KEY"] = api_key
        elif model.startswith("gemini/"):
            os.environ["GEMINI_API_KEY"] = api_key
        else:
            os.environ["OPENAI_API_KEY"] = api_key

    llm = ChatLiteLLM(model=model, temperature=0)

    # Get tool schemas dynamically
    tool_schemas = get_tool_schemas()
    llm_with_tools = llm.bind_tools(tool_schemas)

    SYSTEM_PROMPT = """You are an expert forex trading analyst. You help users understand their forex trading models and portfolio.

Use the available tools to verify your analysis. Available tools are fetched dynamically from the trading system.

Common tools likely available:
- get_trades_summary: Performance metrics
- get_position_details: Current market positions
- get_currency_regime: Market condition analysis
- get_currency_correlation: Pair correlations
- get_news_sentiment: News analysis

Valid pairs: EURINR, GBPINR, JPYINR, EURUSD, GBPUSD, USDJPY

Always answer based on data returned by tools. If a tool fails, explain why."""

    async def agent_node(state: MessagesState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    async def tool_node(state: MessagesState):
        results = []
        last_message = state["messages"][-1]

        # Parallel tool execution
        tasks = []
        tool_call_ids = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_ids.append(tool_call["id"])
            tasks.append(execute_mcp_tool_async(tool_name, tool_args))

        if tasks:
            observations = await asyncio.gather(*tasks)

            for obs, tc_id in zip(observations, tool_call_ids):
                results.append(ToolMessage(content=str(obs), tool_call_id=tc_id))

        return {"messages": results}

    def should_continue(state: MessagesState) -> Literal["tool_node", "__end__"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool_node"
        return "__end__"

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tool_node", "__end__"])
    workflow.add_edge("tool_node", "agent")

    return workflow.compile()


async def run_agent_async(agent, query: str) -> Dict[str, Any]:
    """Run agent asynchronously and return result."""
    messages = [HumanMessage(content=query)]
    result = await agent.ainvoke({"messages": messages})

    tools_called = []
    tool_calls_detailed = []
    tool_outputs = []
    final_response = ""

    # Track tool call IDs to match with outputs
    tool_call_map = {}  # id -> {name, args}

    try:
        for msg in result.get("messages", []):
            if isinstance(msg, AIMessage):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = (
                            tc.get("name", "unknown")
                            if isinstance(tc, dict)
                            else getattr(tc, "name", "unknown")
                        )
                        tool_id = (
                            tc.get("id", "")
                            if isinstance(tc, dict)
                            else getattr(tc, "id", "")
                        )
                        tool_args = (
                            tc.get("args", {})
                            if isinstance(tc, dict)
                            else getattr(tc, "args", {})
                        )

                        tools_called.append(tool_name)
                        if tool_id:
                            tool_call_map[tool_id] = {
                                "name": tool_name,
                                "arguments": tool_args,
                            }
                elif msg.content:
                    final_response = msg.content
            elif isinstance(msg, ToolMessage):
                tool_outputs.append(msg.content)
                # Match with tool call and add to detailed list
                tool_call_id = getattr(msg, "tool_call_id", None)
                if tool_call_id and tool_call_id in tool_call_map:
                    tc_info = tool_call_map[tool_call_id]
                    tool_calls_detailed.append(
                        {
                            "name": tc_info["name"],
                            "arguments": tc_info["arguments"],
                            "output": msg.content,
                        }
                    )
    except Exception as e:
        logger.error(f"Error processing agent messages: {e}")

    return {
        "response": final_response,
        "tools_called": list(set(tools_called)),
        "tool_calls_detailed": tool_calls_detailed,
        "tool_outputs": tool_outputs,
    }


def run_agent_sync(agent, query: str) -> Dict[str, Any]:
    """Run agent synchronously (wrapper around async)."""
    import asyncio
    import threading

    async def _run():
        return await run_agent_async(agent, query)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Clean way to run async from sync in existing loop context strictly requires new thread
        # if loop calls this blocking function
        result_container = {}

        def _runner():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result_container["res"] = new_loop.run_until_complete(_run())
            finally:
                new_loop.close()

        t = threading.Thread(target=_runner)
        t.start()
        t.join()
        return result_container.get("res")
    else:
        return asyncio.run(_run())


if __name__ == "__main__":
    print("Forex Explainability Agent (Async)")
    print("=" * 60)

    # Simple test
    async def main():
        agent = create_forex_agent()
        query = "Analyze EURUSD trading performance"
        print(f"Query: {query}")
        result = await run_agent_async(agent, query)
        print(f"Response: {result['response']}")

    asyncio.run(main())
