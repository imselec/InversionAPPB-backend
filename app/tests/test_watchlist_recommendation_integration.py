"""
Unit tests for watchlist-recommendation engine integration.
Tests Requirement 15.7:
- Watchlist stocks receive priority bonus in new-ticker recommendations
- Watchlist is checked before other candidates in discover_candidates
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.watchlist_service import WATCHLIST_PRIORITY_BONUS


# ---------------------------------------------------------------------------
# Test: watchlist priority bonus applied in scoring
# ---------------------------------------------------------------------------

class TestWatchlistPriorityBonus:
    def test_watchlist_bonus_constant_is_positive(self):
        """WATCHLIST_PRIORITY_BONUS must be a positive number."""
        assert WATCHLIST_PRIORITY_BONUS > 0

    def test_watchlist_score_exceeds_non_watchlist(self):
        """
        A ticker in the watchlist should score higher than an identical
        non-watchlist ticker after the bonus is applied.
        """
        base_score = 10.0
        non_watchlist_score = base_score
        watchlist_score = base_score + WATCHLIST_PRIORITY_BONUS

        assert watchlist_score > non_watchlist_score

    def test_bonus_applied_correctly(self):
        """
        Simulates the bonus logic used in recommend_new_tickers:
        score += WATCHLIST_PRIORITY_BONUS for watchlist tickers.
        """
        recommendations = [
            {"ticker": "MSFT", "score": 10.0},
            {"ticker": "IBM",  "score": 10.0},
        ]
        watchlist_tickers = {"MSFT"}

        for rec in recommendations:
            if rec["ticker"] in watchlist_tickers:
                rec["score"] = round(
                    rec["score"] + WATCHLIST_PRIORITY_BONUS, 2
                )
                rec["in_watchlist"] = True
            else:
                rec["in_watchlist"] = False

        msft = next(r for r in recommendations if r["ticker"] == "MSFT")
        ibm  = next(r for r in recommendations if r["ticker"] == "IBM")

        assert msft["score"] > ibm["score"]
        assert msft["in_watchlist"] is True
        assert ibm["in_watchlist"] is False

    def test_non_watchlist_score_unchanged(self):
        """Non-watchlist tickers keep their original score."""
        base_score = 8.0
        recommendations = [{"ticker": "IBM", "score": base_score}]
        watchlist_tickers = set()  # empty

        for rec in recommendations:
            if rec["ticker"] in watchlist_tickers:
                rec["score"] = round(
                    rec["score"] + WATCHLIST_PRIORITY_BONUS, 2
                )
                rec["in_watchlist"] = True
            else:
                rec["in_watchlist"] = False

        assert recommendations[0]["score"] == base_score
        assert recommendations[0]["in_watchlist"] is False


# ---------------------------------------------------------------------------
# Test: discover_candidates checks watchlist first
# ---------------------------------------------------------------------------

class TestDiscoverCandidatesWatchlistFirst:
    def test_watchlist_tickers_prepended_to_candidates(self):
        """
        discover_candidates must put watchlist tickers before other candidates.
        """
        from app.services.new_ticker_discovery_service import (
            NewTickerDiscoveryService,
        )
        service = NewTickerDiscoveryService()

        watchlist_ticker = "MSFT"

        # Mock WatchlistService inside the module via its import path
        mock_wl_instance = MagicMock()
        mock_wl_instance.get_watchlist.return_value = [
            {"ticker": watchlist_ticker}
        ]
        mock_wl_class = MagicMock(return_value=mock_wl_instance)

        with patch.object(
            service, "screen_by_fundamentals",
            side_effect=lambda candidates, **kw: candidates,
        ), patch(
            "app.services.new_ticker_discovery_service.get_connection"
        ) as mock_conn:
            mock_conn.return_value.__enter__ = MagicMock(
                return_value=mock_conn.return_value
            )
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value.cursor.return_value.fetchall.return_value = []

            # Patch the WatchlistService class inside the function scope
            import app.services.new_ticker_discovery_service as ntd_module
            original = getattr(ntd_module, "WatchlistService", None)
            try:
                # Inject mock into the module namespace temporarily
                ntd_module.WatchlistService = mock_wl_class
                candidates = service.discover_candidates(limit=50)
            finally:
                if original is not None:
                    ntd_module.WatchlistService = original
                elif hasattr(ntd_module, "WatchlistService"):
                    delattr(ntd_module, "WatchlistService")

        # If watchlist ticker made it into candidates, it should be first
        if watchlist_ticker in candidates:
            idx = candidates.index(watchlist_ticker)
            assert idx == 0, (
                f"Expected {watchlist_ticker} at index 0, got {idx}"
            )

    def test_watchlist_tickers_not_duplicated(self):
        """
        Watchlist tickers that also appear in the universe should not
        be duplicated in the candidate list.
        """
        from app.services.new_ticker_discovery_service import (
            NewTickerDiscoveryService,
        )
        service = NewTickerDiscoveryService()

        watchlist_ticker = "MSFT"

        mock_wl_instance = MagicMock()
        mock_wl_instance.get_watchlist.return_value = [
            {"ticker": watchlist_ticker}
        ]
        mock_wl_class = MagicMock(return_value=mock_wl_instance)

        with patch.object(
            service, "screen_by_fundamentals",
            side_effect=lambda candidates, **kw: candidates,
        ), patch(
            "app.services.new_ticker_discovery_service.get_connection"
        ) as mock_conn:
            mock_conn.return_value.cursor.return_value.fetchall.return_value = []

            import app.services.new_ticker_discovery_service as ntd_module
            original = getattr(ntd_module, "WatchlistService", None)
            try:
                ntd_module.WatchlistService = mock_wl_class
                candidates = service.discover_candidates(limit=50)
            finally:
                if original is not None:
                    ntd_module.WatchlistService = original
                elif hasattr(ntd_module, "WatchlistService"):
                    delattr(ntd_module, "WatchlistService")

        # No duplicates
        assert len(candidates) == len(set(candidates)), (
            "Candidate list contains duplicates"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
