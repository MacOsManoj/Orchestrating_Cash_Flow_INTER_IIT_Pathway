"""
MongoDB Client for Portfolio Management
Handles database connections and operations
"""

import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client singleton for portfolio management
    """

    _instance: Optional["MongoDBClient"] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        """Connect to MongoDB"""
        try:
            # Get connection string from environment
            connection_string = os.getenv(
                "MONGODB_URI",
                os.getenv(
                    "MONGODB_CONNECTION_STRING",
                    "mongodb+srv://admin:admin@cluster0.xfoccu0.mongodb.net/?appName=Cluster0",
                ),
            )

            # Get database name from environment
            db_name = os.getenv("MONGODB_DB_NAME", "bond_portfolio_db")

            # Create client
            self._client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )

            # Test connection
            self._client.server_info()

            # Get database
            self._db = self._client[db_name]

            logger.info(f"Connected to MongoDB database: {db_name}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            # Create a mock client for development if connection fails
            self._client = None
            self._db = None
            logger.warning("MongoDB connection failed. Using in-memory fallback.")

    @property
    def db(self) -> Optional[Database]:
        """Get database instance"""
        if self._db is None:
            self._connect()
        return self._db

    @property
    def portfolios_collection(self) -> Optional[Collection]:
        """Get portfolios collection"""
        if self.db is None:
            return None
        return self.db.portfolios

    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        try:
            if self._client is None:
                return False
            self._client.server_info()
            return True
        except Exception:
            return False

    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")


def get_mongodb_client() -> MongoDBClient:
    """Get MongoDB client instance"""
    return MongoDBClient()


def get_portfolios_collection() -> Optional[Collection]:
    """Get portfolios collection"""
    client = get_mongodb_client()
    return client.portfolios_collection
