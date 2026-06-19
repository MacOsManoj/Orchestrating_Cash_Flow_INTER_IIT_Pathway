"""
Price Statistics Processor - Load and process price history from CSV
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.bonds.api_functions.bond_data_processor import load_bond_data


# Cache for CSV data
_price_data_cache: Optional[pd.DataFrame] = None
_price_csv_path = (
    Path(__file__).parent.parent / "api_functions" / "bond_price_forecasts.csv"
)


def load_price_data() -> pd.DataFrame:
    """Load and cache price forecast data from CSV"""
    global _price_data_cache
    if _price_data_cache is None:
        _price_data_cache = pd.read_csv(_price_csv_path)
        # Convert date column to datetime
        _price_data_cache["Date"] = pd.to_datetime(_price_data_cache["Date"])
        # Sort by date (ascending)
        _price_data_cache = _price_data_cache.sort_values("Date").copy()
    return _price_data_cache


def get_bond_name_from_isin(isin: str) -> Optional[str]:
    """
    Get bond name from ISIN using Final_Bond_Data.csv

    Args:
        isin: ISIN identifier

    Returns:
        Bond name if found, None otherwise
    """
    try:
        bond_df = load_bond_data()
        match = bond_df[bond_df["ISIN"].str.strip() == isin.strip()]
        if not match.empty:
            return str(match.iloc[0]["ISIN Description"]).strip()
        return None
    except Exception:
        return None


def filter_price_by_period(
    price_data: List[Dict[str, Any]], period: str, current_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Filter price data by time period.

    Args:
        price_data: List of price data points
        period: Period string (1D, 1W, 1M, 3M, YTD, 1Y, MAX)
        current_date: Current date for filtering

    Returns:
        Filtered list of price data points
    """
    if not price_data:
        return []

    if current_date is None:
        current_date = date.today()

    if period == "MAX":
        return sorted(price_data, key=lambda x: x["date"])

    # Calculate cutoff date
    if period == "1D":
        cutoff_date = current_date - timedelta(days=1)
    elif period == "1W":
        cutoff_date = current_date - timedelta(days=7)
    elif period == "1M":
        cutoff_date = current_date - timedelta(days=30)
    elif period == "3M":
        cutoff_date = current_date - timedelta(days=90)
    elif period == "1Y":
        cutoff_date = current_date - timedelta(days=365)
    elif period == "YTD":
        cutoff_date = date(current_date.year, 1, 1)
    else:
        # Default to 1D
        cutoff_date = current_date - timedelta(days=1)

    # Filter data
    filtered = []
    for data_point in price_data:
        data_date = (
            datetime.strptime(data_point["date"], "%Y-%m-%d").date()
            if isinstance(data_point["date"], str)
            else data_point["date"]
        )
        if data_date >= cutoff_date:
            filtered.append(data_point)

    # Sort by date ascending
    return sorted(filtered, key=lambda x: x["date"])


def calculate_implied_volatility(prices: List[float]) -> float:
    """
    Calculate implied volatility from price returns.

    Formula: σ(returns) × √252 × 100

    Args:
        prices: List of price values (sorted by date)

    Returns:
        Implied volatility as percentage (e.g., 0.71 for 0.71%)
    """
    if len(prices) < 2:
        return 0.0

    try:
        # Calculate daily returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(daily_return)

        if len(returns) < 2:
            # Fallback: use price standard deviation as approximation
            if len(prices) > 1:
                mean_price = np.mean(prices)
                if mean_price > 0:
                    price_std = np.std(prices)
                    annualized_vol = (price_std / mean_price) * np.sqrt(252)
                    return round(annualized_vol * 100, 2)
            return 0.0

        # Calculate standard deviation of returns
        returns_std = np.std(returns)

        # Annualize: multiply by √252 (trading days per year)
        annualized_vol = returns_std * np.sqrt(252)

        # Convert to percentage
        implied_vol = annualized_vol * 100

        return round(implied_vol, 2)
    except Exception:
        return 0.0


