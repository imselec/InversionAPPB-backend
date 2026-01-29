from fastapi import APIRouter

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("")
def alerts():
    return {
        "alerts": [
            {
                "type": "price",
                "symbol": "AVGO",
                "message": "AVGO dropped 5% this week"
            }
        ]
    }
