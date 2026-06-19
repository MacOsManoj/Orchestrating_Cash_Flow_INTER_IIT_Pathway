# Newspaper4K Tool & Real-Time Info Agent Tests

This directory contains test scripts for the Newspaper4K news scraper tool and its integration with the Real-Time Info Agent.

## Test Scripts

### 1. `test_np4k_quick.py` - Quick Tool Test
Simple test to verify the Newspaper4K tool works correctly.

**Usage:**
```bash
python tests/test_np4k_quick.py
```

**What it tests:**
- Direct Newspaper4K tool functionality
- Basic news scraping with a simple query
- Article retrieval and formatting

### 2. `test_np4k_realtime_agent.py` - Comprehensive Integration Test
Full test suite that tests both the tool and agent integration.

**Usage:**
```bash
python tests/test_np4k_realtime_agent.py
```

**What it tests:**
1. **Direct Tool Test**: Tests Newspaper4K tool directly with multiple queries
2. **Agent Fetch News**: Tests the real-time info agent's `fetch_news_direct()` method
3. **Full Flow Test**: Tests the complete real-time info agent workflow:
   - Decision making (should gather real-time info?)
   - Query generation
   - News fetching using Newspaper4K
   - Result processing and formatting

## Prerequisites

1. **Environment Variables:**
   - `OPENAI_API_KEY` - Required for real-time info agent tests
   - NewsData API keys are hardcoded in `tools/np4kvesion.py`

2. **Dependencies:**
   - `newsdataapi` - For NewsData API client
   - `newspaper` - For article scraping
   - `langchain-openai` - For real-time info agent
   - `python-dotenv` - For environment variable loading

## Expected Output

### Quick Test Output:
```
Testing Newspaper4K tool...
============================================================
Query: RBI interest rate India
────────────────────────────────────────────────────────────

✓ Success!
  Time: 2.45s
  Articles: 3

📰 Articles found:

  Article #1:
    Source: Economic Times
    URL: https://...
    Word Count: 450
    Preview: The Reserve Bank of India...
```

### Comprehensive Test Output:
The comprehensive test will show:
- Section headers for each test
- Detailed article information
- Processing times
- Formatted context output from the agent

## Troubleshooting

### Import Errors
If you see import errors, make sure:
- You're running from the project root directory
- All dependencies are installed: `pip install -r requirements.txt`
- The `tools/np4kvesion.py` file exists

### API Errors
If you see API errors:
- Check that the NewsData API keys in `tools/np4kvesion.py` are valid
- Verify your internet connection
- Some API keys may have rate limits

### No Articles Returned
If no articles are returned:
- Try a different query
- Check if the query is too specific or too broad
- Verify the API keys are working

## Integration with Real-Time Info Agent

The Newspaper4K tool is integrated into the Real-Time Info Agent in two ways:

1. **Direct Method**: `fetch_news_direct()` - Called directly by the agent when needed
2. **Tool Method**: Via `NewsScraperTool` - Used by the orchestrator

The agent will automatically use the Newspaper4K scraper when:
- `use_direct_news=True` (default)
- The standard news tool result is not available
- Real-time information is needed for the query

## Performance

The Newspaper4K tool is optimized for speed:
- **Parallel API calls**: Uses 3 API keys simultaneously
- **Threaded scraping**: 20 threads for article scraping
- **Deduplication**: Removes duplicate URLs
- **Fast filtering**: Only returns valid articles with sufficient content

Typical performance:
- **API calls**: ~1-2 seconds
- **Article scraping**: ~2-5 seconds per article (parallel)
- **Total time**: ~3-8 seconds for 5 articles

