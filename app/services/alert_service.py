"""
Alert Service for InversionAPP.

Manages alert rules, evaluates conditions, triggers notifications, and records
notification history.

Implements requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.7, 14.8, 14.9, 14.10:
- Price alerts when stock reaches target price
- Dividend alerts when payment is within 7 days
- Rebalancing alerts when allocation deviates > 5% from target
- Monthly investment reminders within 3 days of investment date
- News alerts for significant events
- Throttling: 24-hour minimum between duplicate notifications
- Full CRUD for alert configuration
- Notification history recording
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import warnings

try:
    from yahooquery import Ticker
except ImportError:  # pragma: no cover
    Ticker = None  # type: ignore

from ..database import get_connection
from .market_data_service import get_prices
from .watchlist_service import WatchlistService as _WatchlistService

warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# Throttle window: skip re-triggering within 24 hours
THROTTLE_HOURS = 24

# Rebalancing deviation threshold (5% per requirement 14.3)
REBALANCING_DEVIATION_THRESHOLD = 5.0

# Dividend look-ahead window in days (requirement 14.2)
DIVIDEND_LOOKAHEAD_DAYS = 7

# Monthly investment reminder window in days (requirement 14.4)
MONTHLY_INVESTMENT_LOOKAHEAD_DAYS = 3


class AlertService:
    """
    Service for managing alert rules and evaluating alert conditions.
    Integrates with MarketDataService, DividendService, and RebalancingService.
    """

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def create_alert(
        self,
        user_id: int,
        alert_type: str,
        ticker: Optional[str] = None,
        target_price: Optional[float] = None,
        enabled: bool = True,
    ) -> Dict:
        """
        Create a new alert rule.

        Args:
            user_id: The user who owns this alert.
            alert_type: One of 'price', 'dividend', 'rebalancing',
                        'monthly_investment', 'news'.
            ticker: Stock ticker (required for price/dividend/news alerts).
            target_price: Target price for price alerts.
            enabled: Whether the alert is active.

        Returns:
            Dict with the created alert data.
        """
        now = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts
                (user_id, alert_type, ticker, target_price, enabled,
                 last_triggered, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (user_id, alert_type, ticker, target_price, int(enabled), now, now),
        )
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": alert_id,
            "user_id": user_id,
            "alert_type": alert_type,
            "ticker": ticker,
            "target_price": target_price,
            "enabled": enabled,
            "last_triggered": None,
            "created_at": now,
            "updated_at": now,
        }

    def update_alert(self, alert_id: int, params: Dict) -> Optional[Dict]:
        """
        Update an existing alert configuration.

        Args:
            alert_id: ID of the alert to update.
            params: Dict of fields to update (alert_type, ticker,
                    target_price, enabled).

        Returns:
            Updated alert dict, or None if not found.
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        allowed = {"alert_type", "ticker", "target_price", "enabled"}
        updates = {k: v for k, v in params.items() if k in allowed}
        if not updates:
            conn.close()
            return dict(row)

        now = datetime.now().isoformat()
        updates["updated_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [alert_id]
        cursor.execute(f"UPDATE alerts SET {set_clause} WHERE id = ?", values)
        conn.commit()

        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        updated = cursor.fetchone()
        conn.close()
        return self._row_to_alert(updated)

    def delete_alert(self, alert_id: int) -> bool:
        """
        Delete an alert rule.

        Returns:
            True if deleted, False if not found.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_user_alerts(self, user_id: int) -> List[Dict]:
        """
        Return all alert rules for a user.

        Args:
            user_id: The user whose alerts to retrieve.

        Returns:
            List of alert dicts ordered by created_at descending.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_alert(r) for r in rows]

    def get_notification_history(
        self, user_id: int, limit: int = 50
    ) -> List[Dict]:
        """
        Return recent notification history for a user.

        Args:
            user_id: The user whose history to retrieve.
            limit: Maximum number of records to return.

        Returns:
            List of notification history dicts ordered by sent_at descending.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM notification_history
            WHERE user_id = ?
            ORDER BY sent_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_notification(r) for r in rows]

    # ------------------------------------------------------------------
    # Alert evaluation
    # ------------------------------------------------------------------

    def evaluate_alerts(self) -> Dict:
        """
        Evaluate all active alerts and trigger notifications for met conditions.

        Checks:
        - Price alerts: current price vs target price
        - Dividend alerts: upcoming dividend within 7 days
        - Rebalancing alerts: allocation deviation > 5%
        - Monthly investment alerts: investment date within 3 days
        - News alerts: (placeholder — requires external news feed)

        Returns:
            Summary dict with counts of evaluated and triggered alerts.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alerts WHERE enabled = 1",
        )
        active_alerts = cursor.fetchall()
        conn.close()

        evaluated = 0
        triggered = 0

        # Batch-fetch prices for all price/dividend/news alerts
        price_tickers = list({
            r['ticker']
            for r in active_alerts
            if r['alert_type'] in ('price', 'dividend', 'news') and r['ticker']
        })
        current_prices: Dict[str, float] = {}
        if price_tickers:
            try:
                current_prices = get_prices(price_tickers)
            except Exception as e:
                logger.warning("Failed to fetch prices for alert evaluation: %s", e)

        for alert in active_alerts:
            evaluated += 1
            alert_id = alert['id']
            alert_type = alert['alert_type']
            ticker = alert['ticker']
            user_id = alert['user_id']

            # Throttle check
            if self._is_throttled(alert):
                continue

            message: Optional[str] = None

            try:
                if alert_type == 'price':
                    message = self.check_price_alert(
                        ticker=ticker,
                        target_price=alert['target_price'],
                        current_price=current_prices.get(ticker, 0),
                    )

                elif alert_type == 'dividend':
                    message = self.check_dividend_alert(ticker=ticker)

                elif alert_type == 'rebalancing':
                    message = self.check_rebalancing_alert()

                elif alert_type == 'monthly_investment':
                    message = self.check_monthly_investment_alert()

                elif alert_type == 'news':
                    # News alerts require an external feed; placeholder only
                    message = None

            except Exception as e:
                logger.warning(
                    "Error evaluating alert %s (type=%s): %s", alert_id, alert_type, e
                )
                continue

            if message:
                self.trigger_notification(
                    alert_id=alert_id,
                    user_id=user_id,
                    alert_type=alert_type,
                    ticker=ticker,
                    message=message,
                )
                triggered += 1

        # Check watchlist stocks against buy criteria (req 15.5)
        try:
            wl_hits = self.check_watchlist_buy_criteria(user_id=1)
            for hit in wl_hits:
                self.trigger_notification(
                    alert_id=0,
                    user_id=1,
                    alert_type="watchlist_buy",
                    ticker=hit["ticker"],
                    message=hit["message"],
                )
                triggered += 1
        except Exception as e:
            logger.warning("Watchlist evaluation error: %s", e)

        return {"evaluated": evaluated, "triggered": triggered}

    def check_watchlist_buy_criteria(
        self, user_id: int = 1
    ) -> List[Dict]:
        """
        Check all watchlist stocks against buy criteria and return
        those that meet conditions (req 15.5).

        Returns a list of dicts with ticker and notification message
        for each watchlist stock that meets buy criteria.
        """
        results = []
        try:
            wl_service = _WatchlistService()
            watchlist = wl_service.get_watchlist(user_id)
            for item in watchlist:
                ticker = item["ticker"]
                try:
                    criteria = wl_service.evaluate_buy_criteria(ticker)
                    if criteria["meets_criteria"]:
                        msg = (
                            f"Watchlist alert: {ticker} now meets your "
                            f"buy criteria (yield="
                            f"{criteria['dividend_yield']*100:.1f}%, "
                            f"P/E={criteria['pe_ratio']:.1f})."
                        )
                        results.append({"ticker": ticker, "message": msg})
                except Exception as e:
                    logger.debug(
                        "Watchlist criteria check failed for %s: %s",
                        ticker, e,
                    )
        except Exception as e:
            logger.warning("Watchlist buy criteria check failed: %s", e)
        return results

    # ------------------------------------------------------------------
    # Notification triggering
    # ------------------------------------------------------------------

    def trigger_notification(
        self,
        alert_id: int,
        user_id: int,
        alert_type: str,
        ticker: Optional[str],
        message: str,
    ) -> Dict:
        """
        Record a triggered notification in history and update last_triggered.

        Optionally sends a push notification via PushNotificationService when
        that service is available.

        Args:
            alert_id: ID of the alert that triggered.
            user_id: User to notify.
            alert_type: Type of alert.
            ticker: Related ticker (may be None for non-price alerts).
            message: Human-readable notification message.

        Returns:
            Dict with the created notification_history record.
        """
        now = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()

        # Record in notification_history
        cursor.execute(
            """
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, ticker, message,
                 sent_at, delivered, read)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (user_id, alert_id, alert_type, ticker, message, now),
        )
        notification_id = cursor.lastrowid

        # Update last_triggered on the alert
        cursor.execute(
            "UPDATE alerts SET last_triggered = ?, updated_at = ? WHERE id = ?",
            (now, now, alert_id),
        )

        conn.commit()
        conn.close()

        notification = {
            "id": notification_id,
            "user_id": user_id,
            "alert_id": alert_id,
            "alert_type": alert_type,
            "ticker": ticker,
            "message": message,
            "sent_at": now,
            "delivered": False,
            "read": False,
        }

        # Attempt push notification delivery (best-effort)
        self._send_push_notification(user_id=user_id, message=message, alert_type=alert_type)

        return notification

    # ------------------------------------------------------------------
    # Individual alert condition checks
    # ------------------------------------------------------------------

    def check_price_alert(
        self,
        ticker: str,
        target_price: Optional[float],
        current_price: float,
    ) -> Optional[str]:
        """
        Evaluate a price alert condition.

        Triggers when current_price >= target_price (price reached or exceeded).

        Args:
            ticker: Stock ticker symbol.
            target_price: User-defined target price.
            current_price: Current market price.

        Returns:
            Notification message string if triggered, else None.
        """
        if not ticker or not target_price or target_price <= 0:
            return None
        if current_price <= 0:
            return None
        if current_price >= target_price:
            return (
                f"Price alert: {ticker} has reached ${current_price:.2f}, "
                f"meeting your target of ${target_price:.2f}."
            )
        return None

    def check_dividend_alert(self, ticker: str) -> Optional[str]:
        """
        Check if a dividend payment for the ticker is scheduled within 7 days.

        Uses yahooquery to fetch the next ex-dividend date.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Notification message string if triggered, else None.
        """
        if not ticker:
            return None
        try:
            data = Ticker(ticker)
            summary = data.summary_detail.get(ticker, {})
            if not isinstance(summary, dict):
                return None

            ex_div_date = summary.get('exDividendDate')
            if not ex_div_date:
                return None

            # exDividendDate may be a timestamp (int/float) or datetime
            if isinstance(ex_div_date, (int, float)):
                ex_div_dt = datetime.fromtimestamp(ex_div_date)
            elif isinstance(ex_div_date, datetime):
                ex_div_dt = ex_div_date
            else:
                ex_div_dt = datetime.fromisoformat(str(ex_div_date))

            days_until = (ex_div_dt.date() - datetime.now().date()).days
            if 0 <= days_until <= DIVIDEND_LOOKAHEAD_DAYS:
                return (
                    f"Dividend alert: {ticker} has an ex-dividend date in "
                    f"{days_until} day(s) on {ex_div_dt.strftime('%Y-%m-%d')}."
                )
        except Exception as e:
            logger.debug("Dividend alert check failed for %s: %s", ticker, e)
        return None

    def check_rebalancing_alert(self, portfolio: Optional[Dict] = None) -> Optional[str]:
        """
        Check if any portfolio position deviates more than 5% from target allocation.

        Args:
            portfolio: Optional pre-computed balance status dict. If None,
                       fetches from RebalancingService.

        Returns:
            Notification message string if triggered, else None.
        """
        try:
            if portfolio is None:
                from .rebalancing_service import RebalancingService
                portfolio = RebalancingService().check_balance_status()

            allocations = portfolio.get('allocations', [])
            deviating = [
                a for a in allocations
                if abs(a.get('deviation', 0)) > REBALANCING_DEVIATION_THRESHOLD
            ]
            if deviating:
                tickers_str = ', '.join(a['ticker'] for a in deviating[:5])
                return (
                    f"Rebalancing alert: {len(deviating)} position(s) deviate more than "
                    f"{REBALANCING_DEVIATION_THRESHOLD}% from target allocation "
                    f"({tickers_str})."
                )
        except Exception as e:
            logger.debug("Rebalancing alert check failed: %s", e)
        return None

    def check_monthly_investment_alert(
        self, user_settings: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Check if the monthly investment date is within 3 days.

        Reads 'monthly_investment_day' from user_settings (1-28).
        Defaults to day 1 if not configured.

        Args:
            user_settings: Optional dict with 'monthly_investment_day' key.

        Returns:
            Notification message string if triggered, else None.
        """
        try:
            investment_day = 1  # default

            if user_settings is not None:
                investment_day = int(user_settings.get('monthly_investment_day', 1))
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT setting_value FROM user_settings WHERE setting_key = 'monthly_investment_day'"
                )
                row = cursor.fetchone()
                conn.close()
                if row:
                    investment_day = int(row['setting_value'])

            today = datetime.now().date()
            # Compute next occurrence of investment_day
            try:
                next_date = today.replace(day=investment_day)
            except ValueError:
                # Day doesn't exist in current month (e.g. day=31 in April)
                next_date = today.replace(day=28)

            if next_date < today:
                # Already passed this month — look at next month
                if today.month == 12:
                    next_date = next_date.replace(year=today.year + 1, month=1)
                else:
                    next_date = next_date.replace(month=today.month + 1)

            days_until = (next_date - today).days
            if 0 <= days_until <= MONTHLY_INVESTMENT_LOOKAHEAD_DAYS:
                return (
                    f"Monthly investment reminder: your scheduled investment date is "
                    f"in {days_until} day(s) on {next_date.strftime('%Y-%m-%d')}. "
                    f"Consider reviewing your recommendations."
                )
        except Exception as e:
            logger.debug("Monthly investment alert check failed: %s", e)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_throttled(self, alert) -> bool:
        """
        Return True if the alert was triggered within the last 24 hours.

        Prevents duplicate notifications for the same alert condition.
        """
        last_triggered = alert['last_triggered']
        if not last_triggered:
            return False
        try:
            if isinstance(last_triggered, str):
                last_dt = datetime.fromisoformat(last_triggered)
            else:
                last_dt = last_triggered
            return (datetime.now() - last_dt) < timedelta(hours=THROTTLE_HOURS)
        except Exception:
            return False

    def _send_push_notification(
        self, user_id: int, message: str, alert_type: str
    ) -> None:
        """
        Best-effort push notification delivery via PushNotificationService.
        Silently ignores errors so alert recording is never blocked.
        """
        try:
            from .push_notification_service import PushNotificationService
            pns = PushNotificationService()
            pns.send_notification(
                user_id=user_id,
                title=f"InversionAPP Alert ({alert_type})",
                body=message,
                data={"alert_type": alert_type},
            )
        except Exception:
            # PushNotificationService may not be available yet
            pass

    @staticmethod
    def _row_to_alert(row) -> Dict:
        """Convert a database row to an alert dict."""
        return {
            "id": row['id'],
            "user_id": row['user_id'],
            "alert_type": row['alert_type'],
            "ticker": row['ticker'],
            "target_price": row['target_price'],
            "enabled": bool(row['enabled']),
            "last_triggered": row['last_triggered'],
            "created_at": row['created_at'],
            "updated_at": row['updated_at'],
        }

    @staticmethod
    def _row_to_notification(row) -> Dict:
        """Convert a database row to a notification history dict."""
        return {
            "id": row['id'],
            "user_id": row['user_id'],
            "alert_id": row['alert_id'],
            "alert_type": row['alert_type'],
            "ticker": row['ticker'],
            "message": row['message'],
            "sent_at": row['sent_at'],
            "delivered": bool(row['delivered']),
            "read": bool(row['read']),
        }
