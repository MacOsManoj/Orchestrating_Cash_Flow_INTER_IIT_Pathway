"""
Yield Data Processor - Load and process yield history from CSV
"""

import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.bonds.api_functions.yield_calculator import (
    calculate_ytm_from_price,
    calculate_yield_metrics,
    filter_by_period,
)
from app.bonds.api_functions.bond_data_processor import load_bond_data


# Cache for CSV data
_yield_data_cache: Optional[pd.DataFrame] = None
_yield_csv_path = (
    Path(__file__).parent.parent / "api_functions" / "bond_price_forecasts.csv"
)


def load_yield_data() -> pd.DataFrame:
    """Load and cache yield forecast data from CSV"""
    global _yield_data_cache
    if _yield_data_cache is None:
        _yield_data_cache = pd.read_csv(_yield_csv_path)
        # Convert date column to datetime
        _yield_data_cache["Date"] = pd.to_datetime(_yield_data_cache["Date"])
        # Sort by date (ascending) - don't modify original CSV
        _yield_data_cache = _yield_data_cache.sort_values("Date").copy()
    return _yield_data_cache


def match_bond_name_to_isin(bond_name: str) -> Optional[str]:
    """
    Match bond name from forecasts CSV to ISIN from Final_Bond_Data.csv

    Args:
        bond_name: Bond name from bond_price_forecasts.csv

    Returns:
        ISIN if found, None otherwise
    """
    try:
        bond_df = load_bond_data()

        # Try exact match first
        match = bond_df[
            bond_df["ISIN Description"].str.contains(bond_name, case=False, na=False)
        ]
        if not match.empty:
            return str(match.iloc[0]["ISIN"]).strip()

        # Try partial match on key parts
        # Extract key identifiers from bond name
        bond_name_parts = bond_name.upper().split()
        for _, row in bond_df.iterrows():
            isin_desc = str(row.get("ISIN Description", "")).upper()
            # Check if significant parts match
            if any(part in isin_desc for part in bond_name_parts if len(part) > 3):
                return str(row["ISIN"]).strip()

        return None
    except Exception:
        return None


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


def get_yield_history(
    isin: str, period: str = "1D", current_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Get yield history for a bond by ISIN.

    Args:
        isin: ISIN identifier
        period: Time period (1D, 1W, 1M, 1Y, YTD, MAX)
        current_date: Current date for filtering

    Returns:
        Dictionary with yield_data and metrics, or None if bond not found
    """
    if current_date is None:
        current_date = date.today()

    # Load yield data
    yield_df = load_yield_data()

    # Get bond name from ISIN
    bond_name = get_bond_name_from_isin(isin)
    if not bond_name:
        return None

    # Try multiple matching strategies
    bond_data = None

    # Strategy 1: Exact or partial name match
    bond_data = yield_df[
        yield_df["Bond_Name"].str.contains(bond_name, case=False, na=False)
    ]

    # Strategy 2: Extract key identifiers from bond name and match
    if bond_data.empty:
        # Extract key parts from ISIN Description (e.g., "GOI 10AG34" from "GOVERNMENT OF INDIA 04010 GOI 10AG34")
        bond_name_upper = bond_name.upper()
        # Look for patterns like "GOI XXYYZZ" or similar identifiers
        for _, row in yield_df.iterrows():
            forecast_name = str(row["Bond_Name"]).upper()
            # Check if significant parts match
            bond_words = [w for w in bond_name_upper.split() if len(w) > 2]
            forecast_words = [w for w in forecast_name.split() if len(w) > 2]
            # Check for common significant words
            common_words = set(bond_words) & set(forecast_words)
            if len(common_words) >= 2:  # At least 2 common significant words
                bond_data = yield_df[yield_df["Bond_Name"] == row["Bond_Name"]]
                break

    # Strategy 3: Try matching by extracting codes/identifiers
    if bond_data.empty:
        # Extract codes like "10AG34", "09SP35" from bond names
        import re

        # Pattern to match codes like "10AG34" (numbers + letters + numbers)
        code_pattern = re.compile(r"\b\d{2}[A-Z]{2}\d{2}\b")
        bond_codes = code_pattern.findall(bond_name.upper())

        if bond_codes:
            for code in bond_codes:
                matching = yield_df[
                    yield_df["Bond_Name"].str.contains(code, case=False, na=False)
                ]
                if not matching.empty:
                    bond_data = matching
                    break

    if bond_data is None or bond_data.empty:
        return None

    # Calculate yield for each row
    yield_points = []
    for _, row in bond_data.iterrows():
        try:
            price = float(row["Predicted_Price"])
            coupon = float(row["Coupon"])
            maturity = str(row["Maturity_Date"])
            row_date = row["Date"]

            # Get the date for this row
            if hasattr(row_date, "date"):
                row_date_obj = row_date.date()
            elif isinstance(row_date, str):
                row_date_obj = datetime.strptime(row_date, "%Y-%m-%d").date()
            else:
                row_date_obj = current_date

            # Calculate YTM from price
            ytm = calculate_ytm_from_price(
                price=price,
                coupon_rate=coupon,
                maturity_date=maturity,
                current_date=row_date_obj,
            )

            # Format date
            date_str = row_date_obj.strftime("%Y-%m-%d")
            time_str = "00:00:00"  # Forecast data doesn't have time, use default

            yield_points.append({"date": date_str, "yield": ytm, "time": time_str})
        except (ValueError, TypeError, KeyError) as e:
            continue

    if not yield_points:
        return None

    # Filter by period
    filtered_points = filter_by_period(yield_points, period, current_date)

    # Calculate metrics from all available data (not just filtered)
    metrics = calculate_yield_metrics(yield_points, current_date)

    return {
        "isin": isin,
        "period": period,
        "yield_data": filtered_points,
        "metrics": metrics,
        "last_updated": datetime.now().isoformat(),
    }
