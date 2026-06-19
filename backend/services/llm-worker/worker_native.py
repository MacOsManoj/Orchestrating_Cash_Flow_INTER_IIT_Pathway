"""
LLM Summarization Worker - Optimized Async Pool
- Decouples Kafka consumption from LLM processing
- Uses internal asyncio.Queue for buffering
- Runs parallel LLM workers for high throughput
- Handles Rate Limiting
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from confluent_kafka import Producer as ConfluentProducer
import google.generativeai as genai
from pymongo import MongoClient
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===========================
# Configuration
# ===========================

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")

# Confluent Kafka Configuration (for summarized news output)
CONFLUENT_BOOTSTRAP_SERVERS = os.getenv(
    "CONFLUENT_BOOTSTRAP_SERVERS", "pkc-619z3.us-east1.gcp.confluent.cloud:9092"
)
CONFLUENT_SECURITY_PROTOCOL = os.getenv("CONFLUENT_SECURITY_PROTOCOL", "SASL_SSL")
CONFLUENT_SASL_MECHANISM = os.getenv("CONFLUENT_SASL_MECHANISM", "PLAIN")
CONFLUENT_SASL_USERNAME = os.getenv("CONFLUENT_SASL_USERNAME", "BOPS3YOPIRNNHBL4")
CONFLUENT_SASL_PASSWORD = os.getenv(
    "CONFLUENT_SASL_PASSWORD",
    "cfltkhIZNB7XoHOvbvVFbtDiPfdNw6+IPVi2D1I76tRy70E+2D1B9b0JqrEsdEsg",
)

# Concurrency & Limits
# Adjust based on your Gemini Tier (Free: 15 RPM, Paid: much higher)
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "60"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))

KAFKA_TOPIC_ENRICHED_NEWS = "enriched-news"
KAFKA_TOPIC_SUMMARIZED_NEWS = "summarized-news"
KAFKA_GROUP_ID = "llm-summarization-worker"
GEMINI_MODEL = "gemini-2.5-flash-lite"
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "news_db")
MONGODB_COLLECTION_SUMMARIES = "summarize"

# ===========================
# Gemini Summarizer
# ===========================


class GeminiSummarizer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self._initialize()

    def _initialize(self):
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
            logger.info(f"Gemini API initialized: {GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            raise

    async def summarize(self, article: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = self._create_prompt(article)

            # KEY CHANGE: Use native async method
            response = await self.model.generate_content_async(prompt)

            if not response or not response.text:
                return self._create_fallback_summary(article)

            return self._parse_response(response.text, article)

        except Exception as e:
            logger.error(f"Error in Gemini summarization: {e}")
            return self._create_fallback_summary(article)

    def _create_prompt(self, article: Dict[str, Any]) -> str:
        content = article.get("content", "")
        content_quality = article.get("content_quality", "unknown")

        # For poor content quality, warn the LLM
        quality_warning = ""
        if content_quality == "poor" or len(content) < 200:
            quality_warning = "\n**⚠️ WARNING:** Content fetch may have failed - analyze title carefully."

        return f"""You are a strict financial analyst AI. First determine if this news is DIRECTLY RELEVANT to {article.get("company", "").upper()} company's business operations, financials, or stock price.{quality_warning}

**Company:** {article.get("company", "").upper()}
**Title:** {article.get("title", "")}
**Content:** {content[:4000]}
**Factor Type:** {article.get("factor_type", "unknown")}

**RELEVANCE CRITERIA:**
- Article MUST be primarily about {article.get("company", "").upper()}
- NOT just a brief mention or peripheral reference
- NOT generic industry news unless {article.get("company", "").upper()} is also impacted
- NOT spam, press releases, or promotional content

**Required Output (JSON only):**
{{
    "is_relevant": true/false,
    "relevance_reason": "specific reason why relevant/irrelevant",
    "summary": "2-3 sentence summary (or 'Not relevant to {article.get("company", "")}' if irrelevant)",
    "key_points": ["Point 1", "Point 2"] or [],
    "financial_metrics": {{
        "revenue_impact": "positive/negative/neutral/unknown",
        "stock_price_impact": "bullish/bearish/neutral/unknown",
        "confidence": "high/medium/low"
    }},
    "impact_assessment": "1 sentence on market impact (or 'Not relevant' if irrelevant)"
}}

