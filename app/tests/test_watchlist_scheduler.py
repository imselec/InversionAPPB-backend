"""
Unit tests for the watchlist metrics update scheduled job.
Tests Requirements 15.3, 15.4
"""
import pytest
from unittest.mock import patch, MagicMock
import app.scheduler as scheduler_module
from app.scheduler import (
    run_watchlist_update,
    start_scheduler,
    stop_scheduler,
    get_scheduler,
)


@pytest.fixture(autouse=True)
def reset_watchlist_service():
    """Reset cached watchlist service between tests."""
    scheduler_module._watchlist_service = None
    yield
    scheduler_module._watchlist_service = None


# ---------------------------------------------------------------------------
# run_watchlist_update
# ---------------------------------------------------------------------------

class TestRunWatchlistUpdate:
    def test_calls_update_metrics(self):
        """run_watchlist_update calls WatchlistService.update_metrics."""
        mock_service = MagicMock()
        mock_service.update_metrics.return_value = [
            {"ticker": "MSFT"}, {"ticker": "JNJ"}
        ]
        scheduler_module._watchlist_service = mock_service

        run_watchlist_update()

        mock_service.update_metrics.assert_called_once_with(user_id=1)

    def test_handles_service_exception_gracefully(self):
        """run_watchlist_update does not raise on service error."""
        mock_service = MagicMock()
        mock_service.update_metrics.side_effect = RuntimeError("API error")
        scheduler_module._watchlist_service = mock_service

        # Should not raise
        run_watchlist_update()

    def test_creates_watchlist_service_if_none(self):
        """run_watchlist_update creates WatchlistService when not cached."""
        scheduler_module._watchlist_service = None

        with patch(
            "app.scheduler._WatchlistService"
        ) as MockWL:
            mock_instance = MagicMock()
            mock_instance.update_metrics.return_value = []
            MockWL.return_value = mock_instance

            run_watchlist_update()

            MockWL.assert_called_once()
            mock_instance.update_metrics.assert_called_once()

    def test_logs_number_of_items_updated(self):
        """run_watchlist_update logs the count of updated items."""
        mock_service = MagicMock()
        mock_service.update_metrics.return_value = [
            {"ticker": "MSFT"}, {"ticker": "PG"}, {"ticker": "JNJ"}
        ]
        scheduler_module._watchlist_service = mock_service

        with patch("app.scheduler.logger") as mock_logger:
            run_watchlist_update()

        mock_logger.info.assert_called_once()
        log_msg = mock_logger.info.call_args[0]
        assert 3 in log_msg or "3" in str(log_msg)


# ---------------------------------------------------------------------------
# Scheduler job registration
# ---------------------------------------------------------------------------

class TestWatchlistJobRegistration:
    def setup_method(self):
        stop_scheduler()

    def teardown_method(self):
        stop_scheduler()

    def test_scheduler_has_watchlist_update_job(self):
        """start_scheduler registers the watchlist_update job."""
        sched = start_scheduler()
        job_ids = [job.id for job in sched.get_jobs()]
        assert "watchlist_update" in job_ids

    def test_watchlist_job_interval_set(self):
        """watchlist_update job has a positive interval."""
        sched = start_scheduler()
        job = sched.get_job("watchlist_update")
        assert job is not None
        # Trigger should be an IntervalTrigger with interval > 0
        interval_secs = job.trigger.interval.total_seconds()
        assert interval_secs > 0


# ---------------------------------------------------------------------------
# Error handling when market data unavailable
# ---------------------------------------------------------------------------

class TestWatchlistUpdateErrorHandling:
    def test_market_data_unavailable_does_not_crash(self):
        """
        If market data is unavailable, run_watchlist_update handles
        the error gracefully and does not raise.
        """
        mock_service = MagicMock()
        mock_service.update_metrics.side_effect = ConnectionError(
            "Market data API unavailable"
        )
        scheduler_module._watchlist_service = mock_service

        # Should complete without raising
        run_watchlist_update()

    def test_empty_watchlist_returns_zero_items(self):
        """run_watchlist_update handles empty watchlist gracefully."""
        mock_service = MagicMock()
        mock_service.update_metrics.return_value = []
        scheduler_module._watchlist_service = mock_service

        with patch("app.scheduler.logger") as mock_logger:
            run_watchlist_update()

        mock_logger.info.assert_called_once()
        log_msg = mock_logger.info.call_args[0]
        assert 0 in log_msg or "0" in str(log_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
