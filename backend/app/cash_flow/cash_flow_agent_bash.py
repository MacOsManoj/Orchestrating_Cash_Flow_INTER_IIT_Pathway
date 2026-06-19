import argparse
import sys
from typing import Annotated, Literal, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from functools import wraps
import os

# Market Tools
from market_tools import (
    get_stock_indices,
    get_forex_performance,
    get_commodity_performance,
    get_bond_yields,
    get_fii_dii_via_nsepython,
    get_advance_decline_analysis,
    get_sector_info,
    get_india_vix,
    get_india_pmi_data,
    get_india_inflation_data,
    get_india_gdp_data,
    get_latest_gst_summary,
    get_index_valuation_snapshot,
    get_index_pcr_summary,
)


# Liquidity Tools
from liquidity_risk_tools import (
    get_cashflow_prediction,
    get_cashflow_shap_explanation,
    predict_liquidity_regime,
)


#  Tool Wrapper
def wrap(fn):
    @tool
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


# Market Agent Tools
market_tools = [
    wrap(get_stock_indices),
    wrap(get_forex_performance),
    wrap(get_commodity_performance),
    wrap(get_bond_yields),
    wrap(get_fii_dii_via_nsepython),
    wrap(get_advance_decline_analysis),
    wrap(get_sector_info),
    wrap(get_india_vix),
    wrap(get_india_pmi_data),
    wrap(get_india_inflation_data),
    wrap(get_india_gdp_data),
    wrap(get_latest_gst_summary),
    wrap(get_index_valuation_snapshot),
    wrap(get_index_pcr_summary),
]

# Liquidity Agent Tools
liquidity_tools = [
    wrap(get_cashflow_prediction),
    wrap(get_cashflow_shap_explanation),
    wrap(predict_liquidity_regime),
]


# Global state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    route: str | None


# Initialize the graph
graph = StateGraph(State)

# Initialize the LLM
load_dotenv()
llm = ChatOpenAI(model="gpt-4o")


# Router Agent
def router_node(state: State) -> State:
    user_query = state["messages"][-1]

    router_prompt = f"""
You are a routing classifier.

Decide which agent(s) should handle the query.

Agents:
- "market" → analysing the general market information for banks and there are tools like getting information on the stock indices, forex, commodities, bonds, VIX, sector performance, FII/DII, advance decline analysis.
- "liquidity" → whenever the user asks to calculate next days cashflow or whenever a person asks why model predicted the cashflow it has predicted and that is got from varaible importance from shap score.
- "both" → if the query needs both.

Return exactly one word: market, liquidity, or both.

Query:
{user_query}
"""

    route = llm.invoke(router_prompt).content.strip().lower()

    if route not in ["market", "liquidity", "both"]:
        route = "market"

    return {"messages": [], "route": route}


graph.add_node("router", router_node)
graph.set_entry_point("router")

# Market Agent
market_llm = llm.bind_tools(market_tools)


def market_agent(state: State) -> State:
    system_prompt = {
        "role": "system",
        "content": "You are a market analysis agent. You are providing a solution for banks on getting general information about the market and providing it to bank treasurer using which the treasurer decide on whether to invest in market(stock, bonds and forex). If there is any liquidity risk or cash flow in the query ignore that and only do market regarding things answering there is other agent for that.",
    }

    messages = state["messages"]
    has_system = any(
        (hasattr(m, "type") and m.type == "system")
        or (isinstance(m, dict) and m.get("role") == "system")
        for m in messages
    )
    if not has_system:
        messages = [system_prompt] + messages

    msg = market_llm.invoke(messages)
    return {"messages": messages + [msg]}


graph.add_node("market_agent", market_agent)

market_tool_node = ToolNode(market_tools)
graph.add_node("market_tools", market_tool_node)


