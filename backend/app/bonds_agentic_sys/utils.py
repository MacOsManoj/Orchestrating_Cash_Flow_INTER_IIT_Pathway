"""
Utility functions for bond calculations and analysis
"""
from datetime import datetime, date
from typing import Tuple, Optional, List
import numpy as np


def calculate_duration(
    coupon_rate: float,
    ytm: float,
    years_to_maturity: float,
    frequency: int = 2,  # Semi-annual payments
) -> Tuple[float, float]:
    """
    Calculate Macaulay and Modified Duration

    Args:
        coupon_rate: Annual coupon rate as percentage (e.g., 7.5)
        ytm: Yield to maturity as percentage (e.g., 7.0)
        years_to_maturity: Years until maturity
        frequency: Payment frequency per year (default 2 for semi-annual)
    Returns:
        Tuple of (Macaulay Duration, Modified Duration)
    """
    if years_to_maturity <= 0:
        return (0.0, 0.0)

    coupon = coupon_rate / 100 / frequency
    y = ytm / 100 / frequency
    n = int(years_to_maturity * frequency)

    if n == 0:
        return (0.0, 0.0)

    # Calculate present value of each cash flow
    pv_sum = 0
    weighted_pv_sum = 0

    for t in range(1, n + 1):
        # Cash flow at time t
        cf = coupon
        if t == n:
            cf += 1  # Add principal at maturity

        pv = cf / ((1 + y) ** t)
        pv_sum += pv
        weighted_pv_sum += t * pv

    # Macaulay Duration (in years)
    if pv_sum > 0:
        mac_duration = (weighted_pv_sum / pv_sum) / frequency
    else:
        mac_duration = years_to_maturity

    # Modified Duration
    mod_duration = mac_duration / (1 + y)

    return (mac_duration, mod_duration)


def calculate_convexity(
    coupon_rate: float, ytm: float, years_to_maturity: float, frequency: int = 2
) -> float:
    """
    Calculate bond convexity

    Args:
        coupon_rate: Annual coupon rate as percentage
        ytm: Yield to maturity as percentage
        years_to_maturity: Years until maturity
        frequency: Payment frequency per year
    Returns:
        Convexity value
    """
    if years_to_maturity <= 0:
        return 0.0

    coupon = coupon_rate / 100 / frequency
    y = ytm / 100 / frequency
    n = int(years_to_maturity * frequency)

    if n == 0:
        return 0.0

    # Calculate present value and convexity numerator
    pv_sum = 0
    convexity_sum = 0

    for t in range(1, n + 1):
        cf = coupon
        if t == n:
            cf += 1

        pv = cf / ((1 + y) ** t)
        pv_sum += pv
        convexity_sum += t * (t + 1) * pv

    if pv_sum > 0:
        convexity = convexity_sum / (pv_sum * (1 + y) ** 2 * frequency**2)
    else:
        convexity = 0.0

    return convexity


def price_bond(
    coupon_rate: float,
    ytm: float,
    years_to_maturity: float,
    face_value: float = 100.0,
    frequency: int = 2,
) -> float:
    """
    Calculate the price of a bond

    Args:
        coupon_rate: Annual coupon rate as percentage
        ytm: Yield to maturity as percentage
        years_to_maturity: Years until maturity
        face_value: Face/par value of the bond
        frequency: Payment frequency per year
    Returns:
        Bond price
    """
    if years_to_maturity <= 0:
        return face_value

    coupon = (coupon_rate / 100) * face_value / frequency
    y = ytm / 100 / frequency
    n = int(years_to_maturity * frequency)

    if n == 0:
        return face_value

    # Present value of coupon payments
    if y > 0:
        pv_coupons = coupon * (1 - (1 + y) ** (-n)) / y
    else:
        pv_coupons = coupon * n

    # Present value of face value
    pv_face = face_value / ((1 + y) ** n)

    return pv_coupons + pv_face


def years_to_maturity(maturity_date) -> float:
    """
    Calculate years to maturity from today

    Args:
        maturity_date: Maturity date (datetime or date object)

    Returns:
        Years to maturity as float
    """
    if maturity_date is None:
        return 0.0

    today = datetime.now().date()

    if isinstance(maturity_date, datetime):
        maturity = maturity_date.date()
    elif isinstance(maturity_date, date):
        maturity = maturity_date
    else:
        # Try to parse string
        try:
            maturity = datetime.strptime(str(maturity_date), "%Y-%m-%d").date()
        except:
            return 0.0
    days_to_maturity = (maturity - today).days
    return max(0.0, days_to_maturity / 365.25)


