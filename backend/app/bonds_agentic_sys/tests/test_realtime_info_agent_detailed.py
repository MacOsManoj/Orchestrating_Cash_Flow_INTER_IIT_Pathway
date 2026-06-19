"""
Test script for Real-Time Info Agent with detailed output
Tests the complete flow: decision -> query generation -> tool execution -> processing
Prints all outputs including full article details and measures execution time
"""

import asyncio
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agents.realtime_info_agent import create_realtime_info_agent
from tools.tools_manager import create_web_search, create_news_scraper
from schemas_v2 import NewsArticle, ToolResult
from utils.agent_logger import AgentLogger


def print_section(title: str, char: str = "="):
    """Print a formatted section header"""
    print(f"\n{char * 80}")
    print(f"{title}")
    print(f"{char * 80}\n")


def print_web_search_results(web_search_result: ToolResult):
    """Print detailed web search results"""
    print_section("WEB SEARCH RESULTS", "=")

    if not web_search_result:
        print(" No web search result provided")
        return

    print(f"Success: {web_search_result.success}")
    print(f"Cached: {web_search_result.cached}")
    if web_search_result.error:
        print(f"Error: {web_search_result.error}")

    if web_search_result.success and web_search_result.data:
        print(f"\nTotal Results: {len(web_search_result.data)}")
        print("\n" + "-" * 80)

        for idx, item in enumerate(web_search_result.data, 1):
            print(f"\n[Result {idx}]")
            print(f"Title: {item.get('title', 'N/A')}")
            print(f"Snippet: {item.get('snippet', 'N/A')}")
            print(f"URL: {item.get('url', 'N/A')}")
            if "source" in item:
                print(f"Source: {item.get('source', 'N/A')}")
            if "date" in item:
                print(f"Date: {item.get('date', 'N/A')}")
    else:
        print("No web search data available")


