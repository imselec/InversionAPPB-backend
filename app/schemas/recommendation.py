from pydantic import BaseModel
from typing import List, Dict


# =========================
# Item Schema
# =========================
class RecommendationItemSchema(BaseModel):
    ticker: str
    score: float
    allocated_amount: float
    rule_trace: Dict[str, float]

    class Config:
        orm_mode = True


# =========================
# Run Schema
# =========================
class RecommendationRunSchema(BaseModel):
    run_id: int
    capital: float
    status: str
    items: List[RecommendationItemSchema]

    class Config:
        orm_mode = True