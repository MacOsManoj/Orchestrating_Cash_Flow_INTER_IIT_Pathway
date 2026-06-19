#!/usr/bin/env python3
"""
Test script to verify Query Classifier routing for the Bond Pipeline.
Matches the architecture: UI → Query Classifier → (LLM / Web Search / News APIs / Credit Risk / Orchestrator)

Usage:
    export OPENAI_API_KEY="your-key"
    python test_classifier_routing.py
"""

import sys
import os

sys.path.insert(0, "agents")

from dotenv import load_dotenv

load_dotenv()

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    print("Run: export OPENAI_API_KEY='your-key'")
    sys.exit(1)

from query_classifier import QueryClassifierAgent, QueryType


def test_classifier():
    """Test query classification routing"""

    print("Creating Query Classifier Agent...")
    classifier = QueryClassifierAgent()
    print(" Classifier created successfully!\n")

    # Test queries with expected routes
    test_queries = [
        # (query, expected_route, description)
        ("show my portfolio", "orchestrator", "Portfolio query"),
        ("who won wimbledon 2025", "web_search", "Sports - off topic"),
        ("what is the credit rating of HDFC", "credit_risk", "Credit risk query"),
        ("high yield bonds", "orchestrator", "Bond search"),
        ("latest RBI policy news", "news_scraper", "Financial news"),
        ("what is duration in bonds", "llm", "Bond education"),
        ("recommend bonds for me", "orchestrator", "Advisory query"),
        ("what is bitcoin price today", "web_search", "Crypto - off topic"),
        ("CRISIL rating for Tata Motors", "credit_risk", "Credit rating"),
        ("calculate YTM for 8% coupon", "orchestrator", "Calculation"),
    ]

    print("Testing Query Classifier Routing:")
    print("=" * 70)
    print(f"{'Query':<40} {'Expected':<15} {'Actual':<15} {'Status'}")
    print("-" * 70)

    passed = 0
    failed = 0

    for query, expected, description in test_queries:
        initial_state = {
            "messages": [],
            "query": query,
            "classification": None,
            "search_results": None,
            "news_results": None,
            "final_response": None,
            "error": None,
        }

        try:
            result = classifier.graph.invoke(initial_state)
            classification = result.get("classification")

            if classification:
                actual = classification.query_type.value
                status = " PASS" if actual == expected else "✗ FAIL"
                if actual == expected:
                    passed += 1
                else:
                    failed += 1

                # Truncate query for display
                display_query = query[:38] + ".." if len(query) > 40 else query
                print(f"{display_query:<40} {expected:<15} {actual:<15} {status}")

                if actual != expected:
                    print(f"   Reasoning: {classification.reasoning[:60]}...")
            else:
                failed += 1
                print(f"{query:<40} {expected:<15} {'N/A':<15} ✗ NO CLASSIFICATION")

        except Exception as e:
            failed += 1
            print(f"{query:<40} {expected:<15} {'ERROR':<15} ✗ {str(e)[:30]}")

    print("-" * 70)
    print(
        f"\nResults: {passed} passed, {failed} failed out of {len(test_queries)} tests"
    )

    if failed == 0:
        print("\n All tests passed! Query Classifier is routing correctly.")
    else:
        print(f"\n✗ {failed} tests failed. Review the classifier prompts.")

    return failed == 0


def test_full_flow():
    """Test the full flow with responses"""
    print("\n" + "=" * 70)
    print("Testing Full Query Flow (Classification + Response)")
    print("=" * 70)

    classifier = QueryClassifierAgent()

    # Test one query from each category
    test_cases = [
        ("who won the 2024 T20 world cup", "web_search"),
        ("what is the credit rating of Reliance", "credit_risk"),
    ]

    for query, expected_route in test_cases:
        print(f"\n--- Query: '{query}' ---")

        initial_state = {
            "messages": [],
            "query": query,
            "classification": None,
            "search_results": None,
            "news_results": None,
            "final_response": None,
            "error": None,
        }

        result = classifier.graph.invoke(initial_state)
        classification = result.get("classification")

        if classification:
            print(f"Routed to: {classification.query_type.value}")
            print(f"Confidence: {classification.confidence:.2f}")

        response = result.get("final_response", "No response")
        if response:
            # Truncate long responses
            display_response = (
                response[:200] + "..." if len(response) > 200 else response
            )
            print(f"Response preview:\n{display_response}")


if __name__ == "__main__":
    print("Bond Pipeline - Query Classifier Test")
    print("Architecture: UI → Query Classifier → Agents")
    print()

    success = test_classifier()

    # Only run full flow test if basic tests pass
    if success and len(sys.argv) > 1 and sys.argv[1] == "--full":
        test_full_flow()

    sys.exit(0 if success else 1)
