"""
Property 59: Watchlist Prioritization in Recommendations
Validates: Requirements 15.7

Property: get_prioritized_watchlist() returns items sorted by score
in descending order, and every score includes the WATCHLIST_PRIORITY_BONUS.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch
from app.database import get_connection, init_database
from app.services.watchlist_service import (
    WatchlistService,
    WATCHLIST_PRIORITY_BONUS,
)

USER_ID = 96


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
        min_size=2,
        max_size=5,
        unique=True,
    )
)
@settings(max_examples=15, deadline=None)
def test_property_watchlist_prioritization_sorted(tickers):
    """
    Property 59: Prioritized watchlist is sorted by score descending.
    """
    service = WatchlistService()

    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE user_id = ?", (USER_ID,))
    for ticker in tickers:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker) VALUES (?, ?)",
            (USER_ID, ticker),
        )
    conn.commit()
    conn.close()

    mock_prices = {t: 100.0 + i * 10 for i, t in enumerate(tickers)}
    mock_dividends = {
        t: {"yield": 0.02 + i * 0.005, "payout": 0.5}
        for i, t in enumerate(tickers)
    }
    mock_valuations = {t: 15.0 + i for i, t in enumerate(tickers)}

    with patch(
        "app.services.watchlist_service.get_prices", return_value=mock_prices
    ), patch.object(
        service.dividend_service, "get_dividends", return_value=mock_dividends
    ), patch.object(
        service.valuation_service, "get_valuation", return_value=mock_valuations
    ), patch.object(
        service, "_get_stock_info",
        return_value=(50_000_000_000, "Technology", "Software"),
    ):
        prioritized = service.get_prioritized_watchlist(USER_ID)

    assert len(prioritized) == len(tickers)

    # Sorted descending
    scores = [item["score"] for item in prioritized]
    assert scores == sorted(scores, reverse=True), (
        f"Expected descending scores, got {scores}"
    )

    # Every score includes the bonus
    for item in prioritized:
        assert item["score"] >= WATCHLIST_PRIORITY_BONUS, (
            f"Score {item['score']} is below WATCHLIST_PRIORITY_BONUS "
            f"{WATCHLIST_PRIORITY_BONUS}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
