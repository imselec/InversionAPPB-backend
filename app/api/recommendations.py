from fastapi import APIRouter
from app.services.scoring_service import calculate_monthly_allocation_dynamic as calculate_monthly_allocation

router = APIRouter()

@router.get("/recommendations/monthly")
def monthly_recommendations():
    return calculate_monthly_allocation()
