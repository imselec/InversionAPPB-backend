"""
Property-based tests for dividend alert triggering.
Property 47: Dividend Alert Triggering — Validates: Requirements 14.2
"""
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import (
    AlertService,
    DIVIDEND_LOOKAHEAD_DAYS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary(ex_div_date):
    """Build a minimal yahooquery summary_detail mock payload."""
    return {
        "TEST": {
            "exDividendDate": ex_div_date,
        }
    }


# ---------------------------------------------------------------------------
# Property 47: Dividend Alert Triggering
# Validates: Requirements 14.2
# ---------------------------------------------------------------------------

@given(
    days_ahead=st.integers(min_value=0, max_value=DIVIDEND_LOOKAHEAD_DAYS),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_dividend_alert_triggers_within_window(days_ahead):
    """
    **Validates: Requirements 14.2**

    Property 47 (triggers): Dividend Alert Triggering

    When the ex-dividend date is within the 7-day look-ahead window
    (0 <= days_ahead <= 7), check_dividend_alert MUST return a non-None
    message.
    """
    ex_div_dt = datetime.now() + timedelta(days=days_ahead)
    ex_div_ts = ex_div_dt.timestamp()

    mock_ticker = MagicMock()
    mock_ticker.summary_detail = _make_summary(ex_div_ts)

    service = AlertService()

    with patch(
        "app.services.alert_service.Ticker",
        return_value=mock_ticker,
    ):
        result = service.check_dividend_alert(ticker="TEST")

    assert result is not None, (
        f"Expected alert when ex-dividend is {days_ahead} day(s) away, "
        f"but got None"
    )
    assert isinstance(result, str) and len(result) > 0


@given(
    days_ahead=st.integers(min_value=DIVIDEND_LOOKAHEAD_DAYS + 1, max_value=365),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_dividend_alert_silent_outside_window(days_ahead):
    """
    **Validates: Requirements 14.2**

    Property 47 (silent): Dividend Alert Triggering

    When the ex-dividend date is beyond the 7-day look-ahead window,
    check_dividend_alert MUST return None.
    """
    ex_div_dt = datetime.now() + timedelta(days=days_ahead)
    ex_div_ts = ex_div_dt.timestamp()

    mock_ticker = MagicMock()
    mock_ticker.summary_detail = _make_summary(ex_div_ts)

    service = AlertService()

    with patch(
        "app.services.alert_service.Ticker",
        return_value=mock_ticker,
    ):
        result = service.check_dividend_alert(ticker="TEST")

    assert result is None, (
        f"Expected None when ex-dividend is {days_ahead} day(s) away "
        f"(outside 7-day window), but got: {result!r}"
    )


def test_dividend_alert_returns_none_when_no_ex_date():
    """
    **Validates: Requirements 14.2**

    Edge case: missing exDividendDate → None.
    """
    mock_ticker = MagicMock()
    mock_ticker.summary_detail = {"TEST": {}}

    service = AlertService()

    with patch("app.services.alert_service.Ticker", return_value=mock_ticker):
        result = service.check_dividend_alert(ticker="TEST")

    assert result is None


def test_dividend_alert_returns_none_for_empty_ticker():
    """
    **Validates: Requirements 14.2**

    Edge case: empty ticker string → None without calling yahooquery.
    """
    service = AlertService()
    result = service.check_dividend_alert(ticker="")
    assert result is None


def test_dividend_alert_message_contains_ticker():
    """
    **Validates: Requirements 14.2**

    Unit check: triggered message must mention the ticker.
    """
    ex_div_dt = datetime.now() + timedelta(days=3)
    mock_ticker = MagicMock()
    # Key must match the ticker passed to check_dividend_alert
    mock_ticker.summary_detail = {"PG": {"exDividendDate": ex_div_dt.timestamp()}}

    service = AlertService()

    with patch("app.services.alert_service.Ticker", return_value=mock_ticker):
        result = service.check_dividend_alert(ticker="PG")

    assert result is not None
    assert "PG" in result

