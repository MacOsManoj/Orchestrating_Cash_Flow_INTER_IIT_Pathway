"""
Article Content Fetcher
- 3-tier fetching: googlenewsdecoder → aiohttp → Playwright
- Extracts: content, metadata, publisher info
- Connection pooling for performance
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "5000"))
MAX_CONCURRENT_FETCHES = int(os.getenv("MAX_CONCURRENT_FETCHES", "20"))
FETCH_DELAY = float(os.getenv("FETCH_DELAY", "0.1"))

# Google News decoder (optional)
try:
    from googlenewsdecoder import gnewsdecoder

    GNEWS_AVAILABLE = True
except ImportError:
    GNEWS_AVAILABLE = False
    logger.warning("googlenewsdecoder not installed")

# Thread pool for blocking decoder
_gnews_workers = int(os.getenv("GNEWS_DECODER_WORKERS", "5"))
_gnews_executor = concurrent.futures.ThreadPoolExecutor(max_workers=_gnews_workers)

# Shared aiohttp connector
_connector: aiohttp.TCPConnector | None = None


def _get_connector() -> aiohttp.TCPConnector:
    """Get shared connection pool"""
    global _connector
    if _connector is None or _connector.closed:
        _connector = aiohttp.TCPConnector(
            limit=MAX_CONCURRENT_FETCHES,
            limit_per_host=5,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
    return _connector


async def fetch_article(url: str) -> Dict[str, Any]:
    """
    Fetch article content with 3-tier approach:
    1. Google News URLs: Try decoder first
    2. Try aiohttp (fast, for static sites)
    3. Fallback to Playwright (for JS-heavy sites)

    Returns: {
        'content', 'final_url', 'publisher_name',
        'author', 'published_date', 'publisher_icon'
    }
    """
    result = {
        "content": None,
        "final_url": url,
        "publisher_name": None,
        "author": None,
        "published_date": None,
        "publisher_icon": None,
    }

    try:
        is_google_news = "news.google" in urlparse(url).netloc

        if is_google_news:
            result = await _fetch_google_news(url, result)
        else:
            result = await _fetch_direct(url, result)

    except Exception as e:
        logger.error(f"Fetch failed for {url[:60]}: {e}")

    return result


async def _fetch_google_news(url: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Google News URLs"""
    decoded_url = None

    # Try decoder first (fast, no browser)
    if GNEWS_AVAILABLE:
        try:
            loop = asyncio.get_event_loop()
            decoded = await loop.run_in_executor(
                _gnews_executor, lambda: gnewsdecoder(url, interval=1)
            )
            if decoded.get("status") and decoded.get("decoded_url"):
                decoded_url = decoded["decoded_url"]
                logger.info(f"✓ Decoded Google News URL: {decoded_url[:80]}")
            else:
                logger.warning(
                    f"✗ Decoder failed for {url}, status={decoded.get('status')}"
                )
        except Exception as e:
            logger.warning(f"✗ Decoder exception: {e}")
    else:
        logger.warning("googlenewsdecoder not available")

    if decoded_url:
        result["final_url"] = decoded_url
        result = await _fetch_with_aiohttp(decoded_url, result)

        # If good content, done
        if result.get("content") and len(result.get("content", "")) > 200:
            logger.info(
                f"✓ Got content via aiohttp: {len(result.get('content', ''))} chars"
            )
            return result

        # Otherwise try Playwright
        logger.info(f"Insufficient content from aiohttp, trying Playwright...")
        return await _fetch_with_playwright(decoded_url, result)

    # Decoder failed, use full Playwright flow
    logger.info(f"Using Playwright to resolve Google News URL: {url[:80]}")
    return await _fetch_google_news_playwright(url, result)


async def _fetch_direct(url: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch non-Google-News URL"""
    result = await _fetch_with_aiohttp(url, result)

    if result.get("content") and len(result.get("content", "")) > 200:
        return result

    # Fallback to Playwright for JS-heavy sites
    return await _fetch_with_playwright(url, result)


async def _fetch_with_aiohttp(url: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Fast fetch with aiohttp"""
    try:
        if FETCH_DELAY > 0:
            await asyncio.sleep(FETCH_DELAY)

        connector = _get_connector()
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(
            connector=connector, connector_owner=False
        ) as session:
            async with session.get(url, timeout=timeout) as resp:
                result["final_url"] = str(resp.url)

                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "lxml")
                    _extract_metadata(soup, result)
                    _extract_content(soup, result)
                    logger.debug(f"aiohttp success: {url[:60]}")

    except asyncio.TimeoutError:
        logger.debug(f"aiohttp timeout: {url[:60]}")
    except Exception as e:
        logger.debug(f"aiohttp error: {e}")

    return result