Be STRICT. If unsure, mark is_relevant as false. Respond with JSON only."""

    def _parse_response(
        self, response_text: str, article: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            # Clean markdown code blocks if present
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_text)
            return result
        except Exception:
            return self._create_fallback_summary(article)

    def _create_fallback_summary(self, article: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "summary": "Processing failed",
            "key_points": [],
            "financial_metrics": {},
            "impact_assessment": "Error",
        }


# ===========================
# Async Worker Pool
# ===========================


class LLMWorker:
    def __init__(self):
        self.consumer = None
        self.producer = None
        self.confluent_producer = None  # Separate producer for Confluent
        self.summarizer = None
        self.mongo_client = None
        self.summaries_collection = None

        # Internal Queue for parallel processing
        self.queue = asyncio.Queue(maxsize=100)
        self.active_workers = []

        # Rate Limiting
        self.rate_limiter = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.request_interval = 60.0 / RATE_LIMIT_RPM  # Time between requests

    async def initialize(self):
        self.summarizer = GeminiSummarizer(GEMINI_API_KEY)

        # MongoDB
        self.mongo_client = await asyncio.to_thread(MongoClient, MONGODB_URI)
        db = self.mongo_client[MONGODB_DB]
        self.summaries_collection = db[MONGODB_COLLECTION_SUMMARIES]
        await asyncio.to_thread(
            self.summaries_collection.create_index, "article_id", unique=True
        )

        # Kafka Consumer - Allow batching for speed
        self.consumer = AIOKafkaConsumer(
            KAFKA_TOPIC_ENRICHED_NEWS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            max_poll_records=20,  # Fetch more records at once
        )
        await self.consumer.start()

        # Local Kafka Producer (kept for other uses if needed)
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            compression_type="gzip",
        )
        await self.producer.start()

        # Confluent Kafka Producer (for summarized news)
        confluent_conf = {
            "bootstrap.servers": CONFLUENT_BOOTSTRAP_SERVERS,
            "security.protocol": CONFLUENT_SECURITY_PROTOCOL,
            "sasl.mechanism": CONFLUENT_SASL_MECHANISM,
            "sasl.username": CONFLUENT_SASL_USERNAME,
            "sasl.password": CONFLUENT_SASL_PASSWORD,
            "client.id": socket.gethostname(),
        }
        self.confluent_producer = ConfluentProducer(confluent_conf)

        logger.info(
            f"Initialized. Workers: {MAX_CONCURRENT_REQUESTS}, RPM Limit: {RATE_LIMIT_RPM}"
        )
        logger.info(f"Confluent Kafka configured: {CONFLUENT_BOOTSTRAP_SERVERS}")

    async def processing_worker(self, worker_id: int):
        """Continuous worker loop that pulls from queue"""
        logger.info(f"Worker {worker_id} started")

        while True:
            # Get message from queue
            msg = await self.queue.get()

            try:
                article = msg.value
                article_id = article.get("article_id")

                # Skip articles with extremely poor content (likely scraping failures)
                content = article.get("content", "")
                if len(content) < 100:
                    logger.warning(
                        f"⊘ SKIPPING - content too short ({len(content)} chars): {article.get('company')} - {article.get('title')[:40]}..."
                    )
                    continue

                # Rate Limiting Logic
                async with self.rate_limiter:
                    # Enforce minimum interval to respect RPM
                    start_time = time.time()

                    # 1. Summarize (The Heavy Lifting)
                    logger.info(
                        f"Worker {worker_id} processing: {article.get('title')[:30]}..."
                    )
                    llm_summary = await self.summarizer.summarize(article)

                    # 2. Check relevance - skip irrelevant articles
                    is_relevant = llm_summary.get("is_relevant", True)
                    relevance_reason = llm_summary.get(
                        "relevance_reason", "No reason provided"
                    )

                    if not is_relevant:
                        elapsed = time.time() - start_time
                        logger.warning(
                            f"⊘ IRRELEVANT (Worker {worker_id}): {article.get('company')} - {article.get('title')[:40]}... | Reason: {relevance_reason} ({elapsed:.1f}s)"
                        )
                        continue  # Skip this article, don't store or publish

                    # 3. Prepare Result (only for relevant articles)
                    summarized = {
                        "_id": article_id,
                        **article,
                        **llm_summary,
                        "summarized_at": datetime.utcnow().isoformat(),
                        "worker_id": f"{WORKER_ID}_{worker_id}",
                    }

                    # 4. DB Write (Async wrapper)
                    await asyncio.to_thread(
                        self.summaries_collection.update_one,
                        {"_id": article_id},
                        {"$set": summarized},
                        upsert=True,
                    )

                    # 5. Send to Confluent Kafka (summarized news)
                    self.confluent_producer.produce(
                        KAFKA_TOPIC_SUMMARIZED_NEWS,
                        value=json.dumps(summarized).encode("utf-8"),
                    )
                    self.confluent_producer.poll(0)  # Trigger delivery callbacks
                    logger.info(
                        f"✓ Sent to Confluent: {article.get('company')} - {article.get('title')[:40]}..."
                    )

                    # Enforce RPM wait if needed
                    elapsed = time.time() - start_time
                    if elapsed < self.request_interval:
                        await asyncio.sleep(self.request_interval - elapsed)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
            finally:
                self.queue.task_done()

    async def run(self):
        """Main loop: Fills the queue from Kafka"""

        # Start the worker pool
        self.active_workers = [
            asyncio.create_task(self.processing_worker(i))
            for i in range(MAX_CONCURRENT_REQUESTS)
        ]

        try:
            # High-speed consumer loop
            async for message in self.consumer:
                # This will block if queue is full (backpressure), preventing memory overflow
                await self.queue.put(message)

        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
            raise

    async def shutdown(self):
        # Cancel workers
        for task in self.active_workers:
            task.cancel()

        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.confluent_producer:
            self.confluent_producer.flush()  # Ensure all messages are delivered
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("Shutdown complete")


async def main():
    worker = LLMWorker()
    try:
        await worker.initialize()
        await worker.run()
    except KeyboardInterrupt:
        pass
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
