"""
Property 56: Watchlist Removal
Validates: Requirements 15.2

Property: After removing a ticker from the watchlist, it must NOT
appear in get_watchlist() for that user.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch
from app.database import get_connection, init_database
from app.services.watchlist_service import WatchlistService

USER_ID = 98


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


@given(ticker=st.from_regex(r"[A-Z]{2,5}", fullmatch=True))
@settings(max_examples=15)
def test_property_watchlist_removal(ticker):
    """
    Property 56: After removing a ticker, it must not appear in get_watchlist().
    """
    service = WatchlistService()

    with patch.object(service, "_is_etf", return_value=False):
        # Add first (ignore duplicate errors)
        try:
            service.add_to_watchlist(user_id=USER_ID, ticker=ticker)
        except ValueError:
            pass

        # Remove
        service.remove_from_watchlist(user_id=USER_ID, ticker=ticker)

        watchlist = service.get_watchlist(USER_ID)
        tickers_in_list = [item["ticker"] for item in watchlist]
        assert ticker not in tickers_in_list, (
            f"Expected {ticker} to be absent after removal, got {tickers_in_list}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
