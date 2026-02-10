from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class MonthlyPlanRequest(BaseModel):
    monthly_amount: float
    currency: str = "USD"
    strategy: str = "dividend_growth"
    exclude: List[str] = []

@router.post("/plan/monthly")
def generate_monthly_plan(body: MonthlyPlanRequest):
    return {
        "investment_amount": body.monthly_amount,
        "purchases": [
            {
                "ticker": "JNJ",
                "amount_usd": 100,
                "shares": 0.62,
                "rationale": "Dividend aristocrat reforzado"
            },
            {
                "ticker": "O",
                "amount_usd": 100,
                "shares": 0.45,
                "rationale": "REIT mensual defensivo"
            }
        ]
    }
