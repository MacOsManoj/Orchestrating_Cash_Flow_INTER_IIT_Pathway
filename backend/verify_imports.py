#!/usr/bin/env python3
"""
Verify all critical imports work before starting services
"""
import sys
import os

# Add bonds_agentic_sys to path
bonds_path = os.path.join(os.path.dirname(__file__), "app", "bonds_agentic_sys")
if bonds_path not in sys.path:
    sys.path.insert(0, bonds_path)

# Add forex to path
forex_path = os.path.join(os.path.dirname(__file__), "app", "forex")
if forex_path not in sys.path:
    sys.path.insert(0, forex_path)

errors = []

# Test critical imports
print("🔍 Verifying imports...")

# Core dependencies
try:
    import chromadb
    print("✅ chromadb")
except ImportError as e:
    errors.append(f"❌ chromadb: {e}")

try:
    import pathway
    print("✅ pathway")
except ImportError as e:
    errors.append(f"⚠️ pathway: {e} (optional)")

try:
    import langchain
    print("✅ langchain")
except ImportError as e:
    errors.append(f"❌ langchain: {e}")

try:
    import langgraph
    print("✅ langgraph")
except ImportError as e:
    errors.append(f"❌ langgraph: {e}")

# Bonds agentic system imports
try:
    from utils.mcp_client import create_mcp_client
    print("✅ bonds_agentic_sys.utils.mcp_client")
except ImportError as e:
    errors.append(f"❌ bonds_agentic_sys.utils.mcp_client: {e}")

try:
    from utils.logger import setup_logger
    print("✅ bonds_agentic_sys.utils.logger")
except ImportError as e:
    errors.append(f"❌ bonds_agentic_sys.utils.logger: {e}")

try:
    from schemas_v2 import SystemConfigV2
    print("✅ bonds_agentic_sys.schemas_v2")
except ImportError as e:
    errors.append(f"❌ bonds_agentic_sys.schemas_v2: {e}")

try:
    from orchestrator_v3 import create_orchestrator_v3
    print("✅ bonds_agentic_sys.orchestrator_v3")
except ImportError as e:
    errors.append(f"❌ bonds_agentic_sys.orchestrator_v3: {e}")

# Forex imports
try:
    import pathway as pw
    from pathway.xpacks.llm.mcp_server import McpServable
    print("✅ forex pathway MCP")
except ImportError as e:
    errors.append(f"⚠️ forex pathway MCP: {e} (optional)")

# Print results
if errors:
    print("\n❌ Import errors found:")
    for error in errors:
        print(f"  {error}")
    sys.exit(1)
else:
    print("\n✅ All critical imports verified!")
    sys.exit(0)

