"""
WORKING VERSION - WITH ERROR FILTERING
Filters out "Access Denied" and broken articles
"""

import os
from dotenv import load_dotenv

# Load .env file FIRST before any other imports
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from newsdataapi import NewsDataApiClient
import re
import time
from datetime import datetime
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

# Gemini LLM
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# FinBERT
try:
    from transformers import pipeline
    import torch

    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

app = FastAPI(title="Financial News API - Filtered", version="6.0")

API_KEYS = [
    "pub_8f5bd39159864856a0542878a7da4cb1",  # Key 1
    "pub_3c1c7125cf614b128e9ed2ec675e8658",  # Key 2 (get from newsdata.io)
    "pub_531a2ce4c76a4b8e97b9af40046fd54c",  # Key 3
]

api_clients = [NewsDataApiClient(apikey=key) for key in API_KEYS]
api_executor = ThreadPoolExecutor(max_workers=len(API_KEYS))


def load_sentiment_model():
    """
    Load FinBERT exactly once at startup.
    Call this function inside FastAPI startup event OR manually for scripts.
    """
    global sentiment_classifier, SENTIMENT_AVAILABLE

    try:
        print("Loading FinBERT model...")

        from transformers import pipeline
        import torch

        sentiment_classifier = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            device=0 if torch.cuda.is_available() else -1,
            truncation=True,
            max_length=512,
            batch_size=8,
        )

        SENTIMENT_AVAILABLE = True
        print("✓ FinBERT loaded successfully")

    except Exception as e:
        print(f"✗ FinBERT failed to load: {e}")
        SENTIMENT_AVAILABLE = False


sentiment_classifier = None
if SENTIMENT_AVAILABLE:
    try:
        print("Loading FinBERT...")
        sentiment_classifier = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            device=0 if torch.cuda.is_available() else -1,
            truncation=True,
            max_length=512,
            batch_size=8,
        )
        print("✓ FinBERT loaded")
    except Exception as e:
        print(f"✗ FinBERT error: {e}")
        SENTIMENT_AVAILABLE = False


# Initialize Gemini API
gemini_model = None
if GEMINI_AVAILABLE:
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")
            print("✓ Gemini API initialized")
        else:
            print("✗ GEMINI_API_KEY not set")
            GEMINI_AVAILABLE = False
    except Exception as e:
        print(f"✗ Gemini initialization error: {e}")
        GEMINI_AVAILABLE = False

TRUSTED_DOMAINS = ",".join(
    [
        "moneycontrol.com",
        "economictimes.indiatimes.com",
        "livemint.com",
        "business-standard.com",
        "financialexpress.com",
    ]
)

SENTENCE_REGEX = re.compile(r"[.!?]+")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Stock/company name")
    max_articles: int = Field(5, ge=1, le=50)


def build_advanced_query(query: str, level: int) -> str:
    """Query building"""
    parts = query.strip().split()

    if level <= 2:
        if len(parts) == 1:
            return parts[0]
        else:
            return " AND ".join(parts)
    else:
        return " OR ".join(parts)


def get_search_params(query: str, level: int) -> Dict:
    """5-level fallback"""
    params = {"language": "en"}
    advanced_query = build_advanced_query(query, level)

    if level == 0:
        params.update(
            {
                "qInTitle": advanced_query,
                "country": "in",
                "category": "business",
                "domainurl": TRUSTED_DOMAINS,
            }
        )
    elif level == 1:
        params.update(
            {"qInTitle": advanced_query, "country": "in", "category": "business"}
        )
    elif level == 2:
        params.update(
            {"q": advanced_query, "country": "in,us,gb,sg", "category": "business"}
        )
    elif level == 3:
        params.update({"q": advanced_query, "country": "in,us,gb,sg"})
    else:
        params.update({"q": advanced_query, "category": "business"})

    return params


