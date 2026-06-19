"""
Test script to verify conversation history with name
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


async def test_name_conversation():
    """Test conversation history with name"""
    print("\n" + "=" * 80)
    print("🧪 TESTING CONVERSATION HISTORY WITH NAME")
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

    # Initialize orchestrator
    print("\n Initializing Orchestrator...")
    orchestrator = create_orchestrator_v3(config, rag_system=None)

    user_id = "TEST_USER_002"
    thread_id = f"{user_id}_name_test"

    print(f"\n User ID: {user_id}")
    print(f"🧵 Thread ID: {thread_id}")

    # Test 1: User says their name
    print("\n" + "=" * 80)
    print("TEST 1: User says their name")
    print("=" * 80)

    query1 = "my name is johnny"
    print(f"\n Query 1: {query1}")

    state1 = await orchestrator.run_async(
        query=query1, user_id=user_id, thread_id=thread_id
    )

    print(f"\n Response 1 received")
    if state1.advisory and state1.advisory.summary:
        print(f"   Summary: {state1.advisory.summary[:200]}...")

    # Check messages in store
    messages1 = orchestrator._message_store.get(thread_id, [])
    print(f"\n Messages in store after query 1: {len(messages1)}")
    for i, msg in enumerate(messages1, 1):
        msg_type = type(msg).__name__
        content_preview = (
            msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        )
        print(f"   {i}. {msg_type}: {content_preview}")

    # Test 2: User asks for their name
    print("\n" + "=" * 80)
    print("TEST 2: User asks for their name")
    print("=" * 80)

    query2 = "what is my name"
    print(f"\n Query 2: {query2}")

    state2 = await orchestrator.run_async(
        query=query2,
        user_id=user_id,
        thread_id=thread_id,  # Same thread_id = same conversation
    )

    print(f"\n Response 2 received")
    if state2.advisory and state2.advisory.summary:
        print(f"   Summary: {state2.advisory.summary}")
        if "johnny" in state2.advisory.summary.lower():
            print("    SUCCESS: System remembered the name!")
        else:
            print("    FAILED: System did not remember the name")

    # Check messages in store
    messages2 = orchestrator._message_store.get(thread_id, [])
    print(f"\n Messages in store after query 2: {len(messages2)}")
    for i, msg in enumerate(messages2, 1):
        msg_type = type(msg).__name__
        content_preview = (
            msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        )
        print(f"   {i}. {msg_type}: {content_preview}")

    print("\n" + "=" * 80)
    print(" CONVERSATION HISTORY TEST COMPLETE")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_name_conversation())
    sys.exit(0 if success else 1)
