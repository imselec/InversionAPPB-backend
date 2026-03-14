"""
Property-based tests for push notification delivery.
Property 51: Push Notification Delivery — Validates: Requirements 14.6
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.push_notification_service import PushNotificationService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

device_token_st = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="-_:",
    ),
    min_size=10,
    max_size=200,
)

notification_st = st.fixed_dictionaries({
    "title": st.text(min_size=1, max_size=100),
    "body": st.text(min_size=1, max_size=500),
    "data": st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.text(min_size=0, max_size=50),
        max_size=5,
    ),
})

platform_st = st.sampled_from(["ios", "android", "web"])


# ---------------------------------------------------------------------------
# Property 51: Push Notification Delivery
# Validates: Requirements 14.6
# ---------------------------------------------------------------------------

@given(
    device_token=device_token_st,
    notification=notification_st,
    platform=platform_st,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_send_to_device_returns_true_on_fcm_success(
    device_token, notification, platform
):
    """
    **Validates: Requirements 14.6**

    Property 51 (success): Push Notification Delivery

    For any valid device token and message, send_to_device MUST return True
    when FCM responds with HTTP 200 and success=1.
    """
    service = PushNotificationService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": 1, "failure": 0}

    with patch("app.services.push_notification_service.requests.post",
               return_value=mock_response):
        result = service.send_to_device(
            device_token=device_token,
            notification=notification,
            platform=platform,
        )

    assert result is True, (
        f"send_to_device must return True on FCM success, "
        f"got {result!r} for token={device_token!r}, platform={platform}"
    )


@given(
    device_token=device_token_st,
    notification=notification_st,
    platform=platform_st,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_send_to_device_returns_false_on_fcm_failure(
    device_token, notification, platform
):
    """
    **Validates: Requirements 14.6**

    Property 51 (failure): Push Notification Delivery

    For any valid device token and message, send_to_device MUST return False
    when FCM responds with HTTP 200 but failure=1 (token rejected).
    """
    service = PushNotificationService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": 0, "failure": 1}

    with patch("app.services.push_notification_service.requests.post",
               return_value=mock_response):
        result = service.send_to_device(
            device_token=device_token,
            notification=notification,
            platform=platform,
        )

    assert result is False, (
        f"send_to_device must return False on FCM failure, "
        f"got {result!r} for token={device_token!r}, platform={platform}"
    )


@given(
    device_token=device_token_st,
    notification=notification_st,
    platform=platform_st,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_send_to_device_returns_false_on_server_error(
    device_token, notification, platform
):
    """
    **Validates: Requirements 14.6**

    Property 51 (server error): Push Notification Delivery

    For any valid device token and message, send_to_device MUST return False
    when FCM consistently returns 500 (all retries exhausted).
    """
    service = PushNotificationService()

    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("app.services.push_notification_service.requests.post",
               return_value=mock_response), \
         patch("app.services.push_notification_service.time.sleep"):
        result = service.send_to_device(
            device_token=device_token,
            notification=notification,
            platform=platform,
        )

    assert result is False, (
        f"send_to_device must return False after all retries exhausted, "
        f"got {result!r} for token={device_token!r}, platform={platform}"
    )
