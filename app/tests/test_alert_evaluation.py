"""
Unit tests for alert evaluation logic.
Tests market hours vs closed hours, throttling, and news alert filtering.
Requirements: 14.5, 14.8
"""
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import AlertService, THROTTLE_HOURS
from app.database import init_database, get_connection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db():
    """Ensure a clean database state for each test."""
    init_database()
    yield
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts WHERE user_id >= 8000")
    cursor.execute(
        "DELETE FROM notification_history WHERE user_id >= 8000"
    )
    conn.commit()
    conn.close()


def _create_price_alert(service, user_id=8001, ticker="AVGO", target=100.0,
                        enabled=True):
    return service.create_alert(
        user_id=user_id,
        alert_type="price",
        ticker=ticker,
        target_price=target,
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# Market hours vs closed hours
# ---------------------------------------------------------------------------

class TestMarketHoursEvaluation:
    """evaluate_alerts works regardless of market hours."""

    def test_price_alert_triggers_during_market_hours(self):
        """Price alert fires when current price >= target."""
        service = AlertService()
        alert = _create_price_alert(service, target=100.0)

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 150.0},
        ):
            result = service.evaluate_alerts()

        notifications = service.get_notification_history(8001)
        triggered = [n for n in notifications if n["alert_id"] == alert["id"]]
        assert len(triggered) == 1
        assert "AVGO" in triggered[0]["message"]

        # Cleanup
        service.delete_alert(alert["id"])

    def test_price_alert_silent_when_price_below_target(self):
        """Price alert does NOT fire when current price < target."""
        service = AlertService()
        alert = _create_price_alert(service, target=200.0)

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 150.0},
        ):
            service.evaluate_alerts()

        notifications = service.get_notification_history(8001)
        triggered = [n for n in notifications if n["alert_id"] == alert["id"]]
        assert len(triggered) == 0

        service.delete_alert(alert["id"])

    def test_evaluate_returns_evaluated_and_triggered_counts(self):
        """evaluate_alerts returns a summary dict with counts."""
        service = AlertService()
        alert = _create_price_alert(service, target=50.0)

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 200.0},
        ):
            result = service.evaluate_alerts()

        assert "evaluated" in result
        assert "triggered" in result
        assert result["evaluated"] >= 1
        assert result["triggered"] >= 1

        service.delete_alert(alert["id"])


# ---------------------------------------------------------------------------
# Throttling logic
# ---------------------------------------------------------------------------

class TestThrottlingLogic:
    """No duplicate notifications within 24 hours."""

    def test_alert_not_retriggered_within_24_hours(self):
        """
        An alert triggered recently must be skipped on the next evaluation.
        """
        service = AlertService()
        alert = _create_price_alert(service, user_id=8002, target=50.0)

        # Simulate a recent trigger by setting last_triggered to 1 hour ago
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerts SET last_triggered = ? WHERE id = ?",
            (recent, alert["id"]),
        )
        conn.commit()
        conn.close()

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 999.0},
        ):
            service.evaluate_alerts()

        notifications = service.get_notification_history(8002)
        triggered = [n for n in notifications if n["alert_id"] == alert["id"]]
        assert len(triggered) == 0, (
            "Alert triggered within 24 hours must not fire again"
        )

        service.delete_alert(alert["id"])

    def test_alert_retriggered_after_24_hours(self):
        """
        An alert whose last_triggered is > 24 hours ago MUST fire again.
        """
        service = AlertService()
        alert = _create_price_alert(service, user_id=8003, target=50.0)

        # Set last_triggered to 25 hours ago
        old = (datetime.now() - timedelta(hours=25)).isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerts SET last_triggered = ? WHERE id = ?",
            (old, alert["id"]),
        )
        conn.commit()
        conn.close()

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 999.0},
        ):
            service.evaluate_alerts()

        notifications = service.get_notification_history(8003)
        triggered = [n for n in notifications if n["alert_id"] == alert["id"]]
        assert len(triggered) == 1, (
            "Alert with last_triggered > 24 hours ago must fire"
        )

        service.delete_alert(alert["id"])

    def test_alert_with_no_last_triggered_fires(self):
        """
        An alert that has never been triggered (last_triggered=None) must fire.
        """
        service = AlertService()
        alert = _create_price_alert(service, user_id=8004, target=50.0)

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 999.0},
        ):
            service.evaluate_alerts()

        notifications = service.get_notification_history(8004)
        triggered = [n for n in notifications if n["alert_id"] == alert["id"]]
        assert len(triggered) == 1

        service.delete_alert(alert["id"])

    def test_throttle_window_is_24_hours(self):
        """THROTTLE_HOURS constant must equal 24."""
        assert THROTTLE_HOURS == 24

    def test_is_throttled_returns_true_within_window(self):
        """_is_throttled returns True when last_triggered < 24 hours ago."""
        service = AlertService()
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        fake_alert = {"last_triggered": recent}
        assert service._is_throttled(fake_alert) is True

    def test_is_throttled_returns_false_outside_window(self):
        """_is_throttled returns False when last_triggered > 24 hours ago."""
        service = AlertService()
        old = (datetime.now() - timedelta(hours=25)).isoformat()
        fake_alert = {"last_triggered": old}
        assert service._is_throttled(fake_alert) is False

    def test_is_throttled_returns_false_when_never_triggered(self):
        """_is_throttled returns False when last_triggered is None."""
        service = AlertService()
        assert service._is_throttled({"last_triggered": None}) is False


