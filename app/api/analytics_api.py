"""
Analytics API endpoints.
Returns flat fields matching frontend PerformanceMetrics interface:
  total_return_pct, annualized_return_pct, portfolio_yield_pct, volatility
"""
from fastapi import APIRouter
from app.services.analytics_service import (
    calculate_total_return,
    calculate_annualized_return,
    calculate_portfolio_dividend_yield,
    calculate_per_ticker_returns,
    calculate_portfolio_volatility,
    calculate_sp500_comparison
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/performance")
def get_performance_metrics():
    """
    Get portfolio performance metrics (flat fields for frontend).
    """
    total_return = calculate_total_return()
    annualized = calculate_annualized_return()
    div_yield = calculate_portfolio_dividend_yield()
    volatility = calculate_portfolio_volatility()

    return {
        "total_return_pct": total_return.get("total_return_pct", 0),
        "annualized_return_pct": annualized.get("annualized_return_pct", 0),
        "portfolio_yield_pct": div_yield.get("portfolio_yield", 0),
        "volatility": volatility.get("volatility", 0),
        # Extra detail fields
        "total_invested": total_return.get("total_invested", 0),
        "current_value": total_return.get("current_value", 0),
        "total_return": total_return.get("total_return", 0),
        "years_invested": annualized.get("years_invested", 0),
        "total_annual_dividends": div_yield.get("total_annual_dividends", 0),
    }


@router.get("/returns")
def get_per_ticker_returns():
    """
    Get per-ticker return breakdown as a flat array.
    Frontend expects: TickerReturn[] directly (not wrapped).
    """
    returns = calculate_per_ticker_returns()
    return returns


@router.get("/volatility")
def get_volatility_metrics():
    """Get portfolio volatility metrics."""
    return calculate_portfolio_volatility()


@router.get("/comparison")
def get_sp500_comparison():
    """Get performance comparison vs S&P 500."""
    return calculate_sp500_comparison()
