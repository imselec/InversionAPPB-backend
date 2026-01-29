from fastapi import APIRouter
from app.services.portfolio_service import (
    portfolio_snapshot,
    portfolio_time_series
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/snapshot")
def snapshot():
    return portfolio_snapshot()

@router.get("/time-series")
def time_series():
    return portfolio_time_series()
