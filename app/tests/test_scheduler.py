"""
Unit tests for the alert evaluation scheduled job.
Tests Requirements 14.1–14.5
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytz

import app.scheduler as scheduler_module
from app.scheduler import (
    _is_market_hours,
    run_alert_evaluation,
    start_scheduler,
    stop_scheduler,
    get_scheduler,
)

ET = pytz.timezone("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_et_datetime(weekday: int, hour: int, minute: int = 0) -> datetime:
    """
    Build a timezone-aware ET datetime for a given weekday and time.
    weekday: 0=Monday ... 4=Friday, 5=Saturday, 6=Sunday
    """
    # Find a Monday in 2026 and offset by weekday
    base = datetime(2026, 3, 16, hour, minute, tzinfo=ET)  # Monday
    delta_days = weekday - base.weekday()
    return base.replace(
        day=base.day + delta_days,
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


# ---------------------------------------------------------------------------
# _is_market_hours
# ---------------------------------------------------------------------------

class TestIsMarketHours:
    def test_weekday_during_market_hours(self):
        """Monday 10:00 ET is market hours."""
        dt = _make_et_datetime(weekday=0, hour=10, minute=0)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is True

    def test_weekday_before_market_open(self):
        """Monday 09:00 ET is before market open."""
        dt = _make_et_datetime(weekday=0, hour=9, minute=0)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is False

    def test_weekday_after_market_close(self):
        """Monday 16:30 ET is after market close."""
        dt = _make_et_datetime(weekday=0, hour=16, minute=30)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is False

    def test_weekday_at_market_open(self):
        """Monday 09:30 ET is exactly at open (inclusive)."""
        dt = _make_et_datetime(weekday=0, hour=9, minute=30)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is True

    def test_weekday_at_market_close(self):
        """Monday 16:00 ET is exactly at close (exclusive)."""
        dt = _make_et_datetime(weekday=0, hour=16, minute=0)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is False

    def test_saturday_is_not_market_hours(self):
        """Saturday is never market hours."""
        dt = _make_et_datetime(weekday=5, hour=11, minute=0)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is False

    def test_sunday_is_not_market_hours(self):
        """Sunday is never market hours."""
        dt = _make_et_datetime(weekday=6, hour=11, minute=0)
        with patch("app.scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            assert _is_market_hours() is False


# ---------------------------------------------------------------------------
# run_alert_evaluation
# ---------------------------------------------------------------------------

class TestRunAlertEvaluation:
    def test_calls_evaluate_alerts(self):
        """run_alert_evaluation calls AlertService.evaluate_alerts."""
        mock_service = MagicMock()
        mock_service.evaluate_alerts.return_value = {
            "evaluated": 5, "triggered": 2
        }
        scheduler_module._alert_service = mock_service

        run_alert_evaluation()

        mock_service.evaluate_alerts.assert_called_once()

    def test_handles_service_exception_gracefully(self):
        """run_alert_evaluation does not raise on service error."""
        mock_service = MagicMock()
        mock_service.evaluate_alerts.side_effect = RuntimeError("DB error")
        scheduler_module._alert_service = mock_service

        # Should not raise
        run_alert_evaluation()

    def test_creates_alert_service_if_none(self):
        """run_alert_evaluation creates AlertService when _alert_service is None."""
        scheduler_module._alert_service = None

        with patch(
            "app.scheduler.AlertService"
        ) as MockAlertService:
            mock_instance = MagicMock()
            mock_instance.evaluate_alerts.return_value = {
                "evaluated": 0, "triggered": 0
            }
            MockAlertService.return_value = mock_instance

            run_alert_evaluation()

            MockAlertService.assert_called_once()
            mock_instance.evaluate_alerts.assert_called_once()


# ---------------------------------------------------------------------------
# start_scheduler / stop_scheduler
# ---------------------------------------------------------------------------

class TestSchedulerLifecycle:
    def setup_method(self):
        """Ensure scheduler is stopped before each test."""
        stop_scheduler()

    def teardown_method(self):
        """Clean up after each test."""
        stop_scheduler()

    def test_start_scheduler_returns_running_scheduler(self):
        """start_scheduler returns a running BackgroundScheduler."""
        sched = start_scheduler()
        assert sched is not None
        assert sched.running is True

    def test_start_scheduler_idempotent(self):
        """Calling start_scheduler twice returns the same instance."""
        sched1 = start_scheduler()
        sched2 = start_scheduler()
        assert sched1 is sched2

    def test_stop_scheduler_stops_running_scheduler(self):
        """stop_scheduler stops the scheduler."""
        start_scheduler()
        stop_scheduler()
        assert get_scheduler() is None

    def test_stop_scheduler_noop_when_not_started(self):
        """stop_scheduler does not raise when scheduler is not running."""
        stop_scheduler()  # already stopped in setup
        stop_scheduler()  # second call should be safe

    def test_scheduler_has_alert_evaluation_job(self):
        """Scheduler registers the alert_evaluation job."""
        sched = start_scheduler()
        job_ids = [job.id for job in sched.get_jobs()]
        assert "alert_evaluation" in job_ids

    def test_scheduler_has_market_hours_check_job(self):
        """Scheduler registers the market_hours_check job."""
        sched = start_scheduler()
        job_ids = [job.id for job in sched.get_jobs()]
        assert "market_hours_check" in job_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
