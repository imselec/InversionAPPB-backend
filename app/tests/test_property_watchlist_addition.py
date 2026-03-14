"""
Property 55: Watchlist Addition
Validates: Requirements 15.1

Property: For any valid (non-ETF) ticker added to the watchlist,
the ticker must appear in the watchlist afterwards.
"""
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from unittest.mock import patch
from app.database import get_connection, init_database
from app.services.watchlist_service import WatchlistService

USER_ID = 99  # isolated test user


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
    ticker=st.from_regex(r"[A-Z]{2,5}", fullmatch=True),
    notes=st.one_of(st.none(), st.text(max_size=50)),
    target_price=st.one_of(st.none(), st.floats(min_value=1.0, max_value=5000.0)),
)
@settings(max_examples=15, deadline=None)
def test_property_watchlist_addition(ticker, notes, target_price):
    """
    Property 55: After adding a ticker, it must appear in get_watchlist().
    """
    service = WatchlistService()

    # Patch _is_etf to always return False (we test ETF exclusion separately)
    with patch.object(service, "_is_etf", return_value=False):
        try:
            service.add_to_watchlist(
                user_id=USER_ID,
                ticker=ticker,
                notes=notes,
                target_price=target_price,
            )
        except ValueError:
            # Duplicate — already added in a previous example; skip
            return

        watchlist = service.get_watchlist(USER_ID)
        tickers_in_list = [item["ticker"] for item in watchlist]
        assert ticker in tickers_in_list, (
            f"Expected {ticker} in watchlist after addition, got {tickers_in_list}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
