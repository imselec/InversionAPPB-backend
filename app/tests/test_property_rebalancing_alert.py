"""
Property-based tests for rebalancing alert triggering.
Property 48: Rebalancing Alert Triggering — Validates: Requirements 14.3
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import (
    AlertService,
    REBALANCING_DEVIATION_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _portfolio_with_deviation(ticker, deviation):
    """Build a minimal portfolio dict with one deviating allocation."""
    return {
        "allocations": [
            {
                "ticker": ticker,
                "current_allocation": 10.0 + deviation,
                "target_allocation": 10.0,
                "deviation": deviation,
            }
        ]
    }


# ---------------------------------------------------------------------------
# Property 48: Rebalancing Alert Triggering
# Validates: Requirements 14.3
# ---------------------------------------------------------------------------

@given(
    excess=st.floats(
        min_value=0.01,
        max_value=50.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_rebalancing_alert_triggers_on_deviation(excess):
    """
    **Validates: Requirements 14.3**

    Property 48 (triggers): Rebalancing Alert Triggering

    When any allocation deviates by more than 5% from target,
    check_rebalancing_alert MUST return a non-None message.
    """
    deviation = REBALANCING_DEVIATION_THRESHOLD + excess
    portfolio = _portfolio_with_deviation("TEST", deviation)

    service = AlertService()
    result = service.check_rebalancing_alert(portfolio=portfolio)

    assert result is not None, (
        f"Expected alert when deviation={deviation:.2f}% "
        f"(> {REBALANCING_DEVIATION_THRESHOLD}%), but got None"
    )
    assert isinstance(result, str) and len(result) > 0


@given(
    deviation=st.floats(
        min_value=-REBALANCING_DEVIATION_THRESHOLD,
        max_value=REBALANCING_DEVIATION_THRESHOLD,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_rebalancing_alert_silent_within_threshold(deviation):
    """
    **Validates: Requirements 14.3**

    Property 48 (silent): Rebalancing Alert Triggering

    When all allocations deviate by <= 5% from target,
    check_rebalancing_alert MUST return None.
    """
    portfolio = _portfolio_with_deviation("TEST", deviation)

    service = AlertService()
    result = service.check_rebalancing_alert(portfolio=portfolio)

    assert result is None, (
        f"Expected None when deviation={deviation:.2f}% "
        f"(<= {REBALANCING_DEVIATION_THRESHOLD}%), but got: {result!r}"
    )


@given(
    num_deviating=st.integers(min_value=1, max_value=10),
    excess=st.floats(
        min_value=0.01,
        max_value=20.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_rebalancing_alert_counts_all_deviating(
    num_deviating, excess
):
    """
    **Validates: Requirements 14.3**

    Property 48 (count): Rebalancing Alert Triggering

    The alert message must reflect that at least one position is deviating.
    """
    deviation = REBALANCING_DEVIATION_THRESHOLD + excess
    allocations = [
        {
            "ticker": f"STOCK{i}",
            "current_allocation": 10.0 + deviation,
            "target_allocation": 10.0,
            "deviation": deviation,
        }
        for i in range(num_deviating)
    ]
    portfolio = {"allocations": allocations}

    service = AlertService()
    result = service.check_rebalancing_alert(portfolio=portfolio)

    assert result is not None
    # Message should mention the count of deviating positions
    assert str(num_deviating) in result


def test_rebalancing_alert_empty_portfolio_returns_none():
    """
    **Validates: Requirements 14.3**

    Edge case: empty allocations list → None.
    """
    service = AlertService()
    result = service.check_rebalancing_alert(portfolio={"allocations": []})
    assert result is None

