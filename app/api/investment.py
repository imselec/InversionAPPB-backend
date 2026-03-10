from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from app.services.recommendation_engine import RecommendationEngine

router = APIRouter()


class InvestmentRequest(BaseModel):

    tickers: List[str]
    capital: float = 200


@router.post("/run")


def run_engine(request: InvestmentRequest):
    engine = RecommendationEngine()

    return engine.generate_recommendations(
        request.tickers,
        request.capital
    )
