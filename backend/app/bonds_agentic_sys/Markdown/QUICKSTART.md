# Quick Start Guide - Orchestrator V3

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
cd bond-pipeline
pip install -r requirements.txt
```

**Note:** Make sure you have Python 3.8+ installed.

### Step 2: Set Environment Variables

Create a `.env` file in the `bond-pipeline` directory:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional (for web search)
SERPAPI_KEY=your-serpapi-key-here
```

Or export them:

```bash
export OPENAI_API_KEY="sk-your-key-here"
export SERPAPI_KEY="your-serpapi-key"  # Optional
```

### Step 3: Run the Application

**Option A: Streamlit UI (Recommended)**
```bash
streamlit run streamlit_app.py
```

Or use the helper script:
```bash
python run_streamlit.py
```

The app will open at `http://localhost:8501`

**Option B: Command Line Test**
```bash
python test_orchestrator_v3.py
```

---

## 📋 Detailed Setup

### Prerequisites

1. **Python 3.8+**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

2. **OpenAI API Key**
   - Get one from https://platform.openai.com/api-keys
   - Add to `.env` file or export as environment variable

3. **Optional: SerpAPI Key** (for web search)
   - Get one from https://serpapi.com/
   - Only needed if you want web search functionality

### Installation

```bash
# Navigate to project directory
cd bond-pipeline

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import langgraph; print('LangGraph installed successfully')"
```

### Verify Installation

Run a quick test:

```bash
python -c "
from orchestrator_v3 import create_orchestrator_v3
from schemas_v2 import SystemConfigV2
import os
from dotenv import load_dotenv
load_dotenv()

config = SystemConfigV2(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    llm_model='gpt-4o-mini'
)
orchestrator = create_orchestrator_v3(config)
print('✅ Orchestrator V3 initialized successfully!')
"
```

---

## 🎯 Running the Streamlit UI

### Basic Usage

```bash
streamlit run streamlit_app.py
```

### Features

- **Chat Interface**: ChatGPT-like interface for bond queries
- **Real-time Recommendations**: See bond recommendations as they're generated
- **Analytics Dashboard**: View bond analytics, scores, and portfolio info
- **Settings**: Configure LLM model, enable/disable RAG, set User ID

### Example Queries

Try these in the Streamlit UI:

1. `"Find high yield AAA bonds with good liquidity"`
2. `"Recommend bonds to reduce my portfolio duration"`
3. `"What are the best PSU bonds for my portfolio?"`
4. `"Explain why HDFC Bank bonds are recommended"`
5. `"Analyze my portfolio and suggest improvements"`

---

## 🧪 Testing the Orchestrator

### Test Script

Create `test_orchestrator_v3.py`:

```python
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from schemas_v2 import SystemConfigV2
from orchestrator_v3 import create_orchestrator_v3

async def test():
    # Configuration
    config = SystemConfigV2(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model="gpt-4o-mini",
        rag_enabled=False,
        cache_enabled=True
    )
    
    # Initialize
    print("Initializing orchestrator...")
    orchestrator = create_orchestrator_v3(config)
    
    # Test query
    query = "Find high yield AAA bonds"
    print(f"\nRunning query: {query}")
    
    result = await orchestrator.run_async(
        query=query,
        user_id="test_user"
    )
    
    # Display results
    print(f"\n✅ Complete!")
    print(f"Processing time: {result.processing_time:.2f}s")
    if result.advisory:
        print(f"Recommendations: {len(result.advisory.recommendations)}")
        for rec in result.advisory.recommendations[:3]:
            print(f"  - {rec.action}: {rec.name}")

if __name__ == "__main__":
    asyncio.run(test())
```

Run it:
```bash
python test_orchestrator_v3.py
```

---

## 🔧 Troubleshooting

### Issue: "OPENAI_API_KEY not set"

**Solution:**
```bash
# Check if .env file exists
ls -la .env

# Create .env file if missing
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Or export directly
export OPENAI_API_KEY="sk-your-key-here"
```

### Issue: "ModuleNotFoundError: No module named 'langgraph'"

**Solution:**
```bash
pip install langgraph>=0.0.20
# Or reinstall all dependencies
pip install -r requirements.txt
```

### Issue: "Failed to initialize orchestrator"

**Check:**
1. API key is valid and has credits
2. All dependencies are installed: `pip install -r requirements.txt`
3. Python version is 3.8+: `python --version`

### Issue: Streamlit app is slow

**Solutions:**
- Use `gpt-4o-mini` instead of `gpt-4-turbo-preview` (faster and cheaper)
- Disable RAG in sidebar if not needed
- Check your internet connection

---

## 📊 Understanding the Output

### Execution Path

The orchestrator logs its execution path:
```
validate_query -> classify_query -> plan_execution -> execute_tools -> 
run_ml_model -> run_analyst -> run_scoring -> run_advisory -> finalize
```

### Conditional Execution

- **Portfolio Check**: Only runs if query mentions portfolio
- **ML Model**: Only runs if in execution plan
- **Explainability**: Only runs if user asks "explain" or "why"

### Results Structure

```python
result = await orchestrator.run_async(query="...", user_id="...")

# Access results
result.advisory.recommendations  # List of TradeRecommendation
result.bond_analytics            # Dict of BondAnalytics
result.bond_scores               # Dict of BondScore
result.execution_plan            # ExecutionPlan with reasoning
result.processing_time           # Time taken in seconds
```

---

## 🎓 Next Steps

1. **Explore the UI**: Try different queries in Streamlit
2. **Read Documentation**: Check `ORCHESTRATOR_V3_README.md` for architecture details
3. **Customize**: Modify agent weights in config
4. **Extend**: Add new agents or tools to the graph

---

## 📚 Additional Resources

- **Architecture**: See `ORCHESTRATOR_V3_README.md`
- **Streamlit Guide**: See `STREAMLIT_README.md`
- **API Reference**: Check `schemas_v2.py` for data structures

---

## 💡 Tips

1. **Start Simple**: Use `gpt-4o-mini` for faster responses
2. **Enable RAG**: Only if you need RBI policy context
3. **Check Logs**: The orchestrator prints detailed execution logs
4. **Cache**: Results are cached to speed up repeated queries

---

## 🆘 Need Help?

1. Check the logs in the terminal/console
2. Verify your API keys are set correctly
3. Ensure all dependencies are installed
4. Check Python version (3.8+)

Happy trading! 📈

