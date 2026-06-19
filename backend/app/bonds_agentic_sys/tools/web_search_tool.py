"""
Web Search Tool
Web search using SerpAPI with retry logic and timeout handling
"""

import asyncio
from typing import Dict, Any, Optional
import os

from schemas_v2 import ToolResult, ToolType
from dotenv import load_dotenv

load_dotenv()


class WebSearchTool:
    """
    Web search using SerpAPI with retry logic and timeout handling
    """

    def __init__(
        self, api_key: Optional[str] = None, timeout: float = 30.0, max_retries: int = 3
    ):
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        self.timeout = timeout
        self.max_retries = max_retries

    async def _search_impl(self, query: str, num_results: int) -> Dict[str, Any]:
        """
        Internal search implementation with retry logic
        """
        if not self.api_key:
            raise ValueError("SerpAPI key not configured")

        # Import GoogleSearch from serpapi
        try:
            from serpapi import GoogleSearch
        except ImportError:
            raise ImportError(
                "SerpAPI library not installed. Install with: pip install google-search-results"
            )

        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "num": num_results,
        }

        # Use GoogleSearch class correctly with timeout
        search = GoogleSearch(params)

        # Run in executor to avoid blocking, with timeout
        loop = asyncio.get_event_loop()
        try:
            results = await asyncio.wait_for(
                loop.run_in_executor(None, search.get_dict), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Web search timed out after {self.timeout}s")

        return results

    async def search(self, query: str, num_results: int = 10) -> ToolResult:
        """
        Perform web search using SerpAPI with retry logic

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            ToolResult with search results or error
        """
        # Input validation
        if not query or not query.strip():
            return ToolResult(
                tool_type=ToolType.WEB_SEARCH,
                success=False,
                data=[],
                error="Query cannot be empty",
            )

        if num_results < 1 or num_results > 100:
            num_results = min(max(1, num_results), 100)  # Clamp between 1 and 100

        # Retry logic with exponential backoff
        last_exception = None
        delay = 1.0

        for attempt in range(self.max_retries + 1):
            try:
                results = await self._search_impl(query, num_results)

                organic_results = results.get("organic_results", [])

                search_results = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("link", ""),
                        "snippet": r.get("snippet", ""),
                        "source": r.get("source", ""),
                    }
                    for r in organic_results
                ]

                return ToolResult(
                    tool_type=ToolType.WEB_SEARCH, success=True, data=search_results
                )

            except (TimeoutError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    print(
                        f"  Web search timeout (attempt {attempt + 1}/{self.max_retries + 1}). Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    return ToolResult(
                        tool_type=ToolType.WEB_SEARCH,
                        success=False,
                        data=[],
                        error=f"Web search timed out after {self.max_retries + 1} attempts",
                    )

            except Exception as e:
                last_exception = e
                # Don't retry on certain errors
                if (
                    "key not configured" in str(e).lower()
                    or "not installed" in str(e).lower()
                ):
                    return ToolResult(
                        tool_type=ToolType.WEB_SEARCH,
                        success=False,
                        data=[],
                        error=str(e),
                    )

                if attempt < self.max_retries:
                    print(
                        f"  Web search error (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    import traceback

                    error_msg = f"Web search failed after {self.max_retries + 1} attempts: {str(e)}"
                    return ToolResult(
                        tool_type=ToolType.WEB_SEARCH,
                        success=False,
                        data=[],
                        error=error_msg,
                    )

        # Should not reach here, but handle just in case
        return ToolResult(
            tool_type=ToolType.WEB_SEARCH,
            success=False,
            data=[],
            error=f"Unexpected error: {str(last_exception) if last_exception else 'Unknown error'}",
        )
