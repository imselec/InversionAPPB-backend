"""
Unit tests for PushNotificationService.
Tests device token registration/unregistration, payload formatting,
retry logic, and inactive token cleanup.
Requirements: 14.6
"""
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.push_notification_service import (
    PushNotificationService,
    MAX_RETRIES,
    BACKOFF_BASE,
    FCM_ENDPOINT,
)
from app.database import init_database, get_connection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db():
    """Ensure a clean database state for each test."""
    init_database()
    # Ensure failure_count column exists (migration for older DBs)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(device_tokens)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "failure_count" not in cols:
        cursor.execute(
            "ALTER TABLE device_tokens "
            "ADD COLUMN failure_count INTEGER DEFAULT 0"
        )
        conn.commit()
    conn.close()
    yield
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM device_tokens WHERE user_id >= 9000")
    conn.commit()
    conn.close()


@pytest.fixture
def service():
    return PushNotificationService()


def _insert_token(user_id, token, platform="android", active=1,
                  failure_count=0):
    """Helper to insert a device token directly into the DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO device_tokens
            (user_id, device_token, platform, active, failure_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, token, platform, active, failure_count),
    )
    conn.commit()
    conn.close()


def _get_token_row(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM device_tokens WHERE device_token = ?", (token,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


# ---------------------------------------------------------------------------
# Device token registration
# ---------------------------------------------------------------------------

class TestRegisterDevice:
    def test_register_new_token(self, service):
        result = service.register_device(9001, "token-abc", "android")
        assert result["registered"] is True
        assert result["device_token"] == "token-abc"
        assert result["platform"] == "android"

        row = _get_token_row("token-abc")
        assert row is not None
        assert row["active"] == 1
        assert row["user_id"] == 9001

    def test_register_ios_token(self, service):
        result = service.register_device(9001, "token-ios", "ios")
        assert result["registered"] is True
        row = _get_token_row("token-ios")
        assert row["platform"] == "ios"

    def test_register_web_token(self, service):
        result = service.register_device(9001, "token-web", "web")
        assert result["registered"] is True
        row = _get_token_row("token-web")
        assert row["platform"] == "web"

    def test_register_reactivates_inactive_token(self, service):
        _insert_token(9001, "token-reactivate", active=0, failure_count=3)
        result = service.register_device(9001, "token-reactivate", "android")
        assert result["registered"] is True
        row = _get_token_row("token-reactivate")
        assert row["active"] == 1

    def test_register_invalid_platform_raises(self, service):
        with pytest.raises(ValueError, match="Unsupported platform"):
            service.register_device(9001, "token-bad", "blackberry")


# ---------------------------------------------------------------------------
# Device token unregistration
# ---------------------------------------------------------------------------

class TestUnregisterDevice:
    def test_unregister_sets_inactive(self, service):
        _insert_token(9002, "token-unreg", active=1)
        result = service.unregister_device("token-unreg")
        assert result["unregistered"] is True
        row = _get_token_row("token-unreg")
        assert row["active"] == 0

    def test_unregister_nonexistent_token_returns_gracefully(self, service):
        result = service.unregister_device("token-does-not-exist")
        assert result["unregistered"] is True


# ---------------------------------------------------------------------------
# Payload formatting
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def test_ios_payload_has_apns_block(self, service):
        notification = {"title": "Hello", "body": "World", "data": {}}
        payload = service._build_payload("tok", notification, "ios")
        assert "apns" in payload
        aps = payload["apns"]["payload"]["aps"]
        assert aps["alert"]["title"] == "Hello"
        assert aps["alert"]["body"] == "World"
        assert aps["sound"] == "default"
        assert aps["badge"] == 1

    def test_android_payload_has_android_block(self, service):
        notification = {"title": "Hi", "body": "There", "data": {}}
        payload = service._build_payload("tok", notification, "android")
        assert "android" in payload
        assert payload["android"]["priority"] == "high"
        assert "apns" not in payload

    def test_web_payload_has_android_block(self, service):
        notification = {"title": "Hi", "body": "There", "data": {}}
        payload = service._build_payload("tok", notification, "web")
        assert "android" in payload
        assert "apns" not in payload

    def test_payload_includes_to_field(self, service):
        notification = {"title": "T", "body": "B", "data": {}}
        for platform in ("ios", "android", "web"):
            payload = service._build_payload("my-token", notification, platform)
            assert payload["to"] == "my-token"

    def test_payload_includes_data(self, service):
        notification = {
            "title": "T", "body": "B",
            "data": {"key": "value"},
        }
        payload = service._build_payload("tok", notification, "android")
        assert payload["data"] == {"key": "value"}

    def test_ios_and_android_payloads_differ(self, service):
        notification = {"title": "T", "body": "B", "data": {}}
        ios_payload = service._build_payload("tok", notification, "ios")
        android_payload = service._build_payload("tok", notification, "android")
        assert ios_payload != android_payload


# ---------------------------------------------------------------------------
# Retry logic (exponential backoff, 3 attempts max)
# ---------------------------------------------------------------------------

class TestRetryLogic:
    def test_retries_on_500_then_succeeds(self, service):
        """Succeeds on the 3rd attempt after two 500 errors."""
        fail_response = MagicMock()
        fail_response.status_code = 500

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"success": 1, "failure": 0}

        with patch(
            "app.services.push_notification_service.requests.post",
            side_effect=[fail_response, fail_response, ok_response],
        ), patch("app.services.push_notification_service.time.sleep") as mock_sleep:
            result = service.send_to_device(
                "tok", {"title": "T", "body": "B", "data": {}}, "android"
            )

        assert result is True
        # Two sleeps for the two failed attempts
        assert mock_sleep.call_count == 2

    def test_returns_false_after_max_retries_exhausted(self, service):
        """Returns False when all MAX_RETRIES attempts return 500."""
        fail_response = MagicMock()
        fail_response.status_code = 500

        with patch(
            "app.services.push_notification_service.requests.post",
            return_value=fail_response,
        ), patch("app.services.push_notification_service.time.sleep"):
            result = service.send_to_device(
                "tok", {"title": "T", "body": "B", "data": {}}, "android"
            )

        assert result is False

    def test_max_retries_is_3(self):
        assert MAX_RETRIES == 3

    def test_exponential_backoff_delays(self, service):
        """Sleep durations follow BACKOFF_BASE ** attempt pattern."""
        fail_response = MagicMock()
        fail_response.status_code = 500

        with patch(
            "app.services.push_notification_service.requests.post",
            return_value=fail_response,
        ), patch(
            "app.services.push_notification_service.time.sleep"
        ) as mock_sleep:
            service.send_to_device(
                "tok", {"title": "T", "body": "B", "data": {}}, "android"
            )

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        # Attempts 0 and 1 trigger sleeps; attempt 2 is the last so no sleep
        assert sleep_calls == [BACKOFF_BASE ** 0, BACKOFF_BASE ** 1]

    def test_no_retry_on_non_retriable_error(self, service):
        """Non-retriable HTTP errors (e.g. 401) return False immediately."""
        bad_response = MagicMock()
        bad_response.status_code = 401

        with patch(
            "app.services.push_notification_service.requests.post",
            return_value=bad_response,
        ) as mock_post, patch(
            "app.services.push_notification_service.time.sleep"
        ) as mock_sleep:
            result = service.send_to_device(
                "tok", {"title": "T", "body": "B", "data": {}}, "android"
            )

        assert result is False
        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()

    def test_request_exception_triggers_retry(self, service):
        """Network errors trigger retry with backoff."""
        import requests as req_lib

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"success": 1, "failure": 0}

        with patch(
            "app.services.push_notification_service.requests.post",
            side_effect=[
                req_lib.RequestException("timeout"),
                ok_response,
            ],
        ), patch(
            "app.services.push_notification_service.time.sleep"
        ) as mock_sleep:
            result = service.send_to_device(
                "tok", {"title": "T", "body": "B", "data": {}}, "android"
            )

        assert result is True
        assert mock_sleep.call_count == 1


# ---------------------------------------------------------------------------
# Inactive token cleanup after 3 consecutive failures
# ---------------------------------------------------------------------------

class TestInactiveTokenCleanup:
    def test_failure_increments_failure_count(self, service):
        _insert_token(9003, "token-fail", failure_count=0)
        service.handle_delivery_status("token-fail", success=False)
        row = _get_token_row("token-fail")
        assert row["failure_count"] == 1
        assert row["active"] == 1

    def test_token_marked_inactive_after_3_failures(self, service):
        _insert_token(9003, "token-3fail", failure_count=2)
        service.handle_delivery_status("token-3fail", success=False)
        row = _get_token_row("token-3fail")
        assert row["failure_count"] == 3
        assert row["active"] == 0

    def test_success_resets_failure_count(self, service):
        _insert_token(9003, "token-reset", failure_count=2)
        service.handle_delivery_status("token-reset", success=True)
        row = _get_token_row("token-reset")
        assert row["failure_count"] == 0
        assert row["active"] == 1

    def test_success_reactivates_token(self, service):
        _insert_token(9003, "token-reactivate2", active=0, failure_count=3)
        service.handle_delivery_status("token-reactivate2", success=True)
        row = _get_token_row("token-reactivate2")
        assert row["active"] == 1

    def test_cleanup_inactive_tokens_removes_them(self, service):
        _insert_token(9004, "token-cleanup1", active=0)
        _insert_token(9004, "token-cleanup2", active=0)
        _insert_token(9004, "token-cleanup3", active=1)

        deleted = service.cleanup_inactive_tokens()
        assert deleted >= 2

        assert _get_token_row("token-cleanup1") is None
        assert _get_token_row("token-cleanup2") is None
        assert _get_token_row("token-cleanup3") is not None

    def test_send_notification_skips_inactive_tokens(self, service):
        """send_notification only sends to active tokens."""
        _insert_token(9005, "token-active", active=1)
        _insert_token(9005, "token-inactive", active=0)

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"success": 1, "failure": 0}

        with patch(
            "app.services.push_notification_service.requests.post",
            return_value=ok_response,
        ) as mock_post:
            result = service.send_notification(
                user_id=9005, title="Test", body="Body"
            )

        # Only one active token should be contacted
        assert mock_post.call_count == 1
        assert result["sent"] == 1
        assert result["failed"] == 0