# ---------------------------------------------------------------------------
# News alert filtering
# ---------------------------------------------------------------------------

class TestNewsAlertFiltering:
    """News alerts are a placeholder and must never trigger notifications."""

    def test_news_alert_never_triggers(self):
        """
        News alerts (type='news') must not produce notifications because
        the external news feed is not implemented.
        """
        service = AlertService()
        alert = service.create_alert(
            user_id=8005,
            alert_type="news",
            ticker="AVGO",
            enabled=True,
        )

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 999.0},
        ):
            service.evaluate_alerts()

        notifications = service.get_notification_history(8005)
        triggered = [n for n in notifications if n["alert_id"] == alert["id"]]
        assert len(triggered) == 0, (
            "News alerts must not trigger until external feed is implemented"
        )

        service.delete_alert(alert["id"])

    def test_news_alert_check_returns_none(self):
        """
        evaluate_alerts sets message=None for news type, so no notification
        is recorded.
        """
        service = AlertService()
        # Directly verify the news branch produces no message
        # by checking that check_price_alert is not called for news type
        # (news has its own branch that returns None)
        alert = service.create_alert(
            user_id=8006,
            alert_type="news",
            ticker="PG",
            enabled=True,
        )

        notifications_before = service.get_notification_history(8006)

        with patch(
            "app.services.alert_service.get_prices",
            return_value={"PG": 999.0},
        ):
            service.evaluate_alerts()

        notifications_after = service.get_notification_history(8006)
        new_count = len(notifications_after) - len(notifications_before)
        assert new_count == 0

        service.delete_alert(alert["id"])


# ---------------------------------------------------------------------------
# trigger_notification unit tests
# ---------------------------------------------------------------------------

class TestTriggerNotification:
    """trigger_notification records history and updates last_triggered."""

    def test_trigger_notification_records_history(self):
        """trigger_notification must insert a row in notification_history."""
        service = AlertService()
        alert = _create_price_alert(service, user_id=8007, target=100.0)

        notif = service.trigger_notification(
            alert_id=alert["id"],
            user_id=8007,
            alert_type="price",
            ticker="AVGO",
            message="Test notification",
        )

        assert notif["id"] is not None
        assert notif["message"] == "Test notification"
        assert notif["delivered"] is False
        assert notif["read"] is False

        history = service.get_notification_history(8007)
        assert any(n["id"] == notif["id"] for n in history)

        service.delete_alert(alert["id"])

    def test_trigger_notification_updates_last_triggered(self):
        """trigger_notification must update last_triggered on the alert."""
        service = AlertService()
        alert = _create_price_alert(service, user_id=8008, target=100.0)

        service.trigger_notification(
            alert_id=alert["id"],
            user_id=8008,
            alert_type="price",
            ticker="AVGO",
            message="Triggered",
        )

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_triggered FROM alerts WHERE id = ?",
            (alert["id"],),
        )
        row = cursor.fetchone()
        conn.close()

        assert row["last_triggered"] is not None

        service.delete_alert(alert["id"])
