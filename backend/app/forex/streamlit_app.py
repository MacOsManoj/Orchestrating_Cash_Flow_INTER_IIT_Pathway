"""
Forex Explainability Agent - Streamlit UI
Minimal interface for querying the forex trading analysis agent
"""

import streamlit as st
import os

from dotenv import load_dotenv

# Add backend directory to sys.path to allow absolute imports
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Load environment variables from .env file
load_dotenv()

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Page configuration
st.set_page_config(page_title="Forex Agent", page_icon="💱", layout="centered")

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = None


def get_tool_display_name(tool_name: str) -> str:
    """Get formatted display name for tool"""
    if tool_name is None:
        return "Unknown Tool"
    tool_names = {
        "get_trades_summary": "Trade Summary",
        "get_position_details": "Position Details",
        "get_currency_regime": "Market Regime Analysis",
        "get_currency_correlation": "Correlation Matrix",
        "get_news_sentiment": "News Sentiment",
    }
    return tool_names.get(tool_name, tool_name.replace("_", " ").title())


def initialize_agent():
    """Initialize the forex agent"""
    from forex_agent import create_forex_agent

    try:
        agent = create_forex_agent()
        return agent
    except Exception as e:
        st.error(f"Error initializing agent: {str(e)}")
        return None


import queue
import threading
import asyncio


def run_agent_with_status(agent, query: str):
    """Run agent and yield status updates"""
    messages = [HumanMessage(content=query)]

    # Use a queue to communicate between the async thread and the sync generator
    q = queue.Queue()
    _SENTINEL = object()

    def _run_async():
        async def _process():
            try:
                # Use astream (async) instead of stream (sync)
                async for event in agent.astream(
                    {"messages": messages}, stream_mode="values"
                ):
                    q.put(event)
            except Exception as e:
                q.put(e)
            finally:
                q.put(_SENTINEL)

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_process())
        finally:
            loop.close()

    # Start the async processing in a background thread
    t = threading.Thread(target=_run_async)
    t.start()

    tool_calls_made = []
    tool_outputs = {}
    pending_tool_calls = {}
    final_response = ""

    # Consume events from queue
    while True:
        try:
            event = q.get()

            if event is _SENTINEL:
                break

            if isinstance(event, Exception):
                raise event

            msgs = event.get("messages", [])
            if msgs:
                for msg in msgs:
                    if isinstance(msg, AIMessage):
                        has_tool_calls = (
                            hasattr(msg, "tool_calls")
                            and msg.tool_calls
                            and len(msg.tool_calls) > 0
                        )

                        if has_tool_calls:
                            for tc in msg.tool_calls:
                                tool_name = tc.get("name", "unknown")
                                tool_id = tc.get("id", "")
                                if tool_name not in tool_calls_made:
                                    tool_calls_made.append(tool_name)
                                    pending_tool_calls[tool_id] = tool_name
                                    yield ("tool_start", tool_name, None)
                        elif msg.content:
                            final_response = msg.content

                    elif isinstance(msg, ToolMessage):
                        tool_id = getattr(msg, "tool_call_id", None)
                        tool_name = (
                            pending_tool_calls.get(tool_id)
                            or getattr(msg, "name", None)
                            or "unknown_tool"
                        )
                        if msg.content and tool_name:
                            tool_outputs[tool_name] = msg.content
                            yield ("tool_complete", tool_name, msg.content)

        except queue.Empty:
            continue

    yield ("response", final_response, tool_outputs)


# Title
st.title("Forex Agent")

# Example queries
st.subheader("Example Queries")
example_queries = [
    "Analyze EURUSD - trades, position, and market regime",
    "What's the correlation between all INR pairs?",
    "Give me a full portfolio overview",
    "How is USDJPY performing and what's the news sentiment?",
    "Compare EURUSD and GBPUSD trading performance",
]

for eq in example_queries:
    if st.button(eq, use_container_width=True, key=f"example_{hash(eq)}"):
        st.session_state.selected_query = eq

# Query input
st.subheader("Enter Your Query")
query = st.text_area(
    "Ask about your forex portfolio",
    value=st.session_state.get("selected_query", ""),
    placeholder="Enter your query...",
    height=100,
    label_visibility="collapsed",
)

if st.session_state.get("selected_query"):
    del st.session_state.selected_query

# Submit button
if st.button("Analyze", use_container_width=True, type="primary"):
    if query:
        if st.session_state.agent is None:
            with st.spinner("Initializing agent..."):
                st.session_state.agent = initialize_agent()

        if st.session_state.agent:
            st.subheader("Analysis Report")
            response_placeholder = st.empty()

            try:
                final_response = ""
                tool_outputs = {}

                for result in run_agent_with_status(st.session_state.agent, query):
                    status_type = result[0]
                    content = result[1]
                    extra = result[2] if len(result) > 2 else None

                    if status_type == "tool_complete":
                        if extra:
                            tool_outputs[content] = extra

                    elif status_type == "response":
                        final_response = content
                        if extra:
                            tool_outputs.update(extra)

                # Display LLM response
                response_placeholder.markdown(final_response)

                # Show tool outputs in dropdown if any
                if tool_outputs:
                    with st.expander("🔧 Tool Results"):
                        for tool_name, output in tool_outputs.items():
                            if tool_name and output:
                                st.markdown(f"**{get_tool_display_name(tool_name)}**")
                                st.code(output, language="json")

            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                import traceback

                st.code(traceback.format_exc())
    else:
        st.warning("Please enter a query")
