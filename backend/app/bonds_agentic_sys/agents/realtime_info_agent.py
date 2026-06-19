"""
Real-Time Info Agent
Processes web search and news results to create formatted, actionable context for advisory agent
Optimized for speed: async operations, intelligent decision-making, parallel execution, caching
"""

from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import hashlib
from datetime import datetime

from schemas_v2 import ToolResult, ToolType, NewsArticle

# Import the new news scraper tool
try:
    from tools.np4kvesion import search_news_newspaper

    NEWSPAPER4K_AVAILABLE = True
except ImportError:
    NEWSPAPER4K_AVAILABLE = False
    print(
        " Newspaper4K scraper not available. News scraping will use alternative methods."
    )


class RealTimeInfoAgent:
    """
    Processes real-time information (web search + news) and formats it for advisory agent
    Optimized for speed with async operations, intelligent decision-making, caching, and content truncation
    """

    def __init__(self, llm: ChatOpenAI, fast_llm: Optional[ChatOpenAI] = None):
        self.llm = llm  # Main LLM for processing
        self.fast_llm = (
            fast_llm or llm
        )  # Fast LLM for quick decisions (use same if not provided)
        self.executor = ThreadPoolExecutor(
            max_workers=3
        )  # For running sync LLM calls async

        # In-memory cache for decisions and query generation (key: hash of query+intent)
        self._decision_cache: Dict[str, Dict[str, Any]] = {}
        self._query_cache: Dict[str, Dict[str, Any]] = {}

        # Content size limits to reduce token usage (aggressive for speed)
        self.MAX_WEB_SNIPPET_LENGTH = 120  # Characters per snippet (reduced)
        self.MAX_NEWS_SUMMARY_LENGTH = 150  # Characters per article summary (reduced)
        self.MAX_TOTAL_CONTENT_LENGTH = 1500  # Total characters sent to LLM (reduced)

        # Optimized prompt for intelligent decision-making (shorter, faster)
        self.decision_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Quickly determine if a bond query needs real-time info (web search + news).

Needed: current market, hypotheticals ("if RBI cuts rates"), forecasts, recent policy, time-sensitive info.
Not needed: general info, history, portfolio analysis, definitions, calculations.

Output JSON only:
{{
    "needs_realtime_info": true/false,
    "reasoning": "brief",
    "priority": "high/medium/low"
}}""",
                ),
                ("user", "Query: {query}\nIntent: {intent}\nNeeds real-time info?"),
            ]
        )

        # Optimized prompt for generating intelligent search queries (shorter, faster)
        self.query_generation_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Generate search queries for Indian bond market. Extract key terms from the query (company names, state names, bond types, etc.). Output JSON:
{{
    "web_search_query": "Indian bond market [5-10 words, include specific entities from query]",
    "news_keywords": ["term1", "term2", "term3", "term4"]  // Include specific entities, bond types, state names
}}""",
                ),
                (
                    "user",
                    "Query: {query}\nIntent: {intent}\nGenerate queries. Extract and include specific entities (company names, state names, bond types) from the query.",
                ),
            ]
        )

        # Ultra-optimized processing prompt (minimal, fast)
        self.processing_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Extract bond market insights. Format:
