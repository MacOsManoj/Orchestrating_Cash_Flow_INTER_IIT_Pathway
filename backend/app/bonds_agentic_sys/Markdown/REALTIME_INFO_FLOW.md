# Real-Time Information Flow

## Overview

The system now automatically gathers real-time market information (web search + news) after query classification, processes it intelligently, and provides formatted context to the advisory agent for better recommendations.

## Architecture Flow

```
User Query
    ↓
Query Classification
    ↓
Real-Time Info Gathering (NEW)
    ├─→ Generate Intelligent Search Queries (LLM-powered)
    ├─→ Web Search (Parallel)
    └─→ News Scraping (Parallel)
    ↓
Real-Time Info Agent Processing
    ├─→ Analyze & Extract Insights
    ├─→ Format for Advisory Agent
    └─→ Highlight Urgent/Breaking News
    ↓
Advisory Agent
    ├─→ Decides Whether to Use Real-Time Info
    └─→ Incorporates into Recommendations
```

## Key Components

### 1. Real-Time Info Agent (`agents/realtime_info_agent.py`)

**Responsibilities:**
- **Query Generation**: Uses LLM to generate optimal search queries based on user query and intent
- **Result Processing**: Analyzes web search and news results to extract actionable insights
- **Formatting**: Creates concise, formatted context for the advisory agent

**Key Methods:**
- `generate_search_queries(query, intent)`: Generates intelligent web search query and news keywords
- `process_realtime_info(query, intent, web_search_result, news_result)`: Processes and formats results

### 2. Orchestrator Integration (`orchestrator_v3.py`)

**Flow:**
1. After query classification, `_gather_realtime_info` node is called
2. Real-time info agent generates optimal search queries
3. Web search and news scraping run in parallel using `asyncio.gather()`
4. Results are processed by real-time info agent
5. Formatted context is stored in `state["web_search_results"]`
6. Advisory agent receives formatted context (not raw results)

## Query Generation Intelligence

### Before (Simple Keyword Matching)
```python
if "rate" in intent:
    search_query = "Indian bond market interest rate outlook"
    news_keywords = ["RBI", "interest rate"]
```

### After (LLM-Powered)
```python
# Real-time info agent analyzes user query and intent
# Generates context-aware queries:
{
    "web_search_query": "best bonds to buy India RBI rate cut 50bps",
    "news_keywords": ["RBI rate cut", "bond investment", "fixed income"]
}
```

**Benefits:**
- More specific and relevant queries
- Better search results
- Context-aware keyword extraction
- Handles complex queries better

## Parallel Execution (No Bottlenecks)

```python
# Both searches run simultaneously
web_search_task = tools[WEB_SEARCH].search(query=web_search_query, num_results=5)
news_task = tools[NEWS_SCRAPER].scrape_news(keywords=news_keywords, max_articles=5)

# Wait for both to complete
web_search_result, news_result = await asyncio.gather(
    web_search_task,
    news_task,
    return_exceptions=True
)
```

**Performance:**
- Web search: ~2-3 seconds
- News scraping: ~1-2 seconds
- **Total time: ~2-3 seconds** (not 4-5 seconds sequential)

## Advisory Agent Integration

The advisory agent receives **formatted, processed context** instead of raw search results:

```python
# Advisory agent decides whether to use real-time info
realtime_context = self._should_use_realtime_info(
    classified_query, bond_analytics, bond_scores, portfolio, web_search_results
)

# Uses context in summary generation
summary = self._generate_summary(
    classified_query, recommendations, portfolio_changes, 
    conversation_history, realtime_context
)
```

**Decision Logic:**
- Uses real-time info if query contains keywords like: "current", "recent", "latest", "news", "market conditions"
- Uses if query is about market/economic factors
- Uses if limited bond data available and query is market-related
- Always uses if formatted context contains "REAL-TIME MARKET INTELLIGENCE"

## Example Flow

### Query: "What bonds should I buy if RBI cuts rates by 50bps?"

1. **Classification**: `buy_recommendation` intent detected
2. **Query Generation**:
   - Web search: "best bonds to buy India RBI rate cut 50bps"
   - News keywords: ["RBI rate cut", "bond investment", "fixed income"]
3. **Parallel Execution**:
   - Web search finds 4 relevant results
   - News scraping finds 4 articles
4. **Processing**:
   - Real-time info agent extracts:
     - Market implications of rate cuts
     - Current bond market sentiment
     - Recent RBI policy updates
   - Formats into concise context
5. **Advisory Agent**:
   - Receives formatted context
   - Decides to use it (query contains "if" and "RBI")
   - Incorporates into recommendations
   - Summary mentions: "In light of the recent 50 basis points rate cut by the RBI..."

## Benefits

1. **Intelligent Query Generation**: LLM-powered queries are more relevant than keyword matching
2. **No Bottlenecks**: Parallel execution reduces total time
3. **Better Context**: Processed, formatted context is more useful than raw results
4. **Smart Usage**: Advisory agent decides when real-time info is valuable
5. **Actionable Insights**: Real-time info agent extracts key insights, not just raw data

## Configuration

The real-time info agent uses:
- **Model**: `gpt-4o-mini` (fast, cost-effective)
- **Temperature**: `0.0` (deterministic, factual)
- **Max Results**: 5 web results, 5 news articles
- **Processing**: Concise 2-3 sentence summary + bullet points

## Testing

Run the test script:
```bash
python tests/test_realtime_info_flow.py
```

The test verifies:
- Query generation works correctly
- Parallel execution completes successfully
- Real-time info is processed and formatted
- Advisory agent receives and uses the context
- Recommendations are generated with real-time context

## Future Improvements

1. **Caching**: Cache search queries and results for similar queries
2. **Streaming**: Stream results as they come in (don't wait for all)
3. **Multi-Query**: Generate multiple search queries for better coverage
4. **Relevance Scoring**: Score and rank results before processing
5. **Entity Extraction**: Extract specific entities (companies, bonds) from results

