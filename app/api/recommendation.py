from fastapi import APIRouter

router = APIRouter()

@router.get("")
def recommendations():
    # Mock dinámico según tu cartera
    return [
        {"ticker": "VYM", "allocation_usd": 100, "yield": 3.1, "reason": "High yield ETF", "score": 88},
        {"ticker": "JEPI", "allocation_usd": 120, "yield": 4.0, "reason": "Monthly income via covered calls", "score": 90}
    ]
