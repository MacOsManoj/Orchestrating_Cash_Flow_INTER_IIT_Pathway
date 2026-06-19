"""
Yield Calculator - Calculate YTM from price and compute yield metrics
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
from scipy.optimize import fsolve


def calculate_ytm_from_price(
    price: float,
    coupon_rate: float,
    maturity_date: str,
    current_date: Optional[date] = None,
    face_value: float = 100.0,
    frequency: int = 2,
) -> float:
    """
    Calculate Yield to Maturity (YTM) from bond price using iterative method.

    Args:
        price: Current bond price
        coupon_rate: Annual coupon rate (as decimal, e.g., 0.075 for 7.5%)
        maturity_date: Maturity date string (YYYY-MM-DD)
        current_date: Current date (default: today)
        face_value: Face value of bond (default: 100.0)
        frequency: Payment frequency per year (default: 2 for semi-annual)

    Returns:
        YTM as decimal (e.g., 0.079 for 7.9%)
    """
    if current_date is None:
        current_date = date.today()

    try:
        maturity = datetime.strptime(maturity_date, "%Y-%m-%d").date()
        years_to_maturity = (maturity - current_date).days / 365.25

        if years_to_maturity <= 0:
            return coupon_rate  # If matured, return coupon rate

        # Calculate number of periods
        n = int(years_to_maturity * frequency)
        if n == 0:
            return coupon_rate

        # Coupon payment per period
        coupon_payment = (coupon_rate * face_value) / frequency

        # Define the bond pricing function
        def bond_price_func(ytm):
            """Bond price as function of YTM"""
            y = ytm / frequency
            if y == 0:
                return coupon_payment * n + face_value

            # Present value of coupon payments
            pv_coupons = coupon_payment * (1 - (1 + y) ** (-n)) / y

            # Present value of face value
            pv_face = face_value / ((1 + y) ** n)

            return pv_coupons + pv_face

        # Objective function: difference between calculated and actual price
        def objective(ytm):
            return bond_price_func(ytm) - price

        # Initial guess: use coupon rate
        initial_guess = coupon_rate

        # Use fsolve to find YTM
        try:
            ytm = fsolve(objective, initial_guess)[0]
            # Ensure reasonable bounds (0% to 50%)
            ytm = max(0.0, min(0.50, ytm))
            return float(ytm)
        except:
            # Fallback: use approximation
            # Simple approximation: YTM ≈ (C + (FV - Price)/n) / ((FV + Price)/2)
            # where C is annual coupon, n is number of periods
            annual_coupon = coupon_rate * face_value
            n_periods = n  # Use number of periods from above calculation
            price_diff_per_period = (face_value - price) / n_periods
            avg_price = (face_value + price) / 2
            ytm_approx = (annual_coupon + price_diff_per_period) / avg_price
            return max(0.0, min(0.50, ytm_approx))

    except (ValueError, TypeError, ZeroDivisionError) as e:
        # Return coupon rate as fallback
        return coupon_rate


def calculate_yield_metrics(
    yield_data: List[Dict[str, Any]], current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculate yield metrics: current yielding, 1-month change, volatility, max drawdown.

    Args:
        yield_data: List of dicts with 'date' and 'yield' keys
        current_date: Current date for calculations

    Returns:
        Dictionary with metrics
    """
    if not yield_data or len(yield_data) == 0:
        return {
            "current_yielding": 0.0,
            "current_yielding_percent": 0.0,
            "one_month_change": 0.0,
            "one_month_change_unit": "bps",
            "volatility_20d": 0.0,
            "volatility_20d_percent": 0.0,
            "max_drawdown_1y": 0.0,
            "max_drawdown_1y_percent": 0.0,
        }

    if current_date is None:
        current_date = date.today()

    # Sort by date (most recent first)
    sorted_data = sorted(yield_data, key=lambda x: x["date"], reverse=True)

    # Current yielding (latest yield)
    current_yielding = sorted_data[0]["yield"] if sorted_data else 0.0
    current_yielding_percent = current_yielding * 100

    # 1-Month Change
    one_month_ago = current_date - timedelta(days=30)
    one_month_yield = None
    for data_point in sorted_data:
        data_date = (
            datetime.strptime(data_point["date"], "%Y-%m-%d").date()
            if isinstance(data_point["date"], str)
            else data_point["date"]
        )
        if data_date <= one_month_ago:
            one_month_yield = data_point["yield"]
            break

    if one_month_yield is not None:
        one_month_change = (
            current_yielding - one_month_yield
        ) * 10000  # Convert to bps
    else:
        # Use first available data point if 1 month ago not available
        if len(sorted_data) > 1:
            one_month_change = (current_yielding - sorted_data[-1]["yield"]) * 10000
        else:
            one_month_change = 0.0

    # Volatility (20D σ) - Standard deviation of last 20 days
    yields_20d = []
    cutoff_date = current_date - timedelta(days=20)

    for data_point in sorted_data:
        data_date = (
            datetime.strptime(data_point["date"], "%Y-%m-%d").date()
            if isinstance(data_point["date"], str)
            else data_point["date"]
        )
        if data_date >= cutoff_date:
            yields_20d.append(data_point["yield"])
        else:
            break

    if len(yields_20d) >= 2:
        volatility_20d = np.std(yields_20d)
        volatility_20d_percent = volatility_20d * 100
    else:
        volatility_20d = 0.0
        volatility_20d_percent = 0.0

    # Max Drawdown (1Y) - Maximum peak-to-trough decline in last year
    one_year_ago = current_date - timedelta(days=365)
    yields_1y = []

    for data_point in sorted_data:
        data_date = (
            datetime.strptime(data_point["date"], "%Y-%m-%d").date()
            if isinstance(data_point["date"], str)
            else data_point["date"]
        )
        if data_date >= one_year_ago:
            yields_1y.append(data_point["yield"])
        else:
            break

    if len(yields_1y) >= 2:
        # Calculate running maximum
        running_max = yields_1y[0]
        max_drawdown = 0.0

        for yield_val in yields_1y:
            if yield_val > running_max:
                running_max = yield_val
            drawdown = (
                (running_max - yield_val) / running_max if running_max > 0 else 0.0
            )
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_1y = max_drawdown
        max_drawdown_1y_percent = max_drawdown_1y * 100
    else:
        max_drawdown_1y = 0.0
        max_drawdown_1y_percent = 0.0

    return {
        "current_yielding": round(current_yielding, 4),
        "current_yielding_percent": round(current_yielding_percent, 2),
        "one_month_change": round(one_month_change, 1),
        "one_month_change_unit": "bps",
        "volatility_20d": round(volatility_20d, 6),
        "volatility_20d_percent": round(volatility_20d_percent, 2),
        "max_drawdown_1y": round(max_drawdown_1y, 4),
        "max_drawdown_1y_percent": round(max_drawdown_1y_percent, 2),
    }


