"""
Analytics API endpoints.
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
    Get portfolio performance metrics.
    Returns total return, annualized return, and dividend yield.
    """
    total_return = calculate_total_return()
    annualized_return = calculate_annualized_return()
    dividend_yield = calculate_portfolio_dividend_yield()
    
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "dividend_yield": dividend_yield
    }


@router.get("/returns")
def get_per_ticker_returns():
    """
    Get per-ticker return breakdown.
    Returns cost basis, current value, gain/loss, and return % for each holding.
    """
    returns = calculate_per_ticker_returns()
    
    return {
        "returns": returns,
        "count": len(returns)
    }


@router.get("/volatility")
def get_volatility_metrics():
    """
    Get portfolio volatility metrics.
    Returns annualized volatility (standard deviation of returns).
    """
    volatility = calculate_portfolio_volatility()
    
    return volatility


@router.get("/comparison")
def get_sp500_comparison():
    """
    Get performance comparison vs S&P 500.
    Returns portfolio return, S&P 500 return, and alpha.
    """
    comparison = calculate_sp500_comparison()
    
    return comparison
