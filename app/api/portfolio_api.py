"""
Portfolio API endpoints.
"""
from fastapi import APIRouter, Query
from typing import Optional
from pydantic import BaseModel
from app.services.portfolio_service import (
    get_portfolio_snapshot,
    get_dashboard,
    get_allocation,
    get_transaction_history,
    record_transaction
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class TransactionRequest(BaseModel):
    ticker: str
    action: str  # "BUY" or "SELL"
    shares: float
    price: float
    transaction_type: str = "PURCHASE"
    notes: Optional[str] = None


@router.get("/snapshot")
def portfolio_snapshot():
    """Get current portfolio snapshot with prices and values."""
    return get_portfolio_snapshot()


@router.get("/dashboard")
def portfolio_dashboard():
    """Get dashboard summary data."""
    return get_dashboard()


@router.get("/allocation")
def portfolio_allocation():
    """Get portfolio allocation percentages."""
    return get_allocation()


@router.get("/history")
def transaction_history(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None)
):
    """Get transaction history with optional filtering."""
    transactions = get_transaction_history(start_date, end_date, ticker)
    return {"transactions": transactions, "count": len(transactions)}


@router.post("/transaction")
def create_transaction(request: TransactionRequest):
    """Record a new buy/sell transaction."""
    result = record_transaction(
        ticker=request.ticker,
        action=request.action,
        shares=request.shares,
        price=request.price,
        transaction_type=request.transaction_type,
        notes=request.notes
    )
    return result
