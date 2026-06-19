"""
Comparison Service - Manage bond comparisons
"""

import re
import uuid
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.bonds.api_functions.bond_data_processor import (
    load_bond_data,
    extract_coupon_info,
)
from app.bonds.api_functions.yield_calculator import calculate_ytm_from_price


# In-memory storage for comparisons
_comparison_storage: Dict[str, Dict[str, Any]] = {}


def extract_bond_name_from_description(isin_desc: str) -> str:
    """
    Extract clean bond name from ISIN Description using regex.

    Examples:
    - "GOVERNMENT OF INDIA 31966 GOI 12SP52 7.36 FV RS 100" -> "GOI 12SP52"
    - "STATE DEVELOPMENT LOAN 32496 TLG 11JN37 7.59 FV RS 100" -> "STATE DEVELOPMENT LOAN TLG 11JN37"
    """
    if not isin_desc:
        return ""

    desc = str(isin_desc).strip()

    # Try to extract short identifier like "GOI 12SP52"
    # Pattern: Look for codes like "GOI XXYYZZ" or similar
    code_pattern = re.compile(r"\b([A-Z]{2,4}\s+\d{2}[A-Z]{2}\d{2})\b")
    match = code_pattern.search(desc)
    if match:
        return match.group(1)

    # If no short code, extract issuer and key identifier
    # Pattern: Extract issuer name and last significant identifier
    if "GOVERNMENT OF INDIA" in desc.upper():
        # Extract "GOI XXYYZZ" pattern
        goi_pattern = re.compile(r"GOI\s+(\d{2}[A-Z]{2}\d{2})")
        goi_match = goi_pattern.search(desc)
        if goi_match:
            return f"GOI {goi_match.group(1)}"
        return "GOVERNMENT OF INDIA"

    if "STATE DEVELOPMENT LOAN" in desc.upper():
        # Extract state code and date code
        state_pattern = re.compile(
            r"STATE DEVELOPMENT LOAN\s+\d+\s+([A-Z]{2,4})\s+(\d{2}[A-Z]{2}\d{2})"
        )
        state_match = state_pattern.search(desc)
        if state_match:
            return (
                f"STATE DEVELOPMENT LOAN {state_match.group(1)} {state_match.group(2)}"
            )
        return "STATE DEVELOPMENT LOAN"

    # Fallback: return first 50 characters
    return desc[:50] if len(desc) > 50 else desc


def extract_issuer_from_description(isin_desc: str) -> str:
    """
    Extract issuer name from ISIN Description.
    """
    if not isin_desc:
        return ""

    desc = str(isin_desc).strip().upper()

    if "GOVERNMENT OF INDIA" in desc:
        return "GOVERNMENT OF INDIA"
    elif "STATE DEVELOPMENT LOAN" in desc:
        return "STATE DEVELOPMENT LOAN"
    elif "TBILL" in desc:
        return "GOVERNMENT OF INDIA"
    else:
        # Extract first significant words
        words = desc.split()
        if len(words) > 0:
            return words[0]
        return "Unknown"


def calculate_current_yield(
    coupon_rate: float, current_price: float, face_value: float = 100.0
) -> float:
    """
    Calculate current yield from coupon rate and price.
    Current Yield = (Annual Coupon Payment / Current Price)

    Returns yield as decimal (e.g., 0.075 for 7.5%)
    """
    if current_price <= 0:
        return 0.0

    annual_coupon = coupon_rate * face_value
    current_yield = annual_coupon / current_price
    return round(current_yield, 4)  # Return as decimal


