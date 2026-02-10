from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_portfolio():
    return [
        {
            "symbol": "JNJ",
            "shares": 1.0214,
            "price_per_share": 160,
            "total_value": 163.4,
            "yield_percent": 3.0,
            "sector": "Healthcare"
        }
    ]
