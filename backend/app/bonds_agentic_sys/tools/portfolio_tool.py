"""
Portfolio Management Tool
Manages user portfolios - get and update portfolio data
"""

import os
import json
from typing import Optional, Dict, Any, List

from schemas_v2 import ToolResult, ToolType, UserPortfolio, Portfolio, PortfolioHolding
from dotenv import load_dotenv

load_dotenv()

# Import portfolio manager
from agents.portfolio_manager import PortfolioManager, create_portfolio_manager


class PortfolioManagerTool:
    """
    Portfolio management tool - uses MongoDB backend
    """

    def __init__(self, db_path: str = ".cache/portfolios", use_mongodb: bool = True):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        # Use PortfolioManager with MongoDB support
        self.portfolio_manager = create_portfolio_manager(use_mongodb=use_mongodb)

    async def get_portfolio(self, user_id: str) -> ToolResult:
        """Get user portfolio from MongoDB or file fallback"""
        try:
            # Try to get from MongoDB via PortfolioManager
            portfolio = self.portfolio_manager.get_portfolio(user_id)

            if portfolio:
                # Convert Portfolio to UserPortfolio format for compatibility
                user_portfolio = self._portfolio_to_user_portfolio(portfolio, user_id)
                return ToolResult(
                    tool_type=ToolType.PORTFOLIO_MANAGER,
                    success=True,
                    data=user_portfolio,
                    cached=False,  # From database
                )

            # Fallback to file-based lookup
            portfolio_file = os.path.join(self.db_path, f"{user_id}.json")

            if not os.path.exists(portfolio_file):
                # Fallback to a default sample if user-specific file not found
                portfolio_file = os.path.join(self.db_path, "SAMPLE_USER_001.json")

            if os.path.exists(portfolio_file):
                with open(portfolio_file, "r") as f:
                    portfolio_data = json.load(f)
                    portfolio = UserPortfolio(**portfolio_data)

                return ToolResult(
                    tool_type=ToolType.PORTFOLIO_MANAGER,
                    success=True,
                    data=portfolio,
                    cached=True,  # From file
                )

            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=f"No portfolio found for user {user_id} in database or files.",
            )

        except Exception as e:
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=str(e),
            )

    async def update_portfolio(
        self, user_id: str, portfolio: UserPortfolio
    ) -> ToolResult:
        """Update user portfolio in MongoDB or file"""
        try:
            # Convert UserPortfolio to Portfolio
            portfolio_obj = self._user_portfolio_to_portfolio(portfolio)

            # Save to MongoDB via PortfolioManager
            if self.portfolio_manager.save_portfolio(portfolio_obj, user_id):
                return ToolResult(
                    tool_type=ToolType.PORTFOLIO_MANAGER, success=True, data=portfolio
                )

            # Fallback to file-based storage
            portfolio_file = os.path.join(self.db_path, f"{user_id}_portfolio.json")

            with open(portfolio_file, "w") as f:
                json.dump(portfolio.dict(), f, indent=2, default=str)

            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER, success=True, data=portfolio
            )

        except Exception as e:
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=str(e),
            )

    def _portfolio_to_user_portfolio(
        self, portfolio: Portfolio, user_id: str
    ) -> UserPortfolio:
        """Convert Portfolio to UserPortfolio format"""
        holdings = [
            PortfolioHolding(
                isin=pos.isin,
                bond_name=pos.name,
                quantity=pos.quantity,
                avg_cost=pos.avg_cost,
                current_price=pos.current_price,
                market_value=pos.market_value,
                weight=pos.weight,
                unrealized_pnl=pos.unrealized_pnl,
            )
            for pos in portfolio.positions
        ]

        return UserPortfolio(
            user_id=user_id,
            portfolio_id=portfolio.portfolio_id,
            holdings=holdings,
            total_value=portfolio.total_value,
            cash=portfolio.cash,
        )

    def _user_portfolio_to_portfolio(self, user_portfolio: UserPortfolio) -> Portfolio:
        """Convert UserPortfolio to Portfolio format"""
        from schemas_v2 import Position

        positions = [
            Position(
                isin=holding.isin,
                name=holding.bond_name,
                quantity=holding.quantity,
                avg_cost=holding.avg_cost,
                current_price=holding.current_price,
                market_value=holding.market_value,
                weight=holding.weight,
                unrealized_pnl=holding.unrealized_pnl,
            )
            for holding in user_portfolio.holdings
        ]

        return Portfolio(
            portfolio_id=user_portfolio.portfolio_id,
            name=user_portfolio.user_id,
            positions=positions,
            total_value=user_portfolio.total_value,
            cash=user_portfolio.cash,
        )

    async def update_bond(
        self, user_id: str, isin: str, updates: Dict[str, Any]
    ) -> ToolResult:
        """
        Update a specific bond in the user's portfolio

        Args:
            user_id: User identifier
            isin: ISIN of the bond to update
            updates: Dictionary with fields to update (quantity, current_price, avg_cost, name)

        Returns:
            ToolResult with success status and updated portfolio
        """
        try:
            success = self.portfolio_manager.update_bond_in_portfolio(
                user_id=user_id, isin=isin, updates=updates, recalculate_metrics=True
            )

            if success:
                # Fetch updated portfolio
                portfolio = self.portfolio_manager.get_portfolio(user_id)
                if portfolio:
                    user_portfolio = self._portfolio_to_user_portfolio(
                        portfolio, user_id
                    )
                    return ToolResult(
                        tool_type=ToolType.PORTFOLIO_MANAGER,
                        success=True,
                        data=user_portfolio,
                        cached=False,
                    )

            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=f"Failed to update bond {isin} in portfolio",
            )
        except Exception as e:
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=str(e),
            )

    async def add_bond(
        self,
        user_id: str,
        isin: str,
        bond_name: str,
        quantity: float,
        current_price: float,
        avg_cost: Optional[float] = None,
    ) -> ToolResult:
        """
        Add a new bond to the user's portfolio

        Args:
            user_id: User identifier
            isin: ISIN of the bond
            bond_name: Name of the bond
            quantity: Quantity to add
            current_price: Current market price
            avg_cost: Average cost (defaults to current_price if not provided)

        Returns:
            ToolResult with success status and updated portfolio
        """
        try:
            updates = {
                "name": bond_name,
                "quantity": quantity,
                "current_price": current_price,
                "avg_cost": avg_cost if avg_cost is not None else current_price,
            }

            success = self.portfolio_manager.update_bond_in_portfolio(
                user_id=user_id, isin=isin, updates=updates, recalculate_metrics=True
            )

            if success:
                # Fetch updated portfolio
                portfolio = self.portfolio_manager.get_portfolio(user_id)
                if portfolio:
                    user_portfolio = self._portfolio_to_user_portfolio(
                        portfolio, user_id
                    )
                    return ToolResult(
                        tool_type=ToolType.PORTFOLIO_MANAGER,
                        success=True,
                        data=user_portfolio,
                        cached=False,
                    )

            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=f"Failed to add bond {isin} to portfolio",
            )
        except Exception as e:
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=str(e),
            )

    async def remove_bond(self, user_id: str, isin: str) -> ToolResult:
        """
        Remove a bond from the user's portfolio

        Args:
            user_id: User identifier
            isin: ISIN of the bond to remove

        Returns:
            ToolResult with success status and updated portfolio
        """
        try:
            success = self.portfolio_manager.remove_bond_from_portfolio(
                user_id=user_id, isin=isin, recalculate_metrics=True
            )

            if success:
                # Fetch updated portfolio
                portfolio = self.portfolio_manager.get_portfolio(user_id)
                if portfolio:
                    user_portfolio = self._portfolio_to_user_portfolio(
                        portfolio, user_id
                    )
                    return ToolResult(
                        tool_type=ToolType.PORTFOLIO_MANAGER,
                        success=True,
                        data=user_portfolio,
                        cached=False,
                    )

            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=f"Failed to remove bond {isin} from portfolio",
            )
        except Exception as e:
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=str(e),
            )

    async def update_multiple_bonds(
        self, user_id: str, bond_updates: List[Dict[str, Any]]
    ) -> ToolResult:
        """
        Update multiple bonds in the portfolio at once

        Args:
            user_id: User identifier
            bond_updates: List of update dictionaries, each with 'isin' and update fields

        Returns:
            ToolResult with success status and updated portfolio
        """
        try:
            results = self.portfolio_manager.update_multiple_bonds(
                user_id=user_id, bond_updates=bond_updates, recalculate_metrics=True
            )

            # Check if all updates succeeded
            all_success = all(results.values())

            if all_success:
                # Fetch updated portfolio
                portfolio = self.portfolio_manager.get_portfolio(user_id)
                if portfolio:
                    user_portfolio = self._portfolio_to_user_portfolio(
                        portfolio, user_id
                    )
                    return ToolResult(
                        tool_type=ToolType.PORTFOLIO_MANAGER,
                        success=True,
                        data=user_portfolio,
                        cached=False,
                    )

            # Return partial success with results
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=all_success,
                data={"update_results": results},
                error=f"Some updates failed: {[k for k, v in results.items() if not v]}",
            )
        except Exception as e:
            return ToolResult(
                tool_type=ToolType.PORTFOLIO_MANAGER,
                success=False,
                data=None,
                error=str(e),
            )
