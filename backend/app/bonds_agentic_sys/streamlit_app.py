"""
Streamlit UI for Bond Trading Application
ChatGPT-like interface for autonomous bond trading
"""
import streamlit as st
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from schemas_v2 import (
    SystemConfigV2,
    EnhancedAgentState,
    TradeRecommendation,
    BondAnalytics,
    BondScore,
)
from orchestrator_v3 import create_orchestrator_v3
from rag.rag_system import create_rag_system
from dotenv import load_dotenv

load_dotenv()

# Page config
st.set_page_config(
    page_title="Agent Bond - AI Bond Trading Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for ChatGPT-like interface
st.markdown(
    """
<style>
    /* Main container */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    
    /* Chat messages */
    .user-message {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #10b981;
    }
    
    .assistant-message {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Recommendation cards */
    .recommendation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .recommendation-buy {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    .recommendation-sell {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }
    
    .recommendation-hold {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    
    /* Stats */
    .stat-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #3b82f6;
    }
    
    .stat-label {
        font-size: 0.9rem;
        color: #6b7280;
        margin-top: 0.5rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Input area - ChatGPT style */
    .stChatInput > div > div > div {
        border-radius: 25px;
    }
    
    .stChatInput > div > div > div > textarea {
        border-radius: 25px;
        padding: 0.75rem 1.5rem;
        border: 2px solid #e5e7eb;
    }
    
    .stChatInput > div > div > div > textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Chat message styling */
    .stChatMessage {
        padding: 1rem 0;
    }
    
    /* Better spacing */
    .element-container {
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_config():
    """Get current config from session state (not cached, so it updates dynamically)"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Error: OPENAI_API_KEY not set. Please set it in your .env file.")
        st.stop()
    return SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model=st.session_state.get("llm_model", "gpt-4o-mini"),
        llm_temperature=0.0,
        rag_enabled=st.session_state.get("rag_enabled", False),
        cache_enabled=True,
        enable_pathway_forecasts=False,
        enable_dynamic_model_selection=st.session_state.get(
            "enable_dynamic_model_selection", False
        ),
        enable_guardrails=st.session_state.get("enable_guardrails", False),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        guardrails_check_input=st.session_state.get("guardrails_check_input", True),
        guardrails_check_output=st.session_state.get("guardrails_check_output", True),
        valuation_weight=0.25,
        return_weight=0.30,
        quality_weight=0.25,
        liquidity_weight=0.20,
        portfolio_db_path=str(project_root / ".cache" / "portfolios"),
        cache_dir=str(project_root / ".cache"),
        vector_db_path=str(project_root / "vector_store"),
    )


