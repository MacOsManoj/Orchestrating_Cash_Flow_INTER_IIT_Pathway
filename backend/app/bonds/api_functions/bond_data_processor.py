"""
Bond Data Processor - Handles CSV loading, data extraction, and calculations
"""

import re
import pandas as pd
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pathlib import Path


# Cache for CSV data
_csv_cache: Optional[pd.DataFrame] = None
_csv_path = Path(__file__).parent.parent / "api_functions" / "Final_Bond_Data.csv"


def load_bond_data() -> pd.DataFrame:
    """Load and cache bond data from CSV"""
    global _csv_cache
    if _csv_cache is None:
        _csv_cache = pd.read_csv(_csv_path)
        # Clean column names (remove extra spaces)
        _csv_cache.columns = _csv_cache.columns.str.strip()
    return _csv_cache


def extract_coupon_info(isin_desc: str) -> Optional[float]:
    """
    Extract coupon rate from ISIN Description using regex pattern.

    Pattern: Look for (\d+\.\d+)\s*FV first, then find numbers between 2.0-20.0
    """
    if not isin_desc:
        return None

    desc = str(isin_desc).strip()

    # First try: Look for pattern like "7.59 FV"
    match = re.search(r"(\d+\.\d+)\s*FV", desc)
    if match:
        return float(match.group(1)) / 100.0

    # Second try: Find all decimal numbers and check if they're in valid range
    numbers = re.findall(r"\b(\d+\.\d+)\b", desc)
    for num in numbers:
        rate = float(num)
        if 2.0 <= rate <= 20.0:
            return rate / 100.0

    return None


def decode_raw_date_code(raw_code: str) -> Optional[str]:
    """
    Decode Raw Date Code to extract next coupon date.

    Format appears to be: DDMMYY (e.g., "11JN37" = 11 Jan 2037, "03JN32" = 03 Jan 2032)
    But we need to extract the next coupon date, not maturity.

    Pattern analysis:
    - "11JN37" -> day 11, month JN (Jan?), year 37 (2037?)
    - "08OT26" -> day 08, month OT (Oct?), year 26 (2026?)
    - "12SP52" -> day 12, month SP (Sep?), year 52 (2052?)
    - "15DC35" -> day 15, month DC (Dec?), year 35 (2035?)

    Month codes seem to be:
    JN = January, SP = September, OT = October, DC = December

    For next coupon date, we need to find the next coupon payment date.
    Since we have maturity date, we can calculate backwards or use the raw code
    to determine the coupon schedule.

    For now, let's extract the date from raw_code and use it as next coupon if it's in the future,
    otherwise calculate next coupon from maturity.
    """
    if not raw_code or pd.isna(raw_code):
        return None

    raw_code = str(raw_code).strip()

    # Try to parse the date code
    # Pattern: DDMMYY where MM is month code
    month_map = {
        "JN": "01",
        "FB": "02",
        "MR": "03",
        "AP": "04",
        "MY": "05",
        "JN": "06",
        "JL": "07",
        "AG": "08",
        "SP": "09",
        "OT": "10",
        "NV": "11",
        "DC": "12",
    }

    # Extract day, month code, and year
    match = re.match(r"(\d{2})([A-Z]{2})(\d{2})", raw_code)
    if match:
        day = match.group(1)
        month_code = match.group(2)
        year_code = match.group(3)

        # Map month code
        month = month_map.get(month_code, "01")

        # Convert year code to full year (assuming 20XX for years < 50, 19XX otherwise)
        year_code_int = int(year_code)
        if year_code_int < 50:
            full_year = 2000 + year_code_int
        else:
            full_year = 1900 + year_code_int

        try:
            # Create date string
            date_str = f"{full_year}-{month}-{day}"
            # Validate date
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            pass

    return None


