from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/snapshot")
def portfolio_snapshot():
    return {
        "total_value": 2450.75,
        "cash": 200.0,
        "positions": [
            {"symbol": "AVGO", "shares": 0.3571, "value": 357.1},
            {"symbol": "CVX", "shares": 1.0876, "value": 162.3},
            {"symbol": "XOM", "shares": 1.0643, "value": 115.4},
            {"symbol": "JNJ", "shares": 1.0, "value": 175.2}
        ]
    }

@router.get("/time-series")
def portfolio_time_series():
    return {
        "series": [
            {"date": "2026-01-01", "value": 2300},
            {"date": "2026-01-10", "value": 2380},
            {"date": "2026-01-20", "value": 2450}
        ]
    }

@router.get("/dividends-by-asset")
def dividends_by_asset():
    return {
        "dividends": [
            {"symbol": "JNJ", "annual_dividend": 4.76},
            {"symbol": "XOM", "annual_dividend": 3.64},
            {"symbol": "CVX", "annual_dividend": 6.52}
        ]
    }

@router.get("/yield-history")
def yield_history():
    return {
        "yield": [
            {"year": 2024, "yield": 3.8},
            {"year": 2025, "yield": 4.1},
            {"year": 2026, "yield": 4.3}
        ]
    }
