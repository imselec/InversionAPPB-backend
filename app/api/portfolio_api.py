"""
Portfolio API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel
import traceback
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


class HoldingUpdateRequest(BaseModel):
    shares: float
    avg_price: Optional[float] = None


@router.get("/snapshot")
def portfolio_snapshot():
    """Get current portfolio snapshot with prices and values."""
    return get_portfolio_snapshot()


@router.get("/dashboard")
def portfolio_dashboard():
    """Get dashboard summary data."""
    try:
        return get_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")


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


@router.put("/holding/{ticker}")
def update_holding(ticker: str, request: HoldingUpdateRequest):
    """Directly update shares and avg_price for a holding (manual correction)."""
    from app.database import get_connection
    from datetime import datetime
    import csv, os
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker.upper(),))
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            "UPDATE portfolio SET shares = ?, avg_price = ?, last_updated = ? WHERE ticker = ?",
            (request.shares, request.avg_price, datetime.now(), ticker.upper())
        )
    else:
        cursor.execute(
            "INSERT INTO portfolio (ticker, shares, avg_price, last_updated) VALUES (?, ?, ?, ?)",
            (ticker.upper(), request.shares, request.avg_price, datetime.now())
        )
    conn.commit()
    conn.close()
    # Persist changes to CSV so they survive restarts
    _sync_portfolio_to_csv()
    return {"ticker": ticker.upper(), "shares": request.shares, "avg_price": request.avg_price}


@router.delete("/holding/{ticker}")
def delete_holding(ticker: str):
    """Remove a holding from the portfolio."""
    from app.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()
    # Persist changes to CSV so they survive restarts
    _sync_portfolio_to_csv()
    return {"deleted": ticker.upper()}


def _sync_portfolio_to_csv():
    """Write current DB portfolio state back to CSV for persistence across restarts."""
    import csv, os
    from app.database import get_connection
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "portfolio.csv"
    )
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, shares, avg_price FROM portfolio ORDER BY ticker")
        rows = cursor.fetchall()
        conn.close()
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ticker", "shares", "avg_price"])
            for row in rows:
                writer.writerow([row["ticker"], row["shares"], row["avg_price"] or ""])
    except Exception as e:
        print(f"Warning: could not sync portfolio to CSV: {e}")
