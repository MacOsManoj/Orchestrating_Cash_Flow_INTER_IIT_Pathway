import os
import logging
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.collection import Collection

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Manager for MongoDB connections and operations"""

    def __init__(self, config: Dict):
        """
        Initialize MongoDB connection

        Args:
            config: Database configuration dict (from config.yaml)
        """
        self.config = config
        self.client: Optional[MongoClient] = None
        self.db = None
        self.positions: Optional[Collection] = None
        self.trades: Optional[Collection] = None

        self.connect()

    def connect(self):
        """Establish connection to MongoDB"""
        uri = os.environ.get("MONGODB_URI") or self.config.get("mongodb", {}).get(
            "uri", "mongodb://localhost:27017"
        )
        db_name = self.config.get("mongodb", {}).get("database_name", "forex_trading")

        try:
            # Connect with a short timeout to fail fast if server is down
            self.client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            # Trigger a connection check
            self.client.admin.command("ping")

            self.db = self.client[db_name]

            # Setup collections
            col_names = self.config.get("mongodb", {}).get("collections", {})
            self.positions = self.db[col_names.get("positions", "positions")]
            self.trades = self.db[col_names.get("trades", "trades")]

            logger.info(f"Connected to MongoDB at {uri}, database: {db_name}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(
                f"Could not connect to MongoDB: {e}. Falling back to file mode if possible, or failing."
            )
            self.client = None
            self.db = None

    def is_connected(self) -> bool:
        """Check if connected to MongoDB"""
        return self.client is not None

    def save_positions(self, positions_data: Dict):
        """Save positions to MongoDB (upsert)"""
        if not self.is_connected() or self.positions is None:
            logger.warning("MongoDB not connected, skipping save_positions")
            return

        try:
            # We store the entire positions dict as a single document for simplicity/compatibility
            # relying on a fixed ID or key to update it.
            # However, a better schema would be one doc per pair.
            # For strict backward compatibility with the current JSON structure
            # (which is a Dict of pair -> data), we can store it as one document with _id="current_positions".

            # Upsert the document with _id="current_positions"
            self.positions.replace_one(
                {"_id": "current_positions"},
                {"_id": "current_positions", "data": positions_data},
                upsert=True,
            )
            logger.debug("Saved positions to MongoDB")
        except Exception as e:
            logger.error(f"Error saving positions to MongoDB: {e}")

    def load_positions(self) -> Dict:
        """Load positions from MongoDB"""
        if not self.is_connected() or self.positions is None:
            return {}

        try:
            doc = self.positions.find_one({"_id": "current_positions"})
            if doc and "data" in doc:
                return doc["data"]
            return {}
        except Exception as e:
            logger.error(f"Error loading positions from MongoDB: {e}")
            return {}

    def save_trades(self, trades_data: Dict):
        """Save trades dictionary to MongoDB"""
        if not self.is_connected() or self.trades is None:
            logger.warning("MongoDB not connected, skipping save_trades")
            return

        try:
            # Similar strategy: store the entire trades aggregate object as one document
            # for full backward compatibility with the current code structure.
            self.trades.replace_one(
                {"_id": "all_trades_history"},
                {"_id": "all_trades_history", "data": trades_data},
                upsert=True,
            )
            logger.debug("Saved trades to MongoDB")
        except Exception as e:
            logger.error(f"Error saving trades to MongoDB: {e}")

    def load_trades(self) -> Dict:
        """Load trades from MongoDB"""
        if not self.is_connected() or self.trades is None:
            return {}

        try:
            doc = self.trades.find_one({"_id": "all_trades_history"})
            if doc and "data" in doc:
                return doc["data"]
            return {}
        except Exception as e:
            logger.error(f"Error loading trades from MongoDB: {e}")
            return {}
