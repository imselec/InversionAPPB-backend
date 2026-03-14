"""
Property-based tests for monthly investment alert triggering.
Property 49: Monthly Investment Alert Triggering — Validates: Requirements 14.4
"""
from datetime import date, timedelta
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import (
    AlertService,
    MONTHLY_INVESTMENT_LOOKAHEAD_DAYS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings_for_day(investment_day: int):
    return {"monthly_investment_day": investment_day}


def _today_plus(days: int) -> date:
    return date.today() + timedelta(days=days)


# ---------------------------------------------------------------------------
# Property 49: Monthly Investment Alert Triggering
# Validates: Requirements 14.4
# ---------------------------------------------------------------------------

@given(
    days_ahead=st.integers(
        min_value=0,
        max_value=MONTHLY_INVESTMENT_LOOKAHEAD_DAYS,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_monthly_investment_alert_triggers_within_window(days_ahead):
    """
    **Validates: Requirements 14.4**

    Property 49 (triggers): Monthly Investment Alert Triggering

    When the investment day is within the 3-day look-ahead window,
    check_monthly_investment_alert MUST return a non-None message.
    """
    target_date = _today_plus(days_ahead)
    investment_day = target_date.day
    # Clamp to valid range 1-28 to avoid month-boundary issues
    assume(1 <= investment_day <= 28)

    service = AlertService()
    result = service.check_monthly_investment_alert(
        user_settings=_settings_for_day(investment_day)
    )

    assert result is not None, (
        f"Expected alert when investment_day={investment_day} is "
        f"{days_ahead} day(s) away, but got None"
    )
    assert isinstance(result, str) and len(result) > 0


@given(
    days_ahead=st.integers(
        min_value=MONTHLY_INVESTMENT_LOOKAHEAD_DAYS + 1,
        max_value=27,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_monthly_investment_alert_silent_outside_window(days_ahead):
    """
    **Validates: Requirements 14.4**

    Property 49 (silent): Monthly Investment Alert Triggering

    When the investment day is more than 3 days away,
    check_monthly_investment_alert MUST return None.
    """
    target_date = _today_plus(days_ahead)
    investment_day = target_date.day
    assume(1 <= investment_day <= 28)

    service = AlertService()
    result = service.check_monthly_investment_alert(
        user_settings=_settings_for_day(investment_day)
    )

    assert result is None, (
        f"Expected None when investment_day={investment_day} is "
        f"{days_ahead} day(s) away, but got: {result!r}"
    )


def test_monthly_investment_alert_message_contains_date():
    """
    **Validates: Requirements 14.4**

    Unit check: triggered message must mention the investment date.
    """
    # Use today as the investment day so it triggers immediately
    today = date.today()
    assume_day = today.day
    if assume_day > 28:
        assume_day = 1  # fallback

    service = AlertService()
    result = service.check_monthly_investment_alert(
        user_settings={"monthly_investment_day": assume_day}
    )

    if result is not None:
        # Message should contain a date string
        assert any(char.isdigit() for char in result)

