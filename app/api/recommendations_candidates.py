from fastapi import APIRouter

router = APIRouter()

@router.get("")
def recommendation_candidates():
    return [
        {
            "ticker": "NEE",
            "reason": "Utility con crecimiento y dividendo estable",
            "sector": "Utilities"
        },
        {
            "ticker": "TXN",
            "reason": "Semiconductores defensivos con dividendos crecientes",
            "sector": "Technology"
        }
    ]