def interpolate_yield(yield_curve, years: float) -> float:
    """
    Interpolate yield from yield curve

    Args:
        yield_curve: YieldCurve object with rates dict {tenor: yield}
        years: Years for which to interpolate

    Returns:
        Interpolated yield
    """
    if yield_curve is None or not hasattr(yield_curve, "rates"):
        return 7.0  # Default yield

    rates = yield_curve.rates
    if not rates:
        return 7.0

    # Get sorted tenors
    tenors = sorted(rates.keys())

    if years <= tenors[0]:
        return rates[tenors[0]]
    if years >= tenors[-1]:
        return rates[tenors[-1]]
    # Linear interpolation
    for i in range(len(tenors) - 1):
        if tenors[i] <= years <= tenors[i + 1]:
            t1, t2 = tenors[i], tenors[i + 1]
            y1, y2 = rates[t1], rates[t2]
            return y1 + (y2 - y1) * (years - t1) / (t2 - t1)
    return 7.0


def calculate_liquidity_score(
    bid: float,
    ask: float,
    volume: float,
    max_spread: float = 2.0,
    max_volume: float = 1000000000,
) -> float:
    """
    Calculate liquidity score based on bid-ask spread and volume

    Args:
        bid: Bid price
        ask: Ask price
        volume: Trading volume
        max_spread: Maximum spread for normalization
        max_volume: Maximum volume for normalization
    Returns:
        Liquidity score between 0 and 1
    """
    if bid <= 0 or ask <= 0:
        return 0.3  # Default low liquidity

    # Bid-ask spread as percentage
    mid = (bid + ask) / 2
    spread = (ask - bid) / mid * 100

    # Spread component (lower is better)
    spread_score = max(0, 1 - spread / max_spread)

    # Volume component (higher is better)
    volume_score = min(1, volume / max_volume) if volume else 0.3

    # Weighted combination
    liquidity_score = 0.6 * spread_score + 0.4 * volume_score

    return liquidity_score


def calculate_rate_sensitivity(
    modified_duration: float, rate_change_bps: float
) -> float:
    """
    Calculate price sensitivity to rate changes

    Args:
        modified_duration: Modified duration of the bond
        rate_change_bps: Rate change in basis points

    Returns:
        Expected price change as percentage
    """
    return -modified_duration * (rate_change_bps / 100)


def optimal_barbell_weights(
    target_duration: float, short_duration: float, long_duration: float
) -> Tuple[float, float]:
    """
    Calculate optimal weights for barbell strategy

    Args:
        target_duration: Target portfolio duration
        short_duration: Duration of short-end bond
        long_duration: Duration of long-end bond
    Returns:
        Tuple of (short_weight, long_weight)
    """
    if long_duration == short_duration:
        return (0.5, 0.5)

    # Solve: w_short * D_short + w_long * D_long = D_target
    # w_short + w_long = 1

    long_weight = (target_duration - short_duration) / (long_duration - short_duration)
    long_weight = max(0, min(1, long_weight))
    short_weight = 1 - long_weight

    return (short_weight, long_weight)


def classify_duration_bucket(duration: float) -> str:
    """
    Classify bond into duration bucket

    Args:
        duration: Bond duration in years

    Returns:
        Duration bucket label
    """
    if duration < 1:
        return "ultra_short"
    elif duration < 3:
        return "short"
    elif duration < 5:
        return "medium"
    elif duration < 7:
        return "long"
    else:
        return "ultra_long"


def calculate_spread(bond_yield: float, benchmark_yield: float) -> float:
    """
    Calculate spread over benchmark

    Args:
        bond_yield: Bond yield as percentage
        benchmark_yield: Benchmark yield as percentage

    Returns:
        Spread in basis points
    """
    return (bond_yield - benchmark_yield) * 100


def calculate_carry(coupon_rate: float, price: float, funding_rate: float) -> float:
    """
    Calculate carry (income minus funding cost)

    Args:
        coupon_rate: Annual coupon rate as percentage
        price: Current price
        funding_rate: Funding rate as percentage
    Returns:
        Carry as percentage
    """
    income = coupon_rate / (price / 100)
    carry = income - funding_rate
    return carry


def calculate_rolldown(
    current_yield: float, forward_yield: float, duration: float
) -> float:
    """
    Calculate rolldown return

    Args:
        current_yield: Current yield
        forward_yield: Expected yield at horizon
        duration: Bond duration
    Returns:
        Rolldown return as percentage
    """
    yield_change = current_yield - forward_yield
    return duration * yield_change


def normalize_rating(rating: str) -> str:
    """
    Normalize credit rating to standard format

    Args:
        rating: Rating string (e.g., "Aaa", "AAA", "AA+")

    Returns:
        Normalized rating string
    """
    rating = rating.upper().strip()
    # Map Moody's to S&P/Fitch style
    moody_map = {
        "AAA": "AAA",
        "AA1": "AA+",
        "AA2": "AA",
        "AA3": "AA-",
        "A1": "A+",
        "A2": "A",
        "A3": "A-",
        "BAA1": "BBB+",
        "BAA2": "BBB",
        "BAA3": "BBB-",
    }
    return moody_map.get(rating, rating)