def is_valid_article(content: Dict, url: str) -> bool:
    """
    NEW: Validate article content - filter out errors/broken pages

    Returns True if article is valid, False if broken/error
    """
    if not content.get("success"):
        return False

    text = content.get("full_text", "")
    title = content.get("title", "")

    # Check 1: Minimum content length
    if len(text) < 100:
        print(f"      ✗ Too short ({len(text)} chars): {url[:60]}...")
        return False

    # Check 2: "Access Denied" errors
    if "access denied" in text.lower() or "access denied" in title.lower():
        print(f"      ✗ Access Denied: {url[:60]}...")
        return False

    # Check 3: Error reference codes (edgesuite.net, cloudflare, etc.)
    error_patterns = [
        "reference #",
        "errors.edgesuite.net",
        "cloudflare",
        "ray id:",
        "blocked",
        "forbidden",
        "403 error",
        "404 error",
        "page not found",
    ]

    text_lower = text.lower()
    for pattern in error_patterns:
        if pattern in text_lower:
            print(f"      ✗ Error page ({pattern}): {url[:60]}...")
            return False

    # Check 4: Word count too low (likely error page)
    word_count = len(text.split())
    if word_count < 50:
        print(f"      ✗ Too few words ({word_count}): {url[:60]}...")
        return False

    # Check 5: Title is generic error
    error_titles = ["access denied", "error", "forbidden", "not found", "404", "403"]
    if any(error_title in title.lower() for error_title in error_titles):
        print(f"      ✗ Error title: {url[:60]}...")
        return False

    return True


def get_query_sentences(text: str, query: str) -> List[str]:
    """Extract sentences mentioning the query"""
    sentences = SENTENCE_REGEX.split(text)
    query_lower = query.lower()

    matches = []
    for s in sentences:
        if len(matches) >= 5:
            break
        if query_lower in s.lower() and len(s.strip()) > 20:
            matches.append(s.strip()[:512])

    return matches


def analyze_sentiment_batch(texts: List[str], queries: List[str]) -> List[Dict]:
    """Batch sentiment analysis"""
    if not SENTIMENT_AVAILABLE or not sentiment_classifier or not texts:
        return [{"label": "neutral", "score": 0.0, "mentions": 0} for _ in texts]

    results = []

    try:
        for text, query in zip(texts, queries):
            query_sents = get_query_sentences(text, query)

            if not query_sents:
                result = sentiment_classifier(text[:512])[0]
                results.append(
                    {
                        "label": result["label"].lower(),
                        "score": round(result["score"], 3),
                        "mentions": 0,
                    }
                )
                continue

            sentiments = sentiment_classifier(query_sents)

            pos = sum(1 for s in sentiments if s["label"].lower() == "positive")
            neg = sum(1 for s in sentiments if s["label"].lower() == "negative")
            neu = len(sentiments) - pos - neg

            if pos > neg and pos > neu:
                overall = "positive"
            elif neg > pos and neg > neu:
                overall = "negative"
            else:
                overall = "neutral"

            avg_conf = sum(s["score"] for s in sentiments) / len(sentiments)

            results.append(
                {
                    "label": overall,
                    "score": round(avg_conf, 3),
                    "mentions": len(query_sents),
                }
            )
    except Exception as e:
        print(f"Batch sentiment error: {e}")
        results = [{"label": "neutral", "score": 0.0, "mentions": 0} for _ in texts]

    return results


def call_newsdata_api_sync(client_index: int, params: Dict) -> Dict:
    """Call NewsData API"""
    try:
        client = api_clients[client_index]
        response = client.latest_api(**params)
        return response
    except Exception as e:
        print(f"    API error: {e}")
        return None


async def call_newsdata_api_async(client_index: int, params: Dict) -> Dict:
    """Async wrapper"""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        api_executor, call_newsdata_api_sync, client_index, params
    )
    return response


async def scrape_article_async(
    session: aiohttp.ClientSession, url: str, query: str
) -> Dict:
    """
    Async scraping with BETTER ERROR DETECTION
    """
    try:
        # Rotate user agents to avoid blocking
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        import random

        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=10), headers=headers
        ) as response:
            html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
                elem.decompose()

            text = ""
            title = ""

            if soup.title:
                title = soup.title.string or ""

            for selector in [
                "article",
                "main",
                ".article-body",
                ".entry-content",
                "#content",
            ]:
                content = soup.select_one(selector)
                if content:
                    text = content.get_text(separator=" ", strip=True)
                    if len(text) > 200:
                        break

            if len(text) < 200:
                paragraphs = soup.find_all("p")
                text = " ".join([p.get_text(strip=True) for p in paragraphs])

            if len(text) > 100:
                summary = text[:500] + "..." if len(text) > 500 else text

                img_tag = soup.find("meta", property="og:image")
                top_image = (
                    img_tag["content"] if img_tag and img_tag.get("content") else ""
                )

                return {
                    "success": True,
                    "full_text": text,
                    "title": title,
                    "summary": summary,
                    "top_image": top_image,
                    "word_count": len(text.split()),
                }

    except Exception as e:
        pass

    return {"success": False}


