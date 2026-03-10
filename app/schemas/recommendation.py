from pydantic import BaseModel
from typing import List


class RecommendationItemOut(BaseModel):
    ticker: str
    weight: float
    allocation_usd: float
    score: float
    buy_signal: bool


class MonthlyRunOut(BaseModel):
    run_id: int
    capital: float
    allocations: List[RecommendationItemOut]