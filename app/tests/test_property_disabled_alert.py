"""
Property-based tests for disabled alert non-triggering.
Property 53: Disabled Alert Non-Triggering — Validates: Requirements 14.8
"""
from datetime import datetime, timedelta
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import AlertService
from app.database import init_database, get_connection

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

user_id_st = st.integers(min_value=1, max_value=1_000)

alert_type_st = st.sampled_from(
    ["price", "dividend", "rebalancing", "monthly_investment"]
)


# ---------------------------------------------------------------------------
# Property 53: Disabled Alert Non-Triggering
# Validates: Requirements 14.8
# ---------------------------------------------------------------------------

@given(
    user_id=user_id_st,
    alert_type=alert_type_st,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_disabled_alert_never_triggers(user_id, alert_type):
    """
    **Validates: Requirements 14.8**

    Property 53: Disabled Alert Non-Triggering

    Alerts with enabled=False MUST never appear in triggered notifications.
    evaluate_alerts() must skip disabled alerts entirely.
    """
    init_database()
    service = AlertService()

    # Create a disabled alert
    created = service.create_alert(
        user_id=user_id,
        alert_type=alert_type,
        ticker="AVGO",
        target_price=1.0,   # very low target → would trigger if enabled
        enabled=False,
    )
    alert_id = created["id"]

    # Record notification count before evaluation
    history_before = service.get_notification_history(user_id)
    count_before = len(history_before)

    try:
        # Mock prices so price alerts would fire if enabled
        mock_prices = {"AVGO": 999_999.0}

        # Mock dividend check to return a message if called
        def _fake_dividend(ticker):
            return f"Dividend alert for {ticker}"

        # Mock rebalancing to return a message if called
        def _fake_rebalancing(portfolio=None):
            return "Rebalancing alert triggered"

        # Mock monthly investment to return a message if called
        def _fake_monthly(user_settings=None):
            return "Monthly investment reminder"

        with (
            patch(
                "app.services.alert_service.get_prices",
                return_value=mock_prices,
            ),
            patch.object(service, "check_dividend_alert", _fake_dividend),
            patch.object(service, "check_rebalancing_alert", _fake_rebalancing),
            patch.object(
                service, "check_monthly_investment_alert", _fake_monthly
            ),
        ):
            result = service.evaluate_alerts()

        # Notification count must not have increased for this user's alert
        history_after = service.get_notification_history(user_id)
        new_notifications = [
            n for n in history_after
            if n["alert_id"] == alert_id
        ]

        assert len(new_notifications) == 0, (
            f"Disabled alert (id={alert_id}, type={alert_type}) "
            f"must not generate notifications, but found: {new_notifications}"
        )

    finally:
        service.delete_alert(alert_id)
        # Clean up any stray notifications
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM notification_history WHERE alert_id = ?",
            (alert_id,),
        )
        conn.commit()
        conn.close()


def test_disabled_alert_not_returned_in_evaluate_triggered_count():
    """
    **Validates: Requirements 14.8**

    Unit check: evaluate_alerts triggered count must be 0 when only
    disabled alerts exist.
    """
    init_database()
    service = AlertService()

    # Create a disabled price alert with a very low target
    created = service.create_alert(
        user_id=9999,
        alert_type="price",
        ticker="AVGO",
        target_price=0.01,
        enabled=False,
    )
    alert_id = created["id"]

    try:
        with patch(
            "app.services.alert_service.get_prices",
            return_value={"AVGO": 999_999.0},
        ):
            result = service.evaluate_alerts()

        # The disabled alert must not contribute to triggered count
        notifications = service.get_notification_history(9999)
        triggered_for_alert = [
            n for n in notifications if n["alert_id"] == alert_id
        ]
        assert len(triggered_for_alert) == 0

    finally:
        service.delete_alert(alert_id)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM notification_history WHERE alert_id = ?",
            (alert_id,),
        )
        conn.commit()
        conn.close()

