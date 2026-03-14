"""
Unit tests for WatchlistService.
Tests Requirements 15.5, 15.7, 15.10
"""
import pytest
from unittest.mock import patch, MagicMock
from app.database import get_connection, init_database
from app.services.watchlist_service import WatchlistService, WATCHLIST_PRIORITY_BONUS

USER_ID = 94


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


# ---------------------------------------------------------------------------
# ETF rejection (req 15.10)
# ---------------------------------------------------------------------------

class TestETFRejection:
    def test_etf_ticker_raises_value_error(self):
        """add_to_watchlist raises ValueError for ETF tickers."""
        service = WatchlistService()
        with patch.object(service, "_is_etf", return_value=True):
            with pytest.raises(ValueError, match="ETF"):
                service.add_to_watchlist(user_id=USER_ID, ticker="SPY")

    def test_etf_not_stored_in_db(self):
        """ETF ticker is not persisted after rejection."""
        service = WatchlistService()
        with patch.object(service, "_is_etf", return_value=True):
            try:
                service.add_to_watchlist(user_id=USER_ID, ticker="QQQ")
            except ValueError:
                pass
        watchlist = service.get_watchlist(USER_ID)
        assert all(item["ticker"] != "QQQ" for item in watchlist)

    def test_non_etf_ticker_is_accepted(self):
        """Non-ETF ticker is stored successfully."""
        service = WatchlistService()
        with patch.object(service, "_is_etf", return_value=False):
            result = service.add_to_watchlist(user_id=USER_ID, ticker="MSFT")
        assert result["ticker"] == "MSFT"


# ---------------------------------------------------------------------------
# Duplicate prevention (req 15.2)
# ---------------------------------------------------------------------------

class TestDuplicatePrevention:
    def test_duplicate_ticker_raises_value_error(self):
        """Adding the same ticker twice raises ValueError."""
        service = WatchlistService()
        with patch.object(service, "_is_etf", return_value=False):
            service.add_to_watchlist(user_id=USER_ID, ticker="AAPL")
            with pytest.raises(ValueError):
                service.add_to_watchlist(user_id=USER_ID, ticker="AAPL")

    def test_watchlist_has_no_duplicates(self):
        """get_watchlist returns unique tickers."""
        service = WatchlistService()
        with patch.object(service, "_is_etf", return_value=False):
            service.add_to_watchlist(user_id=USER_ID, ticker="GOOG")
            try:
                service.add_to_watchlist(user_id=USER_ID, ticker="GOOG")
            except ValueError:
                pass
        watchlist = service.get_watchlist(USER_ID)
        tickers = [item["ticker"] for item in watchlist]
        assert len(tickers) == len(set(tickers))


# ---------------------------------------------------------------------------
# Buy criteria evaluation (req 15.5)
# ---------------------------------------------------------------------------

class TestBuyCriteriaEvaluation:
    def test_ticker_meeting_all_criteria(self):
        """evaluate_buy_criteria returns meets_criteria=True when all pass."""
        service = WatchlistService()
        with patch.object(
            service.dividend_service,
            "get_dividends",
            return_value={"MSFT": {"yield": 0.03, "payout": 0.4}},
        ), patch.object(
            service.valuation_service,
            "get_valuation",
            return_value={"MSFT": 20.0},
        ), patch.object(
            service, "_get_stock_info",
            return_value=(500_000_000_000, "Technology", "Software"),
        ):
            result = service.evaluate_buy_criteria("MSFT")

        assert result["meets_criteria"] is True
        assert result["conditions"]["dividend_yield_ok"] is True
        assert result["conditions"]["pe_ratio_ok"] is True
        assert result["conditions"]["market_cap_ok"] is True

    def test_ticker_failing_dividend_yield(self):
        """evaluate_buy_criteria returns meets_criteria=False for low yield."""
        service = WatchlistService()
        with patch.object(
            service.dividend_service,
            "get_dividends",
            return_value={"LOW": {"yield": 0.005, "payout": 0.3}},
        ), patch.object(
            service.valuation_service,
            "get_valuation",
            return_value={"LOW": 15.0},
        ), patch.object(
            service, "_get_stock_info",
            return_value=(50_000_000_000, "Retail", "Home Improvement"),
        ):
            result = service.evaluate_buy_criteria("LOW")

        assert result["meets_criteria"] is False
        assert result["conditions"]["dividend_yield_ok"] is False

    def test_ticker_failing_pe_ratio(self):
        """evaluate_buy_criteria returns meets_criteria=False for high P/E."""
        service = WatchlistService()
        with patch.object(
            service.dividend_service,
            "get_dividends",
            return_value={"AMZN": {"yield": 0.025, "payout": 0.4}},
        ), patch.object(
            service.valuation_service,
            "get_valuation",
            return_value={"AMZN": 80.0},
        ), patch.object(
            service, "_get_stock_info",
            return_value=(1_500_000_000_000, "Consumer", "E-Commerce"),
        ):
            result = service.evaluate_buy_criteria("AMZN")

        assert result["meets_criteria"] is False
        assert result["conditions"]["pe_ratio_ok"] is False


