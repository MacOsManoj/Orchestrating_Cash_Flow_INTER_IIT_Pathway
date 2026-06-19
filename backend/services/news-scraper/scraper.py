"""
Lightweight News Scraper - Layer 1
- Fetches ONLY metadata (title, URL, date, source, company, factor_type)
- NO content fetching (deferred to Pathway pipeline)
- Multi-layer deduplication (Bloom Filter + Redis + MongoDB)
- Publishes to Kafka raw-news-feed topic
- Runs continuously every 5 minutes
"""

import asyncio
import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

import requests
from bs4 import BeautifulSoup
from pybloom_live import BloomFilter
import redis
from pymongo import MongoClient
from aiokafka import AIOKafkaProducer
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===========================
# Configuration
# ===========================

# Environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "news_db")
MONGODB_CONFIG_DB = os.getenv("MONGODB_CONFIG_DB", "config_db")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "180"))  # 3 minutes

# Company configuration
# Set to specific company code to test single company, or 'all' for all companies
TEST_COMPANY = os.getenv("TEST_COMPANY", "all")  # 'all' = scrape all companies

# Concurrency settings for parallelization
MAX_CONCURRENT_STRATEGIES = int(
    os.getenv("MAX_CONCURRENT_STRATEGIES", "10")
)  # Max parallel scrapes

# Kafka topics
KAFKA_TOPIC_RAW_NEWS = "raw-news-feed"

# Bloom filter configuration
BLOOM_FILTER_CAPACITY = 10_000_000  # 10M URLs
BLOOM_FILTER_ERROR_RATE = 0.0001  # 0.01% false positive rate

# Time range for news (1 day)
TIME_RANGE_DAYS = 1

SEARCH_STRATEGIES = {}

# ===========================
# Query Builder
# ===========================


def get_queries_for_company(config, company_code):
    """
    Get pre-built search queries for a company
    Returns dict of {theme: query}
    """
    companies = config["companies"]

    if company_code not in companies:
        return {}

    return companies[company_code]["queries"]


def load_search_strategies_from_db():
    """
    Load search strategies from MongoDB (config_db.search_config collection)
    Returns dict of {strategy_name: query_string}

    If TEST_COMPANY='all', loads strategies for ALL companies.
    Otherwise, loads only for the specified company.
    """
    try:
        config_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        config_db = config_client[MONGODB_CONFIG_DB]

        config = config_db.search_config.find_one({"_id": "search_config_v1"})

        if not config:
            logger.error("No search config found in database")
            return {}

        strategies = {}

        # Determine which companies to load
        if TEST_COMPANY.lower() == "all":
            # Load ALL companies
            companies_to_load = list(config["companies"].keys())
            logger.info(
                f"Loading strategies for ALL {len(companies_to_load)} companies"
            )
        else:
            # Load single company
            companies_to_load = (
                [TEST_COMPANY] if TEST_COMPANY in config["companies"] else []
            )
            if not companies_to_load:
                logger.error(f"Company '{TEST_COMPANY}' not found in config")

        # Build strategies for each company
        for company_code in companies_to_load:
            queries = get_queries_for_company(config, company_code)

            for theme, query in queries.items():
                strategy_name = f"{company_code}_{theme}"
                strategies[strategy_name] = query

        logger.info(
            f"Loaded {len(strategies)} search strategies for {len(companies_to_load)} companies"
        )

        config_client.close()

        return strategies

    except Exception as e:
        logger.error(f"Error loading search strategies from database: {e}")
        return {}


# ===========================
# Deduplication System
# ===========================


