"""
Script to visualize the LangGraph architecture from orchestrator_v3.py
Dynamically extracts graph structure from the actual LangGraph
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from schemas_v2 import SystemConfigV2
from orchestrator_v3 import create_orchestrator_v3
from dotenv import load_dotenv

load_dotenv()


def visualize_graph():
    """Create orchestrator and print graph diagram dynamically"""
    # Create minimal config for visualization
    config = SystemConfigV2(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        serpapi_key=os.getenv("SERPAPI_KEY", ""),
        llm_model="gpt-4o-mini",
        portfolio_db_path="data/portfolios.db",
        enable_guardrails=False,
        enable_dynamic_model_selection=False,
    )

    # Create orchestrator (this builds the graph)
    print("Building graph...")
    orchestrator = create_orchestrator_v3(config)

    # Get the compiled graph
    graph = orchestrator.graph
    graph_struct = graph.get_graph()

    print("\n" + "=" * 80)
    print("LANGGRAPH AGENTIC ARCHITECTURE DIAGRAM")
    print("=" * 80 + "\n")

    # Extract graph information dynamically
    nodes = list(graph_struct.nodes.keys())
    edges = graph_struct.edges
    conditional_edges_map = {}

    # Process edges to separate regular and conditional
    regular_edges = []
    for edge in edges:
        if edge.conditional:
            # This is a conditional edge
            source = edge.source
            if source not in conditional_edges_map:
                conditional_edges_map[source] = []
            conditional_edges_map[source].append(
                {"condition": edge.data, "target": edge.target}
            )
        else:
            regular_edges.append((edge.source, edge.target))

    # Filter out special nodes (__start__, __end__)
    actual_nodes = [n for n in nodes if not n.startswith("__")]

    # Print Mermaid Diagram
    try:
        mermaid_diagram = graph_struct.draw_mermaid()
        print("Mermaid Diagram:")
        print("-" * 80)
        print(mermaid_diagram)
        print("-" * 80)

        # Save to file (save to project root, not utils/)
        output_file = project_root / "graph_diagram.mmd"
        with open(output_file, "w") as f:
            f.write(mermaid_diagram)
        print(f"\n Mermaid diagram saved to: {output_file}")
    except Exception as e:
        print(f"Could not generate Mermaid diagram: {e}")

    # Print ASCII Diagram
    try:
        print("\nASCII Diagram:")
        print("-" * 80)
        print(graph_struct.draw_ascii())
        print("-" * 80)
    except Exception as e:
        print(f"Could not generate ASCII diagram: {e}")

    # Print Graph Structure (dynamically extracted)
    print("\n" + "=" * 80)
    print("GRAPH STRUCTURE (Dynamically Extracted)")
    print("=" * 80 + "\n")

    print(f"Total Nodes: {len(actual_nodes)}")
    print(f"Regular Edges: {len(regular_edges)}")
    print(f"Conditional Edges: {len(conditional_edges_map)}")

    # Print all nodes
    print("\nNodes:")
    print("-" * 80)
    for node in sorted(actual_nodes):
        print(f"  • {node}")

    # Print regular edges
    print("\nRegular Edges:")
    print("-" * 80)
    for source, target in sorted(regular_edges):
        if not source.startswith("__") and not target.startswith("__"):
            print(f"  • {source} → {target}")

    # Print conditional edges
    print("\nConditional Edges:")
    print("-" * 80)
    for source, conditions in sorted(conditional_edges_map.items()):
        if not source.startswith("__"):
            for cond_info in conditions:
                condition = cond_info["condition"] or "default"
                target = cond_info["target"]
                if not target.startswith("__"):
                    print(f"  • {source} → [{condition}] → {target}")

    # Build execution flow summary
    print("\n" + "=" * 80)
    print("EXECUTION FLOW SUMMARY")
    print("=" * 80 + "\n")

    # Find entry point
    entry_point = None
    for edge in edges:
        if edge.source == "__start__":
            entry_point = edge.target
            break

    if entry_point:
        print(f"  Entry Point: {entry_point}\n")
        print("  Main Execution Path:")
        print("  " + "-" * 76)

        # Build adjacency list
        adjacency = {}
        for source, target in regular_edges:
            if source not in adjacency:
                adjacency[source] = []
            adjacency[source].append(("regular", target))

        for source, conditions in conditional_edges_map.items():
            if source not in adjacency:
                adjacency[source] = []
            for cond_info in conditions:
                adjacency[source].append(
                    ("conditional", cond_info["condition"], cond_info["target"])
                )

        # Print main flow path
        print(f"  START → {entry_point}")
        _print_main_path(entry_point, adjacency, visited=set())

    print("\n" + "=" * 80)


def _print_main_path(node, adjacency, visited, depth=0):
    """Print main execution path through the graph"""
    if node in visited or node.startswith("__") or depth > 20:
        if node == "__end__":
            print("    → END")
        return

    visited.add(node)

    if node not in adjacency:
        print("    → END")
        return

    targets = adjacency[node]

    # Prioritize regular edges first, then show conditional as alternatives
    regular_targets = [t for t in targets if t[0] == "regular"]
    conditional_targets = [t for t in targets if t[0] == "conditional"]

    # Print regular edges (main path)
    for target_info in regular_targets:
        target = target_info[1]
        if not target.startswith("__"):
            print(f"    → {target}")
            _print_main_path(target, adjacency, visited.copy(), depth + 1)

    # Print conditional edges as alternatives
    if conditional_targets:
        for target_info in conditional_targets:
            condition = target_info[1] or "default"
            target = target_info[2]
            if not target.startswith("__"):
                print(f"    → [{condition}] → {target}")
                _print_main_path(target, adjacency, visited.copy(), depth + 1)


if __name__ == "__main__":
    visualize_graph()
