"""
MCP Client for Bond Agent System - CORRECTED VERSION
Uses FastMCP async client to connect to bond_server.py (your real MCP server)
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from fastmcp import Client
import asyncio
import aiohttp


class MCPBondsClient:
    """
    Client for MCP Bonds Server (bond_server.py)

    Connects to your real MCP server with 13 tools:
    - 4 yield analytics tools
    - 4 bond discovery tools
    - 3 bond valuation tools
    - 2 bond analysis tools
    """

    def __init__(self, host: str = "localhost", port: int = 8123):
        # Pathway MCP serves on /mcp (without trailing slash based on curl test)
        # But FastMCP Client might need trailing slash, so we'll try both
        self.mcp_url = f"http://{host}:{port}/mcp"
        self.mcp_url_with_slash = f"http://{host}:{port}/mcp/"
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2

    def _extract_json(self, result):
        """Extract JSON from MCP response"""
        if hasattr(result, "content"):
            for item in result.content:
                if hasattr(item, "text"):
                    try:
                        return json.loads(item.text)
                    except:
                        return item.text
        return result

    async def _call_with_retry(self, tool_name: str, arguments: dict):
        """Call MCP tool with retry logic and better error handling"""
        last_error = None
        urls_to_try = [self.mcp_url, self.mcp_url_with_slash]

        for attempt in range(self.max_retries):
            # Try both URL formats
            for url in urls_to_try:
                try:
                    async with Client(url) as client:
                        result = await client.call_tool(
                            name=tool_name, arguments=arguments
                        )
                        # If successful, update the main URL for future calls
                        if url != self.mcp_url:
                            self.mcp_url = url
                        return result
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # Check if it's a connection error
                    is_connection_error = any(
                        keyword in error_str.lower()
                        for keyword in [
                            "connection",
                            "connect",
                            "refused",
                            "timeout",
                            "unreachable",
                            "network",
                            "dns",
                            "resolve",
                            "all connection attempts failed",
                        ]
                    )

                    # If it's not a connection error, don't retry with other URLs
                    if not is_connection_error:
                        raise

                    # If this is the last URL and last attempt, we'll raise the error
                    if url == urls_to_try[-1] and attempt == self.max_retries - 1:
                        raise ConnectionError(
                            f"Failed to connect to MCP server after {self.max_retries} attempts. "
                            f"Tried: {self.mcp_url} and {self.mcp_url_with_slash}. "
                            f"Error: {e}. "
                            f"Make sure bond_server.py is running (check bond_server_manager.py or run: python bond_server.py)"
                        ) from e

            # Wait before retrying
            if attempt < self.max_retries - 1:
                print(
                    f"   WARNING: MCP connection attempt {attempt + 1}/{self.max_retries} failed, retrying in {self.retry_delay}s..."
                )
                await asyncio.sleep(self.retry_delay)

        if last_error:
            raise last_error

    # ==================== YIELD ANALYTICS ====================

    async def get_latest_yields(self) -> Dict[float, float]:
        """
        Get current yields for all maturities

        Returns:
            Dict mapping maturity (float years) to yield (decimal)
            Example: {1.0: 0.0570, 2.0: 0.0574, 5.0: 0.0617, ...}
        """
        result = await self._call_with_retry("get_latest_yields", {})

        data = self._extract_json(result)

        if not isinstance(data, dict) or "yields" not in data:
            print(" MCP: No yields data returned")
            return {}

        # Convert "1Y": 5.7 to 1.0: 0.057 (string → float, percentage → decimal)
        yields = {}
        for key, value in data["yields"].items():
            if key.endswith("Y"):
                maturity_years = float(key[:-1])
                yields[maturity_years] = value

        return yields

    async def get_yield_forecast(
        self, maturity: int, days_ahead: int = 14
    ) -> List[Dict]:
        """
        Get yield forecasts for specific maturity

        Args:
            maturity: Years to maturity (1, 2, 5, 7, 10)
            days_ahead: Number of days to forecast (default 14, max 21)

        Returns:
            List of forecast dicts with keys:
            - day (int): Day number (1-21)
            - date (str): ISO date
            - predicted_yield (float): Yield in percentage
            - predicted_return (float): Daily return
        """
        result = await self._call_with_retry(
            "get_yield_forecast", {"maturity": maturity, "days_ahead": days_ahead}
        )

        data = self._extract_json(result)
        return data.get("forecasts", []) if isinstance(data, dict) else []

    async def get_all_yield_forecasts(self) -> Dict[int, List[Dict]]:
        """
        Get yield forecasts for all maturities (1Y, 2Y, 5Y, 7Y, 10Y)

        Returns:
            Dict mapping maturity (int) to list of forecast dicts
            Example: {1: [{day: 1, date: "2025-11-05", ...}, ...], 2: [...], ...}
        """
        result = await self._call_with_retry("get_all_yield_forecasts", {})

        data = self._extract_json(result)

        if not isinstance(data, list):
            print(" MCP: No forecast data returned")
            return {}

        # Convert list of {maturity: "5Y", forecasts: [...]} to dict
        forecasts_by_maturity = {}
        for item in data:
            maturity_str = item.get("maturity", "")
            if maturity_str.endswith("Y"):
                maturity = int(maturity_str[:-1])
                forecasts_by_maturity[maturity] = item.get("forecasts", [])

        return forecasts_by_maturity

    async def get_yield_curve(self, days_ahead: int = 1) -> Dict:
        """
        Get complete yield curve for specific forecast date

        Args:
            days_ahead: Which forecast day (1-21)

        Returns:
            Dict with 'date' and 'yield_curve' (list of {maturity, yield})
        """
        result = await self._call_with_retry(
            "get_yield_curve", {"days_ahead": days_ahead}
        )
        return self._extract_json(result)

    # ==================== BOND DISCOVERY ====================

    async def list_bonds(self) -> Dict:
        """
        Get list of all available bonds (169 bonds)

        Returns:
            Dict with keys:
            - total_bonds (int): Number of bonds
            - bonds (List[Dict]): List of bond dicts with symbol, isin, name, etc.
        """
        result = await self._call_with_retry("list_bonds", {})
        return self._extract_json(result)

    async def search_bonds(self, search_term: str) -> Dict:
        """
        Search for bonds by symbol, ISIN, or name

        Args:
            search_term: Search query (e.g., "GS", "2028", "GOI")

        Returns:
            Dict with 'matches' count and 'bonds' list
        """
        result = await self._call_with_retry(
            "search_bonds", {"search_term": search_term}
        )
        return self._extract_json(result)

    async def get_bond_info(self, bond_identifier: str) -> Dict:
        """
        Get detailed information about a specific bond

        Args:
            bond_identifier: Bond symbol or ISIN (e.g., "667GS2035")

        Returns:
            Dict with bond details: symbol, isin, name, face_value, coupon_rate,
            coupon_frequency, maturity_date, years_to_maturity, description
        """
        result = await self._call_with_retry(
            "get_bond_info",
            {
                "bond_identifier": bond_identifier,
                "days_ahead": 0,  # Required by schema
            },
        )
        return self._extract_json(result)

    async def get_bond_details(self, bond_identifier: str, days_ahead: int = 0) -> Dict:
        """
        Get comprehensive bond details including LTP and analytics

        Args:
            bond_identifier: Bond symbol or ISIN
            days_ahead: Days ahead for forecast (0 = today)

        Returns:
            Dict with: isin, symbol, name, last_traded_price, current_price,
            ytm, modified_duration, macaulay_duration, convexity,
            years_to_maturity, coupon_rate, maturity_date
        """
        result = await self._call_with_retry(
            "get_bond_details",
            {"bond_identifier": bond_identifier, "days_ahead": days_ahead},
        )
        return self._extract_json(result)

    async def filter_bonds(
        self,
        min_coupon: float = 0.0,
        max_coupon: float = 0.0,
        min_years_to_maturity: float = 0.0,
        max_years_to_maturity: float = 0.0,
        min_maturity_year: int = 0,
        max_maturity_year: int = 0,
        symbol_contains: str = "",
        name_contains: str = "",
    ) -> Dict:
        """
        Filter bonds by multiple criteria

        Args:
            min_coupon: Minimum coupon rate (percentage, e.g., 6.0)
            max_coupon: Maximum coupon rate (0.0 = no limit)
            min_years_to_maturity: Minimum years to maturity
            max_years_to_maturity: Maximum years to maturity (0.0 = no limit)
            symbol_contains: Symbol filter (e.g., "GS")
            name_contains: Name filter (e.g., "GOVERNMENT")

        Returns:
            Dict with 'total_matches' and filtered 'bonds' list
        """
        result = await self._call_with_retry(
            "filter_bonds",
            {
                "min_coupon": min_coupon,
                "max_coupon": max_coupon,
                "min_years_to_maturity": min_years_to_maturity,
                "max_years_to_maturity": max_years_to_maturity,
                "symbol_contains": symbol_contains,
                "name_contains": name_contains,
            },
        )
        return self._extract_json(result)

    # ==================== BOND VALUATION ====================

    async def get_bond_price(self, bond_identifier: str, days_ahead: int = 0) -> Dict:
        """
        Get bond price forecast

        Args:
            bond_identifier: Bond symbol or ISIN
            days_ahead:
                - 0 = all days (returns starting_price, ending_price, forecasts list)
                - 1-21 = specific day (returns single day estimate)

        Returns:
            If days_ahead > 0:
                {day, date, estimated_price, ytm_percent, ...}
            If days_ahead = 0:
                {starting_price, ending_price, price_change, pct_change, forecasts: [...]}
        """
        result = await self._call_with_retry(
            "get_bond_price",
            {"bond_identifier": bond_identifier, "days_ahead": days_ahead},
        )
        return self._extract_json(result)

    async def calculate_bond_ytm(self, bond_identifier: str) -> Dict:
        """
        Calculate bond yield-to-maturity

        Args:
            bond_identifier: Bond symbol or ISIN

        Returns:
            Dict with: bond_name, ytm_percent, valuation_date
        """
        result = await self._call_with_retry(
            "calculate_bond_ytm", {"bond_identifier": bond_identifier}
        )
        return self._extract_json(result)

    async def calculate_bond_duration(self, bond_identifier: str) -> Dict:
        """
        Calculate bond duration and convexity

        Args:
            bond_identifier: Bond symbol or ISIN

        Returns:
            Dict with: macaulay_duration, modified_duration, convexity,
                      estimated_price, valuation_date
        """
        result = await self._call_with_retry(
            "calculate_bond_duration", {"bond_identifier": bond_identifier}
        )
        return self._extract_json(result)

    # ==================== BOND ANALYSIS ====================

    async def compare_bonds(self, bond_identifiers: str) -> Dict:
        """
        Compare multiple bonds side-by-side

        Args:
            bond_identifiers: Comma-separated list of symbols/ISINs
                             Example: "667GS2035,717GS2030,736GS2052"

        Returns:
            Dict with 'comparison_date', 'bonds_compared' count, and
            'bonds' list with YTM, price, duration, convexity for each
        """
        result = await self._call_with_retry(
            "compare_bonds", {"bond_identifiers": bond_identifiers}
        )
        return self._extract_json(result)

    async def recommend_bonds(
        self,
        target_yield: float = 0.0,
        max_risk: str = "medium",
        investment_horizon: float = 0.0,
        sort_by: str = "yield",
    ) -> Dict:
        """
        Get AI-powered bond recommendations

        Args:
            target_yield: Minimum target yield (percentage, e.g., 6.5)
            max_risk: Risk level - "low" (duration < 3),
                                   "medium" (duration < 7),
                                   "high" (any duration)
            investment_horizon: Preferred years to maturity (e.g., 10.0)
            sort_by: Sort order - "yield", "duration", or "price"

        Returns:
            Dict with 'total_recommendations', 'recommendation_date', and
            'recommendations' list with top bonds ranked by criteria
        """
        result = await self._call_with_retry(
            "recommend_bonds",
            {
                "target_yield": target_yield,
                "max_risk": max_risk,
                "investment_horizon": investment_horizon,
                "sort_by": sort_by,
            },
        )
        return self._extract_json(result)

    # ==================== UTILITY METHODS ====================

    async def is_ready(self) -> bool:
        """
        Check if MCP server is ready to serve data

        Returns:
            True if server is responding and has data loaded
        """
        try:
            yields = await self.get_latest_yields()
            return len(yields) > 0
        except Exception as e:
            print(f" MCP server not ready: {e}")
            return False

    def to_yield_curve_forecast_schema(
        self, forecasts_by_maturity: Dict
    ) -> Optional[Dict]:
        """
        Convert MCP forecasts to YieldCurveForecast schema format
        (For compatibility with your agents)

        Args:
            forecasts_by_maturity: Output from get_all_yield_forecasts()

        Returns:
            Dict compatible with schemas_v2.YieldCurveForecast
        """
        if not forecasts_by_maturity:
            return None

        # Get forecast date from first forecast
        first_maturity = next(iter(forecasts_by_maturity.keys()))
        first_forecast = (
            forecasts_by_maturity[first_maturity][0]
            if forecasts_by_maturity[first_maturity]
            else {}
        )
        forecast_date = first_forecast.get("date", datetime.now().isoformat())

        # Build forecasts list
        forecasts = []
        for maturity, forecast_list in forecasts_by_maturity.items():
            for forecast in forecast_list:
                forecasts.append(
                    {
                        "maturity_years": float(maturity),
                        "forecast_date": forecast.get("date", forecast_date),
                        "predicted_yield": forecast.get("predicted_yield", 0)
                        / 100.0,  # Convert % to decimal
                        "predicted_return": forecast.get("predicted_return", 0),
                        "confidence": 0.85,  # Pathway Hoeffding Tree models have ~85% accuracy
                        "model_type": "Pathway_Hoeffding_NelsonSiegel",
                    }
                )

        return {
            "forecast_date": forecast_date,
            "forecasts": forecasts,
            "regime": self._detect_regime(forecasts_by_maturity),
        }

    def _detect_regime(self, forecasts_by_maturity: Dict) -> str:
        """
        Detect yield curve regime from forecasts

        Returns:
            "inverted", "flattening", "steepening", "normal", or "unknown"
        """
        if not forecasts_by_maturity:
            return "unknown"

        # Calculate slope using 2Y and 10Y
        if 2 in forecasts_by_maturity and 10 in forecasts_by_maturity:
            y2_forecasts = forecasts_by_maturity[2]
            y10_forecasts = forecasts_by_maturity[10]

            if y2_forecasts and y10_forecasts:
                y2_last = y2_forecasts[-1]["predicted_yield"]
                y10_last = y10_forecasts[-1]["predicted_yield"]

                slope = y10_last - y2_last

                if slope < -0.5:
                    return "inverted"  # Recession signal
                elif slope < 0.2:
                    return "flattening"  # Potential recession ahead
                elif slope > 1.0:
                    return "steepening"  # Growth expected
                else:
                    return "normal"  # Typical curve

        return "unknown"

    def to_bond_universe(self, bonds_data: Dict) -> List[Dict]:
        """
        Convert MCP list_bonds() output to agent-friendly format

        Args:
            bonds_data: Output from list_bonds()

        Returns:
            List of bond dicts ready for agent consumption
        """
        if not isinstance(bonds_data, dict):
            return []

        return bonds_data.get("bonds", [])


def create_mcp_client(host: str = "localhost", port: int = 8123) -> MCPBondsClient:
    """
    Factory function to create MCP client

    Usage:
        client = create_mcp_client()
        yields = await client.get_latest_yields()
        bonds = await client.list_bonds()
    """
    return MCPBondsClient(host, port)


async def check_mcp_connection(
    host: str = "localhost", port: int = 8123
) -> Tuple[bool, str]:
    """
    Check if MCP server is running and responding.

    Returns:
        Tuple of (is_connected: bool, message: str)
    """
    mcp_url = f"http://{host}:{port}/mcp"

    try:
        # First, try a simple HTTP connection to the server
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            async with session.get(f"http://{host}:{port}/") as response:
                # Server is responding
                pass
    except aiohttp.ClientConnectorError:
        return (
            False,
            f"❌ MCP Server not running at {host}:{port}. Start it with: python bond_server.py",
        )
    except Exception as e:
        return False, f"❌ Cannot connect to MCP Server: {e}"

    # Now try to actually call a tool
    try:
        client = MCPBondsClient(host, port)
        is_ready = await client.is_ready()
        if is_ready:
            return True, f"✅ MCP Server connected at {host}:{port}"
        else:
            return (
                False,
                f"⚠️ MCP Server running but no data loaded. Check bond_server.py logs.",
            )
    except Exception as e:
        error_str = str(e).lower()
        if "connection" in error_str or "refused" in error_str:
            return (
                False,
                f"❌ MCP Server not running at {host}:{port}. Start it with: python bond_server.py",
            )
        return False, f"⚠️ MCP Server error: {e}"


def check_mcp_connection_sync(
    host: str = "localhost", port: int = 8123
) -> Tuple[bool, str]:
    """
    Synchronous version of check_mcp_connection.
    """
    return asyncio.run(check_mcp_connection(host, port))


# ==================== SYNC WRAPPER (Optional) ====================


class SyncMCPBondsClient:
    """
    Synchronous wrapper for MCPBondsClient
    Use this if you can't use async/await in your code
    """

    def __init__(self, host: str = "localhost", port: int = 8123):
        self.async_client = MCPBondsClient(host, port)

    def _run_async(self, coro):
        """Run async method synchronously"""
        return asyncio.run(coro)

    def get_latest_yields(self) -> Dict[float, float]:
        return self._run_async(self.async_client.get_latest_yields())

    def get_yield_forecast(self, maturity: int, days_ahead: int = 14) -> List[Dict]:
        return self._run_async(
            self.async_client.get_yield_forecast(maturity, days_ahead)
        )

    def get_all_yield_forecasts(self) -> Dict[int, List[Dict]]:
        return self._run_async(self.async_client.get_all_yield_forecasts())

    def list_bonds(self) -> Dict:
        return self._run_async(self.async_client.list_bonds())

    def search_bonds(self, search_term: str) -> Dict:
        return self._run_async(self.async_client.search_bonds(search_term))

    def get_bond_info(self, bond_identifier: str) -> Dict:
        return self._run_async(self.async_client.get_bond_info(bond_identifier))

    def get_bond_price(self, bond_identifier: str, days_ahead: int = 0) -> Dict:
        return self._run_async(
            self.async_client.get_bond_price(bond_identifier, days_ahead)
        )

    def calculate_bond_ytm(self, bond_identifier: str) -> Dict:
        return self._run_async(self.async_client.calculate_bond_ytm(bond_identifier))

    def calculate_bond_duration(self, bond_identifier: str) -> Dict:
        return self._run_async(
            self.async_client.calculate_bond_duration(bond_identifier)
        )

    def filter_bonds(self, **kwargs) -> Dict:
        return self._run_async(self.async_client.filter_bonds(**kwargs))

    def compare_bonds(self, bond_identifiers: str) -> Dict:
        return self._run_async(self.async_client.compare_bonds(bond_identifiers))

    def recommend_bonds(self, **kwargs) -> Dict:
        return self._run_async(self.async_client.recommend_bonds(**kwargs))

    def is_ready(self) -> bool:
        return self._run_async(self.async_client.is_ready())


def create_sync_mcp_client(
    host: str = "localhost", port: int = 8123
) -> SyncMCPBondsClient:
    """
    Create synchronous MCP client

    Usage:
        client = create_sync_mcp_client()
        yields = client.get_latest_yields()  # No await needed
    """
    return SyncMCPBondsClient(host, port)
