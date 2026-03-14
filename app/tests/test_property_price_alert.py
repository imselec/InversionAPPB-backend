"""
Property-based tests for price alert triggering.
Property 46: Price Alert Triggering — Validates: Requirements 14.1
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import AlertService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

positive_price = st.floats(
    min_value=0.01,
    max_value=100_000.0,
    allow_nan=False,
    allow_infinity=False,
)


# ---------------------------------------------------------------------------
# Property 46: Price Alert Triggering
# Validates: Requirements 14.1
# ---------------------------------------------------------------------------

@given(
    target_price=positive_price,
    premium=st.floats(
        min_value=0.0,
        max_value=50_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_price_alert_triggers_when_reached(target_price, premium):
    """
    **Validates: Requirements 14.1**

    Property 46 (triggers): Price Alert Triggering

    For any current_price >= target_price, check_price_alert MUST return
    a non-None message string.
    """
    current_price = target_price + premium
    service = AlertService()

    result = service.check_price_alert(
        ticker="TEST",
        target_price=target_price,
        current_price=current_price,
    )

    assert result is not None, (
        f"Expected alert message when current_price={current_price} "
        f">= target_price={target_price}, but got None"
    )
    assert isinstance(result, str) and len(result) > 0, (
        "Alert message must be a non-empty string"
    )


@given(
    target_price=positive_price,
    gap=st.floats(
        min_value=0.01,
        max_value=50_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_price_alert_silent_below_target(target_price, gap):
    """
    **Validates: Requirements 14.1**

    Property 46 (silent): Price Alert Triggering

    For any current_price < target_price, check_price_alert MUST return None.
    """
    current_price = target_price - gap
    assume(current_price > 0)

    service = AlertService()

    result = service.check_price_alert(
        ticker="TEST",
        target_price=target_price,
        current_price=current_price,
    )

    assert result is None, (
        f"Expected None when current_price={current_price} "
        f"< target_price={target_price}, but got: {result!r}"
    )


def test_price_alert_message_contains_ticker_and_prices():
    """
    **Validates: Requirements 14.1**

    Unit check: the alert message must mention the ticker and both prices.
    """
    service = AlertService()
    result = service.check_price_alert(
        ticker="AVGO",
        target_price=900.0,
        current_price=950.0,
    )
    assert result is not None
    assert "AVGO" in result
    assert "950" in result or "950.00" in result
    assert "900" in result or "900.00" in result


def test_price_alert_returns_none_for_invalid_inputs():
    """
    **Validates: Requirements 14.1**

    Edge cases: None/zero target_price or zero current_price → None.
    """
    service = AlertService()
    assert service.check_price_alert("AVGO", None, 950.0) is None
    assert service.check_price_alert("AVGO", 0.0, 950.0) is None
    assert service.check_price_alert("AVGO", 900.0, 0.0) is None
    assert service.check_price_alert("", 900.0, 950.0) is None

