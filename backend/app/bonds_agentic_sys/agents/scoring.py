"""
Scoring Agent
Scores bonds based on multiple factors: valuation, return, quality, liquidity
"""

from typing import Dict, List, Optional
from datetime import datetime

from schemas_v2 import BondAnalytics, BondScore, Signal, Rating
from dotenv import load_dotenv

load_dotenv()


class ScoringAgent:
    """
    Scores bonds based on configurable weights across multiple dimensions
    """

    def __init__(
        self,
        valuation_weight: float = 0.3,
        return_weight: float = 0.3,
        quality_weight: float = 0.2,
        liquidity_weight: float = 0.2,
    ):
        self.weights = {
            "valuation": valuation_weight,
            "return": return_weight,
            "quality": quality_weight,
            "liquidity": liquidity_weight,
        }

    def score_bonds(
        self, bond_analytics: Dict[str, BondAnalytics]
    ) -> Dict[str, BondScore]:
        """
        Score all bonds and return sorted scores
        """
        scores = {}

        for isin, analytics in bond_analytics.items():
            scores[isin] = self._score_single_bond(analytics)

        # Assign ranks
        sorted_bonds = sorted(
            scores.values(), key=lambda x: x.total_score, reverse=True
        )

        for rank, bond_score in enumerate(sorted_bonds, 1):
            scores[bond_score.isin].rank = rank

        return scores

    def _score_single_bond(self, analytics: BondAnalytics) -> BondScore:
        """
        Calculate composite score for a single bond
        """
        # Valuation score: negative gap is better (undervalued)
        valuation_score = self._calculate_valuation_score(analytics.valuation_gap)

        # Return score: higher expected return is better
        return_score = self._calculate_return_score(analytics.expected_return)

        # Quality score: based on rating and credit risk
        quality_score = self._calculate_quality_score(
            analytics.credit_rating, analytics.credit_risk_score
        )

        # Liquidity score: already normalized 0-1
        liquidity_score = analytics.liquidity_score

        # Calculate total score
        total_score = (
            self.weights["valuation"] * valuation_score
            + self.weights["return"] * return_score
            + self.weights["quality"] * quality_score
            + self.weights["liquidity"] * liquidity_score
        )

        return BondScore(
            isin=analytics.isin,
            name=analytics.name,
            valuation_score=round(valuation_score, 4),
            return_score=round(return_score, 4),
            quality_score=round(quality_score, 4),
            liquidity_score=round(liquidity_score, 4),
            total_score=round(total_score, 4),
            weights=self.weights,
        )

    def _calculate_valuation_score(self, valuation_gap: float) -> float:
        """
        Convert valuation gap to 0-1 score
        Negative gap (undervalued) = higher score
        """
        # Normalize: -5% gap -> 1.0, +5% gap -> 0.0
        score = 0.5 - (valuation_gap / 10)
        return max(0, min(1, score))

    def _calculate_return_score(self, expected_return: float) -> float:
        """
        Convert expected return to 0-1 score
        Higher return = higher score
        """
        # Normalize: assume returns range from -2% to +3%
        score = (expected_return + 2) / 5
        return max(0, min(1, score))

    def _calculate_quality_score(self, rating: Rating, credit_risk: float) -> float:
        """
        Calculate quality score based on rating and credit risk
        """
        # Rating score
        rating_scores = {
            Rating.AAA: 1.0,
            Rating.AA_PLUS: 0.95,
            Rating.AA: 0.9,
            Rating.AA_MINUS: 0.85,
            Rating.A_PLUS: 0.75,
            Rating.A: 0.7,
            Rating.A_MINUS: 0.65,
            Rating.BBB_PLUS: 0.55,
            Rating.BBB: 0.5,
            Rating.BBB_MINUS: 0.4,
            Rating.BB_PLUS: 0.3,
            Rating.BB: 0.2,
            Rating.UNRATED: 0.25,
        }

        rating_score = rating_scores.get(rating, 0.5)

        # Credit risk score (lower is better)
        risk_score = 1 - credit_risk

        # Combine with more weight on rating
        return 0.6 * rating_score + 0.4 * risk_score

    def get_top_bonds(
        self, scores: Dict[str, BondScore], n: int = 10, min_score: float = 0.0
    ) -> List[BondScore]:
        """
        Get top N bonds by score
        """
        filtered = [
            score for score in scores.values() if score.total_score >= min_score
        ]

        return sorted(filtered, key=lambda x: x.total_score, reverse=True)[:n]

    def filter_by_signal(
        self,
        bond_analytics: Dict[str, BondAnalytics],
        scores: Dict[str, BondScore],
        signals: List[Signal],
    ) -> Dict[str, BondScore]:
        """
        Filter scores by ML signal
        """
        return {
            isin: score
            for isin, score in scores.items()
            if isin in bond_analytics and bond_analytics[isin].ml_signal in signals
        }

    def categorize_bonds(
        self, scores: Dict[str, BondScore]
    ) -> Dict[str, List[BondScore]]:
        """
        Categorize bonds into quartiles
        """
        sorted_scores = sorted(
            scores.values(), key=lambda x: x.total_score, reverse=True
        )

        n = len(sorted_scores)
        q1 = n // 4
        q2 = n // 2
        q3 = 3 * n // 4

        return {
            "top_quartile": sorted_scores[:q1] if q1 > 0 else [],
            "second_quartile": sorted_scores[q1:q2] if q2 > q1 else [],
            "third_quartile": sorted_scores[q2:q3] if q3 > q2 else [],
            "bottom_quartile": sorted_scores[q3:] if n > q3 else [],
        }


def create_scoring_agent(
    valuation_weight: float = 0.3,
    return_weight: float = 0.3,
    quality_weight: float = 0.2,
    liquidity_weight: float = 0.2,
) -> ScoringAgent:
    """Factory function to create scoring agent"""
    return ScoringAgent(
        valuation_weight=valuation_weight,
        return_weight=return_weight,
        quality_weight=quality_weight,
        liquidity_weight=liquidity_weight,
    )
