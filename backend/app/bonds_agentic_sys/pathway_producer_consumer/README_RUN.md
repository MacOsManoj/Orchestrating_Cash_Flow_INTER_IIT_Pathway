# How to Run bond_server.py

## The Problem
When running `uv run bond_server.py` from the `pathway_producer_consumer` directory, uv looks for a project in that directory and uses a different virtual environment that doesn't have `pathway` installed.

## Solutions

### Option 1: Run from Backend Directory (Recommended)
```bash
cd /home/nishanth/code/upgraded-octo-spork/backend
uv run python app/bonds_agentic_sys/pathway_producer_consumer/bond_server.py
```

### Option 2: Use the Wrapper Script
```bash
cd /home/nishanth/code/upgraded-octo-spork/backend/app/bonds_agentic_sys/pathway_producer_consumer
./run_bond_server.sh
```

### Option 3: Use Active Venv
```bash
cd /home/nishanth/code/upgraded-octo-spork/backend/app/bonds_agentic_sys/pathway_producer_consumer
uv run --active python bond_server.py
```

### Option 4: Activate Venv Manually
```bash
cd /home/nishanth/code/upgraded-octo-spork/backend
source .venv/bin/activate
cd app/bonds_agentic_sys/pathway_producer_consumer
python bond_server.py
```

## Why This Happens
- `pathway` is installed in `/home/nishanth/code/upgraded-octo-spork/backend/.venv`
- When you run `uv run` from a subdirectory, uv looks for `pyproject.toml` in that directory
- If it finds one (or doesn't find the parent one), it uses a different environment

## Quick Fix for Docker
In Docker, this is already handled - all services run from `/app` (backend directory) with the correct PYTHONPATH set.

