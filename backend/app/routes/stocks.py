from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Any
from app.database import db
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


class StockDataPoint(BaseModel):
    ticker: str
    date: str
    close_price: float
    open_price: float
    volume: float
    high_price: float
    low_price: float
    abs_change: float
    pct_change: float
    action: str
    stop_loss: float
    take_profit: float
    signal_strength: float
    limit_order: float
    current_price: float
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    vwap: float
    bol_bands: List[float]
    sma: List[float]
    crsi: float
    klinger: List[float]
    keltner: List[float]
    cmo: float
    reason: str
    time: int
    diff: int


@router.get("/{ticker}", response_model=List[StockDataPoint])
async def get_stock_data(ticker: str, limit: int = 100):
    # Access the 'indicator_signals' database and 'indicators' collection
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    collection = db.client["indicator_signals"]["indicators"]

    # Find documents for the ticker
    # Sort by date ascending to get chronological order
    cursor = collection.find({"ticker": ticker}).sort("date", 1).limit(limit)
    results = await cursor.to_list(length=limit)

    if not results:
        return []

    return results


@router.get("/", response_model=List[str])
async def get_available_tickers():
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    collection = db.client["indicator_signals"]["indicators"]
    tickers = await collection.distinct("ticker")
    return tickers
