"""
Unit tests for watchlist-alert service integration.
Tests Requirement 15.5:
- Alert notifications are created when watchlist stock meets buy criteria
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.alert_service import AlertService

PATCH_WL = "app.services.alert_service._WatchlistService"


def _mock_wl(watchlist_items, criteria_map):
    """Helper: return a mock WatchlistService instance."""
    instance = MagicMock()
    instance.get_watchlist.return_value = watchlist_items
    instance.evaluate_buy_criteria.side_effect = (
        lambda t: criteria_map.get(t, {"meets_criteria": False,
                                       "dividend_yield": 0, "pe_ratio": 0})
    )
    return instance


class TestWatchlistAlertIntegration:
    def test_check_watchlist_buy_criteria_returns_hits(self):
        """
        check_watchlist_buy_criteria returns tickers that meet buy criteria.
        """
        service = AlertService()
        mock_instance = _mock_wl(
            [{"ticker": "MSFT"}, {"ticker": "IBM"}],
            {
                "MSFT": {"meets_criteria": True,
                         "dividend_yield": 0.008, "pe_ratio": 32.0},
                "IBM":  {"meets_criteria": False,
                         "dividend_yield": 0.05, "pe_ratio": 14.0},
            },
        )
        with patch(PATCH_WL, return_value=mock_instance):
            hits = service.check_watchlist_buy_criteria(user_id=1)

        assert len(hits) == 1
        assert hits[0]["ticker"] == "MSFT"
        assert "buy criteria" in hits[0]["message"].lower()

    def test_check_watchlist_buy_criteria_empty_watchlist(self):
        """
        check_watchlist_buy_criteria returns empty list for empty watchlist.
        """
        service = AlertService()
        mock_instance = _mock_wl([], {})
        with patch(PATCH_WL, return_value=mock_instance):
            hits = service.check_watchlist_buy_criteria(user_id=1)

        assert hits == []

    def test_check_watchlist_buy_criteria_no_hits(self):
        """
        check_watchlist_buy_criteria returns empty list when no ticker
        meets criteria.
        """
        service = AlertService()
        mock_instance = _mock_wl(
            [{"ticker": "AMZN"}],
            {"AMZN": {"meets_criteria": False,
                      "dividend_yield": 0.001, "pe_ratio": 80.0}},
        )
        with patch(PATCH_WL, return_value=mock_instance):
            hits = service.check_watchlist_buy_criteria(user_id=1)

        assert hits == []

    def test_evaluate_alerts_triggers_watchlist_notification(self):
        """
        evaluate_alerts calls check_watchlist_buy_criteria and triggers
        a notification for each watchlist stock that meets buy criteria.
        """
        service = AlertService()

        # No regular alerts
        with patch.object(
            service, "get_user_alerts", return_value=[]
        ), patch(
            "app.services.alert_service.get_connection"
        ) as mock_conn, patch.object(
            service, "check_watchlist_buy_criteria",
            return_value=[
                {"ticker": "MSFT", "message": "MSFT meets buy criteria."}
            ],
        ), patch.object(
            service, "trigger_notification",
            return_value={"id": 1},
        ) as mock_trigger:
            mock_conn.return_value.cursor.return_value.fetchall.return_value = []

            result = service.evaluate_alerts()

        mock_trigger.assert_called_once()
        call_kwargs = mock_trigger.call_args[1]
        assert call_kwargs["ticker"] == "MSFT"
        assert call_kwargs["alert_type"] == "watchlist_buy"
        assert result["triggered"] == 1

    def test_watchlist_criteria_exception_does_not_crash_evaluation(self):
        """
        If check_watchlist_buy_criteria raises, evaluate_alerts still
        returns a valid result.
        """
        service = AlertService()

        with patch.object(
            service, "get_user_alerts", return_value=[]
        ), patch(
            "app.services.alert_service.get_connection"
        ) as mock_conn, patch.object(
            service, "check_watchlist_buy_criteria",
            side_effect=RuntimeError("DB error"),
        ):
            mock_conn.return_value.cursor.return_value.fetchall.return_value = []

            result = service.evaluate_alerts()

        assert "evaluated" in result
        assert "triggered" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
