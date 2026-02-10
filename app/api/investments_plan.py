# app/api/investments_plan.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.services.monthly_plan_engine import build_monthly_plan

router = APIRouter()

# ───────────────────────────────
# Request model para Plan Mensual
# ───────────────────────────────
class MonthlyPlanRequest(BaseModel):
    amount: float = 200
    strategy: str = "dividend_growth"
    exclude: List[str] = []

# ───────────────────────────────
# POST /investments/plan/monthly
# ───────────────────────────────
@router.post("/", summary="Genera el plan mensual de inversión")
def generate_monthly_plan(request: MonthlyPlanRequest):
    # Usamos la función del servicio
    plan = build_monthly_plan(request.amount)
    
    # Filtrar tickers excluidos si es necesario
    if request.exclude:
        plan["purchases"] = [
            p for p in plan["purchases"] if p["ticker"] not in request.exclude
        ]
    
    return plan
