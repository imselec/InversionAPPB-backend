"""
Push Notification Service for InversionAPP.

Manages device token registration and delivers push notifications via
Firebase Cloud Messaging (FCM).

Implements requirement 14.6:
- Device token registration/unregistration per platform (ios, android, web)
- FCM integration with exponential backoff retry (3 attempts max)
- Platform-specific payload formatting (iOS APNs vs Android/Web FCM)
- Mark device tokens inactive after 3 consecutive delivery failures
"""
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..database import get_connection

logger = logging.getLogger(__name__)

FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds; delay = BACKOFF_BASE ** attempt


class PushNotificationService:
    """
    Integrates with Firebase Cloud Messaging to deliver push notifications.
    Handles device token lifecycle and retry logic.
    """

    # ------------------------------------------------------------------
    # Device token management
    # ------------------------------------------------------------------

    def register_device(self, user_id: int, device_token: str, platform: str) -> Dict:
        """Register (or re-activate) a device token for push notifications."""
        if platform not in ("ios", "android", "web"):
            raise ValueError(f"Unsupported platform: {platform}")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Upsert: insert or update existing token
            cursor.execute(
                """
                INSERT INTO device_tokens (user_id, device_token, platform, registered_at, last_used, active)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(device_token) DO UPDATE SET
                    user_id = excluded.user_id,
                    platform = excluded.platform,
                    registered_at = excluded.registered_at,
                    last_used = excluded.last_used,
                    active = 1
                """,
                (user_id, device_token, platform, datetime.now(), datetime.now()),
            )
            conn.commit()
            return {"registered": True, "device_token": device_token, "platform": platform}
        finally:
            conn.close()

    def unregister_device(self, device_token: str) -> Dict:
        """Mark a device token as inactive (soft delete)."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE device_tokens SET active = 0 WHERE device_token = ?",
                (device_token,),
            )
            conn.commit()
            return {"unregistered": True, "device_token": device_token}
        finally:
            conn.close()

    def _get_active_tokens(self, user_id: int) -> List[Dict]:
        """Return all active device tokens for a user."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, device_token, platform FROM device_tokens WHERE user_id = ? AND active = 1",
                (user_id,),
            )
            rows = cursor.fetchall()
            return [{"id": row["id"], "device_token": row["device_token"], "platform": row["platform"]} for row in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Notification delivery
    # ------------------------------------------------------------------

    def send_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict] = None,
    ) -> Dict:
        """Send a push notification to all active devices for a user."""
        tokens = self._get_active_tokens(user_id)
        if not tokens:
            logger.debug("No active device tokens for user %s", user_id)
            return {"sent": 0, "failed": 0}

        sent, failed = 0, 0
        for token_info in tokens:
            success = self.send_to_device(
                device_token=token_info["device_token"],
                notification={"title": title, "body": body, "data": data or {}},
                platform=token_info["platform"],
            )
            if success:
                sent += 1
                self._update_last_used(token_info["device_token"])
            else:
                failed += 1
                self.handle_delivery_status(token_info["device_token"], success=False)

        return {"sent": sent, "failed": failed}

    def send_to_device(
        self,
        device_token: str,
        notification: Dict,
        platform: str = "android",
    ) -> bool:
        """
        Send a notification to a specific device with platform-specific payload.
        Uses exponential backoff with up to MAX_RETRIES attempts.
        Returns True on success, False after all retries exhausted.
        """
        payload = self._build_payload(device_token, notification, platform)
        server_key = os.environ.get("FCM_SERVER_KEY", "")
        headers = {
            "Authorization": f"key={server_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(FCM_ENDPOINT, json=payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    # FCM returns success=1 in the response body
                    if result.get("success", 0) == 1:
                        return True
                    # Token no longer valid
                    if result.get("failure", 0) == 1:
                        logger.warning("FCM rejected token %s: %s", device_token, result)
                        return False
                elif response.status_code in (500, 503):
                    # Retriable server error
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(BACKOFF_BASE ** attempt)
                        continue
                else:
                    logger.error("FCM non-retriable error %s for token %s", response.status_code, device_token)
                    return False
            except requests.RequestException as exc:
                logger.warning("FCM request error (attempt %d): %s", attempt + 1, exc)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_BASE ** attempt)

        return False

    def handle_delivery_status(self, device_token: str, success: bool) -> None:
        """
        Track consecutive failures for a device token.
        After MAX_RETRIES consecutive failures, mark the token as inactive.
        On success, reset the failure counter.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if success:
                cursor.execute(
                    "UPDATE device_tokens SET last_used = ?, failure_count = 0, active = 1 WHERE device_token = ?",
                    (datetime.now(), device_token),
                )
            else:
                cursor.execute(
                    """
                    UPDATE device_tokens
                    SET failure_count = failure_count + 1,
                        active = CASE WHEN failure_count + 1 >= ? THEN 0 ELSE active END
                    WHERE device_token = ?
                    """,
                    (MAX_RETRIES, device_token),
                )
            conn.commit()
        except Exception as exc:
            logger.warning("handle_delivery_status error: %s", exc)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_payload(self, device_token: str, notification: Dict, platform: str) -> Dict:
        """Build a platform-specific FCM payload."""
        title = notification.get("title", "")
        body = notification.get("body", "")
        data = notification.get("data", {})

        if platform == "ios":
            # iOS uses APNs-specific fields via FCM's apns override
            return {
                "to": device_token,
                "notification": {"title": title, "body": body},
                "data": data,
                "apns": {
                    "payload": {
                        "aps": {
                            "alert": {"title": title, "body": body},
                            "sound": "default",
                            "badge": 1,
                        }
                    }
                },
            }
        else:
            # Android and Web use standard FCM format
            return {
                "to": device_token,
                "notification": {"title": title, "body": body},
                "data": data,
                "android": {
                    "priority": "high",
                    "notification": {"sound": "default", "click_action": "FLUTTER_NOTIFICATION_CLICK"},
                },
            }

    def _update_last_used(self, device_token: str) -> None:
        """Update the last_used timestamp for a device token."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE device_tokens SET last_used = ? WHERE device_token = ?",
                (datetime.now(), device_token),
            )
            conn.commit()
        finally:
            conn.close()

    def cleanup_inactive_tokens(self) -> int:
        """Remove device tokens that have been inactive. Returns count deleted."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM device_tokens WHERE active = 0")
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()
