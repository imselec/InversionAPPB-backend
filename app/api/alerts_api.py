"""
Alert API endpoints for InversionAPP.

Implements requirements 14.7, 14.8, 14.9, 14.10:
- Full CRUD for alert configuration
- Notification history with pagination
- Alert enable/disable toggle
- Manual alert evaluation (admin/testing)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])
alert_service = AlertService()

# Default user ID for single-user app
DEFAULT_USER_ID = 1


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateAlertRequest(BaseModel):
    alert_type: str
    ticker: Optional[str] = None
    target_price: Optional[float] = None
    enabled: bool = True


class UpdateAlertRequest(BaseModel):
    alert_type: Optional[str] = None
    ticker: Optional[str] = None
    target_price: Optional[float] = None
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def create_alert(request: CreateAlertRequest):
    """
    Create a new alert rule.

    Request body:
        - alert_type: One of 'price', 'dividend', 'rebalancing',
                      'monthly_investment', 'news'
        - ticker: Stock ticker (required for price/dividend/news alerts)
        - target_price: Target price for price alerts
        - enabled: Whether the alert is active (default True)

    Returns the created alert.
    """
    valid_types = {"price", "dividend", "rebalancing", "monthly_investment", "news"}
    if request.alert_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid alert_type. Must be one of: {', '.join(sorted(valid_types))}",
        )

    if request.alert_type in ("price", "dividend", "news") and not request.ticker:
        raise HTTPException(
            status_code=400,
            detail=f"ticker is required for alert_type '{request.alert_type}'",
        )

    if request.alert_type == "price" and (
        request.target_price is None or request.target_price <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="target_price must be a positive number for price alerts",
        )

    try:
        alert = alert_service.create_alert(
            user_id=DEFAULT_USER_ID,
            alert_type=request.alert_type,
            ticker=request.ticker,
            target_price=request.target_price,
            enabled=request.enabled,
        )
        return alert
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating alert: {str(e)}")


@router.get("")
async def get_alerts():
    """
    Retrieve all alert rules for the current user.

    Returns a list of alerts ordered by created_at descending.
    """
    try:
        alerts = alert_service.get_user_alerts(user_id=DEFAULT_USER_ID)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


@router.get("/history")
async def get_notification_history(
    limit: int = Query(50, description="Maximum number of records to return", ge=1, le=200),
    offset: int = Query(0, description="Number of records to skip for pagination", ge=0),
):
    """
    Retrieve notification history with pagination.

    Query parameters:
        - limit: Max records to return (1-200, default 50)
        - offset: Records to skip (default 0)

    Returns paginated notification history ordered by sent_at descending.
    """
    try:
        # Fetch limit + offset so we can slice for offset-based pagination
        history = alert_service.get_notification_history(
            user_id=DEFAULT_USER_ID, limit=limit + offset
        )
        paginated = history[offset: offset + limit]
        return {
            "history": paginated,
            "count": len(paginated),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notification history: {str(e)}")


@router.get("/{alert_id}")
async def get_alert(alert_id: int):
    """
    Retrieve a specific alert by ID.

    Returns the alert details, or 404 if not found.
    """
    try:
        alerts = alert_service.get_user_alerts(user_id=DEFAULT_USER_ID)
        alert = next((a for a in alerts if a["id"] == alert_id), None)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alert: {str(e)}")


@router.put("/{alert_id}")
async def update_alert(alert_id: int, request: UpdateAlertRequest):
    """
    Update an existing alert configuration.

    Request body (all fields optional):
        - alert_type: New alert type
        - ticker: New ticker symbol
        - target_price: New target price
        - enabled: New enabled state

    Returns the updated alert, or 404 if not found.
    """
    params = request.model_dump(exclude_none=True)
    if not params:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        updated = alert_service.update_alert(alert_id=alert_id, params=params)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating alert: {str(e)}")


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    """
    Delete an alert rule.

    Returns a success message, or 404 if not found.
    """
    try:
        deleted = alert_service.delete_alert(alert_id=alert_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return {"message": f"Alert {alert_id} deleted successfully", "id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting alert: {str(e)}")


@router.put("/{alert_id}/toggle")
async def toggle_alert(alert_id: int):
    """
    Toggle an alert's enabled/disabled state.

    Flips the current enabled state of the alert.
    Returns the updated alert, or 404 if not found.
    """
    try:
        # Fetch current state
        alerts = alert_service.get_user_alerts(user_id=DEFAULT_USER_ID)
        alert = next((a for a in alerts if a["id"] == alert_id), None)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        new_enabled = not alert["enabled"]
        updated = alert_service.update_alert(
            alert_id=alert_id, params={"enabled": new_enabled}
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling alert: {str(e)}")


@router.post("/evaluate")
async def evaluate_alerts():
    """
    Manually trigger alert evaluation (admin/testing).

    Evaluates all active alerts and triggers notifications for met conditions.

    Returns a summary with counts of evaluated and triggered alerts.
    """
    try:
        result = alert_service.evaluate_alerts()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating alerts: {str(e)}")
