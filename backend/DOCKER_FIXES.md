# Docker & UV Setup Fixes

## Issues Fixed

### 1. UV Package Installation
- **Problem**: `uv sync --frozen` was failing if `uv.lock` didn't exist or was outdated
- **Fix**: Dockerfile now handles both cases:
  - If `uv.lock` exists → uses `--frozen` for reproducible builds
  - If `uv.lock` missing → generates it automatically with `uv sync`

### 2. Python Path Configuration
- **Problem**: `bonds_agentic_sys` imports like `from utils.mcp_client` weren't working
- **Fix**: 
  - Set `PYTHONPATH=/app:/app/app/bonds_agentic_sys:/app/app/forex` in all services
  - Added `PATH=/app/.venv/bin:$PATH` to ensure `python` command uses venv

### 3. Python Command Consistency
- **Problem**: Mixed use of `python` vs `python3` causing issues
- **Fix**: All services now use `python` (from venv) instead of `python3`

### 4. Import Verification
- **Problem**: No way to verify imports work before services start
- **Fix**: Added `verify_imports.py` script that checks critical imports during Docker build

### 5. Missing System Dependencies
- **Problem**: Some packages need system libraries
- **Fix**: Added `poppler-utils` for `pdf2image` package

## Key Changes

### Dockerfile
```dockerfile
# Handles uv.lock existence
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev; \
    else \
        uv sync --no-dev; \
    fi

# Proper PYTHONPATH
ENV PYTHONPATH="/app:/app/app/bonds_agentic_sys:/app/app/forex:$PYTHONPATH"

# Import verification
RUN python verify_imports.py
```

### docker-compose.yml (All Services)
```yaml
environment:
  - PYTHONPATH=/app:/app/app/bonds_agentic_sys:/app/app/forex
  - PATH=/app/.venv/bin:$PATH
```

### Commands
- Changed `python3` → `python` (uses venv Python)
- All services use venv Python for consistency

## Verification

After building, verify imports work:

```bash
# Build image
docker build -t backend-test .

# Test imports
docker run --rm backend-test python verify_imports.py
```

Expected output:
```
✅ chromadb
✅ pathway
✅ langchain
✅ langgraph
✅ bonds_agentic_sys.utils.mcp_client
✅ bonds_agentic_sys.utils.logger
✅ bonds_agentic_sys.schemas_v2
✅ bonds_agentic_sys.orchestrator_v3
✅ All critical imports verified!
```

## Deployment

### Local Testing
```bash
cd backend
docker-compose up --build
```

### GCP Cloud Build
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/backend
```

### GCP Cloud Run
```bash
gcloud run deploy backend \
  --image gcr.io/PROJECT_ID/backend \
  --set-env-vars="PYTHONPATH=/app:/app/app/bonds_agentic_sys:/app/app/forex"
```

## Troubleshooting

### "Module not found: utils"
- Check `PYTHONPATH` includes `/app/app/bonds_agentic_sys`
- Verify `PATH` includes `/app/.venv/bin`

### "uv: command not found"
- Dockerfile copies uv from official image
- If issue persists, check builder stage completed

### "Import errors during build"
- Check `verify_imports.py` output
- Ensure all dependencies in `pyproject.toml`
- Run `uv sync` locally to update `uv.lock`

### "Python path not working"
- Verify `PYTHONPATH` env var is set in docker-compose
- Check service logs: `docker-compose logs <service>`
- Test manually: `docker-compose exec <service> python -c "import sys; print(sys.path)"`

