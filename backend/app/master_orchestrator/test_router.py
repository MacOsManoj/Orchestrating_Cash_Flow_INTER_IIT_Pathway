"""
Interactive Test Script for Router Agent
=========================================

Interactive session to test Router Agent with custom queries.

Usage:
    cd /home/aditya/pathway_venv/upgraded-octo-spork
    source ../bin/activate
    python master_orchestrator/test_router.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from master_orchestrator import (
    RouterAgent, 
    get_session_store, 
    PipelineAPIClient,
    Pipeline,
    SessionContext
)


def interactive_router_session():
    """Interactive session to test Router Agent"""
    print("\n" + "="*60)
    print("ROUTER AGENT - INTERACTIVE SESSION")
    print("="*60)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set. Set it in .env or environment.")
        print("   export OPENAI_API_KEY='your-key-here'")
        return
    
    router = RouterAgent()
    store = get_session_store()
    session_id = "interactive-session"
    store.clear_session(session_id)
    
    print("\n✅ Router Agent initialized")
    print("Type your queries to test pipeline routing.")
    print("Commands: 'quit' to exit, 'clear' to reset session context\n")
    
    while True:
        try:
            query = input("\n🔹 You: ").strip()
            
            if not query:
                continue
            
            if query.lower() == 'quit':
                print("Goodbye!")
                break
            
            if query.lower() == 'clear':
                store.clear_session(session_id)
                print("✅ Session context cleared.")
                continue
            
            # Get context for follow-ups
            ctx = store.get_context(session_id)
            
            # Route the query
            print("\n⏳ Routing...")
            decision = router.route(query, ctx)
            
            print(f"\n📊 Routing Decision:")
            print(f"   Pipelines: {[p.upper() for p in decision.selected_pipelines]}")
            print(f"   Reasoning: {decision.reasoning}")
            print(f"   Follow-up: {'Yes' if decision.requires_context else 'No'}")
            
            # Update session context
            store.update_last_query(session_id, query, decision.selected_pipelines)
            
            # Show context summary
            if ctx.previous_responses:
                print(f"\n📝 Context: {len(ctx.previous_responses)} previous responses in memory")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def test_api_calls():
    """Test API Client - Call actual endpoints (requires backend running)"""
    print("\n" + "="*60)
    print("API CLIENT - CALLING ENDPOINTS")
    print("="*60)
    print("⚠️  Make sure backend is running: uvicorn backend.main:app --reload")
    
    client = PipelineAPIClient(timeout=10.0)
    
    # Test Forex endpoints
    print("\n--- FOREX Pipeline ---")
    forex_endpoints = ["pairs", "recommended_trades", "health"]
    for endpoint in forex_endpoints:
        print(f"\nCalling: {endpoint}")
        result = await client.call_endpoint(Pipeline.FOREX, endpoint)
        if isinstance(result, dict) and result.get("error"):
            print(f"  ❌ {result.get('message')}")
        elif isinstance(result, dict):
            print(f"  ✅ Success - Keys: {list(result.keys())[:5]}...")
        else:
            print(f"  ✅ Success - Got response (type: {type(result).__name__})")
    
    # Test Cashflow endpoints
    print("\n--- CASHFLOW Pipeline ---")
    cashflow_endpoints = ["opening_closing_balance", "liquidity_regime", "in_out_flow"]
    for endpoint in cashflow_endpoints:
        print(f"\nCalling: {endpoint}")
        result = await client.call_endpoint(Pipeline.CASHFLOW, endpoint)
        if isinstance(result, dict) and result.get("error"):
            print(f"  ❌ {result.get('message')}")
        elif isinstance(result, dict):
            print(f"  ✅ Success - Keys: {list(result.keys())[:5]}...")
        else:
            print(f"  ✅ Success - Got response (type: {type(result).__name__})")


async def test_full_flow():
    """Full flow - Router + API + Session (requires API key and backend)"""
    print("\n" + "="*60)
    print("FULL FLOW - Router → API → Session")
    print("="*60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set. Skipping.")
        return
    
    router = RouterAgent()
    client = PipelineAPIClient(timeout=10.0)
    store = get_session_store()
    session_id = "full-flow-test"
    store.clear_session(session_id)
    
    # Query 1: Initial forex query
    query1 = "Show me current forex pairs overview"
    print(f"\n[Turn 1] User: \"{query1}\"")
    
    ctx = store.get_context(session_id)
    decision = router.route(query1, ctx)
    print(f"Router: Selected {[p.upper() for p in decision.selected_pipelines]}")
    
    if "forex" in decision.selected_pipelines:
        result = await client.call_endpoint(Pipeline.FOREX, "pairs")
        if not result.get("error"):
            store.add_response(session_id, Pipeline.FOREX, "pairs", result)
            store.update_last_query(session_id, query1, decision.selected_pipelines)
            print(f"API: Got {len(result.get('pairs', []))} forex pairs")
        else:
            print(f"API Error: {result.get('message')}")
    
    # Query 2: Follow-up
    query2 = "What are the recommended trades for those?"
    print(f"\n[Turn 2] User: \"{query2}\"")
    
    ctx = store.get_context(session_id)
    decision = router.route(query2, ctx)
    print(f"Router: Selected {[p.upper() for p in decision.selected_pipelines]}, requires_context={decision.requires_context}")
    
    if "forex" in decision.selected_pipelines:
        result = await client.call_endpoint(Pipeline.FOREX, "recommended_trades")
        if not result.get("error"):
            store.add_response(session_id, Pipeline.FOREX, "recommended_trades", result)
            print(f"API: Got {len(result.get('trades', []))} trade recommendations")
        else:
            print(f"API Error: {result.get('message')}")
    
    store.clear_session(session_id)
    print("\n✅ Full flow completed")


def main():
    print("="*60)
    print("MASTER ORCHESTRATOR - TEST MENU")
    print("="*60)
    print("\n1. Interactive Router Session (Router only, no backend needed)")
    print("2. API Endpoint Tests (Requires backend running)")
    print("3. Full Flow Test (Requires API key + backend)")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        interactive_router_session()
    elif choice == "2":
        asyncio.run(test_api_calls())
    elif choice == "3":
        asyncio.run(test_full_flow())
    elif choice == "4":
        print("Goodbye!")
    else:
        print("Invalid choice. Running interactive session by default...")
        interactive_router_session()


if __name__ == "__main__":
    main()