async def _fetch_with_playwright(url: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch JS-heavy site with Playwright"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()

            await page.goto(
                url, timeout=REQUEST_TIMEOUT * 1000, wait_until="domcontentloaded"
            )
            await asyncio.sleep(2)

            html = await page.content()
            result["final_url"] = page.url

            soup = BeautifulSoup(html, "lxml")
            _extract_metadata(soup, result)
            _extract_content(soup, result)

            await browser.close()
            logger.debug(f"Playwright success: {url[:60]}")

    except Exception as e:
        logger.warning(f"Playwright failed: {url[:60]} - {e}")

    return result


async def _fetch_google_news_playwright(
    url: str, result: Dict[str, Any]
) -> Dict[str, Any]:
    """Full Playwright flow for Google News when decoder fails"""
    try:
        logger.info(f"🎭 Starting Playwright for Google News: {url[:80]}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                },
                java_script_enabled=True,
            )

            # Override navigator.webdriver to hide automation
            await context.add_init_script(
                """Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"""
            )
            page = await context.new_page()

            # Navigate with wait for networkidle to ensure redirects complete
            try:
                await page.goto(
                    url, timeout=REQUEST_TIMEOUT * 1000, wait_until="networkidle"
                )
            except Exception:
                # Fallback to domcontentloaded if networkidle times out
                await page.goto(
                    url, timeout=REQUEST_TIMEOUT * 1000, wait_until="domcontentloaded"
                )

            await asyncio.sleep(2)

            current_url = page.url
            logger.info(f"🎭 After navigation: {current_url[:80]}")

            # If still on Google News, try to find and click the article link
            if "news.google" in current_url:
                logger.info(
                    "🎭 Still on Google News, trying to extract/click article link..."
                )

                # Try multiple methods to get the external URL
                external_url = None

                # Method 1: Try to click the main article element and wait for navigation
                try:
                    logger.info("🎭 Attempting to click article to trigger redirect...")
                    # Find and click the main article link
                    article_link = await page.query_selector(
                        'article a, [role="article"] a, c-wiz a'
                    )
                    if article_link:
                        async with page.expect_navigation(timeout=10000):
                            await article_link.click()
                        await asyncio.sleep(2)
                        current_url = page.url
                        if "news.google" not in current_url:
                            logger.info(
                                f"🎭 Successfully navigated via click: {current_url[:80]}"
                            )
                except Exception as e:
                    logger.debug(f"Click method failed: {e}")

                # Method 2: Extract from page source if still on Google News
                if "news.google" in current_url:
                    external_url = await _extract_google_news_link(page)
                    if external_url:
                        try:
                            logger.info(
                                f"🎭 Found external URL, navigating: {external_url[:80]}"
                            )
                            await page.goto(
                                external_url,
                                timeout=REQUEST_TIMEOUT * 1000,
                                wait_until="domcontentloaded",
                            )
                            await asyncio.sleep(1)
                            current_url = page.url
                            logger.info(f"🎭 Navigated to: {current_url[:80]}")
                        except Exception as e:
                            logger.warning(
                                f"🎭 Failed to navigate to external URL: {e}"
                            )
                    else:
                        logger.warning(
                            "🎭 Could not extract external URL, staying on Google News page"
                        )

            html = await page.content()
            result["final_url"] = current_url

            soup = BeautifulSoup(html, "lxml")
            _extract_metadata(soup, result)
            _extract_content(soup, result)

            await browser.close()

            content_len = len(result.get("content", ""))
            logger.info(
                f"🎭 Playwright done: {content_len} chars from {current_url[:60]}"
            )

    except Exception as e:
        logger.error(f"🎭 Playwright failed for Google News: {url[:60]} - {e}")

    return result


async def _extract_google_news_link(page) -> str | None:
    """Extract external article link from Google News page"""
    try:
        urls = await page.evaluate("""() => {
            const out = [];
            
            // Check meta tags
            const can = document.querySelector('link[rel="canonical"]');
            if (can?.href && !can.href.includes('google')) out.push(can.href);
            const og = document.querySelector('meta[property="og:url"]');
            if (og?.content && !og.content.includes('google')) out.push(og.content);
            
            // Check JSON-LD structured data
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const script of scripts) {
                try {
                    const data = JSON.parse(script.textContent || '{}');
                    if (data.url && !data.url.includes('google')) out.push(data.url);
                    if (data.mainEntityOfPage?.url && !data.mainEntityOfPage.url.includes('google')) {
                        out.push(data.mainEntityOfPage.url);
                    }
                } catch(e) {}
            }
            
            // Check all anchors - be more aggressive
            const links = Array.from(document.querySelectorAll('a[href]'));
            for (const a of links) {
                const href = a.href || a.getAttribute('href') || '';
                if (href.startsWith('http') && 
                    !href.includes('google.com') && 
                    !href.includes('gstatic.com') &&
                    !href.includes('youtube.com')) {
                    out.push(href);
                }
            }
            
            return out;
        }""")

        # Filter and return first valid URL
        for url in urls:
            if url and len(url) > 10:  # Basic validation
                logger.debug(f"Found candidate URL: {url[:80]}")
                return url
        return None
    except Exception as e:
        logger.debug(f"URL extraction error: {e}")
        return None


def _extract_metadata(soup: BeautifulSoup, result: Dict[str, Any]):
    """Extract article metadata"""
    try:
        # Publisher name
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            result["publisher_name"] = og_site["content"].strip()
        else:
            result["publisher_name"] = urlparse(result["final_url"]).netloc.replace(
                "www.", ""
            )

        # Author
        for selector in [
            ("meta", {"property": "article:author"}),
            ("meta", {"name": "author"}),
        ]:
            tag = soup.find(*selector)
            if tag and tag.get("content"):
                result["author"] = tag["content"].strip()
                break

        # Published date
        og_time = soup.find("meta", property="article:published_time")
        if og_time and og_time.get("content"):
            try:
                dt = datetime.fromisoformat(og_time["content"].replace("Z", "+00:00"))
                result["published_date"] = dt.isoformat()
            except Exception:
                result["published_date"] = og_time["content"]
        else:
            # Try JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "{}")
                    if isinstance(data, dict) and data.get("datePublished"):
                        result["published_date"] = data["datePublished"]
                        break
                except Exception:
                    continue

        # Favicon
        icon_selectors = [
            'link[rel="apple-touch-icon"]',
            'link[rel="icon"][sizes="32x32"]',
            'link[rel="icon"]',
            'link[rel="shortcut icon"]',
        ]
        for selector in icon_selectors:
            link = soup.select_one(selector)
            if link and link.get("href"):
                href = link["href"]
                if not href.startswith("http"):
                    base = urlparse(result["final_url"])
                    if href.startswith("//"):
                        href = f"{base.scheme}:{href}"
                    elif href.startswith("/"):
                        href = f"{base.scheme}://{base.netloc}{href}"
                result["publisher_icon"] = href
                break

        if not result["publisher_icon"]:
            base = urlparse(result["final_url"])
            result["publisher_icon"] = f"{base.scheme}://{base.netloc}/favicon.ico"

    except Exception as e:
        logger.debug(f"Metadata extraction error: {e}")


def _extract_content(soup: BeautifulSoup, result: Dict[str, Any]):
    """Extract article content"""
    try:
        # Remove noise
        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "iframe", "form"]
        ):
            tag.decompose()

        # Try article selectors
        selectors = [
            "article",
            ".article-content",
            ".post-content",
            ".entry-content",
            '[itemprop="articleBody"]',
            ".story-content",
            "main",
        ]

        content = None
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                content = el.get_text(separator=" ", strip=True)
                if content and len(content) > 100:
                    break
                content = None

        # Fallback to body
        if not content:
            body = soup.find("body")
            if body:
                content = body.get_text(separator=" ", strip=True)

        if content:
            content = _clean_text(content)
            result["content"] = content[:MAX_CONTENT_LENGTH]

    except Exception as e:
        logger.debug(f"Content extraction error: {e}")


def _clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)  # Normalize whitespace
    text = re.sub(r"[^\w\s\.\,\!\?\-\:\$\%]", "", text)  # Keep basic punctuation
    text = re.sub(r"http\S+|www\S+", "", text)  # Remove URLs
    return text.strip()