async def process_article_async(
    session: aiohttp.ClientSession, article_data: Dict, query: str, level: int
) -> Dict:
    """
    Process article with VALIDATION
    """
    url = article_data.get("link", "")
    if not url:
        return None

    content = await scrape_article_async(session, url, query)

    # NEW: Validate before accepting
    if not is_valid_article(content, url):
        return None

    return {
        "url": url,
        "title": content.get("title", article_data.get("title", "")),
        "full_text": content["full_text"],
        "summary": content["summary"],
        "keywords": "",
        "published_date": article_data.get("pubDate", ""),
        "authors": ", ".join(article_data.get("creator", []))
        if article_data.get("creator")
        else "",
        "source": article_data.get("source_name", ""),
        "top_image": content.get("top_image", article_data.get("image_url", "")),
        "word_count": content["word_count"],
        "search_query": query,
        "search_level": level,
        "sentiment": None,
        "sentiment_score": None,
        "query_mentions": None,
    }


async def scrape_level_async(
    session: aiohttp.ClientSession,
    articles: List[Dict],
    query: str,
    level: int,
    seen_urls: set,
) -> List[Dict]:
    """Scrape level"""
    tasks = []
    for article in articles:
        url = article.get("link", "")
        if url and url not in seen_urls:
            task = process_article_async(session, article, query, level)
            tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    level_articles = []
    for result in results:
        if result and not isinstance(result, Exception) and result:
            level_articles.append(result)
            seen_urls.add(result["url"])

    return level_articles


async def analyze_article_with_gemini(
    article: Dict[str, Any], company: str
) -> Dict[str, Any]:
    """
    Use Gemini LLM to analyze article for financial impact and relevance
    """
    if not GEMINI_AVAILABLE or not gemini_model:
        # Return defaults if Gemini not available
        return {
            "is_relevant": True,
            "relevance_reason": "Gemini not available",
            "financial_metrics": {
                "revenue_impact": "unknown",
                "stock_price_impact": "unknown",
                "confidence": "low",
            },
            "impact_assessment": "Unable to assess",
        }

    try:
        content = article.get("full_text", "")
        title = article.get("title", "")

        prompt = f"""You are a strict financial analyst AI. Analyze if this news is DIRECTLY RELEVANT to {company.upper()} company's business operations, financials, or stock price.

**Company:** {company.upper()}
**Title:** {title}
**Content:** {content[:3000]}

**RELEVANCE CRITERIA:**
- Article MUST be primarily about {company.upper()}
- NOT just a brief mention or peripheral reference
- NOT generic industry news unless {company.upper()} is also impacted
- NOT spam, press releases, or promotional content

**Required Output (JSON only):**
{{
    "is_relevant": true/false,
    "relevance_reason": "specific reason why relevant/irrelevant",
    "financial_metrics": {{
        "revenue_impact": "positive/negative/neutral/unknown",
        "stock_price_impact": "bullish/bearish/neutral/unknown",
        "confidence": "high/medium/low"
    }},
    "impact_assessment": "1 sentence on market impact"
}}

Be STRICT. If unsure, mark is_relevant as false. Respond with JSON only."""

        # Call Gemini asynchronously
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: gemini_model.generate_content(prompt)
        )

        if response and response.text:
            # Parse JSON response
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_text)
            return result

    except Exception as e:
        print(f"  Gemini analysis error: {e}")

    # Return defaults on error
    return {
        "is_relevant": True,
        "relevance_reason": "Analysis unavailable",
        "financial_metrics": {
            "revenue_impact": "unknown",
            "stock_price_impact": "unknown",
            "confidence": "low",
        },
        "impact_assessment": "Unable to assess",
    }


