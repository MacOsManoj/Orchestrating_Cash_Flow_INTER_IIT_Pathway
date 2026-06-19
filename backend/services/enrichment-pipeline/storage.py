"""
MongoDB Storage Handler
- Stores enriched articles
- Manages story clusters
- Thread-safe operations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection

logger = logging.getLogger(__name__)


class StorageHandler:
    """MongoDB storage for articles and clusters"""

    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(
            uri,
            maxPoolSize=10,
            minPoolSize=2,
            maxIdleTimeMS=300000,
            waitQueueTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=30000,
        )
        self.db = self.client[db_name]
        self._create_indexes()
        logger.info(f"MongoDB storage connected: {db_name}")

    def _create_indexes(self):
        """Create required indexes"""
        # Articles collection
        articles = self.db["enriched_articles"]
        articles.create_index([("company", 1), ("published_at", -1)])
        articles.create_index("url", unique=True)
        articles.create_index("url_hash")
        articles.create_index("content_hash")
        articles.create_index("cluster_id")
        articles.create_index("factor_type")
        articles.create_index("sentiment.label")
        articles.create_index("publisher_name")

        # Clusters collection
        clusters = self.db["story_clusters"]
        clusters.create_index([("company", 1), ("published_at", -1)])
        clusters.create_index("cluster_id", unique=True)

        logger.info("MongoDB indexes created")

    @property
    def articles(self) -> Collection:
        return self.db["enriched_articles"]

    @property
    def clusters(self) -> Collection:
        return self.db["story_clusters"]

    def store_article(self, article: Dict[str, Any]) -> bool:
        """
        Store enriched article.
        Returns True if stored (new), False if duplicate.
        """
        try:
            self.articles.update_one(
                {"url": article["url"]}, {"$set": article}, upsert=True
            )
            logger.debug(f"Stored article: {article.get('title', '')[:50]}")
            return True
        except Exception as e:
            logger.error(f"Failed to store article: {e}")
            return False

    def update_cluster(
        self, cluster_id: str, article: Dict[str, Any], publisher_info: Dict[str, Any]
    ):
        """Update or create story cluster"""
        try:
            existing = self.clusters.find_one({"cluster_id": cluster_id})

            if existing:
                # Add publisher to existing cluster
                self.clusters.update_one(
                    {"cluster_id": cluster_id},
                    {
                        "$push": {"publishers": publisher_info},
                        "$addToSet": {
                            "sources": publisher_info.get("source"),
                            "urls": publisher_info.get("url"),
                        },
                        "$inc": {"article_count": 1},
                        "$set": {"last_updated": datetime.utcnow()},
                    },
                )
            else:
                # Create new cluster
                self.clusters.insert_one(
                    {
                        "cluster_id": cluster_id,
                        "title": article.get("title"),
                        "company": article.get("company"),
                        "factor_type": article.get("factor_type"),
                        "published_at": article.get("published_at"),
                        "sources": [publisher_info.get("source")],
                        "urls": [publisher_info.get("url")],
                        "publishers": [publisher_info],
                        "article_count": 1,
                        "sentiment_label": article.get("sentiment_label"),
                        "sentiment_score": article.get("sentiment_score"),
                        "liquidity_impact": article.get("liquidity_impact"),
                        "critical_events": article.get("critical_events"),
                        "decisions": article.get("decisions"),
                        "first_seen": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    }
                )

            logger.debug(f"Updated cluster: {cluster_id}")

        except Exception as e:
            logger.error(f"Failed to update cluster: {e}")

    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        logger.info("MongoDB connection closed")
