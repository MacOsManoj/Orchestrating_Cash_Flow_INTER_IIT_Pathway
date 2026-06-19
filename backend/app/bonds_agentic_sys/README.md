# Agent Bond 007

> **Production-Grade Multi-Agent Bond Trading Advisory System**

An AI-powered bond trading assistant that combines intelligent planning, real-time data analysis, ML-based forecasting, and natural language understanding to provide actionable bond recommendations.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Quick Start

**Important:** The bond forecasting pipeline must be running before starting the Streamlit UI.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup conda environment (if not already done)
conda create -n pathway python=3.11
conda activate pathway
pip install pathway fastmcp

# 3. Configure environment variables
# Create .env file with OPENAI_API_KEY

# 4. Start bond pipeline (REQUIRED FIRST)
cd pathway_producer_consumer
bash run_bond_pipeline.sh
# Wait for all 4 components to start (especially Bond Server Manager)

# 5. In a new terminal, start Streamlit UI
cd ..  # Back to bond-pipeline directory
python run_streamlit.py
```

See [Running the Application](#running-the-application) section for detailed instructions.

---

## Architecture

<p align="center">
  <img src="images/Agent Bond.png" alt="Agent Bond Architecture" width="800"/>
</p>

---

## Prerequisites

- **Python 3.11+**
- **Conda** (recommended) - For managing the `pathway` environment
- **OpenAI API key** (required) - [Get one here](https://platform.openai.com/api-keys)
- **SerpAPI key** (optional) - [Get one here](https://serpapi.com/)
- **Groq API key** (optional) - [Get one here](https://console.groq.com/)
- **Pathway License Key** - Required for Pathway library (get from [Pathway](https://pathway.com/))

### Conda Environment Setup (Recommended)

The bond forecasting pipeline requires a conda environment named `pathway`:

```bash
# Create conda environment
conda create -n pathway python=3.11
conda activate pathway

# Install Pathway (requires license key)
pip install pathway

# Install other dependencies
pip install -r requirements.txt
```

**Note:** The `run_bond_pipeline.sh` script automatically activates the `pathway` conda environment.

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/xoxo121/Agent-Bond.git
cd Agent-Bond
```

### 2. Setup Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Package

```bash
# Install with all dependencies
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt

# Or with optional dependencies
pip install -e ".[dev]"
```

**Note:** The following dependencies are required for the bond forecasting pipeline:
- `pathway>=0.8.0` - For real-time bond forecasting
- `fastmcp>=0.1.0` - For MCP server-client communication
- `scipy>=1.11.0` - For yield curve optimization
- `python-dateutil>=2.8.0` - For bond maturity calculations

### 4. Configure Environment

Create `.env` file in project root:

```env
OPENAI_API_KEY=sk-your-key-here
SERPAPI_KEY=your-serpapi-key  # Optional
GROQ_API_KEY=your-groq-key    # Optional
```

---

## Running the Application

### Important: Start Bond Pipeline First

**Before running the Streamlit UI, you must start the bond forecasting pipeline** to ensure the MCP server is running and bond data is available.

#### Step 1: Start Bond Pipeline (Required)

The bond pipeline consists of 4 components that must be running:

1. **Historical Quotes Scraper** - Fetches historical bond data
2. **NSE GSEC Scheduler** - Fetches current bond quotes from NSE
3. **Pathway Producer** - Generates yield forecasts using Pathway
4. **Bond Server Manager** - Runs the MCP server on port 8123

**On macOS:**

```bash
cd pathway_producer_consumer
bash run_bond_pipeline.sh
```

This will launch all 4 components in separate Terminal windows. Wait for the Bond Server Manager to start (it waits 60 seconds for other components to initialize).

**On Linux/Windows:**

You'll need to start each component manually in separate terminals:

```bash
cd pathway_producer_consumer

# Terminal 1: Historical Quotes Scraper
python historical_quotes_scarper.py

# Terminal 2: NSE GSEC Scheduler
python nse_gsec_script.py --schedule

# Terminal 3: Pathway Producer
python pathway_producer_new.py

# Terminal 4: Bond Server Manager (wait 60s after starting others)
python bond_server_manager.py
```

**Verify Pipeline is Running:**

```bash
# Check if MCP server is running on port 8123
lsof -i :8123  # macOS/Linux
# or
netstat -ano | findstr :8123  # Windows

# Test MCP server connection
curl http://localhost:8123/mcp
# Should return JSON-RPC response (not connection error)
```