def calculate_accrued_interest(
    coupon_rate: float,
    face_value: float,
    maturity_date: str,
    current_date: Optional[date] = None,
    next_coupon_date: Optional[str] = None,
) -> float:
    """
    Calculate accrued interest.

    Formula: Accrued Interest = (Annual Coupon / Frequency) * (Days Since Last Coupon / Days in Period)

    Note: This is a simplified calculation. For accurate results, actual coupon payment dates
    should be used. Currently uses approximation if next_coupon_date is not provided.
    """
    if not coupon_rate or not face_value:
        return 0.0

    if current_date is None:
        current_date = date.today()

    try:
        maturity = datetime.strptime(maturity_date, "%Y-%m-%d").date()

        # Annual coupon amount
        annual_coupon = coupon_rate * face_value

        # Try to use next_coupon_date if provided
        if next_coupon_date:
            try:
                next_coupon = datetime.strptime(next_coupon_date, "%Y-%m-%d").date()
                # Calculate previous coupon date (6 months before next)
                from datetime import timedelta

                prev_coupon = next_coupon - timedelta(days=182)
                days_since_last = (current_date - prev_coupon).days
                days_in_period = 182  # Semi-annual period

                if days_since_last > 0 and days_since_last < days_in_period:
                    # Accrued interest for the period
                    accrued = (annual_coupon / 2) * (days_since_last / days_in_period)
                    return round(accrued, 2)
            except (ValueError, TypeError):
                pass  # Fall through to approximation

        # Approximation: assume we're halfway through the coupon period
        # NOTE: This is an approximation and may not be accurate for all bonds
        days_in_period = 182.5  # Semi-annual
        days_since_last_coupon = (
            days_in_period / 2
        )  # Approximate - assumes halfway through period

        # Accrued interest for the period
        accrued = (annual_coupon / 2) * (days_since_last_coupon / days_in_period)

        return round(accrued, 2)
    except (ValueError, TypeError):
        return 0.0


def calculate_duration(
    maturity_date: str, current_date: Optional[date] = None
) -> float:
    """
    Calculate duration as years from current date to maturity.
    """
    if not maturity_date:
        return 0.0

    if current_date is None:
        current_date = date.today()

    try:
        maturity = datetime.strptime(maturity_date, "%Y-%m-%d").date()
        years = (maturity - current_date).days / 365.25
        return round(years, 1) if years > 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


