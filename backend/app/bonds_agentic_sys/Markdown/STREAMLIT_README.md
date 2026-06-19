# Streamlit UI for Agent Bond

A ChatGPT-like interface for the autonomous bond trading application.

## Features

- 🎨 **ChatGPT-like Interface**: Clean, modern chat interface
- 💼 **Bond Recommendations**: Display trade recommendations with detailed analysis
- 📊 **Analytics Dashboard**: View bond analytics, scores, and metrics
- 💰 **Portfolio Management**: View and manage your bond portfolio
- ⚡ **Real-time Processing**: See execution plans and processing statistics
- 🎯 **Smart Responses**: Context-aware responses based on your queries

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the `bond-pipeline` directory:

```bash
OPENAI_API_KEY=your_openai_api_key_here
SERPAPI_KEY=your_serpapi_key_here  # Optional
```

### 3. Run the Streamlit App

```bash
streamlit run streamlit_app.py
```

Or use the provided script:

```bash
python run_streamlit.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. **Enter your query** in the chat input at the bottom
2. **View recommendations** - The AI will provide bond trading recommendations
3. **Explore analytics** - Click on expandable sections to see detailed analytics
4. **Check your portfolio** - View your current holdings and portfolio metrics
5. **Review execution plan** - See what tools and agents were used

## Example Queries

- "Find high yield AAA bonds with good liquidity"
- "Recommend bonds to reduce my portfolio duration"
- "What are the best PSU bonds for my portfolio?"
- "Show me bonds with high expected returns"
- "Analyze my portfolio and suggest improvements"

## Settings

Use the sidebar to:
- Change LLM model (gpt-4o-mini, gpt-4-turbo-preview, gpt-4)
- Enable/disable RAG system
- Set your User ID
- Clear chat history

## Features in Detail

### Recommendations Display
- Color-coded cards (Green for BUY, Red for SELL, Orange for HOLD)
- Expected returns and confidence scores
- Risk assessments
- Detailed rationale for each recommendation

### Analytics Table
- Current vs Fair Value
- YTM and Duration metrics
- Credit ratings
- ML signals and confidence

### Portfolio View
- Total portfolio value
- Cash position
- Portfolio duration and YTM
- Individual holdings with P&L

### Processing Stats
- Execution time
- Tool calls and cache hits
- Performance metrics

## Troubleshooting

### "OPENAI_API_KEY not set"
- Make sure you have a `.env` file with your OpenAI API key
- The key should start with `sk-`

### "Failed to initialize orchestrator"
- Check that all dependencies are installed
- Verify your API keys are correct
- Check the console for detailed error messages

### App is slow
- Try using `gpt-4o-mini` instead of `gpt-4-turbo-preview`
- Disable RAG if not needed
- Check your internet connection for API calls

## Architecture

The Streamlit app:
1. Initializes the orchestrator (cached for performance)
2. Handles user queries through the chat interface
3. Displays results in an organized, expandable format
4. Maintains chat history in session state

## Next Steps

- Add authentication
- Persist chat history
- Add export functionality for recommendations
- Integrate with real trading APIs
- Add more visualizations (charts, graphs)

