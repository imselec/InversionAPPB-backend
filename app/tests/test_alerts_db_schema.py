"""
Unit tests for alerts database schema.
Tests CRUD operations for alerts, notification_history, and device_tokens tables.
Requirements: 14.1, 14.10
"""
import sqlite3
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import init_database


@pytest.fixture(scope="function")
def db():
    """Provide a fresh in-memory SQLite database for each test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # Create alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type VARCHAR(50) NOT NULL,
            ticker VARCHAR(10),
            target_price REAL,
            enabled BOOLEAN DEFAULT TRUE,
            last_triggered TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON alerts(ticker)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_enabled ON alerts(enabled)"
    )

    # Create notification_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_id INTEGER,
            alert_type VARCHAR(50) NOT NULL,
            ticker VARCHAR(10),
            message TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivered BOOLEAN DEFAULT FALSE,
            read BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (alert_id) REFERENCES alerts(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_user "
        "ON notification_history(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_sent "
        "ON notification_history(sent_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_read "
        "ON notification_history(read)"
    )

    # Create device_tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_token VARCHAR(255) NOT NULL UNIQUE,
            platform VARCHAR(20) NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            active BOOLEAN DEFAULT TRUE
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_device_user ON device_tokens(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_device_token "
        "ON device_tokens(device_token)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_device_active ON device_tokens(active)"
    )

    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Alert CRUD tests
# ---------------------------------------------------------------------------

class TestAlertCRUD:
    """Test Create/Read/Update/Delete operations for the alerts table."""

    def test_create_price_alert(self, db):
        """Test inserting a price alert."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price, enabled)
            VALUES (1, 'price', 'AVGO', 950.00, TRUE)
        """)
        db.commit()

        cursor.execute(
            "SELECT * FROM alerts WHERE user_id = 1 AND ticker = 'AVGO'"
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["user_id"] == 1
        assert row["alert_type"] == "price"
        assert row["ticker"] == "AVGO"
        assert row["target_price"] == 950.00
        assert row["enabled"] == 1  # SQLite stores TRUE as 1

    def test_create_alert_without_ticker(self, db):
        """Test inserting a non-price alert (e.g. monthly investment reminder)."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, enabled)
            VALUES (1, 'monthly_investment', TRUE)
        """)
        db.commit()

        cursor.execute(
            "SELECT * FROM alerts WHERE alert_type = 'monthly_investment'"
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["ticker"] is None
        assert row["target_price"] is None

    def test_read_alerts_by_user(self, db):
        """Test retrieving all alerts for a specific user."""
        cursor = db.cursor()
        for ticker, price in [("PG", 150.00), ("NEE", 75.00)]:
            cursor.execute("""
                INSERT INTO alerts (user_id, alert_type, ticker, target_price)
                VALUES (2, 'price', ?, ?)
            """, (ticker, price))
        db.commit()

        cursor.execute("SELECT * FROM alerts WHERE user_id = 2")
        rows = cursor.fetchall()

        assert len(rows) == 2
        tickers = {r["ticker"] for r in rows}
        assert tickers == {"PG", "NEE"}

    def test_update_alert_target_price(self, db):
        """Test updating the target price of an existing alert."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price)
            VALUES (1, 'price', 'JNJ', 160.00)
        """)
        db.commit()
        alert_id = cursor.lastrowid

        cursor.execute(
            "UPDATE alerts SET target_price = 170.00 WHERE id = ?",
            (alert_id,)
        )
        db.commit()

        cursor.execute("SELECT target_price FROM alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        assert row["target_price"] == 170.00

    def test_update_alert_enabled_flag(self, db):
        """Test disabling an alert."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price, enabled)
            VALUES (1, 'price', 'CVX', 160.00, TRUE)
        """)
        db.commit()
        alert_id = cursor.lastrowid

        cursor.execute(
            "UPDATE alerts SET enabled = FALSE WHERE id = ?", (alert_id,)
        )
        db.commit()

        cursor.execute("SELECT enabled FROM alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        assert row["enabled"] == 0  # FALSE stored as 0

    def test_delete_alert(self, db):
        """Test deleting an alert."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price)
            VALUES (1, 'price', 'XOM', 120.00)
        """)
        db.commit()
        alert_id = cursor.lastrowid

        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        db.commit()

        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        assert cursor.fetchone() is None

    def test_update_last_triggered(self, db):
        """Test recording when an alert was last triggered."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price)
            VALUES (1, 'price', 'ABBV', 180.00)
        """)
        db.commit()
        alert_id = cursor.lastrowid

        triggered_at = datetime.now().isoformat()
        cursor.execute(
            "UPDATE alerts SET last_triggered = ? WHERE id = ?",
            (triggered_at, alert_id)
        )
        db.commit()

        cursor.execute(
            "SELECT last_triggered FROM alerts WHERE id = ?", (alert_id,)
        )
        row = cursor.fetchone()
        assert row["last_triggered"] == triggered_at

    def test_read_only_enabled_alerts(self, db):
        """Test filtering alerts by enabled status."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price, enabled)
            VALUES (3, 'price', 'LMT', 500.00, TRUE)
        """)
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price, enabled)
            VALUES (3, 'price', 'RTX', 100.00, FALSE)
        """)
        db.commit()

        cursor.execute(
            "SELECT * FROM alerts WHERE user_id = 3 AND enabled = TRUE"
        )
        rows = cursor.fetchall()

        assert len(rows) == 1
        assert rows[0]["ticker"] == "LMT"


