import json
import sys
from .server import get_portfolio_recommendation

def main():
    print("==========================================")
    print("   Orchestrator Agent - Interactive CLI   ")
    print("==========================================")
    print("Type 'exit' or 'quit' to stop.")
    print("Ensure your .env file has a valid GROQ_API_KEY.\n")
    
    while True:
        try:
            query = input(">> Enter your financial query: ").strip()
        except EOFError:
            break
            
        if not query:
            continue
            
        if query.lower() in ['exit', 'quit']:
            print("Exiting...")
            break
            
        print("\n... Analyzing Query & Market Conditions ...")
        
        try:
            # Call the Agent via the exposed Tool function
            response_json = get_portfolio_recommendation(query)
            data = json.loads(response_json)
            
            # Display Results
            print("\n" + "-"*40)
            print("ANALYSIS REPORT")
            print("-"*40)
            
            # 1. Intent & Constraints
            print(f"USER INTENT: {data['intent']}")
            constraints = data.get('constraints', {})
            if any(constraints.values()):
                print("CONSTRAINTS DETECTED:")
                for k, v in constraints.items():
                    if v is not None:
                        print(f"  - {k}: {v}")
            
            # 2. Market Context
            print(f"\nMARKET CONTEXT (Aggregated Signals):")
            sig = data['signals']
            print(f"  - Sentiment:      {sig['sentiment']}")
            print(f"  - Volatility:     {sig['volatility']}")
            print(f"  - Liquidity Risk: {sig['liquidity_risk']}")
            print(f"  - Yield Trend:    {sig['yield_trend']}")
            
            # 3. Conflict Warning
            cw = data.get('conflict_warning')
            if cw and cw['detected']:
                print(f"\n[!] CONFLICT WARNING: {cw['message']}")
            
            # 4. Allocation
            print(f"\nRECOMMENDED ALLOCATION:")
            alloc = data['allocation']
            print(f"  [ STOCKS ] : {alloc['stocks']*100:5.1f} %")
            print(f"  [ BONDS  ] : {alloc['bonds']*100:5.1f} %")
            print(f"  [ FOREX  ] : {alloc['forex']*100:5.1f} %")
            print(f"  [ CASH   ] : {alloc['cash']*100:5.1f} %")
            
            # 5. Reasoning
            print(f"\nREASONING ENGINE TRACE:")
            for line in data['reasoning'].split('\n'):
                print(f"  > {line}")
            
            print("-" * 40 + "\n")
            
        except Exception as e:
            print(f"\n[ERROR] Failed to process query: {e}")
            print("Check logs or API Key configuration.\n")

if __name__ == "__main__":
    main()