def should_continue_market(state: State) -> Literal["market_tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "market_tools"
    if not last_message.tool_calls and state["route"] == "both":
        return "liquidity_agent"
    return "__end__"


graph.add_conditional_edges(
    "market_agent",
    should_continue_market,
    {
        "market_tools": "market_tools",
        "liquidity_agent": "liquidity_agent",
        "__end__": "__end__",
    },
)

graph.add_edge("market_tools", "market_agent")

# Liquidity Agent
liquidity_llm = llm.bind_tools(liquidity_tools)


def liquidity_agent(state: State) -> State:
    system_prompt = {
        "role": "system",
        "content": "You are a liquidity risk analysis agent for banks. Help them predict cashflows for the future and provide explainability of the predictions using SHAP values if the user ask for explainability. If the user asks for explainability, reply how the parameters led to the prediction and convince the bank treasurer why we predicted that cashflow.",
    }

    messages = state["messages"]
    has_system = any(
        (hasattr(m, "type") and m.type == "system")
        or (isinstance(m, dict) and m.get("role") == "system")
        for m in messages
    )
    if not has_system:
        messages = [system_prompt] + messages

    msg = liquidity_llm.invoke(messages)
    return {"messages": messages + [msg]}


graph.add_node("liquidity_agent", liquidity_agent)

liquidity_tool_node = ToolNode(liquidity_tools)
graph.add_node("liquidity_tools", liquidity_tool_node)


def should_continue_liquidity(
    state: State,
) -> Literal["liquidity_tools", "merge", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "liquidity_tools"
    if state.get("route") == "both":
        state["liquidity"] = last_message.content
        return "merge"
    return "__end__"


graph.add_conditional_edges(
    "liquidity_agent",
    should_continue_liquidity,
    {"liquidity_tools": "liquidity_tools", "merge": "merge", "__end__": "__end__"},
)

graph.add_edge("liquidity_tools", "liquidity_agent")


# merger agent
def merge_node(state: State) -> State:
    merge_prompt = f"""
Combine the following two agent outputs into a single clear answer.

{state.get("messages")}

Produce a single unified explanation.
"""
    final = llm.invoke(merge_prompt)
    return {"messages": [final]}


graph.add_node("merge", merge_node)


# Route logic
def route_logic(state: State):
    route = state.get("route")
    if route == "market":
        return "market_agent"
    if route == "liquidity":
        return "liquidity_agent"
    if route == "both":
        return "market_agent"
    return "__end__"


graph.add_conditional_edges("router", route_logic)

APP = graph.compile()


# CLI Interface
def interactive_mode():
    """Run in interactive mode with persistent state"""
    print("=== Bank Analysis Agent ===")
    print("Type 'exit' or 'quit' to end the session\n")

    # Initialize state with empty messages
    state = {"messages": [], "route": None}

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Add user message to state
            state["messages"].append({"role": "user", "content": user_input})

            # Invoke the graph with current state
            result = APP.invoke(state)

            # Update state with result
            state = result

            # Get the last assistant message
            last_msg = None
            for msg in reversed(state["messages"]):
                if hasattr(msg, "content") and msg.content:
                    last_msg = msg.content
                    break
                elif isinstance(msg, dict) and msg.get("content"):
                    last_msg = msg["content"]
                    break

            if last_msg:
                print(f"\nAssistant: {last_msg}\n")
            else:
                print("\nAssistant: [No response generated]\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}\n")


def single_query_mode(query: str):
    """Run a single query"""
    state = {"messages": [{"role": "user", "content": query}], "route": None}

    result = APP.invoke(state)

    # Get the last assistant message
    last_msg = None
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.content:
            last_msg = msg.content
            break
        elif isinstance(msg, dict) and msg.get("content"):
            last_msg = msg["content"]
            break

    if last_msg:
        print(last_msg)
    else:
        print("[No response generated]")


def main():
    parser = argparse.ArgumentParser(
        description="Bank Analysis Agent - Market & Liquidity Analysis"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query mode: provide a question and get an answer",
    )

    args = parser.parse_args()

    if args.query:
        single_query_mode(args.query)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
