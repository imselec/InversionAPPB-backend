from fastapi import APIRouter

router = APIRouter(prefix="/history", tags=["history"])

@router.get("")
def history():
    return {
        "operations": [
            {
                "date": "2026-01-05",
                "symbol": "AVGO",
                "action": "BUY",
                "amount": 0.15,
                "price": 1180
            }
        ]
    }