# ---------------------------------------------------------------------------
# Notification history tests
# ---------------------------------------------------------------------------

class TestNotificationHistoryCRUD:
    """Test recording and reading notification history."""

    def _insert_alert(self, db, user_id=1, alert_type="price", ticker="AVGO"):
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO alerts (user_id, alert_type, ticker, target_price)
            VALUES (?, ?, ?, 950.00)
        """, (user_id, alert_type, ticker))
        db.commit()
        return cursor.lastrowid

    def test_record_notification(self, db):
        """Test inserting a notification history entry."""
        alert_id = self._insert_alert(db)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, ticker, message, delivered, read)
            VALUES (1, ?, 'price', 'AVGO', 'AVGO reached $950', FALSE, FALSE)
        """, (alert_id,))
        db.commit()

        cursor.execute(
            "SELECT * FROM notification_history WHERE user_id = 1"
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["alert_type"] == "price"
        assert row["ticker"] == "AVGO"
        assert row["message"] == "AVGO reached $950"
        assert row["delivered"] == 0
        assert row["read"] == 0

    def test_notification_without_alert_id(self, db):
        """Test inserting a notification not linked to a specific alert."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_type, message)
            VALUES (1, 'news', 'Important news for your portfolio')
        """)
        db.commit()

        cursor.execute(
            "SELECT * FROM notification_history WHERE alert_type = 'news'"
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["alert_id"] is None

    def test_mark_notification_delivered(self, db):
        """Test marking a notification as delivered."""
        alert_id = self._insert_alert(db)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, ticker, message)
            VALUES (1, ?, 'price', 'AVGO', 'AVGO reached $950')
        """, (alert_id,))
        db.commit()
        notif_id = cursor.lastrowid

        cursor.execute(
            "UPDATE notification_history SET delivered = TRUE WHERE id = ?",
            (notif_id,)
        )
        db.commit()

        cursor.execute(
            "SELECT delivered FROM notification_history WHERE id = ?",
            (notif_id,)
        )
        assert cursor.fetchone()["delivered"] == 1

    def test_mark_notification_read(self, db):
        """Test marking a notification as read."""
        alert_id = self._insert_alert(db)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, ticker, message, delivered)
            VALUES (1, ?, 'price', 'AVGO', 'AVGO reached $950', TRUE)
        """, (alert_id,))
        db.commit()
        notif_id = cursor.lastrowid

        cursor.execute(
            "UPDATE notification_history SET read = TRUE WHERE id = ?",
            (notif_id,)
        )
        db.commit()

        cursor.execute(
            "SELECT read FROM notification_history WHERE id = ?", (notif_id,)
        )
        assert cursor.fetchone()["read"] == 1

    def test_read_notification_history_by_user(self, db):
        """Test retrieving all notifications for a user."""
        alert_id = self._insert_alert(db, user_id=5)
        cursor = db.cursor()
        messages = ["Price alert triggered", "Dividend upcoming", "Rebalance needed"]
        for msg in messages:
            cursor.execute("""
                INSERT INTO notification_history
                    (user_id, alert_id, alert_type, message)
                VALUES (5, ?, 'price', ?)
            """, (alert_id, msg))
        db.commit()

        cursor.execute(
            "SELECT * FROM notification_history WHERE user_id = 5"
        )
        rows = cursor.fetchall()
        assert len(rows) == 3

    def test_notification_history_ordered_by_sent_at(self, db):
        """Test that notifications can be ordered by sent_at timestamp."""
        alert_id = self._insert_alert(db, user_id=6)
        cursor = db.cursor()
        now = datetime.now()
        for i, msg in enumerate(["first", "second", "third"]):
            ts = (now + timedelta(seconds=i)).isoformat()
            cursor.execute("""
                INSERT INTO notification_history
                    (user_id, alert_id, alert_type, message, sent_at)
                VALUES (6, ?, 'price', ?, ?)
            """, (alert_id, msg, ts))
        db.commit()

        cursor.execute("""
            SELECT message FROM notification_history
            WHERE user_id = 6
            ORDER BY sent_at ASC
        """)
        rows = cursor.fetchall()
        assert [r["message"] for r in rows] == ["first", "second", "third"]

    def test_notification_foreign_key_references_alert(self, db):
        """Test that notification_history stores the correct alert_id."""
        alert_id = self._insert_alert(db, user_id=1, ticker="PG")
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, ticker, message)
            VALUES (1, ?, 'price', 'PG', 'PG hit target')
        """, (alert_id,))
        db.commit()

        cursor.execute(
            "SELECT alert_id FROM notification_history WHERE ticker = 'PG'"
        )
        row = cursor.fetchone()
        assert row["alert_id"] == alert_id

    def test_unread_notifications_filter(self, db):
        """Test filtering unread notifications."""
        alert_id = self._insert_alert(db, user_id=7)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, message, read)
            VALUES (7, ?, 'price', 'unread msg', FALSE)
        """, (alert_id,))
        cursor.execute("""
            INSERT INTO notification_history
                (user_id, alert_id, alert_type, message, read)
            VALUES (7, ?, 'price', 'read msg', TRUE)
        """, (alert_id,))
        db.commit()

        cursor.execute(
            "SELECT * FROM notification_history WHERE user_id = 7 AND read = FALSE"
        )
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["message"] == "unread msg"