class DeduplicationManager:
    """
    Multi-layer deduplication system:
    Layer 1: Bloom Filter (probabilistic, fast)
    Layer 2: Redis Cache (exact match, 30-day TTL)
    Layer 3: MongoDB URL Registry (permanent, fallback)
    """

    def __init__(self, redis_client: redis.Redis, mongo_db):
        self.redis_client = redis_client
        self.mongo_db = mongo_db
        self.bloom_filter = None
        self.bloom_key = "url_bloom_filter"
        self.cache_prefix = "url_cache:"
        self.cache_ttl = 30 * 24 * 60 * 60  # 30 days

        self._initialize_bloom_filter()

    def _initialize_bloom_filter(self):
        """Initialize or load Bloom filter from Redis"""
        try:
            # Try to load existing bloom filter from Redis
            serialized = self.redis_client.get(self.bloom_key)
            if serialized and isinstance(serialized, bytes):
                import pickle

                self.bloom_filter = pickle.loads(serialized)
                logger.info(
                    f"Loaded existing Bloom filter from Redis (capacity: {BLOOM_FILTER_CAPACITY})"
                )
            else:
                # Create new bloom filter
                self.bloom_filter = BloomFilter(
                    capacity=BLOOM_FILTER_CAPACITY, error_rate=BLOOM_FILTER_ERROR_RATE
                )
                self._persist_bloom_filter()
                logger.info(
                    f"Created new Bloom filter (capacity: {BLOOM_FILTER_CAPACITY}, error rate: {BLOOM_FILTER_ERROR_RATE})"
                )
        except Exception as e:
            logger.error(f"Error initializing Bloom filter: {e}")
            # Create fresh bloom filter as fallback
            self.bloom_filter = BloomFilter(
                capacity=BLOOM_FILTER_CAPACITY, error_rate=BLOOM_FILTER_ERROR_RATE
            )

    def _persist_bloom_filter(self):
        """Persist Bloom filter to Redis"""
        try:
            import pickle

            serialized = pickle.dumps(self.bloom_filter)
            self.redis_client.set(self.bloom_key, serialized)
            logger.debug("Persisted Bloom filter to Redis")
        except Exception as e:
            logger.error(f"Error persisting Bloom filter: {e}")

    def _compute_url_hash(self, url: str) -> str:
        """Compute MD5 hash of URL"""
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def is_duplicate(self, url: str) -> bool:
        """
        Check if URL is duplicate using 3-layer deduplication
        Returns True if duplicate, False if new
        """
        url_hash = self._compute_url_hash(url)

        # Layer 1: Bloom Filter (fastest, probabilistic)
        if self.bloom_filter is None or url_hash not in self.bloom_filter:
            # Definitely new - add to all layers
            self._add_to_all_layers(url, url_hash)
            return False

        # Layer 2: Redis Cache (fast, exact)
        redis_key = f"{self.cache_prefix}{url_hash}"
        if self.redis_client.exists(redis_key):
            logger.debug(f"Duplicate detected in Redis cache: {url}")
            return True

        # Layer 3: MongoDB URL Registry (slower, permanent)
        url_registry = self.mongo_db["url_registry"]
        existing = url_registry.find_one({"url_hash": url_hash})
        if existing:
            logger.debug(f"Duplicate detected in MongoDB: {url}")
            # Backfill Redis cache
            self.redis_client.setex(redis_key, self.cache_ttl, existing["article_id"])
            return True

        # New URL - add to all layers
        self._add_to_all_layers(url, url_hash)
        return False

    def _add_to_all_layers(self, url: str, url_hash: str):
        """Add URL to all deduplication layers"""
        article_id = str(uuid.uuid4())

        # Layer 1: Bloom Filter
        if self.bloom_filter is not None:
            self.bloom_filter.add(url_hash)

        # Layer 2: Redis Cache
        redis_key = f"{self.cache_prefix}{url_hash}"
        self.redis_client.setex(redis_key, self.cache_ttl, article_id)

        # Layer 3: MongoDB URL Registry
        try:
            url_registry = self.mongo_db["url_registry"]
            url_registry.insert_one(
                {
                    "article_id": article_id,
                    "url": url,
                    "url_hash": url_hash,
                    "first_seen": datetime.utcnow(),
                    "scraped_at": datetime.utcnow(),
                }
            )
        except Exception as e:
            logger.error(f"Error adding URL to MongoDB registry: {e}")
        # Periodically persist bloom filter (every 100 additions)
        if self.bloom_filter is not None and len(self.bloom_filter) % 100 == 0:
            self._persist_bloom_filter()


# ===========================
# RSS Feed Fetching
# ===========================


