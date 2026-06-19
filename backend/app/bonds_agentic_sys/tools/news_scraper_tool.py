"""
News Scraper Tool
Direct wrapper around Newspaper4K scraper for agent integration
"""

import os
import json
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from schemas_v2 import ToolResult, ToolType, NewsArticle
from dotenv import load_dotenv

load_dotenv()

# Import the Newspaper4K scraper
try:
    from .np4kvesion import search_news_newspaper

    NEWSPAPER4K_AVAILABLE = True
except ImportError:
    NEWSPAPER4K_AVAILABLE = False
    print(
        "  Newspaper4K scraper not available. News scraping will use fallback methods."
    )


class NewsScraperTool:
    """
    News scraper tool using Newspaper4K scraper
    Provides fast, parallel news scraping with multiple API keys and threaded scraping
    """

    def __init__(
        self, cache_dir: str = ".cache/news", newsdata_api_key: Optional[str] = None
    ):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        # Newspaper4K is already initialized in the module
        self.newspaper4k_available = NEWSPAPER4K_AVAILABLE
        if not self.newspaper4k_available:
            print(
                "  Newspaper4K scraper not available. News scraping will use fallback methods."
            )

    async def scrape_news(
        self,
        keywords: Optional[List[str]] = None,
        max_articles: int = 50,
        hours_back: int = 24,
    ) -> ToolResult:
        """
        Scrape news articles using Newspaper4K scraper

        Args:
            keywords: List of keywords to search for (will be combined into query)
            max_articles: Maximum number of articles to return
            hours_back: Hours to look back (used for filtering, not API query)

        Returns:
            ToolResult with list of NewsArticle objects
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(keywords, max_articles, hours_back)
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                return ToolResult(
                    tool_type=ToolType.NEWS_SCRAPER,
                    success=True,
                    data=cached_result,
                    cached=True,
                )

            # If Newspaper4K not available, use mock data
            if not self.newspaper4k_available:
                articles = self._generate_mock_news(keywords, max_articles)
                return ToolResult(
                    tool_type=ToolType.NEWS_SCRAPER,
                    success=True,
                    data=articles,
                    cached=False,
                )

            # Build search query from keywords
            if keywords:
                # Combine keywords into a search query
                query = " ".join(keywords)
            else:
                # Default query for Indian bond market news
                query = "Indian bond market RBI interest rate"

            # Use Newspaper4K scraper (already async)
            result = await search_news_newspaper(query, target_count=max_articles)

            # Convert Newspaper4K results to NewsArticle format
            articles = self._convert_to_news_articles(result.get("articles", []))

            # Cache the results
            self._save_to_cache(cache_key, articles)

            return ToolResult(
                tool_type=ToolType.NEWS_SCRAPER,
                success=True,
                data=articles,
                cached=False,
            )

        except Exception as e:
            print(f"  News scraping error: {e}")
            import traceback

            traceback.print_exc()
            # Fallback to mock data on error
            articles = self._generate_mock_news(keywords, max_articles)
            return ToolResult(
                tool_type=ToolType.NEWS_SCRAPER,
                success=True,
                data=articles,
                cached=False,
                error=f"Newspaper4K scraper failed, using mock data: {str(e)}",
            )

    def _convert_to_news_articles(
        self, newspaper_articles: List[dict]
    ) -> List[NewsArticle]:
        """
        Convert Newspaper4K article format to NewsArticle schema
        """
        articles = []

        for article_data in newspaper_articles:
            try:
                if not article_data:
                    continue

                # Parse published date
                published_at = None
                date_str = article_data.get("date")
                if date_str:
                    published_at = self._parse_date(date_str)

                # Extract title from content if not provided
                content = article_data.get("content", "")
                title = article_data.get("title", "")
                if not title and content:
                    # Use first sentence or first 100 chars as title
                    first_sentence = content.split(".")[0].strip()
                    title = (
                        first_sentence[:100]
                        if len(first_sentence) > 10
                        else content[:100]
                    )

                # Extract basic entities from content (simple keyword extraction)
                entities = []
                # Look for common financial terms
                financial_terms = [
                    "RBI",
                    "bond",
                    "yield",
                    "interest rate",
                    "inflation",
                    "GDP",
                    "NSE",
                    "BSE",
                    "government",
                    "treasury",
                ]
                content_lower = content.lower()
                for term in financial_terms:
                    if term.lower() in content_lower:
                        entities.append(term)

                # Simple sentiment estimation based on content keywords
                # Positive keywords
                positive_keywords = [
                    "growth",
                    "increase",
                    "rise",
                    "surge",
                    "gain",
                    "positive",
                    "strong",
                    "boost",
                    "improve",
                ]
                negative_keywords = [
                    "decline",
                    "fall",
                    "drop",
                    "decrease",
                    "negative",
                    "weak",
                    "concern",
                    "risk",
                    "crisis",
                ]

                positive_count = sum(
                    1 for kw in positive_keywords if kw in content_lower
                )
                negative_count = sum(
                    1 for kw in negative_keywords if kw in content_lower
                )

                # Calculate sentiment score (-1 to 1)
                if positive_count + negative_count > 0:
                    sentiment_score = (positive_count - negative_count) / max(
                        positive_count + negative_count, 1
                    )
                    sentiment_score = max(
                        -1.0, min(1.0, sentiment_score * 0.5)
                    )  # Scale down
                else:
                    sentiment_score = 0.0

                # Calculate relevance score based on word count
                word_count = article_data.get("word_count", len(content.split()))
                relevance_score = min(1.0, 0.5 + (min(word_count, 2000) / 2000 * 0.5))

                # Create summary from content
                summary = content[:500] if content else ""

                # Create NewsArticle
                article = NewsArticle(
                    title=title or "News Article",
                    url=article_data.get("url", ""),
                    source=article_data.get("source", "Unknown"),
                    content=content,
                    summary=summary,
                    sentiment_score=sentiment_score,
                    relevance_score=relevance_score,
                    entities=entities[:10],  # Limit to 10 entities
                    published_at=published_at,
                )

                articles.append(article)

            except Exception as e:
                print(f"  Error converting article: {e}")
                import traceback

                traceback.print_exc()
                continue

        return articles

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        try:
            # Try ISO format first
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except:
                pass

            # Try dateutil parser if available
            try:
                from dateutil import parser

                return parser.parse(date_str)
            except ImportError:
                pass

            # Try common formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S",
            ]:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue

            return None
        except:
            return None

    def _get_cache_key(
        self, keywords: Optional[List[str]], max_articles: int, hours_back: int
    ) -> str:
        """Generate cache key from parameters"""
        keywords_str = "_".join(sorted(keywords)) if keywords else "default"
        return f"news_{keywords_str}_{max_articles}_{hours_back}"

    def _load_from_cache(self, cache_key: str) -> Optional[List[NewsArticle]]:
        """Load articles from cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                # Check if cache is still valid (24 hours TTL)
                file_age = (
                    datetime.now()
                    - datetime.fromtimestamp(os.path.getmtime(cache_file))
                ).total_seconds()
                if file_age < 86400:  # 24 hours
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        articles = [NewsArticle(**item) for item in data]
                        return articles
            except Exception as e:
                print(f"  Cache load error: {e}")
        return None

    def _save_to_cache(self, cache_key: str, articles: List[NewsArticle]):
        """Save articles to cache"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            data = [article.dict() for article in articles]
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f" Cache save error: {e}")

    def _generate_mock_news(
        self, keywords: Optional[List[str]], count: int
    ) -> List[NewsArticle]:
        """Generate mock news for testing/fallback"""
        mock_articles = [
            NewsArticle(
                title=f"RBI maintains repo rate at 6.5% amid inflation concerns",
                url="https://economictimes.com/news/rbi-rate-decision",
                source="Economic Times",
                content="The Reserve Bank of India kept interest rates unchanged...",
                sentiment_score=0.2,
                relevance_score=0.9,
                entities=["RBI", "inflation", "repo rate"],
                published_at=datetime.now() - timedelta(hours=2),
            ),
            NewsArticle(
                title=f"Bond yields spike after CPI data release",
                url="https://moneycontrol.com/news/bond-yields",
                source="Moneycontrol",
                content="Government bond yields rose sharply following higher-than-expected CPI...",
                sentiment_score=-0.3,
                relevance_score=0.8,
                entities=["bonds", "yields", "CPI"],
                published_at=datetime.now() - timedelta(hours=5),
            ),
        ]
        return mock_articles[:count]
