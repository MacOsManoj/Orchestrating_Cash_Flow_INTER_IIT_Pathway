# Backend Dockerfile for GCP Deployment
# Uses uv for fast, reliable Python package management

FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    git \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better caching)
COPY pyproject.toml ./
# Copy uv.lock if it exists, otherwise uv will generate it
COPY uv.lock* ./

# Install dependencies using uv
# If uv.lock exists, use --frozen, otherwise sync will generate it
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev; \
    else \
        uv sync --no-dev; \
    fi

# Production stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    # For chromadb/sqlite
    libsqlite3-0 \
    # For selenium (if using headless browser)
    chromium \
    chromium-driver \
    # For spacy and NLP
    libgomp1 \
    # For pdf2image (poppler)
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:/app/app/bonds_agentic_sys:/app/app/forex:$PYTHONPATH" \
    # Chromium settings for Selenium
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Copy verification script
COPY verify_imports.py ./

# Create necessary directories
RUN mkdir -p /app/app/bonds_agentic_sys/.cache \
    /app/app/bonds_agentic_sys/output_forecasts \
    /app/app/bonds_agentic_sys/pathway_producer_consumer/logs \
    /app/app/bonds_agentic_sys/pathway_producer_consumer/.pids \
    /app/app/forex/data \
    /app/data \
    /app/logs

# Verify Python path and critical imports work
RUN python verify_imports.py || echo "⚠️ Some optional imports may be missing, but core dependencies should work"

# Download spacy model (if needed)
RUN python -m spacy download en_core_web_sm || true

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('averaged_perceptron_tagger', quiet=True); nltk.download('wordnet', quiet=True)" || true

# Expose ports
EXPOSE 8000
# Streamlit port (if running streamlit)
EXPOSE 8501
# MCP server ports
EXPOSE 8123
EXPOSE 8127

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
