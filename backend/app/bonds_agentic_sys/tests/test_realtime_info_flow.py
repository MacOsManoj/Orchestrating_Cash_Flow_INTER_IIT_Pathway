"""
Test script for real-time info flow
Tests the complete flow: query classification -> real-time info gathering -> advisory
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from orchestrator_v3 import create_orchestrator_v3
from schemas_v2 import SystemConfigV2


async def test_realtime_info_flow():
    """Test the complete real-time info flow"""

    print("=" * 80)
    print("TESTING REAL-TIME INFO FLOW")
    print("=" * 80)

    # Create config
    config = SystemConfigV2(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        serpapi_key=os.getenv("SERPAPI_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        llm_model="gpt-4o-mini",
        enable_guardrails=False,
        enable_dynamic_model_selection=False,
    )

    # Create orchestrator
    orchestrator = create_orchestrator_v3(config)

    # Test queries
    test_queries = [
        "What bonds should I buy if RBI cuts rates by 50bps?",
        "If inflation data comes in higher than expected, how will bond prices vary?",
        "Show me high yielding corporate bonds",
        "What should I invest in given current market conditions?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(test_queries)}: {query}")
        print(f"{'=' * 80}\n")

        try:
            result = await orchestrator.run_async(
                query=query,
                user_id="test_user",
                bonds_universe=None,
                user_profile=None,
                conversation_history=None,
            )

            # Check results
            print(f"\n{'=' * 80}")
            print("RESULTS:")
            print(f"{'=' * 80}")

            # Check if real-time info was gathered
            if hasattr(result, "advisory") and result.advisory:
                print(f"\n Advisory generated")
                print(f"  Summary: {result.advisory.summary[:200]}...")
                print(f"  Recommendations: {len(result.advisory.recommendations)}")

            # Check execution path
            if hasattr(result, "execution_plan") and result.execution_plan:
                print(f"\n Execution plan created")
                print(
                    f"  Tools: {[t.tool_type.value for t in result.execution_plan.tools_needed]}"
                )

            # Check for real-time info in state (if accessible)
            print(f"\n Processing time: {result.processing_time:.2f}s")
            print(f" Cache hits: {result.cache_hits}/{result.total_tool_calls}")

            # Check tool results
            if result.tool_results:
                print(f"\n Tool results:")
                for tool_type, tool_result in result.tool_results.items():
                    if tool_result.success:
                        # Handle different data types
                        if tool_result.data:
                            try:
                                data_count = len(tool_result.data)
                                print(
                                    f"  - {tool_type.value}: {data_count} items (cached: {tool_result.cached})"
                                )
                            except TypeError:
                                # Not a list/dict, just show type
                                data_type = type(tool_result.data).__name__
                                print(
                                    f"  - {tool_type.value}: {data_type} object (cached: {tool_result.cached})"
                                )
                        else:
                            print(
                                f"  - {tool_type.value}: No data (cached: {tool_result.cached})"
                            )
                    else:
                        print(f"  - {tool_type.value}: Error - {tool_result.error}")

            print(f"\n{'=' * 80}\n")

        except Exception as e:
            print(f"\n ERROR in test {i}: {e}")
            import traceback

            traceback.print_exc()
            print(f"\n{'=' * 80}\n")

    print("=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_realtime_info_flow())
