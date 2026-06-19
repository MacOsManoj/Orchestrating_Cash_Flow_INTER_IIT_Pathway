#!/bin/bash
# Wrapper script to run bond_server.py with correct Python environment

# Get the backend directory (3 levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Change to backend directory to use correct venv
cd "$BACKEND_DIR"

# Use uv run to ensure correct environment
if command -v uv &> /dev/null; then
    uv run python app/bonds_agentic_sys/pathway_producer_consumer/bond_server.py "$@"
else
    # Fallback to venv Python
    if [ -f ".venv/bin/python" ]; then
        .venv/bin/python app/bonds_agentic_sys/pathway_producer_consumer/bond_server.py "$@"
    else
        echo "Error: No Python environment found. Please run from backend directory or install uv."
        exit 1
    fi
fi