def fetch_news_rss(query: str, days: int = TIME_RANGE_DAYS) -> List[Dict[str, Any]]:
    """
    Fetch news articles metadata from Google News RSS feed
    Returns ONLY metadata: title, URL, date, source
    """
    try:
        rss_url = (
            f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        )
        response = requests.get(rss_url, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content.decode("utf-8"), features="xml")
            articles = soup.find_all("item")

            cutoff_date = datetime.utcnow() - timedelta(days=days)
            parsed_articles = []

            for article in articles:
                try:
                    pub_date_str = article.pubDate.text if article.pubDate else None

                    # Parse date and filter
                    if pub_date_str:
                        try:
                            pub_date = datetime.strptime(
                                pub_date_str, "%a, %d %b %Y %H:%M:%S %Z"
                            )
                        except ValueError:
                            # Try alternative format
                            pub_date = datetime.strptime(
                                pub_date_str, "%a, %d %b %Y %H:%M:%S %z"
                            )

                        # Skip if older than cutoff
                        if pub_date < cutoff_date:
                            continue
                    else:
                        pub_date = datetime.utcnow()
                        pub_date_str = pub_date.isoformat()

                    title = article.title.text if article.title else "No Title"
                    link = article.link.text if article.link else None
                    source = (
                        article.source.text
                        if hasattr(article, "source") and article.source
                        else "Unknown"
                    )

                    if not link:
                        continue

                    parsed_articles.append(
                        {
                            "title": title,
                            "url": link,
                            "published_at": pub_date_str,
                            "source": source,
                        }
                    )

                except Exception as e:
                    logger.error(f"Error parsing article: {e}")
                    continue

            logger.info(
                f"Fetched {len(parsed_articles)} articles for query: {query[:50]}..."
            )
            return parsed_articles
        else:
            logger.error(f"Failed to fetch RSS feed: status {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching RSS feed: {e}")
        return []


# ===========================
# News Scraper
# ===========================


