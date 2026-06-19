"""
Test Script for Orchestrator
============================

Interactive interface to test the full orchestrator flow:
Query → Router → Component Selector → API → Transform → JSON Output

Usage:
    cd /home/aditya/pathway_venv/upgraded-octo-spork
    source ../bin/activate
    python master_orchestrator/test_orchestrator.py
"""

import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from master_orchestrator import (
    Orchestrator,
    get_orchestrator,
    process_query,
    get_ready_components,
    COMPONENT_REGISTRY
)


def print_json(data, indent=2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def show_ready_components():
    """Display which components are ready (have transformers)."""
    ready = get_ready_components()
    print("\n📦 Ready Components (with transformers):")
    for comp_id in ready:
        config = COMPONENT_REGISTRY.get(comp_id, {})
        comp_type = config.get("type", "Unknown")
        if hasattr(comp_type, "value"):
            comp_type = comp_type.value
        print(f"   • {comp_id}: {comp_type}")
    
    print("\n⏳ Not Ready Components:")
    for comp_id, config in COMPONENT_REGISTRY.items():
        if comp_id not in ready:
            comp_type = config.get("type", "Unknown")
            if hasattr(comp_type, "value"):
                comp_type = comp_type.value
            print(f"   • {comp_id}: {comp_type}")


async def interactive_session():
    """Interactive session to test orchestrator."""
    print("\n" + "=" * 60)
    print("ORCHESTRATOR TEST - INTERACTIVE SESSION")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set. Set it in .env or environment.")
        print("   export OPENAI_API_KEY='your-key-here'")
        return
    
    print("✅ API Key found")
    print("⚠️  Make sure backend is running: uvicorn backend.main:app --reload")
    
    show_ready_components()
    
    print("\n" + "-" * 60)
    print("Type your queries to test the full orchestrator flow.")
    print("Commands:")
    print("  'quit'     - Exit")
    print("  'ready'    - Show ready components")
    print("  'verbose'  - Toggle verbose mode (show routing/selection details)")
    print("-" * 60)
    
    verbose = True
    
    while True:
        try:
            query = input("\n🔹 Query: ").strip()
            
            if not query:
                continue
            
            if query.lower() == 'quit':
                print("Goodbye!")
                break
            
            if query.lower() == 'ready':
                show_ready_components()
                continue
            
            if query.lower() == 'verbose':
                verbose = not verbose
                print(f"Verbose mode: {'ON' if verbose else 'OFF'}")
                continue
            
            # Process the query
            print("\n⏳ Processing...")
            result = await process_query(query)
            
            # Display results
            print("\n" + "=" * 60)
            print("📊 RESULT")
            print("=" * 60)
            
            if verbose:
                # Show routing decision
                if result.get("routing"):
                    print("\n🔀 Routing Decision:")
                    print(f"   Pipelines: {result['routing'].get('pipelines', [])}")
                    print(f"   Reasoning: {result['routing'].get('reasoning', 'N/A')}")
                
                # Show component selection
                if result.get("selection"):
                    print("\n🎯 Component Selection:")
                    print(f"   Components: {result['selection'].get('components', [])}")
                    print(f"   Reasoning: {result['selection'].get('reasoning', 'N/A')}")
            
            # Show errors if any
            if result.get("errors"):
                print("\n❌ Errors:")
                for err in result["errors"]:
                    print(f"   • {err}")
            
            # Show the main output - formatted for frontend (matching schema.json)
            print("\n📦 Frontend Output (matching schema.json):")
            frontend_output = {
                "message": result.get("message", ""),
                "components": result.get("components", [])
            }
            print_json(frontend_output)
            
            print("\n" + "-" * 60)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


async def single_query_test(query: str):
    """Run a single query and print full result."""
    print(f"\n📝 Query: {query}")
    print("-" * 40)
    
    result = await process_query(query)
    
    print("\n📊 Full Internal Result:")
    print_json(result)
    
    print("\n📦 Frontend Output (matching schema.json):")
    frontend_output = {
        "message": result.get("message", ""),
        "components": result.get("components", [])
    }
    print_json(frontend_output)


def main():
    print("=" * 60)
    print("ORCHESTRATOR TEST MENU")
    print("=" * 60)
    print("\n1. Interactive Session")
    print("2. Quick Test (single query: 'Show forex correlation')")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(interactive_session())
    elif choice == "2":
        asyncio.run(single_query_test("Show me the forex correlation matrix"))
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice. Running interactive session...")
        asyncio.run(interactive_session())


if __name__ == "__main__":
    main()
