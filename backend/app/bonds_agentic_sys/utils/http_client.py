"""
HTTP client with connection pooling for async operations
Provides reusable aiohttp session management
"""

import aiohttp
from typing import Optional
from contextlib import asynccontextmanager


class HTTPClientPool:
    """
    Singleton HTTP client pool for async operations
    Manages aiohttp ClientSession with connection pooling
    """

    _instance: Optional["HTTPClientPool"] = None
    _session: Optional[aiohttp.ClientSession] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp ClientSession with connection pooling

        Returns:
            Configured aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=10,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                force_close=False,  # Reuse connections
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"User-Agent": "BondPipeline/1.0"},
            )
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @asynccontextmanager
    async def request(self, method: str, url: str, **kwargs):
        """
        Context manager for making HTTP requests

        Usage:
            async with http_pool.request('GET', 'https://api.example.com') as response:
                data = await response.json()
        """
        session = await self.get_session()
        async with session.request(method, url, **kwargs) as response:
            yield response


# Global instance
http_pool = HTTPClientPool()
