"""
Property 57: Watchlist Metrics Display Completeness
Validates: Requirements 15.3, 15.4

Property: For every item returned by get_watchlist_metrics(), the
required metric fields must be present and non-negative.
"""
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from unittest.mock import patch, MagicMock
from app.database import get_connection, init_database
from app.services.watchlist_service import WatchlistService

USER_ID = 97
REQUIRED_METRIC_FIELDS = [
    "ticker", "current_price", "dividend_yield",
    "pe_ratio", "market_cap", "sector", "industry",
]


@pytest.fixture(autouse=True)
def clean_watchlist():
    init_database()
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE user_id = ?", (USER_ID,))
    conn.commit()
    conn.close()
    yield
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE user_id = ?", (USER_ID,))
    conn.commit()
    conn.close()


@given(
    tickers=st.lists(
        st.from_regex(r"[A-Z]{2,4}", fullmatch=True),
        min_size=1,
        max_size=4,
        unique=True,
    )
)
@settings(max_examples=15, deadline=None)
def test_property_watchlist_metrics_completeness(tickers):
    """
    Property 57: Every metrics item contains all required fields
    with non-negative numeric values.
    """
    service = WatchlistService()

    # Clear and re-seed for this example
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE user_id = ?", (USER_ID,))
    for ticker in tickers:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (user_id, ticker) VALUES (?, ?)",
                (USER_ID, ticker),
            )
        except Exception:
            pass
    conn.commit()
    conn.close()

    # Mock external calls so the test is deterministic
    mock_prices = {t: 100.0 for t in tickers}
    mock_dividends = {t: {"yield": 0.03, "payout": 0.5} for t in tickers}
    mock_valuations = {t: 18.0 for t in tickers}

    with patch(
        "app.services.watchlist_service.get_prices", return_value=mock_prices
    ), patch.object(
        service.dividend_service, "get_dividends", return_value=mock_dividends
    ), patch.object(
        service.valuation_service, "get_valuation", return_value=mock_valuations
    ), patch.object(
        service, "_get_stock_info", return_value=(50_000_000_000, "Technology", "Software")
    ):
        metrics = service.get_watchlist_metrics(USER_ID)

    assert len(metrics) == len(tickers)
    for item in metrics:
        for field in REQUIRED_METRIC_FIELDS:
            assert field in item, f"Missing field '{field}' in metrics item"
        assert item["current_price"] >= 0
        assert item["dividend_yield"] >= 0
        assert item["pe_ratio"] >= 0
        assert item["market_cap"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
