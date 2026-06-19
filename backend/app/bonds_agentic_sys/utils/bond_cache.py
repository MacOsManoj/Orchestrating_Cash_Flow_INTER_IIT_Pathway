"""
Bond Data Cache
Caches bond details and price predictions to avoid redundant MCP calls
Data is cached for 24 hours (until end of day) since bond data changes once daily
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path
import hashlib
from utils.logger import setup_logger, get_logger

logger = setup_logger(__name__)

# Cache directory - use .cache in project root (not files-mock since we use real MCP data)
# Go up from utils/ to bond-pipeline/ root, then use .cache
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache" / "bond_data"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cache TTL: 24 hours (bond data changes once per day)
CACHE_TTL_HOURS = 24


class BondDataCache:
    """
    Thread-safe cache for bond details and price predictions
    Caches data for 24 hours to avoid redundant MCP calls
    """

    def __init__(
        self, cache_dir: Optional[Path] = None, ttl_hours: int = CACHE_TTL_HOURS
    ):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self._lock = asyncio.Lock()
        self._memory_cache: Dict[
            str, Dict[str, Any]
        ] = {}  # In-memory cache for fast access

        logger.info(f"Bond data cache initialized: {self.cache_dir}")
        logger.info(f"Cache TTL: {ttl_hours} hours")

    def _get_cache_key(
        self, isin: str, cache_type: str, days_ahead: Optional[int] = None
    ) -> str:
        """Generate cache key for bond data"""
        key_parts = [isin, cache_type]
        if days_ahead is not None:
            key_parts.append(str(days_ahead))
        key_str = "_".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get file path for cache entry"""
        return self.cache_dir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid (not expired)"""
        if "timestamp" not in cache_data:
            return False

        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        age = datetime.now() - cache_time

        # Check if cache is older than TTL
        if age > timedelta(hours=self.ttl_hours):
            return False

        # Also check if it's a new day (bond data changes daily)
        # If cache is from yesterday, invalidate it
        if cache_time.date() < datetime.now().date():
            return False

        return True

    async def get_bond_details(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Get cached bond details or None if not cached/expired

        Args:
            isin: Bond ISIN identifier

        Returns:
            Cached bond details dict or None
        """
        cache_key = self._get_cache_key(isin, "bond_details")

        # Check memory cache first
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            if self._is_cache_valid(cached):
                logger.debug(f"Cache HIT (memory): bond_details for {isin}")
                return cached.get("data")
            else:
                # Expired, remove from memory
                del self._memory_cache[cache_key]

        # Check file cache
        cache_file = self._get_cache_file_path(cache_key)
        if cache_file.exists():
            try:
                async with self._lock:
                    with open(cache_file, "r") as f:
                        cached = json.load(f)

                if self._is_cache_valid(cached):
                    # Load into memory cache
                    self._memory_cache[cache_key] = cached
                    logger.debug(f"Cache HIT (file): bond_details for {isin}")
                    return cached.get("data")
                else:
                    # Expired, delete file
                    cache_file.unlink()
                    logger.debug(f"Cache EXPIRED: bond_details for {isin}")
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")

        logger.debug(f"Cache MISS: bond_details for {isin}")
        return None

    async def set_bond_details(self, isin: str, data: Dict[str, Any]) -> None:
        """
        Cache bond details

        Args:
            isin: Bond ISIN identifier
            data: Bond details dict to cache
        """
        cache_key = self._get_cache_key(isin, "bond_details")
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "isin": isin,
            "cache_type": "bond_details",
            "data": data,
        }

        # Store in memory cache
        self._memory_cache[cache_key] = cache_entry

        # Store in file cache
        cache_file = self._get_cache_file_path(cache_key)
        try:
            async with self._lock:
                with open(cache_file, "w") as f:
                    json.dump(cache_entry, f, indent=2)
            logger.debug(f"Cached bond_details for {isin}")
        except Exception as e:
            logger.warning(f"Error writing cache file {cache_file}: {e}")

    async def get_bond_price(
        self, isin: str, days_ahead: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached bond price prediction or None if not cached/expired

        Args:
            isin: Bond ISIN identifier
            days_ahead: Days ahead for prediction (0 = current, 21 = 21-day forecast)

        Returns:
            Cached price prediction dict or None
        """
        cache_key = self._get_cache_key(isin, "bond_price", days_ahead)

        # Check memory cache first
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            if self._is_cache_valid(cached):
                logger.debug(
                    f"Cache HIT (memory): bond_price for {isin} (days_ahead={days_ahead})"
                )
                return cached.get("data")
            else:
                # Expired, remove from memory
                del self._memory_cache[cache_key]

        # Check file cache
        cache_file = self._get_cache_file_path(cache_key)
        if cache_file.exists():
            try:
                async with self._lock:
                    with open(cache_file, "r") as f:
                        cached = json.load(f)

                if self._is_cache_valid(cached):
                    # Load into memory cache
                    self._memory_cache[cache_key] = cached
                    logger.debug(
                        f"Cache HIT (file): bond_price for {isin} (days_ahead={days_ahead})"
                    )
                    return cached.get("data")
                else:
                    # Expired, delete file
                    cache_file.unlink()
                    logger.debug(
                        f"Cache EXPIRED: bond_price for {isin} (days_ahead={days_ahead})"
                    )
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")

        logger.debug(f"Cache MISS: bond_price for {isin} (days_ahead={days_ahead})")
        return None

    async def set_bond_price(
        self, isin: str, days_ahead: int, data: Dict[str, Any]
    ) -> None:
        """
        Cache bond price prediction

        Args:
            isin: Bond ISIN identifier
            days_ahead: Days ahead for prediction
            data: Price prediction dict to cache
        """
        cache_key = self._get_cache_key(isin, "bond_price", days_ahead)
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "isin": isin,
            "days_ahead": days_ahead,
            "cache_type": "bond_price",
            "data": data,
        }

        # Store in memory cache
        self._memory_cache[cache_key] = cache_entry

        # Store in file cache
        cache_file = self._get_cache_file_path(cache_key)
        try:
            async with self._lock:
                with open(cache_file, "w") as f:
                    json.dump(cache_entry, f, indent=2)
            logger.debug(f"Cached bond_price for {isin} (days_ahead={days_ahead})")
        except Exception as e:
            logger.warning(f"Error writing cache file {cache_file}: {e}")

    async def clear_cache(self, isin: Optional[str] = None) -> None:
        """
        Clear cache entries

        Args:
            isin: If provided, clear only this bond's cache. Otherwise, clear all.
        """
        if isin:
            # Clear specific bond
            patterns = [
                self._get_cache_key(isin, "bond_details"),
                self._get_cache_key(isin, "bond_price", 0),
                self._get_cache_key(isin, "bond_price", 21),
            ]

            for cache_key in patterns:
                # Remove from memory
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]

                # Remove file
                cache_file = self._get_cache_file_path(cache_key)
                if cache_file.exists():
                    cache_file.unlink()

            logger.info(f"Cleared cache for bond {isin}")
        else:
            # Clear all cache
            self._memory_cache.clear()
            async with self._lock:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
            logger.info("Cleared all bond data cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        valid_count = 0
        expired_count = 0

        for cache_file in cache_files:
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                if self._is_cache_valid(cached):
                    valid_count += 1
                else:
                    expired_count += 1
            except:
                expired_count += 1

        return {
            "total_files": len(cache_files),
            "valid_entries": valid_count,
            "expired_entries": expired_count,
            "memory_entries": len(self._memory_cache),
            "cache_dir": str(self.cache_dir),
        }


# Global cache instance
_bond_cache: Optional[BondDataCache] = None


def get_bond_cache() -> BondDataCache:
    """Get or create global bond cache instance"""
    global _bond_cache
    if _bond_cache is None:
        _bond_cache = BondDataCache()
    return _bond_cache