def filter_by_period(
    yield_data: List[Dict[str, Any]], period: str, current_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Filter yield data by time period.

    Args:
        yield_data: List of yield data points
        period: Period string (1D, 1W, 1M, 1Y, YTD, MAX)
        current_date: Current date for filtering

    Returns:
        Filtered list of yield data points
    """
    if not yield_data:
        return []

    if current_date is None:
        current_date = date.today()

    if period == "MAX":
        return sorted(yield_data, key=lambda x: x["date"])

    # Calculate cutoff date
    if period == "1D":
        cutoff_date = current_date - timedelta(days=1)
    elif period == "1W":
        cutoff_date = current_date - timedelta(days=7)
    elif period == "1M":
        cutoff_date = current_date - timedelta(days=30)
    elif period == "1Y":
        cutoff_date = current_date - timedelta(days=365)
    elif period == "YTD":
        cutoff_date = date(current_date.year, 1, 1)
    else:
        # Default to 1D
        cutoff_date = current_date - timedelta(days=1)

    # Filter data
    filtered = []
    for data_point in yield_data:
        data_date = (
            datetime.strptime(data_point["date"], "%Y-%m-%d").date()
            if isinstance(data_point["date"], str)
            else data_point["date"]
        )
        if data_date >= cutoff_date:
            filtered.append(data_point)

    # Sort by date ascending
    return sorted(filtered, key=lambda x: x["date"])
