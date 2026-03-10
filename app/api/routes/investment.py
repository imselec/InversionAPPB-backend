from fastapi import APIRouter

from app.services.recommendation_engine import generate_recommendation

router = APIRouter()


@router.post("/run")
def run_investment():

    capital = 200

    assets = [
        {"ticker": "LMT", "yield": 2.8, "momentum": 0.7, "volatility": 0.3},
        {"ticker": "ABBV", "yield": 3.9, "momentum": 0.6, "volatility": 0.4},
        {"ticker": "TXN", "yield": 3.1, "momentum": 0.5, "volatility": 0.3},
        {"ticker": "CAT", "yield": 1.7, "momentum": 0.8, "volatility": 0.5},
        {"ticker": "JNJ", "yield": 3.0, "momentum": 0.4, "volatility": 0.2},
    ]

    result = generate_recommendation(assets, capital)

    return result
