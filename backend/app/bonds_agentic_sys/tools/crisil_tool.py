"""
CRISIL Credit Rating Tool
Scrapes CRISIL credit ratings for companies
"""

import os
import json
from typing import Optional
from pathlib import Path

from schemas_v2 import ToolResult, ToolType, CreditRating
from dotenv import load_dotenv

load_dotenv()

# Import real scraper
import sys

sys.path.append(str(Path(__file__).parent))
from credit_scraper import CrisilScraper


class CrisilScraperTool:
    """
    CRISIL credit rating scraper
    """

    def __init__(self, cache_dir: str = ".cache/companies"):
        self.scraper = CrisilScraper()
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    async def scrape_rating(
        self, company_name: str, isin: Optional[str] = None
    ) -> ToolResult:
        """
        Scrape CRISIL rating for a company from mock files
        """
        try:
            company_dir = os.path.join(
                self.cache_dir, company_name.upper().replace(" ", "_")
            )
            if not os.path.exists(company_dir):
                return ToolResult(
                    tool_type=ToolType.CRISIL_SCRAPER,
                    success=False,
                    data=None,
                    error=f"No mock CRISIL data found for {company_name}",
                )

            # Look for a generic rating file
            rating_file = os.path.join(company_dir, "crisil_rating.json")

            if os.path.exists(rating_file):
                with open(rating_file, "r") as f:
                    rating_data = json.load(f)

                rating = CreditRating(**rating_data)

                return ToolResult(
                    tool_type=ToolType.CRISIL_SCRAPER,
                    success=True,
                    data=rating,
                    cached=True,
                )

            return ToolResult(
                tool_type=ToolType.CRISIL_SCRAPER,
                success=False,
                data=None,
                error=f"No CRISIL rating file found for {company_name}",
            )

        except Exception as e:
            return ToolResult(
                tool_type=ToolType.CRISIL_SCRAPER,
                success=False,
                data=None,
                error=str(e),
            )
