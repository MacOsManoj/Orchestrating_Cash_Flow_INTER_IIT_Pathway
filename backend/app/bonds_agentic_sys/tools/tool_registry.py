"""
tools/tool_registry.py
Comprehensive Registry: Maps EVERY specific MCP capability to a unique tool name.
"""

from typing import Dict, Callable
from utils.mcp_client import create_mcp_client
from tools.tools_manager import (
    create_news_scraper,
    create_web_search,
    create_portfolio_manager,
    create_crisil_scraper,
)


class ToolRegistry:
    def __init__(self, config):
        # Connect to the Real Data Server
        self.mcp_client = create_mcp_client(
            config.mcp_server_host, config.mcp_server_port
        )

        # Initialize Auxiliary Tools
        self.news_tool = create_news_scraper()
        self.web_tool = create_web_search(config.serpapi_key)
        self.portfolio_tool = create_portfolio_manager(config.portfolio_db_path)
        self.crisil_tool = create_crisil_scraper()

    def get_tool_map(self) -> Dict[str, Callable]:
        """Returns the complete map of 15+ tools."""
        return {
            # ==================================================
            # 1. YIELD CURVE & MACRO TOOLS (MCP)
            # ==================================================
            # Snapshot: "What is the 10Y yield right now?"
            "get_current_yields": self.mcp_client.get_latest_yields,
            # Slope Analysis: "Is the yield curve inverted?" (NEW)
            "analyze_yield_slope": self.mcp_client.calculate_yield_curve_slope,
            # Specific Forecast: "Forecast the 5Y yield for next week" (NEW)
            "forecast_specific_yield": self.mcp_client.get_yield_forecast,
            # Bulk Forecast: "What is the rate outlook?" (Used by ML Agent)
            "forecast_all_yields": self.mcp_client.to_yield_curve_forecast_schema,
            # ==================================================
            # 2. BOND PRICING & DISCOVERY TOOLS (MCP)
            # ==================================================
            # Discovery: "List high yield bonds"
            "fetch_bond_universe": self._fetch_bonds_dynamic,
            # Deep Dive: "Details for bond INE123..."
            "get_bond_details": self.mcp_client.get_bond_info,
            # Specific Price: "Price the Tata Power bond" (NEW)
            "price_single_bond": self.mcp_client.estimate_bond_price,
            # Bulk Pricing: "Find undervalued bonds" (Used by Analyst)
            "price_all_bonds": self.mcp_client.to_bond_price_forecasts_dict,
            # ==================================================
            # 3. SYSTEM TOOLS (MCP)
            # ==================================================
            "check_model_health": self.mcp_client.get_model_status,
            # ==================================================
            # 4. AUXILIARY TOOLS (Local/External)
            # ==================================================
            "get_user_portfolio": self.portfolio_tool.get_portfolio,
            "scrape_news": self.news_tool.scrape_news,
            "web_search": self.web_tool.search,
            "get_credit_rating": self.crisil_tool.scrape_rating,
        }

    async def _fetch_bonds_dynamic(self, limit: int = 50, search_term: str = None):
        """Smart wrapper for list vs search."""
        if search_term:
            result = self.mcp_client.search_bonds(search_term)
            return result.get("matches", [])
        else:
            result = self.mcp_client.list_available_bonds()
            return result.get("available_bonds", [])[:limit]
