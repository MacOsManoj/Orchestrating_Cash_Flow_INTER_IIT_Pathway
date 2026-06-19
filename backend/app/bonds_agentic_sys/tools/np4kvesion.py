"""
OPTIMIZED TOOL: NEWSPAPER4K (Threaded)
Strategy:
1. Fire 3 API Keys at once (Levels 0, 1, 2).
2. Deduplicate URLs.
3. Scrape using ThreadPoolExecutor (to handle blocking code).
"""

import asyncio
import functools
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from newsdataapi import NewsDataApiClient
from newspaper import Config, Article

# --- CONFIGURATION ---
API_KEYS = [
    "pub_8f5bd39159864856a0542878a7da4cb1",
    "pub_3c1c7125cf614b128e9ed2ec675e8658",
    "pub_531a2ce4c76a4b8e97b9af40046fd54c",
]

api_clients = [NewsDataApiClient(apikey=key) for key in API_KEYS]
api_executor = ThreadPoolExecutor(max_workers=len(API_KEYS))
scrape_executor = ThreadPoolExecutor(max_workers=20)  # 20 threads for scraping

TRUSTED_DOMAINS = ",".join(
    [
        "moneycontrol.com",
        "economictimes.indiatimes.com",
        "livemint.com",
        "business-standard.com",
        "financialexpress.com",
    ]
)


def get_search_params(query: str, level: int) -> Dict:
    parts = query.strip().split()
    advanced = (
        parts[0]
        if len(parts) == 1 and level <= 2
        else (" AND ".join(parts) if level <= 2 else " OR ".join(parts))
    )
    params = {"language": "en"}
    if level == 0:
        params.update(
            {
                "qInTitle": advanced,
                "country": "in",
                "category": "business",
                "domainurl": TRUSTED_DOMAINS,
            }
        )
    elif level == 1:
        params.update({"qInTitle": advanced, "country": "in", "category": "business"})
    else:
        params.update({"q": advanced, "category": "business"})
    return params


async def fetch_api_level(client_idx: int, level: int, query: str):
    loop = asyncio.get_event_loop()
    params = get_search_params(query, level)
    try:
        func = functools.partial(api_clients[client_idx].latest_api, **params)
        return await loop.run_in_executor(api_executor, func)
    except Exception:
        return None


def scrape_newspaper_sync(article_metadata: Dict) -> Dict:
    """Sync Scraper running in Thread"""
    url = article_metadata.get("link")
    if not url:
        return None

    try:
        config = Config()
        config.browser_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        )

        # SPEED OPTIMIZATIONS
        config.fetch_images = False  # Disable images (Critical)
        config.memoize_articles = False
        config.request_timeout = 6

        article = Article(url, config=config)
        article.download()
        article.parse()

        text = article.text
        if not text or len(text) < 100:
            return None

        return {
            "source": article_metadata.get("source_name"),
            "url": url,
            # Use Newspaper date if found, else API date
            "date": str(article.publish_date)
            if article.publish_date
            else article_metadata.get("pubDate"),
            "content": text,
            "word_count": len(text.split()),
        }
    except:
        return None


async def search_news_newspaper(query: str, target_count: int = 5):
    start_total = time.perf_counter()

    # 1. PARALLEL API CALLS
    api_tasks = []
    loop = asyncio.get_event_loop()

    for i in range(min(3, len(API_KEYS))):
        api_tasks.append(fetch_api_level(client_idx=i, level=i, query=query))

    api_results = await asyncio.gather(*api_tasks)

    # 2. DEDUPLICATE
    unique_candidates = {}
    for batch in api_results:
        if batch and "results" in batch:
            for art in batch["results"]:
                if art.get("link") and art.get("link") not in unique_candidates:
                    unique_candidates[art["link"]] = art

    candidates = list(unique_candidates.values())[: target_count * 2]

    # 3. PARALLEL SCRAPING (Thread Offloading)
    scrape_tasks = []
    for art in candidates:
        scrape_tasks.append(
            loop.run_in_executor(scrape_executor, scrape_newspaper_sync, art)
        )

    results = await asyncio.gather(*scrape_tasks)

    # 4. FILTER
    valid_articles = [a for a in results if a]

    return {
        "count": len(valid_articles[:target_count]),
        "time": round(time.perf_counter() - start_total, 2),
        "articles": valid_articles[:target_count],
    }