@st.cache_resource
def initialize_orchestrator():
    """Initialize orchestrator (cached)"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Error: OPENAI_API_KEY not set. Please set it in your .env file.")
        st.stop()

    config = get_config()

    # Initialize RAG if enabled
    rag_system = None
    if config.rag_enabled:
        try:
            rag_system = create_rag_system(config)
        except Exception as e:
            st.warning(f"RAG system initialization failed: {e}")

    try:
        orchestrator = create_orchestrator_v3(config, rag_system)

        # Show MCP connection status
        if hasattr(orchestrator, "mcp_connected") and not orchestrator.mcp_connected:
            st.warning(
                " **MCP Server not connected!** Bond predictions will not work.\n\n"
                "Start the MCP server in a separate terminal:\n"
                "```bash\n"
                "cd backend/app/bonds_agentic_sys/pathway_producer_consumer\n"
                "python bond_server.py\n"
                "```"
            )
        return orchestrator, config
    except Exception as e:
        st.error(f"Failed to initialize orchestrator: {e}")
        st.stop()

def display_recommendation(rec: TradeRecommendation, idx: int):
    """Display a single recommendation card"""
    action_colors = {
        "BUY": "recommendation-buy",
        "SELL": "recommendation-sell",
        "HOLD": "recommendation-hold",
        "SWITCH": "recommendation-card",
    }

    color_class = action_colors.get(rec.action, "recommendation-card")

    st.markdown(
        f"""
    <div class="{color_class}">
        <h3 style="margin: 0; color: white;">{rec.action}: {rec.name}</h3>
        <p style="margin: 0.5rem 0; color: rgba(255,255,255,0.9);">ISIN: {rec.isin}</p>
        <p style="margin: 0.5rem 0; color: rgba(255,255,255,0.9);">{rec.rationale}</p>
        <div style="display: flex; gap: 2rem; margin-top: 1rem;">
            <div>
                <strong style="color: rgba(255,255,255,0.9);">Expected Return:</strong>
                <span style="color: white; font-size: 1.2rem;">{rec.expected_return:.2%}</span>
            </div>
            <div>
                <strong style="color: rgba(255,255,255,0.9);">Confidence:</strong>
                <span style="color: white; font-size: 1.2rem;">{rec.confidence:.2%}</span>
            </div>
            <div>
                <strong style="color: rgba(255,255,255,0.9);">Risk Score:</strong>
                <span style="color: white; font-size: 1.2rem;">{rec.risk_score:.2f}</span>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if rec.quantity > 0:
        st.caption(
            f"Quantity: {rec.quantity:,.0f} | Target Price: {rec.target_price or 'N/A'}"
        )


