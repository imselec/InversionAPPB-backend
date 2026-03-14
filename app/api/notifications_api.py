"""
Push Notification API endpoints for InversionAPP.

Implements requirement 14.6:
- POST /notifications/register  — register a device token
- DELETE /notifications/unregister — remove a device token
- POST /notifications/test — send a test push notification
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.push_notification_service import PushNotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])
push_service = PushNotificationService()

DEFAULT_USER_ID = 1


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RegisterDeviceRequest(BaseModel):
    device_token: str
    platform: str  # "ios", "android", or "web"


class UnregisterDeviceRequest(BaseModel):
    device_token: str


class TestNotificationRequest(BaseModel):
    device_token: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_device(request: RegisterDeviceRequest):
    """
    Register a device token for push notifications.

    Request body:
        - device_token: FCM/APNs device token string
        - platform: One of 'ios', 'android', 'web'

    Returns the registered device record.
    """
    valid_platforms = {"ios", "android", "web"}
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid platform '{request.platform}'. "
                f"Must be one of: {', '.join(sorted(valid_platforms))}"
            ),
        )

    if not request.device_token or not request.device_token.strip():
        raise HTTPException(
            status_code=400,
            detail="device_token must not be empty",
        )

    try:
        result = push_service.register_device(
            user_id=DEFAULT_USER_ID,
            device_token=request.device_token,
            platform=request.platform,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error registering device: {str(e)}",
        )


@router.delete("/unregister")
async def unregister_device(request: UnregisterDeviceRequest):
    """
    Remove a device token from push notification registry.

    Request body:
        - device_token: The token to deactivate

    Returns a success message.
    """
    if not request.device_token or not request.device_token.strip():
        raise HTTPException(
            status_code=400,
            detail="device_token must not be empty",
        )

    try:
        result = push_service.unregister_device(
            device_token=request.device_token
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error unregistering device: {str(e)}",
        )


@router.post("/test")
async def send_test_notification(request: TestNotificationRequest):
    """
    Send a test push notification to a specific device.

    Request body:
        - device_token: Target device token

    Returns delivery result.
    """
    if not request.device_token or not request.device_token.strip():
        raise HTTPException(
            status_code=400,
            detail="device_token must not be empty",
        )

    test_notification = {
        "title": "InversionAPP Test",
        "body": "Push notifications are working correctly.",
        "type": "test",
    }

    try:
        result = push_service.send_to_device(
            device_token=request.device_token,
            notification=test_notification,
        )
        return {"message": "Test notification sent", "result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test notification: {str(e)}",
        )
