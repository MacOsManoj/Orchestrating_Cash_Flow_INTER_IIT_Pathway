"""
Portfolio Manager Agent
Manages portfolio data and validates trade recommendations against constraints
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from schemas_v2 import (
    Portfolio,
    Position,
    TradeRecommendation,
    PortfolioHolding,
    UserPortfolio,
    BondAnalytics,
)

# Import MongoDB client
try:
    from utils.mongodb_client import get_mongodb_client, get_portfolios_collection

    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("Warning: MongoDB client not available. Using file-based storage.")


def _safe_get(obj, key, default=None):
    """Safely get attribute from dict or Pydantic model"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# --- Portfolio Loader ---
def load_portfolios_from_files(
    base_dir: str = ".cache/portfolios",
) -> Dict[str, Portfolio]:
    """Load portfolios from JSON files in the specified directory.

    Supports both formats:
    1. Simple format (SAMPLE_USER_001.json style)
    2. Bank format (SAMPLE_BANK_001.json style)
    """
    portfolios = {}
    base_path = Path(base_dir)

    if not base_path.exists():
        print(f"Warning: Portfolio directory not found: {base_dir}")
        return portfolios

    # Load all JSON files in the portfolios directory
    for json_file in base_path.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                data = json.load(f)

            # Determine format and parse accordingly
            if "user_id" in data:
                # Simple user portfolio format
                portfolio = _parse_user_portfolio(data)
                portfolios[data["user_id"]] = portfolio
                if "portfolio_id" in data:
                    portfolios[data["portfolio_id"]] = portfolio

            elif "bank_id" in data:
                # Bank portfolio format
                portfolio = _parse_bank_portfolio(data)
                portfolios[data["bank_id"]] = portfolio
                if "bank_name" in data:
                    portfolios[data["bank_name"]] = portfolio

        except Exception as e:
            print(f"Warning: Failed to load portfolio from {json_file}: {e}")
            continue

    return portfolios


def _parse_user_portfolio(data: Dict) -> Portfolio:
    """Parse simple user portfolio format."""
    positions = []

    for holding in data.get("holdings", []):
        positions.append(
            Position(
                isin=holding.get("isin", ""),
                name=holding.get("bond_name", ""),
                quantity=holding.get("quantity", 0.0),
                avg_cost=holding.get("avg_cost", 0.0),
                current_price=holding.get("current_price", 0.0),
                market_value=holding.get("market_value", 0.0),
                weight=holding.get("weight", 0.0),
                unrealized_pnl=holding.get("unrealized_pnl", 0.0),
            )
        )

    return Portfolio(
        portfolio_id=data.get("portfolio_id", data.get("user_id", "")),
        name=f"Portfolio {data.get('user_id', 'Unknown')}",
        positions=positions,
        total_value=data.get("total_value", 0.0),
        cash=data.get("cash", 0.0),
        duration=data.get("portfolio_duration", 0.0),
        ytm=data.get("portfolio_ytm", 0.0),
        sector_exposures=data.get("sector_exposures", {}),
        rating_exposures=data.get("rating_exposures", {}),
    )


def _parse_bank_portfolio(data: Dict) -> Portfolio:
    """Parse bank portfolio format with detailed holdings."""
    positions = []

    for holding in data.get("holdings", []):
        # Calculate derived values
        quantity = holding.get("quantity", 0.0)
        current_price = holding.get("current_price", 0.0)
        purchase_price = holding.get("purchase_price", 0.0)

        market_value = quantity * current_price
        unrealized_pnl = quantity * (current_price - purchase_price)

        positions.append(
            Position(
                isin=holding.get("isin", ""),
                name=holding.get("bond_id", holding.get("issuer", "")),
                quantity=quantity,
                avg_cost=purchase_price,
                current_price=current_price,
                market_value=market_value,
                weight=0.0,  # Will be calculated below
                unrealized_pnl=unrealized_pnl,
            )
        )

    # Calculate total value and weights
    total_value = sum(pos.market_value for pos in positions)
    for pos in positions:
        pos.weight = pos.market_value / total_value if total_value > 0 else 0.0

    # Extract risk metrics
    risk_metrics = data.get("risk_metrics", {})

    return Portfolio(
        portfolio_id=data.get("bank_id", ""),
        name=data.get("bank_name", "Unknown Bank"),
        positions=positions,
        total_value=total_value,
        cash=data.get("available_capital", 0.0),
        duration=risk_metrics.get("portfolio_duration", 0.0),
        ytm=risk_metrics.get("portfolio_ytm", 0.0),
        sector_exposures={},  # Could be calculated from holdings
        rating_exposures={},  # Could be calculated from holdings
    )