async def run_news_search(query: str, max_articles: int = 5):
    start_time = time.time()
    print(f"\n[SEARCH] {query} (target: {max_articles})")

    all_articles = []
    seen_urls = set()
    highest_level = None

    async with aiohttp.ClientSession() as session:
        for level in range(5):
            if len(all_articles) >= max_articles:
                break

            level_names = [
                "Title+Trusted",
                "Title+India",
                "Full+Multi",
                "Relaxed",
                "Global",
            ]

            remaining = max_articles - len(all_articles)
            print(f"  L{level} ({level_names[level]}) - need {remaining}...")

            params = get_search_params(query, level)
            query_type = "qInTitle" if "qInTitle" in params else "q"
            print(f"    Query: {params.get(query_type)}")

            api_start = time.time()
            response = await call_newsdata_api_async(0, params)
            api_time = time.time() - api_start

            if not response or "results" not in response:
                print(f"    No API response")
                continue

            articles = response["results"][: max_articles * 3]
            if not articles:
                print(f"    0 articles")
                continue

            print(f"    API: {api_time:.2f}s, got {len(articles)}")

            scrape_start = time.time()
            level_articles = await scrape_level_async(
                session, articles, query, level, seen_urls
            )
            scrape_time = time.time() - scrape_start

            if level_articles:
                all_articles.extend(level_articles)
                highest_level = level
                print(
                    f"    +{len(level_articles)} valid in {scrape_time:.2f}s (total: {len(all_articles)})"
                )
            else:
                print(f"    0 valid articles")

            if len(all_articles) >= max_articles:
                all_articles = all_articles[:max_articles]
                break

    if not all_articles:
        # Return empty list instead of raising exception
        return []

    print(f"  Sentiment...")
    sentiment_start = time.time()

    texts = [a["full_text"] for a in all_articles]
    queries = [query] * len(all_articles)
    sentiments = analyze_sentiment_batch(texts, queries)

    print(f"  Analyzing with Gemini...")
    gemini_start = time.time()

    # Analyze articles with Gemini for financial impact
    gemini_analyses = []
    for article in all_articles:
        analysis = await analyze_article_with_gemini(article, query)
        gemini_analyses.append(analysis)

    gemini_time = time.time() - gemini_start
    print(f"  Gemini analysis: {gemini_time:.2f}s")

    # Format articles to match SummarizedArticle model
    formatted_articles = []
    for idx, article in enumerate(all_articles):
        sentiment = sentiments[idx]
        gemini_analysis = gemini_analyses[idx]

        # Generate article_id from URL
        article_id = hashlib.md5(article["url"].encode()).hexdigest()

        # Determine liquidity impact from financial metrics
        revenue_impact = gemini_analysis.get("financial_metrics", {}).get(
            "revenue_impact", "unknown"
        )
        stock_impact = gemini_analysis.get("financial_metrics", {}).get(
            "stock_price_impact", "unknown"
        )

        # Map financial impacts to liquidity impact
        if stock_impact.lower() == "bullish":
            liquidity_impact = "HIGH_POSITIVE"
        elif stock_impact.lower() == "bearish":
            liquidity_impact = "HIGH_NEGATIVE"
        elif revenue_impact.lower() == "positive":
            liquidity_impact = "MEDIUM_POSITIVE"
        elif revenue_impact.lower() == "negative":
            liquidity_impact = "MEDIUM_NEGATIVE"
        else:
            liquidity_impact = "NEUTRAL"

        formatted_article = {
            "article_id": article_id,
            "title": article["title"],
            "url": article["url"],
            "company": query,
            "factor_type": "search_result",
            "published_at": article.get(
                "published_date", datetime.utcnow().isoformat()
            ),
            "source": article.get("source", "unknown"),
            # Enriched fields
            "content": article["full_text"],
            "content_length": article.get(
                "word_count", len(article["full_text"].split())
            ),
            "content_quality": "good" if article.get("word_count", 0) > 300 else "fair",
            "publisher_name": article.get("source", "unknown"),
            "author": article.get("authors", ""),
            "publisher_icon": None,
            "sentiment_label": sentiment["label"],
            "sentiment_score": sentiment["score"],
            "sentiment_confidence": "high"
            if sentiment["score"] > 0.7
            else "medium"
            if sentiment["score"] > 0.5
            else "low",
            "liquidity_impact": liquidity_impact,
            "critical_events": "",
            "decisions": "",
            "cluster_id": "",
            "enriched_at": datetime.utcnow().isoformat(),
            # LLM summary fields from Gemini
            "is_relevant": gemini_analysis.get("is_relevant", True),
            "relevance_reason": gemini_analysis.get("relevance_reason", "No analysis"),
            "summary": article.get("summary", ""),
            "key_points": [],
            "financial_metrics": gemini_analysis.get(
                "financial_metrics",
                {
                    "revenue_impact": "unknown",
                    "stock_price_impact": "unknown",
                    "confidence": "low",
                },
            ),
            "impact_assessment": gemini_analysis.get(
                "impact_assessment",
                f"News about {query} with {sentiment['label']} sentiment",
            ),
            "summarized_at": datetime.utcnow().isoformat(),
            "worker_id": "search_worker",
        }
        formatted_articles.append(formatted_article)

    total_time = time.time() - start_time

    print(f"  Total: {total_time:.2f}s")

    return formatted_articles


# if __name__ == "__main__":
# print(run_news_search("President Putin"))
