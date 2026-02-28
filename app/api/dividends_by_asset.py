from fastapi import APIRouter

router = APIRouter()


@router.get("/dividends-by-asset")
def dividends_by_asset():
    return {
        "data": [
            {"ticker": "JNJ", "annual_dividend": 120},
            {"ticker": "PG", "annual_dividend": 95},
            {"ticker": "KO", "annual_dividend": 80},
            {"ticker": "XOM", "annual_dividend": 140},
        ]
    }
