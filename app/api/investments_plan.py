from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class PlanRequest(BaseModel):
    amount: float = 200
    strategy: str = "dividend_growth"
    exclude: List[str] = []

@router.post("/monthly")
def monthly_plan(body: PlanRequest):
    # Demo: distribuye inversión mensual
    return {
        "investment_amount": body.amount,
        "strategy": body.strategy,
        "purchases": [
            {"ticker": "VYM", "amount_usd": body.amount/2, "shares_to_buy": 0.85, "reason": "High yield diversified ETF"},
            {"ticker": "JNJ", "amount_usd": body.amount/2, "shares_to_buy": 0.62, "reason": "Dividend aristocrat, healthcare sector"},
        ],
        "projected_portfolio": [
            {"symbol": "UPS", "shares": 0.5577, "total_value": 100},
            {"symbol": "TXN", "shares": 0.3150, "total_value": 60},
            {"symbol": "PG", "shares": 0.6941, "total_value": 110},
            {"symbol": "AVGO", "shares": 0.5650, "total_value": 390},
            {"symbol": "CVX", "shares": 1.0876, "total_value": 175},
            {"symbol": "XOM", "shares": 1.0643, "total_value": 118},
            {"symbol": "ABBV", "shares": 0.3574, "total_value": 54},
            {"symbol": "LMT", "shares": 0.2592, "total_value": 125},
            {"symbol": "JNJ", "shares": 1.0214, "total_value": 163},
            {"symbol": "JPM", "shares": 0.2303, "total_value": 32},
            {"symbol": "O", "shares": 1.4206, "total_value": 99},
            {"symbol": "DUK", "shares": 0.2092, "total_value": 21},
            {"symbol": "KO", "shares": 0.5996, "total_value": 36},
            {"symbol": "PEP", "shares": 0.4824, "total_value": 87},
            {"symbol": "NEE", "shares": 0.2875, "total_value": 26},
        ]
    }