def calculate_price_metrics(prices: List[float]) -> Dict[str, float]:
    """
    Calculate statistical metrics from price data.

    Args:
        prices: List of price values

    Returns:
        Dictionary with median_price, price_5th_percentile, price_95th_percentile, implied_volatility
    """
    if not prices:
        return {
            "median_price": 0.0,
            "price_5th_percentile": 0.0,
            "price_95th_percentile": 0.0,
            "implied_volatility": 0.0,
        }

    try:
        prices_array = np.array(prices)

        # Calculate median
        median_price = float(np.median(prices_array))

        # Calculate percentiles
        price_5th_percentile = float(np.percentile(prices_array, 5))
        price_95th_percentile = float(np.percentile(prices_array, 95))

        # Calculate implied volatility
        implied_volatility = calculate_implied_volatility(prices)

        return {
            "median_price": round(median_price, 2),
            "price_5th_percentile": round(price_5th_percentile, 2),
            "price_95th_percentile": round(price_95th_percentile, 2),
            "implied_volatility": implied_volatility,
        }
    except Exception:
        return {
            "median_price": 0.0,
            "price_5th_percentile": 0.0,
            "price_95th_percentile": 0.0,
            "implied_volatility": 0.0,
        }


def get_price_statistics(
    isin: str, period: str = "1D", current_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Get price statistics for a bond by ISIN.

    Args:
        isin: ISIN identifier
        period: Time period (1D, 1W, 1M, 3M, YTD, 1Y, MAX)
        current_date: Current date for filtering

    Returns:
        Dictionary with price_data and metrics, or None if bond not found
    """
    if current_date is None:
        current_date = date.today()

    # Load price data
    price_df = load_price_data()

    # Get bond name from ISIN
    bond_name = get_bond_name_from_isin(isin)
    if not bond_name:
        return None

    # Try multiple matching strategies (same as yield_data_processor)
    bond_data = None

    # Strategy 1: Exact or partial name match
    bond_data = price_df[
        price_df["Bond_Name"].str.contains(bond_name, case=False, na=False)
    ]

    # Strategy 2: Extract key identifiers from bond name and match
    if bond_data.empty:
        bond_name_upper = bond_name.upper()
        for _, row in price_df.iterrows():
            forecast_name = str(row["Bond_Name"]).upper()
            bond_words = [w for w in bond_name_upper.split() if len(w) > 2]
            forecast_words = [w for w in forecast_name.split() if len(w) > 2]
            common_words = set(bond_words) & set(forecast_words)
            if len(common_words) >= 2:
                bond_data = price_df[price_df["Bond_Name"] == row["Bond_Name"]]
                break

    # Strategy 3: Try matching by extracting codes/identifiers
    if bond_data.empty:
        import re

        code_pattern = re.compile(r"\b\d{2}[A-Z]{2}\d{2}\b")
        bond_codes = code_pattern.findall(bond_name.upper())

        if bond_codes:
            for code in bond_codes:
                matching = price_df[
                    price_df["Bond_Name"].str.contains(code, case=False, na=False)
                ]
                if not matching.empty:
                    bond_data = matching
                    break

    if bond_data is None or bond_data.empty:
        return None

    # Extract price data
    price_points = []
    all_prices = []

    for _, row in bond_data.iterrows():
        try:
            price = float(row["Predicted_Price"])
            row_date = row["Date"]

            # Get the date for this row
            if hasattr(row_date, "date"):
                row_date_obj = row_date.date()
            elif isinstance(row_date, str):
                row_date_obj = datetime.strptime(row_date, "%Y-%m-%d").date()
            else:
                row_date_obj = current_date

            date_str = row_date_obj.strftime("%Y-%m-%d")

            price_points.append({"date": date_str, "price": price})
            all_prices.append(price)
        except (ValueError, TypeError, KeyError):
            continue

    if not price_points:
        return None

    # Filter by period
    filtered_points = filter_price_by_period(price_points, period, current_date)

    # Calculate metrics from filtered data
    filtered_prices = [p["price"] for p in filtered_points]
    metrics = calculate_price_metrics(filtered_prices)

    # Calculate percentile bands for each data point (rolling calculation)
    # For each point, calculate percentiles from all data up to that point
    price_data_with_bands = []
    for i, point in enumerate(filtered_points):
        # Get all prices up to current point (inclusive)
        prices_up_to_point = [p["price"] for p in filtered_points[: i + 1]]

        if prices_up_to_point:
            price_5th = float(np.percentile(prices_up_to_point, 5))
            price_95th = float(np.percentile(prices_up_to_point, 95))
        else:
            price_5th = point["price"]
            price_95th = point["price"]

        price_data_with_bands.append(
            {
                "date": point["date"],
                "price": round(point["price"], 2),
                "price_5th_percentile": round(price_5th, 2),
                "price_95th_percentile": round(price_95th, 2),
            }
        )

    return {
        "isin": isin,
        "period": period,
        "price_data": price_data_with_bands,
        "metrics": metrics,
        "last_updated": datetime.now().isoformat(),
    }
