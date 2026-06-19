# import os
# from typing import Literal
# from langgraph.graph import StateGraph, END, START
# from langchain_core.messages import HumanMessage

# # Import Refactored Modules
# from schemas_v2 import AgentState, Bond
# from portfolio_manager import portfolio_node, constraint_check_node
# from analyst import analyst_node
# from advisory_agent import advisory_node
# from query_classifier import classify_and_respond # Assuming you keep the logic, just simplified

# # --- Mock Data Loader (Simplified) ---
# def load_market_data(state: AgentState):
#     """Simulates fetching live market feed."""
#     print("--- System: Fetching Market Data ---")
#     bonds = [
#         Bond(isin="IN002", name="HDFC 2028", issuer="HDFC", rating="AAA",
#              sector="Finance", ytm=7.85, duration=3.5, price=100.5),
#         Bond(isin="IN003", name="Infra Bond", issuer="IRFC", rating="AAA",
#              sector="Infra", ytm=7.60, duration=8.0, price=99.0)
#     ]
#     return {"market_data": bonds}

# # --- Response Generator ---
# def response_generator(state: AgentState):
#     """Summarizes the final state into a user message."""
#     recs = state.get("trade_recommendations", [])
#     if not recs:
#         return {"messages": [HumanMessage(content="No trades recommended at this time.")]}

#     msg = "**Advisory Report**\n\n"
#     for r in recs:
#         msg += f"- **{r.action.upper()}** {r.bond_isin}: {r.rationale} (Conf: {r.confidence})\n"

#     return {"messages": [HumanMessage(content=msg)]}

# # --- The Graph ---

# workflow = StateGraph(AgentState)

# # 1. Add Nodes
# workflow.add_node("load_portfolio", portfolio_node)
# workflow.add_node("load_market", load_market_data)
# workflow.add_node("analyst", analyst_node)
# workflow.add_node("advisory", advisory_node)
# workflow.add_node("compliance", constraint_check_node)
# workflow.add_node("responder", response_generator)

# # 2. Define Edges (The Pipeline)
# # Start -> Load Data (Parallel)
# workflow.add_edge(START, "load_portfolio")
# workflow.add_edge(START, "load_market")

# # Data Loaded -> Analyst
# workflow.add_edge("load_portfolio", "analyst")
# workflow.add_edge("load_market", "analyst")

# # Analyst -> Advisory
# workflow.add_edge("analyst", "advisory")

# # Advisory -> Compliance Check
# workflow.add_edge("advisory", "compliance")

# # Compliance -> Responder -> End
# workflow.add_edge("compliance", "responder")
# workflow.add_edge("responder", END)

# # 3. Compile
# app = workflow.compile()

# # --- Execution Interface ---

# def run_bond_agent(query: str, bank_id: str):
#     initial_state = {
#         "query": query,
#         "bank_id": bank_id,
#         "messages": [],
#         "analysis_reports": [],
#         "trade_recommendations": []
#     }

#     result = app.invoke(initial_state)
#     print("\n\n=== FINAL OUTPUT ===")
#     print(result["messages"][-1].content)

# if __name__ == "__main__":
#     # Test
#     run_bond_agent("Analyze market for opportunities", "BANK_001")