# --- Load portfolios at module import ---
# Try to load from MongoDB first, fallback to files
MOCK_DB: Dict[str, Portfolio] = {}
if MONGODB_AVAILABLE:
    try:
        client = get_mongodb_client()
        if client.is_connected():
            # Load from MongoDB will be done lazily in PortfolioManager
            pass
        else:
            # Fallback to files if MongoDB not connected
            MOCK_DB = load_portfolios_from_files()
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}. Using file-based storage.")
        MOCK_DB = load_portfolios_from_files()
else:
    MOCK_DB = load_portfolios_from_files()


class PortfolioManager:
    """
    Manages portfolio operations and validates trade recommendations

    Key responsibilities:
    - Load and fetch portfolios from MongoDB or JSON files (fallback)
    - Validate trade recommendations against portfolio constraints
    - Check cash availability, position limits, and risk profiles
    - Calculate portfolio metrics and exposures
    - Apply regulatory and risk management rules
    """

    def __init__(
        self, db: Optional[Dict[str, Portfolio]] = None, use_mongodb: bool = True
    ):
        self.use_mongodb = use_mongodb and MONGODB_AVAILABLE
        self.mongodb_client = None
        self.mongodb_collection = None

        if self.use_mongodb:
            try:
                self.mongodb_client = get_mongodb_client()
                if self.mongodb_client.is_connected():
                    self.mongodb_collection = get_portfolios_collection()
                    print(" Portfolio Manager: Using MongoDB")
                else:
                    print(
                        "Warning: Portfolio Manager: MongoDB not connected, using file-based storage"
                    )
                    self.use_mongodb = False
                    self.db = db or MOCK_DB
            except Exception as e:
                print(
                    f"Warning: Portfolio Manager: MongoDB error: {e}, using file-based storage"
                )
                self.use_mongodb = False
                self.db = db or MOCK_DB
        else:
            self.db = db or MOCK_DB

        # Configuration thresholds
        self.max_single_position_pct = 0.15  # 15% max per position
        self.max_sector_concentration_pct = 0.30  # 30% max per sector
        self.min_cash_buffer_pct = 0.05  # Keep 5% cash buffer
        self.conservative_risk_threshold = 0.8
        self.moderate_risk_threshold = 0.6

    def get_portfolio(self, user_id: str) -> Optional[Portfolio]:
        """
        Fetch portfolio for given user/bank ID from MongoDB or in-memory cache

        Args:
            user_id: User or bank identifier

        Returns:
            Portfolio object or None if not found
        """
        if self.use_mongodb and self.mongodb_collection is not None:
            try:
                # Try to find by user_id, portfolio_id, or bank_id
                portfolio_doc = self.mongodb_collection.find_one(
                    {
                        "$or": [
                            {"user_id": user_id},
                            {"portfolio_id": user_id},
                            {"bank_id": user_id},
                        ]
                    }
                )

                if portfolio_doc:
                    # Convert MongoDB document to Portfolio
                    portfolio = self._document_to_portfolio(portfolio_doc)
                    return portfolio
                return None
            except Exception as e:
                print(f"Error fetching portfolio from MongoDB: {e}")
                # Fallback to in-memory cache
                return self.db.get(user_id) if hasattr(self, "db") else None
        else:
            # Use in-memory cache
            return self.db.get(user_id) if hasattr(self, "db") else None

    def refresh_portfolios(self, base_dir: str = ".cache/portfolios") -> None:
        """
        Reload portfolios from JSON files (and optionally sync to MongoDB)

        Args:
            base_dir: Directory containing portfolio JSON files
        """
        portfolios = load_portfolios_from_files(base_dir)
        self.db = portfolios

        # If MongoDB is available, sync portfolios to MongoDB
        if self.use_mongodb and self.mongodb_collection is not None:
            try:
                for user_id, portfolio in portfolios.items():
                    self._save_portfolio_to_mongodb(portfolio, user_id)
                print(f" Synced {len(portfolios)} portfolios to MongoDB")
            except Exception as e:
                print(f"Warning: Could not sync portfolios to MongoDB: {e}")

    def get_all_portfolios(self) -> Dict[str, Portfolio]:
        """Return all loaded portfolios from MongoDB or in-memory cache"""
        if self.use_mongodb and self.mongodb_collection is not None:
            try:
                portfolios = {}
                cursor = self.mongodb_collection.find({})
                for doc in cursor:
                    portfolio = self._document_to_portfolio(doc)
                    # Use user_id, portfolio_id, or bank_id as key
                    key = (
                        doc.get("user_id")
                        or doc.get("portfolio_id")
                        or doc.get("bank_id")
                    )
                    if key and portfolio:
                        portfolios[key] = portfolio
                return portfolios
            except Exception as e:
                print(f"Error fetching all portfolios from MongoDB: {e}")
                return self.db if hasattr(self, "db") else {}
        else:
            return self.db if hasattr(self, "db") else {}

    def validate_recommendations(
        self,
        portfolio: Portfolio,
        recommendations: List[TradeRecommendation],
        bond_analytics: Optional[Dict[str, BondAnalytics]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[TradeRecommendation]:
        """
        Validate and filter trade recommendations against portfolio constraints

        Args:
            portfolio: User's portfolio
            recommendations: List of trade recommendations to validate
            bond_analytics: Optional bond analytics for enhanced validation
            context: Additional context (risk_profile, constraints, etc.)

        Returns:
            List of validated recommendations (rejected ones filtered out)

        Validation Rules:
        - BUY: Sufficient cash, position size limits, risk profile match
        - SELL: Position exists, quantity available
        - SWITCH: Sell-side and buy-side checks, net cash impact
        - HOLD: Always valid
        - Risk profile alignment (conservative/moderate/aggressive)
        - Sector concentration limits
        - Regulatory constraints
        """
        valid: List[TradeRecommendation] = []
        ctx = context or {}
        risk_profile = ctx.get("risk_profile", "moderate")

        # Get analytics if provided
        analytics = bond_analytics or {}

        # Position lookup for quick checks
        pos_map = (
            {p.isin: p for p in portfolio.positions} if portfolio.positions else {}
        )

        for rec in recommendations:
            # Defensive: ensure fields exist
            action = (rec.action or "").upper()

            # Resolve a price for cost estimates
            price = (
                rec.target_price
                if getattr(rec, "target_price", None)
                else getattr(rec, "target_price", 1.0)
            )
            try:
                price = float(price) if price is not None else 1.0
            except Exception:
                price = 1.0

            # BUY logic
            if action == "BUY":
                # Check cash availability
                cost = (rec.quantity or 0) * price
                min_cash_required = portfolio.total_value * self.min_cash_buffer_pct
                available_cash = (portfolio.cash or 0) - min_cash_required

                if cost > available_cash:
                    rec.rationale = (
                        (rec.rationale or "")
                        + f" [REJECTED: Insufficient cash - need {cost:.2f}, have {available_cash:.2f}]"
                    )
                    continue

                # Risk profile check
                risk_threshold = self._get_risk_threshold(risk_profile)
                if getattr(rec, "risk_score", 0) > risk_threshold:
                    rec.rationale = (
                        (rec.rationale or "")
                        + f" [REJECTED: Risk score {rec.risk_score:.2f} exceeds {risk_profile} threshold {risk_threshold}]"
                    )
                    continue

                # Position size check
                new_position_value = cost
                new_weight = (
                    new_position_value / (portfolio.total_value + cost)
                    if portfolio.total_value > 0
                    else 0
                )
                if new_weight > self.max_single_position_pct:
                    rec.rationale = (
                        (rec.rationale or "")
                        + f" [REJECTED: Position would exceed {self.max_single_position_pct * 100}% limit]"
                    )
                    continue

                # Sector concentration check (if analytics available)
                if rec.isin in analytics:
                    bond = analytics[rec.isin]
                    sector = str(bond.sector)
                    current_sector_exposure = portfolio.sector_exposures.get(sector, 0)
                    new_sector_exposure = current_sector_exposure + new_weight

                    if new_sector_exposure > self.max_sector_concentration_pct:
                        rec.rationale = (
                            (rec.rationale or "")
                            + f" [REJECTED: {sector} exposure would exceed {self.max_sector_concentration_pct * 100}% limit]"
                        )
                        continue

            # SELL logic
            if action == "SELL":
                held = pos_map.get(rec.isin)
                if not held:
                    rec.rationale = (
                        rec.rationale or ""
                    ) + " [REJECTED: Position not held]"
                    continue

                if rec.quantity and rec.quantity > held.quantity:
                    # Cap the sell to available quantity and mark rationale
                    rec.rationale = (
                        rec.rationale or ""
                    ) + f" [ADJUSTED: quantity reduced to {held.quantity}]"
                    rec.quantity = held.quantity

            # SWITCH logic: ensure sell side and buy side basic checks
            if action == "SWITCH":
                # If switching away from a held position, ensure we hold it
                held = pos_map.get(rec.isin)
                if not held:
                    rec.rationale = (
                        rec.rationale or ""
                    ) + " [REJECTED: Original position not held]"
                    continue

                # For the buy leg (switch_to_isin), ensure cash is enough for an approximate
                # purchase; this is simplistic: use price if provided in recommendation
                buy_price = getattr(rec, "target_price", price)
                buy_cost = (rec.quantity or 0) * (buy_price or 1.0)
                if buy_cost > (portfolio.cash or 0) + (
                    held.quantity * getattr(held, "current_price", 0)
                ):
                    rec.rationale = (
                        rec.rationale or ""
                    ) + " [REJECTED: Insufficient funds for switch]"
                    continue

            # If we reach here, recommendation passed checks
            valid.append(rec)

        return valid

    def _get_risk_threshold(self, risk_profile: str) -> float:
        """Get risk score threshold based on risk profile"""
        thresholds = {
            "conservative": self.conservative_risk_threshold,
            "moderate": self.moderate_risk_threshold,
            "aggressive": 1.0,
        }
        return thresholds.get(risk_profile.lower(), self.moderate_risk_threshold)

    def calculate_portfolio_metrics(
        self,
        portfolio: Portfolio,
        bond_analytics: Optional[Dict[str, BondAnalytics]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio metrics

        Args:
            portfolio: Portfolio to analyze
            bond_analytics: Optional bond analytics for enhanced calculations

        Returns:
            Dict with portfolio metrics (duration, ytm, exposures, etc.)
        """
        if not portfolio.positions:
            return {
                "duration": 0.0,
                "ytm": 0.0,
                "total_value": portfolio.total_value,
                "cash_pct": 1.0,
                "num_positions": 0,
                "sector_exposures": {},
                "rating_exposures": {},
            }

        total_weight = sum(pos.weight for pos in portfolio.positions)

        # Basic metrics
        metrics = {
            "duration": portfolio.duration,
            "ytm": portfolio.ytm,
            "total_value": portfolio.total_value,
            "cash": portfolio.cash,
            "cash_pct": portfolio.cash / portfolio.total_value
            if portfolio.total_value > 0
            else 0,
            "num_positions": len(portfolio.positions),
            "sector_exposures": portfolio.sector_exposures,
            "rating_exposures": portfolio.rating_exposures,
        }

        # Enhanced metrics if analytics available
        if bond_analytics:
            weighted_return = 0.0
            weighted_risk = 0.0

            for pos in portfolio.positions:
                if pos.isin in bond_analytics:
                    bond = bond_analytics[pos.isin]
                    weighted_return += bond.expected_return * pos.weight
                    weighted_risk += bond.credit_risk_score * pos.weight

            metrics["expected_return"] = round(weighted_return, 2)
            metrics["portfolio_risk_score"] = round(weighted_risk, 4)

        return metrics

    def check_constraints(
        self, portfolio: Portfolio, constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check portfolio against specified constraints

        Args:
            portfolio: Portfolio to check
            constraints: Dict of constraints to verify

        Returns:
            Dict with constraint check results and violations
        """
        violations = []
        checks = {}

        # Duration constraints
        if "max_duration" in constraints:
            max_duration = constraints["max_duration"]
            checks["duration_check"] = portfolio.duration <= max_duration
            if portfolio.duration > max_duration:
                violations.append(
                    f"Duration {portfolio.duration:.2f} exceeds max {max_duration}"
                )

        if "min_duration" in constraints:
            min_duration = constraints["min_duration"]
            checks["duration_check"] = portfolio.duration >= min_duration
            if portfolio.duration < min_duration:
                violations.append(
                    f"Duration {portfolio.duration:.2f} below min {min_duration}"
                )

        # Cash constraints
        if "min_cash_pct" in constraints:
            min_cash = constraints["min_cash_pct"]
            cash_pct = (
                portfolio.cash / portfolio.total_value
                if portfolio.total_value > 0
                else 0
            )
            checks["cash_check"] = cash_pct >= min_cash
            if cash_pct < min_cash:
                violations.append(
                    f"Cash {cash_pct * 100:.1f}% below min {min_cash * 100}%"
                )

        # Sector concentration
        if "max_sector_pct" in constraints:
            max_sector = constraints["max_sector_pct"]
            for sector, exposure in portfolio.sector_exposures.items():
                if exposure > max_sector:
                    violations.append(
                        f"Sector {sector} exposure {exposure * 100:.1f}% exceeds max {max_sector * 100}%"
                    )
                    checks[f"sector_{sector}"] = False

        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "checks": checks,
        }

    def find_rebalancing_opportunities(
        self,
        portfolio: Portfolio,
        bond_analytics: Dict[str, BondAnalytics],
        target_duration: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Identify rebalancing opportunities to optimize portfolio

        Args:
            portfolio: Current portfolio
            bond_analytics: Bond analytics for all positions
            target_duration: Optional target duration to achieve

        Returns:
            List of rebalancing suggestions
        """
        opportunities = []

        # Check for underperforming positions
        for pos in portfolio.positions:
            if pos.isin in bond_analytics:
                bond = bond_analytics[pos.isin]

                # Low expected return
                if bond.expected_return < 0:
                    opportunities.append(
                        {
                            "type": "sell_underperformer",
                            "isin": pos.isin,
                            "name": pos.name,
                            "reason": f"Negative expected return: {bond.expected_return:.2f}%",
                            "priority": "high",
                        }
                    )

                # High risk with low return
                if bond.credit_risk_score > 0.5 and bond.expected_return < 5.0:
                    opportunities.append(
                        {
                            "type": "sell_high_risk",
                            "isin": pos.isin,
                            "name": pos.name,
                            "reason": f"High risk ({bond.credit_risk_score:.2f}) with low return ({bond.expected_return:.2f}%)",
                            "priority": "medium",
                        }
                    )

        # Check sector concentration
        for sector, exposure in portfolio.sector_exposures.items():
            if exposure > self.max_sector_concentration_pct:
                opportunities.append(
                    {
                        "type": "rebalance_sector",
                        "sector": sector,
                        "current_exposure": f"{exposure * 100:.1f}%",
                        "reason": f"Over-concentrated in {sector}",
                        "priority": "medium",
                    }
                )

        return opportunities

    def update_bond_in_portfolio(
        self,
        user_id: str,
        isin: str,
        updates: Dict[str, Any],
        recalculate_metrics: bool = True,
    ) -> bool:
        """
        Update specific bond information in a user's portfolio

        Args:
            user_id: User identifier
            isin: ISIN of the bond to update
            updates: Dictionary of fields to update (e.g., {'quantity': 1000, 'current_price': 98.5})
            recalculate_metrics: Whether to recalculate portfolio metrics after update

        Returns:
            True if successful, False otherwise

        Example:
            manager.update_bond_in_portfolio(
                user_id="SAMPLE_USER_001",
                isin="INE001A01036",
                updates={
                    "quantity": 1500000,
                    "current_price": 101.5,
                    "avg_cost": 100.0
                }
            )
        """
        if not self.use_mongodb or self.mongodb_collection is None:
            print("MongoDB not available for portfolio updates")
            return False

        try:
            # Fetch existing portfolio
            portfolio = self.get_portfolio(user_id)

            # If portfolio doesn't exist, create a new one
            if not portfolio:
                print(
                    f"Portfolio not found for user: {user_id}, creating new portfolio"
                )
                # Create a new position
                new_position = Position(
                    isin=isin,
                    name=updates.get("name", ""),
                    quantity=float(updates.get("quantity", 0.0)),
                    avg_cost=float(
                        updates.get("avg_cost", updates.get("current_price", 0.0))
                    ),
                    current_price=float(updates.get("current_price", 0.0)),
                    market_value=float(updates.get("quantity", 0.0))
                    * float(updates.get("current_price", 0.0)),
                    weight=0.0,  # Will be recalculated
                    unrealized_pnl=0.0,  # Will be recalculated
                )

                # Create new portfolio
                portfolio = Portfolio(
                    portfolio_id=user_id,
                    name=f"Portfolio {user_id}",
                    positions=[new_position],
                    total_value=0.0,  # Will be recalculated
                    cash=0.0,
                    duration=0.0,
                    ytm=0.0,
                    sector_exposures={},
                    rating_exposures={},
                )
            else:
                # Portfolio exists - find the position to update
                position_found = False
                for pos in portfolio.positions:
                    if pos.isin == isin:
                        position_found = True
                        # Update position fields
                        if "quantity" in updates:
                            pos.quantity = float(updates["quantity"])
                        if "current_price" in updates:
                            pos.current_price = float(updates["current_price"])
                        if "avg_cost" in updates:
                            pos.avg_cost = float(updates["avg_cost"])
                        if "name" in updates:
                            pos.name = str(updates["name"])

                        # Recalculate derived values
                        pos.market_value = pos.quantity * pos.current_price
                        pos.unrealized_pnl = pos.quantity * (
                            pos.current_price - pos.avg_cost
                        )

                        break

                if not position_found:
                    # If position doesn't exist, create a new one
                    new_position = Position(
                        isin=isin,
                        name=updates.get("name", ""),
                        quantity=float(updates.get("quantity", 0.0)),
                        avg_cost=float(
                            updates.get("avg_cost", updates.get("current_price", 0.0))
                        ),
                        current_price=float(updates.get("current_price", 0.0)),
                        market_value=float(updates.get("quantity", 0.0))
                        * float(updates.get("current_price", 0.0)),
                        weight=0.0,  # Will be recalculated
                        unrealized_pnl=0.0,  # Will be recalculated
                    )
                    portfolio.positions.append(new_position)

            # Recalculate portfolio metrics if requested
            if recalculate_metrics:
                self._recalculate_portfolio_metrics(portfolio)

            # Save updated portfolio
            return self._save_portfolio_to_mongodb(portfolio, user_id)

        except Exception as e:
            print(f"Error updating bond in portfolio: {e}")
            import traceback

            traceback.print_exc()
            return False

    def update_multiple_bonds(
        self,
        user_id: str,
        bond_updates: List[Dict[str, Any]],
        recalculate_metrics: bool = True,
    ) -> Dict[str, bool]:
        """
        Update multiple bonds in a portfolio at once

        Args:
            user_id: User identifier
            bond_updates: List of update dictionaries, each with 'isin' and update fields
            recalculate_metrics: Whether to recalculate portfolio metrics after all updates

        Returns:
            Dictionary mapping ISIN to success status

        Example:
            manager.update_multiple_bonds(
                user_id="SAMPLE_USER_001",
                bond_updates=[
                    {"isin": "INE001A01036", "current_price": 101.5, "quantity": 1500000},
                    {"isin": "INE002A01018", "current_price": 98.5}
                ]
            )
        """
        results = {}

        for update in bond_updates:
            isin = update.get("isin")
            if not isin:
                results["unknown"] = False
                continue

            # Extract ISIN and remove it from updates
            updates = {k: v for k, v in update.items() if k != "isin"}

            # Update each bond (don't recalculate until all are done)
            success = self.update_bond_in_portfolio(
                user_id=user_id, isin=isin, updates=updates, recalculate_metrics=False
            )
            results[isin] = success

        # Recalculate metrics once after all updates
        if recalculate_metrics:
            try:
                portfolio = self.get_portfolio(user_id)
                if portfolio:
                    self._recalculate_portfolio_metrics(portfolio)
                    self._save_portfolio_to_mongodb(portfolio, user_id)
            except Exception as e:
                print(f"Error recalculating portfolio metrics: {e}")

        return results

    def remove_bond_from_portfolio(
        self, user_id: str, isin: str, recalculate_metrics: bool = True
    ) -> bool:
        """
        Remove a bond position from a user's portfolio

        Args:
            user_id: User identifier
            isin: ISIN of the bond to remove
            recalculate_metrics: Whether to recalculate portfolio metrics after removal

        Returns:
            True if successful, False otherwise
        """
        if not self.use_mongodb or self.mongodb_collection is None:
            print("MongoDB not available for portfolio updates")
            return False

        try:
            # Fetch existing portfolio
            portfolio = self.get_portfolio(user_id)
            if not portfolio:
                print(f"Portfolio not found for user: {user_id}")
                return False

            # Remove the position
            original_count = len(portfolio.positions)
            portfolio.positions = [
                pos for pos in portfolio.positions if pos.isin != isin
            ]

            if len(portfolio.positions) == original_count:
                print(f"Bond {isin} not found in portfolio")
                return False

            # Recalculate portfolio metrics if requested
            if recalculate_metrics:
                self._recalculate_portfolio_metrics(portfolio)

            # Save updated portfolio
            return self._save_portfolio_to_mongodb(portfolio, user_id)

        except Exception as e:
            print(f"Error removing bond from portfolio: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _recalculate_portfolio_metrics(self, portfolio: Portfolio) -> None:
        """
        Recalculate portfolio-level metrics after position updates

        Args:
            portfolio: Portfolio to recalculate metrics for
        """
        if not portfolio.positions:
            portfolio.total_value = portfolio.cash or 0.0
            return

        # Recalculate total value
        total_market_value = sum(pos.market_value for pos in portfolio.positions)
        portfolio.total_value = total_market_value + (portfolio.cash or 0.0)

        # Recalculate weights
        for pos in portfolio.positions:
            pos.weight = (
                pos.market_value / total_market_value if total_market_value > 0 else 0.0
            )

        # Recalculate sector and rating exposures (if we had analytics, we'd use them here)
        # For now, we'll keep existing exposures or set to empty
        if not portfolio.sector_exposures:
            portfolio.sector_exposures = {}
        if not portfolio.rating_exposures:
            portfolio.rating_exposures = {}

        # Note: Duration and YTM would need bond analytics to recalculate properly
        # These are typically calculated from bond characteristics, not just positions

    def save_portfolio(
        self, portfolio: Portfolio, user_id: Optional[str] = None
    ) -> bool:
        """
        Save portfolio to MongoDB

        Args:
            portfolio: Portfolio to save
            user_id: Optional user identifier (uses portfolio.portfolio_id if not provided)

        Returns:
            True if successful, False otherwise
        """
        if not self.use_mongodb or self.mongodb_collection is None:
            return False

        try:
            return self._save_portfolio_to_mongodb(portfolio, user_id)
        except Exception as e:
            print(f"Error saving portfolio to MongoDB: {e}")
            return False

    def _save_portfolio_to_mongodb(
        self, portfolio: Portfolio, user_id: Optional[str] = None
    ) -> bool:
        """Internal method to save portfolio to MongoDB"""
        try:
            portfolio_dict = self._portfolio_to_document(portfolio, user_id)

            # Use upsert to update or insert
            result = self.mongodb_collection.update_one(
                {
                    "$or": [
                        {"user_id": user_id or portfolio.portfolio_id},
                        {"portfolio_id": portfolio.portfolio_id},
                        {"bank_id": user_id or portfolio.portfolio_id},
                    ]
                },
                {"$set": portfolio_dict},
                upsert=True,
            )
            return result.acknowledged
        except Exception as e:
            print(f"Error in _save_portfolio_to_mongodb: {e}")
            return False

    def _portfolio_to_document(
        self, portfolio: Portfolio, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert Portfolio to MongoDB document"""
        doc = {
            "portfolio_id": portfolio.portfolio_id,
            "name": portfolio.name,
            "total_value": portfolio.total_value,
            "cash": portfolio.cash,
            "duration": portfolio.duration,
            "ytm": portfolio.ytm,
            "sector_exposures": portfolio.sector_exposures,
            "rating_exposures": portfolio.rating_exposures,
            "positions": [
                {
                    "isin": pos.isin,
                    "name": pos.name,
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "weight": pos.weight,
                    "unrealized_pnl": pos.unrealized_pnl,
                }
                for pos in portfolio.positions
            ],
            "last_updated": datetime.now().isoformat(),
        }

        # Add user_id or bank_id if provided
        if user_id:
            if user_id.startswith("SAMPLE_USER") or "user" in user_id.lower():
                doc["user_id"] = user_id
            elif user_id.startswith("SAMPLE_BANK") or "bank" in user_id.lower():
                doc["bank_id"] = user_id
                doc["bank_name"] = portfolio.name

        return doc

    def _document_to_portfolio(self, doc: Dict[str, Any]) -> Portfolio:
        """Convert MongoDB document to Portfolio"""
        positions = [
            Position(
                isin=pos.get("isin", ""),
                name=pos.get("name", ""),
                quantity=pos.get("quantity", 0.0),
                avg_cost=pos.get("avg_cost", 0.0),
                current_price=pos.get("current_price", 0.0),
                market_value=pos.get("market_value", 0.0),
                weight=pos.get("weight", 0.0),
                unrealized_pnl=pos.get("unrealized_pnl", 0.0),
            )
            for pos in doc.get("positions", [])
        ]

        return Portfolio(
            portfolio_id=doc.get(
                "portfolio_id", doc.get("user_id") or doc.get("bank_id", "")
            ),
            name=doc.get("name", "Unknown Portfolio"),
            positions=positions,
            total_value=doc.get("total_value", 0.0),
            cash=doc.get("cash", 0.0),
            duration=doc.get("duration", 0.0),
            ytm=doc.get("ytm", 0.0),
            sector_exposures=doc.get("sector_exposures", {}),
            rating_exposures=doc.get("rating_exposures", {}),
        )


# --- Node-style functions (compatibility layer) ---
def portfolio_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node entry: fetch portfolio for `user_id` or `bank_id`.

    Expects `state` to be a dict-like object that may contain `user_id`.
    Returns a dict with `portfolio` on success or `messages` on failure.
    """
    user_id = state.get("user_id") or state.get("bank_id") or state.get("portfolio_id")
    manager = PortfolioManager()

    # Refresh portfolios to ensure we have the latest data
    if not manager.db or len(manager.db) == 0:
        manager.refresh_portfolios()

    portfolio = manager.get_portfolio(user_id) if user_id else None

    if not portfolio:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Portfolio not found for user: {user_id}",
                }
            ]
        }

    return {"portfolio": portfolio}


def constraint_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node entry: validate `trade_recommendations` against `portfolio`.

    Expects `state` to contain `portfolio` and `trade_recommendations`.
    Returns a dict with `trade_recommendations` filtered/adjusted.
    """
    portfolio = state.get("portfolio")
    recs = state.get("trade_recommendations") or []
    context = state.get("context", {})

    if not portfolio:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": "No portfolio provided to constraint checker.",
                }
            ],
            "trade_recommendations": [],
        }

    manager = PortfolioManager()
    valid = manager.validate_recommendations(portfolio, recs, context)
    return {"trade_recommendations": valid}


def create_portfolio_manager(
    db: Optional[Dict[str, Portfolio]] = None, use_mongodb: bool = True
) -> PortfolioManager:
    """Factory to create a PortfolioManager instance."""
    return PortfolioManager(db=db, use_mongodb=use_mongodb)
