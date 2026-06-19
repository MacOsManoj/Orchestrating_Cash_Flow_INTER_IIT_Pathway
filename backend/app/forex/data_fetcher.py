"""
Data Fetcher Module
Fetches OHLCV data from Polygon.io for forex pairs.
Includes Pathway connector integration for real-time data streaming.
"""

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import time

logger = logging.getLogger(__name__)


class PolygonForexFetcher:
    """
    Fetches forex OHLCV data from Polygon.io API.
    Note: Basic subscription does not have real-time data, so we fetch latest available daily data.
    """

    # Polygon forex pairs format: C:EURUSD (currency pair with C: prefix)
    POLYGON_PAIR_MAP = {
        "EURUSD": "C:EURUSD",
        "GBPUSD": "C:GBPUSD",
        "USDJPY": "C:USDJPY",
        "EURINR": "C:EURINR",
        "GBPINR": "C:GBPINR",
        "JPYINR": "C:JPYINR",
        "USDINR": "C:USDINR",
    }

    def __init__(self, api_key: str):
        """
        Initialize Polygon fetcher.

        Args:
            api_key: Polygon.io API key
        """
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to Polygon API"""
        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def get_forex_ticker(self, pair: str) -> str:
        """Convert pair name to Polygon ticker format"""
        return self.POLYGON_PAIR_MAP.get(pair, f"C:{pair}")

    def fetch_daily_bars(
        self, pair: str, from_date: str, to_date: str, limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV bars for a forex pair.

        Args:
            pair: Currency pair (e.g., 'EURUSD')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            limit: Maximum number of results

        Returns:
            DataFrame with OHLCV data
        """
        ticker = self.get_forex_ticker(pair)

        endpoint = f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
        params = {"adjusted": "true", "sort": "asc", "limit": limit}

        logger.info(f"Fetching {pair} data from {from_date} to {to_date}")

        try:
            data = self._make_request(endpoint, params)

            if "results" not in data or not data["results"]:
                logger.warning(f"No data returned for {pair}")
                return pd.DataFrame()

            df = pd.DataFrame(data["results"])

            # Rename columns to standard format
            column_map = {
                "t": "ts_ms",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "vw": "vwap",
                "n": "transactions",
            }
            df = df.rename(columns=column_map)

            # Select required columns
            required_cols = ["ts_ms", "open", "high", "low", "close", "volume"]
            available_cols = [c for c in required_cols if c in df.columns]
            df = df[available_cols]

            # If volume is not available (common for forex), fill with 0
            if "volume" not in df.columns:
                df["volume"] = 0

            df["pair"] = pair

            logger.info(f"Fetched {len(df)} bars for {pair}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {pair}: {e}")
            return pd.DataFrame()

    def fetch_latest_bar(self, pair: str) -> Optional[Dict]:
        """
        Fetch the latest available bar for a forex pair.

        Args:
            pair: Currency pair

        Returns:
            Dict with latest OHLCV data or None
        """
        ticker = self.get_forex_ticker(pair)

        # Get previous close (latest available)
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"

        try:
            data = self._make_request(endpoint)

            if "results" not in data or not data["results"]:
                logger.warning(f"No latest data for {pair}")
                return None

            result = data["results"][0]

            return {
                "ts_ms": result.get("t"),
                "open": result.get("o"),
                "high": result.get("h"),
                "low": result.get("l"),
                "close": result.get("c"),
                "volume": result.get("v", 0),
                "pair": pair,
            }

        except Exception as e:
            logger.error(f"Error fetching latest bar for {pair}: {e}")
            return None

    def fetch_multiple_pairs(
        self, pairs: List[str], from_date: str, to_date: str
    ) -> pd.DataFrame:
        """
        Fetch data for multiple pairs.

        Args:
            pairs: List of currency pairs
            from_date: Start date
            to_date: End date

        Returns:
            Combined DataFrame
        """
        all_dfs = []

        for pair in pairs:
            df = self.fetch_daily_bars(pair, from_date, to_date)
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            return pd.DataFrame()

        return pd.concat(all_dfs, ignore_index=True)

    def fetch_latest_all_pairs(self, pairs: List[str]) -> Dict[str, Dict]:
        """
        Fetch latest bar for all pairs.

        Args:
            pairs: List of currency pairs

        Returns:
            Dict of {pair: latest_bar}
        """
        latest_data = {}

        for pair in pairs:
            bar = self.fetch_latest_bar(pair)
            if bar:
                latest_data[pair] = bar

        return latest_data

    def update_historical_csv(
        self, pair: str, data_dir: str, days_back: int = 30
    ) -> bool:
        """
        Update historical CSV file with new data.

        Args:
            pair: Currency pair
            data_dir: Directory containing CSV files
            days_back: Number of days to fetch

        Returns:
            True if update successful
        """
        csv_path = os.path.join(data_dir, f"{pair}.csv")

        # Calculate date range
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Fetch new data
        new_df = self.fetch_daily_bars(pair, from_date, to_date)

        if new_df.empty:
            logger.warning(f"No new data fetched for {pair}")
            return False

        # Load existing data if it exists
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)

            # Combine and remove duplicates
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["ts_ms"], keep="last")
            combined_df = combined_df.sort_values("ts_ms").reset_index(drop=True)
        else:
            combined_df = new_df

        # Remove pair column before saving (it's in the filename)
        if "pair" in combined_df.columns:
            combined_df = combined_df.drop(columns=["pair"])

        # Save
        combined_df.to_csv(csv_path, index=False)
        logger.info(f"Updated {csv_path} with {len(combined_df)} total rows")

        return True


