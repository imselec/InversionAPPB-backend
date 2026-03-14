"""
Market data API endpoints.
"""
from fastapi import APIRouter, Query
from typing import List
from app.services.market_data_service import (
    get_prices,
    get_price_changes,
    is_market_open,
    get_cached_price
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices")
def market_prices(tickers: str = Query(..., description="Comma-separated list of tickers")):
    """Get current prices for list of tickers."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    prices = get_prices(ticker_list)
    
    return {
        "prices": prices,
        "market_open": is_market_open(),
        "tickers_count": len(ticker_list)
    }


@router.get("/changes")
def market_changes(tickers: str = Query(..., description="Comma-separated list of tickers")):
    """Get daily price changes and percentages."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    changes = get_price_changes(ticker_list)
    
    return {
        "changes": changes,
        "market_open": is_market_open()
    }


@router.get("/status")
def market_status():
    """Get market open/closed status."""
    return {
        "market_open": is_market_open(),
        "market": "US Stock Market",
        "hours": "9:30 AM - 4:00 PM ET"
    }


@router.get("/cached/{ticker}")
def cached_price(ticker: str):
    """Get cached price with staleness indicator."""
    return get_cached_price(ticker.upper())
