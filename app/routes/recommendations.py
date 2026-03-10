from fastapi import APIRouter
from app.services.recommendation_engine import RecommendationEngine

router = APIRouter()

engine = RecommendationEngine()


@router.get("/recommendations/top-pick")
def get_top_pick():

    capital = 200

    tickers = [
        "LMT",
        "ABBV",
        "TXN",
        "CAT",
        "JNJ"
    ]

    result = engine.run_investment(capital, tickers)

    # devolver solo el mejor
    top_pick = result["results"][0]

    return {
        "top_pick": top_pick
    }
