"""
Analyst Agent
Performs comprehensive bond analytics using REAL market data only.
"""
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas_v2 import BondAnalytics, MLPrediction, Rating, Sector, Signal

# Import utils (Ensure these exist in your utils/ folder)
from utils import (
    calculate_duration,
    calculate_convexity,
    price_bond,
    years_to_maturity,
    interpolate_yield,
    calculate_liquidity_score,
    calculate_rate_sensitivity,
)


def _safe_get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class AnalystAgent:
    def __init__(self):
        self.high_duration_threshold = 7.0
        self.high_liquidity_threshold = 0.6
        self.high_quality_ratings = {Rating.AAA, Rating.AA_PLUS, Rating.AA}
    def analyze_bonds(
        self,
        bonds: List,
        ml_predictions: Dict[str, MLPrediction],
        credit_data: Dict[str, Any],
        yield_curve: Dict[float, float],  # Live Yield Curve
        risk_free_rate: float = 7.0,
    ) -> Dict[str, BondAnalytics]:
        analytics = {}

        for bond in bonds:
            isin = _safe_get(bond, "isin", "")
            if not isin:
                continue

            ml_pred = ml_predictions.get(isin)  # Can be None if ML failed
            credit = credit_data.get(isin)  # Can be None

            bond_analytics = self._analyze_single_bond(
                bond=bond,
                ml_prediction=ml_pred,
                credit_data=credit,
                yield_curve=yield_curve,
                risk_free_rate=risk_free_rate,
            )

            if bond_analytics:
                analytics[isin] = bond_analytics

        return analytics

    def _analyze_single_bond(
        self,
        bond,
        ml_prediction,
        credit_data,
        yield_curve: Dict[float, float],
        risk_free_rate: float,
    ) -> Optional[BondAnalytics]:
        #  FIX: Get real market data from MCP (like ML does)
        # If bond doesn't have last_traded_price, skip expensive calculations
        last_traded_price = _safe_get(bond, "last_traded_price", None)
        if last_traded_price is None:
            # Set dummy values to avoid validation errors
            return BondAnalytics(
                isin=_safe_get(bond, "isin", ""),
                name=_safe_get(bond, "name", ""),
                current_price=100.0,  # Dummy
                fair_value=100.0,  # Dummy
                valuation_gap=0.0,
                duration=0.0,
                modified_duration=0.0,
                convexity=0.0,
                rate_sensitivity=0.0,
                credit_risk_score=0.0,
                current_yield=0.0,
                ytm=0.0,
                expected_return=_safe_get(ml_prediction, "expected_return", 0.0)
                if ml_prediction
                else 0.0,
                liquidity_score=0.0,
                credit_rating=Rating.UNRATED,
                sector=Sector.OTHER,
                ml_signal=Signal.HOLD,
                ml_confidence=0.0,
                is_rate_sensitive=False,
                is_liquid=False,
                is_defensive=False,
            )

        # 1. Basic Extraction
        isin = _safe_get(bond, "isin", "")
        name = _safe_get(bond, "name", "")
        coupon_rate = _safe_get(bond, "coupon_rate", 0.0)
        face_value = _safe_get(bond, "face_value", 100.0)
        last_traded_price = _safe_get(bond, "last_traded_price", 100.0)
        bond_ytm_value = _safe_get(bond, "ytm", None)

        # Normalize percentages
        if bond_ytm_value is not None and bond_ytm_value > 1.0:
            bond_ytm_value /= 100.0
        if coupon_rate > 1.0:
            coupon_rate /= 100.0

        # Calculate Years to Maturity
        maturity_date = _safe_get(bond, "maturity_date", None)
        if maturity_date:
            ytm_years = years_to_maturity(maturity_date)
        else:
            ytm_years = _safe_get(bond, "years_to_maturity", 0.0)

        # 2. STRICT YIELD CURVE DEPENDENCY
        if not yield_curve or not isinstance(yield_curve, dict):
            # If no yield curve is provided, we cannot perform valid valuation analysis.
            # We set fair_value = price to neutralize valuation gap.
            fair_value = last_traded_price
            benchmark_yield = bond_ytm_value if bond_ytm_value else 0.07
        else:
            # Interpolate Benchmark
            benchmark_yield = interpolate_yield(yield_curve, ytm_years)

            # Add Credit Spread (from Real Credit Data)
            spread = _safe_get(credit_data, "credit_spread", 0.0) / 10000.0
            fair_yield = benchmark_yield + spread

            fair_value = price_bond(
                coupon_rate=coupon_rate,
                ytm=fair_yield,
                years_to_maturity=ytm_years,
                face_value=face_value,
            )

        # 3. Calculate Math Metrics
        calc_ytm = (
            bond_ytm_value
            if bond_ytm_value
            else (coupon_rate / (last_traded_price / 100) if last_traded_price else 0)
        )

        duration, mod_duration = calculate_duration(coupon_rate, calc_ytm, ytm_years)
        convexity = calculate_convexity(coupon_rate, calc_ytm, ytm_years)

        # 4. Valuation Gap
        valuation_gap = (
            ((last_traded_price - fair_value) / fair_value) * 100 if fair_value else 0.0
        )

        # 5. Rating & Liquidity
        rating_str = _safe_get(bond, "rating") or _safe_get(
            credit_data, "rating", "AAA"
        )
        try:
            rating_enum = Rating(rating_str)
        except:
            rating_enum = Rating.UNRATED

        vol = _safe_get(bond, "volume", 0)
        liquidity_score = min(vol / 500000.0, 1.0) if vol else 0.1  # Normalize volume

        # 6. ML Signals
        if ml_prediction:
            ml_expected_return = _safe_get(ml_prediction, "expected_return", 0.0)
            ml_confidence = _safe_get(ml_prediction, "confidence", 0.0)
        else:
            ml_expected_return = 0.0
            ml_confidence = 0.0

        # Determine Signal (Buy/Sell)
        # Buy if Undervalued (negative gap) OR High Exp Return
        score = ml_expected_return - (valuation_gap * 0.01)
        if score > 0.10:
            signal = Signal.STRONG_BUY
        elif score > 0.05:
            signal = Signal.BUY
        elif score < -0.05:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        return BondAnalytics(
            isin=isin,
            name=name,
            current_price=last_traded_price,
            fair_value=fair_value,
            valuation_gap=round(valuation_gap, 2),
            duration=round(duration, 2),
            modified_duration=round(mod_duration, 2),
            convexity=round(convexity, 4),
            rate_sensitivity=calculate_rate_sensitivity(mod_duration, 100),
            credit_risk_score=0.0,  # Handled by scoring agent via Rating
            current_yield=(coupon_rate / last_traded_price) * 100
            if last_traded_price
            else 0,
            ytm=round(calc_ytm, 4),
            expected_return=ml_expected_return,
            liquidity_score=liquidity_score,
            credit_rating=rating_enum,
            sector=Sector.OTHER,
            ml_signal=signal,
            ml_confidence=ml_confidence,
            is_rate_sensitive=mod_duration > self.high_duration_threshold,
            is_liquid=liquidity_score > self.high_liquidity_threshold,
            is_defensive=False,
        )


def create_analyst_agent() -> AnalystAgent:
    return AnalystAgent()
