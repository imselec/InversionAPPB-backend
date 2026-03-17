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


class ManualDividendRequest(BaseModel):
    ticker: str
    payment_date: str
    per_share_amount: float
    reinvested: bool = False


@router.get("/summary")
async def get_dividend_summary():
    try:
        return dividend_service.get_dividend_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-ticker")
async def get_dividends_by_ticker():
    try:
        data = dividend_service.get_dividends_by_ticker()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_dividend_history(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None)
):
    try:
        history = dividend_service.get_dividend_history(
            start_date, end_date, ticker
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reinvestment")
async def record_dividend_reinvestment(request: DividendReinvestmentRequest):
    try:
        return dividend_service.record_dividend_reinvestment(
            request.ticker,
            request.dividend_amount,
            request.reinvestment_price
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_historical_dividends():
    """Import last 2 years of dividend history from yfinance."""
    try:
        return dividend_service.import_historical_dividends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record")
async def record_manual_dividend(request: ManualDividendRequest):
    """Record a single dividend payment manually."""
    try:
        return dividend_service.record_manual_dividend(
            request.ticker,
            request.payment_date,
            request.per_share_amount,
            request.reinvested
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chart")
async def get_dividend_chart_data(
    period: str = Query("12m")
):
    try:
        if period not in ["1m", "3m", "6m", "12m"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid period. Use 1m, 3m, 6m, or 12m"
            )
        return dividend_service.get_dividend_chart_data(period)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
