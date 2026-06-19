#!/usr/bin/env python3
"""
Test script for News Headlines Sentiment Tool
Tests the FinancialNewsScraperTool independently without the API
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Colors for console output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def sentiment_color(sentiment: str) -> str:
    """Get color for sentiment label"""
    if sentiment.lower() in ["positive", "bullish"]:
        return Colors.GREEN
    elif sentiment.lower() in ["negative", "bearish"]:
        return Colors.RED
    else:
        return Colors.YELLOW


# Forex pair to search query mapping
PAIR_SEARCH_QUERIES = {
    "EURUSD": "EUR USD euro dollar forex ECB Federal Reserve",
    "GBPUSD": "GBP USD pound dollar forex Bank of England Fed",
    "USDJPY": "USD JPY dollar yen forex Bank of Japan Fed BOJ",
    "EURINR": "EUR INR euro rupee forex ECB RBI India",
    "GBPINR": "GBP INR pound rupee forex BOE RBI India",
    "JPYINR": "JPY INR yen rupee forex BOJ RBI India",
    "USDINR": "USD INR dollar rupee forex Fed RBI India",
}


def test_news_tool_initialization():
    """Test that the news tool can be initialized"""
    print_header("Testing News Tool Initialization")

    api_key = os.getenv("NEWSDATA_API_KEY")

    if not api_key:
        print_error("NEWSDATA_API_KEY environment variable not set!")
        print_info("Please set it in your .env file or environment")
        return None

    print_success(f"API Key found: {api_key[:8]}...{api_key[-4:]}")

    try:
        from news_tool import FinancialNewsScraperTool

        news_tool = FinancialNewsScraperTool(api_key)
        print_success("FinancialNewsScraperTool initialized successfully")
        return news_tool
    except ImportError as e:
        print_error(f"Failed to import news_tool: {e}")
        print_info("Make sure all dependencies are installed:")
        print_info(
            "  pip install newspaper3k lxml_html_clean beautifulsoup4 newsdataapi requests textblob"
        )
        return None
    except Exception as e:
        print_error(f"Failed to initialize news tool: {e}")
        return None


def test_sentiment_analysis(news_tool):
    """Test the sentiment analysis functionality"""
    print_header("Testing Sentiment Analysis")

    test_texts = [
        (
            "The dollar surged to multi-year highs as Fed signals more rate hikes",
            "positive",
        ),
        ("Currency markets crash amid global economic uncertainty", "negative"),
        ("EUR/USD traded sideways in a quiet session", "neutral"),
        ("Strong jobs data boosts outlook for the US economy", "positive"),
        ("Recession fears grow as inflation remains stubbornly high", "negative"),
    ]

    correct = 0
    for text, expected in test_texts:
        result = news_tool.analyze_sentiment(text)
        actual = result["label"]
        match = "✓" if actual == expected else "✗"
        color = Colors.GREEN if actual == expected else Colors.RED
        print(f'  {color}{match}{Colors.ENDC} "{text[:50]}..."')
        print(
            f"      Expected: {expected}, Got: {actual} (polarity: {result['polarity']:+.3f})"
        )
        if actual == expected:
            correct += 1

    print(
        f"\n  Accuracy: {correct}/{len(test_texts)} ({100 * correct / len(test_texts):.0f}%)"
    )
    return correct == len(test_texts)


def test_global_news_search(
    news_tool, query: str = "forex currency market", timeout: int = 30
):
    """Test global news search functionality"""
    print_header(f"Testing Global News Search: '{query}'")

    print_info(
        "Note: NewsData API has rate limits. If you hit them, wait a few minutes."
    )

    try:
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("API call took too long (possible rate limit)")

        # Set timeout for API call
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            result = news_tool.search_news_global(query, max_articles=5, verbose=True)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        if result.get("success"):
            print_success(f"Found {len(result['articles'])} articles")
            print_info(result["summary"])

            print(f"\n  {Colors.BOLD}Headlines:{Colors.ENDC}")
            for i, article in enumerate(result["articles"], 1):
                sentiment = article.get("sentiment", "neutral")
                score = article.get("sentiment_score", 0)
                color = sentiment_color(sentiment)

                print(f"  {i}. {article['title'][:70]}...")
                print(
                    f"     {color}[{sentiment.upper()} {score:+.2f}]{Colors.ENDC} - {article['source']}"
                )
                print(f"     {article.get('published_date', 'N/A')}")
                print()

            return True
        else:
            print_warning(
                f"No articles found: {result.get('summary', 'Unknown error')}"
            )
            return False

    except TimeoutError as e:
        print_warning(f"Timeout: {e}")
        print_info("This usually means the API rate limit was hit. Try again later.")
        return False

    except Exception as e:
        print_error(f"Error during search: {e}")
        if "Rate limit" in str(e) or "rate limit" in str(e).lower():
            print_info("Rate limit exceeded. The free API tier has strict limits.")
            print_info("Wait a few minutes before trying again.")
        import traceback

        traceback.print_exc()
        return False


def test_forex_pair_headlines(news_tool, pairs: List[str] = None):
    """Test getting headlines for forex pairs"""
    if pairs is None:
        pairs = ["EURUSD", "USDJPY", "GBPUSD"]

    print_header("Testing Forex Pair Headlines")

    results = {}

    for pair in pairs:
        query = PAIR_SEARCH_QUERIES.get(pair, f"{pair[:3]} {pair[3:]} forex")
        print(
            f"\n  {Colors.BOLD}Testing {pair}{Colors.ENDC} (query: '{query[:40]}...')"
        )

        try:
            result = news_tool.search_news_global(query, max_articles=5, verbose=False)

            if result.get("success") and result.get("articles"):
                articles = result["articles"]

                # Calculate overall sentiment
                scores = [a.get("sentiment_score", 0) for a in articles]
                avg_score = sum(scores) / len(scores) if scores else 0

                if avg_score > 0.15:
                    overall = "BULLISH"
                    color = Colors.GREEN
                elif avg_score < -0.15:
                    overall = "BEARISH"
                    color = Colors.RED
                else:
                    overall = "NEUTRAL"
                    color = Colors.YELLOW

                positive = sum(1 for a in articles if a.get("sentiment") == "positive")
                negative = sum(1 for a in articles if a.get("sentiment") == "negative")
                neutral = len(articles) - positive - negative

                print(f"     {color}{overall} (score: {avg_score:+.3f}){Colors.ENDC}")
                print(
                    f"     Headlines: {len(articles)} (+{positive} / -{negative} / ~{neutral})"
                )

                # Show top 2 headlines
                for article in articles[:2]:
                    sent = article.get("sentiment", "neutral")
                    sent_color = sentiment_color(sent)
                    print(
                        f"     • {article['title'][:60]}... {sent_color}[{sent}]{Colors.ENDC}"
                    )

                results[pair] = {
                    "sentiment": overall,
                    "score": avg_score,
                    "headlines": len(articles),
                    "positive": positive,
                    "negative": negative,
                }
            else:
                print_warning(f"     No articles found for {pair}")
                results[pair] = {"sentiment": "NEUTRAL", "score": 0, "headlines": 0}

        except Exception as e:
            print_error(f"     Error: {e}")
            results[pair] = {"sentiment": "ERROR", "score": 0, "headlines": 0}

    # Summary
    print(f"\n  {Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  {'Pair':<10} {'Sentiment':<10} {'Score':>8} {'Headlines':>10}")
    print(f"  {'-' * 40}")
    for pair, data in results.items():
        sent = data["sentiment"]
        color = sentiment_color(sent)
        print(
            f"  {pair:<10} {color}{sent:<10}{Colors.ENDC} {data['score']:>+8.3f} {data['headlines']:>10}"
        )

    return results


def test_article_scraping(news_tool):
    """Test article content scraping"""
    print_header("Testing Article Scraping")

    # First get some article URLs
    result = news_tool.search_news_global(
        "forex trading", max_articles=2, verbose=False
    )

    if not result.get("success") or not result.get("articles"):
        print_warning("No articles found to test scraping")
        return False

    article = result["articles"][0]
    url = article.get("url", "")

    if not url:
        print_warning("No URL found in article")
        return False

    print_info(f"Testing scraping for: {url[:60]}...")

    try:
        content = news_tool.scrape_article_content(url)

        if content.get("success"):
            print_success("Article scraped successfully")
            print(f"  Title: {content.get('title', 'N/A')[:60]}...")
            print(f"  Word count: {content.get('word_count', 0)}")
            print(
                f"  Sentiment: {content.get('sentiment_label', 'N/A')} ({content.get('sentiment_polarity', 0):+.3f})"
            )
            print(f"  Keywords: {', '.join(content.get('keywords', [])[:5])}")
            return True
        else:
            print_warning(f"Scraping failed: {content.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print_error(f"Error during scraping: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("   FOREX NEWS HEADLINES TOOL - TEST SUITE")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    print(f"Time: {datetime.now().isoformat()}")

    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
    }

    # Test 1: Initialize
    news_tool = test_news_tool_initialization()
    if news_tool is None:
        print_error("\nCannot continue without news tool. Exiting.")
        return results
    results["passed"] += 1

    # Test 2: Sentiment Analysis
    try:
        if test_sentiment_analysis(news_tool):
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        print_error(f"Sentiment test failed: {e}")
        results["failed"] += 1

    # Test 3: Global News Search
    try:
        if test_global_news_search(news_tool, "forex currency trading"):
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        print_error(f"Global search test failed: {e}")
        results["failed"] += 1

    # Test 4: Forex Pair Headlines
    try:
        pair_results = test_forex_pair_headlines(
            news_tool, ["EURUSD", "USDJPY", "GBPUSD"]
        )
        if pair_results and any(
            r.get("headlines", 0) > 0 for r in pair_results.values()
        ):
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        print_error(f"Forex pair test failed: {e}")
        results["failed"] += 1

    # Test 5: Article Scraping (optional, can be slow)
    try:
        if test_article_scraping(news_tool):
            results["passed"] += 1
        else:
            results["skipped"] += (
                1  # Scraping failures are common due to site restrictions
            )
    except Exception as e:
        print_warning(f"Article scraping test skipped: {e}")
        results["skipped"] += 1

    # Summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("   TEST SUMMARY")
    print("=" * 60)
    print(f"{Colors.ENDC}")

    total = results["passed"] + results["failed"]
    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Skipped: {results['skipped']}{Colors.ENDC}")

    if results["failed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}")
    else:
        print(
            f"\n{Colors.YELLOW}⚠ Some tests failed - check API key and network{Colors.ENDC}"
        )

    return results


if __name__ == "__main__":
    # Check for quick test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test - just check if tool initializes
        news_tool = test_news_tool_initialization()
        if news_tool:
            test_sentiment_analysis(news_tool)
    else:
        # Full test suite
        run_all_tests()