def display_analytics(state: EnhancedAgentState):
    """Display bond analytics in a table"""
    if not state.bond_analytics:
        return

    analytics_data = []
    for isin, analytics in state.bond_analytics.items():
        analytics_data.append(
            {
                "Bond": analytics.name,
                "ISIN": isin,
                "Current Price": f"₹{analytics.current_price:.2f}",
                "Fair Value": f"₹{analytics.fair_value:.2f}",
                "Valuation Gap": f"{analytics.valuation_gap:.2f}%",
                "YTM": f"{analytics.ytm:.2%}",
                "Duration": f"{analytics.duration:.2f}",
                "Rating": analytics.credit_rating.value,
                "Signal": analytics.ml_signal.value,
                "Confidence": f"{analytics.ml_confidence:.2%}",
            }
        )

    df = pd.DataFrame(analytics_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_contextual_analytics(
    state: EnhancedAgentState, focus: list, detail_level: str
):
    """
    Display analytics table with contextual filtering
    """
    if not state.bond_analytics:
        return

    st.subheader("Bond Analytics")

    # Define which columns to show for each focus
    focus_columns = {
        "yield": ["name", "ytm", "current_yield", "coupon_rate"],
        "duration": ["name", "duration", "modified_duration", "convexity"],
        "price": ["name", "current_price", "fair_value", "valuation_gap"],
        "return": ["name", "expected_return", "predicted_price", "ml_confidence"],
        "rating": ["name", "credit_rating", "credit_risk_score", "sector"],
        "liquidity": ["name", "liquidity_score", "volume"],
    }

    # Convert to DataFrame
    data = []
    for isin, analytics in state.bond_analytics.items():
        if hasattr(analytics, "model_dump"):
            row = analytics.model_dump()
        elif hasattr(analytics, "dict"):
            row = analytics.dict()
        else:
            row = analytics
        data.append(row)

    df = pd.DataFrame(data)

    # Filter columns based on focus
    if "all" not in focus:
        display_columns = ["name"]  # Always show name
        for focus_area in focus:
            if focus_area in focus_columns:
                display_columns.extend(focus_columns[focus_area])

        # Remove duplicates, keep order
        display_columns = list(dict.fromkeys(display_columns))

        # Keep only columns that exist
        display_columns = [col for col in display_columns if col in df.columns]

        if display_columns:
            df = df[display_columns]

    # Limit rows based on detail level
    if detail_level == "minimal":
        df = df.head(5)
        st.caption("Showing top 5 bonds")
    elif detail_level == "summary":
        df = df.head(10)
        st.caption("Showing top 10 bonds")

    # Format numeric columns
    for col in df.columns:
        if df[col].dtype in ["float64", "float32"]:
            if "yield" in col or "return" in col or "ytm" in col:
                df[col] = df[col].apply(lambda x: f"{x * 100:.2f}%")
            elif "price" in col or "value" in col:
                df[col] = df[col].apply(lambda x: f"₹{x:.2f}")
            elif "score" in col:
                df[col] = df[col].apply(lambda x: f"{x:.3f}")
            else:
                df[col] = df[col].apply(lambda x: f"{x:.2f}")

    st.dataframe(df, use_container_width=True, hide_index=True)


def display_portfolio(state: EnhancedAgentState):
    """Display portfolio information"""
    if not state.portfolio:
        return

    portfolio = state.portfolio

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Value", f"₹{portfolio.total_value:,.2f}")
    with col2:
        st.metric("Cash", f"₹{portfolio.cash:,.2f}")
    with col3:
        st.metric("Portfolio Duration", f"{portfolio.portfolio_duration:.2f}")
    with col4:
        st.metric("Portfolio YTM", f"{portfolio.portfolio_ytm:.2%}")
    if portfolio.holdings:
        st.subheader("Holdings")
        holdings_data = []
        for holding in portfolio.holdings:
            holdings_data.append(
                {
                    "Bond": holding.bond_name,
                    "ISIN": holding.isin,
                    "Quantity": f"{holding.quantity:,.0f}",
                    "Avg Cost": f"₹{holding.avg_cost:.2f}",
                    "Current Price": f"₹{holding.current_price:.2f}",
                    "Market Value": f"₹{holding.market_value:,.2f}",
                    "Weight": f"{holding.weight:.2%}",
                    "P&L": f"₹{holding.unrealized_pnl:,.2f}",
                }
            )

        df = pd.DataFrame(holdings_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


def display_scores(state: EnhancedAgentState):
    """Display bond scores"""
    if not state.bond_scores:
        return

    scores_data = []
    for isin, score in state.bond_scores.items():
        scores_data.append(
            {
                "Bond": score.name,
                "ISIN": isin,
                "Total Score": f"{score.total_score:.2f}",
                "Rank": score.rank,
                "Valuation": f"{score.valuation_score:.2f}",
                "Return": f"{score.return_score:.2f}",
                "Quality": f"{score.quality_score:.2f}",
                "Liquidity": f"{score.liquidity_score:.2f}",
            }
        )

    df = pd.DataFrame(scores_data)
    df = df.sort_values("Total Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_execution_plan(state: EnhancedAgentState):
    """Display execution plan details"""
    if not state.execution_plan:
        return

    plan = state.execution_plan

    with st.expander("Execution Plan Details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Tools Used:**")
            for tool in plan.tools_needed:
                st.write(f"- {tool.tool_type.value}")
        with col2:
            st.write("**Agents Used:**")
            for agent in plan.agents_needed:
                st.write(f"- {agent.value}")
        st.write("**Reasoning:**")
        st.info(plan.reasoning)


def display_processing_stats(state: EnhancedAgentState):
    """Display processing statistics"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Processing Time", f"{state.processing_time:.2f}s")
    with col2:
        st.metric("Tool Calls", state.total_tool_calls)
    with col3:
        st.metric("Cache Hits", state.cache_hits)
    with col4:
        cache_rate = (state.cache_hits / max(state.total_tool_calls, 1)) * 100
        st.metric("Cache Hit Rate", f"{cache_rate:.1f}%")


def render_markdown_safe(content: str) -> None:
    """
    Safely render markdown content, handling edge cases
    Args:
        content: Markdown content to render
    """
    if not content:
        return

    # Ensure content is a string
    content_str = str(content) if not isinstance(content, str) else content

    # Remove any null bytes or problematic characters that might break rendering
    content_str = content_str.replace("\x00", "")

    # Normalize line endings
    content_str = content_str.replace("\r\n", "\n").replace("\r", "\n")

    # Use st.write() which automatically detects and renders markdown, LaTeX, and other formats
    # This is the recommended way in Streamlit chat messages as it handles all content types
    st.write(content_str)


def main():
    """Main Streamlit app"""

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "orchestrator" not in st.session_state:
        with st.spinner("Initializing Agent Bond system..."):
            try:
                orchestrator, config = initialize_orchestrator()
                st.session_state.orchestrator = orchestrator
                st.session_state.config = config
                st.success("Orchestrator V3 (LangGraph) initialized!")
            except Exception as e:
                st.error(f"Failed to initialize: {e}")
                import traceback

                st.code(traceback.format_exc())
                st.stop()

    # Update orchestrator config dynamically before each query (so guardrails settings take effect immediately)
    if "orchestrator" in st.session_state:
        config = get_config()
        # Update config in orchestrator so guardrails settings are respected
        st.session_state.orchestrator.config = config
        # Also update guardrails enabled state dynamically
        if st.session_state.orchestrator.guardrails:
            st.session_state.orchestrator.guardrails.enabled = config.enable_guardrails
    # Sidebar for settings
    with st.sidebar:
        st.title("Settings")
        st.session_state.llm_model = st.selectbox(
            "LLM Model", ["gpt-4o-mini", "gpt-4-turbo-preview", "gpt-4"], index=0
        )
        st.session_state.rag_enabled = st.checkbox("Enable RAG", value=False)
        st.session_state.user_id = st.text_input("User ID", value="demo_user")

        # Model selection settings
        st.markdown("---")
        st.subheader("Model Selection")
        st.session_state.enable_dynamic_model_selection = st.checkbox(
            "Enable Dynamic Model Selection",
            value=st.session_state.get("enable_dynamic_model_selection", False),
            help="Dynamically select GPT-5 models based on query complexity. If disabled, uses fixed model for all agents.",
        )

        # Guardrails settings
        st.markdown("---")
        st.subheader("Guardrails")
        st.session_state.enable_guardrails = st.checkbox(
            "Enable Guardrails",
            value=st.session_state.get("enable_guardrails", False),
            help="Enable safety checks using Llama Guard 4-12B",
        )
        if st.session_state.enable_guardrails:
            st.session_state.guardrails_check_input = st.checkbox(
                "Check Input",
                value=st.session_state.get("guardrails_check_input", True),
            )
            st.session_state.guardrails_check_output = st.checkbox(
                "Check Output",
                value=st.session_state.get("guardrails_check_output", True),
            )
            if not os.getenv("GROQ_API_KEY"):
                st.warning(
                    "Warning: GROQ_API_KEY not set. Guardrails require Groq API key."
                )

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # Main title with better styling
    st.markdown(
        """
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #3b82f6; margin-bottom: 0.5rem;">Agent Bond</h1>
        <p style="color: #6b7280; font-size: 1.1rem;">AI Bond Trading Assistant</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Welcome message if no chat history
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("""
            **Welcome to Agent Bond!** 
            
            I'm your AI bond trading assistant. I can help you with:
            
            -  **Bond Recommendations**: Get personalized trading recommendations
            -  **Analytics**: Analyze bond performance, yields, and risk metrics
            -  **Portfolio Management**: Review and optimize your bond portfolio
            -  **Market Insights**: Understand yield curves, credit ratings, and market trends
            
            **Try asking me:**
            - "Find high yield AAA bonds with good liquidity"
            - "Recommend bonds to reduce my portfolio duration"
            - "What are the best PSU bonds for my portfolio?"
            - "Analyze my portfolio and suggest improvements"
            """)
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Use safe markdown rendering
            render_markdown_safe(message.get("content", ""))

            # Display recommendations if available
            if message["role"] == "assistant" and "state" in message:
                state = message["state"]

                # Display advisory summary
                # Display advisory summary FIRST
                if state.advisory:
                    # Always show summary if it exists
                    if state.advisory.summary:
                        st.markdown(state.advisory.summary)
                    # Then show recommendations if they exist
                    if state.advisory.recommendations:
                        st.markdown("### Recommendations")
                        for idx, rec in enumerate(state.advisory.recommendations, 1):
                            display_recommendation(rec, idx)
                    else:
                        st.info("No specific recommendations generated.")
                    if state.advisory.summary:
                        st.markdown("**Summary:**")
                        # Use safe markdown rendering
                        render_markdown_safe(state.advisory.summary)
                # Display analytics
                if state.bond_analytics:
                    with st.expander("Bond Analytics", expanded=False):
                        display_analytics(state)
                # Display scores
                if state.bond_scores:
                    with st.expander("🏆 Bond Scores", expanded=False):
                        display_scores(state)
                # Display portfolio
                if state.portfolio:
                    with st.expander("Portfolio", expanded=False):
                        display_portfolio(state)

                # Display execution plan
                display_execution_plan(state)

                # Display processing stats
                with st.expander("⚡ Processing Stats", expanded=False):
                    display_processing_stats(state)

    # Chat input
    if prompt := st.chat_input(
        "Ask about bonds, portfolios, or get recommendations..."
    ):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            render_markdown_safe(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your query..."):
                try:
                    # Run orchestrator (handle async in Streamlit)
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Use thread_id for LangGraph conversation history management
                    # Thread ID combines user_id with session for proper conversation tracking
                    thread_id = f"{st.session_state.user_id}_{st.session_state.get('session_id', 'default')}"

                    # Optionally pass conversation history for backward compatibility
                    # LangGraph will use checkpointing with thread_id to manage history
                    conversation_history = [
                        {
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        }
                        for msg in st.session_state.messages[-10:]  # Last 10 messages
                        if msg.get("role")
                        in ["user", "assistant"]  # Only include valid roles
                    ]

                    state = loop.run_until_complete(
                        st.session_state.orchestrator.run_async(
                            query=prompt,
                            user_id=st.session_state.user_id,
                            thread_id=thread_id,
                            conversation_history=conversation_history,  # Optional, for backward compatibility
                        )
                    )

                    # Display response from response agent
                    # The response agent always generates an AdvisoryOutput with a summary
                    if state.advisory and state.advisory.summary:
                        response_text = state.advisory.summary
                    elif state.advisory:
                        # Advisory exists but summary is empty - this shouldn't happen normally
                        response_text = "I've processed your query, but no response was generated. Please try rephrasing your question."
                    else:
                        # No advisory output - this indicates the response agent didn't run
                        response_text = "I encountered an issue processing your query. Please try again."

                    # Render markdown properly using safe rendering function
                    render_markdown_safe(response_text)

                    # Display recommendations
                    if state.advisory and state.advisory.recommendations:
                        st.markdown("### Recommendations")
                        for idx, rec in enumerate(state.advisory.recommendations, 1):
                            display_recommendation(rec, idx)
                    # # Display analytics
                    if state.bond_analytics:
                        with st.expander("Bond Analytics", expanded=False):
                            display_analytics(state)
                    # # Display scores
                    if state.bond_scores:
                        with st.expander("🏆 Bond Scores", expanded=False):
                            display_scores(state)
                    # # Display portfolio
                    if state.portfolio:
                        with st.expander("Portfolio", expanded=False):
                            display_portfolio(state)

                    # # Display execution plan
                    display_execution_plan(state)

                    # # Display processing stats
                    with st.expander("⚡ Processing Stats", expanded=False):
                        display_processing_stats(state)

                    # Add assistant message to history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text, "state": state}
                    )

                except Exception as e:
                    error_msg = f" Error processing query: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )


if __name__ == "__main__":
    main()