def calculate_yield_change_info(pct_change: float) -> Dict[str, Any]:
    """
    Calculate yield change information from %CHNG column.

    Args:
        pct_change: Percentage change from %CHNG column (e.g., 4.99 means 4.99%)

    Returns:
        Dictionary with yield_change (as decimal), yield_change_direction, yield_change_symbol

    Note: %CHNG column in CSV contains percentage values (e.g., 4.99 = 4.99%),
    which are converted to decimal (0.0499) for calculations.
    """
    if pd.isna(pct_change) or pct_change == 0:
        return {
            "yield_change": 0.0,
            "yield_change_direction": "neutral",
            "yield_change_symbol": "—",
        }

    # Convert percentage to decimal (e.g., 4.99% -> 0.0499)
    # Verified: CSV %CHNG column contains percentage values, not decimals
    yield_change = pct_change / 100.0

    if yield_change > 0:
        return {
            "yield_change": round(yield_change, 4),
            "yield_change_direction": "up",
            "yield_change_symbol": "▲",
        }
    elif yield_change < 0:
        return {
            "yield_change": round(yield_change, 4),
            "yield_change_direction": "down",
            "yield_change_symbol": "▼",
        }
    else:
        return {
            "yield_change": 0.0,
            "yield_change_direction": "neutral",
            "yield_change_symbol": "—",
        }


