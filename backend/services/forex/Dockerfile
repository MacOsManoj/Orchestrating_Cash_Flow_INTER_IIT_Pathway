FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_server.py .
COPY data/ ./data/ 2>/dev/null || true

# Create directories
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose MCP server port
EXPOSE 8127

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c 'import requests; requests.get("http://localhost:8127/mcp/", timeout=5)' || exit 1

# Run the MCP server
CMD ["python", "-u", "mcp_server.py"]
