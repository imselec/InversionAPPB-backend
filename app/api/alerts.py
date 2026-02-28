from fastapi import APIRouter

router = APIRouter()


@router.get("/alerts")
def get_alerts():
    return {
        "alerts": [
            {
                "type": "opportunity",
                "ticker": "JNJ",
                "message": "Strong buy opportunity based on scoring engine",
                "score": 87.5,
            }
        ]
    }
