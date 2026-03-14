"""
Property-based tests for alert configuration round-trip.
Property 52: Alert Configuration Round-Trip — Validates: Requirements 14.7, 14.9
"""
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.alert_service import AlertService
from app.database import init_database, get_connection

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

alert_type_st = st.sampled_from(
    ["price", "dividend", "rebalancing", "monthly_investment", "news"]
)

ticker_st = st.one_of(
    st.none(),
    st.sampled_from(["AVGO", "PG", "NEE", "JNJ", "UPS", "CVX", "XOM"]),
)

target_price_st = st.one_of(
    st.none(),
    st.floats(
        min_value=1.0,
        max_value=10_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)

enabled_st = st.booleans()

user_id_st = st.integers(min_value=1, max_value=1_000)


# ---------------------------------------------------------------------------
# Property 52: Alert Configuration Round-Trip
# Validates: Requirements 14.7, 14.9
# ---------------------------------------------------------------------------

@given(
    user_id=user_id_st,
    alert_type=alert_type_st,
    ticker=ticker_st,
    target_price=target_price_st,
    enabled=enabled_st,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_alert_config_roundtrip(
    user_id, alert_type, ticker, target_price, enabled
):
    """
    **Validates: Requirements 14.7, 14.9**

    Property 52: Alert Configuration Round-Trip

    For any valid alert configuration, create_alert followed by
    get_user_alerts MUST return an entry with all fields preserved exactly.
    """
    init_database()
    service = AlertService()

    created = service.create_alert(
        user_id=user_id,
        alert_type=alert_type,
        ticker=ticker,
        target_price=target_price,
        enabled=enabled,
    )

    alert_id = created["id"]

    try:
        alerts = service.get_user_alerts(user_id)
        matching = [a for a in alerts if a["id"] == alert_id]

        assert len(matching) == 1, (
            f"Expected exactly 1 alert with id={alert_id}, "
            f"found {len(matching)}"
        )

        retrieved = matching[0]

        assert retrieved["user_id"] == user_id
        assert retrieved["alert_type"] == alert_type
        assert retrieved["ticker"] == ticker
        assert retrieved["enabled"] == enabled

        # target_price: allow small float rounding tolerance
        if target_price is None:
            assert retrieved["target_price"] is None
        else:
            assert retrieved["target_price"] is not None
            assert abs(retrieved["target_price"] - target_price) < 0.001, (
                f"target_price mismatch: stored={retrieved['target_price']}, "
                f"expected={target_price}"
            )

        # Timestamps must be present
        assert retrieved["created_at"] is not None
        assert retrieved["updated_at"] is not None

    finally:
        # Cleanup
        service.delete_alert(alert_id)


@given(
    user_id=user_id_st,
    alert_type=alert_type_st,
    new_enabled=enabled_st,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_update_alert_preserves_fields(
    user_id, alert_type, new_enabled
):
    """
    **Validates: Requirements 14.7**

    Property 52 (update): After update_alert, get_user_alerts reflects
    the new enabled value while preserving other fields.
    """
    init_database()
    service = AlertService()

    created = service.create_alert(
        user_id=user_id,
        alert_type=alert_type,
        ticker="AVGO",
        target_price=500.0,
        enabled=not new_enabled,  # start with opposite
    )
    alert_id = created["id"]

    try:
        service.update_alert(alert_id, {"enabled": new_enabled})

        alerts = service.get_user_alerts(user_id)
        matching = [a for a in alerts if a["id"] == alert_id]
        assert len(matching) == 1

        retrieved = matching[0]
        assert retrieved["enabled"] == new_enabled
        # Other fields unchanged
        assert retrieved["alert_type"] == alert_type
        assert retrieved["ticker"] == "AVGO"

    finally:
        service.delete_alert(alert_id)

