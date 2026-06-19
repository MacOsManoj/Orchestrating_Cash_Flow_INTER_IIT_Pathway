"""
Test script to verify LangGraph conversation history integration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from schemas_v2 import SystemConfigV2
from orchestrator_v3 import create_orchestrator_v3
from dotenv import load_dotenv

load_dotenv()


async def test_conversation_history():
    """Test conversation history with LangGraph checkpointing"""
    print("\n" + "=" * 80)
    print("🧪 TESTING LANGGRAPH CONVERSATION HISTORY")
    print("=" * 80)

    # Configuration
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(" Error: OPENAI_API_KEY not set")
        return False

    config = SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model="gpt-4o-mini",
        llm_temperature=0.0,
        rag_enabled=False,
        cache_enabled=True,
        enable_pathway_forecasts=False,
        enable_dynamic_model_selection=False,
        enable_guardrails=False,
        valuation_weight=0.25,
        return_weight=0.30,
        quality_weight=0.25,
        liquidity_weight=0.20,
        portfolio_db_path=str(project_root / "files-mock" / "portfolios"),
        cache_dir=str(project_root / "files-mock" / "cache"),
        vector_db_path=str(project_root / "vector_store"),
    )

    print("\n Configuration:")
    print(f"   - LLM Model: {config.llm_model}")
    print(f"   - Checkpoint: MemorySaver (in-memory)")

    # Initialize orchestrator
    print("\n Initializing Orchestrator...")
    orchestrator = create_orchestrator_v3(config, rag_system=None)

    user_id = "TEST_USER_001"
    thread_id = f"{user_id}_test_conversation"

    print(f"\n User ID: {user_id}")
    print(f"🧵 Thread ID: {thread_id}")

    # Test 1: First message (no history)
    print("\n" + "=" * 80)
    print("TEST 1: First Message (No History)")
    print("=" * 80)

    query1 = "What are high yield AAA bonds?"
    print(f"\n Query 1: {query1}")

    state1 = await orchestrator.run_async(
        query=query1, user_id=user_id, thread_id=thread_id
    )

    print(f"\n Response 1 received")
    if state1.advisory and state1.advisory.summary:
        print(f"   Summary length: {len(state1.advisory.summary)} chars")
        print(f"   Preview: {state1.advisory.summary[:100]}...")

    # Verify messages in store
    try:
        messages = orchestrator._message_store.get(thread_id, [])
        print(f"\n Messages in store: {len(messages)}")
        for i, msg in enumerate(messages, 1):
            msg_type = type(msg).__name__
            content_preview = (
                msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            )
            print(f"   {i}. {msg_type}: {content_preview}")
    except Exception as e:
        print(f"  Could not read message store: {e}")

    # Test 2: Follow-up message (with history)
    print("\n" + "=" * 80)
    print("TEST 2: Follow-up Message (With History)")
    print("=" * 80)

    query2 = "Tell me more about the first one"
    print(f"\n Query 2: {query2}")

    state2 = await orchestrator.run_async(
        query=query2,
        user_id=user_id,
        thread_id=thread_id,  # Same thread_id = same conversation
    )

    print(f"\n Response 2 received")
    if state2.advisory and state2.advisory.summary:
        print(f"   Summary length: {len(state2.advisory.summary)} chars")
        print(f"   Preview: {state2.advisory.summary[:100]}...")

    # Verify conversation history was used
    try:
        messages = orchestrator._message_store.get(thread_id, [])
        print(f"\n Messages in store after query 2: {len(messages)}")
        print(f"   Expected: 4 messages (2 user + 2 assistant)")
        if len(messages) >= 4:
            print("    Conversation history is being maintained!")
        else:
            print(f"     Expected 4 messages, got {len(messages)}")

        # Show all messages
        for i, msg in enumerate(messages, 1):
            msg_type = type(msg).__name__
            role = "user" if "Human" in msg_type else "assistant"
            content_preview = (
                msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            )
            print(f"   {i}. [{role}] {content_preview}")
    except Exception as e:
        print(f"  Could not read message store: {e}")

    # Test 3: New thread (no history)
    print("\n" + "=" * 80)
    print("TEST 3: New Thread (No History)")
    print("=" * 80)

    new_thread_id = f"{user_id}_new_conversation"
    query3 = "What are the best bonds for retirement?"
    print(f"\n Query 3: {query3}")
    print(f"🧵 New Thread ID: {new_thread_id}")

    state3 = await orchestrator.run_async(
        query=query3,
        user_id=user_id,
        thread_id=new_thread_id,  # Different thread = new conversation
    )

    print(f"\n Response 3 received")
    if state3.advisory and state3.advisory.summary:
        print(f"   Summary length: {len(state3.advisory.summary)} chars")

    # Verify new thread has no history from previous thread
    try:
        messages = orchestrator._message_store.get(new_thread_id, [])
        print(f"\n Messages in new thread: {len(messages)}")
        print(f"   Expected: 2 messages (1 user + 1 assistant)")
        if len(messages) == 2:
            print("    New thread started fresh (no history from previous thread)!")
        else:
            print(f"     Expected 2 messages, got {len(messages)}")
    except Exception as e:
        print(f"  Could not read message store: {e}")

    # Test 4: Verify original thread still has history
    print("\n" + "=" * 80)
    print("TEST 4: Verify Original Thread Still Has History")
    print("=" * 80)

    try:
        messages = orchestrator._message_store.get(thread_id, [])
        print(f"\n Messages in original thread: {len(messages)}")
        if len(messages) >= 4:
            print("    Original thread history preserved!")
        else:
            print(f"     Expected at least 4 messages, got {len(messages)}")
    except Exception as e:
        print(f"  Could not read message store: {e}")

    print("\n" + "=" * 80)
    print(" CONVERSATION HISTORY TEST COMPLETE")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_conversation_history())
    sys.exit(0 if success else 1)