class PathwayDataConnector:
    """
    Pathway connector for real-time forex data streaming.
    Uses Pathway's polling mechanism to fetch latest data at intervals.
    """

    def __init__(
        self,
        polygon_fetcher: PolygonForexFetcher,
        pairs: List[str],
        polling_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize Pathway connector.

        Args:
            polygon_fetcher: PolygonForexFetcher instance
            pairs: List of currency pairs to monitor
            polling_interval: Polling interval in seconds
        """
        self.fetcher = polygon_fetcher
        self.pairs = pairs
        self.polling_interval = polling_interval
        self._latest_data = {}

    def create_input_schema(self):
        """Create Pathway input schema for forex data"""
        try:
            import pathway as pw

            class ForexSchema(pw.Schema):
                ts_ms: int
                open: float
                high: float
                low: float
                close: float
                volume: float
                pair: str

            return ForexSchema
        except ImportError:
            logger.warning("Pathway not installed, schema not created")
            return None

    def get_data_callback(self):
        """
        Create callback function for Pathway polling connector.

        Returns:
            Callable that returns list of dicts with forex data
        """

        def fetch_callback():
            data = []
            for pair in self.pairs:
                bar = self.fetcher.fetch_latest_bar(pair)
                if bar:
                    data.append(bar)
                    self._latest_data[pair] = bar
            return data

        return fetch_callback

    def create_pathway_table(self):
        """
        Create a Pathway table from polling data.

        Returns:
            Pathway table with forex data
        """
        try:
            import pathway as pw

            schema = self.create_input_schema()

            # Create polling connector
            # Note: This uses a file-based approach for simplicity
            # In production, you might use a more sophisticated connector

            logger.info(f"Creating Pathway table for pairs: {self.pairs}")

            # For now, return None - actual Pathway table creation
            # would require running Pathway runtime
            return None

        except ImportError:
            logger.error("Pathway not installed")
            return None

    def get_latest_data(self) -> Dict[str, Dict]:
        """Get the most recently fetched data"""
        return self._latest_data.copy()


class DataManager:
    """
    Manages data fetching, storage, and updates for the trading pipeline.
    """

    def __init__(self, api_key: str, data_dir: str, pairs: List[str]):
        """
        Initialize DataManager.

        Args:
            api_key: Polygon.io API key
            data_dir: Directory for CSV data storage
            pairs: List of currency pairs
        """
        self.fetcher = PolygonForexFetcher(api_key) if api_key else None
        self.data_dir = data_dir
        self.pairs = pairs

        os.makedirs(data_dir, exist_ok=True)

    def load_historical_data(self, pair: str) -> pd.DataFrame:
        """Load historical data from CSV"""
        csv_path = os.path.join(self.data_dir, f"{pair}.csv")

        if not os.path.exists(csv_path):
            logger.warning(f"No historical data file for {pair}")
            return pd.DataFrame()

        df = pd.read_csv(csv_path)
        df["pair"] = pair
        return df

    def load_all_historical_data(self) -> pd.DataFrame:
        """Load historical data for all pairs"""
        all_dfs = []

        for pair in self.pairs:
            df = self.load_historical_data(pair)
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            return pd.DataFrame()

        return pd.concat(all_dfs, ignore_index=True)

    def update_all_pairs(self, days_back: int = 30) -> Dict[str, bool]:
        """Update historical data for all pairs"""
        if not self.fetcher:
            logger.error("No Polygon API key configured")
            return {pair: False for pair in self.pairs}

        results = {}
        for i, pair in enumerate(self.pairs):
            results[pair] = self.fetcher.update_historical_csv(
                pair, self.data_dir, days_back
            )

        return results

    def get_latest_prices(self) -> Dict[str, float]:
        """Get latest closing prices for all pairs"""
        prices = {}

        for pair in self.pairs:
            df = self.load_historical_data(pair)
            if not df.empty:
                prices[pair] = df["close"].iloc[-1]

        return prices

    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON file"""
        filepath = os.path.join(self.data_dir, "..", filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved data to {filepath}")

    def load_from_json(self, filename: str) -> Optional[Dict]:
        """Load data from JSON file"""
        filepath = os.path.join(self.data_dir, "..", filename)

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r") as f:
            return json.load(f)


def create_pathway_input_connector(
    data_manager: DataManager, polling_interval: int = 300
):
    """
    Create a Pathway input connector for real-time data.

    This function sets up a Pathway-compatible data source that:
    1. Loads initial historical data from CSV
    2. Polls for new data at specified intervals
    3. Streams data into the Pathway pipeline

    Args:
        data_manager: DataManager instance
        polling_interval: Polling interval in seconds

    Returns:
        Pathway table or None if Pathway not available
    """
    try:
        import pathway as pw

        # Define schema
        class ForexOHLCV(pw.Schema):
            ts_ms: int
            open: float
            high: float
            low: float
            close: float
            volume: float
            pair: str

        # For CSV-based input (historical data)
        csv_dir = data_manager.data_dir

        # Use filesystem connector for CSV files
        # This monitors the directory for changes
        table = pw.io.csv.read(
            csv_dir,
            schema=ForexOHLCV,
            mode="streaming",
            autocommit_duration_ms=polling_interval * 1000,
        )

        logger.info(f"Created Pathway connector for {csv_dir}")
        return table

    except ImportError:
        logger.warning("Pathway not installed, using fallback data loading")
        return None
    except Exception as e:
        logger.error(f"Error creating Pathway connector: {e}")
        return None