#### Step 2: Run Streamlit UI

**Only after the bond pipeline is running**, start the Streamlit UI:

```bash
python run_streamlit.py
```

App will open at `http://localhost:8501`

**Note:** The Streamlit app requires the MCP server (from Step 1) to be running. If you see connection errors, ensure the bond pipeline is started first.

### CLI Pipeline Test

```bash
python run_pipeline.py
```

**Note:** This also requires the bond pipeline to be running.

---

## Verification

Quick check that everything works:

```bash
# Test imports
python -c "from orchestrator_v3 import create_orchestrator_v3; print('OK')"

# Test API key
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key loaded' if os.getenv('OPENAI_API_KEY') else 'Missing API key')"
```

---

## Package Structure

```
agent-bond/
├── agents/     # Agent modules
├── tools/       # Tool modules
├── rag/         # RAG system
├── models/      # ML models
├── config/      # Configuration
└── utils/       # Utilities
```

**Import example:**
```python
from orchestrator_v3 import create_orchestrator_v3
from agents.planner import create_planner_agent
from tools.tools_manager import create_news_scraper
```

---

## Troubleshooting

### Installation Issues

**Module not found**
```bash
pip install -e .
# or
pip install -r requirements.txt
```

**Pathway not found**
- Ensure you're in the `pathway` conda environment: `conda activate pathway`
- Install Pathway: `pip install pathway`
- Verify Pathway license key is set (check Pathway documentation)

**fastmcp not found**
```bash
pip install fastmcp>=0.1.0
```

### Configuration Issues

**API key not found**
- Verify `.env` file exists in project root
- Check format: `OPENAI_API_KEY=sk-...` (no quotes, no spaces)
- Restart terminal/IDE after creating `.env`

**MCP server connection errors**
- Ensure bond pipeline is running: `bash pathway_producer_consumer/run_bond_pipeline.sh`
- Check if MCP server is listening: `lsof -i :8123`
- Wait 60+ seconds after starting pipeline for server to initialize
- Check bond_server_manager.py logs in `pathway_producer_consumer/logs/`

**Port conflicts**

Port 8501 (Streamlit) in use:
```bash
# macOS/Linux
lsof -ti:8501 | xargs kill -9

# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Or use different port
streamlit run streamlit_app.py --server.port 8502
```

Port 8123 (MCP Server) in use:
```bash
# macOS/Linux
lsof -ti:8123 | xargs kill -9

# Windows
netstat -ano | findstr :8123
taskkill /PID <PID> /F
```

### Pipeline Issues

**Bond pipeline not starting**
- Verify conda environment `pathway` exists: `conda env list`
- Check that all scripts exist in `pathway_producer_consumer/`:
  - `historical_quotes_scarper.py`
  - `nse_gsec_script.py`
  - `pathway_producer_new.py`
  - `bond_server_manager.py`
- Check logs in `pathway_producer_consumer/logs/`

**No bonds available**
- Ensure `data/bonds_data.csv` exists
- Check that NSE GSEC script is fetching data
- Verify Pathway Producer is generating forecasts
- Check `output_forecasts/final_forecasts.csv` exists

---

## Example Queries

| Type | Example |
|------|---------|
| Buy Recommendations | "What bonds should I buy now?" |
| Risk Analysis | "Analyze my portfolio duration risk" |
| Sector Focus | "Find AAA corporate bonds in financial sector" |
| Strategy | "Create a barbell strategy with short and long duration" |
| Market Context | "Recommend bonds given RBI's hawkish stance" |
| Explainability | "Why is HDFC bond recommended?" |
| Portfolio | "Show my portfolio status and metrics" |

---

## Configuration

Configuration is done via `SystemConfigV2` in `schemas_v2.py`:

```python
class SystemConfigV2(BaseModel):
    openai_api_key: str
    serpapi_key: Optional[str] = None
    rag_enabled: bool = True
    cache_enabled: bool = True
    llm_model: str = "gpt-4-turbo-preview"
    # ... more options
```

---

## Testing

```bash
# Run tests
python -m pytest tests/ -v

# Test pipeline
python run_pipeline.py
```

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---
<p align="center">
  <b>Built with love for the Indian Bond Market</b>
</p>