def search_bonds(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search bonds from Final_Bond_Data.csv by ISIN or name.

    Args:
        query: Search query (ISIN or name)
        limit: Maximum number of results

    Returns:
        List of bond search results
    """
    import pandas as pd

    bond_df = load_bond_data()
    query_upper = query.upper().strip()

    results = []

    for _, row in bond_df.iterrows():
        isin = str(row.get("ISIN", "")).strip()
        isin_desc = str(row.get("ISIN Description", "")).strip()

        # Check if query matches ISIN or description
        if query_upper in isin.upper() or query_upper in isin_desc.upper():
            try:
                # Extract bond info
                bond_name = extract_bond_name_from_description(isin_desc)
                issuer = extract_issuer_from_description(isin_desc)
                coupon_rate = extract_coupon_info(isin_desc)
                if coupon_rate is None:
                    # FALLBACK: Default coupon rate when not found in description
                    # 7% is a reasonable default for Indian government bonds
                    coupon_rate = 0.07  # Default fallback

                maturity_date = str(row.get("Maturity Date", "")).strip()

                # Get current price
                ltp = row.get("LTP", 0.0)
                try:
                    ltp_value = (
                        float(ltp) if pd.notna(ltp) and str(ltp).strip() != "-" else 0.0
                    )
                except (ValueError, TypeError):
                    ltp_value = 0.0

                prev_close = row.get("PREV.CLOSE", 0.0)
                try:
                    prev_close_value = (
                        float(prev_close)
                        if pd.notna(prev_close) and str(prev_close).strip() != "-"
                        else 0.0
                    )
                except (ValueError, TypeError):
                    prev_close_value = 0.0

                current_price = ltp_value if ltp_value > 0 else prev_close_value
                if current_price == 0:
                    # FALLBACK: Default to face value when price data is missing
                    # This assumes bond is trading at par (100)
                    current_price = 100.0  # Default to face value

                # Calculate current yield
                current_yield = calculate_current_yield(coupon_rate, current_price)
                current_yield_percent = current_yield * 100

                # Get yield change info
                pct_change = row.get("%CHNG", 0.0)
                try:
                    pct_change_value = (
                        float(pct_change) if pd.notna(pct_change) else 0.0
                    )
                except (ValueError, TypeError):
                    pct_change_value = 0.0

                yield_change_info = calculate_yield_change_info(pct_change_value)

                results.append(
                    {
                        "isin": isin,
                        "name": bond_name,
                        "issuer": issuer,
                        "coupon_rate": coupon_rate,
                        "maturity_date": maturity_date,
                        "current_yield": current_yield,
                        "current_yield_percent": round(current_yield_percent, 2),
                        "yield_change": yield_change_info["yield_change"],
                        "yield_change_direction": yield_change_info[
                            "yield_change_direction"
                        ],
                    }
                )

                if len(results) >= limit:
                    break
            except Exception:
                continue

    return results


def get_comparison_list(
    user_id: Optional[str] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get current comparison list for user/session.

    Args:
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Comparison list dictionary
    """
    key = user_id or session_id or "default"

    if key not in _comparison_storage:
        _comparison_storage[key] = {
            "comparison_id": str(uuid.uuid4()),
            "instruments": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    return _comparison_storage[key]


def add_to_comparison(
    isin: str, user_id: Optional[str] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add bond to comparison list.

    Args:
        isin: ISIN identifier
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Updated comparison list
    """
    import pandas as pd

    key = user_id or session_id or "default"

    # Get or create comparison list
    comparison = get_comparison_list(user_id, session_id)

    # Check if already in list
    if any(inst["isin"] == isin for inst in comparison["instruments"]):
        return comparison

    # Get bond data
    bond_df = load_bond_data()
    bond_row = bond_df[bond_df["ISIN"].str.strip() == isin.strip()]

    if bond_row.empty:
        raise ValueError(f"Bond with ISIN {isin} not found")

    row = bond_row.iloc[0]
    isin_desc = str(row.get("ISIN Description", "")).strip()

    # Extract bond info
    bond_name = extract_bond_name_from_description(isin_desc)
    coupon_rate = extract_coupon_info(isin_desc)
    if coupon_rate is None:
        # FALLBACK: Default coupon rate when not found in description
        coupon_rate = 0.07  # Default fallback

    # Get current price
    ltp = row.get("LTP", 0.0)
    try:
        ltp_value = float(ltp) if pd.notna(ltp) and str(ltp).strip() != "-" else 0.0
    except (ValueError, TypeError):
        ltp_value = 0.0

    prev_close = row.get("PREV.CLOSE", 0.0)
    try:
        prev_close_value = (
            float(prev_close)
            if pd.notna(prev_close) and str(prev_close).strip() != "-"
            else 0.0
        )
    except (ValueError, TypeError):
        prev_close_value = 0.0

    current_price = ltp_value if ltp_value > 0 else prev_close_value
    if current_price == 0:
        # FALLBACK: Default to face value when price data is missing
        current_price = 100.0  # Default to face value

    # Calculate current yield
    current_yield = calculate_current_yield(coupon_rate, current_price)
    current_yield_percent = current_yield * 100

    # Get yield change info
    pct_change = row.get("%CHNG", 0.0)
    try:
        pct_change_value = float(pct_change) if pd.notna(pct_change) else 0.0
    except (ValueError, TypeError):
        pct_change_value = 0.0

    yield_change_info = calculate_yield_change_info(pct_change_value)

    # Add to comparison
    comparison["instruments"].append(
        {
            "isin": isin,
            "name": bond_name,
            "current_yield": current_yield,
            "current_yield_percent": round(current_yield_percent, 2),
            "yield_change": yield_change_info["yield_change"],
            "yield_change_direction": yield_change_info["yield_change_direction"],
            "yield_change_symbol": yield_change_info["yield_change_symbol"],
        }
    )

    comparison["last_updated"] = datetime.now().isoformat()
    _comparison_storage[key] = comparison

    return comparison


def remove_from_comparison(
    isin: str, user_id: Optional[str] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Remove bond from comparison list.

    Args:
        isin: ISIN identifier
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Updated comparison list
    """
    key = user_id or session_id or "default"

    if key not in _comparison_storage:
        raise ValueError("Comparison list not found")

    comparison = _comparison_storage[key]
    comparison["instruments"] = [
        inst for inst in comparison["instruments"] if inst["isin"] != isin
    ]

    comparison["last_updated"] = datetime.now().isoformat()
    _comparison_storage[key] = comparison

    return comparison


def get_comparison_details(comparison_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed comparison data by comparison_id.

    Args:
        comparison_id: Comparison identifier

    Returns:
        Detailed comparison data or None if not found
    """
    for key, comparison in _comparison_storage.items():
        if comparison.get("comparison_id") == comparison_id:
            return comparison

    return None
