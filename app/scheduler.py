"""
Scheduled jobs for InversionAPP alert evaluation.

Requirements 14.1–14.5:
- Every 5 minutes during market hours (9:30–16:00 ET, Mon–Fri)
- Every 60 minutes outside market hours
"""
import logging
from datetime import datetime, time
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .services.alert_service import AlertService
from .services.watchlist_service import WatchlistService as _WatchlistService

logger = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

_scheduler: "BackgroundScheduler | None" = None
_alert_service: AlertService | None = None
_watchlist_service: "_WatchlistService | None" = None


def _is_market_hours() -> bool:
    """Return True if current ET time is within market hours Mon-Fri."""
    now_et = datetime.now(ET)
    if now_et.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    current_time = now_et.time()
    return MARKET_OPEN <= current_time < MARKET_CLOSE


def run_alert_evaluation() -> None:
    """
    Evaluate all active alerts and log results.
    Called by the scheduler on each tick.
    """
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()

    try:
        result = _alert_service.evaluate_alerts()
        evaluated = result.get("evaluated", 0)
        triggered = result.get("triggered", 0)
        logger.info(
            "Alert evaluation complete: %d evaluated, %d triggered",
            evaluated,
            triggered,
        )
    except Exception:
        logger.exception("Error during scheduled alert evaluation")


def run_watchlist_update() -> None:
    """
    Refresh metrics for all watchlist items and log results.
    Runs every 15 minutes during market hours (req 15.3, 15.4).
    """
    global _watchlist_service
    if _watchlist_service is None:
        _watchlist_service = _WatchlistService()

    try:
        updated = _watchlist_service.update_metrics(user_id=1)
        logger.info(
            "Watchlist metrics updated: %d items refreshed",
            len(updated),
        )
    except Exception:
        logger.exception("Error during scheduled watchlist update")


def _reschedule_job(scheduler: BackgroundScheduler) -> None:
    """
    Adjust the evaluation job interval based on whether the market is open.
    Called once per minute by a lightweight check job.
    """
    in_market = _is_market_hours()
    interval_minutes = 5 if in_market else 60

    if scheduler.get_job("alert_evaluation"):
        scheduler.reschedule_job(
            "alert_evaluation",
            trigger=IntervalTrigger(minutes=interval_minutes),
        )
        logger.debug(
            "Rescheduled alert_evaluation to every %d min (market_hours=%s)",
            interval_minutes,
            in_market,
        )


def start_scheduler() -> BackgroundScheduler:
    """
    Start the background scheduler.

    Creates two jobs:
    1. alert_evaluation - runs every 5 min (market hours) or 60 min (off hours)
    2. market_hours_check - runs every minute to adjust the interval above

    Returns the running scheduler instance.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=ET)

    # Initial interval based on current time
    initial_interval = 5 if _is_market_hours() else 60

    _scheduler.add_job(
        run_alert_evaluation,
        trigger=IntervalTrigger(minutes=initial_interval),
        id="alert_evaluation",
        name="Alert Evaluation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_job(
        lambda: _reschedule_job(_scheduler),
        trigger=IntervalTrigger(minutes=1),
        id="market_hours_check",
        name="Market Hours Check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Watchlist metrics refresh: every 15 min during market hours
    watchlist_interval = 15 if _is_market_hours() else 60
    _scheduler.add_job(
        run_watchlist_update,
        trigger=IntervalTrigger(minutes=watchlist_interval),
        id="watchlist_update",
        name="Watchlist Metrics Update",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started. Alert evaluation every %d min initially.",
        initial_interval,
    )
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
    _scheduler = None


def get_scheduler() -> "BackgroundScheduler | None":
    """Return the current scheduler instance (or None if not started)."""
    return _scheduler
