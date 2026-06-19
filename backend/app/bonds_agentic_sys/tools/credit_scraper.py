import requests
import logging
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
import re

try:
    from serpapi import GoogleSearch

    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    GoogleSearch = None
import pandas as pd
import json
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class CrisilScraper:
    """Simple CRISIL data scraper using DuckDuckGo"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            }
        )

    def search_crisil_data(self, company_name: str) -> list:
        """Search for CRISIL rating data using SERP API"""

        current_year = datetime.now().year
        print(f"Current year: {current_year}")
        search_query = f"crisil bond rating {current_year} {company_name}"

        logger.info(f"Searching: {search_query}")

        # Use SERP API
        if not SERPAPI_AVAILABLE:
            logger.error(
                "SerpAPI library not available. Install with: pip install google-search-results"
            )
            return []

        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            logger.error(
                "SerpAPI API key not found. Please set the SERPAPI_KEY environment variable."
            )
            return []
        params = {
            "api_key": api_key,
            "engine": "google",
            "q": search_query,
            "location": "India",
            "google_domain": "google.co.in",
            "gl": "us",
            "hl": "en",
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            organic_results = results.get("organic_results", [])

            for result in organic_results:
                link = result.get("link", "")
                if "crisil.com" in link.lower():
                    return [
                        {
                            "url": link,
                            "title": result.get("title", ""),
                            "company": company_name,
                        }
                    ]

            logger.warning("No CRISIL link found in organic results")
            return []

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def fetch_crisil_document(self, url: str, company_name: str) -> dict:
        """Fetch and properly parse CRISIL document content"""

        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Remove unwanted elements
            for element in soup(
                ["script", "style", "nav", "header", "footer", "aside", "noscript"]
            ):
                element.decompose()

            # Try to find main content area (common CRISIL page structures)
            main_content = None
            for selector in [
                "main",
                ".main-content",
                ".content",
                "#content",
                ".article-body",
                ".post-content",
            ]:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.body or soup

            # Extract text content with better formatting
            text_content = main_content.get_text(separator="\n", strip=True)
            # Clean up excessive whitespace
            text_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", text_content)

            # Extract tables manually for better accuracy
            tables = []
            table_elements = main_content.find_all("table")
            for table_elem in table_elements:
                try:
                    # Extract headers
                    headers = []
                    header_rows = (
                        table_elem.find_all("th")
                        or table_elem.find("tr").find_all("td")
                        if table_elem.find("tr")
                        else []
                    )
                    for th in header_rows:
                        headers.append(th.get_text(strip=True))

                    # Extract data rows
                    rows = []
                    data_rows = (
                        table_elem.find_all("tr")[1:]
                        if headers
                        else table_elem.find_all("tr")
                    )
                    for tr in data_rows:
                        row_data = []
                        for td in tr.find_all(["td", "th"]):
                            # Handle colspan/rowspan by getting text
                            text = td.get_text(strip=True)
                            # Skip empty cells or cells with only whitespace
                            if text:
                                row_data.append(text)
                        if row_data:  # Only add non-empty rows
                            rows.append(row_data)

                    if headers or rows:
                        table_dict = {
                            "headers": headers,
                            "rows": rows,
                            "shape": (
                                len(rows),
                                max(len(row) for row in rows) if rows else 0,
                            ),
                        }
                        tables.append(table_dict)
                except Exception as e:
                    logger.warning(f"Could not parse table: {e}")
                    continue

            # Extract key information if available
            metadata = {}
            title_tag = soup.find("title")
            if title_tag:
                metadata["page_title"] = title_tag.get_text(strip=True)

            # Look for rating information (common in CRISIL pages)
            rating_elements = main_content.find_all(
                text=re.compile(r"rating|Rating|RATING", re.IGNORECASE)
            )
            if rating_elements:
                metadata["has_rating_info"] = True

            if len(text_content) < 500 and not tables:
                logger.warning(f"Insufficient content from {url}")
                return None

            return {
                "url": url,
                "title": soup.title.string if soup.title else "CRISIL Document",
                "text_content": text_content,
                "tables": tables,
                "metadata": metadata,
                "company": company_name,
                "fetched_at": datetime.now().isoformat(),
                "word_count": len(text_content.split()),
                "table_count": len(tables),
            }

        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def save_document(self, doc_data: dict, output_dir: str) -> str:
        """Save CRISIL document to JSON file"""

        if not doc_data:
            return None

        os.makedirs(output_dir, exist_ok=True)

        # Create filename
        company_clean = re.sub(r"[^\w\-_]", "_", doc_data["company"])
        url_parts = urlparse(doc_data["url"]).path.split("/")
        doc_name = url_parts[-1] if url_parts else "document"
        doc_name = re.sub(r"[^\w\-_.]", "_", doc_name)

        filename = f"{company_clean}_CRISIL_{doc_name}.json"
        filepath = os.path.join(output_dir, filename)

        # Prepare JSON data
        json_data = {
            "metadata": {
                "company": doc_data["company"],
                "title": doc_data["title"],
                "source_url": doc_data["url"],
                "fetched_at": doc_data["fetched_at"],
                "word_count": doc_data["word_count"],
                "table_count": doc_data["table_count"],
                **doc_data.get("metadata", {}),
            },
            "content": {"text": doc_data["text_content"], "tables": doc_data["tables"]},
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Saved: {filepath} ({len(doc_data['text_content'])} chars text, {len(doc_data['tables'])} tables)"
        )
        return filepath

    def get_company_data(
        self, company_name: str, output_dir: str = "files-for-indexing"
    ) -> list:
        """Complete workflow: search and fetch CRISIL data"""

        logger.info(f"Getting CRISIL data for: {company_name}")

        # Create company directory
        company_dir = os.path.join(
            output_dir, "companies", company_name.replace(" ", "_")
        )
        os.makedirs(company_dir, exist_ok=True)

        # Search for documents
        search_results = self.search_crisil_data(company_name)

        if not search_results:
            logger.warning(f"No CRISIL documents found for {company_name}")
            return []

        saved_files = []

        # Fetch and save each document
        for result in search_results:
            doc_data = self.fetch_crisil_document(result["url"], company_name)

            if doc_data:
                filepath = self.save_document(doc_data, company_dir)
                if filepath:
                    saved_files.append(filepath)

            # Be respectful with requests
            time.sleep(2)

        logger.info(
            f"Successfully saved {len(saved_files)} documents for {company_name}"
        )
        return saved_files


if __name__ == "__main__":
    scraper = CrisilScraper()

    company = input("Enter company name to scrape CRISIL data: ").strip()
    if not company:
        print(" No company name provided")
        exit(1)
    files = scraper.get_company_data(company)

    print(f"\n Retrieved {len(files)} CRISIL documents:")
    for file in files:
        print(f" {file}")
