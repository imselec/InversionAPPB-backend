"""
Dividend API endpoints for InversionAPP.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from ..services.dividend_service import DividendService

router = APIRouter(prefix="/dividends", tags=["dividends"])
dividend_service = DividendService()


class DividendReinvestmentRequest(BaseModel):
    ticker: str
    dividend_amount: float
    reinvestment_price: float


@router.get("/summary")
async def get_dividend_summary():
    """
    Get monthly and yearly dividend totals.
    
    Returns:
        - monthly_total: Total dividends received in last 30 days
        - yearly_total: Total dividends received in last 365 days
        - total_all_time: Total dividends received all time
    """
    try:
        summary = dividend_service.get_dividend_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dividend summary: {str(e)}")


@router.get("/by-ticker")
async def get_dividends_by_ticker():
    """
    Get dividend data per stock.
    
    Returns list of stocks with:
        - ticker: Stock symbol
        - total_dividends: Total dividends received from this stock
        - payment_count: Number of dividend payments
        - last_payment_date: Date of most recent payment
        - avg_per_share: Average dividend per share
    """
    try:
        data = dividend_service.get_dividends_by_ticker()
        return {"dividends": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dividends by ticker: {str(e)}")


@router.get("/history")
async def get_dividend_history(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol")
):
    """
    Get historical dividend payments with optional filtering.
    
    Query parameters:
        - start_date: Filter payments after this date (YYYY-MM-DD)
        - end_date: Filter payments before this date (YYYY-MM-DD)
        - ticker: Filter by specific stock symbol
    
    Returns list of dividend payments with full details.
    """
    try:
        history = dividend_service.get_dividend_history(start_date, end_date, ticker)
        return {"payments": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dividend history: {str(e)}")


@router.post("/reinvestment")
async def record_dividend_reinvestment(request: DividendReinvestmentRequest):
    """
    Record a dividend reinvestment transaction.
    
    Request body:
        - ticker: Stock symbol
        - dividend_amount: Total dividend amount to reinvest
        - reinvestment_price: Price per share for reinvestment
    
    Returns:
        - ticker: Stock symbol
        - dividend_amount: Amount reinvested
        - reinvestment_price: Price per share
        - shares_purchased: Number of shares purchased
        - new_total_shares: New total shares owned
    """
    try:
        result = dividend_service.record_dividend_reinvestment(
            request.ticker,
            request.dividend_amount,
            request.reinvestment_price
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording dividend reinvestment: {str(e)}")


@router.get("/chart")
async def get_dividend_chart_data(
    period: str = Query("12m", description="Time period: 1m, 3m, 6m, 12m")
):
    """
    Get dividend income data for visualization.
    
    Query parameters:
        - period: Time period (1m, 3m, 6m, 12m)
    
    Returns monthly aggregated dividend data for charting.
    """
    try:
        if period not in ["1m", "3m", "6m", "12m"]:
            raise HTTPException(status_code=400, detail="Invalid period. Use 1m, 3m, 6m, or 12m")
        
        chart_data = dividend_service.get_dividend_chart_data(period)
        return {"period": period, "data": chart_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")
