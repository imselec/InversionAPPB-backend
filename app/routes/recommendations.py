from fastapi import APIRouter

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("")
def recommendations():
    return {
        "recommended": [
            {
                "symbol": "PG",
                "reason": "Defensive dividend stock",
                "confidence": 0.82
            },
            {
                "symbol": "KO",
                "reason": "Stable cash flow",
                "confidence": 0.78
            }
        ]
    }

@router.get("/candidates")
def recommendation_candidates():
    return {
        "candidates": [
            {"symbol": "PEP"},
            {"symbol": "TXN"},
            {"symbol": "JPM"}
        ]
    }
