"""
Settings API endpoints for InversionAPP.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
settings_service = SettingsService()


class UpdateBudgetRequest(BaseModel):
    budget: float


class UpdateAllocationTargetsRequest(BaseModel):
    targets: Dict


@router.get("/budget")
async def get_monthly_budget():
    """
    Get the current monthly investment budget.
    
    Returns:
        - monthly_budget: Current budget amount
    """
    try:
        budget = settings_service.get_monthly_budget()
        return {"monthly_budget": budget}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching budget: {str(e)}")


@router.put("/budget")
async def update_monthly_budget(request: UpdateBudgetRequest):
    """
    Update the monthly investment budget.
    
    Request body:
        - budget: New monthly budget (minimum $50)
    
    Returns:
        - monthly_budget: Updated budget amount
        - updated_at: Timestamp of update
        - message: Success message
    """
    try:
        result = settings_service.update_monthly_budget(request.budget)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating budget: {str(e)}")


@router.get("/allocation-targets")
async def get_allocation_targets():
    """
    Get custom allocation targets.
    
    Returns allocation target configuration.
    """
    try:
        targets = settings_service.get_allocation_targets()
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching allocation targets: {str(e)}")


@router.put("/allocation-targets")
async def update_allocation_targets(request: UpdateAllocationTargetsRequest):
    """
    Update custom allocation targets.
    
    Request body:
        - targets: Dictionary with allocation configuration
    
    Returns:
        - allocation_targets: Updated targets
        - updated_at: Timestamp of update
        - message: Success message
    """
    try:
        result = settings_service.update_allocation_targets(request.targets)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating allocation targets: {str(e)}")


@router.get("/budget/history")
async def get_budget_history(
    limit: int = Query(10, description="Number of history entries to retrieve", ge=1, le=100)
):
    """
    Get history of budget changes.
    
    Query parameters:
        - limit: Number of entries to retrieve (1-100, default 10)
    
    Returns list of past budget changes.
    """
    try:
        history = settings_service.get_budget_change_history(limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching budget history: {str(e)}")
