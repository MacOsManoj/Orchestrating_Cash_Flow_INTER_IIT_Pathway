# backend/app/routes/portfolio_trades.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from app.database import get_trades_database

router = APIRouter()

# ============================================================================
# SCHEMAS
# ============================================================================


class TradeRequest(BaseModel):
    """Request model for executing a trade"""

    asset_type: Literal["stocks", "bonds", "forex"]
    ticker: str
    action: Literal["buy", "sell"]
    quantity: float = Field(gt=0, description="Quantity to buy/sell")
    price: float = Field(gt=0, description="Price per unit")
    asset_name: Optional[str] = None


class TradeResponse(BaseModel):
    """Response model for a trade execution"""

    trade_id: str
    status: str
    message: str
    trade: dict


class PortfolioState(BaseModel):
    """Current portfolio state"""

    total_deposits: float = 100000000
    free_cash: float = 5000000
    loans: float = 65000000
    amount_in_govt_bonds: float = 24000000
    amount_in_stocks: float = 4000000
    amount_in_forex: float = 2000000


class AssetDistribution(BaseModel):
    """Asset distribution response"""

    total_portfolio_value: float
    free_cash: float
    invested_amount: float
    asset_breakdown: dict


# ============================================================================
# INITIAL STATE DOCUMENT - These are MAX HOLDINGS (limits)
# ============================================================================

# Initial state represents the MAXIMUM possible holdings in each asset class
INITIAL_STATE = {
    "_id": "initial_state",
    "total_deposits": 100000000,
    "free_cash": 5000000,  # Max free cash limit
    "loans": 65000000,
    "max_govt_bonds": 24000000,  # Max allowed in bonds
    "max_stocks": 4000000,  # Max allowed in stocks
    "max_forex": 2000000,  # Max allowed in forex
    "created_at": datetime.utcnow().isoformat(),
}

