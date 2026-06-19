"""
Tools Manager - Factory and Registry Module
Provides factory functions for creating tool instances
All tool implementations are in separate modules for better modularity
Supports MCP (Model Context Protocol) tools for yield forecasting
"""

from typing import Optional, List
from datetime import datetime
from pathlib import Path
import sys

# Import MCP client for yield forecasting
from utils.mcp_client import create_mcp_client
from schemas_v2 import ToolResult, ToolType, YieldForecast, YieldCurveForecast
from dotenv import load_dotenv

load_dotenv()

# Import all tool classes from their respective modules
from .news_scraper_tool import NewsScraperTool
from .web_search_tool import WebSearchTool
from .crisil_tool import CrisilScraperTool
from .portfolio_tool import PortfolioManagerTool
from .yield_forecaster_tool import YieldForecasterTool
from .bond_pricer_tool import BondPricerTool

# Re-export tool classes for backward compatibility
__all__ = [
    "MCPYieldForecaster",
    "NewsScraperTool",
    "WebSearchTool",
    "CrisilScraperTool",
    "PortfolioManagerTool",
    "YieldForecasterTool",
    "BondPricerTool",
    "create_news_scraper",
    "create_web_search",
    "create_crisil_scraper",
    "create_portfolio_manager",
    "create_yield_forecaster",
    "create_bond_pricer",
]


class MCPYieldForecaster:
    """Yield forecaster using MCP bonds server"""

    def __init__(self, mcp_host: str = "localhost", mcp_port: int = 8123):
        self.mcp_client = create_mcp_client(mcp_host, mcp_port)

    async def forecast_yield_curve(
        self, maturities: Optional[List[float]] = None, horizon_days: int = 14
    ) -> ToolResult:
        """
        Forecast yield curve using MCP server

        Args:
            maturities: List of maturities to forecast (if None, uses all available)
            horizon_days: Forecast horizon in days

        Returns:
            ToolResult with YieldCurveForecast data
        """
        try:
            # Check if MCP server is ready
            if not self.mcp_client.is_ready():
                return ToolResult(
                    tool_type=ToolType.YIELD_FORECASTER,
                    success=False,
                    data=None,
                    error="MCP server not ready",
                )

            # Get forecasts from MCP
            if maturities:
                # Fetch specific maturities
                forecasts_by_mat = {}
                for mat in maturities:
                    mat_int = int(mat)
                    forecasts = self.mcp_client.get_yield_forecast(
                        mat_int, horizon_days
                    )
                    if forecasts:
                        forecasts_by_mat[mat_int] = forecasts
            else:
                # Fetch all maturities
                forecasts_by_mat = self.mcp_client.get_all_yield_forecasts()

            # Convert to YieldCurveForecast schema
            yield_forecast_data = self.mcp_client.to_yield_curve_forecast_schema()

            if not yield_forecast_data:
                return ToolResult(
                    tool_type=ToolType.YIELD_FORECASTER,
                    success=False,
                    data=None,
                    error="No forecast data available",
                )

            # Create YieldForecast objects
            forecast_objects = []
            for f in yield_forecast_data["forecasts"]:
                forecast_objects.append(YieldForecast(**f))

            yield_curve_forecast = YieldCurveForecast(
                forecast_date=datetime.fromisoformat(
                    yield_forecast_data["forecast_date"]
                ),
                forecasts=forecast_objects,
                regime=yield_forecast_data.get("regime", "unknown"),
            )

            return ToolResult(
                tool_type=ToolType.YIELD_FORECASTER,
                success=True,
                data=yield_curve_forecast,
                cached=False,
            )

        except Exception as e:
            return ToolResult(
                tool_type=ToolType.YIELD_FORECASTER,
                success=False,
                data=None,
                error=f"MCP forecasting error: {str(e)}",
            )


# Factory functions for creating tool instances
def create_news_scraper(
    cache_dir: str = ".cache/news", newsdata_api_key: Optional[str] = None
) -> NewsScraperTool:
    """Create a NewsScraperTool instance with Newspaper4K scraper"""
    return NewsScraperTool(cache_dir=cache_dir, newsdata_api_key=newsdata_api_key)


def create_web_search(api_key: Optional[str] = None) -> WebSearchTool:
    """Create a WebSearchTool instance"""
    return WebSearchTool(api_key=api_key)


def create_crisil_scraper(cache_dir: str = ".cache/companies") -> CrisilScraperTool:
    """Create a CrisilScraperTool instance"""
    return CrisilScraperTool(cache_dir=cache_dir)


def create_portfolio_manager(
    db_path: str = ".cache/portfolios", use_mongodb: bool = True
) -> PortfolioManagerTool:
    """Create a PortfolioManagerTool instance with MongoDB support"""
    return PortfolioManagerTool(db_path=db_path, use_mongodb=use_mongodb)


def create_yield_forecaster(
    use_mcp: bool = True,
    mcp_host: str = "localhost",
    mcp_port: int = 8123,
    forecast_dir: str = "output_forecasts",
):
    """
    Factory function - creates yield forecaster

    Args:
        use_mcp: If True, use MCP-based forecaster (default: True)
        mcp_host: MCP server host (default: localhost)
        mcp_port: MCP server port (default: 8123)
        forecast_dir: Directory for forecast files (used if MCP not available)

    Returns:
        MCPYieldForecaster if use_mcp=True, else YieldForecasterTool
    """
    if use_mcp:
        return MCPYieldForecaster(mcp_host, mcp_port)
    else:
        return YieldForecasterTool(forecast_dir=forecast_dir)


def create_bond_pricer(forecast_dir: str = "output_forecasts") -> BondPricerTool:
    """Create a BondPricerTool instance"""
    return BondPricerTool(forecast_dir=forecast_dir)
