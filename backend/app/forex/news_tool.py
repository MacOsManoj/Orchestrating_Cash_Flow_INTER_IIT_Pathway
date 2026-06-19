# pip install newspaper3k lxml_html_clean beautifulsoup4 newsdataapi requests textblob
"""
Financial News Scraper MCP Tool
Designed to be called by LLMs via MCP (Model Context Protocol)
"""

import requests
import json
import sqlite3
import csv
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from newsdataapi import NewsDataApiClient

try:
    from newspaper import Article

    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    Article = None
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# For sentiment analysis
try:
    from textblob import TextBlob

    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False


class FinancialNewsScraperTool:
    """
    MCP Tool for scraping financial news with smart fallback
    Optimized for Indian stock/bond markets
    """

    def __init__(self, newsdata_api_key: str):
        self.newsdata_api = NewsDataApiClient(apikey=newsdata_api_key)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        # Configuration
        self.MIN_RESULTS = 2
        self.TRUSTED_DOMAINS = ",".join(
            [
                "moneycontrol.com",
                "economictimes.indiatimes.com",
                "livemint.com",
                "business-standard.com",
                "financialexpress.com",
                "thehindubusinessline.com",
                "cnbctv18.com",
                "bloombergquint.com",
                "reuters.com",
                "businesstoday.in",
                "outlookbusiness.com",
                "financialchronicle.com",
            ]
        )

    def get_search_params_for_level(self, query: str, level: int) -> Dict[str, Any]:
        """Get search parameters for each fallback level"""
        params = {"language": "en"}

        if level == 0:
            params.update(
                {
                    "q": query,
                    "country": "in",
                    "category": "business",
                    "domainurl": self.TRUSTED_DOMAINS,
                }
            )
        elif level == 1:
            params.update(
                {
                    "q": query,
                    "country": "in",
                    "category": "business",
                }
            )
        elif level == 2:
            params.update(
                {
                    "q": query,
                    "country": "in,us,gb,sg",
                    "category": "business",
                }
            )
        elif level == 3:
            params.update(
                {
                    "q": query,
                    "country": "in,us,gb,sg",
                }
            )
        elif level == 4:
            params.update(
                {
                    "q": f"{query} (stock OR share OR NSE OR BSE OR equity)",
                    "category": "business",
                }
            )

        return params

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using TextBlob"""
        if not SENTIMENT_AVAILABLE or not text:
            return {"label": "neutral", "polarity": 0.0, "subjectivity": 0.0}

        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity

            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"

            return {
                "label": label,
                "polarity": round(polarity, 3),
                "subjectivity": round(subjectivity, 3),
            }
        except:
            return {"label": "neutral", "polarity": 0.0, "subjectivity": 0.0}

    def scrape_article_content(self, url: str) -> Dict[str, Any]:
        """Scrape full article content"""
        try:
            # Only use newspaper if available
            if not NEWSPAPER_AVAILABLE:
                raise Exception("newspaper3k not installed, using fallback scraper")

            article = Article(url, language="en")
            article.download()
            article.parse()

            full_text = article.text

            if full_text and len(full_text) > 100:
                try:
                    article.nlp()
                    summary = article.summary
                    keywords = article.keywords
                except:
                    summary = (
                        full_text[:500] + "..." if len(full_text) > 500 else full_text
                    )
                    keywords = []

                sentiment = self.analyze_sentiment(full_text)

                return {
                    "success": True,
                    "full_text": full_text,
                    "title": article.title,
                    "summary": summary,
                    "keywords": keywords if keywords else [],
                    "published_date": article.publish_date.isoformat()
                    if article.publish_date
                    else "",
                    "sentiment_label": sentiment["label"],
                    "sentiment_polarity": sentiment["polarity"],
                    "word_count": len(full_text.split()),
                }
            else:
                raise Exception("No content")

        except Exception as e:
            try:
                # Fallback scraper
                response = self.session.get(url, timeout=20)
                soup = BeautifulSoup(response.content, "html.parser")

                for element in soup(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()

                paragraphs = soup.find_all("p")
                article_text = " ".join([p.get_text(strip=True) for p in paragraphs])

                if len(article_text) > 100:
                    sentiment = self.analyze_sentiment(article_text)
                    return {
                        "success": True,
                        "full_text": article_text,
                        "title": soup.title.string if soup.title else "",
                        "summary": article_text[:500] + "...",
                        "keywords": [],
                        "published_date": "",
                        "sentiment_label": sentiment["label"],
                        "sentiment_polarity": sentiment["polarity"],
                        "word_count": len(article_text.split()),
                    }
            except:
                pass

            return {"success": False, "error": str(e)}

    def search_news(
        self, query: str, max_articles: int = 5, verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Main tool function - search for financial news with smart fallback

        Args:
            query: Stock/company name to search (e.g., "Reliance Industries", "HDFC Bank")
            max_articles: Maximum articles to return (default: 5)
            verbose: Print detailed progress (default: False)

        Returns:
            Dictionary with:
            - articles: List of article dictionaries
            - summary: Quick summary of results
            - metadata: Search metadata
        """

        if verbose:
            print(f"Searching for: {query}")

        all_results = []
        successful_level = None

        # Try each level until we get enough results
        for level in range(5):
            params = self.get_search_params_for_level(query, level)

            try:
                response = self.newsdata_api.latest_api(**params)
            except Exception as e:
                if verbose:
                    print(f"Level {level} API error: {e}")
                continue

            if not response or "results" not in response:
                continue

            articles = response["results"][:max_articles]

            if len(articles) == 0:
                continue

            if verbose:
                print(f"Level {level}: Found {len(articles)} articles, scraping...")

            # Scrape articles
            for article_data in articles:
                url = article_data.get("link", "")
                if not url:
                    continue

                content = self.scrape_article_content(url)

                if content["success"]:
                    result = {
                        "url": url,
                        "title": content["title"] or article_data.get("title", ""),
                        "summary": content["summary"],
                        "full_text": content["full_text"],
                        "keywords": content["keywords"],
                        "published_date": content["published_date"]
                        or article_data.get("pubDate", ""),
                        "source": article_data.get("source_name", ""),
                        "sentiment": content["sentiment_label"],
                        "sentiment_score": content["sentiment_polarity"],
                        "word_count": content["word_count"],
                    }
                    all_results.append(result)

            # Check if we have enough
            if len(all_results) >= self.MIN_RESULTS:
                successful_level = level
                break

        # Prepare response
        if len(all_results) > 0:
            # Generate summary
            sentiments = [a["sentiment"] for a in all_results]
            avg_sentiment = sum(a["sentiment_score"] for a in all_results) / len(
                all_results
            )

            summary_text = f"Found {len(all_results)} articles about '{query}'. "
            summary_text += f"Sentiment: {sentiments.count('positive')} positive, "
            summary_text += f"{sentiments.count('neutral')} neutral, "
            summary_text += f"{sentiments.count('negative')} negative. "
            summary_text += f"Average sentiment score: {avg_sentiment:+.3f}"

            return {
                "success": True,
                "query": query,
                "articles": all_results,
                "summary": summary_text,
                "metadata": {
                    "total_articles": len(all_results),
                    "search_level": successful_level,
                    "timestamp": datetime.now().isoformat(),
                },
            }
        else:
            return {
                "success": False,
                "query": query,
                "articles": [],
                "summary": f"No articles found for '{query}' after trying all search levels.",
                "metadata": {
                    "total_articles": 0,
                    "search_level": None,
                    "timestamp": datetime.now().isoformat(),
                },
            }

    def search_news_global(
        self, query: str, max_articles: int = 5, verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Global news search without country restrictions - better for forex news

        Args:
            query: Search query (e.g., "euro dollar currency")
            max_articles: Maximum articles to return (default: 5)
            verbose: Print detailed progress (default: False)
        """
        if verbose:
            print(f"Global search for: {query}")

        all_results = []

        # Try global search with business category first, then without
        search_params = [
            {"q": query, "language": "en", "category": "business"},
            {"q": query, "language": "en"},
            {"q": f"{query} forex market", "language": "en"},
        ]

        for params in search_params:
            try:
                response = self.newsdata_api.latest_api(**params)
            except Exception as e:
                if verbose:
                    print(f"API error: {e}")
                continue

            if not response or "results" not in response:
                continue

            articles = response.get("results", [])[:max_articles]

            if len(articles) == 0:
                continue

            if verbose:
                print(f"Found {len(articles)} articles, scraping...")

            # Scrape articles
            for article_data in articles:
                url = article_data.get("link", "")
                if not url:
                    continue

                # Get basic info without full scraping for speed
                sentiment = self.analyze_sentiment(
                    article_data.get("description", "") or article_data.get("title", "")
                )

                result = {
                    "url": url,
                    "title": article_data.get("title", ""),
                    "summary": article_data.get("description", "")[:500]
                    if article_data.get("description")
                    else "",
                    "source": article_data.get("source_id", "Unknown"),
                    "published_date": article_data.get("pubDate", ""),
                    "sentiment": sentiment["label"],
                    "sentiment_score": sentiment["polarity"],
                }
                all_results.append(result)

            # If we found articles, return them
            if all_results:
                break

        if all_results:
            avg_sentiment = sum(r["sentiment_score"] for r in all_results) / len(
                all_results
            )
            return {
                "success": True,
                "query": query,
                "articles": all_results,
                "summary": f"Found {len(all_results)} articles. Average sentiment: {avg_sentiment:+.2f}",
                "metadata": {
                    "total_articles": len(all_results),
                    "timestamp": datetime.now().isoformat(),
                },
            }
        else:
            return {
                "success": False,
                "query": query,
                "articles": [],
                "summary": f"No articles found for '{query}'.",
                "metadata": {
                    "total_articles": 0,
                    "timestamp": datetime.now().isoformat(),
                },
            }

    def get_latest_news(
        self, stocks: List[str], max_articles_per_stock: int = 3
    ) -> Dict[str, Any]:
        """
        Batch search for multiple stocks

        Args:
            stocks: List of stock/company names
            max_articles_per_stock: Max articles per stock (default: 3)

        Returns:
            Dictionary with results for each stock
        """
        results = {}

        for stock in stocks:
            result = self.search_news(
                stock, max_articles=max_articles_per_stock, verbose=False
            )
            results[stock] = result
            time.sleep(1)  # Rate limiting

        return {
            "success": True,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }


# ============================================
# MCP TOOL INTERFACE
# ============================================


def create_tool(api_key: str) -> FinancialNewsScraperTool:
    """
    Factory function to create the tool instance
    Use this in your MCP server
    """
    return FinancialNewsScraperTool(api_key)


# Example tool schema for MCP
TOOL_SCHEMA = {
    "name": "search_financial_news",
    "description": "Search for financial news articles about stocks, bonds, or companies with sentiment analysis. Optimized for Indian markets (NSE/BSE) but works globally.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Stock/company name to search (e.g., 'Reliance Industries', 'HDFC Bank', 'Britannia')",
            },
            "max_articles": {
                "type": "integer",
                "description": "Maximum number of articles to return (default: 5)",
                "default": 5,
            },
            "verbose": {
                "type": "boolean",
                "description": "Print detailed progress (default: false)",
                "default": False,
            },
        },
        "required": ["query"],
    },
}

BATCH_TOOL_SCHEMA = {
    "name": "get_latest_news_batch",
    "description": "Get latest news for multiple stocks/companies at once with sentiment analysis",
    "parameters": {
        "type": "object",
        "properties": {
            "stocks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of stock/company names to search",
            },
            "max_articles_per_stock": {
                "type": "integer",
                "description": "Maximum articles per stock (default: 3)",
                "default": 3,
            },
        },
        "required": ["stocks"],
    },
}


# ============================================
# STANDALONE USAGE (for testing)
# ============================================

if __name__ == "__main__":
    # Test the tool
    API_KEY = "pub_8f5bd39159864856a0542878a7da4cb1"

    tool = create_tool(API_KEY)

    # Single search
    result = tool.search_news("Reliance Industries", max_articles=3, verbose=True)

    print("\n" + "=" * 70)
    print("RESULT:")
    print("=" * 70)
    print(json.dumps(result, indent=2, default=str))

    # Batch search
    # batch_result = tool.get_latest_news(
    #     stocks=["Reliance Industries", "HDFC Bank", "TCS"],
    #     max_articles_per_stock=2
    # )
    # print(json.dumps(batch_result, indent=2, default=str))
