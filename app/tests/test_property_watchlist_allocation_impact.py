"""
Property 61: Watchlist Allocation Impact Calculation
Validates: Requirements 15.9

Property: calculate_allocation_impact() must satisfy:
- new_allocation_pct >= 0
- portfolio_value_after >= portfolio_value_before
- impact_pct == new_allocation_pct - current_allocation_pct
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch
from app.services.watchlist_service import WatchlistService


@given(
    ticker=st.from_regex(r"[A-Z]{2,5}", fullmatch=True),
    current_price=st.floats(min_value=1.0, max_value=5000.0),
    portfolio_value=st.floats(min_value=0.0, max_value=1_000_000.0),
    shares=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=15)
def test_property_allocation_impact_invariants(
    ticker, current_price, portfolio_value, shares
):
    """
    Property 61: Allocation impact calculation invariants.
    """
    service = WatchlistService()

    with patch(
        "app.services.watchlist_service.get_prices",
        return_value={ticker: current_price},
    ), patch(
        "app.services.watchlist_service.get_connection"
    ) as mock_conn:
        mock_cursor = mock_conn.return_value
        mock_cursor.execute.return_value.fetchone.return_value = {
            "total": portfolio_value
        }

        result = service.calculate_allocation_impact(ticker=ticker, shares=shares)

    assert result["new_allocation_pct"] >= 0, (
        "new_allocation_pct must be non-negative"
    )
    assert result["portfolio_value_after"] >= result["portfolio_value_before"], (
        "portfolio value must not decrease after hypothetical purchase"
    )
    expected_impact = round(
        result["new_allocation_pct"] - result["current_allocation_pct"], 4
    )
    assert abs(result["impact_pct"] - expected_impact) < 1e-6, (
        f"impact_pct {result['impact_pct']} != "
        f"new - current = {expected_impact}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
