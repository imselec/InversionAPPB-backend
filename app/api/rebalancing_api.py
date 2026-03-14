"""
Rebalancing API endpoints for InversionAPP.
"""
from fastapi import APIRouter, HTTPException
from ..services.rebalancing_service import RebalancingService

router = APIRouter(prefix="/rebalancing", tags=["rebalancing"])
rebalancing_service = RebalancingService()


@router.get("/status")
async def get_balance_status():
    """
    Get current portfolio balance status.
    
    Returns:
        - total_value: Total portfolio value
        - target_allocation: Target percentage per stock
        - stock_count: Number of stocks in portfolio
        - allocations: List of stocks with current vs target allocation
    """
    try:
        status = rebalancing_service.check_balance_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking balance status: {str(e)}")


@router.get("/recommendations")
async def get_rebalancing_recommendations():
    """
    Get specific trade recommendations to rebalance portfolio.
    
    Returns list of buy/sell recommendations to achieve target allocation.
    """
    try:
        recommendations = rebalancing_service.get_rebalancing_recommendations()
        return {"recommendations": recommendations, "count": len(recommendations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.post("/alerts/generate")
async def generate_alerts():
    """
    Generate and store rebalancing alerts for imbalanced positions.
    
    Returns list of generated alerts.
    """
    try:
        alerts = rebalancing_service.generate_rebalancing_alerts()
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating alerts: {str(e)}")


@router.get("/alerts")
async def get_active_alerts():
    """
    Get all active (unresolved) rebalancing alerts.
    
    Returns list of active alerts sorted by severity.
    """
    try:
        alerts = rebalancing_service.get_active_alerts()
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")
