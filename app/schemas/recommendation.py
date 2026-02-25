# backend/app/schemas/recommendation.py
from pydantic import BaseModel
from typing import List, Dict


class RecommendationItemSchema(BaseModel):
    ticker: str
    score: float
    allocated_amount: float
    rule_trace: Dict


class RecommendationRunSchema(BaseModel):
    run_id: int
    status: str
    items: List[RecommendationItemSchema]

    model_config = {"from_attributes": True}