# Current portfolio state - tracks actual current holdings
CURRENT_PORTFOLIO_INITIAL = {
    "_id": "current_portfolio",
    "free_cash": 5000000,  # Starting free cash (all deposits available initially)
    "amount_in_govt_bonds": 0,  # Starting bond holdings
    "amount_in_stocks": 0,  # Starting stock holdings
    "amount_in_forex": 0,  # Starting forex holdings
    "total_invested": 0,  # Total invested amount
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def get_initial_state():
    """Get initial state (max holdings limits)"""
    db = get_trades_database()
    state_collection = db["initial_state"]

    state = await state_collection.find_one({"_id": "initial_state"})
    if not state:
        await state_collection.insert_one(INITIAL_STATE.copy())
        state = INITIAL_STATE.copy()

    return state


async def get_or_create_current_portfolio():
    """Get current portfolio or create if not exists"""
    db = get_trades_database()
    portfolio_collection = db["current_portfolio"]

    portfolio = await portfolio_collection.find_one({"_id": "current_portfolio"})
    if not portfolio:
        await portfolio_collection.insert_one(CURRENT_PORTFOLIO_INITIAL.copy())
        portfolio = CURRENT_PORTFOLIO_INITIAL.copy()

    return portfolio


async def update_current_portfolio(asset_type: str, amount_change: float, is_buy: bool):
    """Update current portfolio after a trade"""
    db = get_trades_database()
    portfolio_collection = db["current_portfolio"]
    initial_state = await get_initial_state()

    # Map asset type to field name
    asset_field_map = {
        "stocks": "amount_in_stocks",
        "bonds": "amount_in_govt_bonds",
        "forex": "amount_in_forex",
    }

    max_field_map = {
        "stocks": "max_stocks",
        "bonds": "max_govt_bonds",
        "forex": "max_forex",
    }

    field_name = asset_field_map.get(asset_type)
    max_field = max_field_map.get(asset_type)

    if not field_name:
        raise HTTPException(status_code=400, detail=f"Invalid asset type: {asset_type}")

    # Get current portfolio
    portfolio = await get_or_create_current_portfolio()
    max_allowed = initial_state.get(max_field, float("inf"))

    if is_buy:
        # Buying: decrease free_cash, increase asset amount
        new_free_cash = portfolio["free_cash"] - amount_change
        new_asset_amount = portfolio[field_name] + amount_change

        if new_free_cash < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient free cash. Available: ₹{portfolio['free_cash']:,.2f}, Required: ₹{amount_change:,.2f}",
            )

        # Check max holdings limit
        if new_asset_amount > max_allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Exceeds max {asset_type} limit. Max allowed: ₹{max_allowed:,.2f}, Would be: ₹{new_asset_amount:,.2f}",
            )
    else:
        # Selling: increase free_cash, decrease asset amount
        new_free_cash = portfolio["free_cash"] + amount_change
        new_asset_amount = portfolio[field_name] - amount_change

        if new_asset_amount < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {asset_type} holdings. Available: ₹{portfolio[field_name]:,.2f}, Trying to sell: ₹{amount_change:,.2f}",
            )

        # Check max free cash limit
        max_free_cash = initial_state.get("free_cash", float("inf"))
        if new_free_cash > max_free_cash:
            raise HTTPException(
                status_code=400,
                detail=f"Exceeds max free cash limit. Max allowed: ₹{max_free_cash:,.2f}",
            )

    # Calculate new total invested
    new_total_invested = (
        (
            new_asset_amount
            if field_name == "amount_in_stocks"
            else portfolio["amount_in_stocks"]
        )
        + (
            new_asset_amount
            if field_name == "amount_in_govt_bonds"
            else portfolio["amount_in_govt_bonds"]
        )
        + (
            new_asset_amount
            if field_name == "amount_in_forex"
            else portfolio["amount_in_forex"]
        )
    )

    # Update portfolio
    await portfolio_collection.update_one(
        {"_id": "current_portfolio"},
        {
            "$set": {
                "free_cash": new_free_cash,
                field_name: new_asset_amount,
                "total_invested": new_total_invested,
                "updated_at": datetime.utcnow().isoformat(),
            }
        },
    )

    return {
        "free_cash": new_free_cash,
        field_name: new_asset_amount,
        "total_invested": new_total_invested,
    }


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/trade", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """
    Execute a buy or sell trade.
    Updates both the user-trades collection and current portfolio.
    """
    db = get_trades_database()
    trades_collection = db["user_trades"]

    # Calculate total trade value
    trade_value = trade.quantity * trade.price

    # Update current portfolio
    try:
        await update_current_portfolio(
            asset_type=trade.asset_type,
            amount_change=trade_value,
            is_buy=(trade.action == "buy"),
        )
    except HTTPException:
        raise

    # Create trade record
    trade_record = {
        "asset_type": trade.asset_type,
        "ticker": trade.ticker,
        "asset_name": trade.asset_name or trade.ticker,
        "action": trade.action,
        "quantity": trade.quantity,
        "price": trade.price,
        "total_value": trade_value,
        "executed_at": datetime.utcnow().isoformat(),
        "status": "completed",
    }

    # Insert trade record
    result = await trades_collection.insert_one(trade_record)
    trade_record["_id"] = str(result.inserted_id)

    return TradeResponse(
        trade_id=str(result.inserted_id),
        status="success",
        message=f"Successfully {'bought' if trade.action == 'buy' else 'sold'} {trade.quantity} units of {trade.ticker} at ₹{trade.price:,.2f}",
        trade=trade_record,
    )


@router.get("/initial-distribution")
async def get_initial_distribution():
    """
    Get the initial asset distribution and value.
    Returns the static initial state.
    """
    initial = INITIAL_STATE.copy()
    initial.pop("_id", None)
    initial.pop("created_at", None)
    initial.pop("updated_at", None)

    total_invested = (
        initial["amount_in_govt_bonds"]
        + initial["amount_in_stocks"]
        + initial["amount_in_forex"]
    )

    total_portfolio = initial["free_cash"] + total_invested

    return {
        "total_portfolio_value": total_portfolio,
        "free_cash": initial["free_cash"],
        "invested_amount": total_invested,
        "loans": initial["loans"],
        "total_deposits": initial["total_deposits"],
        "asset_breakdown": {
            "govt_bonds": {
                "amount": initial["amount_in_govt_bonds"],
                "percentage": round(
                    (initial["amount_in_govt_bonds"] / total_portfolio) * 100, 2
                ),
            },
            "stocks": {
                "amount": initial["amount_in_stocks"],
                "percentage": round(
                    (initial["amount_in_stocks"] / total_portfolio) * 100, 2
                ),
            },
            "forex": {
                "amount": initial["amount_in_forex"],
                "percentage": round(
                    (initial["amount_in_forex"] / total_portfolio) * 100, 2
                ),
            },
            "free_cash": {
                "amount": initial["free_cash"],
                "percentage": round((initial["free_cash"] / total_portfolio) * 100, 2),
            },
        },
    }


@router.get("/current-distribution")
async def get_current_distribution():
    """
    Get the current asset distribution after all trades.
    Returns the live state from database.
    """
    state = await get_or_create_current_portfolio()

    total_invested = (
        state["amount_in_govt_bonds"]
        + state["amount_in_stocks"]
        + state["amount_in_forex"]
    )

    total_portfolio = state["free_cash"] + total_invested

    return {
        "total_portfolio_value": total_portfolio,
        "free_cash": state["free_cash"],
        "invested_amount": total_invested,
        "loans": state.get("loans", 0),
        "total_deposits": state.get("total_deposits", 0),
        "asset_breakdown": {
            "govt_bonds": {
                "amount": state["amount_in_govt_bonds"],
                "percentage": round(
                    (state["amount_in_govt_bonds"] / total_portfolio) * 100, 2
                )
                if total_portfolio > 0
                else 0,
            },
            "stocks": {
                "amount": state["amount_in_stocks"],
                "percentage": round(
                    (state["amount_in_stocks"] / total_portfolio) * 100, 2
                )
                if total_portfolio > 0
                else 0,
            },
            "forex": {
                "amount": state["amount_in_forex"],
                "percentage": round(
                    (state["amount_in_forex"] / total_portfolio) * 100, 2
                )
                if total_portfolio > 0
                else 0,
            },
            "free_cash": {
                "amount": state["free_cash"],
                "percentage": round((state["free_cash"] / total_portfolio) * 100, 2)
                if total_portfolio > 0
                else 0,
            },
        },
        "last_updated": state.get("updated_at"),
    }


@router.get("/trades")
async def get_trade_history(
    asset_type: Optional[str] = None, ticker: Optional[str] = None, limit: int = 50
):
    """
    Get trade history with optional filters.
    """
    db = get_trades_database()
    trades_collection = db["user_trades"]

    # Build query
    query = {}
    if asset_type:
        query["asset_type"] = asset_type
    if ticker:
        query["ticker"] = ticker

    # Fetch trades
    cursor = trades_collection.find(query).sort("executed_at", -1).limit(limit)
    trades = []
    async for trade in cursor:
        trade["_id"] = str(trade["_id"])
        trades.append(trade)

    return {"trades": trades, "count": len(trades)}


@router.post("/reset-state")
async def reset_portfolio_state():
    """
    Reset the portfolio state to initial values.
    Useful for testing.
    """
    db = get_trades_database()
    state_collection = db["portfolio_state"]

    # Delete and recreate
    await state_collection.delete_one({"_id": "portfolio_state"})
    await state_collection.insert_one(INITIAL_STATE.copy())

    return {
        "status": "success",
        "message": "Portfolio state reset to initial values",
        "state": INITIAL_STATE,
    }
