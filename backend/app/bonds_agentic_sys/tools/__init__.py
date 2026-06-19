"""
Agent Bond V2 - Tools Module
Data collection and external API integration tools.
Modularized tool implementations with factory functions.
"""

# Import factory functions from tools_manager
from .tools_manager import (
    create_news_scraper,
    create_web_search,
    create_crisil_scraper,
    create_portfolio_manager,
    create_yield_forecaster,
    create_bond_pricer,
)

# Import tool classes for direct access if needed
from .news_scraper_tool import NewsScraperTool
from .web_search_tool import WebSearchTool
from .crisil_tool import CrisilScraperTool
from .portfolio_tool import PortfolioManagerTool
from .yield_forecaster_tool import YieldForecasterTool
from .bond_pricer_tool import BondPricerTool

__all__ = [
    # Factory functions
    "create_news_scraper",
    "create_web_search",
    "create_crisil_scraper",
    "create_portfolio_manager",
    "create_yield_forecaster",
    "create_bond_pricer",
    # Tool classes
    "NewsScraperTool",
    "WebSearchTool",
    "CrisilScraperTool",
    "PortfolioManagerTool",
    "YieldForecasterTool",
    "BondPricerTool",
]