class NewsScraper:
    """
    Lightweight news scraper that fetches metadata only
    and publishes to Kafka after deduplication
    """

    def __init__(self):
        self.producer = None
        self.redis_client = None
        self.mongo_db = None
        self.dedup_manager = None

    async def initialize(self):
        """Initialize connections to Redis, MongoDB, and Kafka"""
        # Load search strategies from database
        global SEARCH_STRATEGIES
        SEARCH_STRATEGIES = load_search_strategies_from_db()

        if not SEARCH_STRATEGIES:
            logger.warning(
                "No search strategies loaded from database. Waiting for config to be seeded..."
            )
            logger.warning(
                "Run: docker exec -it news-scraper python /app/setup_search_config.py"
            )
            # Don't raise exception - let it retry on next cycle
            return

        # Connect to Redis
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=False,  # We'll handle encoding for bloom filter
                socket_connect_timeout=5,
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        # Connect to MongoDB
        try:
            mongo_client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=2,
                maxIdleTimeMS=300000,  # 5 minutes
                waitQueueTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
            )
            mongo_client.admin.command("ismaster")
            self.mongo_db = mongo_client[MONGODB_DB]

            # Create indexes
            self.mongo_db["url_registry"].create_index("url_hash", unique=True)
            self.mongo_db["url_registry"].create_index("scraped_at")

            logger.info(f"Connected to MongoDB at {MONGODB_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

        # Initialize deduplication manager
        self.dedup_manager = DeduplicationManager(self.redis_client, self.mongo_db)

        # Initialize Kafka producer
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type="gzip",
                acks="all",
                # Reduce buffering for real-time streaming
                linger_ms=10,  # Send after 10ms max, not waiting for full batch
                max_batch_size=1024,  # Smaller batches for faster delivery
            )
            await self.producer.start()
            logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    async def shutdown(self):
        """Cleanup connections"""
        if self.producer:
            await self.producer.stop()
        if self.redis_client:
            self.redis_client.close()
        logger.info("Shutdown complete")

    async def scrape_strategy(self, strategy_name: str, query: str) -> int:
        """
        Scrape news for a single strategy
        Returns: number of new articles sent to Kafka
        """
        logger.info(f"Scraping strategy: {strategy_name}")

        # Ensure deduplication manager is initialized
        if self.dedup_manager is None:
            logger.error("Deduplication manager not initialized")
            return 0

        # Ensure Kafka producer is initialized
        if self.producer is None:
            logger.error("Kafka producer not initialized")
            return 0

        # Extract company and factor_type from strategy name
        parts = strategy_name.split("_")
        company = parts[0]
        factor_type = parts[1] if len(parts) > 1 else "general"

        # Fetch RSS articles (synchronous)
        articles = fetch_news_rss(query)

        if not articles:
            logger.warning(f"No articles found for {strategy_name}")
            return 0

        # Filter out duplicates and publish new articles
        new_articles = 0
        duplicate_articles = 0

        for article in articles:
            url = article["url"]

            # Check if duplicate
            if self.dedup_manager.is_duplicate(url):
                duplicate_articles += 1
                continue

            # Create message for Kafka
            message = {
                "article_id": str(uuid.uuid4()),
                "title": article["title"],
                "url": url,
                "source": article["source"],
                "published_at": article["published_at"],
                "company": company,
                "factor_type": factor_type,
                "strategy": strategy_name,
                "scraped_at": datetime.utcnow().isoformat(),
            }

            # Send to Kafka
            try:
                await self.producer.send(KAFKA_TOPIC_RAW_NEWS, value=message)
                new_articles += 1
                logger.debug(f"Sent to Kafka: {article['title'][:50]}...")
            except Exception as e:
                logger.error(f"Error sending to Kafka: {e}")

        # Flush to ensure messages are sent immediately (real-time streaming)
        if new_articles > 0 and self.producer:
            await self.producer.flush()

        logger.info(
            f"Strategy {strategy_name}: "
            f"{new_articles} new articles sent, "
            f"{duplicate_articles} duplicates filtered"
        )

        return new_articles

    async def scrape_all_strategies(self):
        """
        Scrape all configured strategies with parallelization.
        Reloads config from DB every cycle to pick up changes.
        """
        start_time = time.time()

        # ✅ RELOAD CONFIG FROM DB EVERY CYCLE
        logger.info("Reloading search strategies from database...")
        global SEARCH_STRATEGIES
        SEARCH_STRATEGIES = load_search_strategies_from_db()

        if not SEARCH_STRATEGIES:
            logger.error("No search strategies loaded. Skipping cycle.")
            return 0

        logger.info("=" * 60)
        logger.info("Starting scraping cycle")
        logger.info(f"Total strategies: {len(SEARCH_STRATEGIES)}")
        logger.info(f"Max concurrent: {MAX_CONCURRENT_STRATEGIES}")
        logger.info("=" * 60)

        # Semaphore to limit concurrent scrapes
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_STRATEGIES)

        async def scrape_with_semaphore(strategy_name: str, query: str) -> int:
            """Scrape a strategy with semaphore-controlled concurrency"""
            async with semaphore:
                try:
                    return await self.scrape_strategy(strategy_name, query)
                except Exception as e:
                    logger.error(f"Error scraping {strategy_name}: {e}")
                    return 0

        # Create tasks for all strategies
        tasks = [
            scrape_with_semaphore(strategy_name, query)
            for strategy_name, query in SEARCH_STRATEGIES.items()
        ]

        # Run all tasks concurrently (limited by semaphore)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Sum up results
        total_new = sum(r for r in results if isinstance(r, int))
        errors = sum(1 for r in results if isinstance(r, Exception))

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"Scraping cycle complete!")
        logger.info(f"Total new articles: {total_new}")
        logger.info(f"Strategies processed: {len(results)}")
        if errors:
            logger.info(f"Errors: {errors}")
        logger.info(f"Time elapsed: {elapsed:.2f} seconds")
        logger.info("=" * 60)

        return total_new

    async def run_continuously(self):
        """Run scraper continuously with configured interval"""
        logger.info(f"Starting continuous scraping (interval: {SCRAPE_INTERVAL}s)")

        while True:
            try:
                # Reload strategies if they were empty during init
                global SEARCH_STRATEGIES
                if not SEARCH_STRATEGIES:
                    logger.info("No strategies loaded yet, reloading from database...")
                    SEARCH_STRATEGIES = load_search_strategies_from_db()
                    if not SEARCH_STRATEGIES:
                        logger.warning(
                            "Still no strategies. Waiting for config to be seeded..."
                        )
                        await asyncio.sleep(SCRAPE_INTERVAL)
                        continue

                await self.scrape_all_strategies()
            except Exception as e:
                logger.error(f"Error in scraping cycle: {e}")

            # Wait for next cycle
            logger.info(f"Sleeping for {SCRAPE_INTERVAL} seconds...")
            await asyncio.sleep(SCRAPE_INTERVAL)


# ===========================
# Main Execution
# ===========================


async def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("Lightweight News Scraper - Starting")
    logger.info("=" * 60)

    scraper = NewsScraper()

    try:
        await scraper.initialize()
        await scraper.run_continuously()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await scraper.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