# ---------------------------------------------------------------------------
# Device token management tests
# ---------------------------------------------------------------------------

class TestDeviceTokenCRUD:
    """Test Create/Read/Update/Delete operations for device_tokens table."""

    def test_register_device_token(self, db):
        """Test registering a new device token."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES (1, 'token_abc123', 'ios')
        """)
        db.commit()

        cursor.execute(
            "SELECT * FROM device_tokens WHERE device_token = 'token_abc123'"
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["user_id"] == 1
        assert row["platform"] == "ios"
        assert row["active"] == 1  # default TRUE

    def test_register_android_token(self, db):
        """Test registering an Android device token."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES (2, 'android_token_xyz', 'android')
        """)
        db.commit()

        cursor.execute(
            "SELECT platform FROM device_tokens WHERE device_token = 'android_token_xyz'"
        )
        row = cursor.fetchone()
        assert row["platform"] == "android"

    def test_register_web_token(self, db):
        """Test registering a web push token."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES (3, 'web_push_token_001', 'web')
        """)
        db.commit()

        cursor.execute(
            "SELECT platform FROM device_tokens WHERE device_token = 'web_push_token_001'"
        )
        row = cursor.fetchone()
        assert row["platform"] == "web"

    def test_device_token_uniqueness(self, db):
        """Test that duplicate device tokens are rejected."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES (1, 'unique_token_999', 'ios')
        """)
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO device_tokens (user_id, device_token, platform)
                VALUES (2, 'unique_token_999', 'android')
            """)
            db.commit()

    def test_deactivate_device_token(self, db):
        """Test marking a device token as inactive."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform, active)
            VALUES (1, 'token_to_deactivate', 'ios', TRUE)
        """)
        db.commit()
        token_id = cursor.lastrowid

        cursor.execute(
            "UPDATE device_tokens SET active = FALSE WHERE id = ?", (token_id,)
        )
        db.commit()

        cursor.execute(
            "SELECT active FROM device_tokens WHERE id = ?", (token_id,)
        )
        assert cursor.fetchone()["active"] == 0

    def test_delete_device_token(self, db):
        """Test unregistering (deleting) a device token."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES (1, 'token_to_delete', 'ios')
        """)
        db.commit()
        token_id = cursor.lastrowid

        cursor.execute(
            "DELETE FROM device_tokens WHERE id = ?", (token_id,)
        )
        db.commit()

        cursor.execute(
            "SELECT * FROM device_tokens WHERE id = ?", (token_id,)
        )
        assert cursor.fetchone() is None

    def test_get_active_tokens_for_user(self, db):
        """Test retrieving only active tokens for a user."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform, active)
            VALUES (4, 'active_token_1', 'ios', TRUE)
        """)
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform, active)
            VALUES (4, 'inactive_token_1', 'android', FALSE)
        """)
        db.commit()

        cursor.execute(
            "SELECT * FROM device_tokens WHERE user_id = 4 AND active = TRUE"
        )
        rows = cursor.fetchall()

        assert len(rows) == 1
        assert rows[0]["device_token"] == "active_token_1"

    def test_update_last_used_timestamp(self, db):
        """Test updating the last_used timestamp when a token is used."""
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES (1, 'token_last_used', 'ios')
        """)
        db.commit()
        token_id = cursor.lastrowid

        last_used = datetime.now().isoformat()
        cursor.execute(
            "UPDATE device_tokens SET last_used = ? WHERE id = ?",
            (last_used, token_id)
        )
        db.commit()

        cursor.execute(
            "SELECT last_used FROM device_tokens WHERE id = ?", (token_id,)
        )
        row = cursor.fetchone()
        assert row["last_used"] == last_used

    def test_multiple_tokens_per_user(self, db):
        """Test that a user can have multiple device tokens."""
        cursor = db.cursor()
        for i, platform in enumerate(["ios", "android", "web"]):
            cursor.execute("""
                INSERT INTO device_tokens (user_id, device_token, platform)
                VALUES (8, ?, ?)
            """, (f"multi_token_{i}", platform))
        db.commit()

        cursor.execute(
            "SELECT * FROM device_tokens WHERE user_id = 8"
        )
        rows = cursor.fetchall()
        assert len(rows) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
