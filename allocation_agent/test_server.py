import json
import asyncio
from .server import agent

async def test_e2e_async():
    queries = [
        "I want aggressive growth but max 40% stocks."
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        
        # Run Async
        result = await agent.run(query)
        
        print(f"Intent: {result['intent']}")
        print(f"Signals: {result['signals']}")
        if 'forex_opportunity_index' in result['signals']:
            print(f"Forex Index: {result['signals']['forex_opportunity_index']}")
        print(f"Allocation: {result['allocation']}")
        print(f"Reasoning:\n{result['reasoning']}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_e2e_async())
