"""
Unit tests for watchlist database operations.
Tests Requirements 15.1, 15.2
"""
import pytest
import sqlite3
from app.database import get_connection, init_database


@pytest.fixture(autouse=True)
def clean_watchlist():
    """Remove watchlist rows before each test."""
    init_database()
    conn = get_connection()
    conn.execute("DELETE FROM watchlist")
    conn.commit()
    conn.close()
    yield
    conn = get_connection()
    conn.execute("DELETE FROM watchlist")
    conn.commit()
    conn.close()


class TestWatchlistInsertion:
    def test_insert_watchlist_item(self):
        """Can insert a ticker into the watchlist."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
            (1, "MSFT"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM watchlist WHERE ticker = 'MSFT' AND user_id = 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["ticker"] == "MSFT"
        assert row["user_id"] == 1

    def test_insert_with_notes_and_target_price(self):
        """Can insert a watchlist item with optional notes and target_price."""
        conn = get_connection()
        conn.execute(
            """INSERT INTO watchlist (user_id, ticker, notes, target_price)
               VALUES (?, ?, ?, ?)""",
            (1, "AAPL", "Waiting for dip", 150.0),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM watchlist WHERE ticker = 'AAPL'"
        ).fetchone()
        conn.close()
        assert row["notes"] == "Waiting for dip"
        assert row["target_price"] == 150.0

    def test_added_at_is_set_automatically(self):
        """added_at timestamp is populated on insert."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
            (1, "GOOG"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT added_at FROM watchlist WHERE ticker = 'GOOG'"
        ).fetchone()
        conn.close()
        assert row["added_at"] is not None


class TestDuplicatePrevention:
    def test_duplicate_ticker_raises_integrity_error(self):
        """Inserting the same (user_id, ticker) twice raises IntegrityError."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
            (1, "MSFT"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
                (1, "MSFT"),
            )
            conn.commit()
        conn.close()

    def test_same_ticker_different_users_allowed(self):
        """Same ticker can be in watchlist for different users."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)", (1, "MSFT")
        )
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)", (2, "MSFT")
        )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) as c FROM watchlist WHERE ticker = 'MSFT'"
        ).fetchone()["c"]
        conn.close()
        assert count == 2


class TestWatchlistDeletion:
    def test_delete_watchlist_item(self):
        """Can delete a ticker from the watchlist."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
            (1, "TSLA"),
        )
        conn.commit()
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (1, "TSLA"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM watchlist WHERE ticker = 'TSLA' AND user_id = 1"
        ).fetchone()
        conn.close()
        assert row is None

    def test_delete_nonexistent_item_is_noop(self):
        """Deleting a ticker not in watchlist does not raise."""
        conn = get_connection()
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (1, "NONEXISTENT"),
        )
        conn.commit()
        conn.close()

    def test_delete_only_affects_target_user(self):
        """Deleting for user 1 does not remove user 2's entry."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)", (1, "AMZN")
        )
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)", (2, "AMZN")
        )
        conn.commit()
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = 1 AND ticker = 'AMZN'"
        )
        conn.commit()
        remaining = conn.execute(
            "SELECT COUNT(*) as c FROM watchlist WHERE ticker = 'AMZN'"
        ).fetchone()["c"]
        conn.close()
        assert remaining == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