# ---------------------------------------------------------------------------
# Prioritization scoring (req 15.7)
# ---------------------------------------------------------------------------

class TestPrioritizationScoring:
    def test_prioritized_list_sorted_descending(self):
        """get_prioritized_watchlist returns items sorted by score desc."""
        service = WatchlistService()
        tickers = ["AAPL", "MSFT", "JNJ"]

        conn = get_connection()
        conn.execute("DELETE FROM watchlist WHERE user_id = ?", (USER_ID,))
        for t in tickers:
            conn.execute(
                "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
                (USER_ID, t),
            )
        conn.commit()
        conn.close()

        mock_prices = {"AAPL": 150.0, "MSFT": 300.0, "JNJ": 165.0}
        mock_dividends = {
            "AAPL": {"yield": 0.015, "payout": 0.25},
            "MSFT": {"yield": 0.008, "payout": 0.28},
            "JNJ": {"yield": 0.028, "payout": 0.50},
        }
        mock_valuations = {"AAPL": 28.0, "MSFT": 32.0, "JNJ": 16.0}

        with patch(
            "app.services.watchlist_service.get_prices",
            return_value=mock_prices,
        ), patch.object(
            service.dividend_service, "get_dividends",
            return_value=mock_dividends,
        ), patch.object(
            service.valuation_service, "get_valuation",
            return_value=mock_valuations,
        ), patch.object(
            service, "_get_stock_info",
            return_value=(100_000_000_000, "Technology", "Software"),
        ):
            prioritized = service.get_prioritized_watchlist(USER_ID)

        scores = [item["score"] for item in prioritized]
        assert scores == sorted(scores, reverse=True)

    def test_all_scores_include_priority_bonus(self):
        """Every score in prioritized list includes WATCHLIST_PRIORITY_BONUS."""
        service = WatchlistService()
        tickers = ["PG", "KO"]

        conn = get_connection()
        conn.execute("DELETE FROM watchlist WHERE user_id = ?", (USER_ID,))
        for t in tickers:
            conn.execute(
                "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)",
                (USER_ID, t),
            )
        conn.commit()
        conn.close()

        mock_prices = {"PG": 145.0, "KO": 60.0}
        mock_dividends = {
            "PG": {"yield": 0.025, "payout": 0.6},
            "KO": {"yield": 0.03, "payout": 0.7},
        }
        mock_valuations = {"PG": 18.0, "KO": 22.0}

        with patch(
            "app.services.watchlist_service.get_prices",
            return_value=mock_prices,
        ), patch.object(
            service.dividend_service, "get_dividends",
            return_value=mock_dividends,
        ), patch.object(
            service.valuation_service, "get_valuation",
            return_value=mock_valuations,
        ), patch.object(
            service, "_get_stock_info",
            return_value=(200_000_000_000, "Consumer Staples", "Beverages"),
        ):
            prioritized = service.get_prioritized_watchlist(USER_ID)

        for item in prioritized:
            assert item["score"] >= WATCHLIST_PRIORITY_BONUS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