def print_news_articles(news_result: ToolResult):
    """Print detailed news articles with all information"""
    print_section("NEWS ARTICLES", "=")

    if not news_result:
        print(" No news result provided")
        return

    print(f"Success: {news_result.success}")
    print(f"Cached: {news_result.cached}")
    if news_result.error:
        print(f"Error: {news_result.error}")

    if news_result.success and news_result.data:
        print(f"\nTotal Articles: {len(news_result.data)}")
        print("\n" + "-" * 80)

        for idx, article in enumerate(news_result.data, 1):
            print(f"\n[Article {idx}]")
            print("-" * 80)

            # Handle both NewsArticle object and dict
            if isinstance(article, NewsArticle):
                print(f"Title: {article.title}")
                print(f"Source: {article.source}")
                print(f"URL: {article.url}")

                if article.published_at:
                    print(
                        f"Published At: {article.published_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                else:
                    print(f"Published At: Unknown")

                print(f"Scraped At: {article.scraped_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Sentiment Score: {article.sentiment_score:+.3f}")
                print(
                    f"Sentiment Label: {'Positive' if article.sentiment_score > 0.1 else 'Negative' if article.sentiment_score < -0.1 else 'Neutral'}"
                )
                print(f"Relevance Score: {article.relevance_score:.3f}")

                if article.summary:
                    print(f"\nSummary:")
                    print(f"  {article.summary}")

                if article.content:
                    # Show full content, not just preview
                    print(f"\nFull Content ({len(article.content)} characters):")
                    print(f"  {article.content}")

                if article.entities:
                    print(f"\nEntities ({len(article.entities)}):")
                    print(f"  {', '.join(article.entities)}")
                else:
                    print(f"\nEntities: None")

                # Show all other attributes
                if hasattr(article, "embedding") and article.embedding:
                    print(
                        f"\nEmbedding: Available ({len(article.embedding)} dimensions)"
                    )

                if hasattr(article, "doc_id") and article.doc_id:
                    print(f"Doc ID: {article.doc_id}")

                # Try to access raw data if available (for aspects, etc.)
                if hasattr(article, "__dict__"):
                    other_attrs = {
                        k: v
                        for k, v in article.__dict__.items()
                        if k
                        not in [
                            "title",
                            "url",
                            "source",
                            "content",
                            "summary",
                            "sentiment_score",
                            "relevance_score",
                            "entities",
                            "published_at",
                            "scraped_at",
                            "embedding",
                            "doc_id",
                        ]
                    }
                    if other_attrs:
                        print(f"\nAdditional Attributes:")
                        for k, v in other_attrs.items():
                            if v:
                                print(f"  {k}: {v}")

            elif isinstance(article, dict):
                # Handle dict format - show ALL fields
                print(f"Title: {article.get('title', 'N/A')}")
                print(
                    f"Source: {article.get('source', article.get('source_name', 'N/A'))}"
                )
                print(f"URL: {article.get('url', article.get('link', 'N/A'))}")

                published = article.get(
                    "published_at", article.get("published_date", "Unknown")
                )
                if published:
                    if isinstance(published, str):
                        print(f"Published: {published}")
                    else:
                        print(f"Published: {published}")
                else:
                    print(f"Published: Unknown")

                sentiment = article.get(
                    "sentiment_score", article.get("sentiment_polarity", 0.0)
                )
                print(f"Sentiment Score: {sentiment:+.3f}")
                print(
                    f"Sentiment Label: {'Positive' if sentiment > 0.1 else 'Negative' if sentiment < -0.1 else 'Neutral'}"
                )

                if "sentiment_subjectivity" in article:
                    print(
                        f"Sentiment Subjectivity: {article['sentiment_subjectivity']:.3f}"
                    )

                if "relevance_score" in article:
                    print(f"Relevance Score: {article['relevance_score']:.3f}")

                summary = article.get("summary", "")
                content = article.get("content", article.get("full_text", ""))

                if summary:
                    print(f"\nSummary ({len(summary)} characters):")
                    print(f"  {summary}")

                if content:
                    print(f"\nFull Content ({len(content)} characters):")
                    print(f"  {content}")

                if "keywords" in article and article["keywords"]:
                    keywords = article["keywords"]
                    if isinstance(keywords, str):
                        keywords = [k.strip() for k in keywords.split(",")]
                    print(f"\nKeywords ({len(keywords)}):")
                    print(f"  {', '.join(keywords)}")

                if "entities" in article and article["entities"]:
                    entities = article["entities"]
                    if isinstance(entities, str):
                        entities = [e.strip() for e in entities.split(",")]
                    print(f"\nEntities ({len(entities)}):")
                    print(f"  {', '.join(entities)}")

                # Show aspects if available
                if "aspects_sentiment" in article and article["aspects_sentiment"]:
                    try:
                        aspects_data = article["aspects_sentiment"]
                        if isinstance(aspects_data, str):
                            aspects_data = json.loads(aspects_data)

                        if aspects_data:
                            print(f"\nAspects Sentiment ({len(aspects_data)} aspects):")
                            for aspect_item in aspects_data:
                                if isinstance(aspect_item, dict):
                                    aspect_name = aspect_item.get("aspect", "Unknown")
                                    aspect_sentiment = aspect_item.get("sentiment", 0.0)
                                    print(f"  - {aspect_name}: {aspect_sentiment:+.3f}")
                                else:
                                    print(f"  - {aspect_item}")
                    except Exception as e:
                        print(f"\nAspects (parse error): {e}")

                if "word_count" in article:
                    print(f"\nWord Count: {article['word_count']}")

                if "search_level" in article:
                    print(f"Search Level: {article['search_level']}")

                if "scrape_success" in article:
                    print(f"Scrape Success: {article['scrape_success']}")

                # Show all other fields
                known_fields = {
                    "title",
                    "source",
                    "source_name",
                    "url",
                    "link",
                    "published_at",
                    "published_date",
                    "sentiment_score",
                    "sentiment_polarity",
                    "sentiment_subjectivity",
                    "relevance_score",
                    "summary",
                    "content",
                    "full_text",
                    "keywords",
                    "entities",
                    "aspects_sentiment",
                    "word_count",
                    "search_level",
                    "scrape_success",
                }
                other_fields = {
                    k: v for k, v in article.items() if k not in known_fields and v
                }
                if other_fields:
                    print(f"\nAdditional Fields:")
                    for k, v in other_fields.items():
                        if isinstance(v, (str, int, float, bool)):
                            print(f"  {k}: {v}")
                        elif isinstance(v, list) and len(v) < 10:
                            print(f"  {k}: {v}")
                        else:
                            print(f"  {k}: {type(v).__name__} (not displayed)")
            else:
                print(f"Unknown article format: {type(article)}")
                print(f"Article data: {json.dumps(article, default=str, indent=2)}")
    else:
        print("No news articles available")


def print_formatted_context(formatted_context: str):
    """Print the formatted context from real-time info agent"""
    print_section("FORMATTED CONTEXT (Final Output)", "=")
    if formatted_context:
        print(formatted_context)
    else:
        print(" No formatted context generated")


async def test_realtime_info_agent():
    """Test the real-time info agent with detailed output"""

    print_section("REAL-TIME INFO AGENT TEST", "=")

    # Test query
    test_query = "What bonds should I buy if RBI cuts rates by 50bps?"
    test_intent = "buy_recommendation"

    print(f"Test Query: {test_query}")
    print(f"Test Intent: {test_intent}")

    # Initialize components
    print_section("INITIALIZING COMPONENTS", "-")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(" OPENAI_API_KEY not set")
        return

    # Initialize real-time info agent
    start_init = time.time()
    realtime_agent = create_realtime_info_agent(
        api_key=api_key, model="gpt-4o-mini", fast_model="gpt-4o-mini"
    )
    init_time = time.time() - start_init
    print(f" Real-time info agent initialized ({init_time:.2f}s)")

    # Initialize tools
    web_search_tool = create_web_search(api_key=os.getenv("SERPAPI_KEY"))
    news_scraper_tool = create_news_scraper(
        cache_dir="files-mock/analytics", newsdata_api_key=os.getenv("NEWSDATA_API_KEY")
    )
    print(f" Tools initialized")

    # Step 1: Decision - Should we gather real-time info?
    print_section("STEP 1: DECISION - Should gather real-time info?", "-")
    start_decision = time.time()
    decision = await realtime_agent.should_gather_realtime_info(
        query=test_query, intent=test_intent
    )
    decision_time = time.time() - start_decision

    print(f"Decision Time: {decision_time:.2f}s")
    print(f"Needs Real-time Info: {decision.get('needs_realtime_info', False)}")
    print(f"Reasoning: {decision.get('reasoning', 'N/A')}")
    print(f"Priority: {decision.get('priority', 'N/A')}")

    if not decision.get("needs_realtime_info", False):
        print("\n  Decision: Skip real-time info gathering")
        return

    # Step 2: Generate search queries
    print_section("STEP 2: QUERY GENERATION", "-")
    start_query_gen = time.time()
    search_queries = await realtime_agent.generate_search_queries(
        query=test_query, intent=test_intent
    )
    query_gen_time = time.time() - start_query_gen

    print(f"Query Generation Time: {query_gen_time:.2f}s")
    print(f"Web Search Query: {search_queries.get('web_search_query', 'N/A')}")
    print(f"News Keywords: {search_queries.get('news_keywords', [])}")

    web_search_query = search_queries.get("web_search_query", test_query)
    news_keywords = search_queries.get("news_keywords", [test_query])

    # Step 3: Execute tools in parallel
    print_section("STEP 3: TOOL EXECUTION (Parallel)", "-")
    start_tools = time.time()

    web_search_task = web_search_tool.search(query=web_search_query, num_results=5)

    news_task = news_scraper_tool.scrape_news(
        keywords=news_keywords, max_articles=10, hours_back=24
    )

    # Execute in parallel
    web_search_result, news_result = await asyncio.gather(
        web_search_task, news_task, return_exceptions=True
    )

    tools_time = time.time() - start_tools

    # Handle exceptions
    if isinstance(web_search_result, Exception):
        print(f" Web search error: {web_search_result}")
        web_search_result = None
    else:
        print(f" Web search completed")

    if isinstance(news_result, Exception):
        print(f" News scraping error: {news_result}")
        news_result = None
    else:
        print(f" News scraping completed")

    print(f"\nTotal Tool Execution Time: {tools_time:.2f}s")

    # Print detailed results
    print_web_search_results(
        web_search_result if not isinstance(web_search_result, Exception) else None
    )
    print_news_articles(news_result if not isinstance(news_result, Exception) else None)

    # Step 4: Process results
    print_section("STEP 4: PROCESSING RESULTS", "-")
    start_processing = time.time()

    formatted_context = await realtime_agent.process_realtime_info(
        query=test_query,
        intent=test_intent,
        web_search_result=web_search_result
        if not isinstance(web_search_result, Exception)
        else None,
        news_result=news_result if not isinstance(news_result, Exception) else None,
    )

    processing_time = time.time() - start_processing
    print(f"Processing Time: {processing_time:.2f}s")

    # Print formatted context
    print_formatted_context(formatted_context)

    # Data Summary
    print_section("DATA SUMMARY", "=")
    web_count = (
        len(web_search_result.data)
        if web_search_result and web_search_result.success and web_search_result.data
        else 0
    )
    news_count = (
        len(news_result.data)
        if news_result and news_result.success and news_result.data
        else 0
    )

    print(f"Web Search Results: {web_count}")
    print(f"News Articles: {news_count}")
    print(f"Formatted Context Generated: {'Yes' if formatted_context else 'No'}")
    if formatted_context:
        print(f"Formatted Context Length: {len(formatted_context)} characters")

    # Calculate total information extracted
    total_web_chars = 0
    if web_search_result and web_search_result.success and web_search_result.data:
        for item in web_search_result.data:
            total_web_chars += len(item.get("title", "")) + len(item.get("snippet", ""))

    total_news_chars = 0
    total_entities = 0
    if news_result and news_result.success and news_result.data:
        for article in news_result.data:
            if isinstance(article, NewsArticle):
                if article.content:
                    total_news_chars += len(article.content)
                total_entities += len(article.entities)
            elif isinstance(article, dict):
                content = article.get("content", article.get("full_text", ""))
                if content:
                    total_news_chars += len(content)
                entities = article.get("entities", [])
                if isinstance(entities, list):
                    total_entities += len(entities)
                elif isinstance(entities, str):
                    total_entities += len(entities.split(","))

    print(f"\nInformation Extracted:")
    print(f"  - Web Search Text: {total_web_chars:,} characters")
    print(f"  - News Content: {total_news_chars:,} characters")
    print(f"  - Total Entities: {total_entities}")

    # Performance Summary
    print_section("PERFORMANCE SUMMARY", "=")
    total_time = (
        init_time + decision_time + query_gen_time + tools_time + processing_time
    )
    print(f"Initialization: {init_time:.2f}s")
    print(f"Decision: {decision_time:.2f}s")
    print(f"Query Generation: {query_gen_time:.2f}s")
    print(f"Tool Execution: {tools_time:.2f}s")
    print(f"Processing: {processing_time:.2f}s")
    print(f"{'=' * 40}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"{'=' * 40}")

    # Breakdown
    llm_time = decision_time + query_gen_time + processing_time
    print(f"\nTime Breakdown:")
    print(f"  - LLM Calls: {llm_time:.2f}s ({(llm_time / total_time * 100):.1f}%)")
    print(f"  - Tool Calls: {tools_time:.2f}s ({(tools_time / total_time * 100):.1f}%)")
    print(f"  - Other: {init_time:.2f}s ({(init_time / total_time * 100):.1f}%)")

    # Efficiency metrics
    print(f"\nEfficiency Metrics:")
    if web_count > 0:
        print(f"  - Web Search: {tools_time / 2:.2f}s per result (avg)")
    if news_count > 0:
        print(f"  - News Scraping: {tools_time / 2:.2f}s per article (avg)")
    if formatted_context:
        chars_per_sec = (
            len(formatted_context) / processing_time if processing_time > 0 else 0
        )
        print(f"  - Processing Speed: {chars_per_sec:.0f} chars/sec")


if __name__ == "__main__":
    asyncio.run(test_realtime_info_agent())
