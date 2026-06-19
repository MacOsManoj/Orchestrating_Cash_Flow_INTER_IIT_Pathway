"""
Rate vs Yield Overlay Data Processor
"""

import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.bonds.api_functions.yield_calculator import (
    calculate_ytm_from_price,
    filter_by_period,
)
from app.bonds.api_functions.bond_data_processor import (
    load_bond_data,
    extract_coupon_info,
)
from app.bonds.api_functions.yield_data_processor import load_yield_data


def get_rate_yield_overlay(
    isin: str, period: str = "1Y", current_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Get rate vs yield overlay data for a bond.

    Args:
        isin: ISIN identifier
        period: Time period (5Y, 3Y, 1Y, YTD)
        current_date: Current date for filtering

    Returns:
        Dictionary with overlay data, or None if bond not found
    """
    if current_date is None:
        current_date = date.today()

    # Load bond data to get bond info
    bond_df = load_bond_data()
    bond_row = bond_df[bond_df["ISIN"].str.strip() == isin.strip()]

    if bond_row.empty:
        return None

    row = bond_row.iloc[0]

    # Extract bond info
    coupon_rate = extract_coupon_info(str(row.get("ISIN Description", "")))
    if coupon_rate is None:
        # FALLBACK: Default coupon rate when not found in description
        # 7% is a reasonable default for Indian government bonds
        coupon_rate = 0.07  # Default fallback

    maturity_date = str(row.get("Maturity Date", "")).strip()
    if not maturity_date:
        return None

    # Try to get historical yield data from bond_price_forecasts.csv
    yield_df = load_yield_data()

    # Get bond name from ISIN Description
    isin_desc = str(row.get("ISIN Description", "")).strip()

    # Use the same matching strategies as yield_history to get all historical data
    bond_data = None

    # Strategy 1: Exact or partial name match
    bond_data = yield_df[
        yield_df["Bond_Name"].str.contains(isin_desc, case=False, na=False)
    ]

    # Strategy 2: Extract key identifiers from bond name and match
    if bond_data.empty:
        bond_name_upper = isin_desc.upper()
        for _, forecast_row in yield_df.iterrows():
            forecast_name = str(forecast_row["Bond_Name"]).upper()
            bond_words = [w for w in bond_name_upper.split() if len(w) > 2]
            forecast_words = [w for w in forecast_name.split() if len(w) > 2]
            common_words = set(bond_words) & set(forecast_words)
            if len(common_words) >= 2:  # At least 2 common significant words
                bond_data = yield_df[yield_df["Bond_Name"] == forecast_row["Bond_Name"]]
                break

    # Strategy 3: Try matching by extracting codes/identifiers
    if bond_data.empty:
        import re

        # Pattern to match codes like "10AG34", "12SP52" (numbers + letters + numbers)
        code_pattern = re.compile(r"\b\d{2}[A-Z]{2}\d{2}\b")
        bond_codes = code_pattern.findall(isin_desc.upper())
        if bond_codes:
            for code in bond_codes:
                matching = yield_df[
                    yield_df["Bond_Name"].str.contains(code, case=False, na=False)
                ]
                if not matching.empty:
                    bond_data = matching
                    break

    overlay_data = []

    if bond_data is not None and not bond_data.empty:
        # Use historical data from forecasts
        for _, yield_row in bond_data.iterrows():
            try:
                price = float(yield_row["Predicted_Price"])
                row_date = yield_row["Date"]

                if hasattr(row_date, "date"):
                    row_date_obj = row_date.date()
                elif isinstance(row_date, str):
                    row_date_obj = datetime.strptime(row_date, "%Y-%m-%d").date()
                else:
                    continue

                # Calculate YTM from price
                ytm = calculate_ytm_from_price(
                    price=price,
                    coupon_rate=coupon_rate,
                    maturity_date=maturity_date,
                    current_date=row_date_obj,
                )

                # Policy rate - PLACEHOLDER/APPROXIMATION
                # NOTE: This is a placeholder calculation. In production, policy rate should
                # come from an actual data source (e.g., RBI repo rate, Fed funds rate).
                # This approximation (60% of yield) is arbitrary and should be replaced
                # with real policy rate data.
                policy_rate = (
                    ytm * 0.6
                )  # PLACEHOLDER: Approximate policy rate as 60% of yield

                overlay_data.append(
                    {
                        "date": row_date_obj.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "policy_rate": round(
                            policy_rate * 100, 2
                        ),  # Convert to percentage
                        "yield_10y": round(ytm * 100, 2),  # Convert to percentage
                    }
                )
            except (ValueError, TypeError, KeyError):
                continue

    # If no historical data, create a single current data point
    if not overlay_data:
        try:
            ltp = (
                float(row.get("LTP", 0))
                if pd.notna(row.get("LTP")) and str(row.get("LTP")).strip() != "-"
                else 0.0
            )
            if ltp == 0:
                prev_close = (
                    float(row.get("PREV.CLOSE", 0))
                    if pd.notna(row.get("PREV.CLOSE"))
                    and str(row.get("PREV.CLOSE")).strip() != "-"
                    else 0.0
                )
                # FALLBACK: Default to face value when price data is missing
                price = prev_close if prev_close > 0 else 100.0  # Default to face value
            else:
                price = ltp

            ytm = calculate_ytm_from_price(
                price=price,
                coupon_rate=coupon_rate,
                maturity_date=maturity_date,
                current_date=current_date,
            )

            # PLACEHOLDER: Policy rate approximation (see note above)
            policy_rate = (
                ytm * 0.6
            )  # PLACEHOLDER: Approximate policy rate as 60% of yield

            overlay_data.append(
                {
                    "date": current_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "policy_rate": round(policy_rate * 100, 2),
                    "yield_10y": round(ytm * 100, 2),
                }
            )
        except (ValueError, TypeError):
            return None

    # Filter by period
    if period == "5Y":
        cutoff_date = current_date - timedelta(days=365 * 5)
    elif period == "3Y":
        cutoff_date = current_date - timedelta(days=365 * 3)
    elif period == "1Y":
        cutoff_date = current_date - timedelta(days=365)
    elif period == "YTD":
        cutoff_date = date(current_date.year, 1, 1)
    else:
        cutoff_date = current_date - timedelta(days=365)

    filtered_data = [
        point
        for point in overlay_data
        if datetime.strptime(point["date"].split("T")[0], "%Y-%m-%d").date()
        >= cutoff_date
    ]

    # Sort by date
    filtered_data = sorted(filtered_data, key=lambda x: x["date"])

    # Calculate Y-axis ranges
    if filtered_data:
        yields = [p["yield_10y"] for p in filtered_data]
        policy_rates = [p["policy_rate"] for p in filtered_data]
        yield_min = max(0.0, min(yields) - 0.5)
        yield_max = max(yields) + 0.5
        policy_min = max(0.0, min(policy_rates) - 0.5)
        policy_max = max(policy_rates) + 0.5
    else:
        yield_min = yield_max = policy_min = policy_max = 0.0

    return {
        "isin": isin,
        "period": period,
        "data": filtered_data,
        "series": [
            {
                "name": "Policy Rate",
                "data_key": "policy_rate",
                "color": "light_blue",
                "y_axis": "left",
            },
            {
                "name": "10Y Yield",
                "data_key": "yield_10y",
                "color": "white",
                "y_axis": "right",
            },
        ],
        "y_axes": {
            "left": {
                "label": "Policy Rate (%)",
                "min": round(policy_min, 1),
                "max": round(policy_max, 1),
            },
            "right": {
                "label": "10Y Yield (%)",
                "min": round(yield_min, 1),
                "max": round(yield_max, 1),
            },
        },
        "last_updated": datetime.now().isoformat() + "Z",
    }