def calculate_risk_metrics(
    coupon_rate: float,
    maturity_date: str,
    current_price: float,
    face_value: float = 100.0,
    current_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Calculate risk metrics: convexity, DV01, Z-spread, VaR

    These are simplified calculations. In production, these would use
    more sophisticated bond pricing models.
    """
    if current_date is None:
        current_date = date.today()

    try:
        maturity = datetime.strptime(maturity_date, "%Y-%m-%d").date()
        years_to_maturity = (maturity - current_date).days / 365.25

        if years_to_maturity <= 0:
            return {"convexity": 0.0, "dv01": 0.0, "z_spread": 0.0, "var": 0.0}

        # Simplified Convexity calculation
        # NOTE: This is a simplified approximation. The actual convexity formula requires
        # summing all cash flows: Convexity = (1 / (1 + y)^2) * Σ [t(t+1) * C / (1+y)^t] / P
        # This approximation uses: Convexity ≈ (T^2) / (1 + y)^2 where T is time to maturity
        yield_approx = coupon_rate  # Approximate yield as coupon rate
        convexity = (years_to_maturity**2) / (1 + yield_approx) ** 2
        convexity = round(convexity, 2)

        # DV01 (Dollar Value of 01) - price change for 1bp yield change
        # DV01 ≈ -Duration * Price * 0.0001 (for $100 face value bond)
        duration = calculate_duration(maturity_date, current_date)
        dv01 = abs(duration * current_price * 0.0001)
        dv01 = round(dv01, 2)

        # Price Spread (simplified approximation)
        # NOTE: This is NOT the actual Z-spread calculation. Z-spread requires iterative
        # solving to find the spread that makes PV of cash flows equal to price.
        # This calculates price deviation from face value as a proxy.
        # Actual Z-spread = spread that solves: Price = Σ [CF / (1 + (r_i + z)^t_i)]
        price_spread = (
            (current_price - face_value) / face_value * 10000
        )  # Convert to bps
        z_spread = round(price_spread, 0)

        # VaR (Value at Risk) - simplified calculation
        # VaR ≈ Price * Duration * Yield_Volatility * Z-score
        # Using 95% confidence (Z=1.65) and assumed yield volatility
        yield_volatility = 0.0015  # 15 bps (0.15%) yield volatility per day
        z_score = 1.65  # 95% confidence
        var = abs(current_price * duration * yield_volatility * z_score)
        var = round(var, 2)

        return {
            "convexity": convexity,
            "dv01": dv01,
            "z_spread": int(z_spread),
            "var": var,
        }
    except (ValueError, TypeError, ZeroDivisionError):
        return {"convexity": 0.0, "dv01": 0.0, "z_spread": 0, "var": 0.0}


def calculate_volatility_metrics(isin: str) -> Dict[str, Optional[float]]:
    """
    Calculate volatility metrics from yield history.

    Args:
        isin: Bond ISIN identifier

    Returns:
        Dictionary with:
        - interest_rate_volatility: Annualized volatility (%)
        - credit_spread_volatility: Approximation (%)
    """
    try:
        from app.bonds.api_functions.yield_data_processor import get_yield_history
        import numpy as np

        # Get yield history (use MAX period to get all available data)
        yield_data = get_yield_history(isin, "MAX")

        if not yield_data or len(yield_data.get("yield_data", [])) < 2:
            return {"interest_rate_volatility": None, "credit_spread_volatility": None}

        # Extract yield values
        yields = [point["yield"] for point in yield_data["yield_data"]]

        if len(yields) < 2:
            return {"interest_rate_volatility": None, "credit_spread_volatility": None}

        # Calculate daily yield changes
        yield_changes = []
        for i in range(1, len(yields)):
            change = yields[i] - yields[i - 1]
            yield_changes.append(change)

        if not yield_changes:
            return {"interest_rate_volatility": None, "credit_spread_volatility": None}

        # Calculate standard deviation
        std_dev = np.std(yield_changes)

        # Annualize: σ × √252 × 100
        annualized_vol = std_dev * np.sqrt(252) * 100

        return {
            "interest_rate_volatility": round(annualized_vol, 4),
            "credit_spread_volatility": round(annualized_vol, 4),  # Approximation
        }
    except Exception:
        return {"interest_rate_volatility": None, "credit_spread_volatility": None}


def get_bond_by_isin(isin: str) -> Optional[Dict[str, Any]]:
    """
    Get bond data by ISIN and process all fields.
    """
    df = load_bond_data()

    # Find bond by ISIN
    bond_row = df[df["ISIN"].str.strip() == isin.strip()]

    if bond_row.empty:
        return None

    row = bond_row.iloc[0]
    current_date = date.today()

    # Extract basic fields
    isin_value = str(row.get("ISIN", "")).strip()
    isin_desc = str(row.get("ISIN Description", "")).strip()
    maturity_date = str(row.get("Maturity Date", "")).strip()
    raw_date_code = (
        str(row.get("Raw Date Code", "")).strip()
        if pd.notna(row.get("Raw Date Code"))
        else ""
    )
    face_value = (
        float(row.get("FACE VALUE", 100.0))
        if pd.notna(row.get("FACE VALUE"))
        else 100.0
    )

    # Handle LTP - may be '-' or other non-numeric values
    ltp_value = row.get("LTP", 0.0)
    try:
        ltp = (
            float(ltp_value)
            if pd.notna(ltp_value) and str(ltp_value).strip() != "-"
            else 0.0
        )
    except (ValueError, TypeError):
        ltp = 0.0

    # Handle PREV.CLOSE - may be '-' or other non-numeric values
    prev_close_value = row.get("PREV.CLOSE", 0.0)
    try:
        prev_close = (
            float(prev_close_value)
            if pd.notna(prev_close_value) and str(prev_close_value).strip() != "-"
            else 0.0
        )
    except (ValueError, TypeError):
        prev_close = 0.0
    symbol = str(row.get("SYMBOL", "")).strip() if pd.notna(row.get("SYMBOL")) else ""

    # Extract coupon rate
    coupon_rate = extract_coupon_info(isin_desc)

    # Decode next coupon date
    next_coupon_date = decode_raw_date_code(raw_date_code)
    # If decoded date is in the past or None, try to estimate from maturity
    if next_coupon_date:
        try:
            coupon_date = datetime.strptime(next_coupon_date, "%Y-%m-%d").date()
            if coupon_date < current_date:
                # Date is in the past, calculate next coupon from maturity
                # For semi-annual, go back 6 months from maturity (approx 182 days)
                maturity = datetime.strptime(maturity_date, "%Y-%m-%d").date()
                from datetime import timedelta

                # Approximate 6 months as 182 days
                next_coupon_date = (maturity - timedelta(days=182)).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass

    # Calculate fields
    duration_years = calculate_duration(maturity_date, current_date)
    accrued_int = calculate_accrued_interest(
        coupon_rate or 0.0, face_value, maturity_date, current_date, next_coupon_date
    )
    risk_metrics = calculate_risk_metrics(
        coupon_rate or 0.0,
        maturity_date,
        ltp if ltp > 0 else prev_close,
        face_value,
        current_date,
    )

    # Calculate YTM
    current_price = ltp if ltp > 0 else prev_close
    ytm = None
    if coupon_rate and current_price > 0:
        from app.bonds.api_functions.yield_calculator import calculate_ytm_from_price
        ytm = calculate_ytm_from_price(
            current_price, coupon_rate, maturity_date, current_date, face_value
        )

    # Calculate volatility metrics
    volatility_metrics = calculate_volatility_metrics(isin_value)

    # Extract credit rating (check for rating column in CSV)
    credit_rating = None
    rating_columns = ["RATING", "Credit Rating", "Rating", "CREDIT_RATING"]
    for col in rating_columns:
        if col in df.columns:
            rating_value = row.get(col)
            if pd.notna(rating_value) and str(rating_value).strip():
                credit_rating = str(rating_value).strip()
                break

    # Build response
    result = {
        "isin": isin_value,
        "bond_name": isin_desc,
        "symbol": symbol,
        "coupon_rate": round(coupon_rate, 4) if coupon_rate else None,
        "maturity_date": maturity_date,
        "next_coupon_date": next_coupon_date,
        "minimum_increment": face_value,
        "last_price": round(ltp, 2) if ltp > 0 else round(prev_close, 2),
        "clean_price": round(prev_close, 2) if prev_close > 0 else round(ltp, 2),
        "accrued_interest": accrued_int,
        "duration": duration_years,
        "convexity": risk_metrics["convexity"],
        "dv01": risk_metrics["dv01"],
        "z_spread": risk_metrics["z_spread"],
        "var": risk_metrics["var"],
        "ytm": round(ytm, 6) if ytm else None,
        "interest_rate_volatility": volatility_metrics["interest_rate_volatility"],
        "credit_spread_volatility": volatility_metrics["credit_spread_volatility"],
        "credit_rating": credit_rating,
    }

    return result


def get_all_bonds() -> List[Dict[str, Any]]:
    """
    Get all bonds with basic information for universe endpoint.
    """
    df = load_bond_data()
    bonds = []

    for _, row in df.iterrows():
        isin = str(row.get("ISIN", "")).strip()
        if not isin:
            continue

        isin_desc = str(row.get("ISIN Description", "")).strip()
        maturity_date = str(row.get("Maturity Date", "")).strip()

        # Handle LTP - may be '-' or other non-numeric values
        ltp_value = row.get("LTP", 0.0)
        try:
            ltp = (
                float(ltp_value)
                if pd.notna(ltp_value) and str(ltp_value).strip() != "-"
                else 0.0
            )
        except (ValueError, TypeError):
            ltp = 0.0

        # Handle PREV.CLOSE - may be '-' or other non-numeric values
        prev_close_value = row.get("PREV.CLOSE", 0.0)
        try:
            prev_close = (
                float(prev_close_value)
                if pd.notna(prev_close_value) and str(prev_close_value).strip() != "-"
                else 0.0
            )
        except (ValueError, TypeError):
            prev_close = 0.0

        coupon_rate = extract_coupon_info(isin_desc)

        bonds.append(
            {
                "isin": isin,
                "bond_name": isin_desc,
                "coupon_rate": round(coupon_rate, 4) if coupon_rate else None,
                "maturity_date": maturity_date,
                "last_price": round(ltp, 2) if ltp > 0 else round(prev_close, 2),
            }
        )

    return bonds
