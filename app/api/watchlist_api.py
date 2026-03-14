"""
Watchlist API endpoints for InversionAPP.

Implements requirements 15.1–15.9:
- POST   /watchlist                       add ticker
- GET    /watchlist                       list all items with metrics
- DELETE /watchlist/{ticker}              remove ticker
- GET    /watchlist/prioritized           sorted by recommendation score
- GET    /watchlist/{ticker}              detailed metrics for one ticker
- GET    /watchlist/compare/{ticker}      compare with current holdings
- GET    /watchlist/{ticker}/allocation-impact  expected allocation change
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
watchlist_service = WatchlistService()

DEFAULT_USER_ID = 1


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AddWatchlistRequest(BaseModel):
    ticker: str
    notes: Optional[str] = None
    target_price: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def add_to_watchlist(request: AddWatchlistRequest):
    """
    Add a ticker to the watchlist.

    Rejects ETF tickers (req 15.10) and duplicate entries (req 15.2).
    Returns the created watchlist record.
    """
    if not request.ticker or not request.ticker.strip():
        raise HTTPException(status_code=400, detail="ticker must not be empty")

    try:
        result = watchlist_service.add_to_watchlist(
            user_id=DEFAULT_USER_ID,
            ticker=request.ticker,
            notes=request.notes,
            target_price=request.target_price,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding to watchlist: {str(e)}",
        )


@router.get("")
async def get_watchlist():
    """
    Retrieve all watchlist items with current market metrics.

    Returns each item enriched with dividend_yield, pe_ratio,
    market_cap, sector, industry (req 15.3, 15.4).
    """
    try:
        items = watchlist_service.get_watchlist_metrics(
            user_id=DEFAULT_USER_ID
        )
        return {"watchlist": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching watchlist: {str(e)}",
        )


@router.get("/prioritized")
async def get_prioritized_watchlist():
    """
    Retrieve watchlist sorted by recommendation score (req 15.7).

    Watchlist stocks receive a priority bonus over non-watchlist candidates.
    """
    try:
        items = watchlist_service.get_prioritized_watchlist(
            user_id=DEFAULT_USER_ID
        )
        return {"watchlist": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching prioritized watchlist: {str(e)}",
        )


@router.get("/compare/{ticker}")
async def compare_with_holdings(ticker: str):
    """
    Compare a watchlist ticker with current portfolio holdings (req 15.6).

    Returns metrics for the ticker alongside portfolio averages.
    """
    try:
        result = watchlist_service.compare_with_holdings(ticker=ticker)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing ticker: {str(e)}",
        )


@router.get("/{ticker}/allocation-impact")
async def get_allocation_impact(
    ticker: str,
    shares: int = Query(1, ge=1, description="Number of shares to evaluate"),
):
    """
    Calculate expected allocation impact if ticker is added (req 15.9).

    Query parameters:
        - shares: Number of shares to hypothetically purchase (default 1)
    """
    try:
        result = watchlist_service.calculate_allocation_impact(
            ticker=ticker, shares=shares
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating allocation impact: {str(e)}",
        )


@router.get("/{ticker}")
async def get_watchlist_ticker(ticker: str):
    """
    Retrieve detailed metrics for a specific watchlist ticker (req 15.3, 15.4).

    Returns 404 if the ticker is not in the watchlist.
    """
    try:
        items = watchlist_service.get_watchlist_metrics(
            user_id=DEFAULT_USER_ID
        )
        item = next(
            (i for i in items if i["ticker"] == ticker.upper()), None
        )
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"{ticker.upper()} not found in watchlist",
            )
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching watchlist ticker: {str(e)}",
        )


@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str):
    """
    Remove a ticker from the watchlist (req 15.2).

    Returns a success message, or 404 if not found.
    """
    try:
        removed = watchlist_service.remove_from_watchlist(
            user_id=DEFAULT_USER_ID, ticker=ticker
        )
        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"{ticker.upper()} not found in watchlist",
            )
        return {
            "message": f"{ticker.upper()} removed from watchlist",
            "ticker": ticker.upper(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error removing from watchlist: {str(e)}",
        )
