#!/bin/bash

# Bond Pipeline Services Startup Script
# Starts both the MCP server and Streamlit app

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Bond Pipeline Services${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found. Please install Python 3.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Make sure OPENAI_API_KEY is set.${NC}\n"
fi

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill MCP server if running
    if [ ! -z "$MCP_PID" ]; then
        echo -e "${YELLOW}   Stopping MCP server (PID: $MCP_PID)...${NC}"
        kill $MCP_PID 2>/dev/null || true
        wait $MCP_PID 2>/dev/null || true
    fi
    
    # Kill Streamlit if running
    if [ ! -z "$STREAMLIT_PID" ]; then
        echo -e "${YELLOW}   Stopping Streamlit (PID: $STREAMLIT_PID)...${NC}"
        kill $STREAMLIT_PID 2>/dev/null || true
        wait $STREAMLIT_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}All services stopped${NC}\n"
    exit 0
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start MCP Server in background
echo -e "${BLUE}Starting MCP Bond Server...${NC}"
cd tools
python3 bond_server.py > ../.cache/mcp_server.log 2>&1 &
MCP_PID=$!
cd ..

# Wait for MCP server to initialize (give it 5 seconds)
echo -e "${YELLOW}   Waiting for MCP server to initialize...${NC}"
sleep 5

# Check if MCP server is still running
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo -e "${RED}MCP server failed to start. Check .cache/mcp_server.log for details.${NC}"
    exit 1
fi

echo -e "${GREEN}   MCP server running (PID: $MCP_PID)${NC}"
echo -e "${GREEN}   MCP server logs: .cache/mcp_server.log${NC}\n"

# Start Streamlit app in foreground
echo -e "${BLUE}Starting Streamlit app...${NC}"
echo -e "${GREEN}   Streamlit will open at http://localhost:8501${NC}\n"

python3 run_streamlit.py &
STREAMLIT_PID=$!

# Wait for Streamlit to start
sleep 3

# Check if Streamlit is running
if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
    echo -e "${RED}Streamlit failed to start.${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All services are running!${NC}"
echo -e "${GREEN}========================================${NC}\n"
echo -e "${BLUE}MCP Server:${NC} http://localhost:8123 (PID: $MCP_PID)"
echo -e "${BLUE}Streamlit:${NC} http://localhost:8501 (PID: $STREAMLIT_PID)"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for Streamlit process (it will run in foreground)
wait $STREAMLIT_PID

