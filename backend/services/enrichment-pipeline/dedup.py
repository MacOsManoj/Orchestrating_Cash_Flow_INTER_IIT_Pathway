"""
Redis-based Deduplication Manager
- URL hash dedup (24hr TTL)
- Content hash dedup (24hr TTL)
- Fuzzy title matching with Levenshtein (24hr TTL)
- Cross-batch, cross-restart persistence
"""

import hashlib
import logging
import re
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import Levenshtein
import redis

logger = logging.getLogger(__name__)

# TTL for dedup keys (24 hours)
DEDUP_TTL_SECONDS = 24 * 60 * 60

# Max titles to scan for fuzzy matching per company/day
MAX_FUZZY_SCAN = 200

# Levenshtein similarity threshold (lowered to catch similar articles)
# 0.85 was too strict - similar articles scored 0.5-0.7
TITLE_SIMILARITY_THRESHOLD = 0.65


class DeduplicationManager:
    """
    Redis-based deduplication with 24-hour sliding window.

    Dedup layers:
    1. URL hash - exact URL match (after normalization)
    2. Content hash - identical content from different URLs
    3. Fuzzy title - similar titles using Levenshtein distance
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._verify_connection()

    def _verify_connection(self):
        """Verify Redis connection"""
        try:
            self.redis.ping()
            logger.info("Redis dedup manager connected")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    # ========================
    # URL Deduplication
    # ========================

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for consistent hashing"""
        parsed = urlparse(url)

        # Remove tracking parameters
        tracking_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "ref",
            "source",
            "fbclid",
            "gclid",
            "cid",
            "soc_src",
            "src",
            "ig_cid",
        }
        query_params = parse_qs(parsed.query)
        filtered_params = {
            k: v for k, v in query_params.items() if k.lower() not in tracking_params
        }

        return urlunparse(
            (
                parsed.scheme or "https",
                parsed.netloc.lower(),
                parsed.path.rstrip("/"),
                parsed.params,
                urlencode(filtered_params, doseq=True),
                "",  # Remove fragment
            )
        )

    @staticmethod
    def compute_url_hash(url: str) -> str:
        """Compute MD5 hash of normalized URL"""
        normalized = DeduplicationManager.normalize_url(url)
        return hashlib.md5(normalized.encode()).hexdigest()

    def is_url_duplicate(self, url: str) -> Tuple[bool, str]:
        """
        Check if URL is duplicate.
        Returns: (is_duplicate, url_hash)
        """
        url_hash = self.compute_url_hash(url)
        key = f"url:{url_hash}"

        if self.redis.exists(key):
            return True, url_hash

        # Mark as seen
        self.redis.setex(key, DEDUP_TTL_SECONDS, "1")
        return False, url_hash

    # ========================
    # Content Deduplication
    # ========================

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute hash of content (first 1000 chars)"""
        if not content or len(content) < 100:
            return ""
        return hashlib.md5(content[:1000].encode()).hexdigest()

    def is_content_duplicate(self, content: str) -> Tuple[bool, str]:
        """
        Check if content is duplicate.
        Returns: (is_duplicate, content_hash)
        """
        content_hash = self.compute_content_hash(content)
        if not content_hash:
            return False, ""

        key = f"content:{content_hash}"

        if self.redis.exists(key):
            return True, content_hash

        # Mark as seen
        self.redis.setex(key, DEDUP_TTL_SECONDS, "1")
        return False, content_hash

    # ========================
    # Fuzzy Title Deduplication
    # ========================

    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize title for fuzzy matching"""
        if not title:
            return ""
        title = title.lower()
        title = re.sub(r"[^\w\s]", " ", title)  # Remove punctuation
        title = re.sub(r"\s+", " ", title).strip()  # Normalize whitespace
        return title

    def is_title_duplicate(
        self, title: str, company: str, published_at: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if similar title exists using Levenshtein distance.
        Uses Redis sorted set for efficient time-based lookups.

        Returns: (is_duplicate, matching_cluster_id or None)
        """
        normalized = self.normalize_title(title)
        if not normalized or len(normalized) < 10:
            return False, None

        # Get day from published_at for grouping
        day = (
            published_at[:10]
            if published_at
            else datetime.utcnow().strftime("%Y-%m-%d")
        )

        # Key format: titles:{company}:{day}
        key = f"titles:{company}:{day}"

        # Get recent titles for this company/day
        # Format: score=timestamp, member="{normalized_title}|{cluster_id}"
        recent_titles = self.redis.zrange(key, 0, MAX_FUZZY_SCAN - 1, withscores=False)

        # Check similarity against each
        for stored in recent_titles:
            if isinstance(stored, bytes):
                stored = stored.decode()

            parts = stored.rsplit("|", 1)
            if len(parts) != 2:
                continue

            stored_title, cluster_id = parts

            # Levenshtein similarity check
            similarity = Levenshtein.ratio(normalized, stored_title)
            if similarity >= TITLE_SIMILARITY_THRESHOLD:
                logger.debug(
                    f"Fuzzy match found: {similarity:.2f} - '{title[:50]}' ~ '{stored_title[:50]}'"
                )
                return True, cluster_id

        return False, None

    def add_title(self, title: str, company: str, published_at: str, cluster_id: str):
        """Add title to fuzzy matching index"""
        normalized = self.normalize_title(title)
        if not normalized or len(normalized) < 10:
            return

        day = (
            published_at[:10]
            if published_at
            else datetime.utcnow().strftime("%Y-%m-%d")
        )
        key = f"titles:{company}:{day}"

        # Store with timestamp as score
        timestamp = datetime.utcnow().timestamp()
        member = f"{normalized}|{cluster_id}"

        self.redis.zadd(key, {member: timestamp})
        self.redis.expire(key, DEDUP_TTL_SECONDS)

    # ========================
    # Combined Check
    # ========================

    def check_all(
        self, url: str, title: str, content: str, company: str, published_at: str
    ) -> Tuple[bool, str, str, Optional[str]]:
        """
        Run all dedup checks.

        Returns: (is_duplicate, url_hash, content_hash, existing_cluster_id)

        If is_duplicate=True, one of the dedup layers caught it.
        existing_cluster_id is set if fuzzy title matched an existing story.
        """
        # Layer 1: URL hash
        url_dup, url_hash = self.is_url_duplicate(url)
        if url_dup:
            logger.debug(f"URL duplicate: {url[:60]}")
            return True, url_hash, "", None

        # Layer 2: Content hash (only if we have content)
        content_hash = ""
        if content and len(content) >= 100:
            content_dup, content_hash = self.is_content_duplicate(content)
            if content_dup:
                logger.debug(f"Content duplicate: {url[:60]}")
                return True, url_hash, content_hash, None

        # Layer 3: Fuzzy title matching
        title_dup, existing_cluster = self.is_title_duplicate(
            title, company, published_at
        )
        if title_dup:
            logger.debug(f"Title duplicate (cluster {existing_cluster}): {title[:60]}")
            return True, url_hash, content_hash, existing_cluster

        return False, url_hash, content_hash, None

    def register_article(
        self,
        url_hash: str,
        content_hash: str,
        title: str,
        company: str,
        published_at: str,
        cluster_id: str,
    ):
        """
        Register a new article in dedup indexes.
        Call this AFTER processing a non-duplicate article.
        """
        # URL hash already registered in is_url_duplicate
        # Content hash already registered in is_content_duplicate

        # Add title to fuzzy index
        self.add_title(title, company, published_at, cluster_id)