Summary: [2 sentences]
Insights: [3 bullets]
Implications: [1-2 sentences]
Be concise, focus on rates/RBI/credit/sentiment.""",
                ),
                (
                    "user",
                    "Q: {query}\n\n{web_search_results}\n{news_articles}\n\nExtract insights.",
                ),
            ]
        )

    def _get_cache_key(self, query: str, intent: str) -> str:
        """Generate cache key from query and intent"""
        key_str = f"{query.lower().strip()}|{intent.lower().strip()}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def should_gather_realtime_info(
        self, query: str, intent: str = ""
    ) -> Dict[str, Any]:
        """
        Intelligently decide if real-time info is needed (async, fast, cached)

        Returns:
            Dict with 'needs_realtime_info' (bool), 'reasoning' (str), 'priority' (str)
        """
        # Check cache first
        cache_key = self._get_cache_key(query, intent or "general")
        if cache_key in self._decision_cache:
            return self._decision_cache[cache_key]

        try:
            # Fast keyword-based pre-check (avoid LLM call for obvious cases)
            query_lower = query.lower()

            # Data queries that should use MCP tools, NOT news/web search
            data_query_keywords = [
                "yield",
                "yields",
                "g-sec",
                "gsec",
                "government bond",
                "bond price",
                "bond info",
                "bond details",
                "ytm",
                "coupon",
                "maturity",
                "duration",
                "convexity",
                "isin",
                "bond symbol",
            ]

            # Check if this is a data query (should skip real-time info, use MCP instead)
            if any(kw in query_lower for kw in data_query_keywords):
                result = {
                    "needs_realtime_info": False,
                    "reasoning": "Data query - should use MCP tools, not news/web search",
                    "priority": "low",
                }
                self._decision_cache[cache_key] = result
                return result

            obvious_keywords = [
                "if",
                "when",
                "what if",
                "hypothetical",
                "scenario",
                "forecast",
                "outlook",
                "prediction",
                "expect",
                "breaking",
                "news",
                "update",
                "announcement",
                "market sentiment",
                "rate cut",
                "rate hike",
                "rbi policy",
            ]
            obvious_no_keywords = [
                "explain",
                "what is",
                "define",
                "how does",
                "calculate",
                "compare",
                "show me",
            ]

            # Only trigger on time-sensitive keywords if NOT a data query
            if any(kw in query_lower for kw in obvious_keywords):
                result = {
                    "needs_realtime_info": True,
                    "reasoning": "Contains time-sensitive keywords",
                    "priority": "high"
                    if any(kw in query_lower for kw in ["breaking", "today", "recent"])
                    else "medium",
                }
                self._decision_cache[cache_key] = result
                return result

            if any(kw in query_lower for kw in obvious_no_keywords) and not any(
                kw in query_lower for kw in obvious_keywords
            ):
                result = {
                    "needs_realtime_info": False,
                    "reasoning": "General information query",
                    "priority": "low",
                }
                self._decision_cache[cache_key] = result
                return result

            # Run LLM call in thread pool to make it async
            loop = asyncio.get_event_loop()
            messages = self.decision_prompt.format_messages(
                query=query, intent=intent or "general"
            )

            # Use fast LLM for quick decision
            response = await loop.run_in_executor(
                self.executor, lambda: self.fast_llm.invoke(messages)
            )

            # Handle structured output or parse JSON
            if isinstance(response, dict):
                decision = response
            else:
                content = (
                    response.content if hasattr(response, "content") else str(response)
                )
                # Quick JSON extraction
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                elif content.startswith("{") and content.endswith("}"):
                    pass  # Already JSON
                else:
                    # Try to find JSON object
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        content = content[start:end]

                decision = json.loads(content)

            result = {
                "needs_realtime_info": decision.get("needs_realtime_info", False),
                "reasoning": decision.get("reasoning", ""),
                "priority": decision.get("priority", "medium"),
            }

            # Cache result
            self._decision_cache[cache_key] = result
            return result

        except Exception as e:
            # Fallback: analyze query text for keywords
            query_lower = query.lower()
            needs_info = any(keyword in query_lower for keyword in obvious_keywords)
            result = {
                "needs_realtime_info": needs_info,
                "reasoning": f"Error: {str(e)}, using keyword fallback",
                "priority": "medium" if needs_info else "low",
            }
            self._decision_cache[cache_key] = result
            return result

    async def generate_search_queries(
        self, query: str, intent: str = ""
    ) -> Dict[str, Any]:
        """
        Generate intelligent search queries based on user query and intent (async, cached)

        Returns:
            Dict with 'web_search_query' and 'news_keywords' (list)
        """
        # Check cache first
        cache_key = self._get_cache_key(query, intent or "general")
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        try:
            # Extract key terms from query for better keyword generation
            query_words = query.split()
            # Extract capitalized words (likely entities: company names, state names)
            entities = [w for w in query_words if w[0].isupper() and len(w) > 2]
            # Extract important lowercase words (bond-related terms)
            important_terms = [
                w.lower()
                for w in query_words
                if len(w) > 4
                and w.lower()
                not in [
                    "what",
                    "is",
                    "the",
                    "latest",
                    "news",
                    "on",
                    "about",
                    "state",
                    "bonds",
                ]
            ]

            # Fast fallback for simple queries
            if len(query.split()) <= 5:
                keywords = []
                if entities:
                    keywords.extend(entities[:2])
                keywords.append("bonds" if "bond" in query.lower() else "bond market")
                keywords.extend(important_terms[:2])

                result = {
                    "web_search_query": f"Indian bond market {query}",
                    "news_keywords": keywords[:4]
                    if keywords
                    else [query[:30], "bond market"],
                }
                self._query_cache[cache_key] = result
                return result

            # Run LLM call in thread pool to make it async
            loop = asyncio.get_event_loop()
            messages = self.query_generation_prompt.format_messages(
                query=query, intent=intent or "general"
            )

            # Use fast LLM for query generation
            response = await loop.run_in_executor(
                self.executor, lambda: self.fast_llm.invoke(messages)
            )

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Try to parse JSON from response
            try:
                # Quick JSON extraction
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                elif content.startswith("{") and content.endswith("}"):
                    pass  # Already JSON
                else:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        content = content[start:end]

                queries = json.loads(content)
                result = {
                    "web_search_query": queries.get(
                        "web_search_query", f"Indian bond market {query[:50]}"
                    ),
                    "news_keywords": queries.get(
                        "news_keywords",
                        [query[:30]] if len(query) > 10 else ["bond market"],
                    ),
                }
                self._query_cache[cache_key] = result
                return result
            except json.JSONDecodeError:
                # Fast fallback: use query directly
                result = {
                    "web_search_query": f"Indian bond market {query[:50]}",
                    "news_keywords": [query[:30]]
                    if len(query) > 10
                    else ["bond market"],
                }
                self._query_cache[cache_key] = result
                return result
        except Exception as e:
            # Fast fallback: use query directly
            result = {
                "web_search_query": f"Indian bond market {query[:50]}",
                "news_keywords": [query[:30]] if len(query) > 10 else ["bond market"],
            }
            self._query_cache[cache_key] = result
            return result

    async def fetch_news_direct(
        self, query: str, target_count: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch news directly using the Newspaper4K scraper

        Args:
            query: Search query for news
            target_count: Number of articles to fetch

        Returns:
            List of news articles in dict format, or None if scraper unavailable
        """
        if not NEWSPAPER4K_AVAILABLE:
            return None

        try:
            result = await search_news_newspaper(query, target_count)
            if result and result.get("articles"):
                # Convert to NewsArticle-compatible format
                articles = []
                for article in result["articles"]:
                    if article:
                        # Extract title from content (first sentence or first 100 chars)
                        content = article.get("content", "")
                        title = article.get("title", "")
                        if not title and content:
                            # Use first sentence or first 100 chars as title
                            first_sentence = content.split(".")[0].strip()
                            title = (
                                first_sentence[:100]
                                if len(first_sentence) > 10
                                else content[:100]
                            )

                        articles.append(
                            {
                                "title": title or "News Article",
                                "url": article.get("url", ""),
                                "source": article.get("source", "Unknown"),
                                "source_name": article.get("source", "Unknown"),
                                "content": content,
                                "summary": content[:500] if content else None,
                                "published_at": self._parse_date(article.get("date")),
                                "scraped_at": datetime.now(),
                                "sentiment_score": 0.0,  # Can be enhanced with sentiment analysis
                                "sentiment_polarity": 0.0,
                                "relevance_score": 1.0,
                                "word_count": article.get("word_count", 0),
                            }
                        )
                return articles
            return None
        except Exception as e:
            print(f" Error fetching news with Newspaper4K: {e}")
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        try:
            # Try common date formats
            try:
                from dateutil import parser

                return parser.parse(date_str)
            except ImportError:
                # Fallback to basic parsing
                from datetime import datetime as dt

                # Try ISO format first
                try:
                    return dt.fromisoformat(date_str.replace("Z", "+00:00"))
                except:
                    # Try common formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
                        try:
                            return dt.strptime(date_str, fmt)
                        except:
                            continue
                    return None
        except:
            return None

    async def process_realtime_info(
        self,
        query: str,
        intent: str,
        web_search_result: Optional[ToolResult] = None,
        news_result: Optional[ToolResult] = None,
        use_direct_news: bool = True,
    ) -> Optional[str]:
        """
        Process web search and news results into formatted context

        Args:
            query: User's original query
            intent: Classified intent
            web_search_result: Web search ToolResult
            news_result: News scraping ToolResult
            use_direct_news: If True, use Newspaper4K scraper directly when news_result is not available

        Returns:
            Formatted context string or None if no relevant information
        """
        # Check if we have any data to process
        has_web_search = (
            web_search_result and web_search_result.success and web_search_result.data
        )

        # Try to fetch news directly if news_result is not available and use_direct_news is True
        news_data = None
        has_news = False

        if news_result and news_result.success and news_result.data:
            # Use provided news result
            news_data = news_result.data
            has_news = True
        elif use_direct_news and NEWSPAPER4K_AVAILABLE:
            # Try to fetch news directly using Newspaper4K
            try:
                # Generate news query from the original query
                search_queries = await self.generate_search_queries(query, intent)
                news_keywords = search_queries.get("news_keywords", [query])
                # Combine keywords into a query
                news_query = " ".join(news_keywords[:3]) if news_keywords else query

                direct_news = await self.fetch_news_direct(news_query, target_count=5)
                if direct_news:
                    news_data = direct_news
                    has_news = True
                    print(f" Fetched {len(direct_news)} articles using Newspaper4K")
            except Exception as e:
                print(f"  Error fetching direct news: {e}")

        if not has_web_search and not has_news:
            return None

        # Format web search results (aggressively truncated for speed)
        web_search_text = ""
        if has_web_search:
            web_items = []
            for item in web_search_result.data[
                :2
            ]:  # Top 2 results only (reduced from 3)
                title = item.get("title", "")[:80]  # Truncate title more
                snippet = item.get("snippet", "")[
                    : self.MAX_WEB_SNIPPET_LENGTH
                ]  # Truncate snippet
                if title or snippet:
                    web_items.append(f"{title}: {snippet}")
            web_search_text = " | ".join(web_items)  # More compact format
            # Truncate total length
            if len(web_search_text) > self.MAX_TOTAL_CONTENT_LENGTH // 2:
                web_search_text = (
                    web_search_text[: self.MAX_TOTAL_CONTENT_LENGTH // 2] + "..."
                )

        # Format news articles (aggressively truncated for speed)
        news_text = ""
        if has_news and news_data:
            news_items = []
            for article in news_data[:2]:  # Top 2 articles only (reduced from 3)
                if isinstance(article, NewsArticle):
                    title = article.title[:80]  # Truncate title more
                    summary = (
                        article.summary
                        or (
                            article.content[: self.MAX_NEWS_SUMMARY_LENGTH]
                            if article.content
                            else ""
                        )
                    )[: self.MAX_NEWS_SUMMARY_LENGTH]
                    source = article.source[:20]  # Truncate source name
                    sentiment_label = (
                        "pos"
                        if article.sentiment_score > 0.1
                        else "neg"
                        if article.sentiment_score < -0.1
                        else "neu"
                    )
                    news_items.append(
                        f"{title} ({source}, {sentiment_label}): {summary}"
                    )
                elif isinstance(article, dict):
                    # Handle dict format (from Newspaper4K or other sources)
                    title = article.get("title", article.get("source", "News Article"))[
                        :80
                    ]
                    summary = article.get("summary", article.get("content", ""))[
                        : self.MAX_NEWS_SUMMARY_LENGTH
                    ]
                    source = article.get(
                        "source", article.get("source_name", "Unknown")
                    )[:20]
                    sentiment = article.get(
                        "sentiment_score", article.get("sentiment_polarity", 0.0)
                    )
                    sentiment_label = (
                        "pos"
                        if sentiment > 0.1
                        else "neg"
                        if sentiment < -0.1
                        else "neu"
                    )
                    news_items.append(
                        f"{title} ({source}, {sentiment_label}): {summary}"
                    )

            news_text = " | ".join(news_items)  # More compact format
            # Truncate total length
            if len(news_text) > self.MAX_TOTAL_CONTENT_LENGTH // 2:
                news_text = news_text[: self.MAX_TOTAL_CONTENT_LENGTH // 2] + "..."

        # Early exit if no data
        if not web_search_text and not news_text:
            return None

        # Quick relevance check: if results are too generic, skip processing
        if web_search_text and len(web_search_text) < 100:
            # Very short results, likely not relevant
            return None

        # For very short content, use simple formatting instead of LLM
        total_content_length = len(web_search_text) + len(news_text)
        if total_content_length < 300:
            # Simple formatted output for short content (no LLM call)
            parts = []
            if web_search_text:
                parts.append(f"Web Search Results:\n{web_search_text}")
            if news_text:
                parts.append(f"News Articles:\n{news_text}")
            return f" REAL-TIME MARKET INTELLIGENCE:\n\n" + "\n\n".join(parts)

        # Process with LLM (async, use fast_llm for speed)
        try:
            loop = asyncio.get_event_loop()
            messages = self.processing_prompt.format_messages(
                query=query,
                intent=intent,
                web_search_results=web_search_text
                if web_search_text
                else "No web search results.",
                news_articles=news_text if news_text else "No news articles.",
            )

            # Use fast_llm for processing to speed up (same model as decision/query gen)
            # Use lower temperature and max_tokens to speed up
            response = await loop.run_in_executor(
                self.executor, lambda: self.fast_llm.invoke(messages)
            )

            formatted_context = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Truncate if too long (shouldn't happen with max_tokens, but safety check)
            if len(formatted_context) > 1500:
                formatted_context = formatted_context[:1500] + "..."

            # Add header to make it clear this is real-time info
            if formatted_context and len(formatted_context.strip()) > 50:
                return f" REAL-TIME MARKET INTELLIGENCE:\n\n{formatted_context}"

            return None

        except Exception as e:
            print(f"  Real-time info processing error: {e}")
            # Fallback: return simple formatted version
            if web_search_text or news_text:
                web_count = (
                    len(web_search_result.data)
                    if has_web_search and web_search_result
                    else 0
                )
                news_count = len(news_data) if has_news and news_data else 0
                return f" Real-Time Market Context:\n\nWeb Search: {web_count} results\nNews: {news_count} articles"
            return None


def create_realtime_info_agent(
    api_key: str, model: str = "gpt-4o-mini", fast_model: str = "gpt-4o-mini"
) -> RealTimeInfoAgent:
    """
    Factory function

    Args:
        api_key: OpenAI API key
        model: Main model for processing (default: gpt-4o-mini)
        fast_model: Fast model for decisions and query generation (default: gpt-4o-mini)
    """
    # Use fast model for all operations to maximize speed
    # Reduced max_tokens for faster generation
    llm = ChatOpenAI(api_key=api_key, model=fast_model, temperature=0.0, max_tokens=400)
    fast_llm = ChatOpenAI(
        api_key=api_key, model=fast_model, temperature=0.0, max_tokens=150
    )
    return RealTimeInfoAgent(llm, fast_llm)
