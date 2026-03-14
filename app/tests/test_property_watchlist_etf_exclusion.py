"""
Property 62: Watchlist ETF Exclusion
Validates: Requirements 15.10

Property: Attempting to add an ETF ticker to the watchlist must
raise a ValueError and the ticker must NOT appear in the watchlist.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch
from app.database import get_connection, init_database
from app.services.watchlist_service import WatchlistService

USER_ID = 95


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
def test_property_etf_rejected_from_watchlist(ticker):
    """
    Property 62: ETF tickers are rejected with ValueError and not stored.
    """
    service = WatchlistService()

    # Force _is_etf to return True
    with patch.object(service, "_is_etf", return_value=True):
        with pytest.raises(ValueError, match="ETF"):
            service.add_to_watchlist(user_id=USER_ID, ticker=ticker)

    # Confirm it was not stored
    watchlist = service.get_watchlist(USER_ID)
    tickers_in_list = [item["ticker"] for item in watchlist]
    assert ticker not in tickers_in_list, (
        f"ETF ticker {ticker} should not be in watchlist"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
