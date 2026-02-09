from fastapi import APIRouter

router = APIRouter()

@router.get("/candidates")
def recommendation_candidates():
    return [
        {"ticker": "JEPI", "reason": "High monthly income via covered calls", "sector": "Multi-Asset"},
        {"ticker": "VYM", "reason": "Diversified dividend ETF", "sector": "ETF"}
    ]
